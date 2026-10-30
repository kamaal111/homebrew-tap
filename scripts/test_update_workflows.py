from pathlib import Path

import yaml
import pytest

ROOT = Path(__file__).resolve().parent.parent


def workflow(name):
    return yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)


@pytest.mark.parametrize("name", ["namu", "agent-vm"])
def test_manual_updater_has_required_permissions_and_safe_optional_version_input(name):
    action = workflow(f"update-{name}.yml")
    assert set(action["on"]) == {"workflow_dispatch"}
    assert action["on"]["workflow_dispatch"]["inputs"]["version"]["required"] == "false"
    assert action["permissions"] == {"contents": "write", "pull-requests": "write", "actions": "write"}
    assert action["concurrency"]["group"] == f"update-{name}"
    job = action["jobs"]["update"]
    assert job["runs-on"] == "macos-15"
    step = next(step for step in job["steps"] if step.get("name") == "Validate release and propose formula PR")
    assert step["env"]["RELEASE_VERSION"] == "${{ inputs.version }}"
    assert '--version "$RELEASE_VERSION"' in step["run"]
    assert "${{ inputs.version }}" not in step["run"]
    assert f'scripts/update-package.py {name} --version' in step["run"]


def test_validation_is_dispatchable_and_rehearses_real_release_with_read_only_token():
    action = workflow("validate-namu.yml")
    assert "workflow_dispatch" in action["on"]
    assert action["permissions"] == {"contents": "read"}
    job = action["jobs"]["rehearse-updater"]
    assert job["strategy"]["matrix"]["package"] == ["namu", "agent-vm"]
    steps = job["steps"]
    rehearsal = next(step for step in steps if step.get("name") == "Rehearse package update without publishing")
    assert '--dry-run --output-dir "$RUNNER_TEMP/package-rehearsal"' in rehearsal["run"]
    assert "--version" not in rehearsal["run"]
    candidate = next(step for step in steps if step.get("name") == "Test suite against generated formula")
    assert 'cp "$RUNNER_TEMP/package-rehearsal/$RELEASE_PACKAGE.rb" "Formula/$RELEASE_PACKAGE.rb"' in candidate["run"]
    assert "just check" in candidate["run"]
    artifacts = next(step for step in steps if step.get("uses", "").startswith("actions/upload-artifact@"))
    assert artifacts["with"]["if-no-files-found"] == "error"
    assert "${{ matrix.package }}.rb" in artifacts["with"]["path"]
    assert "report.json" in artifacts["with"]["path"]
