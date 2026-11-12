"""Pluggy interface for installed feature providers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pluggy import HookimplMarker, HookspecMarker

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .models import Feature

hookimpl = HookimplMarker("conda_features")
hookspec = HookspecMarker("conda_features")


class FeatureSpecs:
    @hookspec
    def conda_features(self) -> Iterable[Feature]:
        """Yield local feature declarations without performing setup or I/O."""
        raise NotImplementedError
