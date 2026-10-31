# Contributing

This repository packages Python software for Homebrew. The maintainer environment
uses **Python 3.15** and [uv](https://docs.astral.sh/uv/); it is separate from the
Python environment created by Homebrew when users install a formula.

## Repository layout

| Path | Purpose |
| --- | --- |
| `Formula/open_api_maker.rb` | Package source, checksum, resources, installation, and Homebrew test |
| `pyproject.toml` | Maintainer dependency declarations and Python requirement |
| `uv.lock` | Resolved maintainer dependency versions and artifact hashes |
| `mise.toml` | Pinned uv, just, and actionlint toolchain |
| `.python-version` | Python version selected by uv |
| `justfile` | Setup, formula generation, and local installation recipes |

## Set up

Install [mise](https://mise.jdx.dev/getting-started.html), Homebrew, Git, and zsh.
Clone the tap and install the pinned tools:

```sh
git clone https://github.com/kamaal111/homebrew-tap.git
cd homebrew-tap
mise trust
mise install
mise exec -- just init-venv
mise exec -- just check
```

`mise.toml` pins uv 0.13.5, just 1.59.0, and actionlint 1.7.12. CI installs
these tools from the same config using mise 2026.10.24. uv selects Python 3.15
from `.python-version` and downloads a compatible interpreter when needed.
Python is managed by uv, not mise.

`just check` runs workflow syntax/expression validation with actionlint, then the
locked Python test suite. Recipes invoke tools through mise, so they also work
without interactive shell activation when just is already on your `PATH`.
Use `mise exec --` for direct uv commands, for example:

```sh
mise exec -- uv run --locked python --version
mise exec -- uv run --locked poet --help
```

The environment is created by `uv sync --locked`; do not edit `uv.lock` by hand.
Formula installation and native bottle validation still require Homebrew and
compatible developer tools from the system. Mise does not install or alter CLT.

## Commands

Run recipes from the repository root:

| Command | Effect |
| --- | --- |
| `just` or `just --list` | List available recipes |
| `just check` | Run actionlint and the locked test suite |
| `just lint` | Validate Actions syntax and expressions |
| `just test` | Run the locked Python test suite |
| `just test-run PATTERN PACKAGE` | Run matching locked Python tests in a file or directory (default: `scripts`) |
| `just validate-namu` | Validate the checked-in Namu formula and native bottle in isolation |
| `just rehearse-namu VERSION OUTPUT` | Rehearse a release update without publishing; use an empty output directory |
| `just init-venv` | Synchronize the uv environment using the existing lockfile |
| `just formulate` | Regenerate `Formula/open_api_maker.rb` using the locked environment |
| `just test-install` | Install the local formula from source with verbose output and Homebrew debugging enabled |

`uv run --locked` checks the lockfile and synchronizes the environment before
running the generator. An outdated lockfile causes an error rather than an
implicit lockfile change. See [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/).

## Update a formula

1. Change the exact application pin deliberately. For example, to reproduce the
   current application dependency:

   ```sh
   uv add --dev --exact open-api-maker-kamaalio==0.0.2
   ```

   For a release update, substitute the reviewed release version. This updates
   `pyproject.toml`, `uv.lock`, and the environment. Use the same workflow for
   `homebrew-pypi-poet` tooling changes.

2. Regenerate the formula:

   ```sh
   just formulate
   git diff -- Formula/open_api_maker.rb pyproject.toml uv.lock
   ```

   The generator looks up package metadata on PyPI, so network access is needed.
   It uses installed dependency versions from the uv environment. Updating the
   lockfile can therefore change generated formula resources even when the
   application version stays the same.

3. Review the generated output before accepting it. Generation replaces the
   entire formula and renames `OpenApiMakerKamaalio` to `OpenApiMaker`. Check the
   description, homepage, source version and URL, SHA-256, Python dependency,
   resource versions and checksums, installation logic, and test block. Restore
   any intentional hand-maintained content that generation replaces.

The recipe writes temporary files beside the destination and replaces it only
after generation and transformation succeed. A failed generator leaves the
existing formula intact. To preview without replacing the tracked formula:

```sh
just OPEN_API_MAKER_FORMULA=/tmp/open_api_maker.rb formulate
ruby -c /tmp/open_api_maker.rb
```

`pyproject.toml` is the dependency source of truth; generate `uv.lock` with uv
rather than editing it manually. After intentional manifest edits, run `uv lock`
and `uv sync --locked`. For a targeted transitive update, use
`uv lock --upgrade-package PyYAML` and review the resulting graph. There is no
separate requirements file to maintain.

## Validate changes

Check the environment and Ruby syntax first:

```sh
uv lock --check
just init-venv
uv run --locked poet --help
ruby -c Formula/open_api_maker.rb
just --dry-run test-install
```

For packaging changes, run Homebrew's style and audit checks against your tap
checkout. `brew --repository kamaal111/tap` identifies the checkout Homebrew uses;
ensure it contains your changes before running:

```sh
brew style kamaal111/tap/open_api_maker
brew audit --strict kamaal111/tap/open_api_maker
```

Then test the local formula's source installation:

```sh
just test-install
```

This installs software into your Homebrew prefix and may enter an interactive
debugger on failure. If the formula is already installed, use an intentional
`brew reinstall --build-from-source --verbose --debug ./Formula/open_api_maker.rb`
to exercise the changed formula. Installation alone does not run the formula's
functional test. See [Homebrew's formula cookbook](https://docs.brew.sh/Formula-Cookbook)
and [command reference](https://docs.brew.sh/Manpage) for packaging guidance.

## Current limitations and troubleshooting

- **Placeholder formula metadata and test:** the checked-in formula has the
  description `Shiny new formula`, an empty homepage, and `test do false end`.
  Audit or functional checks may fail. The test provides no application behavior
  coverage and must be replaced before treating functional testing as a passing
  release gate. This setup migration does not repair those packaging issues.
- **Deprecated generator API:** poet 0.10.0 imports `pkg_resources`, so the
  maintainer dependencies constrain `setuptools<81`. A deprecation warning is
  expected. Removing the constraint requires replacing or updating that API usage
  and validating generation on Python 3.15.
- **Setuptools advisories:** the compatible locked version, 80.10.2, is affected
  by [a source-distribution exclusion bypass](https://osv.dev/vulnerability/GHSA-h35f-9h28-mq5c)
  (also tracked as PYSEC-2026-3447) and
  [a Windows legacy wheel-installation path escape](https://osv.dev/vulnerability/GHSA-xmj3-9gf7-h52w).
  Their fixes require versions without poet's required `pkg_resources` API.
  This non-package project uses setuptools for poet's installed-package lookup;
  it does not build or publish source distributions or use legacy Windows wheel
  installation. Keep those operations out of this maintainer environment.
  Replacing poet's deprecated API is needed to remove this compatibility risk.
- **Lockfile mismatch:** after an intentional dependency edit, run `uv lock`,
  review the diff, and rerun `just init-venv`. Do not hand-edit hashes or bypass
  the locked checks to hide a mismatch.
- **Missing commands:** run `mise install` and use `mise exec -- just check`.
  Synchronize an existing virtual environment with `mise exec -- just init-venv`.
- **Generation or download failure:** check access to PyPI and Python download
  hosts, then rerun the command. The existing formula is preserved when
  generation fails.

## Before opening a pull request

- Keep changes focused and update documentation when commands or pins change.
- Review the manifest, generated lockfile, and any generated formula changes.
- Report checks run and any unresolved compatibility, audit, or testing issues.
- Keep local environments and temporary generated files out of the commit.

## agent-vm bottles

agent-vm ships a prebuilt Apple Silicon macOS executable and a relocatable
Homebrew bottle for macOS 27. Homebrew selects a compatible bottle when available;
otherwise it installs from the release archive with compatible Command Line Tools.

The formula is generated from `packaging/homebrew/agent-vm.rb.in`. Keep template
changes synchronized with `Formula/agent-vm.rb`. The updater verifies the upstream
release archive and checksum, builds a native macOS bottle in an isolated
Homebrew prefix, and tests installation from that bottle before publishing it.
It writes the native bottle tag and verified checksum into the formula.
Bottles are hosted in immutable, checksum-named releases in this tap repository.
Published assets are verified and reused rather than overwritten. Release updates
require permission to create releases and PRs in this tap. The updater rejects
downgrades and protects manual branch changes.

Run on Apple Silicon macOS:

```sh
mise exec -- just check
mise exec -- uv run --locked python scripts/update-package.py agent-vm --validate-only
```

Validation clones Homebrew into a disposable prefix under `~/Library/Caches`,
checks Ruby syntax and formula style, and fetches the published bottle with
checksum verification. It then builds a native bottle from the source archive,
installs it through a temporary validation tap, checks `poured_from_bottle` in
the installation receipt, runs `brew test`, checks version/help, and uninstalls.
Downloads, installation files, and executable links stay inside the disposable
environment. Validation requires Git, Homebrew, Ruby, compatible developer tools
for bottle preparation, and network access. It does not need GitHub credentials
or publish commits, releases, branches, or PRs. The PR workflow runs these checks.

Keep Tart and guest setup separate from package validation.

## Namu bottles

Namu's upstream archives already contain compiled binaries, but Homebrew still
runs source-build CLT checks for a formula without a compatible bottle. Native
macOS bottles avoid that path. Namu and agent-vm share bottle preparation,
checksum verification, immutable publication, and receipt validation through
`scripts/homebrew_bottle.py`.

Validate without publishing or changing the formula:

```sh
mise exec -- just check
mise exec -- uv run --locked python scripts/namu-bottle.py
```

This needs a Mac with compatible build tools for bottle preparation. It clones
Homebrew into a disposable cache prefix, builds from the verified release
archive, requires a relocatable bottle, reinstalls it with an ordinary
`brew install`, and checks `poured_from_bottle` in the installation receipt.
It runs the worktree lifecycle test, checks version/help, and uninstalls.
It does not modify the system CLT installation or disable Homebrew checks.

For application version updates, use the **Update Namu** workflow described in
[the README](README.md#update-namu). Its updater uses the shared bottle tooling
and `packaging/homebrew/namu.rb.in`; keep template and formula maintenance in sync.
It verifies all four platform archives, prepares a native bottle, and proposes a
formula-only PR without altering platform dependencies or the functional test.

Run the updater tests and a publication-free rehearsal:

```sh
mise exec -- just check
mise exec -- uv run --locked python scripts/update-package.py namu --version v0.2.0 \
  --dry-run --output-dir /tmp/namu-update-rehearsal
```

Use an empty output directory. Review `namu.rb` and `report.json`. The report records
the release, tap base, verified archive digests, native bottle metadata, and completed
validation stages. Dry runs never publish releases, push branches, open PRs, or
trigger workflows. The CI rehearsal retains the formula and report as artifacts.

The existing `namu-bottle.py` tool remains available for deliberate bottle-only
maintenance of the checked-in version. Its `--output-dir`, `--publish`,
`--target-sha`, and `--write` options preserve their existing behavior. Version
updates should go through `update-package.py namu` so release verification, branch ownership,
lease protection, and PR validation are applied together.

The checked-in bottle targets Apple Silicon macOS 27. The updater publishes a
native bottle for its validation host; other supported platforms retain the
release-archive installation path. When the application version is unchanged,
existing platform bottles are preserved rather than replaced by another platform.

## Shared release updater

Both update workflows call `update_package(package, version)` in
`scripts/tap_updater.py`. Package definitions contain only the name, release targets,
and expected help text. The release repository, formula path, update branch, marker,
and validation workflow are derived from the name. Formula templates and optional
managed README sections live under `packaging/homebrew/`.

The CLI is `mise exec -- uv run --locked python scripts/update-package.py namu` or
`mise exec -- uv run --locked python scripts/update-package.py agent-vm`. Both support
`--version`, `--dry-run --output-dir`, and `--validate-only`. The old
`update-namu.py` and `update-agent-vm.py` filenames remain compatibility wrappers.
Release verification, rendering, bottle validation, reporting, publication, and
PR recovery all use one implementation and one suite parameterized for both tools.
