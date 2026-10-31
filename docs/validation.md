# Validation and troubleshooting

Use this guide to choose checks for a documentation, tooling, or formula change.
Complete the [contributor setup](../CONTRIBUTING.md#set-up) and run commands from
the repository root. For publication, see [Release updates](releases.md).

## Routine repository checks

```sh
mise exec -- just check
```

This runs actionlint for workflow syntax and expressions, followed by the locked
Python test suite. It does not perform native Homebrew installation validation.
For focused iteration, use `just lint`, `just test`, or
`just test-run PATTERN PACKAGE`; the package argument defaults to `scripts`.
Prefix recipes with `mise exec --` when needed.

For documentation changes, check relative links and heading anchors, compare
commands with `justfile` and CLI parsers, and ensure the managed agent-vm README
block matches `packaging/homebrew/agent-vm.md`. Formula installation and release
publication are unnecessary for a documentation-only change.

## Native formula and bottle validation

Namu and agent-vm ship compiled release executables. Homebrew selects a compatible
bottle when available; otherwise it uses the release archive and may require
compatible Command Line Tools on macOS. Native relocatable bottles avoid that
source-installation path. Read bottle tags from the checked-in formulae rather
than assuming every macOS version has a native bottle.

Run these checks on Apple Silicon macOS with Git, Homebrew, Ruby, compatible
developer tools for bottle preparation, and network access:

| Package | Command |
| --- | --- |
| agent-vm | `mise exec -- uv run --locked python scripts/update-package.py agent-vm --validate-only` |
| Namu | `mise exec -- just validate-namu` |

The Namu recipe runs `scripts/namu-bottle.py` without publication options.
The shared updater also supports `scripts/update-package.py namu --validate-only`.
`--validate-only` cannot be combined with version, dry-run, or output-directory
options. These validation commands do not need GitHub credentials.

Validation clones Homebrew into a disposable cache prefix, checks Ruby syntax and
formula style, and fetches the published bottle with checksum verification. It
builds a native bottle from the verified release archive, requires relocatability,
installs through a temporary validation tap, and checks `poured_from_bottle` in
the installation receipt. It runs `brew test`, checks version/help, and uninstalls.
Namu's functional test exercises creating, opening, listing, and deleting a Git
worktree; agent-vm checks its version and help text.

Downloads, installations, and executable links stay in the disposable environment.
The checks do not publish commits, releases, branches, or PRs, modify the system
CLT installation, or disable Homebrew checks. Keep Tart, guest images, and
credentials separate from agent-vm package validation.

To validate a proposed upstream release instead of the checked-in formula, use a
[publication-free rehearsal](releases.md#rehearse-without-publishing).
For the legacy formula's style, audit, source installation, and known test
limitations, use [Maintaining open_api_maker](open-api-maker.md#validate-changes).
Its `just test-install` recipe installs into your Homebrew prefix and may enter
an interactive debugger on failure.

## CI coverage

The validation workflows run on pull requests, pushes to `main`, and manual dispatch:

| Workflow | Coverage |
| --- | --- |
| `validate-agent-vm.yml` | Routine checks and isolated agent-vm bottle validation on `macos-15` |
| `validate-namu.yml` | Routine checks, Namu formula style and installation tests on `macos-15` and `ubuntu-latest`; native bottle validation on macOS |
| `validate-namu.yml` rehearsal job | Latest stable release rehearsal for both Namu and agent-vm on `macos-15`, followed by tests against each generated formula |

Rehearsal artifacts are named `namu-update-rehearsal` and
`agent-vm-update-rehearsal`. Each contains the candidate formula and `report.json`.
The update workflows run routine checks before validating and proposing a release
PR, then explicitly dispatch the corresponding validation workflow.

## Troubleshooting

- **Missing commands:** run `mise install` and use `mise exec -- just check`.
  Synchronize an existing virtual environment with `mise exec -- just init-venv`.
- **Lockfile mismatch:** after an intentional dependency edit, run
  `mise exec -- uv lock`, review the diff, and rerun `mise exec -- just init-venv`.
  Do not hand-edit hashes or bypass locked checks to hide a mismatch.
- **Download failure:** check access to GitHub release assets, Homebrew, and Python
  download hosts as appropriate, then retry. Legacy generation also needs PyPI.
- **Native validation prerequisites:** use Apple Silicon macOS and compatible
  developer tools. Mise manages contributor tools; it does not install or alter CLT.
- **Publication or protected-branch failures:** follow
  [Retry and recover](releases.md#retry-and-recover) before retrying an update.
- **Legacy generator warnings or audit failures:** consult the
  [known limitations](open-api-maker.md#current-limitations-and-troubleshooting).

Return to [Contributing](../CONTRIBUTING.md) or the [installation guide](../README.md).
