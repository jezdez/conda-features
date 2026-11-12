from dataclasses import replace
from pathlib import Path

import pytest
from conda import CondaError
from conda.base.context import Context
from conda.common.configuration import YamlRawParameter

from conda_features.models import Feature
from conda_features.operations import configuration as operations


@pytest.fixture
def setup(tmp_path):
    path = tmp_path / ".condarc"
    path.write_text("# keep this comment\nchannels:\n  - conda-forge\n")
    feature = Feature(
        "offline-mode", "Use cached packages", "offline", scopes=("user", "environment")
    )
    catalog = {feature.name: ("test-provider", feature)}
    return path, catalog, Context(search_path=(path,))


def test_preview_does_not_write_and_apply_preserves_unrelated_config(setup):
    path, catalog, ctx = setup
    original = path.read_bytes()
    plan = catalog["offline-mode"][1].enable(catalog, ctx, path, "user")
    assert plan["changes"] == {"offline": True}
    assert path.read_bytes() == original
    operations.apply_change(plan, ctx)
    assert "# keep this comment" in path.read_text()
    assert "conda-forge" in path.read_text()
    assert Context(search_path=(path,)).offline is True
    assert (
        catalog["offline-mode"][1].enable(
            catalog, Context(search_path=(path,)), path, "user"
        )["changes"]
        == {}
    )


def test_stale_plan_does_not_overwrite_another_edit(setup):
    path, catalog, ctx = setup
    plan = operations.plan_change(catalog, ctx, path, "user", "enable", "offline-mode")
    path.write_text("offline: false\nquiet: true\n")
    with pytest.raises(CondaError, match="changed"):
        operations.apply_change(plan, ctx)
    assert path.read_text() == "offline: false\nquiet: true\n"


def test_failed_atomic_replace_preserves_original(setup, monkeypatch):
    path, catalog, ctx = setup
    original = path.read_bytes()
    plan = operations.plan_change(catalog, ctx, path, "user", "enable", "offline-mode")

    def fail(*args):
        raise OSError("disk failure")

    monkeypatch.setattr("os.replace", fail)
    with pytest.raises(CondaError, match="write"):
        operations.apply_change(plan, ctx)
    assert path.read_bytes() == original


def test_configuration_override_blocks_ineffective_enable(setup, monkeypatch):
    path, catalog, _ = setup
    monkeypatch.setenv("CONDA_OFFLINE", "false")
    ctx = Context(search_path=(path,))
    with pytest.raises(CondaError, match="overrid"):
        operations.plan_change(catalog, ctx, path, "user", "enable", "offline-mode")


def test_missing_dependency_and_cycles_are_actionable(setup):
    path, catalog, ctx = setup
    provider, feature = catalog["offline-mode"]
    catalog[feature.name] = (provider, replace(feature, requires=("missing",)))
    with pytest.raises(CondaError, match="missing"):
        operations.plan_change(catalog, ctx, path, "user", "enable", feature.name)
    catalog[feature.name] = (provider, replace(feature, requires=(feature.name,)))
    with pytest.raises(CondaError, match="cycle"):
        operations.plan_change(catalog, ctx, path, "user", "enable", feature.name)


def test_dependency_safe_disable_and_bulk_disable(setup):
    path, catalog, _ = setup
    path.write_text("offline: true\nquiet: true\n")
    YamlRawParameter.cache_clear()
    catalog["quiet-mode"] = (
        "test-provider",
        Feature("quiet-mode", "Quiet output", "quiet", requires=("offline-mode",)),
    )
    ctx = Context(search_path=(path,))
    with pytest.raises(CondaError, match="quiet-mode"):
        operations.plan_change(catalog, ctx, path, "user", "disable", "offline-mode")
    plan = operations.plan_change(
        catalog, ctx, path, "user", "disable", None, all_features=True
    )
    assert list(plan["changes"]) == ["quiet", "offline"]
    operations.apply_change(plan, ctx)
    assert Context(search_path=(path,)).quiet is False
    assert Context(search_path=(path,)).offline is False


@pytest.mark.parametrize(
    "updates, match",
    [
        ({"maturity": "oops"}, "maturity"),
        ({"scopes": ("environment",)}, "scope"),
        ({"retired": True}, "retired"),
        ({"platforms": ("unsupported",)}, "platform"),
        ({"conda_version": ">=999"}, "conda"),
        ({"enabled_setting": "channels"}, "boolean"),
    ],
)
def test_reject_invalid_or_unavailable_features(setup, updates, match):
    path, catalog, ctx = setup
    provider, feature = catalog["offline-mode"]
    catalog[feature.name] = (provider, replace(feature, **updates))
    with pytest.raises(CondaError, match=match):
        operations.plan_change(catalog, ctx, path, "user", "enable", feature.name)


def test_conflict_is_checked_in_both_directions(setup):
    path, catalog, _ = setup
    path.write_text("quiet: true\n")
    YamlRawParameter.cache_clear()
    catalog["quiet-mode"] = (
        "test-provider",
        Feature("quiet-mode", "Quiet output", "quiet", conflicts=("offline-mode",)),
    )
    with pytest.raises(CondaError, match="conflict"):
        operations.plan_change(
            catalog,
            Context(search_path=(path,)),
            path,
            "user",
            "enable",
            "offline-mode",
        )


def test_configure_uses_conda_validation_and_allowlist(setup):
    path, catalog, ctx = setup
    provider, feature = catalog["offline-mode"]
    catalog[feature.name] = (provider, replace(feature, settings=("channel_priority",)))
    plan = catalog[feature.name][1].configure(
        catalog, ctx, path, "user", {"channel_priority": "strict"}
    )
    operations.apply_change(plan, ctx)
    assert str(Context(search_path=(path,)).channel_priority) == "strict"
    with pytest.raises(CondaError):
        operations.plan_change(
            catalog,
            ctx,
            path,
            "user",
            "configure",
            feature.name,
            settings={"channel_priority": "invalid"},
        )
    with pytest.raises(CondaError, match="declared"):
        operations.plan_change(
            catalog,
            ctx,
            path,
            "user",
            "configure",
            feature.name,
            settings={"proxy_servers": "secret"},
        )


def test_status_reports_requested_state_and_unmet_prerequisite(setup):
    path, catalog, _ = setup
    provider, feature = catalog["offline-mode"]
    catalog[feature.name] = (provider, replace(feature, requires=("missing",)))
    path.write_text("offline: true\n")
    YamlRawParameter.cache_clear()
    result = catalog[feature.name][1].status(
        catalog, Context(search_path=(path,)), "user", path=path
    )
    assert result["requested"] == "enabled"
    assert result["effective"] == "enabled"
    assert result["runtime"] == "unknown"
    assert result["readiness"] == "blocked"
    assert "missing" in " ".join(result["reasons"])
    assert result["sources"]["offline"] == [str(path)]


def test_saved_choice_recognizes_conda_alias(setup):
    path, _, _ = setup
    path.write_text("self_update: false\n")
    YamlRawParameter.cache_clear()
    feature = Feature("updates", "Updates", "auto_update_conda")
    result = feature.status(
        {"updates": ("test", feature)}, Context(search_path=(path,)), "user", path=path
    )
    assert result["requested"] == "disabled"


def test_final_config_setting_prevents_override(setup, tmp_path):
    path, catalog, _ = setup
    enforced = tmp_path / "enforced.yaml"
    enforced.write_text("offline: false  #!final\n")
    ctx = Context(search_path=(enforced, path))
    original = path.read_bytes()
    with pytest.raises(CondaError, match="overrid"):
        operations.plan_change(catalog, ctx, path, "user", "enable", "offline-mode")
    assert path.read_bytes() == original


def test_symlink_target_is_not_replaced(setup, tmp_path):
    path, catalog, ctx = setup
    link = tmp_path / "linked.yaml"
    link.symlink_to(path)
    original = path.read_bytes()
    with pytest.raises(CondaError, match="symbolic"):
        operations.plan_change(catalog, ctx, link, "user", "enable", "offline-mode")
    assert link.is_symlink()
    assert path.read_bytes() == original


def test_retired_feature_can_still_be_disabled(setup):
    path, catalog, _ = setup
    path.write_text("offline: true\n")
    YamlRawParameter.cache_clear()
    provider, feature = catalog["offline-mode"]
    catalog[feature.name] = (provider, replace(feature, retired=True))
    ctx = Context(search_path=(path,))
    plan = catalog[feature.name][1].disable(catalog, ctx, path, "user")
    operations.apply_change(plan, ctx)
    assert Context(search_path=(path,)).offline is False


def test_disable_persists_despite_temporary_override(setup, monkeypatch):
    path, catalog, _ = setup
    path.write_text("offline: true\n")
    YamlRawParameter.cache_clear()
    monkeypatch.setenv("CONDA_OFFLINE", "false")
    ctx = Context(search_path=(path,))
    plan = operations.plan_change(catalog, ctx, path, "user", "disable", "offline-mode")
    assert plan["changes"] == {"offline": False}
    operations.apply_change(plan, ctx)
    monkeypatch.delenv("CONDA_OFFLINE")
    assert Context(search_path=(path,)).offline is False


def test_cross_setting_validation_prevents_invalid_configuration(setup):
    path, _, _ = setup
    path.write_text("always_softlink: true\n")
    YamlRawParameter.cache_clear()
    catalog = {
        "copy-mode": (
            "test",
            Feature("copy-mode", "Copy", "offline", settings=("always_copy",)),
        )
    }
    with pytest.raises(CondaError):
        operations.plan_change(
            catalog,
            Context(search_path=(path,)),
            path,
            "user",
            "configure",
            "copy-mode",
            settings={"always_copy": "true"},
        )


def test_disable_all_recovers_from_dependency_cycle(setup):
    path, catalog, _ = setup
    path.write_text("offline: true\n")
    YamlRawParameter.cache_clear()
    provider, feature = catalog["offline-mode"]
    catalog[feature.name] = (provider, replace(feature, requires=(feature.name,)))
    ctx = Context(search_path=(path,))
    plan = operations.plan_change(
        catalog, ctx, path, "user", "disable", None, all_features=True
    )
    operations.apply_change(plan, ctx)
    assert Context(search_path=(path,)).offline is False


def test_missing_user_config_keeps_lower_priority_than_environment(
    setup, monkeypatch, empty_env
):
    _, catalog, _ = setup
    monkeypatch.delenv("CONDARC")
    monkeypatch.setenv("CONDA_PREFIX", str(empty_env))
    (empty_env / ".condarc").write_text("offline: false\n")
    path = Path.home() / ".condarc"
    assert not path.exists()
    with pytest.raises(CondaError, match="overrid"):
        operations.plan_change(
            catalog, Context(), path, "user", "enable", "offline-mode"
        )


@pytest.mark.parametrize(
    "extra",
    [
        {"requires": ("offline-mode", "missing")},
        {"retired": True},
        {"conda_version": ">=999"},
    ],
)
def test_blocked_enabled_dependent_still_protects_prerequisite(setup, extra):
    path, catalog, _ = setup
    dependent = replace(
        Feature("dependent", "Dependent", "quiet", requires=("offline-mode",)), **extra
    )
    catalog[dependent.name] = ("test", dependent)
    path.write_text("offline: true\nquiet: true\n")
    YamlRawParameter.cache_clear()
    ctx = Context(search_path=(path,))
    before = path.read_bytes()
    with pytest.raises(CondaError, match="dependent.*requires.*offline-mode"):
        catalog["offline-mode"][1].disable(catalog, ctx, path, "user")
    assert path.read_bytes() == before
    plan = operations.plan_change(
        catalog, ctx, path, "user", "disable", None, all_features=True
    )
    operations.apply_change(plan, ctx)
    assert Context(search_path=(path,)).offline is False
    assert Context(search_path=(path,)).quiet is False


@pytest.mark.parametrize(
    "extra", [{"retired": True}, {"requires": ("missing",)}, {"conda_version": ">=999"}]
)
def test_blocked_feature_does_not_claim_runtime_suppression(setup, extra):
    path, catalog, _ = setup
    provider, feature = catalog["offline-mode"]
    feature = replace(feature, **extra)
    catalog[feature.name] = (provider, feature)
    path.write_text("offline: true\n")
    YamlRawParameter.cache_clear()
    result = feature.status(catalog, Context(search_path=(path,)), "user", path=path)
    assert result["requested"] == "enabled"
    assert result["effective"] == "enabled"
    assert result["runtime"] == "unknown"
    assert result["readiness"] == "blocked"


def test_saved_choice_is_distinct_from_effective_override(setup, monkeypatch):
    path, catalog, _ = setup
    monkeypatch.setenv("CONDA_OFFLINE", "true")
    feature = catalog["offline-mode"][1]
    ctx = Context(search_path=(path,))
    result = feature.status(catalog, ctx, "user", path=path)
    assert result["requested"] == "unset"
    assert result["effective"] == "enabled"
    path.write_text("offline: false\n")
    YamlRawParameter.cache_clear()
    result = feature.status(catalog, Context(search_path=(path,)), "user", path=path)
    assert result["requested"] == "disabled"
    assert result["effective"] == "enabled"
