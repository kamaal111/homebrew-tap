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
