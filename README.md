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

See [CONTRIBUTING.md](CONTRIBUTING.md) for the pinned mise toolchain, formula
generation, validation, and current packaging limitations.

Report packaging problems in the [issue tracker](https://github.com/kamaal111/homebrew-tap/issues).
Include the command, its output, `brew config`, and relevant `brew doctor` output,
after removing sensitive information.

## Update agent-vm

After an agent-vm release has published its archive and checksums, run:

```sh
gh workflow run update-agent-vm.yml --repo kamaal111/homebrew-tap -f version=v0.1.0
```

Or run locally on an Apple Silicon Mac after the
[contributor tool setup](CONTRIBUTING.md#set-up). Configure Git for commits and
sign GitHub CLI in with write access to this tap:

```sh
gh auth setup-git
mise exec -- uv run --locked python scripts/update-package.py agent-vm --version v0.1.0
```

Omit the version to use the latest stable release. The updater tests the formula
and opens a PR for you to review and merge. Installation becomes available after
the first formula PR is merged.

For the workflow, enable **Settings → Actions → General → Workflow permissions →
Allow GitHub Actions to create and approve pull requests**.

Run updater tests with:

```sh
mise exec -- just check
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
installs Git as a dependency. Apple Silicon macOS 27 installs from a relocatable
Homebrew bottle, avoiding source-build CLT checks. Other hosts use the release
archive when no compatible bottle is available and may require compatible tools.

### Update Namu

After Namu publishes a stable release and all four archives, open
**Actions → Update Namu → Run workflow** in this tap. Enter a stable tag such as
`v0.2.0`, or leave the version empty for the latest stable release:

```sh
gh workflow run update-namu.yml --repo kamaal111/homebrew-tap -f version=v0.2.0
```

The workflow verifies all archive checksums, builds and tests a native macOS
bottle in an isolated Homebrew prefix, publishes an immutable bottle asset, and
opens or refreshes one `update-namu` PR. It explicitly starts Namu validation
for that branch. Review the formula and passing checks, then merge the PR.
The tap update does not create a new upstream Namu release or merge itself.
Other supported platforms continue using their verified release archives.

Enable **Settings → Actions → General → Workflow permissions → Allow GitHub
Actions to create and approve pull requests**. The workflow declares the
contents, pull-request, and Actions permissions it needs; no extra token is
required. Updating the formula template and shared updater tooling is covered
by the existing agent-vm tests and the Namu updater tests.

To rehearse a particular release without publishing or changing this checkout:

```sh
mise exec -- uv run --locked python scripts/update-package.py namu --version v0.2.0 \
  --dry-run --output-dir /tmp/namu-update-rehearsal
```

Use an empty output directory. The real downloads, bottle installation, functional
test, and uninstall run in isolation. The output includes `namu.rb`, `report.json`,
and bottle artifacts. PR CI rehearses the latest stable releases of both packages, tests the suite
against each generated formula, and uploads the candidate formula and
report as `namu-update-rehearsal`. Keep these artifacts out of Git.

Rerun the workflow after transient failures. It verifies and reuses an existing
bottle asset rather than replacing it, and refreshes its existing PR. An already
merged release is a no-op. Downgrades, checksum mismatches, manual edits to the
update branch, or a changing tap base/head stop publication; inspect the failure
before retrying. Do not delete or force-update someone else's branch to bypass
these checks. If validation dispatch fails after a PR is opened, rerun the update
workflow, or dispatch `validate-namu.yml` against `update-namu` manually.
