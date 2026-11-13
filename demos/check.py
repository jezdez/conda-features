"""Check the same real operations as the tapes in a prepared demo shell."""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

from conda_features.steps.packages import installed_records


def main():
    home = Path.home()
    rc = home / "demo/.condarc"
    context = importlib.import_module("conda.base.context")
    assert context.SEARCH_PATH == (str(rc),)
    assert context.reset_context.__defaults__[0] == (str(rc),)
    assert context.Context().solver == "libmamba"
    assert context.Context().channels == ("conda-forge",)
    assert os.environ["CONDA_PKGS_DIRS"].startswith(str(home))
    before = installed_records()

    def run(*args):
        result = subprocess.run(
            [sys.executable, "-m", "conda", "feature", *args, "--json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, "Demo command failed: " + " ".join(args)
        assert not result.stderr, "Demo command produced diagnostics"
        return json.loads(result.stdout)

    run("list")
    run("explain", "conda-pypi")
    original = rc.read_bytes()
    run("enable", "conda-pypi", "--file", str(rc), "--dry-run")
    assert rc.read_bytes() == original
    run("enable", "conda-pypi", "--file", str(rc), "--yes")
    assert "rattler" in rc.read_text()
    run("disable", "conda-pypi", "--file", str(rc), "--yes")
    assert "rattler" not in rc.read_text()
    run("config", "conda-completion", "--file", str(rc), "--get")
    run("config", "conda-completion", "--file", str(rc), "--show")
    run(
        "config",
        "conda-completion",
        "--file",
        str(rc),
        "--set",
        "plugins.feature_completion_shell",
        "zsh",
        "--yes",
    )
    assert "feature_completion_shell: zsh" in rc.read_text()
    run("config", "conda-completion", "--file", str(rc), "--get")
    assert not (home / ".bashrc").exists()
    assert not (home / ".zshrc").exists()
    assert not (home / ".cache/conda-features/completion").exists()
    assert installed_records() == before
    print("Demo isolation and real commands passed.")


if __name__ == "__main__":
    main()
