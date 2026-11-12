# conda-features

A conda plugin for discovering and configuring optional features supplied by installed providers.

This is an initial implementation. It adds `conda feature` commands and manages existing conda settings. It does not install providers, perform login, or ship a built-in feature catalog. Without a provider, `conda feature list` returns an empty list.

The [design document](DESIGN.md) includes planned work beyond the current implementation.

## Try It Locally

Requires [Pixi](https://pixi.sh). The development environment uses Python 3.12 and conda 26.9.4.

```sh
pixi install
pixi run python -m conda feature --help
pixi run python -m conda feature list
```

To install the checkout into another conda installation, run this with that installation's Python, which must already have conda 26.9.4 or newer:

```sh
python -m pip install .
```

Install the plugin in the environment running conda, not merely in an environment you want to configure.

## Commands

For a provider that declares a feature named `sample`:

```sh
conda feature list
conda feature explain sample
conda feature enable sample --dry-run
conda feature enable sample --yes
conda feature configure sample plugins.sample_limit=4 --yes
conda feature disable sample --yes
conda feature disable --all --yes
```

`sample` is an example, not a bundled feature. Setting names and supported scopes come from the provider.

- `--user` is the default configuration destination.
- `--prefix PATH` targets an existing conda environment.
- `--system` targets the conda installation's configuration.
- `--file PATH` uses a standalone user-scope configuration file. Its name must be `.condarc`, `condarc`, or have a YAML extension. Its parent directory must exist.

Normal scopes use conda's configuration precedence. `--file` reads only that file plus environment-variable overrides. `explain` reports configuration sources and known prerequisites.

Status separates the choice saved in the selected file (`requested`: `enabled`, `disabled`, or `unset`) from the effective boolean setting after conda applies overrides (`effective`: `enabled` or `disabled`). `readiness` reports declared prerequisites. `runtime` is `unknown` because the plugin does not observe provider execution. An enabled setting can have blocked readiness without its execution being suppressed.

Commands reject an overriding value even when the destination already contains the requested value. The error lists other configuration sources and asks you to change or remove the override. Disabling a prerequisite is refused while any enabled dependent still requires it, including dependents already blocked for another reason.

Mutating commands preview changes with `--dry-run`. Without `--yes`, interactive commands ask for confirmation and noninteractive commands refuse changes. `--json` returns one JSON result. Exit codes are `0` for success or preview, `1` for operation errors, and `2` for argument errors.

Enabling requires compatible versions and platforms, enabled dependencies, and no declared conflicts. Disabling preserves other settings and installed packages. Bulk disable handles dependents before prerequisites where possible. Changes take effect on the next conda invocation.

Configuration writes preserve comments and unrelated settings, reject stale destination files, and use atomic replacement. A sidecar lock coordinates this plugin's writers. Other editors do not honor that lock.

## UX Examples

The separate `conda-features-examples` package provides `conda-pypi` and `conda-completions` simulations. Install them only in the opt-in examples environment:

```sh
pixi install -e examples
pixi run -e examples python -m conda feature list
pixi run -e examples python -m conda feature explain conda-pypi
pixi run -e examples python -m conda feature enable conda-pypi --dry-run
pixi run -e examples test-examples
```

These examples use `plugins.example_*` settings. They do not install real providers, add channels, fetch packages, or modify shell startup files. To try persistent changes without touching your usual configuration, add `--file /path/to/demo.yaml` to each command and use `--yes` after reviewing the preview. The file's parent directory must exist.

`conda-pypi` supports user and environment scopes. `conda-completions` supports user scope and a shell setting with `bash`, `zsh`, `fish`, and `powershell` choices. Their maturity values are sample UX data, not claims about those real projects.

## Declare a Feature

A provider registers its settings through conda's `conda_settings` hook and yields `Feature` objects from a dedicated Pluggy hook. Register both provider modules:

```toml
[project.entry-points.conda]
my-provider = "my_provider.plugin"

[project.entry-points.conda_features]
my-provider = "my_provider.features"
```

In `my_provider/plugin.py`:

```python
from conda.common.configuration import PrimitiveParameter
from conda.plugins import hookimpl
from conda.plugins.types import CondaSetting


@hookimpl
def conda_settings():
    yield CondaSetting(
        "sample_enabled",
        "Enable sample behavior",
        PrimitiveParameter(False, element_type=bool),
    )
    yield CondaSetting(
        "sample_limit",
        "Sample limit",
        PrimitiveParameter(1, element_type=int),
    )
```

In `my_provider/features.py`:

```python
from conda_features.models import Feature
from conda_features.hooks import hookimpl


@hookimpl
def conda_features():
    yield Feature(
        name="sample",
        description="Enable the provider's optional behavior",
        enabled_setting="plugins.sample_enabled",
        settings=("plugins.sample_limit",),
        scopes=("user", "environment"),
        guidance="Use the provider's sample command.",
    )
```

Providers need `conda-features` as a dependency. Feature IDs and owned setting names must be unique. The enabled setting must be boolean, and configurable settings must be non-secret scalar values. Declarations can also specify maturity, required settings, dependencies, conflicts, supported conda versions and platforms, retirement, and replacement guidance. See [`Feature`](src/conda_features/models.py) for the fields.

The provider reads `context.plugins.sample_enabled` to control its behavior. This plugin changes settings but does not intercept provider execution. Readiness describes declared checks, not proof that a remote service or login works. Providers must enforce their own runtime requirements.

Declarations should be cheap to import and must not read credentials, contact services, or run setup. Installed providers are trusted Python code, not sandboxed metadata.

## Development

```sh
pixi run test
pixi run lint
pixi run format-check
pixi run type-check
pixi run python -m hatchling build -t wheel
```

Tests use conda's CLI, context, and environment fixtures. Subprocess tests verify installed entry-point discovery and behavior across invocations. Test providers and configuration files are isolated from the user's configuration.

## Current Limits

- No automatic provider installation, authentication, migrations, telemetry, export, or `conda doctor` integration.
- No dependency scanning across other environments or automatic enabling of prerequisites.
- Runtime activity is not observed. Providers must check their own settings and prerequisites before executing optional behavior.
- Native verification has covered macOS with conda 26.9.4. The lockfile also includes Linux and Windows, but those platforms have not been tested natively.
