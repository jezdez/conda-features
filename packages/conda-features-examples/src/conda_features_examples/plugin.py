"""Configuration for the completion deployment provider."""

from conda.common.configuration import PrimitiveParameter
from conda.plugins import hookimpl
from conda.plugins.types import CondaSetting


@hookimpl
def conda_settings():
    yield CondaSetting(
        "feature_completion_shell",
        "Shell to configure when deploying conda-completion.",
        PrimitiveParameter(
            "bash",
            element_type=str,
            validation=lambda value: value in ("bash", "zsh", "fish", "powershell"),
        ),
    )
