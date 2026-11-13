"""Feature declarations and user operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from conda import CondaError, __version__
from conda.base.context import Context
from conda.cli.condarc import ConfigurationFile
from conda.common.configuration import YamlRawParameter
from conda.models.version import VersionSpec

from .operations.configuration import apply_change, plan_change
from .operations.dependencies import plan_prerequisites, prerequisite_order
from .operations.settings import setting_context, value
from .steps import runner

if TYPE_CHECKING:
    from pathlib import Path

    from .steps.base import Step

type Catalog = dict[str, tuple[str, Feature]]


@dataclass(frozen=True)
class Feature:
    """A feature backed by a boolean conda setting or deployment steps.

    Providers yield these from the ``conda_features`` Pluggy hook, registered
    through the entry-point group of the same name. Settings must already be
    registered with conda. ``settings`` is an
    allowlist of non-secret scalar settings configurable through this command.
    ``required_settings`` must also appear in that allowlist.
    """

    name: str
    description: str
    enabled_setting: str | None = None
    maturity: str = "experimental"
    scopes: tuple[str, ...] = ("user",)
    settings: tuple[str, ...] = ()
    required_settings: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    conda_version: str = ">=26.9.4"
    platforms: tuple[str, ...] = ()
    retired: bool = False
    replacement: str | None = None
    guidance: str = ""
    steps: tuple[Step, ...] = ()

    def validate_deployment_methods(self) -> None:
        for method in ("enable", "disable", "status", "apply"):
            if getattr(type(self), method) is getattr(Feature, method):
                raise CondaError(
                    f"Deployment feature {self.name} must implement {method}."
                )

    def apply(self, plan: dict[str, Any], ctx: Context) -> None:
        """Apply an approved configuration plan. Deployment providers override this."""
        if self.steps and plan["operation"] != "configure":
            return runner.apply(plan, ctx)
        apply_change(plan, ctx)

    def enable(
        self,
        catalog: Catalog,
        ctx: Context,
        path: Path,
        scope: str,
        *,
        with_dependencies: bool = False,
    ) -> dict[str, Any]:
        """Plan an opt-in. The caller confirms and applies the returned plan."""
        if with_dependencies:
            selected = prerequisite_order(catalog, ctx, scope, self.name)
            if all(catalog[name][1].enabled_setting for name in selected):
                return plan_change(
                    catalog,
                    ctx,
                    path,
                    scope,
                    "enable",
                    self.name,
                    selected_names=selected,
                )
            if len(selected) > 1:
                return plan_prerequisites(self, catalog, ctx, path, scope)
        if self.steps:
            return runner.plan(self, catalog, ctx, path, scope, "enable")
        return plan_change(catalog, ctx, path, scope, "enable", self.name)

    def disable(
        self, catalog: Catalog, ctx: Context, path: Path, scope: str
    ) -> dict[str, Any]:
        """Plan a dependency-safe opt-out without removing other settings."""
        if self.steps:
            return runner.plan(self, catalog, ctx, path, scope, "disable")
        return plan_change(catalog, ctx, path, scope, "disable", self.name)

    def configure(
        self,
        catalog: Catalog,
        ctx: Context,
        path: Path,
        scope: str,
        settings: dict[str, str],
    ) -> dict[str, Any]:
        """Plan changes to this feature's declared scalar settings."""
        if self.steps:
            if runner.load(self, path)[1]:
                raise CondaError(
                    "Disable the deployment before changing its configuration."
                )
        return plan_change(
            catalog, ctx, path, scope, "configure", self.name, settings=settings
        )

    def status(
        self,
        catalog: Catalog,
        ctx: Context,
        scope: str | None,
        visiting: tuple[str, ...] = (),
        *,
        path: Path | None = None,
    ) -> dict[str, Any]:
        """Explain the configured choice and known prerequisites."""
        provider, _ = catalog[self.name]
        reasons = []
        if scope is not None and scope not in self.scopes:
            reasons.append(f"Unsupported scope: {scope}.")
        if self.retired:
            reasons.append(
                "Feature is retired."
                + (f" Consider {self.replacement}." if self.replacement else "")
            )
        if not VersionSpec(self.conda_version).match(__version__):
            reasons.append(f"Requires conda {self.conda_version}.")
        if self.platforms and ctx.subdir not in self.platforms:
            reasons.append(f"Unsupported platform: {ctx.subdir}.")
        step_reasons = [
            reason for step in self.steps for reason in step.check(ctx, path)
        ]
        if self.steps:
            effective = not step_reasons
        else:
            assert self.enabled_setting is not None
            effective = value(ctx, self.enabled_setting)
        requested = "unknown"
        if self.steps and path is not None:
            requested = "enabled" if runner.load(self, path)[1] else "unset"
        elif path is not None:
            assert self.enabled_setting is not None
            saved_config = ConfigurationFile(path=path, context=ctx)
            saved_ctx = Context(search_path=())
            saved_ctx.raw_data.clear()
            saved_ctx.raw_data[path] = YamlRawParameter.make_raw_parameters(
                path, saved_config.content
            )
            owner, parameter = setting_context(saved_ctx, self.enabled_setting)
            requested = "unset"
            names = {parameter, *owner.describe_parameter(parameter)["aliases"]}
            if any(
                names.intersection(values) for values in owner.collect_all().values()
            ):
                requested = (
                    "enabled" if value(saved_ctx, self.enabled_setting) else "disabled"
                )
        if self.name in visiting:
            reasons.append(
                "Feature dependency cycle: " + " -> ".join((*visiting, self.name))
            )
        else:
            for dependency in self.requires:
                if dependency not in catalog:
                    reasons.append(f"Missing dependency: {dependency}.")
                else:
                    dependency_status = catalog[dependency][1].status(
                        catalog, ctx, None, (*visiting, self.name)
                    )
                    if (
                        dependency_status["effective"] != "enabled"
                        or dependency_status["readiness"] != "ready"
                    ):
                        reasons.append(f"Requires enabled feature {dependency}.")
                        reasons.extend(dependency_status["reasons"])
        for other, (_, other_feature) in catalog.items():
            if (other in self.conflicts or self.name in other_feature.conflicts) and (
                value(ctx, other_feature.enabled_setting)
                if other_feature.enabled_setting
                else not any(step.check(ctx, path) for step in other_feature.steps)
                if other_feature.steps
                else other_feature.status(catalog, ctx, scope)["effective"] == "enabled"
            ):
                reasons.append(f"Feature conflict with {other}.")
        missing = [
            key for key in self.required_settings if value(ctx, key) in (None, "")
        ]
        readiness = (
            "blocked"
            if reasons
            else "setup required"
            if missing or step_reasons
            else "ready"
        )
        reasons.extend(step_reasons)
        reasons.extend(f"Configure required setting {key}." for key in missing)
        sources = {}
        for key in (
            *((self.enabled_setting,) if self.enabled_setting else ()),
            *self.settings,
        ):
            config, parameter = setting_context(ctx, key)
            sources[key] = [
                str(source)
                for source, values in config.collect_all().items()
                if parameter in values
            ]
        return {
            "name": self.name,
            "provider": provider,
            "description": self.description,
            "maturity": self.maturity,
            "requested": requested,
            "effective": "enabled" if effective else "disabled",
            "runtime": "unknown",
            "readiness": readiness,
            "reasons": reasons,
            "sources": sources,
            "guidance": self.guidance,
            "settings": list(self.settings),
        }
