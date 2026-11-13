from __future__ import annotations

from dataclasses import fields

import pytest

from conda_features.models import Feature


@pytest.mark.parametrize("command", ["export", "apply"])
def test_intent_commands_are_removed(conda_cli, tmp_path, command):
    path = tmp_path / ".condarc"
    path.write_text("offline: true\n")
    manifest = tmp_path / "old-intent.json"
    manifest.write_text('{"version": 1, "scope": "user", "features": []}')
    args = (str(manifest),) if command == "apply" else ()
    with pytest.raises(SystemExit) as exc:
        conda_cli("feature", command, *args, "--file", path, "--yes")
    assert exc.value.code == 2
    assert path.read_text() == "offline: true\n"


def test_feature_has_no_portable_intent_api():
    assert "portable_settings" not in {field.name for field in fields(Feature)}
    assert not hasattr(Feature, "export_intent")
    assert hasattr(Feature, "apply")
