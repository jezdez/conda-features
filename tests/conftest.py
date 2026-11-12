import importlib
import os

import pytest
from conda.base.context import reset_context
from conda.testing.fixtures import (  # noqa: F401
    conda_cli,
    context_aware_monkeypatch,
    empty_env,
    path_factory,
    reset_conda_context,
    tmp_env,
)


@pytest.fixture(autouse=True)
def isolated_conda(monkeypatch, tmp_path, request):
    request.getfixturevalue("reset_conda_context")
    for key in tuple(os.environ):
        if key.startswith("CONDA_") or key == "CONDARC":
            monkeypatch.delenv(key)
    rc = tmp_path / "condarc"
    rc.write_text("{}\n")
    monkeypatch.setenv("CONDARC", str(rc))
    monkeypatch.setenv("CONDA_NO_PLUGINS", "false")
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    module = importlib.import_module("conda.base.context")
    monkeypatch.setattr(
        module, "SEARCH_PATH", ("~/.condarc", "$CONDA_PREFIX/.condarc", "$CONDARC")
    )
    monkeypatch.setattr(module, "user_rc_path", str(home / ".condarc"))
    reset_context(search_path=())
