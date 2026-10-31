# Maintaining open_api_maker

This guide covers the deprecated Python formula and its generator limitations.
Start with the [contributor setup](../CONTRIBUTING.md#set-up). Run commands from
this repository's root; use `mise exec --` before direct `uv` commands if mise
is not activated in your shell.

## Regenerate the formula

`open_api_maker` is deprecated as of 2026-10-31 because it is no longer
maintained in this tap. If regenerating it, preserve its deprecation metadata.

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

   In particular, restore this declaration after the source checksum and before
   dependencies:

   ```ruby
   deprecate! date: "2026-10-31", because: "is no longer maintained in this tap"
   ```

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
  release gate. These packaging issues remain unresolved.
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

For generation or download failures, check access to PyPI and Python download
hosts, then retry. A failed generator preserves the existing formula.
For environment problems, see [troubleshooting](validation.md#troubleshooting).

Return to [Contributing](../CONTRIBUTING.md) or the [installation guide](../README.md).
