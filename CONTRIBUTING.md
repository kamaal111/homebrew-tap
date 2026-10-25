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
| `.python-version` | Python 3.15 selection for uv |
| `justfile` | Setup, formula generation, and local installation recipes |

## Set up

Install [Homebrew](https://brew.sh/), Git, and zsh. Install the maintainer tools:

```sh
brew install uv just
git clone https://github.com/kamaal111/homebrew-tap.git
cd homebrew-tap
just init-venv
```

The setup recipe runs `uv sync --locked`, creating or synchronizing `.venv` from
the committed lockfile. uv selects Python 3.15 from `.python-version` and can
[download it](https://docs.astral.sh/uv/guides/install-python/) when needed.
PyYAML may need to build from source on Python 3.15; on macOS, install the Xcode
Command Line Tools with `xcode-select --install` if compiler tools are missing.

No shell activation or global pip installation is needed. Confirm the environment:

```sh
uv run --locked python --version
uv run --locked poet --help
```

The Python version should be 3.15.x. `.venv` is ignored; commit `uv.lock`.

## Commands

Run recipes from the repository root:

| Command | Effect |
| --- | --- |
| `just` or `just --list` | List available recipes |
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
- **Missing commands:** install uv and just and ensure their executables are on
  `PATH`. An existing environment created with another Python version can be
  synchronized with `just init-venv`; uv will select the required interpreter.
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
uv run --locked pytest
uv run --locked python scripts/update-agent-vm.py --validate-only
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
