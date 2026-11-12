"""Installed only into subprocess test discovery, never shipped as a feature."""

from conda.common.configuration import PrimitiveParameter
from conda.plugins import hookimpl
from conda.plugins.types import CondaSetting

from conda_features.models import Feature

FEATURES = (
    Feature(
        "sample",
        "A test capability",
        "plugins.sample_enabled",
        maturity="stable",
        scopes=("user", "environment"),
        settings=("plugins.sample_limit", "plugins.sample_label"),
        guidance="Use the sample provider.",
    ),
)


@hookimpl
def conda_settings():
    yield CondaSetting(
        "sample_enabled", "Test feature", PrimitiveParameter(False, element_type=bool)
    )
    yield CondaSetting(
        "sample_limit",
        "Test limit",
        PrimitiveParameter(1, element_type=int, validation=lambda value: value > 0),
    )
    yield CondaSetting(
        "sample_label", "Test label", PrimitiveParameter("", element_type=str)
    )
