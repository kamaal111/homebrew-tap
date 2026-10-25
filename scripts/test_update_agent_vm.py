import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "updater", Path(__file__).with_name("update-agent-vm.py")
)
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)
TEMPLATE = (
    Path(__file__).resolve().parent.parent / "packaging/homebrew/agent-vm.rb.in"
).read_text()
DIGEST = "a" * 64
BOTTLE = {"tag": "arm64_sequoia", "sha256": "b" * 64}


def release(tag="v0.1.0", **changes):
    return {
        "tagName": tag,
        "isDraft": False,
        "isPrerelease": False,
        "assets": [
            {"name": f"agent-vm_{tag[1:]}_darwin_arm64.tar.gz"},
            {"name": "checksums.txt"},
        ],
        **changes,
    }


class TestRelease:
    def test_accepts_exact_stable_release(self):
        assert updater.validate_release(release(), "v0.1.0") == "v0.1.0"

    def test_accepts_latest_stable_without_requested_version(self):
        assert updater.validate_release(release("v0.2.0"), None) == "v0.2.0"

    def test_rejects_prerelease(self):
        with pytest.raises(ValueError):
            updater.validate_release(release(isPrerelease=True), None)

    def test_rejects_draft(self):
        with pytest.raises(ValueError):
            updater.validate_release(release(isDraft=True), None)

    def test_rejects_missing_artifacts(self):
        with pytest.raises(ValueError):
            updater.validate_release(release(assets=[]), None)

    def test_rejects_tag_mismatch(self):
        with pytest.raises(ValueError):
            updater.validate_release(release(), "v0.2.0")

    def test_rejects_shell_injection_version(self):
        with pytest.raises(ValueError):
            updater.version_tuple("v0.1.0; touch /tmp/should-not-exist")

    def test_compares_versions_numerically(self):
        assert updater.version_tuple("v0.10.0") > updater.version_tuple("v0.9.0")

    def test_rejects_downgrade(self):
        with pytest.raises(ValueError):
            updater.ensure_upgrade("v0.2.0", "v0.1.0")

    def test_allows_first_version(self):
        assert updater.ensure_upgrade(None, "v0.1.0") is None

    def test_allows_same_version(self):
        assert updater.ensure_upgrade("v0.1.0", "v0.1.0") is None


class TestChecksum:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.archive = tmp_path / "agent-vm_0.1.0_darwin_arm64.tar.gz"
        self.archive.write_bytes(b"archive fixture")
        self.digest = hashlib.sha256(b"archive fixture").hexdigest()
        self.line = f"{self.digest}  {self.archive.name}\n"

    def test_accepts_verified_archive(self):
        assert updater.verify_checksum(self.line, self.archive) == self.digest

    def test_rejects_corrupted_archive(self):
        self.archive.write_bytes(b"corrupted")
        with pytest.raises(ValueError):
            updater.verify_checksum(self.line, self.archive)

    def test_rejects_duplicate_checksums(self):
        with pytest.raises(ValueError):
            updater.verify_checksum(self.line * 2, self.archive)

    def test_rejects_checksum_for_other_filename(self):
        with pytest.raises(ValueError):
            updater.verify_checksum(f"{self.digest}  other.tar.gz\n", self.archive)


class TestFormula:
    def test_formula_contains_verified_url_and_platform_requirements(self):
        formula = updater.render_formula(TEMPLATE, "v0.1.0", DIGEST)
        assert "depends_on arch: :arm64" in formula
        assert "depends_on :macos" in formula
        assert "/v0.1.0/agent-vm_0.1.0_darwin_arm64.tar.gz" in formula
        assert f'sha256 "{DIGEST}"' in formula
        assert updater.formula_version(formula) == "v0.1.0"

    def test_readme_updates_are_idempotent(self):
        first = updater.readme_with_install("# Homebrew Tap\n")
        assert updater.readme_with_install(first) == first
        assert "brew install kamaal111/tap/agent-vm" in first

    def test_readme_preserves_existing_prose(self):
        assert updater.readme_with_install(
            "# Tap\n\nExisting instructions.\n"
        ).startswith("# Tap\n\nExisting instructions.\n")

    def test_rejects_broken_managed_readme(self):
        with pytest.raises(ValueError):
            updater.readme_with_install(updater.BEGIN)

    def test_accepts_owned_single_commit(self):
        assert (
            updater.validate_owned_change(
                updater.MARKER,
                {"Formula/agent-vm.rb", "README.md"},
                1,
                updater.render_formula(TEMPLATE, "v0.1.0", DIGEST),
                TEMPLATE,
                "# Tap\n",
                updater.readme_with_install("# Tap\n"),
            )
            is None
        )

    def test_rejects_additional_manual_commit(self):
        with pytest.raises(ValueError):
            updater.validate_owned_change(
                updater.MARKER,
                {"Formula/agent-vm.rb"},
                2,
                updater.render_formula(TEMPLATE, "v0.1.0", DIGEST),
                TEMPLATE,
                "# Tap\n",
                updater.readme_with_install("# Tap\n"),
            )

    def test_rejects_unrelated_branch_files(self):
        with pytest.raises(ValueError):
            updater.validate_owned_change(
                updater.MARKER,
                {"Formula/open_api_maker.rb"},
                1,
                updater.render_formula(TEMPLATE, "v0.1.0", DIGEST),
                TEMPLATE,
                "# Tap\n",
                updater.readme_with_install("# Tap\n"),
            )

    def test_rejects_manual_formula_edits(self):
        with pytest.raises(ValueError):
            updater.validate_owned_change(
                updater.MARKER,
                {"Formula/agent-vm.rb"},
                1,
                updater.render_formula(TEMPLATE, "v0.1.0", DIGEST) + "# manual\n",
                TEMPLATE,
                "# Tap\n",
                updater.readme_with_install("# Tap\n"),
            )

    def test_rejects_manual_readme_edits(self):
        with pytest.raises(ValueError):
            updater.validate_owned_change(
                updater.MARKER,
                {"README.md"},
                1,
                updater.render_formula(TEMPLATE, "v0.1.0", DIGEST),
                TEMPLATE,
                "# Tap\n",
                updater.readme_with_install("# Tap\n") + "manual\n",
            )


class ValidationRecorder:
    def __init__(self):
        self.calls = 0

    def __call__(self, formula, work):
        self.calls += 1
        return BOTTLE


class TestUpdateIntegration:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, monkeypatch):
        self.root = tmp_path
        self.local = self.root / "local"
        self.remote = self.root / "remote.git"
        self.real_run = updater.run
        self.real_run(
            "git", "init", "--quiet", "--initial-branch=main", str(self.local)
        )
        self.real_run("git", "config", "user.name", "Updater Test", cwd=self.local)
        self.real_run("git", "config", "user.email", "test@example.com", cwd=self.local)
        self.real_run("git", "config", "commit.gpgsign", "false", cwd=self.local)
        (self.local / "README.md").write_text("# Fixture Tap\n")
        template_path = self.local / "packaging/homebrew/agent-vm.rb.in"
        template_path.parent.mkdir(parents=True)
        template_path.write_text(TEMPLATE)
        self.real_run("git", "add", ".", cwd=self.local)
        self.real_run(
            "git", "commit", "--quiet", "-m", "Initial fixture", cwd=self.local
        )
        self.real_run(
            "git", "clone", "--quiet", "--bare", str(self.local), str(self.remote)
        )
        self.real_run(
            "git", "remote", "add", "origin", str(self.remote), cwd=self.local
        )
        self.archive = self.root / "agent-vm_0.1.0_darwin_arm64.tar.gz"
        self.archive.write_bytes(b"downloaded fixture")
        self.digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.prs = []
        self.created = 0
        self.edited = 0
        self.validation = ValidationRecorder()
        monkeypatch.setattr(updater, "SCRIPT_ROOT", self.local)
        monkeypatch.setattr(updater, "run", self.external_boundary)
        monkeypatch.setattr(updater.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(updater.platform, "machine", lambda: "arm64")
        monkeypatch.setattr(updater.shutil, "which", lambda tool: "/fixture/tool")
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setattr(updater, "validate_formula", self.validation)
        monkeypatch.setattr(updater, "publish_bottle", lambda *args: None)

    def external_boundary(self, *args, cwd=None, env=None):
        if args[0] != "gh":
            return self.real_run(*args, cwd=cwd, env=env)
        if args[1:3] == ("auth", "status"):
            return "Authenticated fixture"
        if args[1:3] == ("release", "view"):
            return json.dumps(release())
        if args[1:3] == ("release", "download"):
            assets = Path(args[args.index("--dir") + 1])
            shutil.copyfile(self.archive, assets / self.archive.name)
            (assets / "checksums.txt").write_text(
                f"{self.digest}  {self.archive.name}\n"
            )
            return ""
        if args[1:3] == ("repo", "clone"):
            return self.real_run("git", "clone", "--quiet", str(self.remote), args[4])
        if args[1:3] == ("repo", "view"):
            return json.dumps({"defaultBranchRef": {"name": "main"}})
        if args[1:3] == ("pr", "list"):
            return json.dumps(self.prs)
        if args[1:3] == ("pr", "create"):
            self.created += 1
            self.prs = [
                {
                    "number": 1,
                    "baseRefName": "main",
                    "url": "https://example.com/pr/1",
                    "headRefOid": self.real_run(
                        "git", "rev-parse", updater.BRANCH, cwd=self.remote
                    ),
                }
            ]
            return self.prs[0]["url"]
        if args[1:3] == ("pr", "edit"):
            self.edited += 1
            self.prs[0]["headRefOid"] = self.real_run(
                "git", "rev-parse", updater.BRANCH, cwd=self.remote
            )
            return self.prs[0]["url"]
        raise AssertionError(f"Unexpected external operation: {args}")

    def test_rejects_linux_before_remote_operations(self, monkeypatch):
        monkeypatch.setattr(updater.platform, "system", lambda: "Linux")
        with pytest.raises(ValueError, match="Apple Silicon macOS"):
            updater.update("v0.1.0")
        assert self.created == 0
        assert self.validation.calls == 0

    def test_rejects_intel_before_remote_operations(self, monkeypatch):
        monkeypatch.setattr(updater.platform, "machine", lambda: "x86_64")
        with pytest.raises(ValueError, match="Apple Silicon macOS"):
            updater.update("v0.1.0")
        assert self.created == 0
        assert self.validation.calls == 0

    def test_initial_update_publishes_one_commit_and_preserves_caller_checkout(self):
        initial = self.real_run("git", "rev-parse", "HEAD", cwd=self.local)
        updater.update("v0.1.0")
        assert self.created == 1
        assert (
            self.real_run(
                "git", "rev-list", "--count", "main..update-agent-vm", cwd=self.remote
            )
            == "1"
        )
        assert self.real_run("git", "rev-parse", "HEAD", cwd=self.local) == initial
        assert self.real_run("git", "status", "--porcelain", cwd=self.local) == ""
        assert self.validation.calls == 1

    def test_repeated_update_reuses_pr(self):
        updater.update("v0.1.0")
        updater.update("v0.1.0")
        assert self.created == 1
        assert self.edited == 1
        assert (
            self.real_run(
                "git", "rev-list", "--count", "main..update-agent-vm", cwd=self.remote
            )
            == "1"
        )

    def test_merged_version_is_no_op_without_validation_or_push(self):
        updater.update("v0.1.0")
        self.real_run(
            "git", "fetch", "--quiet", "origin", updater.BRANCH, cwd=self.local
        )
        self.real_run(
            "git", "merge", "--quiet", "--ff-only", "FETCH_HEAD", cwd=self.local
        )
        self.real_run("git", "push", "--quiet", "origin", "main", cwd=self.local)
        self.prs = []
        self.validation.calls = 0
        updater.update("v0.1.0")
        assert self.created == 1
        assert self.edited == 0
        assert self.validation.calls == 0

    def test_recovers_owned_branch_when_pr_creation_previously_failed(self):
        updater.update("v0.1.0")
        self.prs = []
        updater.update("v0.1.0")
        assert self.created == 2
        assert (
            self.real_run(
                "git", "rev-list", "--count", "main..update-agent-vm", cwd=self.remote
            )
            == "1"
        )

    def test_checksum_failure_does_not_create_branch_or_pr(self):
        self.digest = "0" * 64
        with pytest.raises(ValueError):
            updater.update("v0.1.0")
        assert self.created == 0
        assert (
            self.real_run("git", "branch", "--list", updater.BRANCH, cwd=self.remote)
            == ""
        )
        assert self.validation.calls == 0

    def test_manual_commit_blocks_branch_replacement(self):
        updater.update("v0.1.0")
        self.real_run(
            "git", "fetch", "--quiet", "origin", updater.BRANCH, cwd=self.local
        )
        self.real_run(
            "git", "checkout", "--quiet", "-b", "manual", "FETCH_HEAD", cwd=self.local
        )
        (self.local / "manual.txt").write_text("manual change\n")
        self.real_run("git", "add", ".", cwd=self.local)
        self.real_run("git", "commit", "--quiet", "-m", "Manual change", cwd=self.local)
        self.real_run(
            "git",
            "push",
            "--quiet",
            "origin",
            "HEAD:refs/heads/update-agent-vm",
            cwd=self.local,
        )
        manual_sha = self.real_run("git", "rev-parse", "HEAD", cwd=self.local)
        self.prs[0]["headRefOid"] = manual_sha
        with pytest.raises(ValueError):
            updater.update("v0.1.0")
        assert (
            self.real_run("git", "rev-parse", updater.BRANCH, cwd=self.remote)
            == manual_sha
        )
        assert self.edited == 0


class TestBottle:
    def test_checked_in_formula_matches_its_template_and_bottle(self):
        formula = (updater.SCRIPT_ROOT / "Formula/agent-vm.rb").read_text()
        digest = updater.re.search(r'^  sha256 "([0-9a-f]{64})"$', formula, updater.re.MULTILINE)[1]
        assert updater.render_formula(
            TEMPLATE, updater.formula_version(formula), digest, updater.formula_bottle(formula),
        ) == formula

    def test_renders_bottle_without_changing_application_version(self):
        formula = updater.render_formula(TEMPLATE, "v0.1.0", DIGEST, BOTTLE)
        assert updater.formula_version(formula) == "v0.1.0"
        assert updater.formula_bottle(formula) == BOTTLE
        assert f'sha256 "{DIGEST}"' in formula
        assert updater.bottle_root("v0.1.0", BOTTLE["sha256"]) in formula
        assert "@BOTTLE@" not in formula

    def test_source_formula_can_be_used_to_build_bottle(self):
        formula = updater.render_formula(TEMPLATE, "v0.1.0", DIGEST)
        assert updater.formula_bottle(formula) is None
        assert "@BOTTLE@" not in formula

    def test_rejects_wrong_architecture(self):
        with pytest.raises(ValueError, match="macOS bottle tag"):
            updater.render_formula(TEMPLATE, "v0.1.0", DIGEST, {**BOTTLE, "tag": "x86_64_linux"})

    def test_rejects_invalid_bottle_checksum(self):
        with pytest.raises(ValueError, match="bottle SHA256"):
            updater.render_formula(TEMPLATE, "v0.1.0", DIGEST, {**BOTTLE, "sha256": "bad"})

    def test_accepts_owned_bottle_update(self):
        assert updater.validate_owned_change(
            updater.MARKER, {"Formula/agent-vm.rb"}, 1,
            updater.render_formula(TEMPLATE, "v0.1.0", DIGEST, BOTTLE),
            TEMPLATE, "# Tap\n", updater.readme_with_install("# Tap\n"),
        ) is None

    def test_rejects_manually_changed_bottle_url(self):
        formula = updater.render_formula(TEMPLATE, "v0.1.0", DIGEST, BOTTLE)
        with pytest.raises(ValueError, match="unexpected manual edits"):
            updater.validate_owned_change(
                updater.MARKER, {"Formula/agent-vm.rb"}, 1,
                formula.replace("/releases/download/agent-vm-", "/releases/download/manual-"),
                TEMPLATE, "# Tap\n", updater.readme_with_install("# Tap\n"),
            )

    def test_checksum_mismatch_prevents_publication(self, tmp_path, monkeypatch):
        archive = tmp_path / "agent-vm.bottle.tar.gz"
        archive.write_bytes(b"corrupt")
        monkeypatch.setattr(updater, "run", lambda *args, **kwargs: pytest.fail("Unexpected publication"))
        with pytest.raises(ValueError, match="mismatched checksum"):
            updater.publish_bottle({**BOTTLE, "archive": archive}, "v0.1.0", "base-sha")


class TestValidationOnly:
    def test_validates_without_github_or_publication(self, monkeypatch):
        calls = []
        monkeypatch.setattr(updater.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(updater.platform, "machine", lambda: "arm64")
        monkeypatch.setattr(updater.shutil, "which", lambda tool: None if tool == "gh" else "/fixture/tool")
        monkeypatch.setattr(updater, "validate_formula", lambda formula, work: calls.append(formula))
        monkeypatch.setattr(updater, "run", lambda *args, **kwargs: pytest.fail("Unexpected publication"))
        monkeypatch.setattr("sys.argv", ["update-agent-vm.py", "--validate-only"])
        assert updater.main() == 0
        assert calls == [updater.SCRIPT_ROOT / "Formula/agent-vm.rb"]

    def test_rejects_version_with_validation_only(self, monkeypatch):
        monkeypatch.setattr("sys.argv", ["update-agent-vm.py", "--validate-only", "--version", "v0.1.0"])
        with pytest.raises(SystemExit) as error:
            updater.main()
        assert error.value.code == 2


class TestBottlePublication:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path, monkeypatch):
        self.archive = tmp_path / "agent-vm--0.1.0.arm64_sequoia.bottle.tar.gz"
        self.archive.write_bytes(b"verified bottle")
        self.digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.bottle = {"tag": "arm64_sequoia", "sha256": self.digest,
                       "filename": "agent-vm-0.1.0.arm64_sequoia.bottle.tar.gz",
                       "archive": self.archive}
        self.releases = []
        self.created = []
        self.existing_bytes = self.archive.read_bytes()
        monkeypatch.setattr(updater, "run", self.external_boundary)

    def external_boundary(self, *args, **kwargs):
        if args[1:3] == ("release", "list"):
            return json.dumps(self.releases)
        if args[1:3] == ("release", "create"):
            self.created.append((args, Path(args[4]).read_bytes()))
            return "https://example.com/release"
        if args[1:3] == ("release", "download"):
            (Path(args[args.index("--dir") + 1]) / self.bottle["filename"]).write_bytes(self.existing_bytes)
            return ""
        raise AssertionError(f"Unexpected external operation: {args}")

    def test_publishes_verified_asset_to_checksum_named_tap_release(self):
        updater.publish_bottle(self.bottle, "v0.1.0", "base-sha")
        args, contents = self.created[0]
        assert contents == b"verified bottle"
        assert args[3] == updater.bottle_release("v0.1.0", self.digest)
        assert args[args.index("--repo") + 1] == updater.TAP
        assert args[args.index("--target") + 1] == "base-sha"
        assert "--latest=false" in args
        assert Path(args[4]).name == self.bottle["filename"]

    def test_reuses_existing_asset_after_verifying_checksum(self):
        self.releases = [{"tagName": updater.bottle_release("v0.1.0", self.digest)}]
        updater.publish_bottle(self.bottle, "v0.1.0", "base-sha")
        assert self.created == []

    def test_does_not_overwrite_mismatched_existing_asset(self):
        self.releases = [{"tagName": updater.bottle_release("v0.1.0", self.digest)}]
        self.existing_bytes = b"different content"
        with pytest.raises(ValueError, match="different checksum"):
            updater.publish_bottle(self.bottle, "v0.1.0", "base-sha")
        assert self.created == []
