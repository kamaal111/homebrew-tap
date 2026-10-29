import hashlib
import json
from pathlib import Path

import pytest

import homebrew_bottle as bottles


FORMULA = (Path(__file__).resolve().parent.parent / "Formula/namu.rb").read_text()
DIGEST = "a" * 64
BOTTLE = {"tag": "arm64_golden_gate", "sha256": DIGEST}


class NativeHomebrew:
    def __init__(self, work, prefix, *, poured=True, cellar="any_skip_relocation", checksum=None):
        self.work, self.prefix = work, prefix
        self.poured, self.cellar, self.checksum = poured, cellar, checksum
        self.calls = []

    def __call__(self, *args, cwd=None, env=None):
        self.calls.append(args)
        if args[1:2] == ("bottle",):
            archive = self.work / "namu--0.1.0.arm64_golden_gate.bottle.tar.gz"
            archive.write_bytes(b"native bottle fixture")
            metadata = {"namu/validation/namu": {"bottle": {
                "cellar": self.cellar, "tags": {"arm64_golden_gate": {
                    "local_filename": archive.name,
                    "filename": "namu-0.1.0.arm64_golden_gate.bottle.tar.gz",
                    "sha256": self.checksum or hashlib.sha256(archive.read_bytes()).hexdigest(),
                }},
            }}}
            (self.work / "namu--0.1.0.arm64_golden_gate.bottle.json").write_text(json.dumps(metadata))
        if args[1:2] == ("install",) and "--build-bottle" not in args:
            receipt = self.prefix / "Cellar/namu/0.1.0/INSTALL_RECEIPT.json"
            receipt.parent.mkdir(parents=True, exist_ok=True)
            receipt.write_text(json.dumps({"poured_from_bottle": self.poured}))
        if args[1:] == ("--version",):
            return "namu version 0.1.0"
        if args[1:] == ("--help",):
            return "Create, open, list and delete Git worktrees"
        return ""


class TestBottleFormula:
    def test_adds_verified_native_bottle_and_preserves_source_archives(self):
        clean = bottles.with_bottle(FORMULA, "namu", BOTTLE)
        assert bottles.bottle_metadata(clean) == BOTTLE
        assert bottles.formula_version(clean) == "v0.1.0"
        assert bottles.root_url("namu", "v0.1.0", DIGEST) in clean
        assert clean.count('/releases/download/v0.1.0/namu_') == 4
        assert clean.count('bottle do') == 1

    def test_rendering_same_bottle_is_idempotent(self):
        first = bottles.with_bottle(FORMULA, "namu", BOTTLE)
        assert bottles.with_bottle(first, "namu", BOTTLE) == first

    def test_other_native_platform_can_be_tested_with_disposable_local_bottle(self):
        existing = bottles.with_bottle(FORMULA, "namu", BOTTLE)
        local = bottles.with_bottle(existing, "namu", {**BOTTLE, "tag": "arm64_sequoia"}, "file:///tmp/bottle")
        assert bottles.bottle_metadata(local)["tag"] == "arm64_sequoia"
        assert 'root_url "file:///tmp/bottle"' in local
        assert bottles.bottle_metadata(existing)["tag"] == "arm64_golden_gate"

    def test_rejects_bad_checksum(self):
        with pytest.raises(ValueError, match="SHA256"):
            bottles.with_bottle(FORMULA, "namu", {**BOTTLE, "sha256": "invalid"})

    def test_refuses_to_remove_another_platforms_bottle(self):
        first = bottles.with_bottle(FORMULA, "namu", BOTTLE)
        with pytest.raises(ValueError, match="different platform"):
            bottles.with_bottle(first, "namu", {**BOTTLE, "tag": "golden_gate"})


class TestNativeBottleValidation:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        self.work, self.prefix = tmp_path / "output", tmp_path / "prefix"
        self.work.mkdir()
        self.formula = tmp_path / "namu.rb"
        self.formula.write_text(FORMULA)

    def validate(self, runner):
        return bottles.validate_formula_in_prefix(
            self.formula, self.work, self.prefix, name="namu", help_text="Git worktrees", runner=runner,
        )

    def test_default_install_pours_native_bottle_and_runs_functional_test(self):
        runner = NativeHomebrew(self.work, self.prefix)
        bottle = self.validate(runner)
        brew = str(self.prefix / "bin/brew")
        assert (brew, "install", "namu/validation/namu") in runner.calls
        assert (brew, "test", "namu/validation/namu") in runner.calls
        assert not any("--force-bottle" in call for call in runner.calls)
        assert bottle["sha256"] == hashlib.sha256(bottle["archive"].read_bytes()).hexdigest()

    def test_rejects_source_fallback_even_if_install_succeeded(self):
        runner = NativeHomebrew(self.work, self.prefix, poured=False)
        with pytest.raises(ValueError, match="did not install from a bottle"):
            self.validate(runner)
        assert not any("test" in call for call in runner.calls)

    def test_rejects_nonrelocatable_bottle(self):
        runner = NativeHomebrew(self.work, self.prefix, cellar="/opt/homebrew/Cellar")
        with pytest.raises(ValueError, match="relocatable"):
            self.validate(runner)
        assert not any(call[1:2] == ("test",) for call in runner.calls)

    def test_rejects_generated_checksum_mismatch(self):
        runner = NativeHomebrew(self.work, self.prefix, checksum="0" * 64)
        with pytest.raises(ValueError, match="checksum mismatch"):
            self.validate(runner)
        assert not any(call[1:2] == ("test",) for call in runner.calls)


class Publication:
    def __init__(self):
        self.calls = []

    def __call__(self, *args, cwd=None, env=None):
        self.calls.append(args)
        if args[1:3] == ("release", "list"):
            return "[]"
        return ""


class TestBottlePublication:
    def test_digest_mismatch_prevents_any_remote_operation(self, tmp_path):
        archive = tmp_path / "namu.bottle.tar.gz"
        archive.write_bytes(b"corrupt")
        runner = Publication()
        with pytest.raises(ValueError, match="mismatched checksum"):
            bottles.publish_bottle("namu", {**BOTTLE, "archive": archive}, "v0.1.0", "f" * 40, runner=runner)
        assert runner.calls == []

    def test_publication_does_not_change_latest_application_release(self, tmp_path):
        archive = tmp_path / "namu.bottle.tar.gz"
        archive.write_bytes(b"verified native bottle")
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        runner = Publication()
        bottles.publish_bottle("namu", {"archive": archive, "filename": archive.name, "sha256": digest},
                               "v0.1.0", "f" * 40, runner=runner)
        creates = [call for call in runner.calls if call[1:3] == ("release", "create")]
        assert len(creates) == 1
        assert "--latest=false" in creates[0]
        assert creates[0][3] == f"namu-v0.1.0-bottle-{digest}"
