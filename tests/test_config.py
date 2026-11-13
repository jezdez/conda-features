from __future__ import annotations

import json

import pytest
from conda.base.context import Context
from conda.common.configuration import YamlRawParameter

from conda_features.models import Feature


@pytest.fixture
def config_cli(conda_cli, monkeypatch, tmp_path):
    from conda_features.cli import commands

    feature = Feature(
        "sample",
        "Sample",
        "offline",
        settings=("channel_priority", "remote_read_timeout_secs"),
    )
    monkeypatch.setattr(commands, "discover", lambda: {feature.name: ("test", feature)})
    path = tmp_path / ".condarc"
    path.write_text("# preserve\noffline: false\n")

    def run(*args):
        return conda_cli("feature", *args, "--file", path, "--json")

    return run, path


def test_config_set_preview_and_confirmed_write(config_cli):
    run, path = config_cli
    original = path.read_bytes()
    args = (
        "config",
        "sample",
        "--set",
        "remote_read_timeout_secs",
        "12",
        "--set",
        "channel_priority",
        "strict",
    )
    out, err, code = run(*args, "--dry-run")
    assert code == 0, out + err
    assert json.loads(out)["changes"] == {
        "channel_priority": "strict",
        "remote_read_timeout_secs": 12.0,
    }
    assert path.read_bytes() == original
    out, _, code = run(*args)
    assert code == 1 and "--yes" in out
    assert path.read_bytes() == original
    out, err, code = run(*args, "--yes")
    assert code == 0, out + err
    assert Context(search_path=(path,)).remote_read_timeout_secs == 12
    assert "# preserve" in path.read_text()


@pytest.mark.parametrize(
    "args",
    [
        ("config", "sample"),
        ("config", "sample", "--set", "channel_alias"),
        (
            "config",
            "sample",
            "--set",
            "channel_alias",
            "https://a.test",
            "--set",
            "channel_alias",
            "https://b.test",
        ),
        ("config", "sample", "--set", "quiet", "true"),
        ("config", "sample", "channel_alias=https://a.test"),
    ],
)
def test_invalid_config_input_does_not_write(config_cli, args):
    run, path = config_cli
    original = path.read_bytes()
    try:
        out, err, code = run(*args, "--yes")
    except SystemExit as exc:
        assert exc.code == 2
    else:
        assert code != 0
    assert path.read_bytes() == original


def test_released_configure_syntax_still_works(config_cli):
    run, path = config_cli
    out, err, code = run("configure", "sample", "remote_read_timeout_secs=12", "--yes")
    assert code == 0, out + err
    assert Context(search_path=(path,)).remote_read_timeout_secs == 12


def test_duplicate_declared_setting_is_rejected(config_cli):
    run, path = config_cli
    original = path.read_bytes()
    out, _, code = run(
        "config",
        "sample",
        "--set",
        "remote_read_timeout_secs",
        "12",
        "--set",
        "remote_read_timeout_secs",
        "20",
        "--yes",
    )
    assert code == 1
    assert "supplied more than once" in json.loads(out)["error"]
    assert path.read_bytes() == original


def test_get_reads_saved_values_while_show_reads_overrides(config_cli, monkeypatch):
    run, path = config_cli
    path.write_text("remote_read_timeout_secs: 12\nquiet: true\n")
    YamlRawParameter.cache_clear()
    monkeypatch.setenv("CONDA_REMOTE_READ_TIMEOUT_SECS", "30")
    before = path.read_bytes()
    out, err, code = run("config", "sample", "--get")
    assert code == 0, out + err
    assert json.loads(out)["values"] == {"remote_read_timeout_secs": 12.0}
    out, err, code = run("config", "sample", "--show", "remote_read_timeout_secs")
    assert code == 0, out + err
    assert json.loads(out)["values"] == {"remote_read_timeout_secs": 30.0}
    assert path.read_bytes() == before


def test_show_sources_filters_values_to_feature_settings(config_cli, monkeypatch):
    run, path = config_cli
    path.write_text(
        "remote_read_timeout_secs: 12\nproxy_servers: {https: DO_NOT_SHOW}\n"
    )
    YamlRawParameter.cache_clear()
    monkeypatch.setenv("CONDA_REMOTE_READ_TIMEOUT_SECS", "30")
    out, err, code = run("config", "sample", "--show-sources")
    assert code == 0, out + err
    result = json.loads(out)
    assert result["sources"][str(path)] == {"remote_read_timeout_secs": 12.0}
    assert result["sources"]["envvars"] == {"remote_read_timeout_secs": 30.0}
    assert "DO_NOT_SHOW" not in out + err
    assert "proxy_servers" not in out


def test_describe_uses_conda_parameter_metadata(config_cli):
    run, _ = config_cli
    out, err, code = run("config", "sample", "--describe", "remote_read_timeout_secs")
    assert code == 0, out + err
    description = json.loads(out)["descriptions"]["remote_read_timeout_secs"]
    expected = Context(search_path=()).describe_parameter("remote_read_timeout_secs")
    assert description["default_value"] == expected["default_value"]
    assert description["element_types"] == list(expected["element_types"])


@pytest.mark.parametrize("option", ["--get", "--show", "--describe", "--remove-key"])
def test_config_options_cannot_access_undeclared_or_enabled_settings(
    config_cli, option
):
    run, path = config_cli
    before = path.read_bytes()
    out, _, code = run("config", "sample", option, "offline", "--yes")
    assert code == 1 and "declared" in out
    assert path.read_bytes() == before


def test_remove_key_previews_confirms_and_reveals_default(config_cli):
    run, path = config_cli
    path.write_text("# keep\nremote_read_timeout_secs: 12\nquiet: true\n")
    YamlRawParameter.cache_clear()
    before = path.read_bytes()
    out, err, code = run(
        "config", "sample", "--remove-key", "remote_read_timeout_secs", "--dry-run"
    )
    assert code == 0, out + err
    assert json.loads(out)["remove"] == ["remote_read_timeout_secs"]
    assert path.read_bytes() == before
    out, _, code = run("config", "sample", "--remove-key", "remote_read_timeout_secs")
    assert code == 1 and "--yes" in out
    out, err, code = run(
        "config", "sample", "--remove-key", "remote_read_timeout_secs", "--yes"
    )
    assert code == 0, out + err
    assert "remote_read_timeout_secs" not in path.read_text()
    assert "# keep" in path.read_text() and "quiet: true" in path.read_text()


def test_validate_inspects_configuration_and_feature_requirements(config_cli):
    run, path = config_cli
    out, err, code = run("config", "sample", "--validate")
    assert code == 0, out + err
    assert json.loads(out)["valid"] is True
    path.write_text("always_copy: true\nalways_softlink: true\n")
    YamlRawParameter.cache_clear()
    out, _, code = run("config", "sample", "--validate")
    assert code == 1
    assert "configuration validation failed" in out


def test_config_actions_are_mutually_exclusive(config_cli):
    run, path = config_cli
    before = path.read_bytes()
    with pytest.raises(SystemExit) as exc:
        run("config", "sample", "--get", "--set", "channel_priority", "strict")
    assert exc.value.code == 2
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "action", ["--get", "--show", "--show-sources", "--describe", "--validate"]
)
def test_config_text_queries_are_read_only(conda_cli, config_cli, action):
    _, path = config_cli
    path.write_text("remote_read_timeout_secs: 12\n")
    YamlRawParameter.cache_clear()
    before = path.read_bytes()
    out, err, code = conda_cli("feature", "config", "sample", action, "--file", path)
    assert code == 0, out + err
    assert "remote_read_timeout_secs" in out or "valid" in out
    assert not err
    assert path.read_bytes() == before


def test_saved_alias_query_and_removal(conda_cli, monkeypatch, tmp_path):
    from conda_features.cli import commands

    feature = Feature("sample", "Sample", "offline", settings=("auto_update_conda",))
    monkeypatch.setattr(commands, "discover", lambda: {"sample": ("test", feature)})
    path = tmp_path / ".condarc"
    path.write_text("self_update: false\n")
    out, err, code = conda_cli(
        "feature", "config", "sample", "--get", "--file", path, "--json"
    )
    assert code == 0, out + err
    assert json.loads(out)["values"] == {"auto_update_conda": False}
    out, err, code = conda_cli(
        "feature",
        "config",
        "sample",
        "--remove-key",
        "auto_update_conda",
        "--file",
        path,
        "--yes",
        "--json",
    )
    assert code == 0, out + err
    assert "self_update" not in path.read_text()


def test_removal_cannot_break_enabled_required_setting(
    conda_cli, monkeypatch, tmp_path
):
    from conda_features.cli import commands

    feature = Feature(
        "sample",
        "Sample",
        "offline",
        settings=("client_ssl_cert",),
        required_settings=("client_ssl_cert",),
    )
    monkeypatch.setattr(commands, "discover", lambda: {"sample": ("test", feature)})
    path = tmp_path / ".condarc"
    path.write_text("offline: true\nclient_ssl_cert: example.pem\n")
    before = path.read_bytes()
    out, _, code = conda_cli(
        "feature",
        "config",
        "sample",
        "--remove-key",
        "client_ssl_cert",
        "--file",
        path,
        "--yes",
        "--json",
    )
    assert code == 1 and "required setting" in out
    assert path.read_bytes() == before


def test_removal_preserves_inherited_configuration_and_checks_stale_plan(tmp_path):
    from conda import CondaError

    feature = Feature(
        "sample", "Sample", "offline", settings=("remote_read_timeout_secs",)
    )
    catalog = {"sample": ("test", feature)}
    inherited = tmp_path / "inherited.yaml"
    inherited.write_text("remote_read_timeout_secs: 30\n")
    path = tmp_path / ".condarc"
    path.write_text("remote_read_timeout_secs: 12\n")
    ctx = Context(search_path=(inherited, path))
    plan = feature.configure(
        catalog, ctx, path, "user", {}, remove_keys=("remote_read_timeout_secs",)
    )
    path.write_text("remote_read_timeout_secs: 15\n")
    with pytest.raises(CondaError, match="changed after preview"):
        feature.apply(plan, ctx)
    YamlRawParameter.cache_clear()
    ctx = Context(search_path=(inherited, path))
    feature.apply(
        feature.configure(
            catalog, ctx, path, "user", {}, remove_keys=("remote_read_timeout_secs",)
        ),
        ctx,
    )
    assert Context(search_path=(inherited, path)).remote_read_timeout_secs == 30
    assert inherited.read_text() == "remote_read_timeout_secs: 30\n"


@pytest.mark.parametrize("json_output", [False, True])
@pytest.mark.parametrize("option", ["--show-sources", "--validate"])
def test_invalid_unrelated_setting_is_never_exposed(
    conda_cli, config_cli, json_output, option
):
    _, path = config_cli
    path.write_text("remote_read_timeout_secs: 12\nssl_verify: PRIVATE_SENTINEL\n")
    YamlRawParameter.cache_clear()
    args = ("--json",) if json_output else ()
    out, err, code = conda_cli(
        "feature", "config", "sample", option, "--file", path, *args
    )
    assert "PRIVATE_SENTINEL" not in out + err
    if option == "--show-sources":
        assert code == 0, out + err
        assert "remote_read_timeout_secs" in out
    else:
        assert code == 1
