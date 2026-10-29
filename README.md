# kamaal111 Homebrew tap

A [Homebrew](https://brew.sh/) tap for installing packages maintained by
[kamaal111](https://github.com/kamaal111).

## Available formulae

| Formula | Python package | Packaged version |
| --- | --- | --- |
| `open_api_maker` | [open-api-maker-kamaalio](https://pypi.org/project/open-api-maker-kamaalio/) | 0.0.2 |

This repository contains the Homebrew packaging. See the upstream package for
application usage information.

## Install

Install [Homebrew](https://brew.sh/) first, then run:

```sh
brew tap kamaal111/tap
brew install kamaal111/tap/open_api_maker
```

Homebrew manages the formula's Python dependency. You do not need uv or the
maintainer environment to install this formula.

## Inspect and update

```sh
brew info kamaal111/tap/open_api_maker
brew list kamaal111/tap/open_api_maker
brew update
brew upgrade kamaal111/tap/open_api_maker
```

Upgrades install the version published in this tap; they do not track new PyPI
releases automatically.

## Uninstall

```sh
brew uninstall kamaal111/tap/open_api_maker
brew untap kamaal111/tap
```

Uninstall any formulae from this tap before removing the tap itself.

## Contribute and get help

See [CONTRIBUTING.md](CONTRIBUTING.md) for the Python 3.15 uv setup, formula
generation, validation, and current packaging limitations.

Report packaging problems in the [issue tracker](https://github.com/kamaal111/homebrew-tap/issues).
Include the command, its output, `brew config`, and relevant `brew doctor` output,
after removing sensitive information.

## Update agent-vm

After an agent-vm release has published its archive and checksums, run:

```sh
gh workflow run update-agent-vm.yml --repo kamaal111/homebrew-tap -f version=v0.1.0
```

Or run locally from this checkout on an Apple Silicon Mac. You'll need Python
3.11+, Git configured for commits, Homebrew, and GitHub CLI signed in with write
access to this tap:

```sh
gh auth setup-git
python3 scripts/update-agent-vm.py --version v0.1.0
```

Omit the version to use the latest stable release. The updater tests the formula
and opens a PR for you to review and merge. Installation becomes available after
the first formula PR is merged.

For the workflow, enable **Settings → Actions → General → Workflow permissions →
Allow GitHub Actions to create and approve pull requests**.

Run updater tests with:

```sh
uv run --locked pytest
```

<!-- agent-vm:start -->
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
<!-- agent-vm:end -->

## Namu

Install on macOS or Linux, on ARM64 or AMD64:

```sh
brew install kamaal111/tap/namu
```

Namu manages Git worktrees across your projects. Try `namu create feature/cards`,
`namu open`, and `namu list`. See [Namu's documentation](https://github.com/kamaal111/namu)
for setup hooks, ignored-file copying, and safe deletion.

The formula selects a prebuilt executable for your OS and architecture; Go is
not required to install or run it. It uses macOS's system Git; on Linux, Homebrew
installs Git as a dependency.

### Update Namu

Generate a formula using Namu's upstream release tooling rather than maintaining
another copy of its checksum and platform-selection logic in this tap. From the
root of a Namu checkout, run:

```sh
python3 scripts/update_homebrew.py --version v0.1.0 --output /tmp/namu.rb
```

Use the desired stable release tag, review the generated URLs and checksums,
and copy its version, URL, and checksum changes into `Formula/namu.rb` while
preserving the tap's platform dependencies and functional test. The generator verifies all four published
archives against the release checksum manifest before writing the formula.
Open a worktree branch and PR for each update; do not commit updates on `main`.
The Namu validation workflow checks formula style, installation, the worktree
lifecycle test, and uninstallation on macOS and Linux.
