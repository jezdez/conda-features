"""Read only a feature's declared configuration through conda's adapters."""

from __future__ import annotations

from copy import copy
from pathlib import Path
from typing import TYPE_CHECKING, Any

from conda import CondaError
from conda.base.context import Context
from conda.cli.condarc import ConfigurationFile

from ..steps.configuration import SetSetting
from .settings import saved_keys, saved_value, setting_context, value

if TYPE_CHECKING:
    from ..models import Feature


def query(
    feature: Feature,
    ctx: Context,
    path: Path,
    scope: str,
    action: str,
    keys: list[str] | None,
) -> dict[str, Any]:
    if scope not in feature.scopes:
        raise CondaError(f"Feature {feature.name} does not support scope {scope}.")
    selected = list(feature.settings) if not keys else keys
    if set(selected) - set(feature.settings):
        raise CondaError(
            "Only declared feature settings may be inspected. Use explain for the enabled state."
        )
    result: dict[str, Any] = {
        "operation": action,
        "feature": feature.name,
        "path": str(path),
        "scope": scope,
    }
    if action == "describe":
        result["descriptions"] = {
            key: owner.describe_parameter(name)
            for key in selected
            for owner, name in [setting_context(ctx, key)]
        }
    elif action == "show":
        result["values"] = {key: SetSetting.scalar(value(ctx, key)) for key in selected}
    elif action == "get":
        config = ConfigurationFile(path=path, context=ctx)
        values = {}
        for key in selected:
            names = saved_keys(config, ctx, key)
            if len(names) > 1:
                raise CondaError(
                    f"Multiple saved aliases for {key}. Reconcile them before reading."
                )
            if names:
                values[key] = SetSetting(
                    key, saved_value(config, names[0])
                ).normalized_value(ctx)
        result["values"] = values
    elif action == "show-sources":
        sources: dict[str, dict[str, Any]] = {}
        for key in selected:
            owner, name = setting_context(ctx, key)
            aliases = (name, *owner.describe_parameter(name)["aliases"])
            filtered = copy(owner)
            # check_source validates only parameter_names. Keep the owner's
            # source adapter intact, including PluginConfig's read-only view.
            filtered.parameter_names = (name,)
            filtered._cache_ = {}
            for source, values in filtered.collect_all().items():
                found = [alias for alias in aliases if alias in values]
                if len(found) > 1:
                    raise CondaError(
                        f"Multiple saved aliases for {key}. Reconcile them before reading."
                    )
                if found:
                    sources.setdefault(str(source), {})[key] = SetSetting(
                        key, values[found[0]]
                    ).normalized_value(ctx)
        result["sources"] = sources
    else:
        raise CondaError(f"Unknown configuration query: {action}")
    return result
