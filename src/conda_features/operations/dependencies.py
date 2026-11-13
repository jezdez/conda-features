"""Explicit prerequisite ordering and checks of affected environments."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from conda import CondaError
from conda.base.context import Context
from conda.cli.condarc import ConfigurationFile
from conda.core.envs_manager import get_user_environments_txt_file

from ..steps import runner
from ..steps.configuration import EnsureChannel, SetSetting
from ..steps.packages import InstallPackages
from .configuration import plan_change
from .settings import fingerprint, prospective_context

if TYPE_CHECKING:
    from ..models import Catalog


def prerequisite_order(
    catalog: Catalog, ctx: Context, scope: str, name: str
) -> list[str]:
    ordered: list[str] = []

    def visit(key: str, visiting: tuple[str, ...]) -> None:
        if key in visiting:
            raise CondaError(
                "Feature dependency cycle: " + " -> ".join((*visiting, key))
            )
        if key not in catalog:
            raise CondaError(f"Missing dependency: {key}")
        if key in ordered:
            return
        feature = catalog[key][1]
        if key != name:
            status = feature.status(catalog, ctx, None)
            if (
                status["effective"] == "enabled"
                or feature.graduation == "unconditional"
            ) and not feature.retired:
                return
        if scope not in feature.scopes:
            raise CondaError(
                f"Feature {key} does not support scope {scope}. Enable it explicitly at a supported scope first."
            )
        for dependency in feature.requires:
            visit(dependency, (*visiting, key))
        ordered.append(key)

    visit(name, ())
    return ordered


def projected_context(plan: dict[str, Any], ctx: Context) -> Context:
    path = Path(plan["path"])
    config = ConfigurationFile(path=path, context=ctx)
    for child in plan.get("plans", [plan]):
        if "steps" in child:
            for step, item in child["steps"]:
                if isinstance(step, (SetSetting, EnsureChannel)):
                    step.update_config(config, item)
        else:
            for key, val in child["changes"].items():
                if key not in child.get("remove", ()):
                    config.set_key(key, val)
            for key in child.get("remove", ()):
                config.remove_key(key)
    return prospective_context(ctx, path, config.content)


def plan_prerequisites(
    feature, catalog: Catalog, ctx: Context, path: Path, scope: str
) -> dict[str, Any]:
    """Plan prerequisites without performing an unconstrained second solve."""
    names = prerequisite_order(catalog, ctx, scope, feature.name)
    for name in names:
        item = catalog[name][1]
        if item.enabled_setting is None and (
            not item.steps
            or any(
                type(step) not in (SetSetting, EnsureChannel, InstallPackages)
                for step in item.steps
            )
        ):
            raise CondaError(
                f"Deploy custom feature {name} separately. Combined planning uses built-in configuration steps only."
            )
        if name != feature.name and any(
            not isinstance(step, (SetSetting, EnsureChannel))
            for step in catalog[name][1].steps
        ):
            raise CondaError(
                f"Deploy prerequisite {name} separately before enabling {feature.name}. Combined prerequisite plans support configuration steps only."
            )
    package_steps = sum(
        isinstance(step, InstallPackages)
        for name in names
        for step in catalog[name][1].steps
    )
    if package_steps > 1:
        raise CondaError(
            "This selection needs multiple package transactions. Enable the package prerequisites individually before retrying."
        )
    plans = []
    candidate = ctx
    config = ConfigurationFile(path=path, context=ctx)
    for name in names:
        item = catalog[name][1]
        child = (
            plan_change(
                catalog,
                candidate,
                path,
                scope,
                "enable",
                name,
                initial_content=config.content,
            )
            if item.enabled_setting
            else runner.plan(
                item,
                catalog,
                candidate,
                path,
                scope,
                "enable",
                initial_content=config.content,
            )
        )
        plans.append(child)
        if "steps" in child:
            for step, step_plan in child["steps"]:
                if isinstance(step, (SetSetting, EnsureChannel)):
                    step.update_config(config, step_plan)
        else:
            for key, val in child["changes"].items():
                config.set_key(key, val)
        candidate = projected_context({"plans": plans, "path": str(path)}, ctx)
    candidate.validate_configuration()
    candidate.plugins.validate_configuration()
    return {
        "operation": "enable",
        "features": names,
        "scope": scope,
        "path": str(path),
        "changes": {
            name: child["changes"]
            for name, child in zip(names, plans)
            if child["changes"]
        },
        "plans": plans,
        "fingerprint": fingerprint(path),
    }


def check_affected(
    catalog: Catalog, plan: dict[str, Any], environments: list[tuple[Path, Context]]
) -> None:
    for prefix, before in environments:
        after = projected_context(plan, before)
        after.validate_configuration()
        after.plugins.validate_configuration()
        for name, (_, feature) in catalog.items():
            status = feature.status(catalog, after, None, path=prefix / ".condarc")
            if status["effective"] != "enabled":
                continue
            for dependency in feature.requires:
                if dependency not in catalog:
                    continue
                prerequisite = catalog[dependency][1]
                if prerequisite.graduation == "unconditional":
                    continue
                old = prerequisite.status(catalog, before, None)
                new = prerequisite.status(catalog, after, None)
                if old["effective"] == "enabled" and new["effective"] != "enabled":
                    raise CondaError(
                        f"Environment {prefix}: enabled feature {name} requires {dependency}. Disable the dependent in that environment first. No changes made."
                    )
            old_status = feature.status(catalog, before, None)
            if old_status["readiness"] == "ready" and status["readiness"] != "ready":
                raise CondaError(
                    f"Environment {prefix}: change would break enabled feature {name}. "
                    + " ".join(status["reasons"])
                )


def affected_environments(args: Namespace, scope: str) -> list[tuple[Path, Context]]:
    explicit = {
        Path(item).expanduser().absolute() for item in getattr(args, "check_prefix", ())
    }
    for prefix in explicit:
        if not (prefix / "conda-meta").is_dir():
            raise CondaError(f"Not a conda environment: {prefix}")
    known: set[Path] = set()
    if scope in ("user", "system") and not args.file:
        registry = Path(get_user_environments_txt_file())
        if registry.exists():
            known.update(
                Path(line).expanduser().absolute()
                for line in registry.read_text().splitlines()
                if line.strip()
            )
        known.add(Path(Context().root_prefix))
    prefixes = explicit | {
        prefix for prefix in known if (prefix / "conda-meta").is_dir()
    }
    return [
        (prefix, Context(argparse_args=Namespace(prefix=str(prefix))))
        for prefix in sorted(prefixes)
    ]


def guard_plan(args: Namespace, catalog: Catalog, plan: dict[str, Any]) -> None:
    environments = affected_environments(args, plan["scope"])
    check_affected(catalog, plan, environments)
    plan["checked_environments"] = [str(prefix) for prefix, _ in environments]
    plan["guard_args"] = args
    plan["source_membership"] = {
        str(prefix): sorted(str(source) for source in ctx.raw_data)
        for prefix, ctx in environments
    }
    plan["discovery"] = (
        "Checked explicit targets and the current user's registered environments for shared scopes. Unregistered environments and other users' registries are not scanned."
    )
    plan["source_fingerprints"] = {
        str(source): fingerprint(Path(source))
        for _, ctx in environments
        for source in ctx.raw_data
        if str(source) not in ("envvars", "cmd_line")
    }
    for prefix, _ in environments:
        plan["source_fingerprints"].setdefault(
            str(prefix / ".condarc"), fingerprint(prefix / ".condarc")
        )


def verify_guard(plan: dict[str, Any]) -> None:
    if "guard_args" in plan:
        fresh = affected_environments(plan["guard_args"], plan["scope"])
        membership = {
            str(prefix): sorted(str(source) for source in ctx.raw_data)
            for prefix, ctx in fresh
        }
        if membership != plan["source_membership"]:
            raise CondaError(
                "An affected environment changed after preview. Review the plan again."
            )
    for source, expected in plan.get("source_fingerprints", {}).items():
        if fingerprint(Path(source)) != expected:
            raise CondaError(
                "An affected environment changed after preview. Review the plan again."
            )
