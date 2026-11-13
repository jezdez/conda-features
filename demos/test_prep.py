"""Exercise demo isolation and real commands without recording a terminal."""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path


def test_demo_prep(tmp_path):
    root = Path(__file__).resolve().parents[1]
    existing = set((root / "demos/.scratch").glob("recording.*"))
    home = tmp_path / "original-home"
    home.mkdir()
    (home / ".condarc").write_text("solver: not-a-solver\n")
    (home / ".bashrc").write_text("exit 99\n")
    env = {
        **os.environ,
        "HOME": str(home),
        "CONDARC": str(home / ".condarc"),
        "CONDA_SOLVER": "not-a-solver",
        "CONDA_CHANNELS": "https://invalid.example/private",
        "CONDA_NO_PLUGINS": "true",
        "DEMO_REPO": str(root),
        "BASH_ENV": str(home / ".bashrc"),
        "PROMPT_COMMAND": "exit 98",
        "PYTHONOPTIMIZE": "1",
    }
    result = subprocess.run(
        [
            "env",
            "-u",
            "BASH_ENV",
            "-u",
            "ENV",
            "-u",
            "PROMPT_COMMAND",
            "-u",
            "PYTHONOPTIMIZE",
            "bash",
            "--noprofile",
            "--norc",
            "-c",
            'source "$DEMO_REPO/demos/_prep.sh"\npython "$DEMO_REPO/demos/check.py"',
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == "Demo isolation and real commands passed.\n"
    assert result.stderr == ""
    assert (home / ".condarc").read_text() == "solver: not-a-solver\n"
    assert sorted(path.name for path in home.iterdir()) == [".bashrc", ".condarc"]
    assert set((root / "demos/.scratch").glob("recording.*")) <= existing


def test_demo_task_rejects_shell_syntax():
    root = Path(__file__).resolve().parents[1]
    metadata = tomllib.loads((root / "pyproject.toml").read_text())
    task = metadata["tool"]["pixi"]["feature"]["demos"]["tasks"]["demos"]
    assert task["args"][0]["choices"] == ["", "feature-management", "configuration"]
    result = subprocess.run(
        ["pixi", "run", "--locked", "-e", "demos", "demos", "invalid || exit 0"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "feature-management, configuration" in result.stderr
