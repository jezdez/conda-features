import json

import pytest
from conda import CondaError
from conda.base.context import Context
from conda.common.configuration import YamlRawParameter

from conda_features.models import Feature


def test_declared_steps_preview_apply_and_reverse(tmp_path):
    from conda_features.steps import EnsureChannel, SetSetting

    path = tmp_path / ".condarc"
    path.write_text("# keep\nsolver: libmamba\nchannels: [conda-forge]\n")
    feature = Feature(
        "pypi",
        "PyPI",
        steps=(SetSetting("solver", "rattler"), EnsureChannel("conda-pypi")),
    )
    catalog = {feature.name: ("test", feature)}
    ctx = Context(search_path=(path,))
    before = path.read_bytes()
    plan = feature.enable(catalog, ctx, path, "user")
    assert plan["changes"]["setting:solver"] == "set solver to rattler"
    assert path.read_bytes() == before
    feature.apply(plan, ctx)
    ctx = Context(search_path=(path,))
    assert ctx.solver == "rattler"
    assert "conda-pypi" in ctx.channels
    assert feature.enable(catalog, ctx, path, "user")["changes"] == {}
    feature.apply(feature.disable(catalog, ctx, path, "user"), ctx)
    ctx = Context(search_path=(path,))
    assert ctx.solver == "libmamba"
    assert list(ctx.channels) == ["conda-forge"]
    assert "# keep" in path.read_text()


def test_channel_cleanup_preserves_later_additions(tmp_path):
    from conda_features.steps import EnsureChannel

    path = tmp_path / ".condarc"
    path.write_text("channels: [conda-forge]\n")
    feature = Feature("channel", "Channel", steps=(EnsureChannel("conda-pypi"),))
    catalog = {feature.name: ("test", feature)}
    ctx = Context(search_path=(path,))
    feature.apply(feature.enable(catalog, ctx, path, "user"), ctx)
    path.write_text("channels: [conda-forge, conda-pypi, later]\n")
    YamlRawParameter.cache_clear()
    ctx = Context(search_path=(path,))
    feature.apply(feature.disable(catalog, ctx, path, "user"), ctx)
    assert list(Context(search_path=(path,)).channels) == ["conda-forge", "later"]


def test_steps_preserve_external_settings_and_reject_edits(tmp_path):
    from conda_features.steps import SetSetting

    path = tmp_path / ".condarc"
    path.write_text("offline: true\n")
    feature = Feature("offline", "Offline", steps=(SetSetting("offline", True),))
    catalog = {feature.name: ("test", feature)}
    ctx = Context(search_path=(path,))
    plan = feature.enable(catalog, ctx, path, "user")
    feature.apply(plan, ctx)
    feature.apply(feature.disable(catalog, ctx, path, "user"), ctx)
    assert Context(search_path=(path,)).offline is True

    path.write_text("offline: false\n")
    YamlRawParameter.cache_clear()
    ctx = Context(search_path=(path,))
    feature.apply(feature.enable(catalog, ctx, path, "user"), ctx)
    path.write_text("offline: false\n")
    YamlRawParameter.cache_clear()
    before = path.read_bytes()
    ctx = Context(search_path=(path,))
    feature.apply(feature.disable(catalog, ctx, path, "user"), ctx)
    assert path.read_bytes() == before


def test_completed_step_is_recoverable_when_later_step_fails(tmp_path, monkeypatch):
    from conda_features.steps import EnsureChannel, SetSetting, configuration

    path = tmp_path / ".condarc"
    path.write_text("offline: false\nchannels: [conda-forge]\n")
    feature = Feature(
        "setup",
        "Setup",
        steps=(SetSetting("offline", True), EnsureChannel("conda-pypi")),
    )
    catalog = {feature.name: ("test", feature)}
    ctx = Context(search_path=(path,))
    write = configuration.write_configuration
    count = 0

    def fail_second(*args):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError("disk full")
        write(*args)

    monkeypatch.setattr(configuration, "write_configuration", fail_second)
    with pytest.raises(CondaError, match="channel:conda-pypi"):
        feature.apply(feature.enable(catalog, ctx, path, "user"), ctx)
    assert Context(search_path=(path,)).offline is True
    receipt = json.loads(path.with_name(path.name + ".setup.json").read_text())
    assert "setting:offline" in receipt["steps"]
    monkeypatch.setattr(configuration, "write_configuration", write)
    ctx = Context(search_path=(path,))
    feature.apply(feature.enable(catalog, ctx, path, "user"), ctx)
    ctx = Context(search_path=(path,))
    feature.apply(feature.disable(catalog, ctx, path, "user"), ctx)
    assert Context(search_path=(path,)).offline is False


def test_step_validation_rejects_duplicate_ids(tmp_path):
    from conda_features.operations.discovery import validate_catalog
    from conda_features.steps import SetSetting

    feature = Feature(
        "dup",
        "Duplicate",
        steps=(SetSetting("offline", True), SetSetting("offline", False)),
    )
    with pytest.raises(CondaError, match="Duplicate step"):
        validate_catalog({"dup": ("test", feature)}, Context(search_path=()))


def test_legacy_receipt_is_not_reinterpreted(tmp_path):
    from conda_features.steps import SetSetting

    path = tmp_path / ".condarc"
    path.write_text("offline: true\n")
    receipt = path.with_name(path.name + ".old.json")
    receipt.write_text(
        '{"before": {}, "after": {"offline": true}, "owned": ["offline"]}'
    )
    feature = Feature("old", "Old", steps=(SetSetting("offline", True),))
    original = receipt.read_bytes()
    with pytest.raises(CondaError, match="previous provider version"):
        feature.disable(
            {"old": ("test", feature)}, Context(search_path=(path,)), path, "user"
        )
    assert receipt.read_bytes() == original
    assert path.read_text() == "offline: true\n"


def test_disable_retries_after_receipt_write_failure(tmp_path, monkeypatch):
    from conda_features.steps import SetSetting, runner

    path = tmp_path / ".condarc"
    path.write_text("offline: false\n")
    feature = Feature("recover", "Recover", steps=(SetSetting("offline", True),))
    catalog = {feature.name: ("test", feature)}
    ctx = Context(search_path=(path,))
    feature.apply(feature.enable(catalog, ctx, path, "user"), ctx)
    ctx = Context(search_path=(path,))
    write = runner.write_receipt

    def fail(*args):
        raise OSError("receipt failed")

    monkeypatch.setattr(runner, "write_receipt", fail)
    with pytest.raises(CondaError, match="receipt failed"):
        feature.apply(feature.disable(catalog, ctx, path, "user"), ctx)
    monkeypatch.setattr(runner, "write_receipt", write)
    ctx = Context(search_path=(path,))
    assert ctx.offline is False
    feature.apply(feature.disable(catalog, ctx, path, "user"), ctx)


def test_channel_cleanup_restores_absent_local_setting(tmp_path):
    from conda.common.serialize import yaml

    from conda_features.steps import EnsureChannel

    path = tmp_path / ".condarc"
    path.write_text("{}\n")
    inherited = tmp_path / "inherited.yaml"
    inherited.write_text("channels: [conda-forge]\n")
    feature = Feature("channel", "Channel", steps=(EnsureChannel("test-channel"),))
    catalog = {feature.name: ("test", feature)}
    ctx = Context(search_path=(inherited, path))
    feature.apply(feature.enable(catalog, ctx, path, "user"), ctx)
    ctx = Context(search_path=(inherited, path))
    feature.apply(feature.disable(catalog, ctx, path, "user"), ctx)
    assert "channels" not in yaml.read(path=path)


@pytest.mark.parametrize("kind", ["channels", "packages", "setting"])
def test_duplicate_resource_writers_are_rejected(kind):
    from conda_features.operations.discovery import validate_catalog
    from conda_features.steps import EnsureChannel, InstallPackages, SetSetting

    steps = {
        "channels": (EnsureChannel("a"), EnsureChannel("b")),
        "packages": (InstallPackages("a"), InstallPackages("b")),
        "setting": (SetSetting("offline", True), SetSetting("offline", False)),
    }[kind]
    feature = Feature("duplicate", "Duplicate", steps=steps)
    with pytest.raises(CondaError, match="Duplicate"):
        validate_catalog({feature.name: ("test", feature)}, Context(search_path=()))


def test_step_conflicts_do_not_recurse(tmp_path):
    from conda_features.steps import SetSetting

    path = tmp_path / ".condarc"
    path.write_text("offline: true\nquiet: true\n")
    first = Feature(
        "first", "First", steps=(SetSetting("offline", True),), conflicts=("second",)
    )
    second = Feature("second", "Second", steps=(SetSetting("quiet", True),))
    catalog = {item.name: ("test", item) for item in (first, second)}
    for item in (first, second):
        result = item.status(catalog, Context(search_path=(path,)), "user", path=path)
        assert result["readiness"] == "blocked"
        assert any("conflict" in reason for reason in result["reasons"])


def test_step_setting_owners_are_unique():
    from conda_features.operations.discovery import validate_catalog
    from conda_features.steps import SetSetting

    features = [
        Feature(name, name, steps=(SetSetting("offline", True),))
        for name in ("first", "second")
    ]
    with pytest.raises(CondaError, match="declared more than once"):
        validate_catalog(
            {item.name: ("test", item) for item in features}, Context(search_path=())
        )


def test_required_configuration_is_checked_before_deployment(tmp_path):
    from conda_features.steps import SetSetting

    path = tmp_path / ".condarc"
    path.write_text("{}\n")
    feature = Feature(
        "required",
        "Required",
        steps=(SetSetting("offline", True),),
        settings=("client_ssl_cert",),
        required_settings=("client_ssl_cert",),
    )
    with pytest.raises(CondaError, match="client_ssl_cert"):
        feature.enable(
            {feature.name: ("test", feature)},
            Context(search_path=(path,)),
            path,
            "user",
        )
