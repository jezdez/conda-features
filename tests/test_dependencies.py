from __future__ import annotations

import json

import pytest
from conda import CondaError
from conda.base.context import Context

from conda_features.models import Feature


@pytest.fixture
def dependency_catalog(monkeypatch):
    from conda_features.cli import commands

    base = Feature("base", "Base", "offline", scopes=("user", "environment"))
    dependent = Feature(
        "dependent",
        "Dependent",
        "quiet",
        scopes=("user", "environment"),
        requires=("base",),
    )
    catalog = {item.name: ("test", item) for item in (base, dependent)}
    monkeypatch.setattr(commands, "discover", lambda: catalog)
    return catalog


def test_explicit_prerequisite_opt_in_is_previewed_and_confirmed(
    conda_cli, dependency_catalog, tmp_path
):
    path = tmp_path / ".condarc"
    path.write_text("offline: false\nquiet: false\n")
    before = path.read_bytes()
    out, err, code = conda_cli(
        "feature",
        "enable",
        "dependent",
        "--with-dependencies",
        "--file",
        path,
        "--dry-run",
        "--json",
    )
    assert code == 0, out + err
    result = json.loads(out)
    assert result["features"] == ["base", "dependent"]
    assert result["changes"] == {"offline": True, "quiet": True}
    assert path.read_bytes() == before
    out, err, code = conda_cli(
        "feature",
        "enable",
        "dependent",
        "--with-dependencies",
        "--file",
        path,
        "--json",
    )
    assert code == 1 and "--yes" in out
    assert path.read_bytes() == before
    out, err, code = conda_cli(
        "feature",
        "enable",
        "dependent",
        "--with-dependencies",
        "--file",
        path,
        "--yes",
        "--json",
    )
    assert code == 0, out + err
    ctx = Context(search_path=(path,))
    assert ctx.offline and ctx.quiet


@pytest.mark.parametrize("all_features", [False, True], ids=["individual", "bulk"])
def test_shared_disable_protects_explicit_environment(
    dependency_catalog, tmp_path, empty_env, all_features
):
    from conda_features.operations import dependencies
    from conda_features.operations.configuration import plan_change

    shared = tmp_path / "shared.yaml"
    shared.write_text("offline: true\n")
    local = empty_env / ".condarc"
    local.write_text("quiet: true\n")
    original = shared.read_bytes()
    ctx = Context(search_path=(shared,))
    plan = plan_change(
        dependency_catalog,
        ctx,
        shared,
        "user",
        "disable",
        None if all_features else "base",
        all_features=all_features,
    )
    other = Context(search_path=(shared, local))
    with pytest.raises(CondaError, match="dependent.*base"):
        dependencies.check_affected(dependency_catalog, plan, [(empty_env, other)])
    assert shared.read_bytes() == original


def test_cli_checks_two_explicit_environments(
    conda_cli, dependency_catalog, tmp_path, monkeypatch, empty_env
):
    import importlib

    from conda_features.cli import targets

    shared = tmp_path / "shared.yaml"
    shared.write_text("offline: true\n")
    first = empty_env
    second = tmp_path / "second"
    (second / "conda-meta").mkdir(parents=True)
    (first / ".condarc").write_text("quiet: false\n")
    (second / ".condarc").write_text("quiet: true\n")
    module = importlib.import_module("conda.base.context")
    monkeypatch.setattr(module, "SEARCH_PATH", (str(shared), "$CONDA_PREFIX/.condarc"))
    monkeypatch.setattr(targets, "user_rc_path", str(shared))
    out, _, code = conda_cli(
        "feature",
        "disable",
        "base",
        "--user",
        "--check-prefix",
        first,
        "--check-prefix",
        second,
        "--yes",
        "--json",
    )
    assert code == 1
    assert str(second) in json.loads(out)["error"]
    assert shared.read_text() == "offline: true\n"
    assert (second / ".condarc").read_text() == "quiet: true\n"


def test_environment_override_preserves_dependent(
    dependency_catalog, tmp_path, empty_env
):
    from conda_features.operations.dependencies import check_affected

    shared = tmp_path / "shared.yaml"
    shared.write_text("offline: true\n")
    local = empty_env / ".condarc"
    local.write_text("offline: true\nquiet: true\n")
    ctx = Context(search_path=(shared,))
    plan = dependency_catalog["base"][1].disable(
        dependency_catalog, ctx, shared, "user"
    )
    check_affected(
        dependency_catalog, plan, [(empty_env, Context(search_path=(shared, local)))]
    )
    assert local.read_text() == "offline: true\nquiet: true\n"


def test_guard_detects_environment_edit_after_preview(
    dependency_catalog, tmp_path, empty_env, monkeypatch
):
    from argparse import Namespace

    from conda_features.operations import dependencies

    shared = tmp_path / "shared.yaml"
    shared.write_text("offline: true\n")
    local = empty_env / ".condarc"
    local.write_text("quiet: false\n")
    ctx = Context(search_path=(shared,))
    plan = dependency_catalog["base"][1].disable(
        dependency_catalog, ctx, shared, "user"
    )
    monkeypatch.setattr(
        dependencies,
        "affected_environments",
        lambda args, scope: [(empty_env, Context(search_path=(shared, local)))],
    )
    dependencies.guard_plan(Namespace(), dependency_catalog, plan)
    local.write_text("quiet: true\n")
    with pytest.raises(CondaError, match="changed after preview"):
        dependencies.verify_guard(plan)


def test_setting_step_prerequisite_and_boolean_feature_share_one_confirmation(
    conda_cli, dependency_catalog, tmp_path
):
    from conda_features.steps import SetSetting

    dependency_catalog["base"] = (
        "test",
        Feature("base", "Base", steps=(SetSetting("offline", True),)),
    )
    path = tmp_path / ".condarc"
    path.write_text("offline: false\nquiet: false\n")
    out, err, code = conda_cli(
        "feature",
        "enable",
        "dependent",
        "--with-dependencies",
        "--file",
        path,
        "--dry-run",
        "--json",
    )
    assert code == 0, out + err
    assert json.loads(out)["features"] == ["base", "dependent"]
    assert path.read_text() == "offline: false\nquiet: false\n"
    out, err, code = conda_cli(
        "feature",
        "enable",
        "dependent",
        "--with-dependencies",
        "--file",
        path,
        "--yes",
        "--json",
    )
    assert code == 0, out + err
    assert Context(search_path=(path,)).offline
    assert Context(search_path=(path,)).quiet


def test_invalid_explicit_check_prefix_rejects_mutation(
    conda_cli, dependency_catalog, tmp_path
):
    path = tmp_path / ".condarc"
    path.write_text("offline: false\n")
    out, _, code = conda_cli(
        "feature",
        "enable",
        "base",
        "--file",
        path,
        "--check-prefix",
        tmp_path / "missing",
        "--yes",
        "--json",
    )
    assert code == 1
    assert "Not a conda environment" in out
    assert path.read_text() == "offline: false\n"


def test_registered_environments_are_read_without_cleaning_registry(
    tmp_path, monkeypatch
):
    from argparse import Namespace

    from conda_features.operations import dependencies

    prefix = tmp_path / "registered"
    (prefix / "conda-meta").mkdir(parents=True)
    registry = tmp_path / "environments.txt"
    registry.write_text(str(prefix) + "\n" + str(tmp_path / "removed") + "\n")
    original = registry.read_bytes()
    monkeypatch.setattr(
        dependencies, "get_user_environments_txt_file", lambda: str(registry)
    )
    result = dependencies.affected_environments(
        Namespace(file=None, check_prefix=[]), "user"
    )
    assert prefix in [path for path, _ in result]
    assert registry.read_bytes() == original


def test_standalone_file_does_not_scan_registry(tmp_path, monkeypatch):
    from argparse import Namespace

    from conda_features.operations import dependencies

    def unexpected():
        pytest.fail(
            "Standalone file must not inspect unrelated registered environments"
        )

    monkeypatch.setattr(dependencies, "get_user_environments_txt_file", unexpected)
    assert (
        dependencies.affected_environments(
            Namespace(file=str(tmp_path / "demo.yaml"), check_prefix=[]), "user"
        )
        == []
    )


def test_projected_context_keeps_selected_prefix(empty_env):
    from argparse import Namespace

    from conda_features.operations.settings import prospective_context

    ctx = Context(argparse_args=Namespace(prefix=str(empty_env)))
    projected = prospective_context(ctx, empty_env / ".condarc", {"offline": True})
    assert projected.target_prefix == str(empty_env)


def test_new_condarc_directory_source_invalidates_guard(
    dependency_catalog, tmp_path, empty_env, monkeypatch
):
    import importlib
    from argparse import Namespace

    from conda_features.operations import dependencies

    shared = tmp_path / "shared.yaml"
    shared.write_text("offline: true\n")
    module = importlib.import_module("conda.base.context")
    monkeypatch.setattr(module, "SEARCH_PATH", (str(shared), "$CONDA_PREFIX/condarc.d"))
    args = Namespace(file=str(shared), check_prefix=[str(empty_env)])
    ctx = Context(search_path=(shared,))
    plan = dependency_catalog["base"][1].disable(
        dependency_catalog, ctx, shared, "user"
    )
    dependencies.guard_plan(args, dependency_catalog, plan)
    directory = empty_env / "condarc.d"
    directory.mkdir()
    (directory / "dependent.yaml").write_text("quiet: true\n")
    with pytest.raises(CondaError, match="changed after preview"):
        dependencies.verify_guard(plan)


def test_inherited_user_prerequisite_can_enable_environment_feature(
    conda_cli, dependency_catalog, empty_env, tmp_path, monkeypatch
):
    import importlib
    from dataclasses import replace

    provider, feature = dependency_catalog["base"]
    dependency_catalog["base"] = (provider, replace(feature, scopes=("user",)))
    shared = tmp_path / "shared.yaml"
    shared.write_text("offline: true\n")
    monkeypatch.setattr(
        importlib.import_module("conda.base.context"),
        "SEARCH_PATH",
        (str(shared), "$CONDA_PREFIX/.condarc"),
    )
    out, err, code = conda_cli(
        "feature",
        "enable",
        "dependent",
        "--prefix",
        empty_env,
        "--with-dependencies",
        "--yes",
        "--json",
    )
    assert code == 0, out + err
    assert json.loads(out)["features"] == ["dependent"]
    assert "quiet: true" in (empty_env / ".condarc").read_text()
    assert shared.read_text() == "offline: true\n"


def test_user_only_conflict_detected_in_checked_environment(tmp_path, empty_env):
    from conda_features.operations.dependencies import check_affected

    catalog = {
        "base": ("test", Feature("base", "Base", "offline", conflicts=("other",))),
        "other": ("test", Feature("other", "Other", "quiet")),
    }
    shared = tmp_path / "shared.yaml"
    shared.write_text("offline: false\n")
    local = empty_env / ".condarc"
    local.write_text("quiet: true\n")
    plan = catalog["base"][1].enable(
        catalog, Context(search_path=(shared,)), shared, "user"
    )
    with pytest.raises(CondaError, match="conflict"):
        check_affected(
            catalog, plan, [(empty_env, Context(search_path=(shared, local)))]
        )


def test_missing_nonconfiguration_prerequisite_refused_before_solve(
    dependency_catalog, tmp_path, monkeypatch
):
    from conda_features.steps import InstallPackages, packages

    monkeypatch.setattr(packages, "missing_packages", lambda specs: ["missing"])

    def no_solve(*args):
        pytest.fail("Unsupported combined setup must fail before solving")

    monkeypatch.setattr(InstallPackages, "plan", no_solve)
    dependency_catalog["base"] = (
        "test",
        Feature("base", "Base", steps=(InstallPackages("missing"),)),
    )
    path = tmp_path / ".condarc"
    path.write_text("{}\n")
    with pytest.raises(CondaError, match="separately"):
        dependency_catalog["dependent"][1].enable(
            dependency_catalog,
            Context(search_path=(path,)),
            path,
            "user",
            with_dependencies=True,
        )


def test_dependent_step_sees_selected_prefix_during_plan_and_apply(
    conda_cli, dependency_catalog, empty_env, monkeypatch
):
    from conda_features.steps import SetSetting

    dependency_catalog["dependent"] = (
        "test",
        Feature(
            "dependent",
            "Dependent",
            requires=("base",),
            scopes=("environment",),
            steps=(SetSetting("quiet", True),),
        ),
    )
    seen = []
    original_plan = SetSetting.plan
    original_apply = SetSetting.apply

    def plan(self, ctx, path, operation, saved):
        seen.append(("plan", ctx.target_prefix))
        return original_plan(self, ctx, path, operation, saved)

    def apply(self, plan, ctx, checkpoint):
        seen.append(("apply", ctx.target_prefix))
        return original_apply(self, plan, ctx, checkpoint)

    monkeypatch.setattr(SetSetting, "plan", plan)
    monkeypatch.setattr(SetSetting, "apply", apply)
    out, err, code = conda_cli(
        "feature",
        "enable",
        "dependent",
        "--prefix",
        empty_env,
        "--with-dependencies",
        "--yes",
        "--json",
    )
    assert code == 0, out + err
    assert seen == [("plan", str(empty_env)), ("apply", str(empty_env))]


def test_prerequisite_cycle_and_scope_are_rejected(dependency_catalog, tmp_path):
    from dataclasses import replace

    from conda_features.operations.dependencies import prerequisite_order

    ctx = Context(search_path=())
    provider, base = dependency_catalog["base"]
    dependency_catalog["base"] = (provider, replace(base, requires=("dependent",)))
    with pytest.raises(CondaError, match="cycle"):
        prerequisite_order(dependency_catalog, ctx, "user", "dependent")
    dependency_catalog["base"] = (provider, replace(base, scopes=("system",)))
    with pytest.raises(CondaError, match="scope"):
        prerequisite_order(dependency_catalog, ctx, "user", "dependent")
