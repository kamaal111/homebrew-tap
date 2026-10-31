# kamaal111 Homebrew tap

A [Homebrew](https://brew.sh/) tap for installing packages maintained by
[kamaal111](https://github.com/kamaal111).

## Available formulae

| Formula | Purpose and upstream documentation | Supported platforms | Status |
| --- | --- | --- | --- |
| `namu` | [Manage Git worktrees](https://github.com/kamaal111/namu) | macOS and Linux, ARM64 and AMD64 | Maintained |
| `agent-vm` | [Persistent development VMs and coding-agent sessions](https://github.com/kamaal111/agent-vm) | Apple Silicon macOS | Maintained |
| `open_api_maker` | [Python OpenAPI tooling](https://pypi.org/project/open-api-maker-kamaalio/) | Python-based Homebrew formula; platform compatibility is not validated in this tap | Deprecated |

This repository contains Homebrew packaging. See the upstream projects for
application usage and configuration. Run `brew info` for the currently packaged
version and requirements.

## Install

Install [Homebrew](https://brew.sh/) first, then add the tap:

```sh
brew tap kamaal111/tap
```

Choose a package below. Contributor tools such as mise and uv are not required.

### Namu

Install on macOS or Linux, on ARM64 or AMD64:

```sh
brew install kamaal111/tap/namu
```

The formula selects a prebuilt executable for your OS and architecture; Go is
not required. It uses macOS's system Git; on Linux, Homebrew installs Git as a
dependency. Homebrew uses a compatible bottle when available, otherwise the
release archive, which may require compatible Command Line Tools on macOS.

Try `namu create feature/cards`, `namu open`, and `namu list`. See
[Namu's documentation](https://github.com/kamaal111/namu) for setup hooks,
ignored-file copying, and safe deletion.

<!-- agent-vm:start -->
### agent-vm

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

### open_api_maker (deprecated)

`open_api_maker` is deprecated as of 2026-10-31 because it is no longer
maintained in this tap. Installation remains available but is discouraged.
For existing users:

```sh
brew install kamaal111/tap/open_api_maker
```

Homebrew manages the formula's Python dependency. See the
[legacy guide](docs/open-api-maker.md#current-limitations-and-troubleshooting)
for known packaging limitations.

## Inspect and update

For example, to inspect and upgrade Namu:

```sh
brew info kamaal111/tap/namu
brew list kamaal111/tap/namu
brew update
brew upgrade kamaal111/tap/namu
```

Substitute `agent-vm` or `open_api_maker` for the other formulae. Upgrades install
the version published in this tap; they do not automatically track upstream releases.

## Uninstall

```sh
brew uninstall kamaal111/tap/namu
brew untap kamaal111/tap
```

Substitute the formula you installed. Uninstall all formulae from this tap before
removing the tap itself.

## Get help

Report packaging problems in the [issue tracker](https://github.com/kamaal111/homebrew-tap/issues).
Include the command, its output, `brew config`, and relevant `brew doctor` output,
after removing sensitive information. Use the upstream projects for application issues.

## Contribute

Start with [Contributing](CONTRIBUTING.md) for the pinned toolchain and repository
layout. Maintainer guides cover [release updates](docs/releases.md),
[validation and troubleshooting](docs/validation.md), and the
[deprecated Python formula](docs/open-api-maker.md).
