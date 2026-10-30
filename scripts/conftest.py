"""Real local Git remotes shared by updater integration tests."""
from pathlib import Path

import pytest

from homebrew_bottle import run


@pytest.fixture
def tap_repository(tmp_path):
    def create(files):
        local, remote = tmp_path / "local", tmp_path / "remote.git"
        run("git", "init", "--quiet", "--initial-branch=main", str(local))
        for key, value in {"user.name": "Updater Test", "user.email": "test@example.com",
                           "commit.gpgsign": "false"}.items():
            run("git", "config", key, value, cwd=local)
        for name, contents in files.items():
            target = local / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents)
        run("git", "add", ".", cwd=local)
        run("git", "commit", "--quiet", "-m", "Initial fixture", cwd=local)
        run("git", "clone", "--quiet", "--bare", str(local), str(remote))
        run("git", "remote", "add", "origin", str(remote), cwd=local)
        return local, remote, run
    return create
