"""Real deployment providers suitable for moving into their upstream packages."""

from conda_features.hooks import hookimpl
from conda_features.models import Feature
from conda_features.steps import EnsureChannel, InstallPackages, SetSetting

from .completion import InstallCompletionHook


@hookimpl
def conda_features():
    yield Feature(
        name="conda-pypi",
        description="Install and configure PyPI support with the Rattler solver",
        maturity="preview",
        scopes=("user", "environment"),
        steps=(
            InstallPackages("conda-pypi>=0.13", "conda-rattler-solver>=26.10"),
            SetSetting("solver", "rattler"),
            EnsureChannel("conda-pypi"),
        ),
        guidance="Use conda install with packages from the conda-pypi channel. Disabling restores owned configuration, not installed packages.",
    )
    yield Feature(
        name="conda-completion",
        description="Install shell completion and generate completion data",
        maturity="stable",
        scopes=("user",),
        settings=("plugins.feature_completion_shell",),
        steps=(InstallPackages("conda-completion==0.3.2"), InstallCompletionHook()),
        guidance="Restart your shell after enabling or disabling. Ensure its conda command uses the installation hosting conda-completion.",
    )
