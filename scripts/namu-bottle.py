#!/usr/bin/env python3
"""Build and verify a native Namu bottle; publish or update the formula explicitly."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile

import homebrew_bottle as bottles

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Keep the verified bottle and metadata here")
    parser.add_argument("--publish", action="store_true", help="Publish the verified immutable bottle asset")
    parser.add_argument("--target-sha", help="Existing tap commit to associate with a published bottle")
    parser.add_argument("--write", action="store_true", help="Write the verified bottle block into Formula/namu.rb")
    args = parser.parse_args()
    if args.publish and not args.target_sha:
        parser.error("--publish requires --target-sha")
    if (args.publish or args.write) and not args.output_dir:
        parser.error("--publish and --write require --output-dir")
    if args.publish and not re.fullmatch(r"[0-9a-f]{40}", args.target_sha):
        parser.error("--target-sha must be a full existing commit SHA")
    try:
        if platform.system() != "Darwin":
            raise ValueError("Build native macOS bottles on a Mac; Linux source installation remains supported")
        for tool in ("git", "brew", "ruby"):
            if not shutil.which(tool):
                raise ValueError(f"Missing prerequisite: {tool}")
        if args.publish and not shutil.which("gh"):
            raise ValueError("Missing prerequisite: gh")
        formula = ROOT / "Formula/namu.rb"
        with tempfile.TemporaryDirectory(prefix="namu-bottle-") as temporary:
            work = args.output_dir.resolve() if args.output_dir else Path(temporary)
            work.mkdir(parents=True, exist_ok=True)
            if list(work.glob("namu--*.bottle.json")):
                raise ValueError("Use an output directory without a previous bottle build")
            bottle = bottles.validate_formula(formula, work, name="namu", help_text="Git worktrees")
            if args.output_dir:
                candidate = bottles.with_bottle(formula.read_text(), "namu", bottle)
                (work / "namu.rb").write_text(candidate)
                (work / "bottle.json").write_text(json.dumps(bottle, default=str, indent=2) + "\n")
                if args.publish:
                    bottles.publish_bottle("namu", bottle, bottles.formula_version(candidate), args.target_sha)
                if args.write:
                    formula.write_text(candidate)
            print(f"Verified native bottle {bottle['tag']} ({bottle['sha256']})")
        return 0
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Namu bottle validation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
