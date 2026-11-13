from io import StringIO
from pathlib import Path

import pytest
from conda.base.context import Context
from conda.common.configuration import YamlRawParameter
from conda.common.serialize import yaml

from conda_features.models import Feature


@pytest.fixture
def feature_cli(conda_cli, monkeypatch, tmp_path):
    from conda_features.cli import commands

    feature = Feature(
        "sample",
        "Use cached packages",
        "offline",
        maturity="stable",
        scopes=("user", "system"),
        settings=("channel_alias",),
        guidance="Use cached packages offline.",
    )
    catalog = {feature.name: ("test-provider", feature)}
    monkeypatch.setattr(commands, "discover", lambda: catalog)
    path = tmp_path / ".condarc"
    path.write_text("# preserve\noffline: false\n")

    def run(*args):
        return conda_cli("feature", *args, "--file", path)

    return run, path, catalog


def test_text_listing_and_explanation(feature_cli):
    run, path, _ = feature_cli
    out, err, code = run("list")
    assert code == 0 and not err
    for value in ("sample", "stable", "disabled", "ready", "Use cached packages"):
        assert value in out
    out, err, code = run("explain", "sample")
    assert code == 0 and not err
    for text in (
        "sample: Use cached packages",
        "Provider: test-provider",
        "Maturity: stable",
        "Requested: disabled",
        "Effective setting: disabled",
        "Runtime: unknown (provider execution is not observed)",
        "Readiness: ready",
        f"offline: sources {path}",
        "channel_alias: sources default",
        "Configurable settings: channel_alias",
        "Use cached packages offline.",
    ):
        assert text in out


def test_text_empty_catalog_and_error(conda_cli):
    out, err, code = conda_cli("feature", "list")
    assert code == 0 and not err
    assert out.strip() == "No feature providers installed."
    out, err, code = conda_cli("feature", "explain", "missing")
    assert code == 1 and not out
    assert "Unknown feature: missing" in err


def test_text_preview_and_idempotent_apply(feature_cli):
    run, path, _ = feature_cli
    before = path.read_bytes()
    out, err, code = run("enable", "sample", "--dry-run")
    assert code == 0 and not err
    assert f"Configuration: {path} (user)" in out
    assert "offline = True" in out
    assert "Preview only. No changes made." in out
    assert path.read_bytes() == before
    out, err, code = run("enable", "sample", "--yes")
    assert code == 0 and not err
    assert "Configuration updated." in out
    persisted = path.read_bytes()
    out, err, code = run("enable", "sample", "--yes")
    assert code == 0 and not err
    assert "No changes needed." in out
    assert path.read_bytes() == persisted


@pytest.mark.parametrize(
    "answer, accepted",
    [("y\n", True), (" YES \n", True), ("n\n", False), ("\n", False), ("", False)],
)
def test_interactive_confirmation_controls_write(
    feature_cli, monkeypatch, answer, accepted
):
    class TerminalInput(StringIO):
        def isatty(self):
            return True

    run, path, _ = feature_cli
    before = path.read_bytes()
    monkeypatch.setattr("sys.stdin", TerminalInput(answer))
    out, err, code = run("enable", "sample")
    assert "Proceed? [y/N]" in err
    assert f"Configuration: {path} (user)" in err
    assert "offline = True" in err
    if accepted:
        assert code == 0
        assert "Configuration updated." in out
        assert yaml.read(path=path)["offline"] is True
        assert "# preserve" in path.read_text()
    else:
        assert code == 1 and not out
        assert "Cancelled. No changes made." in err
        assert path.read_bytes() == before


def test_noninteractive_text_requires_confirmation(feature_cli, monkeypatch):
    run, path, _ = feature_cli
    before = path.read_bytes()
    monkeypatch.setattr("sys.stdin", StringIO("yes\n"))
    out, err, code = run("enable", "sample")
    assert code == 1 and not out
    assert "pass --yes" in err
    assert path.read_bytes() == before


def test_explanation_shows_missing_dependency(feature_cli):
    from dataclasses import replace

    run, _, catalog = feature_cli
    provider, feature = catalog["sample"]
    catalog["sample"] = (
        provider,
        replace(
            feature,
            requires=("missing",),
            settings=(),
            required_settings=(),
            guidance="",
        ),
    )
    out, err, code = run("explain", "sample")
    assert code == 0 and not err
    assert "Readiness: blocked" in out
    assert "Missing dependency: missing." in out
    assert "Configurable settings:" not in out


def test_missing_required_setting_has_actionable_guidance(feature_cli):
    from dataclasses import replace

    run, path, catalog = feature_cli
    provider, feature = catalog["sample"]
    catalog["sample"] = (
        provider,
        replace(feature, required_settings=("channel_alias",)),
    )
    before = path.read_bytes()
    out, err, code = run("explain", "sample")
    assert code == 0 and not err
    assert "Readiness: setup required" in out
    assert "Configure required setting channel_alias." in out
    out, err, code = run("enable", "sample", "--yes")
    assert code == 1 and not out
    assert "Configure required setting channel_alias." in err
    assert path.read_bytes() == before


def test_system_scope_changes_only_temporary_installation(
    feature_cli, conda_cli, monkeypatch, tmp_path
):
    user_path = Path.home() / ".condarc"
    user_path.write_text("# user configuration\noffline: false\n")
    root = tmp_path / "installation"
    root.mkdir()
    system_path = root / ".condarc"
    system_path.write_text("offline: false\n")
    before = user_path.read_bytes()
    monkeypatch.setattr(Context, "root_prefix", property(lambda self: str(root)))
    import importlib

    monkeypatch.setattr(
        importlib.import_module("conda.base.context"),
        "SEARCH_PATH",
        (str(system_path),),
    )
    out, err, code = conda_cli("feature", "enable", "sample", "--system", "--yes")
    assert code == 0, err
    assert f"Configuration: {system_path} (system)" in out
    assert yaml.read(path=system_path)["offline"] is True
    assert user_path.read_bytes() == before
    YamlRawParameter.cache_clear()
    assert Context(search_path=(system_path,)).offline is True
