"""Conda settings used only by the example features."""

from conda.common.configuration import PrimitiveParameter
from conda.plugins import hookimpl
from conda.plugins.types import CondaSetting


@hookimpl
def conda_settings():
    yield CondaSetting(
        "example_pypi_enabled",
        "Enable the PyPI UX example (no packages are installed).",
        PrimitiveParameter(False, element_type=bool),
    )
    yield CondaSetting(
        "example_completions_enabled",
        "Enable the completions UX example (no shell files are changed).",
        PrimitiveParameter(False, element_type=bool),
    )
    yield CondaSetting(
        "example_completions_shell",
        "Shell selection for the completions UX example.",
        PrimitiveParameter(
            "bash",
            element_type=str,
            validation=lambda value: value in ("bash", "zsh", "fish", "powershell"),
        ),
    )
