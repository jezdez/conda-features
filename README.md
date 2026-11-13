# conda-features

A conda plugin for discovering and configuring optional features supplied by installed providers.

This is an initial implementation. It adds `conda feature` commands for settings and provider-owned deployments. Without an installed feature provider, `conda feature list` returns an empty list. Deployment providers can install their missing prerequisites after confirmation.

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

Use `enable FEATURE --with-dependencies` to preview prerequisite opt-ins at the selected scope. Nothing is enabled in another scope implicitly. Already-enabled prerequisites are reused, including inherited user or installation choices. Prerequisites with unsupported write scopes or cycles are rejected. Combined prerequisite plans support settings and channels. Deploy missing package or shell-setup prerequisites separately before retrying, so readiness is checked against real deployment results rather than assumed success.

Shared user and installation changes check the current user's conda environment registry and the hosting installation. Add `--check-prefix PATH` for each additional environment that must be protected. The preview lists checked environments and explains that unregistered environments and other users' registries are not scanned. These checks never write to the other environments. Changes that would remove an enabled dependent's prerequisite are refused, including bulk disable. An environment configuration changed after preview requires a new preview.

Configuration writes preserve comments and unrelated settings, reject stale destination files, and use atomic replacement. A sidecar lock coordinates this plugin's writers. Other editors do not honor that lock.

## Deployment Providers

The separate `conda-features-examples` package contains working deployment providers that could move into their upstream projects. Use the opt-in examples environment:

```sh
pixi install -e examples
pixi run -e examples python -m conda feature list
pixi run -e examples python -m conda feature explain conda-pypi
pixi run -e examples python -m conda feature enable conda-pypi --dry-run
pixi run -e examples test-examples
```

`conda-pypi` installs missing `conda-pypi` and `conda-rattler-solver` packages, selects `solver: rattler`, and appends the `conda-pypi` channel. It supports user and environment configuration scopes. `conda-completion` installs the upstream completion package, generates completion data without fetching repodata, and installs its shell hook. Choose a shell with `configure conda-completion plugins.feature_completion_shell=zsh`. Supported shells are bash, zsh, fish, and powershell.

These commands have real side effects. Package installation targets the Python environment running conda, even if `--prefix` selects another configuration environment. Package plans use conda-forge and reject replacement of existing packages in the running installation. Dry-run may fetch repodata and update package-manager caches while solving, but does not install packages or change configuration or shell hooks.

`--file /path/to/demo.yaml` isolates conda settings, not the shell home or package installation. Completion install writes to the current user's shell configuration. Review the displayed shell path before confirming. Use an isolated home and a disposable conda installation for experiments.

Deployment receipts beside the selected configuration file record which changes belong to a provider. Disable restores owned PyPI configuration or removes an unchanged, owned completion hook. Pre-existing hooks and later edits are preserved. Installed packages and completion caches remain. Deploy or disable these providers individually rather than through `disable --all`.

The integration environment supplies the real prerequisites and exercises configuration and shell changes in temporary homes:

```sh
pixi install -e integration
pixi run -e integration test-integration
```

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

For deployment rather than a boolean setting, declare steps:

```python
from conda_features.models import Feature
from conda_features.steps import EnsureChannel, InstallPackages, SetSetting

Feature(
    name="conda-pypi",
    description="Enable PyPI support",
    steps=(
        InstallPackages("conda-pypi>=0.13", "conda-rattler-solver>=26.10"),
        SetSetting("solver", "rattler"),
        EnsureChannel("conda-pypi"),
    ),
)
```

`Feature` plans the steps in order and disables them in reverse order. Core code owns receipts, stale-plan checks, and partial-failure reporting. Package steps leave packages installed on disable. Setting steps restore only values they changed. Channel steps remove only their channel, preserving later additions.

Use one `InstallPackages` step per feature, passing all package specifications together, and at most one `EnsureChannel` step. Duplicate resource writers are rejected because their independent previews would otherwise become stale during application. Settings managed by `SetSetting` cannot also be owned by another feature.

Channel claims must also be unique across features. Put a channel needed by several features in a shared prerequisite feature. The planner validates the combined configuration before applying steps. Setting values are normalized through conda, including booleans and enum settings. Channel receipts store a digest for cleanup comparisons, not copies of inherited channel URLs.

Provider-specific steps implement `Step.check`, `plan`, and `apply`, with a stable `id`. `check` performs local inspection only. `plan` returns a `StepPlan` with a public change description, private apply data, and serializable ownership state. `apply` receives a checkpoint callback to save additional recovery state before a side effect. Keep secrets out of public descriptions and receipts. `ManagedBlock` supplies ownership and recovery for generated blocks in user files. The completion provider only supplies its shell paths, hook recognition, rendering, and upstream install command.

Changing step IDs or using an older deployment receipt is refused rather than guessing how to undo it. The current receipt format is version 2. Disable deployments with the previous provider version before upgrading. Existing boolean-setting providers continue to work.

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

- No authentication, migrations, telemetry, export, or `conda doctor` integration. Automatic prerequisite installation is provided by the two deployment adapters, not a remote feature catalog.
- Environment checks cover explicit targets and the current user's registry, not every environment on the machine. Prerequisite opt-ins require `--with-dependencies` and confirmation.
- Runtime activity is not observed. Providers must check their own settings and prerequisites before executing optional behavior.
- Native verification has covered macOS with conda 26.9.4. The lockfile also includes Linux and Windows, but those platforms have not been tested natively.
