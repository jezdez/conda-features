"""Load and validate feature declarations from installed providers."""

import re
from importlib.metadata import entry_points

from conda import CondaError
from conda.base.context import Context
from conda.models.version import VersionSpec

from ..models import Catalog, Feature


def discover() -> Catalog:
    features = {}
    for entry in entry_points(group="conda_features"):
        try:
            declarations = entry.load()
        except Exception as exc:
            raise CondaError(f"Cannot load feature provider {entry.name!r}.") from exc
        if not isinstance(declarations, tuple):
            raise CondaError(
                f"Provider {entry.name!r} must expose a tuple of Feature declarations."
            )
        for feature in declarations:
            if not isinstance(feature, Feature):
                raise CondaError(f"Invalid feature declaration from {entry.name!r}.")
            if feature.name in features:
                raise CondaError(f"Duplicate feature ID: {feature.name}")
            features[feature.name] = (entry.name, feature)
    return dict(sorted(features.items()))


def validate_catalog(catalog: Catalog, ctx: Context) -> None:
    from .configuration import setting_context

    owners = {}
    for name, (_, feature) in catalog.items():
        if name != feature.name or not re.fullmatch(r"[a-z][a-z0-9_-]*", name):
            raise CondaError(f"Invalid feature ID: {name!r}")
        if feature.maturity not in ("experimental", "preview", "stable"):
            raise CondaError(f"Invalid maturity for {name}.")
        if not feature.scopes or set(feature.scopes) - {
            "user",
            "system",
            "environment",
        }:
            raise CondaError(f"Invalid scopes for {name}.")
        if not set(feature.required_settings) <= set(feature.settings):
            raise CondaError(
                f"Required settings for {name} must be declared in settings."
            )
        if feature.enabled_setting in feature.settings:
            raise CondaError(f"Use enable/disable to change {name}'s boolean setting.")
        for key in (feature.enabled_setting, *feature.settings):
            if key in owners:
                raise CondaError(
                    f"Setting {key} is declared more than once ({owners[key]}, {name})."
                )
            owners[key] = name
            config, parameter = setting_context(ctx, key)
            if parameter not in config.list_parameters():
                raise CondaError(
                    f"Setting {key} for {name} is not registered with conda."
                )
            description = config.describe_parameter(parameter)
            if key == feature.enabled_setting:
                if description["parameter_type"] != "primitive" or description[
                    "element_types"
                ] != ("bool",):
                    raise CondaError(
                        f"Feature {name} requires a boolean enabled setting."
                    )
            elif description["parameter_type"] != "primitive":
                raise CondaError(f"Setting {key} must be scalar.")
        try:
            VersionSpec(feature.conda_version)
        except Exception as exc:
            raise CondaError(f"Invalid conda version requirement for {name}.") from exc
