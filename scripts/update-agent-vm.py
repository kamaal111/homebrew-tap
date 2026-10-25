#!/usr/bin/env python3
"""Validate a stable agent-vm release and open a formula PR in this tap."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

SOURCE = "kamaal111/agent-vm"
TAP = "kamaal111/homebrew-tap"
BRANCH = "update-agent-vm"
MARKER = "Agent-VM-Updater: v1"
BEGIN = "<!-- agent-vm:start -->"
END = "<!-- agent-vm:end -->"
SCRIPT_ROOT = Path(__file__).resolve().parent.parent


def run(*args: str, cwd: Path | None = None, env: dict | None = None) -> str:
    result = subprocess.run(args, cwd=cwd, env=env, check=False, text=True,
                            stdout=subprocess.PIPE)
    if result.returncode:
        print(result.stdout, file=sys.stderr, end="")
        raise subprocess.CalledProcessError(result.returncode, args, output=result.stdout)
    return result.stdout.strip()


def gh_json(*args: str, cwd: Path | None = None):
    return json.loads(run("gh", *args, cwd=cwd))


def version_tuple(tag: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", tag):
        raise ValueError(f"Expected stable vX.Y.Z version, got {tag!r}")
    return tuple(int(part) for part in tag[1:].split("."))


def validate_release(release: dict, requested: str | None) -> str:
    tag = release["tagName"]
    version_tuple(tag)
    if release["isDraft"] or release["isPrerelease"]:
        raise ValueError("Draft and prerelease releases are not supported")
    if requested and requested != tag:
        raise ValueError("Resolved release does not match requested tag")
    expected = {f"agent-vm_{tag[1:]}_darwin_arm64.tar.gz", "checksums.txt"}
    names = [asset["name"] for asset in release["assets"]]
    if any(names.count(name) != 1 for name in expected):
        raise ValueError("Release must have exactly one archive and checksums.txt")
    return tag


def verify_checksum(checksums: str, archive: Path) -> str:
    matches = []
    for line in checksums.splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64}) [ *](.+)", line)
        if match and match[2] == archive.name:
            matches.append(match[1].lower())
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if matches != [digest]:
        raise ValueError("Missing, duplicate, or mismatched archive checksum")
    return digest


def render_formula(template: str, tag: str, digest: str, bottle: dict | None = None) -> str:
    version_tuple(tag)
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Expected SHA256 digest")
    block = ""
    if bottle:
        if not re.fullmatch(r"arm64_[a-z_]+", bottle["tag"]):
            raise ValueError("Expected Apple Silicon macOS bottle tag")
        if not re.fullmatch(r"[0-9a-f]{64}", bottle["sha256"]):
            raise ValueError("Expected bottle SHA256 digest")
        block = ("  bottle do\n"
                 f'    root_url "{bottle_root(tag, bottle["sha256"])}"\n'
                 f'    sha256 cellar: :any_skip_relocation, {bottle["tag"]}: "{bottle["sha256"]}"\n'
                 "  end\n\n")
    return template.replace("@VERSION@", tag[1:]).replace("@SHA256@", digest).replace("@BOTTLE@", block)


def bottle_release(tag: str, digest: str) -> str:
    return f"agent-vm-{tag}-bottle-{digest}"


def bottle_root(tag: str, digest: str) -> str:
    return f"https://github.com/{TAP}/releases/download/{bottle_release(tag, digest)}"


def formula_bottle(formula: str) -> dict | None:
    match = re.search(
        r'^    sha256 cellar: :any_skip_relocation, (arm64_[a-z_]+): "([0-9a-f]{64})"$',
        formula, re.MULTILINE,
    )
    if not match:
        return None
    return {"tag": match[1], "sha256": match[2]}


def formula_version(formula: str) -> str:
    match = re.search(r'^  version "([^"]+)"$', formula, re.MULTILINE)
    if not match:
        raise ValueError("Cannot determine current formula version")
    tag = "v" + match[1]
    version_tuple(tag)
    return tag


def readme_with_install(readme: str) -> str:
    section = f"""{BEGIN}
## agent-vm

Install on Apple Silicon macOS:

```sh
brew install kamaal111/tap/agent-vm
```

Homebrew selects a prebuilt bottle matching the host macOS, or an older
compatible bottle. When no compatible bottle is available, installation uses
the release archive and requires compatible Command Line Tools.

Run `agent-vm config init` and `agent-vm doctor` after installation.
Tart, guest images and credentials are configured separately.
{END}"""
    if BEGIN in readme or END in readme:
        if readme.count(BEGIN) != 1 or readme.count(END) != 1:
            raise ValueError("Invalid managed agent-vm README section")
        start, end = readme.index(BEGIN), readme.index(END) + len(END)
        if end < start:
            raise ValueError("Invalid managed README section order")
        return readme[:start] + section + readme[end:]
    return readme.rstrip() + "\n\n" + section + "\n"


def ensure_upgrade(current: str | None, target: str) -> None:
    if current and version_tuple(target) < version_tuple(current):
        raise ValueError(f"Refusing downgrade from {current} to {target}")


def validate_owned_change(message: str, paths: set[str], count: int,
                          formula: str, template: str, parent_readme: str,
                          readme: str) -> None:
    if MARKER not in message.splitlines() or count != 1:
        raise ValueError("Unexpected manual commits on update-agent-vm; refusing overwrite")
    if not paths or not paths <= {"Formula/agent-vm.rb", "README.md"}:
        raise ValueError("Unexpected changed files on update-agent-vm")
    checksum = re.search(r'^  sha256 "([0-9a-f]{64})"$', formula, re.MULTILINE)
    if not checksum or formula != render_formula(template, formula_version(formula), checksum[1], formula_bottle(formula)):
        raise ValueError("Formula has unexpected manual edits")
    if readme != readme_with_install(parent_readme):
        raise ValueError("README has unexpected manual edits")


def validate_formula(formula: Path, work: Path) -> dict:
    # Homebrew permits build writes throughout system temp, so its executable
    # must live outside that tree for its own sandbox inheritance checks.
    cache = Path.home() / "Library/Caches"
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agent-vm-homebrew-", dir=cache) as directory:
        return validate_formula_in_prefix(formula, work, Path(directory))


def validate_formula_in_prefix(formula: Path, work: Path, prefix: Path) -> dict:
    run("git", "clone", "--quiet", "--depth=1", "https://github.com/Homebrew/brew.git", str(prefix))
    brew = str(prefix / "bin/brew")
    env = {**os.environ, "HOMEBREW_NO_AUTO_UPDATE": "1", "HOMEBREW_NO_ANALYTICS": "1",
           "HOMEBREW_NO_ENV_HINTS": "1",
           "HOMEBREW_TEMP": str(work / "brew-tmp"),
           "HOMEBREW_CACHE": str(work / "brew-cache"),
           "XDG_CONFIG_HOME": str(work / "config")}
    (work / "brew-tmp").mkdir()
    tap_dir = prefix / "Library/Taps/agent-vm/homebrew-validation"
    (tap_dir / "Formula").mkdir(parents=True)
    shutil.copyfile(formula, tap_dir / "Formula/agent-vm.rb")
    run("git", "init", "--quiet", str(tap_dir))
    run("git", "-C", str(tap_dir), "add", ".")
    run("git", "-C", str(tap_dir), "-c", "user.name=Validation",
        "-c", "user.email=validation@example.com", "commit", "--quiet", "-m", "Validate packaging")
    run("ruby", "-c", str(formula))
    run(brew, "style", "--formula", str(tap_dir / "Formula/agent-vm.rb"), env=env)
    run(brew, "trust", "--formula", "agent-vm/validation/agent-vm", env=env)
    published = formula_bottle(formula.read_text())
    if published:
        run(brew, "fetch", "--bottle-tag=" + published["tag"],
            "agent-vm/validation/agent-vm", env=env)
    run(brew, "install", "--build-bottle", "agent-vm/validation/agent-vm", env=env)
    run(brew, "bottle", "--json", "--no-rebuild", "agent-vm/validation/agent-vm", cwd=work, env=env)
    metadata_files = list(work.glob("agent-vm--*.bottle.json"))
    if len(metadata_files) != 1:
        raise ValueError("Expected exactly one generated bottle metadata file")
    metadata = json.loads(metadata_files[0].read_text())["agent-vm/validation/agent-vm"]["bottle"]
    if metadata["cellar"] != "any_skip_relocation" or len(metadata["tags"]) != 1:
        raise ValueError("Expected one relocatable bottle without prefix references")
    bottle_tag, artifact = next(iter(metadata["tags"].items()))
    archive = work / artifact["local_filename"]
    if hashlib.sha256(archive.read_bytes()).hexdigest() != artifact["sha256"]:
        raise ValueError("Generated bottle checksum mismatch")
    run(brew, "uninstall", "agent-vm/validation/agent-vm", env=env)
    local_template = re.sub(r"  bottle do\n.*?  end\n\n", "", formula.read_text(), flags=re.DOTALL)
    local_template = local_template.replace("  depends_on arch:", "@BOTTLE@  depends_on arch:")
    source_digest = re.search(r'^  sha256 "([0-9a-f]{64})"$', formula.read_text(), re.MULTILINE)[1]
    bottle = {"tag": bottle_tag, "sha256": artifact["sha256"]}
    local_formula = render_formula(local_template, formula_version(formula.read_text()), source_digest, bottle)
    local_formula = local_formula.replace(
        bottle_root(formula_version(formula.read_text()), artifact["sha256"]), work.as_uri(),
    )
    shutil.copyfile(archive, work / artifact["filename"])
    (tap_dir / "Formula/agent-vm.rb").write_text(local_formula)
    run(brew, "install", "--force-bottle", "agent-vm/validation/agent-vm", env=env)
    receipt = json.loads((prefix / "Cellar/agent-vm" / formula_version(formula.read_text())[1:]
                          / "INSTALL_RECEIPT.json").read_text())
    if not receipt["poured_from_bottle"]:
        raise ValueError("Validation did not install from a bottle")
    run(brew, "test", "agent-vm/validation/agent-vm", env=env)
    binary = prefix / "bin/agent-vm"
    expected = "agent-vm version " + formula_version(formula.read_text())[1:]
    if run(str(binary), "--version", env=env) != expected:
        raise ValueError("Installed binary version differs from formula")
    if "Persistent development VMs" not in run(str(binary), "--help", env=env):
        raise ValueError("Installed binary help differs from agent-vm")
    run(brew, "uninstall", "agent-vm/validation/agent-vm", env=env)
    if binary.exists() or binary.is_symlink():
        raise ValueError("Installed binary was not removed")
    return {"tag": bottle_tag, "sha256": artifact["sha256"],
            "filename": artifact["filename"], "archive": archive}


def publish_bottle(bottle: dict, tag: str, base_sha: str) -> None:
    archive = bottle["archive"]
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    if digest != bottle["sha256"]:
        raise ValueError("Refusing to publish a bottle with a mismatched checksum")
    release_tag = bottle_release(tag, digest)
    releases = gh_json("release", "list", "--repo", TAP, "--limit", "1000", "--json", "tagName")
    with tempfile.TemporaryDirectory(prefix="agent-vm-bottle-publish-") as directory:
        asset = Path(directory) / bottle["filename"]
        if any(release["tagName"] == release_tag for release in releases):
            run("gh", "release", "download", release_tag, "--repo", TAP,
                "--dir", directory, "--pattern", asset.name)
            if hashlib.sha256(asset.read_bytes()).hexdigest() != digest:
                raise ValueError("Existing bottle release asset has a different checksum")
            return
        shutil.copyfile(archive, asset)
        run("gh", "release", "create", release_tag, str(asset), "--repo", TAP,
            "--target", base_sha, "--latest=false", "--title", f"agent-vm {tag} Homebrew bottle",
            "--notes", "Homebrew bottle of the existing agent-vm release; no application version change.")


def require_validation_host() -> None:
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("Formula validation requires Apple Silicon macOS")
    for tool in ("git", "brew", "ruby"):
        if not shutil.which(tool):
            raise ValueError(f"Missing prerequisite: {tool}")


def update(requested: str | None) -> None:
    if requested:
        version_tuple(requested)
    require_validation_host()
    if not shutil.which("gh"):
        raise ValueError("Missing prerequisite: gh")
    run("gh", "auth", "status")
    identity = {"name": "github-actions[bot]", "email": "41898282+github-actions[bot]@users.noreply.github.com"}
    if os.environ.get("GITHUB_ACTIONS") != "true":
        identity = {key: run("git", "config", "--get", f"user.{key}", cwd=SCRIPT_ROOT)
                    for key in ("name", "email")}
    args = ["release", "view"] + ([requested] if requested else [])
    release = gh_json(*args, "--repo", SOURCE, "--json", "tagName,isDraft,isPrerelease,assets")
    tag = validate_release(release, requested)
    template = (SCRIPT_ROOT / "packaging/homebrew/agent-vm.rb.in").read_text()
    with tempfile.TemporaryDirectory(prefix="agent-vm-tap-") as directory:
        work = Path(directory)
        assets = work / "assets"
        assets.mkdir()
        archive = assets / f"agent-vm_{tag[1:]}_darwin_arm64.tar.gz"
        run("gh", "release", "download", tag, "--repo", SOURCE, "--dir", str(assets),
            "--pattern", archive.name, "--pattern", "checksums.txt")
        digest = verify_checksum((assets / "checksums.txt").read_text(), archive)
        formula = render_formula(template, tag, digest)
        repo = work / "tap"
        # gh handles the user's configured authentication for pushes as well.
        run("gh", "repo", "clone", TAP, str(repo))
        base = gh_json("repo", "view", TAP, "--json", "defaultBranchRef")["defaultBranchRef"]["name"]
        base_sha = run("git", "rev-parse", f"origin/{base}", cwd=repo)
        run("git", "checkout", "--quiet", "--detach", base_sha, cwd=repo)
        formula_path = repo / "Formula/agent-vm.rb"
        current = formula_path.read_text() if formula_path.exists() else None
        ensure_upgrade(formula_version(current) if current else None, tag)
        prs = gh_json("pr", "list", "--repo", TAP, "--head", BRANCH, "--state", "open",
                      "--json", "number,headRefOid,baseRefName,url")
        if len(prs) > 1:
            raise ValueError("Multiple update PRs found")
        remote_branch = run("git", "ls-remote", "origin", f"refs/heads/{BRANCH}", cwd=repo)
        previous_sha = remote_branch.split()[0] if remote_branch else ""
        if prs and (prs[0]["headRefOid"] != previous_sha or prs[0]["baseRefName"] != base):
            raise ValueError("Update PR branch/base changed unexpectedly")
        if (formula_bottle(current or "") and
                current == render_formula(template, tag, digest, formula_bottle(current)) and not prs):
            print(f"{tag} is already installed in the tap; no changes needed.")
            return
        if previous_sha:
            run("git", "fetch", "--quiet", "origin", BRANCH, cwd=repo)
            merged = run("git", "merge-base", base_sha, previous_sha, cwd=repo) == previous_sha
            if not merged:
                parent = run("git", "rev-parse", previous_sha + "^", cwd=repo)
                validate_owned_change(
                    run("git", "log", "-1", "--format=%B", previous_sha, cwd=repo),
                    set(run("git", "diff", "--name-only", parent, previous_sha, cwd=repo).splitlines()),
                    int(run("git", "rev-list", "--count", f"{base_sha}..{previous_sha}", cwd=repo)),
                    run("git", "show", f"{previous_sha}:Formula/agent-vm.rb", cwd=repo) + "\n",
                    template, run("git", "show", f"{parent}:README.md", cwd=repo) + "\n",
                    run("git", "show", f"{previous_sha}:README.md", cwd=repo) + "\n")
                old = run("git", "show", f"{previous_sha}:Formula/agent-vm.rb", cwd=repo)
                ensure_upgrade(formula_version(old), tag)
        formula_path.parent.mkdir(exist_ok=True)
        formula_path.write_text(formula)
        readme_path = repo / "README.md"
        readme_path.write_text(readme_with_install(readme_path.read_text()))
        print(f"Validating {tag} in an isolated Homebrew prefix…", flush=True)
        bottle = validate_formula(formula_path, work)
        formula = render_formula(template, tag, digest, bottle)
        formula_path.write_text(formula)
        publish_bottle(bottle, tag, base_sha)
        if not run("git", "diff", "--name-only", cwd=repo) and current == formula:
            print("No changes needed.")
            return
        title = f"chore: update agent-vm to {tag[1:]}" if current else f"feat: add agent-vm {tag[1:]}"
        body = ("**Summary**\nInstall the verified Apple Silicon agent-vm release through Homebrew.\n\n"
                f"**Changes**\nUse the {tag} macOS ARM64 archive and its verified SHA256.\n"
                "Restrict installation to Apple Silicon macOS; keep Tart setup separate.\n\n"
                f"Release: https://github.com/{SOURCE}/releases/tag/{tag}\n\n"
                "Publish a relocatable Homebrew bottle to avoid client build checks.\n\n"
                "Validation: SHA256, formula style, isolated bottle install, brew test,\n"
                "help and version.")
        run("git", "checkout", "--quiet", "-b", BRANCH, cwd=repo)
        for key, value in identity.items():
            run("git", "config", f"user.{key}", value, cwd=repo)
        message = work / "commit.txt"
        message.write_text(f"{title}\n\n{body}\n\n{MARKER}\n")
        run("git", "add", "--", "Formula/agent-vm.rb", "README.md", cwd=repo)
        run("git", "commit", "--quiet", "-F", str(message), cwd=repo)
        # Refuse to publish against a base that changed during validation.
        run("git", "fetch", "--quiet", "origin", base, cwd=repo)
        if run("git", "rev-parse", f"origin/{base}", cwd=repo) != base_sha:
            raise ValueError("Tap base changed during validation; rerun the updater")
        run("git", "push", f"--force-with-lease=refs/heads/{BRANCH}:{previous_sha}",
            "origin", f"HEAD:refs/heads/{BRANCH}", cwd=repo)
        body_path = work / "pr.md"
        body_path.write_text(body + "\n\n" + MARKER + "\n")
        if prs:
            run("gh", "pr", "edit", str(prs[0]["number"]), "--repo", TAP,
                "--title", title, "--body-file", str(body_path))
            print(prs[0]["url"])
        else:
            print(run("gh", "pr", "create", "--repo", TAP, "--base", base, "--head", BRANCH,
                      "--title", title, "--body-file", str(body_path)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--version", help="Stable tag such as v0.1.0; default: latest stable release")
    mode.add_argument("--validate-only", action="store_true",
                      help="Validate the checked-in formula and bottle without publishing")
    args = parser.parse_args()
    try:
        if args.validate_only:
            require_validation_host()
            with tempfile.TemporaryDirectory(prefix="agent-vm-validation-") as directory:
                validate_formula(SCRIPT_ROOT / "Formula/agent-vm.rb", Path(directory))
        else:
            update(args.version)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(f"agent-vm tap update failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
