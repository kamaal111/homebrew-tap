"""Shared release verification and protected single-commit tap updates."""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import platform
import shutil
import subprocess
import sys
import tempfile

import homebrew_bottle as bottles
from homebrew_bottle import TAP, formula_version, version_tuple, run


def validate_release(release: dict, requested: str | None, name: str,
                     targets: tuple[str, ...]) -> str:
    tag = release["tagName"]
    version_tuple(tag)
    if release["isDraft"] or release["isPrerelease"]:
        raise ValueError("Draft and prerelease releases are not supported")
    if requested and requested != tag:
        raise ValueError("Resolved release does not match requested tag")
    expected = {f"{name}_{tag[1:]}_{target}.tar.gz" for target in targets} | {"checksums.txt"}
    names = [asset["name"] for asset in release["assets"]]
    if any(names.count(asset) != 1 for asset in expected):
        raise ValueError("Release must have exactly one of each required archive and checksums.txt")
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


def ensure_upgrade(current: str | None, target: str) -> None:
    if current and version_tuple(target) < version_tuple(current):
        raise ValueError(f"Refusing downgrade from {current} to {target}")


def commit_identity(root: Path, *, runner) -> dict[str, str]:
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return {"name": "github-actions[bot]", "email": "41898282+github-actions[bot]@users.noreply.github.com"}
    return {key: runner("git", "config", "--get", f"user.{key}", cwd=root) for key in ("name", "email")}


def clone_tap(work: Path, *, runner) -> tuple[Path, str, str]:
    repo = work / "tap"
    runner("gh", "repo", "clone", TAP, str(repo))
    base = json.loads(runner("gh", "repo", "view", TAP, "--json", "defaultBranchRef"))["defaultBranchRef"]["name"]
    base_sha = runner("git", "rev-parse", f"origin/{base}", cwd=repo)
    runner("git", "checkout", "--quiet", "--detach", base_sha, cwd=repo)
    return repo, base, base_sha


@dataclass(frozen=True)
class BranchState:
    base: str
    base_sha: str
    previous_sha: str
    prs: tuple[dict, ...]


def inspect_branch(repo: Path, base: str, base_sha: str, branch: str,
                   formula_file: str, tag: str, validate_owned, *, runner) -> BranchState:
    prs = json.loads(runner("gh", "pr", "list", "--repo", TAP, "--head", branch, "--state", "open",
                            "--json", "number,headRefOid,baseRefName,url"))
    if len(prs) > 1:
        raise ValueError("Multiple update PRs found")
    remote = runner("git", "ls-remote", "origin", f"refs/heads/{branch}", cwd=repo)
    previous_sha = remote.split()[0] if remote else ""
    if prs and (prs[0]["headRefOid"] != previous_sha or prs[0]["baseRefName"] != base):
        raise ValueError("Update PR branch/base changed unexpectedly")
    if previous_sha:
        runner("git", "fetch", "--quiet", "origin", branch, cwd=repo)
        merged = runner("git", "merge-base", base_sha, previous_sha, cwd=repo) == previous_sha
        if not merged:
            parent = runner("git", "rev-parse", previous_sha + "^", cwd=repo)
            validate_owned(
                runner("git", "log", "-1", "--format=%B", previous_sha, cwd=repo),
                set(runner("git", "diff", "--name-only", parent, previous_sha, cwd=repo).splitlines()),
                int(runner("git", "rev-list", "--count", f"{base_sha}..{previous_sha}", cwd=repo)),
                runner("git", "show", f"{previous_sha}:{formula_file}", cwd=repo) + "\n",
                runner("git", "show", f"{parent}:README.md", cwd=repo) + "\n",
                runner("git", "show", f"{previous_sha}:README.md", cwd=repo) + "\n")
            old = runner("git", "show", f"{previous_sha}:{formula_file}", cwd=repo)
            ensure_upgrade(formula_version(old), tag)
    return BranchState(base, base_sha, previous_sha, tuple(prs))


def require_current_base(repo: Path, state: BranchState, *, runner) -> None:
    runner("git", "fetch", "--quiet", "origin", state.base, cwd=repo)
    if runner("git", "rev-parse", f"origin/{state.base}", cwd=repo) != state.base_sha:
        raise ValueError("Tap base changed during validation; rerun the updater")


def publish_update(repo: Path, work: Path, branch: str, marker: str, identity: dict,
                   paths: tuple[str, ...], title: str, body: str, state: BranchState, *, runner) -> str:
    runner("git", "checkout", "--quiet", "-b", branch, cwd=repo)
    for key, value in identity.items():
        runner("git", "config", f"user.{key}", value, cwd=repo)
    message = work / "commit.txt"
    message.write_text(f"{title}\n\n{body}\n\n{marker}\n")
    runner("git", "add", "--", *paths, cwd=repo)
    runner("git", "commit", "--quiet", "-F", str(message), cwd=repo)
    require_current_base(repo, state, runner=runner)
    runner("git", "push", f"--force-with-lease=refs/heads/{branch}:{state.previous_sha}",
           "origin", f"HEAD:refs/heads/{branch}", cwd=repo)
    body_path = work / "pr.md"
    body_path.write_text(body + "\n\n" + marker + "\n")
    if state.prs:
        runner("gh", "pr", "edit", str(state.prs[0]["number"]), "--repo", TAP,
               "--title", title, "--body-file", str(body_path))
        return state.prs[0]["url"]
    return runner("gh", "pr", "create", "--repo", TAP, "--base", state.base, "--head", branch,
                  "--title", title, "--body-file", str(body_path))


ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Package:
    name: str
    targets: tuple[str, ...]
    help_text: str

    @property
    def source(self) -> str:
        return f"kamaal111/{self.name}"

    @property
    def branch(self) -> str:
        return f"update-{self.name}"

    @property
    def marker(self) -> str:
        return f"{self.name.title()}-Updater: v1"

    @property
    def formula_file(self) -> str:
        return f"Formula/{self.name}.rb"


PACKAGES = {
    "namu": Package("namu", ("darwin_arm64", "darwin_amd64", "linux_arm64", "linux_amd64"), "Git worktrees"),
    "agent-vm": Package("agent-vm", ("darwin_arm64",), "Persistent development VMs"),
}


def render_formula(package: Package, template: str, tag: str, digests: dict[str, str],
                   bottle: dict | None = None) -> str:
    version_tuple(tag)
    if set(digests) != set(package.targets) or any(not re.fullmatch(r"[0-9a-f]{64}", d) for d in digests.values()):
        raise ValueError("Expected verified SHA256 values for every release target")
    formula = template.replace("@VERSION@", tag[1:])
    for target, digest in digests.items():
        formula = formula.replace(f"@SHA_{target.upper()}@", digest)
    if re.search(r"@[A-Z_]+@", formula):
        raise ValueError("Unresolved formula placeholder")
    if bottle and not re.fullmatch(r"arm64_[a-z_]+", bottle["tag"]):
        raise ValueError("Expected Apple Silicon macOS bottle tag")
    return bottles.with_bottle(formula, package.name, bottle) if bottle else formula


def formula_digests(package: Package, formula: str) -> dict[str, str]:
    pattern = (rf'/{re.escape(package.name)}_[0-9.]+_([a-z0-9_]+)\.tar\.gz"\n'
               r'(?:  version "[^"]+"\n)?[ \t]+sha256 "([0-9a-f]{64})"')
    matches = re.findall(pattern, formula)
    if len(matches) != len(package.targets) or {target for target, _ in matches} != set(package.targets):
        raise ValueError("Formula has unexpected release archive entries")
    return dict(matches)


def readme_with_install(package: Package, readme: str, root: Path) -> str:
    path = root / f"packaging/homebrew/{package.name}.md"
    if not path.exists():
        return readme
    section = path.read_text().strip()
    begin, end = f"<!-- {package.name}:start -->", f"<!-- {package.name}:end -->"
    if begin in readme or end in readme:
        if readme.count(begin) != 1 or readme.count(end) != 1 or readme.index(end) < readme.index(begin):
            raise ValueError("Invalid managed README section")
        return readme[:readme.index(begin)] + section + readme[readme.index(end) + len(end):]
    return readme.rstrip() + "\n\n" + section + "\n"


def validate_owned_change(package: Package, message: str, paths: set[str], count: int,
                          formula: str, parent_readme: str, readme: str, *, root: Path) -> None:
    allowed = {package.formula_file}
    if (root / f"packaging/homebrew/{package.name}.md").exists():
        allowed.add("README.md")
    if (package.marker.casefold() not in {line.casefold() for line in message.splitlines()}
            or count != 1 or not paths or not paths <= allowed):
        raise ValueError(f"Unexpected manual changes on {package.branch}; refusing overwrite")
    template = (root / f"packaging/homebrew/{package.name}.rb.in").read_text()
    expected = render_formula(package, template, formula_version(formula), formula_digests(package, formula),
                              bottles.bottle_metadata(formula))
    if formula != expected or readme != readme_with_install(package, parent_readme, root):
        raise ValueError("Formula or README has unexpected manual edits")


def require_host(*, publishing: bool) -> None:
    if (platform.system(), platform.machine()) != ("Darwin", "arm64"):
        raise ValueError("Formula validation requires Apple Silicon macOS")
    tools = ("git", "brew", "ruby", "gh") if publishing else ("git", "brew", "ruby")
    for tool in tools:
        if not shutil.which(tool):
            raise ValueError(f"Missing prerequisite: {tool}")


def prepare_release(package: Package, requested: str | None, work: Path, *, runner) -> tuple[str, dict[str, str]]:
    args = ["gh", "release", "view"] + ([requested] if requested else [])
    release = json.loads(runner(*args, "--repo", package.source, "--json", "tagName,isDraft,isPrerelease,assets"))
    tag = validate_release(release, requested, package.name, package.targets)
    assets = work / "assets"
    assets.mkdir()
    patterns = [part for name in ("checksums.txt", *(f"{package.name}_{tag[1:]}_{t}.tar.gz" for t in package.targets))
                for part in ("--pattern", name)]
    runner("gh", "release", "download", tag, "--repo", package.source, "--dir", str(assets), *patterns)
    checksums = (assets / "checksums.txt").read_text()
    return tag, {target: verify_checksum(checksums, assets / f"{package.name}_{tag[1:]}_{target}.tar.gz")
                 for target in package.targets}


def update_package(package: Package, requested: str | None = None, *, dry_run: bool = False,
                   output_dir: Path | None = None, root: Path = ROOT, runner=run) -> None:
    if requested:
        version_tuple(requested)
    require_host(publishing=True)
    runner("gh", "auth", "status")
    template = (root / f"packaging/homebrew/{package.name}.rb.in").read_text()
    if output_dir and output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Use an empty output directory")
    with tempfile.TemporaryDirectory(prefix=f"{package.name}-tap-") as temporary:
        work = output_dir.resolve() if output_dir else Path(temporary)
        work.mkdir(parents=True, exist_ok=True)
        tag, digests = prepare_release(package, requested, work, runner=runner)
        repo, base, base_sha = clone_tap(work, runner=runner)
        path = repo / package.formula_file
        current = path.read_text() if path.exists() else None
        ensure_upgrade(formula_version(current) if current else None, tag)
        state = inspect_branch(
            repo, base, base_sha, package.branch, package.formula_file, tag,
            lambda *args: validate_owned_change(package, *args, root=root), runner=runner)
        readme_path = repo / "README.md"
        original_readme = readme_path.read_text()
        readme = readme_with_install(package, original_readme, root)
        if (not dry_run and current and bottles.bottle_metadata(current) and not state.prs
                and current == render_formula(package, template, tag, digests, bottles.bottle_metadata(current))
                and readme == readme_path.read_text()):
            print(f"{tag} is already installed in the tap; no changes needed.")
            return
        path.parent.mkdir(exist_ok=True)
        path.write_text(render_formula(package, template, tag, digests))
        readme_path.write_text(readme)
        print(f"Validating {package.name} {tag} in an isolated Homebrew prefix…", flush=True)
        bottle = bottles.validate_formula(path, work, name=package.name, help_text=package.help_text, runner=runner)
        formula = render_formula(package, template, tag, digests, bottle)
        path.write_text(formula)
        title = f"chore: update {package.name} to {tag[1:]}" if current else f"feat: add {package.name} {tag[1:]}"
        body = (f"**Summary**\nInstall the verified {package.name} release through Homebrew.\n\n"
                f"**Changes**\nUse {tag} archives with verified SHA256 values for every supported target.\n"
                "Publish a verified relocatable macOS bottle.\n\n"
                "Validation: archive checksums, formula style, isolated bottle\n"
                "installation, functional test, version/help, and uninstallation.\n\n"
                f"Release: https://github.com/{package.source}/releases/tag/{tag}")
        report = {"package": package.name, "version": tag, "base": base_sha, "branch": package.branch,
                  "title": title, "body": body, "digests": digests,
                  "bottle": {key: str(value) for key, value in bottle.items()}, "dry_run": dry_run,
                  "validation": ["checksums", "style", "bottle_install", "brew_test", "version", "help", "uninstall"]}
        (work / f"{package.name}.rb").write_text(formula)
        (work / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        if dry_run:
            print(f"Dry run passed for {package.name} {tag}; no remote writes. Report: {work / 'report.json'}")
            return
        identity = commit_identity(root, runner=runner)
        require_current_base(repo, state, runner=runner)
        bottles.publish_bottle(package.name, bottle, tag, base_sha, runner=runner)
        paths = (package.formula_file, "README.md") if readme != original_readme else (package.formula_file,)
        url = publish_update(repo, work, package.branch, package.marker, identity, paths,
                             title, body, state, runner=runner)
        print(url)
        runner("gh", "workflow", "run", f"validate-{package.name}.yml", "--repo", TAP, "--ref", package.branch)


def main(default_package: str | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a release and propose a protected Homebrew update")
    if default_package is None:
        parser.add_argument("package", choices=PACKAGES)
    parser.add_argument("--version", help="Stable vX.Y.Z release; empty or omitted: latest stable")
    parser.add_argument("--dry-run", action="store_true", help="Verify and prepare without remote writes")
    parser.add_argument("--output-dir", type=Path, help="Empty directory for rehearsal artifacts and report")
    parser.add_argument("--validate-only", action="store_true", help="Validate the checked-in formula without GitHub")
    args = parser.parse_args()
    if args.dry_run and not args.output_dir:
        parser.error("--dry-run requires --output-dir")
    if args.validate_only and (args.version is not None or args.dry_run or args.output_dir):
        parser.error("--validate-only cannot be combined with update options")
    package = PACKAGES[default_package or args.package]
    try:
        if args.validate_only:
            require_host(publishing=False)
            with tempfile.TemporaryDirectory(prefix=f"{package.name}-validation-") as temporary:
                bottles.validate_formula(ROOT / package.formula_file, Path(temporary), name=package.name,
                                         help_text=package.help_text, runner=run)
        else:
            update_package(package, args.version or None, dry_run=args.dry_run, output_dir=args.output_dir)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(f"{package.name} tap update failed: {error}", file=sys.stderr)
        return 1
    return 0
