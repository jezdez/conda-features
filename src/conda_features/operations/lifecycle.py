"""Explicit replacement and obsolete opt-in cleanup plans."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from conda import CondaError
from conda.base.context import Context
from conda.cli.condarc import MISSING, ConfigurationFile

from ..steps.configuration import SetSetting
from .settings import fingerprint, prospective_context, saved_keys, saved_value, value

if TYPE_CHECKING:
    from ..models import Catalog, Feature


def migrate(
    feature: Feature, catalog: Catalog, ctx: Context, path: Path, scope: str
) -> dict[str, Any]:
    initial = fingerprint(path)
    if not feature.replacement or feature.replacement not in catalog:
        raise CondaError(
            "No installed replacement provider is available. Install the replacement provider before migrating."
        )
    replacement = catalog[feature.replacement][1]
    if replacement.name == feature.name:
        raise CondaError("A feature cannot replace itself.")
    if not feature.enabled_setting or not replacement.enabled_setting:
        raise CondaError(
            "Deployment migrations need provider-specific cleanup. Enable the replacement and disable the old deployment explicitly."
        )
    if scope not in feature.scopes or scope not in replacement.scopes:
        raise CondaError("Both features must support the selected migration scope.")
    if replacement.retired or replacement.graduation == "unconditional":
        raise CondaError(
            "The declared replacement is not an available optional feature."
        )
    config = ConfigurationFile(path=path, context=ctx)
    old = feature.status(catalog, ctx, None, path=path)
    if old["requested"] != "enabled":
        raise CondaError(
            "Migration requires an enabled choice saved at the selected scope."
        )
    changes = {feature.enabled_setting: False, replacement.enabled_setting: True}
    for source, destination in feature.migration_settings:
        if source not in feature.settings or destination not in replacement.settings:
            raise CondaError(
                "Migration settings must be declared non-secret settings on both features."
            )
        keys = saved_keys(config, ctx, source)
        if not keys:
            continue
        if len(keys) != 1:
            raise CondaError(
                f"Multiple saved aliases for {source}. Reconcile them before migrating."
            )
        saved = saved_value(config, keys[0])
        normalized = SetSetting(source, saved).normalized_value(ctx)
        destinations = saved_keys(config, ctx, destination)
        if len(destinations) > 1:
            raise CondaError(
                f"Multiple saved aliases for {destination}. Reconcile them before migrating."
            )
        existing = saved_value(config, destinations[0] if destinations else destination)
        target_value = SetSetting(destination, normalized).normalized_value(ctx)
        if (
            existing is not MISSING
            and SetSetting(destination, existing).normalized_value(ctx) != target_value
        ):
            raise CondaError(
                f"Destination setting {destination} already has a different saved choice. Preserve or reconcile it before migrating."
            )
        if existing is MISSING:
            config.set_key(destination, target_value)
            changes[destination] = target_value
    remove = []
    for key, setting in changes.items():
        for saved_key in saved_keys(config, ctx, key):
            if saved_key != key:
                config.remove_key(saved_key)
                remove.append(saved_key)
        config.set_key(key, setting)
    candidate = prospective_context(ctx, path, config.content)
    candidate.validate_configuration()
    candidate.plugins.validate_configuration()
    for key, expected in changes.items():
        if SetSetting.scalar(value(candidate, key)) != expected:
            raise CondaError(f"Migration setting {key} is overridden. No changes made.")
    status = replacement.status(catalog, candidate, scope, path=path)
    if status["readiness"] != "ready":
        raise CondaError("Replacement is not ready: " + " ".join(status["reasons"]))
    for name, (_, other) in catalog.items():
        if name == feature.name:
            continue
        before = other.status(catalog, ctx, None)
        after = other.status(catalog, candidate, None)
        if after["effective"] == "enabled" and feature.name in other.requires:
            raise CondaError(f"Enabled feature {name} still requires {feature.name}.")
        if (
            before["effective"] == "enabled"
            and before["readiness"] == "ready"
            and after["readiness"] != "ready"
        ):
            raise CondaError(f"Migration would break enabled feature {name}.")
    return {
        "operation": "migrate",
        "features": [feature.name, replacement.name],
        "path": str(path),
        "scope": scope,
        "changes": changes,
        "remove": remove,
        "fingerprint": initial,
    }


def cleanup(
    feature: Feature, catalog: Catalog, ctx: Context, path: Path, scope: str
) -> dict[str, Any]:
    initial = fingerprint(path)
    if feature.graduation != "unconditional" or not feature.enabled_setting:
        raise CondaError(
            "Cleanup is only available for a graduated unconditional feature's obsolete boolean opt-in."
        )
    if scope not in feature.scopes:
        raise CondaError(f"Unsupported scope: {scope}")
    config = ConfigurationFile(path=path, context=ctx)
    remove = saved_keys(config, ctx, feature.enabled_setting)
    for key in remove:
        config.remove_key(key)
    candidate = prospective_context(ctx, path, config.content)
    candidate.validate_configuration()
    candidate.plugins.validate_configuration()
    return {
        "operation": "cleanup",
        "features": [feature.name],
        "path": str(path),
        "scope": scope,
        "changes": {
            key: "remove obsolete opt-in (functionality remains unconditional)"
            for key in remove
        },
        "remove": remove,
        "fingerprint": initial,
    }
