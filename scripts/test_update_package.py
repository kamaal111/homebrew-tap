import hashlib
import json
from pathlib import Path
import subprocess

import pytest

import homebrew_bottle as bottles
import tap_updater as updater

ROOT = Path(__file__).resolve().parent.parent
BOTTLE = {"tag": "arm64_sequoia", "sha256": "b" * 64}


@pytest.fixture(params=tuple(updater.PACKAGES))
def package(request):
    return updater.PACKAGES[request.param]


def release(package, tag="v0.2.0", **changes):
    return {"tagName": tag, "isDraft": False, "isPrerelease": False,
            "assets": [{"name": f"{package.name}_{tag[1:]}_{t}.tar.gz"} for t in package.targets]
                      + [{"name": "checksums.txt"}], **changes}


class TestPackageFormula:
    def test_template_reproduces_current_formula(self, package):
        formula = (ROOT / package.formula_file).read_text()
        template = (ROOT / f"packaging/homebrew/{package.name}.rb.in").read_text()
        assert updater.render_formula(package, template, bottles.formula_version(formula),
                                      updater.formula_digests(package, formula), bottles.bottle_metadata(formula)) == formula

    def test_new_release_has_all_targets_and_no_old_bottle(self, package):
        template = (ROOT / f"packaging/homebrew/{package.name}.rb.in").read_text()
        digests = {t: "a" * 64 for t in package.targets}
        formula = updater.render_formula(package, template, "v0.2.0", digests)
        assert updater.formula_digests(package, formula) == digests
        assert formula.count(f'/releases/download/v0.2.0/{package.name}_') == len(package.targets)
        assert bottles.bottle_metadata(formula) is None

    @pytest.mark.parametrize("changes", [{"isDraft": True}, {"isPrerelease": True}, {"assets": []}])
    def test_rejects_unusable_release(self, package, changes):
        with pytest.raises(ValueError):
            updater.validate_release(release(package, **changes), None, package.name, package.targets)

    def test_rejects_duplicate_release_assets(self, package):
        metadata = release(package)
        metadata["assets"] *= 2
        with pytest.raises(ValueError):
            updater.validate_release(metadata, None, package.name, package.targets)

    def test_rejects_mismatched_release_tag(self, package):
        with pytest.raises(ValueError):
            updater.validate_release(release(package), "v0.3.0", package.name, package.targets)

    def test_rejects_missing_target_digest(self, package):
        template = (ROOT / f"packaging/homebrew/{package.name}.rb.in").read_text()
        with pytest.raises(ValueError):
            updater.render_formula(package, template, "v0.2.0", {})

    def test_rejects_wrong_bottle_architecture(self, package):
        template = (ROOT / f"packaging/homebrew/{package.name}.rb.in").read_text()
        with pytest.raises(ValueError, match="macOS bottle tag"):
            updater.render_formula(package, template, "v0.2.0", {t: "a" * 64 for t in package.targets},
                                   {**BOTTLE, "tag": "x86_64_linux"})

    def test_rejects_manual_formula_edits_on_owned_branch(self, package):
        template = (ROOT / f"packaging/homebrew/{package.name}.rb.in").read_text()
        formula = updater.render_formula(package, template, "v0.2.0", {t: "a" * 64 for t in package.targets}, BOTTLE)
        readme = updater.readme_with_install(package, "# Tap\n", ROOT)
        with pytest.raises(ValueError, match="manual edits"):
            updater.validate_owned_change(package, package.marker, {package.formula_file}, 1,
                                           formula + "# manual\n", "# Tap\n", readme, root=ROOT)

    def test_readme_updates_are_idempotent(self, package):
        readme = updater.readme_with_install(package, "# Tap\n", ROOT)
        assert updater.readme_with_install(package, readme, ROOT) == readme
        assert readme.startswith("# Tap\n")

    def test_rejects_manual_readme_edits_on_owned_branch(self, package):
        formula = (ROOT / package.formula_file).read_text()
        readme = updater.readme_with_install(package, "# Tap\n", ROOT)
        with pytest.raises(ValueError, match="manual edits"):
            updater.validate_owned_change(package, package.marker, {package.formula_file}, 1,
                                           formula, "# Tap\n", readme + "manual\n", root=ROOT)

    def test_legacy_owned_marker_is_accepted(self, package):
        formula = (ROOT / package.formula_file).read_text()
        readme = updater.readme_with_install(package, "# Tap\n", ROOT)
        assert updater.validate_owned_change(package, package.marker.upper(), {package.formula_file}, 1,
                                             formula, "# Tap\n", readme, root=ROOT) is None


class PackageFixture:
    def __init__(self, tmp_path, monkeypatch, tap_repository, package):
        self.package = package
        template = (ROOT / f"packaging/homebrew/{package.name}.rb.in").read_text()
        current = updater.render_formula(package, template, "v0.1.0", {t: "a" * 64 for t in package.targets}, BOTTLE)
        files = {"README.md": "# Fixture Tap\n", package.formula_file: current,
                 f"packaging/homebrew/{package.name}.rb.in": template}
        readme = ROOT / f"packaging/homebrew/{package.name}.md"
        if readme.exists():
            files[f"packaging/homebrew/{package.name}.md"] = readme.read_text()
        self.local, self.remote, self.real_run = tap_repository(files)
        self.root = tmp_path
        self.prs, self.calls = [], []
        self.created, self.edited, self.validated, self.published = 0, 0, 0, 0
        self.fail_pr = self.fail_bottle = self.corrupt = self.change_base = self.change_head = False
        self.fail_validation = False
        self.tag = "v0.2.0"
        self.archives = {target: f"verified {target}".encode() for target in self.package.targets}
        monkeypatch.setattr(updater.platform, "system", lambda: "Darwin")
        monkeypatch.setattr(updater.platform, "machine", lambda: "arm64")
        monkeypatch.setattr(updater.shutil, "which", lambda tool: "/fixture/tool")
        monkeypatch.setenv("GITHUB_ACTIONS", "true")
        monkeypatch.setattr(bottles, "validate_formula", self.validate)

    def validate(self, formula, work, **kwargs):
        self.validated += 1
        if self.fail_validation:
            raise ValueError("bottle validation failed")
        archive = work / f"{self.package.name}.bottle.tar.gz"
        archive.write_bytes(b"verified bottle")
        return {**BOTTLE, "archive": archive, "filename": archive.name,
                "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}

    def boundary(self, *args, cwd=None, env=None):
        self.calls.append(args)
        if args[:4] == ("git", "fetch", "--quiet", "origin") and args[4:] == ("main",) and self.change_base:
            self.real_run("git", "commit", "--allow-empty", "-qm", "Concurrent base", cwd=self.local)
            self.real_run("git", "push", "origin", "main", cwd=self.local)
        if args[:2] == ("git", "push") and self.change_head:
            self.real_run("git", "push", "origin", f"main:refs/heads/{self.package.branch}", cwd=self.local)
        if args[0] != "gh":
            return self.real_run(*args, cwd=cwd, env=env)
        action = args[1:3]
        if action == ("auth", "status"):
            return "Authenticated fixture"
        if action == ("release", "view"):
            return json.dumps(release(self.package, self.tag))
        if action == ("release", "download"):
            assets = Path(args[args.index("--dir") + 1])
            lines = []
            for target, data in self.archives.items():
                name = f"{self.package.name}_{self.tag[1:]}_{target}.tar.gz"
                (assets / name).write_bytes(data)
                lines.append(f"{hashlib.sha256(data).hexdigest()}  {name}\n")
            (assets / "checksums.txt").write_text("".join(lines))
            if self.corrupt:
                (assets / f"{self.package.name}_{self.tag[1:]}_{self.package.targets[-1]}.tar.gz").write_bytes(b"corrupt")
            return ""
        if action == ("release", "list"):
            return "[]"
        if action == ("release", "create"):
            if self.fail_bottle:
                raise ValueError("bottle publication failed")
            self.published += 1
            return "https://example.com/bottle"
        if action == ("repo", "clone"):
            return self.real_run("git", "clone", "--quiet", str(self.remote), args[4])
        if action == ("repo", "view"):
            return json.dumps({"defaultBranchRef": {"name": "main"}})
        if action == ("pr", "list"):
            return json.dumps(self.prs)
        if action == ("pr", "create"):
            if self.fail_pr:
                raise ValueError("PR creation failed")
            self.created += 1
            self.prs = [{"number": 1, "baseRefName": "main", "url": "https://example.com/pr/1",
                         "headRefOid": self.real_run("git", "rev-parse", self.package.branch, cwd=self.remote)}]
            return self.prs[0]["url"]
        if action == ("pr", "edit"):
            self.edited += 1
            self.prs[0]["headRefOid"] = self.real_run("git", "rev-parse", self.package.branch, cwd=self.remote)
            return self.prs[0]["url"]
        if action == ("workflow", "run"):
            return ""
        raise AssertionError(f"Unexpected external operation: {args}")

    def update(self, requested="v0.2.0", **options):
        return updater.update_package(self.package, requested, root=self.local, runner=self.boundary, **options)

    def merge(self):
        self.real_run("git", "fetch", "origin", self.package.branch, cwd=self.local)
        self.real_run("git", "merge", "--ff-only", "FETCH_HEAD", cwd=self.local)
        self.real_run("git", "push", "origin", "main", cwd=self.local)
        self.prs = []


@pytest.fixture
def fixture(tmp_path, monkeypatch, tap_repository, package):
    return PackageFixture(tmp_path, monkeypatch, tap_repository, package)


class TestPackageUpdate:
    def test_creates_one_commit_and_dispatches_validation_without_changing_caller(self, fixture):
        fixture.update("v0.2.0")
        assert fixture.created == 1
        assert fixture.published == 1
        assert fixture.real_run("git", "rev-list", "--count", f"main..{fixture.package.branch}", cwd=fixture.remote) == "1"
        assert fixture.real_run("git", "status", "--porcelain", cwd=fixture.local) == ""
        assert fixture.real_run("git", "diff", "--name-only", "main", fixture.package.branch, cwd=fixture.remote) in {fixture.package.formula_file, fixture.package.formula_file + "\nREADME.md"}
        assert ("gh", "workflow", "run", f"validate-{fixture.package.name}.yml", "--repo", bottles.TAP, "--ref", fixture.package.branch) in fixture.calls

    def test_initial_install_uses_the_same_update_pipeline(self, fixture):
        fixture.real_run("git", "rm", fixture.package.formula_file, cwd=fixture.local)
        fixture.real_run("git", "commit", "-qm", "Fixture without package", cwd=fixture.local)
        fixture.real_run("git", "push", "origin", "main", cwd=fixture.local)
        fixture.update("v0.2.0")
        create = next(call for call in fixture.calls if call[1:3] == ("pr", "create"))
        assert create[create.index("--title") + 1] == f"feat: add {fixture.package.name} 0.2.0"
        assert fixture.created == 1

    def test_unsupported_host_is_rejected_before_remote_operations(self, fixture, monkeypatch):
        monkeypatch.setattr(updater.platform, "system", lambda: "Linux")
        with pytest.raises(ValueError, match="Apple Silicon macOS"):
            fixture.update()
        assert fixture.calls == []

    def test_invalid_version_is_rejected_before_remote_operations(self, fixture):
        with pytest.raises(ValueError, match="stable vX.Y.Z"):
            fixture.update("v0.2.0; echo invalid")
        assert fixture.calls == []

    def test_latest_stable_without_explicit_tag(self, fixture):
        fixture.update(None)
        assert fixture.created == 1

    def test_repeated_update_refreshes_existing_single_commit_pr(self, fixture):
        fixture.update("v0.2.0")
        fixture.update("v0.2.0")
        assert fixture.created == 1
        assert fixture.edited == 1
        assert fixture.real_run("git", "rev-list", "--count", f"main..{fixture.package.branch}", cwd=fixture.remote) == "1"

    def test_merged_update_is_no_op_without_bottle_or_push(self, fixture):
        fixture.update("v0.2.0")
        fixture.merge()
        fixture.update("v0.2.0")
        assert fixture.created == 1
        assert fixture.published == 1
        assert fixture.validated == 1

    def test_dry_run_validates_and_writes_report_without_any_publication(self, fixture):
        output = fixture.root / "report"
        fixture.update("v0.2.0", dry_run=True, output_dir=output)
        assert fixture.created == fixture.published == 0
        assert fixture.validated == 1
        assert json.loads((output / "report.json").read_text())["dry_run"] is True
        assert 'version "0.2.0"' in (output / f"{fixture.package.name}.rb").read_text()
        assert fixture.real_run("git", "branch", "--list", fixture.package.branch, cwd=fixture.remote) == ""
        assert not any(call[:2] == ("git", "push") for call in fixture.calls)
        assert not any(call[1:3] in (("release", "create"), ("pr", "create"), ("workflow", "run")) for call in fixture.calls)

    def test_dry_run_rehearses_even_an_already_merged_version(self, fixture):
        fixture.update("v0.2.0")
        fixture.merge()
        output = fixture.root / "report"
        fixture.update("v0.2.0", dry_run=True, output_dir=output)
        assert fixture.validated == 2
        assert json.loads((output / "report.json").read_text())["version"] == "v0.2.0"
        assert fixture.published == 1

    def test_corrupted_last_archive_stops_before_bottle_and_publication(self, fixture):
        fixture.corrupt = True
        with pytest.raises(ValueError, match="checksum"):
            fixture.update("v0.2.0")
        assert fixture.validated == fixture.published == fixture.created == 0

    def test_bottle_validation_failure_prevents_publication(self, fixture):
        fixture.fail_validation = True
        with pytest.raises(ValueError, match="validation failed"):
            fixture.update("v0.2.0")
        assert fixture.published == fixture.created == 0

    def test_bottle_publication_failure_prevents_pr(self, fixture):
        fixture.fail_bottle = True
        with pytest.raises(ValueError, match="publication failed"):
            fixture.update("v0.2.0")
        assert fixture.created == 0
        assert fixture.real_run("git", "branch", "--list", fixture.package.branch, cwd=fixture.remote) == ""

    def test_pr_creation_failure_is_recoverable_from_owned_remote_branch(self, fixture):
        fixture.fail_pr = True
        with pytest.raises(ValueError, match="PR creation failed"):
            fixture.update("v0.2.0")
        fixture.fail_pr = False
        fixture.update("v0.2.0")
        assert fixture.created == 1
        assert fixture.real_run("git", "rev-list", "--count", f"main..{fixture.package.branch}", cwd=fixture.remote) == "1"

    def test_downgrade_is_rejected(self, fixture):
        fixture.update("v0.2.0")
        fixture.merge()
        fixture.tag = "v0.1.0"
        with pytest.raises(ValueError, match="downgrade"):
            fixture.update("v0.1.0")
        assert fixture.validated == 1

    def test_manual_branch_change_is_not_overwritten(self, fixture):
        fixture.update("v0.2.0")
        fixture.real_run("git", "fetch", "origin", fixture.package.branch, cwd=fixture.local)
        fixture.real_run("git", "checkout", "-b", "manual", "FETCH_HEAD", cwd=fixture.local)
        (fixture.local / "manual.txt").write_text("keep")
        fixture.real_run("git", "add", ".", cwd=fixture.local)
        fixture.real_run("git", "commit", "-qm", "Manual change", cwd=fixture.local)
        fixture.real_run("git", "push", "origin", f"HEAD:refs/heads/{fixture.package.branch}", cwd=fixture.local)
        manual = fixture.real_run("git", "rev-parse", "HEAD", cwd=fixture.local)
        fixture.prs[0]["headRefOid"] = manual
        with pytest.raises(ValueError, match="manual changes"):
            fixture.update("v0.2.0")
        assert fixture.real_run("git", "rev-parse", fixture.package.branch, cwd=fixture.remote) == manual
        assert fixture.edited == 0

    def test_changed_base_stops_before_bottle_publication(self, fixture):
        fixture.change_base = True
        with pytest.raises(ValueError, match="base changed"):
            fixture.update("v0.2.0")
        assert fixture.published == fixture.created == 0

    def test_concurrent_remote_branch_change_is_lease_protected(self, fixture):
        fixture.change_head = True
        with pytest.raises(subprocess.CalledProcessError):
            fixture.update("v0.2.0")
        assert fixture.created == 0
        assert fixture.real_run("git", "rev-parse", fixture.package.branch, cwd=fixture.remote) == fixture.real_run("git", "rev-parse", "main", cwd=fixture.remote)
