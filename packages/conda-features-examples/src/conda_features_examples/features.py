"""Real deployment providers suitable for moving into their upstream packages."""

from conda_features.hooks import hookimpl

from .completion import CompletionFeature
from .pypi import PyPIFeature


@hookimpl
def conda_features():
    yield PyPIFeature(
        name="conda-pypi",
        description="Install and configure PyPI support with the Rattler solver",
        maturity="preview",
        scopes=("user", "environment"),
        guidance="Use conda install with packages from the conda-pypi channel. Disabling restores owned configuration, not installed packages.",
    )
    yield CompletionFeature(
        name="conda-completion",
        description="Install shell completion and generate completion data",
        maturity="stable",
        scopes=("user",),
        settings=("plugins.feature_completion_shell",),
        guidance="Restart your shell after enabling or disabling. Ensure its conda command uses the installation hosting conda-completion.",
    )
