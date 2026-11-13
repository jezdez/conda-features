from __future__ import annotations

import json

import pytest
from conda.base.context import Context

from conda_features.models import Feature


@pytest.fixture
def lifecycle_catalog(monkeypatch):
    from conda_features.cli import commands

    old = Feature(
        "old",
        "Old",
        "offline",
        retired=True,
        replacement="new",
        settings=("remote_connect_timeout_secs",),
        migration_settings=(
            ("remote_connect_timeout_secs", "remote_read_timeout_secs"),
        ),
    )
    new = Feature("new", "New", "quiet", settings=("remote_read_timeout_secs",))
    catalog = {feature.name: ("test", feature) for feature in (old, new)}
    monkeypatch.setattr(commands, "discover", lambda: catalog)
    return catalog


def test_migration_preview_confirmation_and_settings(
    lifecycle_catalog, conda_cli, tmp_path
):
    path = tmp_path / ".condarc"
    path.write_text("# preserve\noffline: true\nremote_connect_timeout_secs: 7\n")
    original = path.read_bytes()
    out, err, code = conda_cli(
        "feature", "migrate", "old", "--file", path, "--dry-run", "--json"
    )
    assert code == 0, out + err
    assert json.loads(out)["changes"] == {
        "offline": False,
        "quiet": True,
        "remote_read_timeout_secs": 7.0,
    }
    assert path.read_bytes() == original
    out, _, code = conda_cli("feature", "migrate", "old", "--file", path, "--json")
    assert code == 1 and "--yes" in out
    assert path.read_bytes() == original
    out, err, code = conda_cli(
        "feature", "migrate", "old", "--file", path, "--yes", "--json"
    )
    assert code == 0, out + err
    ctx = Context(search_path=(path,))
    assert not ctx.offline and ctx.quiet
    assert ctx.remote_read_timeout_secs == 7
    assert ctx.remote_connect_timeout_secs == 7
    assert "# preserve" in path.read_text()


def test_migration_preserves_existing_destination_choice(
    lifecycle_catalog, conda_cli, tmp_path
):
    path = tmp_path / ".condarc"
    path.write_text(
        "offline: true\nremote_connect_timeout_secs: 7\nremote_read_timeout_secs: 20\n"
    )
    before = path.read_bytes()
    out, _, code = conda_cli(
        "feature", "migrate", "old", "--file", path, "--yes", "--json"
    )
    assert code == 1 and "already" in out
    assert path.read_bytes() == before


def test_absent_replacement_is_actionable(lifecycle_catalog, conda_cli, tmp_path):
    del lifecycle_catalog["new"]
    path = tmp_path / ".condarc"
    path.write_text("offline: true\n")
    out, _, code = conda_cli(
        "feature", "migrate", "old", "--file", path, "--yes", "--json"
    )
    assert code == 1 and "replacement" in out
    assert path.read_text() == "offline: true\n"


def test_unconditional_graduation_cleanup_is_not_disable(
    conda_cli, monkeypatch, tmp_path
):
    from conda_features.cli import commands

    feature = Feature("graduated", "Graduated", "offline", graduation="unconditional")
    monkeypatch.setattr(commands, "discover", lambda: {feature.name: ("test", feature)})
    path = tmp_path / ".condarc"
    path.write_text("offline: true\nquiet: true\n")
    out, _, code = conda_cli(
        "feature", "disable", "graduated", "--file", path, "--yes", "--json"
    )
    assert code == 1 and "unconditional" in out
    out, err, code = conda_cli(
        "feature", "cleanup", "graduated", "--file", path, "--dry-run", "--json"
    )
    assert code == 0, out + err
    assert json.loads(out)["remove"] == ["offline"]
    assert "offline: true" in path.read_text()
    out, err, code = conda_cli(
        "feature", "cleanup", "graduated", "--file", path, "--yes", "--json"
    )
    assert code == 0, out + err
    assert "offline:" not in path.read_text()
    assert "quiet: true" in path.read_text()


def test_incompatible_migration_setting_fails_before_write(
    lifecycle_catalog, conda_cli, tmp_path
):
    from dataclasses import replace

    provider, old = lifecycle_catalog["old"]
    lifecycle_catalog["old"] = (
        provider,
        replace(
            old,
            settings=("channel_alias",),
            migration_settings=(("channel_alias", "remote_read_timeout_secs"),),
        ),
    )
    path = tmp_path / ".condarc"
    path.write_text("offline: true\nchannel_alias: https://example.test\n")
    before = path.read_bytes()
    out, _, code = conda_cli(
        "feature", "migrate", "old", "--file", path, "--yes", "--json"
    )
    assert code == 1
    assert path.read_bytes() == before


def test_migration_preserves_dependent_requirements(
    lifecycle_catalog, conda_cli, tmp_path
):
    lifecycle_catalog["dependent"] = (
        "test",
        Feature("dependent", "Dependent", "always_copy", requires=("old",)),
    )
    path = tmp_path / ".condarc"
    path.write_text("offline: true\nalways_copy: true\n")
    before = path.read_bytes()
    out, _, code = conda_cli(
        "feature", "migrate", "old", "--file", path, "--yes", "--json"
    )
    assert code == 1 and "still requires" in out
    assert path.read_bytes() == before


def test_optional_graduation_keeps_disable_available(conda_cli, monkeypatch, tmp_path):
    from conda_features.cli import commands

    feature = Feature("optional", "Optional", "offline", graduation="optional")
    monkeypatch.setattr(commands, "discover", lambda: {feature.name: ("test", feature)})
    path = tmp_path / ".condarc"
    path.write_text("offline: true\n")
    out, err, code = conda_cli(
        "feature", "disable", "optional", "--file", path, "--yes", "--json"
    )
    assert code == 0, out + err
    assert not Context(search_path=(path,)).offline


def test_cleanup_rejects_stale_plan_without_removing_user_edit(tmp_path):
    from conda import CondaError

    feature = Feature("graduated", "Graduated", "offline", graduation="unconditional")
    catalog = {feature.name: ("test", feature)}
    path = tmp_path / ".condarc"
    path.write_text("offline: true\n")
    ctx = Context(search_path=(path,))
    plan = feature.cleanup(catalog, ctx, path, "user")
    path.write_text("offline: false\n")
    with pytest.raises(CondaError, match="changed after preview"):
        feature.apply(plan, ctx)
    assert path.read_text() == "offline: false\n"


def test_unconditional_feature_still_blocks_conflicts(tmp_path):
    from conda import CondaError

    base = Feature("base", "Base", "offline", graduation="unconditional")
    other = Feature("other", "Other", "quiet", conflicts=("base",))
    catalog = {item.name: ("test", item) for item in (base, other)}
    path = tmp_path / ".condarc"
    path.write_text("offline: false\n")
    with pytest.raises(CondaError, match="conflict"):
        other.enable(catalog, Context(search_path=(path,)), path, "user")


def test_unconditional_prerequisite_is_not_selected_for_opt_in(
    conda_cli, monkeypatch, tmp_path
):
    from conda_features.cli import commands

    base = Feature("base", "Base", "offline", graduation="unconditional")
    other = Feature("other", "Other", "quiet", requires=("base",))
    catalog = {item.name: ("test", item) for item in (base, other)}
    monkeypatch.setattr(commands, "discover", lambda: catalog)
    path = tmp_path / ".condarc"
    path.write_text("{}\n")
    out, err, code = conda_cli(
        "feature",
        "enable",
        "other",
        "--with-dependencies",
        "--file",
        path,
        "--yes",
        "--json",
    )
    assert code == 0, out + err
    assert json.loads(out)["features"] == ["other"]


def test_matching_destination_alias_is_preserved(
    lifecycle_catalog, conda_cli, tmp_path
):
    from dataclasses import replace

    provider, old = lifecycle_catalog["old"]
    provider2, new = lifecycle_catalog["new"]
    lifecycle_catalog["old"] = (
        provider,
        replace(
            old,
            settings=("always_copy",),
            migration_settings=(("always_copy", "auto_update_conda"),),
        ),
    )
    lifecycle_catalog["new"] = (
        provider2,
        replace(new, settings=("auto_update_conda",)),
    )
    path = tmp_path / ".condarc"
    path.write_text("offline: true\nalways_copy: true\nself_update: true\n")
    out, err, code = conda_cli(
        "feature", "migrate", "old", "--file", path, "--yes", "--json"
    )
    assert code == 0, out + err
    assert "auto_update_conda:" not in path.read_text()
    assert "self_update: true" in path.read_text()


def test_cleanup_removes_saved_alias(conda_cli, monkeypatch, tmp_path):
    from conda_features.cli import commands

    feature = Feature(
        "graduated", "Graduated", "auto_update_conda", graduation="unconditional"
    )
    monkeypatch.setattr(commands, "discover", lambda: {feature.name: ("test", feature)})
    path = tmp_path / ".condarc"
    path.write_text("self_update: true\nquiet: true\n")
    out, err, code = conda_cli(
        "feature", "cleanup", "graduated", "--file", path, "--yes", "--json"
    )
    assert code == 0, out + err
    assert "self_update" not in path.read_text()
    assert "quiet: true" in path.read_text()


def test_migration_transfers_saved_alias(lifecycle_catalog, conda_cli, tmp_path):
    from dataclasses import replace

    provider, old = lifecycle_catalog["old"]
    provider2, new = lifecycle_catalog["new"]
    lifecycle_catalog["old"] = (
        provider,
        replace(
            old,
            settings=("auto_update_conda",),
            migration_settings=(("auto_update_conda", "always_copy"),),
        ),
    )
    lifecycle_catalog["new"] = (provider2, replace(new, settings=("always_copy",)))
    path = tmp_path / ".condarc"
    path.write_text("offline: true\nself_update: true\n")
    out, err, code = conda_cli(
        "feature", "migrate", "old", "--file", path, "--yes", "--json"
    )
    assert code == 0, out + err
    assert Context(search_path=(path,)).always_copy


def test_graduation_cleanup_preserves_dependency_readiness(tmp_path, empty_env):
    from conda_features.operations.dependencies import check_affected

    base = Feature("base", "Base", "offline", graduation="unconditional")
    dependent = Feature("dependent", "Dependent", "quiet", requires=("base",))
    catalog = {item.name: ("test", item) for item in (base, dependent)}
    shared = tmp_path / "shared.yaml"
    shared.write_text("offline: true\nquiet: true\n")
    local = empty_env / ".condarc"
    local.write_text("quiet: true\n")
    ctx = Context(search_path=(shared,))
    plan = base.cleanup(catalog, ctx, shared, "user")
    check_affected(catalog, plan, [(empty_env, Context(search_path=(shared, local)))])
    base.apply(plan, ctx)
    result = dependent.status(catalog, Context(search_path=(shared,)), "user")
    assert result["readiness"] == "ready"


@pytest.mark.parametrize("operation", ["migrate", "cleanup"])
def test_edit_during_lifecycle_planning_is_stale(
    lifecycle_catalog, tmp_path, monkeypatch, operation
):
    from dataclasses import replace

    from conda import CondaError

    from conda_features.operations import lifecycle

    path = tmp_path / ".condarc"
    path.write_text("offline: true\n")
    feature = lifecycle_catalog["old"][1]
    if operation == "cleanup":
        feature = replace(feature, graduation="unconditional")
        lifecycle_catalog["old"] = ("test", feature)
    ctx = Context(search_path=(path,))
    original = lifecycle.prospective_context

    def edited(*args):
        candidate = original(*args)
        path.write_text("offline: false\n")
        return candidate

    monkeypatch.setattr(lifecycle, "prospective_context", edited)
    plan = getattr(feature, operation)(lifecycle_catalog, ctx, path, "user")
    with pytest.raises(CondaError, match="changed after preview"):
        feature.apply(plan, ctx)
    assert path.read_text() == "offline: false\n"
