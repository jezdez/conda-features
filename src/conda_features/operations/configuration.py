"""Plan and persist conda configuration changes."""

import hashlib
import os
import stat
import tempfile
from copy import copy
from pathlib import Path
from typing import Any

from conda import CondaError
from conda.base.constants import SEARCH_PATH
from conda.base.context import Context
from conda.cli.condarc import ConfigurationFile
from conda.common.configuration import YamlRawParameter, custom_expandvars
from conda.common.serialize import yaml
from filelock import FileLock, Timeout

from ..models import Catalog
from .discovery import validate_catalog


def setting_context(ctx: Context, key: str):
    if key.startswith("plugins."):
        return ctx.plugins, key.removeprefix("plugins.")
    return ctx, key


def value(ctx: Context, key: str) -> Any:
    config, name = setting_context(ctx, key)
    return getattr(config, name)


def prospective_context(ctx: Context, path: Path, content: dict) -> Context:
    # Replace this source in place so conda still handles precedence and !final.
    raw = YamlRawParameter.make_raw_parameters(path, yaml.loads(yaml.dumps(content)))
    data = {}
    inserted = False
    # Conda omits nonexistent files from raw_data. Recover their position from
    # its search templates instead of giving a new user file highest priority.
    source_order = []
    for template in SEARCH_PATH:
        expanded = Path(
            custom_expandvars(
                template,
                os.environ,
                CONDA_ROOT=ctx.root_prefix,
                CONDA_PREFIX=ctx.target_prefix,
            )
        ).expanduser()
        if expanded == path:
            source_order.append(path)
        else:
            source_order.extend(ctx._expand_search_path((expanded,)))
    later_sources = (
        set(source_order[source_order.index(path) + 1 :])
        if path in source_order
        else set()
    )
    for source, parameters in ctx.raw_data.items():
        if str(source) == str(path):
            data[path] = raw
            inserted = True
        else:
            if not inserted and (
                source in later_sources or str(source) in ("envvars", "cmd_line")
            ):
                data[path] = raw
                inserted = True
            data[source] = {
                key: copy(parameter) for key, parameter in parameters.items()
            }
    if not inserted:
        data[path] = raw
    result = Context(search_path=())
    result.raw_data.clear()
    result.raw_data.update(data)
    return result


def fingerprint(path: Path) -> str | None:
    if path.is_symlink():
        raise CondaError("Refusing to replace a symbolic-link configuration file.")
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


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
) -> dict[str, Any]:
    validate_catalog(catalog, ctx)
    if all_features:
        if operation != "disable" or name is not None:
            raise CondaError("Use disable --all without a feature name.")
        selected = [
            key for key, (_, feature) in catalog.items() if scope in feature.scopes
        ]
    elif name in catalog:
        selected = [name]
    else:
        raise CondaError(f"Unknown feature: {name}")
    initial = fingerprint(path)
    config = ConfigurationFile(path=path, context=ctx)
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
        if scope not in feature.scopes:
            raise CondaError(f"Feature {key} does not support scope {scope}.")
        if operation == "configure":
            requested = settings or {}
            if not requested or set(requested) - set(feature.settings):
                raise CondaError(f"Only declared settings for {key} may be configured.")
        elif operation in ("enable", "disable"):
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
        if key not in selected and value(candidate, feature.enabled_setting):
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
                config.set_key(key, new_value)
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
