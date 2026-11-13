"""Plan and persist conda configuration changes."""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

from conda import CondaError
from conda.base.context import Context
from conda.cli.condarc import ConfigurationFile
from conda.common.configuration import YamlRawParameter
from filelock import FileLock, Timeout

from .settings import fingerprint, prospective_context, setting_context, value
from .validation import validate_catalog

if TYPE_CHECKING:
    from ..models import Catalog


def plan_change(
    catalog: Catalog,
    ctx: Context,
    path: Path,
    scope: str,
    operation: str,
    name: str | None,
    *,
    all_features: bool = False,
    settings: dict[str, str] | None = None,
    selected_names: list[str] | None = None,
    initial_content: dict | None = None,
) -> dict[str, Any]:
    validate_catalog(catalog, ctx)
    if selected_names is not None:
        selected = selected_names
    elif all_features:
        if operation != "disable" or name is not None:
            raise CondaError("Use disable --all without a feature name.")
        selected = [
            key
            for key, (_, feature) in catalog.items()
            if scope in feature.scopes and feature.graduation != "unconditional"
        ]
    elif name in catalog:
        selected = [name]
    else:
        raise CondaError(f"Unknown feature: {name}")
    initial = fingerprint(path)
    config = (
        ConfigurationFile(path=path, context=ctx)
        if initial_content is None
        else ConfigurationFile(content=initial_content, context=ctx)
    )
    changes = {}
    expected_values = {}
    ordered = []

    def visit(key, visiting=()):
        if key in visiting:
            if operation == "disable":
                return
            raise CondaError(
                "Feature dependency cycle: " + " -> ".join((*visiting, key))
            )
        if key in ordered:
            return
        for dependency in catalog[key][1].requires:
            if dependency in selected:
                visit(dependency, (*visiting, key))
        ordered.append(key)

    for key in selected:
        visit(key)
    if operation == "disable":
        ordered.reverse()
    for key in ordered:
        feature = catalog[key][1]
        if feature.graduation == "unconditional":
            raise CondaError(
                f"Feature {key} is unconditional. Use cleanup instead of changing its opt-in."
            )
        if scope not in feature.scopes:
            raise CondaError(f"Feature {key} does not support scope {scope}.")
        if operation == "configure":
            requested = settings or {}
            if not requested or set(requested) - set(feature.settings):
                raise CondaError(f"Only declared settings for {key} may be configured.")
        elif operation in ("enable", "disable"):
            if feature.enabled_setting is None:
                raise CondaError(
                    f"Deploy {key} individually. It owns its deployment plan."
                )
            requested = {feature.enabled_setting: operation == "enable"}
        else:
            raise CondaError(f"Unknown operation: {operation}")
        for setting, new_value in requested.items():
            _, previous = config.get_key(setting)
            config.set_key(setting, new_value)
            _, typed = config.get_key(setting)
            expected_values[setting] = typed
            if previous != typed:
                changes[setting] = typed
    candidate = prospective_context(ctx, path, config.content)
    candidate.validate_configuration()
    candidate.plugins.validate_configuration()
    for setting, expected in expected_values.items():
        if value(candidate, setting) != expected:
            owner, parameter = setting_context(candidate, setting)
            sources = [
                str(source)
                for source, values in owner.collect_all().items()
                if parameter in values and str(source) != str(path)
            ]
            raise CondaError(
                f"Setting {setting} is overridden. Other sources: {', '.join(sources)}. "
                "Change or remove the override, then retry. No changes made."
            )
    for key in selected:
        if operation != "disable":
            result = catalog[key][1].status(catalog, candidate, scope)
            if result["readiness"] == "blocked" or (
                operation == "enable" and result["readiness"] != "ready"
            ):
                raise CondaError(
                    f"Cannot {operation} {key}: " + " ".join(result["reasons"])
                )
    # A change must not break a previously usable dependent at this scope.
    for key, (_, feature) in catalog.items():
        if key not in selected and (
            value(candidate, feature.enabled_setting)
            if feature.enabled_setting
            else feature.status(catalog, candidate, scope)["effective"] == "enabled"
        ):
            if operation == "disable":
                for prerequisite in set(feature.requires).intersection(selected):
                    raise CondaError(
                        f"Enabled feature {key} requires {prerequisite}. "
                        "Disable the dependent first, or use disable --all at this scope."
                    )
            before = feature.status(catalog, ctx, scope)
            after = feature.status(catalog, candidate, scope)
            if before["readiness"] == "ready" and after["readiness"] != "ready":
                raise CondaError(
                    f"Change would break enabled feature {key}: "
                    + " ".join(after["reasons"])
                )
    return {
        "operation": operation,
        "features": selected,
        "scope": scope,
        "path": str(path),
        "changes": changes,
        "fingerprint": initial,
    }


def apply_change(plan: dict[str, Any], ctx: Context) -> None:
    if not plan["changes"]:
        return
    path = Path(plan["path"])
    temporary = None
    try:
        with FileLock(str(path) + ".lock", timeout=5):
            if fingerprint(path) != plan["fingerprint"]:
                raise CondaError(
                    "Configuration changed after preview. Run the command again."
                )
            config = ConfigurationFile(path=path, context=ctx)
            for key, new_value in plan["changes"].items():
                if key not in plan.get("remove", ()):
                    config.set_key(key, new_value)
            for key in plan.get("remove", ()):
                config.remove_key(key)
            with tempfile.NamedTemporaryFile(
                dir=path.parent, prefix=".conda-features-", delete=False
            ) as stream:
                temporary = Path(stream.name)
            config.write(temporary)
            if path.exists():
                temporary.chmod(stat.S_IMODE(path.stat().st_mode))
            os.replace(temporary, path)
            YamlRawParameter.cache_clear()
    except (OSError, Timeout) as exc:
        raise CondaError(
            "Cannot write feature configuration. No changes were applied."
        ) from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
