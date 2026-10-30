import hashlib
import json
from pathlib import Path

import pytest

import homebrew_bottle as bottles
import tap_updater as updater


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


class TestBottlePublication:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.archive = tmp_path / "agent-vm--0.1.0.arm64_sequoia.bottle.tar.gz"
        self.archive.write_bytes(b"verified bottle")
        self.digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.bottle = {"tag": "arm64_sequoia", "sha256": self.digest,
                       "filename": "agent-vm-0.1.0.arm64_sequoia.bottle.tar.gz",
                       "archive": self.archive}
        self.releases = []
        self.created = []
        self.existing_bytes = self.archive.read_bytes()


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
        bottles.publish_bottle("agent-vm", self.bottle, "v0.1.0", "base-sha", runner=self.external_boundary)
        args, contents = self.created[0]
        assert contents == b"verified bottle"
        assert args[3] == bottles.release_name("agent-vm", "v0.1.0", self.digest)
        assert args[args.index("--repo") + 1] == bottles.TAP
        assert args[args.index("--target") + 1] == "base-sha"
        assert "--latest=false" in args
        assert Path(args[4]).name == self.bottle["filename"]

    def test_reuses_existing_asset_after_verifying_checksum(self):
        self.releases = [{"tagName": bottles.release_name("agent-vm", "v0.1.0", self.digest)}]
        bottles.publish_bottle("agent-vm", self.bottle, "v0.1.0", "base-sha", runner=self.external_boundary)
        assert self.created == []

    def test_does_not_overwrite_mismatched_existing_asset(self):
        self.releases = [{"tagName": bottles.release_name("agent-vm", "v0.1.0", self.digest)}]
        self.existing_bytes = b"different content"
        with pytest.raises(ValueError, match="different checksum"):
            bottles.publish_bottle("agent-vm", self.bottle, "v0.1.0", "base-sha", runner=self.external_boundary)
        assert self.created == []


@pytest.mark.parametrize("name", ["namu", "agent-vm"])
def test_validate_only_uses_same_pipeline_without_github(name, monkeypatch):
    calls = []
    monkeypatch.setattr(updater, "require_host", lambda **kwargs: None)
    monkeypatch.setattr(updater.bottles, "validate_formula", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(updater, "run", lambda *args, **kwargs: pytest.fail("Unexpected GitHub operation"))
    monkeypatch.setattr(updater.sys, "argv", ["update-package.py", name, "--validate-only"])
    assert updater.main() == 0
    assert calls[0][0][0] == updater.ROOT / f"Formula/{name}.rb"
    assert calls[0][1]["name"] == name


@pytest.mark.parametrize("name", ["namu", "agent-vm"])
def test_empty_workflow_version_selects_latest_stable(name, monkeypatch):
    calls = []
    monkeypatch.setattr(updater, "update_package", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(updater.sys, "argv", ["update-package.py", name, "--version", ""])
    assert updater.main() == 0
    assert calls[0][0] == (updater.PACKAGES[name], None)


@pytest.mark.parametrize("name", ["namu", "agent-vm"])
def test_legacy_script_calls_shared_cli(name, monkeypatch):
    calls = []
    monkeypatch.setattr(updater, "update_package", lambda *args, **kwargs: calls.append((args, kwargs)))
    monkeypatch.setattr(updater.sys, "argv", [f"update-{name}.py", "--version", "v0.2.0"])
    assert updater.main(name) == 0
    assert calls[0][0] == (updater.PACKAGES[name], "v0.2.0")


@pytest.mark.parametrize("args", [["--dry-run"], ["--version", "v0.2.0", "--validate-only"]])
def test_invalid_cli_combinations_are_rejected(args, monkeypatch):
    monkeypatch.setattr(updater.sys, "argv", ["update-package.py", "namu", *args])
    with pytest.raises(SystemExit) as error:
        updater.main()
    assert error.value.code == 2


def test_rejects_incomplete_managed_readme_section():
    with pytest.raises(ValueError, match="managed README"):
        updater.readme_with_install(updater.PACKAGES["agent-vm"], "<!-- agent-vm:start -->", updater.ROOT)
