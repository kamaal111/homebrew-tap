set export

OPEN_API_MAKER_FORMULA := "Formula/open_api_maker.rb"

default:
  just --list

formulate:
    #!/bin/zsh
    set -eu

    generated=$(mktemp "${OPEN_API_MAKER_FORMULA}.generated.XXXXXX")
    transformed=""
    trap 'rm -f "$generated" "$transformed"' EXIT
    transformed=$(mktemp "${OPEN_API_MAKER_FORMULA}.transformed.XXXXXX")
    mise exec -- uv run --locked poet -f open-api-maker-kamaalio > "$generated"
    sed 's/OpenApiMakerKamaalio/OpenApiMaker/g' "$generated" > "$transformed"
    chmod 644 "$transformed"
    mv "$transformed" "$OPEN_API_MAKER_FORMULA"

test-install:
    #!/bin/zsh

    export HOMEBREW_NO_INSTALL_FROM_API=1

    brew install --build-from-source --verbose --debug $OPEN_API_MAKER_FORMULA

init-venv:
    mise exec -- uv sync --locked

# Validate workflow syntax and expressions with the pinned actionlint
lint:
    mise exec -- actionlint -shellcheck=

# Run the locked Python test suite
test:
    mise exec -- uv run --locked pytest

# Run the same checks used by CI
check: lint test

# Run matching locked Python tests
test-run pattern package="scripts":
    mise exec -- uv run --locked pytest {{ quote(package) }} -k {{ quote(pattern) }}

# Validate the checked-in Namu formula in an isolated Homebrew prefix
validate-namu:
    mise exec -- uv run --locked python scripts/namu-bottle.py

# Rehearse a Namu release update without publishing
rehearse-namu version output:
    mise exec -- uv run --locked python scripts/update-package.py namu --version {{ quote(version) }} --dry-run --output-dir {{ quote(output) }}
