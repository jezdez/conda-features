"""Pluggy interface for installed feature providers."""

from collections.abc import Iterable

from pluggy import HookimplMarker, HookspecMarker

from .models import Feature

hookimpl = HookimplMarker("conda_features")
hookspec = HookspecMarker("conda_features")


class FeatureSpecs:
    @hookspec
    def conda_features(self) -> Iterable[Feature]:
        """Yield local feature declarations without performing setup or I/O."""
        raise NotImplementedError
