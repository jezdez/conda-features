"""Versioned, portable feature choices without machine-specific recovery state."""

from __future__ import annotations

import math
from pathlib import Path, PureWindowsPath
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

from conda import CondaError
from conda.base.context import Context
from conda.cli.condarc import ConfigurationFile

from ..steps.configuration import SetSetting
from .settings import fingerprint, prospective_context, saved_keys, saved_value, value

if TYPE_CHECKING:
    from ..models import Catalog, Feature


class IntentError(CondaError):
    """A public intent error constructed without configuration values."""


def portable_value(key: str, item: Any) -> None:
    """Reject obvious credentials and host paths in explicitly portable settings."""
    if item is not None and type(item) not in (str, int, float, bool):
        raise IntentError(f"Portable setting {key} must be scalar.")
    if isinstance(item, float) and not math.isfinite(item):
        raise IntentError(f"Portable setting {key} must be finite.")
    if isinstance(item, str):
        try:
            parsed = urlsplit(item)
        except ValueError as exc:
            raise IntentError(
                f"Portable setting {key} contains an invalid URL."
            ) from exc
        if (
            parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or "/t/" in parsed.path
        ):
            raise IntentError(
                f"Portable setting {key} contains a credential-bearing URL. Its value is not exported or applied."
            )
        if (
            parsed.scheme == "file"
            or item.startswith(("/", "~", "\\"))
            or PureWindowsPath(item).is_absolute()
        ):
            raise IntentError(
                f"Portable setting {key} contains a machine-specific path."
            )


def export_feature(
    feature: Feature, catalog: Catalog, ctx: Context, path: Path, scope: str
) -> dict[str, Any] | None:
    if scope not in feature.scopes:
        return None
    status = feature.status(catalog, ctx, None, path=path)
    if status["requested"] not in ("enabled", "disabled"):
        return None
    config = ConfigurationFile(path=path, context=ctx)
    settings = {}
    for key in feature.portable_settings:
        keys = saved_keys(config, ctx, key)
        if len(keys) > 1:
            raise IntentError(f"Reconcile saved aliases for {key} before exporting.")
        if keys:
            try:
                item = SetSetting(key, saved_value(config, keys[0])).normalized_value(
                    ctx
                )
            except (CondaError, ValueError, TypeError, OverflowError) as exc:
                raise IntentError(f"Cannot normalize portable setting {key}.") from exc
            portable_value(key, item)
            settings[key] = item
    return {
        "name": feature.name,
        "provider": catalog[feature.name][0],
        "requested": status["requested"],
        "settings": settings,
    }


def plan_intent(
    document: Any, catalog: Catalog, ctx: Context, path: Path, scope: str
) -> dict[str, Any]:
    initial = fingerprint(path)
    if (
        not isinstance(document, dict)
        or set(document) != {"version", "scope", "features"}
        or type(document["version"]) is not int
        or document["version"] != 1
    ):
        raise IntentError(
            "Unsupported feature intent document. Expected version 1 with scope and features."
        )
    if document["scope"] not in ("user", "system", "environment") or not isinstance(
        document["features"], list
    ):
        raise IntentError("Invalid intent scope or feature list.")
    selected = {}
    for entry in document["features"]:
        if not isinstance(entry, dict) or set(entry) != {
            "name",
            "provider",
            "requested",
            "settings",
        }:
            raise IntentError(
                "Each intent entry needs name, provider, requested, and settings."
            )
        name = entry["name"]
        if not isinstance(name, str) or name not in catalog:
            raise IntentError(
                "Intent refers to an unknown feature. Install its provider before applying."
            )
        if name in selected:
            raise IntentError(f"Duplicate intent entry for {name}.")
        provider, feature = catalog[name]
        if entry["provider"] != provider:
            raise IntentError(
                f"Provider identity changed for {name}. Review the declaration before applying."
            )
        if entry["requested"] not in ("enabled", "disabled") or not isinstance(
            entry["settings"], dict
        ):
            raise IntentError(f"Invalid choice or settings for {name}.")
        if (
            feature.retired
            or feature.replacement
            or feature.graduation == "unconditional"
        ):
            raise IntentError(
                f"Feature {name} is retired, replaced, or unconditional. Review feature explain and migrate before applying intent."
            )
        if scope not in feature.scopes:
            raise IntentError(
                f"Feature {name} does not support destination scope {scope}."
            )
        if set(entry["settings"]) - set(feature.portable_settings):
            raise IntentError(
                f"Intent includes settings not declared portable by {name}."
            )
        for key, item in entry["settings"].items():
            portable_value(key, item)
        selected[name] = entry
    deployments = [
        name for name in selected if catalog[name][1].enabled_setting is None
    ]
    if deployments:
        if len(selected) != 1:
            raise IntentError(
                "Apply deployment features individually so each package transaction and recovery plan can be reviewed."
            )
        name = deployments[0]
        feature = catalog[name][1]
        entry = selected[name]
        if entry["settings"]:
            raise IntentError(
                "Configure deployment settings explicitly before applying its saved choice."
            )
        return (
            feature.enable(catalog, ctx, path, scope)
            if entry["requested"] == "enabled"
            else feature.disable(catalog, ctx, path, scope)
        )
    config = ConfigurationFile(path=path, context=ctx)
    changes = {}
    remove = []
    for name, entry in selected.items():
        feature = catalog[name][1]
        assert feature.enabled_setting is not None
        values = {
            feature.enabled_setting: entry["requested"] == "enabled",
            **entry["settings"],
        }
        for key, item in values.items():
            try:
                normalized = SetSetting(key, item).normalized_value(ctx)
            except (CondaError, ValueError, TypeError, OverflowError) as exc:
                raise IntentError(f"Invalid portable value for {key}.") from exc
            portable_value(key, normalized)
            keys = saved_keys(config, ctx, key)
            if len(keys) > 1:
                raise IntentError(
                    f"Reconcile saved aliases for {key} before applying intent."
                )
            current = (
                SetSetting(key, saved_value(config, keys[0])).normalized_value(ctx)
                if keys
                else None
            )
            if not keys or current != normalized:
                if keys and keys[0] != key:
                    config.remove_key(keys[0])
                    remove.append(keys[0])
                config.set_key(key, normalized)
                changes[key] = normalized
    candidate = prospective_context(ctx, path, config.content)
    candidate.validate_configuration()
    candidate.plugins.validate_configuration()
    for name, entry in selected.items():
        feature = catalog[name][1]
        assert feature.enabled_setting is not None
        expected = entry["requested"] == "enabled"
        if value(candidate, feature.enabled_setting) != expected:
            raise IntentError(f"Feature {name} is overridden at the destination.")
        for key, item in entry["settings"].items():
            if SetSetting.scalar(value(candidate, key)) != SetSetting(
                key, item
            ).normalized_value(ctx):
                raise IntentError(
                    f"Portable setting {key} is overridden at the destination."
                )
        status = feature.status(catalog, candidate, scope)
        if expected and status["readiness"] != "ready":
            raise IntentError(
                f"Feature {name} is not ready. Inspect its prerequisites locally before applying intent."
            )
    for name, (_, feature) in catalog.items():
        after = feature.status(catalog, candidate, None)
        if after["effective"] != "enabled":
            continue
        for prerequisite in feature.requires:
            if (
                prerequisite in selected
                and selected[prerequisite]["requested"] == "disabled"
            ):
                raise IntentError(f"Enabled feature {name} requires {prerequisite}.")
        before = feature.status(catalog, ctx, None)
        if (
            before["effective"] == "enabled"
            and before["readiness"] == "ready"
            and after["readiness"] != "ready"
        ):
            raise IntentError(f"Applying intent would break enabled feature {name}.")
    return {
        "operation": "apply",
        "features": list(selected),
        "scope": scope,
        "path": str(path),
        "changes": changes,
        "remove": remove,
        "fingerprint": initial,
    }
