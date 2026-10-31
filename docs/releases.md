# Release updates

Use this guide to update Namu or agent-vm after an upstream stable release.
For contributor tools, start with [Set up](../CONTRIBUTING.md#set-up). For legacy
Python generation, use [Maintaining open_api_maker](open-api-maker.md).

## Prerequisites

The upstream release must publish a stable `vX.Y.Z` tag, `checksums.txt`, and
all supported archives:

| Package | Upstream repository | Required archive targets | Update branch |
| --- | --- | --- | --- |
| Namu | `kamaal111/namu` | `darwin_arm64`, `darwin_amd64`, `linux_arm64`, `linux_amd64` | `update-namu` |
| agent-vm | `kamaal111/agent-vm` | `darwin_arm64` | `update-agent-vm` |

In this tap, enable **Settings → Actions → General → Workflow permissions →
Allow GitHub Actions to create and approve pull requests**. Update workflows
declare the contents, pull-request, and Actions permissions they need and use
the workflow's GitHub token; no extra token is required.

Local updates and rehearsals require Apple Silicon macOS, Git, Homebrew, Ruby,
compatible Command Line Tools, network access, and an authenticated GitHub CLI.
Publishing also requires Git commit identity and write access to this tap for
releases, branches, PRs, and validation workflow dispatch.

## Run an update workflow

Open **Actions → Update Namu → Run workflow** or
**Actions → Update agent-vm → Run workflow** in this tap. Supply a stable release
tag or leave the version empty to use the latest stable release.

Equivalent explicit-version CLI examples:

```sh
gh workflow run update-namu.yml --repo kamaal111/homebrew-tap -f version=v0.2.0
gh workflow run update-agent-vm.yml --repo kamaal111/homebrew-tap -f version=v0.2.0
```

These tags illustrate selecting a release; they are not declarations of the
latest version. Choose the intended upstream release. Omit `-f version=...`
to select the latest stable release.

The updater verifies every archive checksum, renders the formula, and builds
and tests a native macOS bottle in an isolated Homebrew prefix. It publishes an
immutable bottle asset, opens or refreshes the package's update PR, and explicitly
dispatches its validation workflow. Other platforms retain their verified
release-archive installation path.

Review the formula diff, upstream release, and passing checks, then merge the PR.
The updater does not create an upstream application release or merge its own PR.

## Run an update locally

Run commands from the repository root after contributor setup. Configure Git's
commit identity and authenticate GitHub CLI with write access to this tap:

```sh
gh auth setup-git
mise exec -- uv run --locked python scripts/update-package.py namu --version v0.2.0
```

Replace `namu` with `agent-vm` for that package. Omit `--version` to select the
latest stable release. This command publishes releases, pushes the update branch,
opens or updates a PR, and dispatches validation after local checks pass.

## Rehearse without publishing

To prepare and validate a particular release without changing this checkout or
publishing remote changes:

```sh
mise exec -- uv run --locked python scripts/update-package.py namu --version v0.2.0 \
  --dry-run --output-dir /tmp/namu-update-rehearsal
```

Use a new or empty output directory. Replace `namu` with `agent-vm` and choose a
separate output directory for that package. Local prerequisites, including GitHub
CLI authentication, still apply. The rehearsal performs real downloads, bottle
installation, functional tests, and uninstall in isolation.

Review the generated `namu.rb` (or `agent-vm.rb`), `report.json`, and bottle
artifacts. The report records the release, tap base, archive digests, native
bottle metadata, and completed validation stages. Keep these artifacts out of Git.
Dry runs never publish releases, push branches, open PRs, or trigger workflows.
See [CI coverage](validation.md#ci-coverage) for retained rehearsal artifacts.

## Retry and recover

Rerun after transient failures. The updater verifies and reuses an existing
immutable bottle asset instead of replacing it and refreshes its existing PR.
An already merged release with matching generated content and a bottle is a no-op.

Downgrades, checksum mismatches, manual edits to the update branch, and changes to
the tap base or branch head stop publication. Inspect these failures before
retrying; do not delete or force-update someone else's branch to bypass checks.
If validation dispatch fails after the PR is opened, rerun the update workflow
or dispatch the matching validation workflow against its update branch:

```sh
gh workflow run validate-namu.yml --repo kamaal111/homebrew-tap --ref update-namu
```

For agent-vm, use `validate-agent-vm.yml` and `update-agent-vm`.

## Updater ownership and bottle maintenance

Both workflows use `update_package(package, version)` in `scripts/tap_updater.py`
through `scripts/update-package.py`. Package definitions own the name, release
targets, and expected help text; repository names, formula paths, update branches,
markers, and validation workflow names derive from the package name.

Templates live at `packaging/homebrew/namu.rb.in` and
`packaging/homebrew/agent-vm.rb.in`. Keep template changes synchronized with
`Formula/namu.rb` and `Formula/agent-vm.rb`. The optional agent-vm Markdown snippet
owns the [managed README section](../CONTRIBUTING.md#documentation-and-generated-files).
The old `update-namu.py` and `update-agent-vm.py` entry points remain compatibility
wrappers. Both packages share release verification, rendering, bottle validation,
reporting, publication, and PR recovery.

Bottle preparation, checksum verification, immutable publication, and receipt
validation share `scripts/homebrew_bottle.py`. Bottles are hosted in immutable,
checksum-named releases in this tap. The updater publishes a native bottle for
its validation host; when the application version is unchanged, existing platform
bottles are preserved.

`scripts/namu-bottle.py` remains available for deliberate bottle-only maintenance
of the checked-in version. `--output-dir` retains artifacts; `--publish` requires
`--target-sha` naming a full existing tap commit SHA and `--output-dir`; `--write`
also requires `--output-dir` and edits the checked-in formula. Use
`update-package.py namu` for version updates so release verification, branch
ownership, lease protection, and PR validation apply together.

Return to [Contributing](../CONTRIBUTING.md) or continue with
[Validation and troubleshooting](validation.md).
