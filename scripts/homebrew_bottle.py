"""Build, test, and publish native relocatable bottles for prebuilt CLIs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

TAP = "kamaal111/homebrew-tap"


def run(*args: str, cwd: Path | None = None, env: dict | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, env=env, check=False, text=True,
                            stdout=subprocess.PIPE)
    if result.returncode:
        print(result.stdout, file=sys.stderr, end="")
        raise subprocess.CalledProcessError(result.returncode, args, output=result.stdout)
    return result.stdout.strip()


def version_tuple(tag: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag):
        raise ValueError(f"Expected stable vX.Y.Z version, got {tag!r}")
    return tuple(int(part) for part in tag[1:].split("."))


def formula_version(formula: str) -> str:
    match = re.search(r'^  version "([^"]+)"$', formula, re.MULTILINE)
    if not match:
        raise ValueError("Cannot determine current formula version")
    tag = "v" + match[1]
    version_tuple(tag)
    return tag


def release_name(name: str, tag: str, digest: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
        raise ValueError("Invalid package name")
    version_tuple(tag)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Expected bottle SHA256 digest")
    return f"{name}-{tag}-bottle-{digest}"


def root_url(name: str, tag: str, digest: str) -> str:
    return f"https://github.com/{TAP}/releases/download/{release_name(name, tag, digest)}"


def bottle_metadata(formula: str) -> dict | None:
    match = re.search(
        r'^    sha256 cellar: :any_skip_relocation, ([a-z0-9_]+): "([0-9a-f]{64})"$',
        formula, re.MULTILINE,
    )
    if not match:
        return None
    return {"tag": match[1], "sha256": match[2]}


def with_bottle(formula: str, name: str, bottle: dict, url: str | None = None) -> str:
    if not re.fullmatch(r"(?:arm64_)?[a-z][a-z0-9_]*|x86_64_linux", bottle["tag"]):
        raise ValueError("Invalid native bottle tag")
    if url and any(c in url for c in ('"', "\n", "\r")):
        raise ValueError("Invalid bottle root URL")
    existing = bottle_metadata(formula)
    if existing and existing["tag"] != bottle["tag"] and not (url and url.startswith("file://")):
        raise ValueError("Refusing to replace a bottle for a different platform")
    root = root_url(name, formula_version(formula), bottle["sha256"])
    block = ("  bottle do\n"
             f'    root_url "{url or root}"\n'
             f'    sha256 cellar: :any_skip_relocation, {bottle["tag"]}: "{bottle["sha256"]}"\n'
             "  end\n\n")
    clean = re.sub(r"^  bottle do\n.*?^  end\n\n", "", formula, flags=re.MULTILINE | re.DOTALL)
    marker = re.search(r"^  (?:depends_on|uses_from_macos|on_macos|on_linux|def install)\b", clean, re.MULTILINE)
    if not marker:
        raise ValueError("Cannot find bottle insertion point")
    return clean[:marker.start()] + block + clean[marker.start():]


def validate_formula(formula: Path, work: Path, *, name: str, help_text: str,
                     runner=run) -> dict:
    cache = Path.home() / "Library/Caches"
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{name}-homebrew-", dir=cache) as directory:
        return validate_formula_in_prefix(formula, work, Path(directory), name=name,
                                          help_text=help_text, runner=runner)


def validate_formula_in_prefix(formula: Path, work: Path, prefix: Path, *,
                               name: str, help_text: str, runner=run) -> dict:
    tag = formula_version(formula.read_text())
    runner("git", "clone", "--quiet", "--depth=1", "https://github.com/Homebrew/brew.git", str(prefix))
    brew = str(prefix / "bin/brew")
    env = {**os.environ, "HOMEBREW_NO_AUTO_UPDATE": "1", "HOMEBREW_NO_ANALYTICS": "1",
           "HOMEBREW_NO_ENV_HINTS": "1", "HOMEBREW_TEMP": str(work / "brew-tmp"),
           "HOMEBREW_CACHE": str(work / "brew-cache"), "HOMEBREW_LOGS": str(work / "brew-logs"),
           "XDG_CONFIG_HOME": str(work / "config")}
    (work / "brew-tmp").mkdir()
    tap_dir = prefix / f"Library/Taps/{name}/homebrew-validation"
    (tap_dir / "Formula").mkdir(parents=True)
    target = tap_dir / f"Formula/{name}.rb"
    shutil.copyfile(formula, target)
    runner("git", "init", "--quiet", "--initial-branch=validation", str(tap_dir))
    runner("git", "-C", str(tap_dir), "add", ".")
    runner("git", "-C", str(tap_dir), "-c", "user.name=Validation",
           "-c", "user.email=validation@example.com", "commit", "--quiet", "-m", "Validate packaging")
    identifier = f"{name}/validation/{name}"
    runner("ruby", "-c", str(formula))
    runner(brew, "style", "--formula", str(target), env=env)
    runner(brew, "trust", "--formula", identifier, env=env)
    published = bottle_metadata(formula.read_text())
    if published:
        runner(brew, "fetch", "--bottle-tag=" + published["tag"], identifier, env=env)
    runner(brew, "install", "--build-bottle", identifier, env=env)
    runner(brew, "bottle", "--json", "--no-rebuild", identifier, cwd=work, env=env)
    files = list(work.glob(f"{name}--*.bottle.json"))
    if len(files) != 1:
        raise ValueError("Expected exactly one generated bottle metadata file")
    metadata = json.loads(files[0].read_text())[identifier]["bottle"]
    if metadata["cellar"] != "any_skip_relocation" or len(metadata["tags"]) != 1:
        raise ValueError("Expected one relocatable bottle without prefix references")
    bottle_tag, artifact = next(iter(metadata["tags"].items()))
    archive = work / artifact["local_filename"]
    if archive.parent != work or Path(artifact["filename"]).name != artifact["filename"]:
        raise ValueError("Bottle filenames must stay inside the output directory")
    if hashlib.sha256(archive.read_bytes()).hexdigest() != artifact["sha256"]:
        raise ValueError("Generated bottle checksum mismatch")
    runner(brew, "uninstall", identifier, env=env)
    bottle = {"tag": bottle_tag, "sha256": artifact["sha256"]}
    shutil.copyfile(archive, work / artifact["filename"])
    target.write_text(with_bottle(formula.read_text(), name, bottle, work.as_uri()))
    runner(brew, "install", identifier, env=env)
    receipt = json.loads((prefix / f"Cellar/{name}" / tag[1:] / "INSTALL_RECEIPT.json").read_text())
    if not receipt["poured_from_bottle"]:
        raise ValueError("Validation did not install from a bottle")
    runner(brew, "test", identifier, env=env)
    binary = prefix / f"bin/{name}"
    if runner(str(binary), "--version", env=env) != f"{name} version {tag[1:]}":
        raise ValueError("Installed binary version differs from formula")
    if help_text not in runner(str(binary), "--help", env=env):
        raise ValueError(f"Installed binary help differs from {name}")
    runner(brew, "uninstall", identifier, env=env)
    if binary.exists() or binary.is_symlink():
        raise ValueError("Installed binary was not removed")
    return {"tag": bottle_tag, "sha256": artifact["sha256"],
            "filename": artifact["filename"], "archive": archive}


def publish_bottle(name: str, bottle: dict, tag: str, base_sha: str, *, runner=run) -> None:
    archive = bottle["archive"]
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != bottle["sha256"]:
        raise ValueError("Refusing to publish a bottle with a mismatched checksum")
    release_tag = release_name(name, tag, digest)
    releases = json.loads(runner("gh", "release", "list", "--repo", TAP, "--limit", "1000", "--json", "tagName"))
    with tempfile.TemporaryDirectory(prefix=f"{name}-bottle-publish-") as directory:
        asset = Path(directory) / bottle["filename"]
        if any(release["tagName"] == release_tag for release in releases):
            runner("gh", "release", "download", release_tag, "--repo", TAP,
                   "--dir", directory, "--pattern", asset.name)
            if hashlib.sha256(asset.read_bytes()).hexdigest() != digest:
                raise ValueError("Existing bottle release asset has a different checksum")
            return
        shutil.copyfile(archive, asset)
        runner("gh", "release", "create", release_tag, str(asset), "--repo", TAP,
               "--target", base_sha, "--latest=false", "--title", f"{name} {tag} Homebrew bottle",
               "--notes", f"Homebrew bottle of the existing {name} release; no application version change.")
