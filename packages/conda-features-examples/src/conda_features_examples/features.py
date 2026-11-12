"""Example declarations with no installation, network, or shell side effects."""

from conda_features.hooks import hookimpl
from conda_features.models import Feature


@hookimpl
def conda_features():
    yield Feature(
        name="conda-pypi",
        description="UX example: opt into PyPI package support",
        enabled_setting="plugins.example_pypi_enabled",
        maturity="preview",
        scopes=("user", "environment"),
        guidance="Simulation only. No PyPI provider, packages, or channels were installed or configured.",
    )
    yield Feature(
        name="conda-completions",
        description="UX example: choose shell completions",
        enabled_setting="plugins.example_completions_enabled",
        maturity="stable",
        scopes=("user",),
        settings=("plugins.example_completions_shell",),
        guidance="Simulation only. Configure plugins.example_completions_shell to choose bash, zsh, fish, or powershell. No shell files are changed.",
    )
