"""Validate feature metadata and resource ownership."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from conda import CondaError
from conda.base.context import Context
from conda.models.version import VersionSpec

from ..steps.base import Step
from ..steps.configuration import EnsureChannel, SetSetting
from ..steps.packages import InstallPackages
from .settings import setting_context

if TYPE_CHECKING:
    from ..models import Catalog


def validate_catalog(catalog: Catalog, ctx: Context) -> None:
    owners = {}
    channel_owners = {}
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
        step_settings = set()
        if feature.steps:
            if feature.enabled_setting is not None:
                raise CondaError(
                    f"Feature {name} must choose steps or an enabled setting."
                )
            ids = set()
            resources = set()
            for step in feature.steps:
                if not isinstance(step, Step):
                    raise CondaError(f"Invalid deployment step for {name}.")
                if step.id in ids:
                    raise CondaError(f"Duplicate step ID: {step.id}")
                ids.add(step.id)
                resource = (
                    "channels"
                    if isinstance(step, EnsureChannel)
                    else "packages"
                    if isinstance(step, InstallPackages)
                    else None
                )
                if resource is not None:
                    if resource in resources:
                        raise CondaError(
                            f"Duplicate resource writer: {resource}. Use one step per resource in a feature."
                        )
                    resources.add(resource)
                if isinstance(step, SetSetting):
                    step_settings.add(step.key)
                if isinstance(step, EnsureChannel):
                    if step.channel in channel_owners:
                        raise CondaError(
                            f"Channel {step.channel} is declared more than once ({channel_owners[step.channel]}, {name}). Declare a shared prerequisite feature instead."
                        )
                    channel_owners[step.channel] = name
        elif feature.enabled_setting is None:
            feature.validate_deployment_methods()
        for key in (
            *((feature.enabled_setting,) if feature.enabled_setting else ()),
            *feature.settings,
            *sorted(step_settings - set(feature.settings)),
        ):
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
