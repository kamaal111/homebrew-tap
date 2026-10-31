# Contributing

This repository maintains Homebrew packaging for Namu, agent-vm, and deprecated
`open_api_maker`. Application development and usage belong in their upstream
projects, linked from the [README](README.md#available-formulae).

## Contributor guides

| Task | Guide |
| --- | --- |
| Update Namu or agent-vm to an upstream release | [Release updates](docs/releases.md) |
| Check formulae, bottles, or workflow changes | [Validation and troubleshooting](docs/validation.md) |
| Regenerate the deprecated Python formula | [Maintaining open_api_maker](docs/open-api-maker.md) |

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
```

The environment is created by `uv sync --locked`; do not edit `uv.lock` by hand.
Formula installation and native bottle validation still require Homebrew and
compatible developer tools from the system. Mise does not install or alter CLT.

## Repository layout

| Path | Purpose |
| --- | --- |
| `Formula/` | Published formulae, checksums, dependencies, installation, and functional tests |
| `packaging/homebrew/` | Formula templates and updater-managed README snippets |
| `scripts/` | Shared release updater, bottle tooling, compatibility entry points, and tests |
| `.github/workflows/` | Release update and formula validation workflows |
| `docs/` | Detailed maintainer guides |
| `pyproject.toml` and `uv.lock` | Maintainer dependencies and their resolved versions and hashes |
| `.python-version` | Python version selected by uv |
| `mise.toml` | Pinned uv, just, and actionlint toolchain |
| `justfile` | Setup, checks, validation, rehearsal, and legacy generation recipes |

The Python maintainer environment is separate from software installed by
Homebrew. Installing packages from this tap does not require contributor tools.

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
| `just formulate` | Legacy: regenerate `Formula/open_api_maker.rb` |
| `just test-install` | Legacy: install local `open_api_maker` from source with verbose output and debugging |

Prefix these recipes with `mise exec --` when just is not on your `PATH`.
See [validation](docs/validation.md) for platform prerequisites and installation
side effects, and [release updates](docs/releases.md) for publishing commands.

## Documentation and generated files

Keep user installation instructions in [README.md](README.md), onboarding here,
and detailed maintenance procedures in the linked guides. Link to the owning
guide instead of copying procedures between documents.

Keep formula template edits synchronized with the corresponding checked-in
formula. The agent-vm install block in README is managed by the shared updater:
edit `packaging/homebrew/agent-vm.md` and copy the same contents into README,
including exactly one `<!-- agent-vm:start -->` / `<!-- agent-vm:end -->` pair.
Future updates replace that block from the snippet. Other README content is
maintained manually.

## Before opening a pull request

- Keep changes focused and update documentation when commands or pins change.
- Review any manifest, generated lockfile, template, and formula changes together.
- Run the [checks appropriate to your change](docs/validation.md) and report
  results and unresolved compatibility, audit, or testing issues.
- Keep local environments, rehearsal output, and temporary generated files out of Git.
