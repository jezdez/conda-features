"""Feature management for conda.

Install this distribution in the Python environment running conda. During
development, ``pixi run python -m conda feature --help`` uses that environment.

User commands::

    conda feature list
    conda feature explain sample
    conda feature enable sample --dry-run
    conda feature enable sample --yes
    conda feature configure sample plugins.sample_limit=4 --yes
    conda feature disable sample --yes
    conda feature disable --all --yes

Use ``--prefix PATH`` for an existing environment, ``--system`` for the conda
installation, or ``--user`` (the default). Providers declare supported scopes.
``--file PATH`` selects a standalone user-scope file, with environment-variable
overrides still applied. Use a conda-recognized name (``.condarc``, ``condarc``,
or a YAML extension). Its parent directory must exist. Other scopes use
conda's normal configuration search path. ``--json`` produces one JSON result.
Exit codes are 0 for success or preview, 1 for an operation error, and 2 for
argument parsing errors. Noninteractive mutations require ``--yes``.

Providers register their settings with conda's ``conda_settings`` hook and
publish a tuple of ``conda_features.models.Feature`` objects through a Python
entry point. For example, in their pyproject.toml::

    [project.entry-points.conda_features]
    my-provider = "my_provider.features:FEATURES"

An example declaration::

    from conda_features.models import Feature

    FEATURES = (
        Feature(
            name="sample",
            description="Enable the provider's optional behavior",
            enabled_setting="plugins.sample_enabled",
            settings=("plugins.sample_limit",),
        ),
    )

The provider reads its boolean setting to control behavior. This plugin does
not intercept provider execution. Declarations must be cheap to import and
must not access the network, credentials, or files. Installed providers are
trusted Python code, not sandboxed data. Only expose non-secret settings.
Required settings check for missing values, not login or service availability.
Status reports the selected file's saved choice separately from the effective
boolean setting and readiness. Runtime activity is unknown, even when a setting
is enabled and a prerequisite is blocked. Providers enforce their own checks.

Enable refuses unmet dependencies instead of implicitly opting into them.
Disable preserves other settings and installed packages. Changes take effect
on the next invocation. Repeating a persisted operation requires no write.
An explicit disable is saved even if a temporary override already disables it.
Writes preserve comments and unrelated settings, use atomic file replacement,
and reject previews whose destination changed. A sidecar lock coordinates this
plugin's writers, but external editors do not honor it.

This initial implementation has no bundled features. Without a provider,
``list`` reports an empty catalog. Package installation, authentication,
cross-environment dependency scanning, telemetry, migrations, export, and
doctor integration are not implemented. Tests use an isolated sample provider,
not an integration with the hypothetical PyPI feature in DESIGN.md.
"""
