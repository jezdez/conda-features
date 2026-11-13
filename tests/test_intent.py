from __future__ import annotations

import json

import pytest
from conda.base.context import Context

from conda_features.models import Feature


@pytest.fixture
def intent_catalog(monkeypatch):
    from conda_features.cli import commands

    feature = Feature(
        "sample",
        "Sample",
        "offline",
        scopes=("user", "environment"),
        settings=("remote_read_timeout_secs", "client_ssl_cert"),
        portable_settings=("remote_read_timeout_secs",),
    )
    catalog = {feature.name: ("provider", feature)}
    monkeypatch.setattr(commands, "discover", lambda: catalog)
    return catalog


def test_export_only_saved_portable_intent(conda_cli, intent_catalog, tmp_path):
    path = tmp_path / ".condarc"
    path.write_text(
        "offline: true\nremote_read_timeout_secs: 17\nclient_ssl_cert: /private/secret.pem\nproxy_servers: {https: password}\n"
    )
    out, err, code = conda_cli("feature", "export", "--file", path)
    assert code == 0, out + err
    data = json.loads(out)
    assert data == {
        "version": 1,
        "scope": "user",
        "features": [
            {
                "name": "sample",
                "provider": "provider",
                "requested": "enabled",
                "settings": {"remote_read_timeout_secs": 17.0},
            }
        ],
    }
    assert "secret" not in out and "password" not in out and str(path) not in out


def test_apply_intent_roundtrip_requires_preview_confirmation(
    conda_cli, intent_catalog, tmp_path
):
    source = tmp_path / "source.yaml"
    source.write_text("offline: true\nremote_read_timeout_secs: 17\n")
    out, _, _ = conda_cli("feature", "export", "--file", source)
    manifest = tmp_path / "intent.json"
    manifest.write_text(out)
    target = tmp_path / "target.yaml"
    target.write_text("# keep\nquiet: true\n")
    original = target.read_bytes()
    out, err, code = conda_cli(
        "feature", "apply", manifest, "--file", target, "--dry-run", "--json"
    )
    assert code == 0, out + err
    assert json.loads(out)["changes"] == {
        "offline": True,
        "remote_read_timeout_secs": 17.0,
    }
    assert target.read_bytes() == original
    out, _, code = conda_cli("feature", "apply", manifest, "--file", target, "--json")
    assert code == 1 and "--yes" in out
    out, err, code = conda_cli(
        "feature", "apply", manifest, "--file", target, "--yes", "--json"
    )
    assert code == 0, out + err
    ctx = Context(search_path=(target,))
    assert ctx.offline and ctx.quiet
    assert ctx.remote_read_timeout_secs == 17
    assert "# keep" in target.read_text()


@pytest.mark.parametrize(
    "entry",
    [
        {
            "name": "missing",
            "provider": "provider",
            "requested": "enabled",
            "settings": {},
        },
        {"name": "sample", "provider": "wrong", "requested": "enabled", "settings": {}},
        {
            "name": "sample",
            "provider": "provider",
            "requested": "enabled",
            "settings": {"client_ssl_cert": "secret"},
        },
    ],
)
def test_invalid_intent_is_rejected_without_writing(
    conda_cli, intent_catalog, tmp_path, entry
):
    manifest = tmp_path / "intent.json"
    manifest.write_text(
        json.dumps({"version": 1, "scope": "user", "features": [entry]})
    )
    target = tmp_path / "target.yaml"
    target.write_text("{}\n")
    out, _, code = conda_cli(
        "feature", "apply", manifest, "--file", target, "--yes", "--json"
    )
    assert code == 1
    assert target.read_text() == "{}\n"


def test_apply_requires_explicit_destination(conda_cli, intent_catalog, tmp_path):
    manifest = tmp_path / "intent.json"
    manifest.write_text('{"version": 1, "scope": "user", "features": []}')
    out, _, code = conda_cli("feature", "apply", manifest, "--yes", "--json")
    assert code == 1 and "explicit" in out


def test_export_omits_authenticated_urls(conda_cli, intent_catalog, tmp_path):
    from dataclasses import replace

    provider, feature = intent_catalog["sample"]
    intent_catalog["sample"] = (
        provider,
        replace(
            feature, settings=("channel_alias",), portable_settings=("channel_alias",)
        ),
    )
    source = tmp_path / "source.yaml"
    source.write_text(
        "offline: true\nchannel_alias: https://user:password@example.test/channel\n"
    )
    out, _, code = conda_cli("feature", "export", "--file", source)
    assert code == 1
    assert "password" not in out


@pytest.mark.parametrize(
    "updates",
    [
        {"retired": True},
        {"replacement": "new"},
        {"graduation": "unconditional"},
        {"conda_version": ">=999"},
        {"platforms": ("unsupported",)},
    ],
)
def test_apply_refuses_incompatible_or_obsolete_feature(
    conda_cli, intent_catalog, tmp_path, updates
):
    from dataclasses import replace

    provider, feature = intent_catalog["sample"]
    intent_catalog["sample"] = (provider, replace(feature, **updates))
    manifest = tmp_path / "intent.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "scope": "user",
                "features": [
                    {
                        "name": "sample",
                        "provider": "provider",
                        "requested": "enabled",
                        "settings": {},
                    }
                ],
            }
        )
    )
    target = tmp_path / "target.yaml"
    target.write_text("{}\n")
    out, _, code = conda_cli(
        "feature", "apply", manifest, "--file", target, "--yes", "--json"
    )
    assert code == 1 and "error" in json.loads(out)
    assert target.read_text() == "{}\n"


@pytest.mark.parametrize(
    "document",
    [
        [],
        {},
        {"version": 2, "scope": "user", "features": []},
        {"version": 1, "scope": "user", "features": "bad"},
        {"version": 1, "scope": "user", "features": [{"name": []}]},
    ],
)
def test_invalid_manifest_shapes_fail_cleanly(
    conda_cli, intent_catalog, tmp_path, document
):
    manifest = tmp_path / "intent.json"
    manifest.write_text(json.dumps(document))
    target = tmp_path / "target.yaml"
    target.write_text("{}\n")
    out, _, code = conda_cli(
        "feature", "apply", manifest, "--file", target, "--yes", "--json"
    )
    assert code == 1 and "error" in json.loads(out)
    assert target.read_text() == "{}\n"


def test_combined_intent_dependencies_and_conflicts(
    conda_cli, intent_catalog, tmp_path
):
    intent_catalog["dependent"] = (
        "provider",
        Feature("dependent", "Dependent", "quiet", requires=("sample",)),
    )
    target = tmp_path / "target.yaml"
    target.write_text("{}\n")
    manifest = tmp_path / "intent.json"
    entries = [
        {"name": name, "provider": "provider", "requested": "enabled", "settings": {}}
        for name in ("dependent", "sample")
    ]
    manifest.write_text(
        json.dumps({"version": 1, "scope": "user", "features": entries})
    )
    out, err, code = conda_cli(
        "feature", "apply", manifest, "--file", target, "--yes", "--json"
    )
    assert code == 0, out + err
    assert (
        Context(search_path=(target,)).offline and Context(search_path=(target,)).quiet
    )
    entries[1]["requested"] = "disabled"
    manifest.write_text(
        json.dumps({"version": 1, "scope": "user", "features": entries})
    )
    before = target.read_bytes()
    out, _, code = conda_cli(
        "feature", "apply", manifest, "--file", target, "--yes", "--json"
    )
    assert code == 1
    assert target.read_bytes() == before


@pytest.mark.parametrize(
    "setting",
    [
        "/home/private/file",
        "C:\\Users\\private\\file",
        "https://host/t/secret/channel",
        "https://host/path?token=secret",
    ],
)
def test_portable_settings_reject_host_paths_and_tokens(
    conda_cli, intent_catalog, tmp_path, setting
):
    from dataclasses import replace

    provider, feature = intent_catalog["sample"]
    intent_catalog["sample"] = (
        provider,
        replace(
            feature, settings=("channel_alias",), portable_settings=("channel_alias",)
        ),
    )
    manifest = tmp_path / "intent.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "scope": "user",
                "features": [
                    {
                        "name": "sample",
                        "provider": "provider",
                        "requested": "enabled",
                        "settings": {"channel_alias": setting},
                    }
                ],
            }
        )
    )
    target = tmp_path / "target.yaml"
    target.write_text("{}\n")
    out, _, code = conda_cli(
        "feature", "apply", manifest, "--file", target, "--yes", "--json"
    )
    assert code == 1
    assert "secret" not in out and "private" not in out


@pytest.mark.parametrize("operation", ["export", "apply"])
def test_intent_errors_do_not_echo_unrelated_credentials(
    conda_cli, intent_catalog, tmp_path, operation
):
    target = tmp_path / "target.yaml"
    target.write_text(
        "offline: true\nproxy_servers: https://user:DO_NOT_PRINT@example.test\n"
    )
    args = ["feature", operation]
    if operation == "apply":
        manifest = tmp_path / "intent.json"
        manifest.write_text(
            json.dumps(
                {
                    "version": 1,
                    "scope": "user",
                    "features": [
                        {
                            "name": "sample",
                            "provider": "provider",
                            "requested": "enabled",
                            "settings": {},
                        }
                    ],
                }
            )
        )
        args.append(str(manifest))
    out, err, code = conda_cli(*args, "--file", target, "--json")
    assert code == 1
    assert "DO_NOT_PRINT" not in out + err
    assert "user:" not in out + err


@pytest.mark.parametrize(
    "url",
    [
        "https://[DO_NOT_PRINT]",
        "file:///private/DO_NOT_PRINT",
        "file://localhost/private/DO_NOT_PRINT",
        "file:///C:/DO_NOT_PRINT",
    ],
)
def test_export_rejects_file_urls_and_sanitizes_url_errors(
    conda_cli, intent_catalog, tmp_path, url
):
    from dataclasses import replace

    provider, feature = intent_catalog["sample"]
    intent_catalog["sample"] = (
        provider,
        replace(
            feature, settings=("channel_alias",), portable_settings=("channel_alias",)
        ),
    )
    path = tmp_path / ".condarc"
    path.write_text(f"offline: true\nchannel_alias: '{url}'\n")
    out, err, code = conda_cli("feature", "export", "--file", path, "--json")
    assert code == 1
    assert "DO_NOT_PRINT" not in out + err


@pytest.mark.parametrize(
    "number", ["1e999", 10**400], ids=["float-text", "large-integer"]
)
def test_apply_rejects_numeric_overflow_after_normalization(
    conda_cli, intent_catalog, tmp_path, number
):
    manifest = tmp_path / "intent.json"
    manifest.write_text(
        json.dumps(
            {
                "version": 1,
                "scope": "user",
                "features": [
                    {
                        "name": "sample",
                        "provider": "provider",
                        "requested": "enabled",
                        "settings": {"remote_read_timeout_secs": number},
                    }
                ],
            }
        )
    )
    target = tmp_path / "target.yaml"
    target.write_text("{}\n")
    out, err, code = conda_cli(
        "feature", "apply", manifest, "--file", target, "--yes", "--json"
    )
    assert code == 1
    assert "finite" in out or "Invalid portable value" in out
    assert "Infinity" not in out + err
    assert target.read_text() == "{}\n"
