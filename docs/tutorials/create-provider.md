# Build your first feature provider

Build a small provider whose optional greeting is controlled by `conda feature`. It registers its own non-secret settings, declares one boolean feature, and implements `conda provider-demo` to consume those settings. It does not install prerequisites, edit shell files, or use deployment receipts.

Use Python 3.12 and conda 26.9.4 for the example. You need an existing conda installation to create a disposable runtime, a local checkout of `conda-features`, and a POSIX shell for the commands below. Pip installs the Python projects only after conda and their dependencies are provisioned. Native Windows command syntax is not covered here.

See the [provider reference](../reference/providers.md) for every declaration field and the [CLI reference](../reference/cli.md) for scope and confirmation options. Return to the [documentation index](../index.md).

## 1. Create the package

Create a separate directory with these four files:

```text
conda-provider-demo/
  pyproject.toml
  src/
    conda_provider_demo/
      __init__.py
      plugin.py
      features.py
```

Use this `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling>=1.26"]
build-backend = "hatchling.build"

[project]
name = "conda-provider-demo"
version = "0.1.0"
description = "A small conda-features provider"
requires-python = ">=3.12"
dependencies = ["conda>=26.9.4", "conda-features>=0.2.0"]

[project.entry-points.conda]
conda-provider-demo = "conda_provider_demo.plugin"

[project.entry-points.conda_features]
conda-provider-demo = "conda_provider_demo.features"

[tool.hatch.build.targets.wheel]
packages = ["src/conda_provider_demo"]
```

The `conda` entry point supplies settings and the demonstration command. The separate `conda_features` entry point supplies the feature declaration. Its entry-point name identifies the provider in feature status.

Use this `src/conda_provider_demo/__init__.py`:

```python
"""A small conda-features provider."""
```

## 2. Register settings and consume them

Use this `src/conda_provider_demo/plugin.py`:

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from conda import CondaError
from conda.base.context import Context, context
from conda.cli.helpers import add_output_and_prompt_options
from conda.common.configuration import PrimitiveParameter
from conda.plugins import hookimpl
from conda.plugins.types import CondaSetting, CondaSubcommand

if TYPE_CHECKING:
    from argparse import ArgumentParser, Namespace
    from collections.abc import Iterator


@hookimpl
def conda_settings() -> Iterator[CondaSetting]:
    yield CondaSetting(
        name="demo_enabled",
        description="Use the configured demonstration greeting",
        parameter=PrimitiveParameter(False, element_type=bool),
    )
    yield CondaSetting(
        name="demo_greeting",
        description="Public greeting text used by the demonstration command",
        parameter=PrimitiveParameter("Welcome", element_type=str),
    )


def configure_parser(parser: ArgumentParser) -> None:
    add_output_and_prompt_options(parser)
    parser.add_argument("--name", default="Ada")
    parser.add_argument(
        "--file", required=True, help="Read only this YAML file and env overrides"
    )


def run(args: Namespace) -> int:
    path = Path(args.file).expanduser().absolute()
    ctx = Context(search_path=(path,))
    enabled = ctx.plugins.demo_enabled
    greeting = ctx.plugins.demo_greeting if enabled else "Hello"
    if enabled and greeting in (None, ""):
        raise CondaError("Configure plugins.demo_greeting before using this feature.")
    result = {"message": f"{greeting}, {args.name}!", "feature_enabled": enabled}
    if context.json:
        print(json.dumps(result))
    else:
        print(result["message"])
    return 0


@hookimpl
def conda_subcommands() -> Iterator[CondaSubcommand]:
    yield CondaSubcommand(
        name="provider-demo",
        summary="Print a greeting using the demonstration feature",
        action=run,
        configure_parser=configure_parser,
    )
```

Conda setting registration uses names without `plugins.`. A feature declaration uses `plugins.demo_enabled` and `plugins.demo_greeting`. The runtime reads the effective values from `ctx.plugins`, after conda applies defaults, the selected file, and environment overrides.

The command requires `--file` and constructs `Context(search_path=(path,))` to match the configuration selection of `conda feature --file`. Ordinary providers usually consume `conda.base.context.context` for the invocation's normal configuration and target. Setting `CONDARC` would still allow other files in conda's normal search path.

The optional behavior is in `run`, which chooses the configured greeting only when the flag is true. Its empty-value check also runs there. A `Feature` declaration does not intercept this command or enforce runtime checks for it. The parser uses conda's standard output options once, and JSON output is one complete object.

Only public greeting text belongs in these settings. Do not adapt `demo_greeting` into a password or token setting. Configuration queries and previews can show it.

## 3. Declare the feature

Use this `src/conda_provider_demo/features.py`:

```python
from __future__ import annotations

from collections.abc import Iterable

from conda_features.hooks import hookimpl
from conda_features.models import Feature


@hookimpl
def conda_features() -> Iterable[Feature]:
    yield Feature(
        name="demo-greeting",
        description="Use a configurable public greeting in provider-demo",
        enabled_setting="plugins.demo_enabled",
        settings=("plugins.demo_greeting",),
        required_settings=("plugins.demo_greeting",),
        scopes=("user",),
        guidance="Run conda provider-demo --file PATH --name Ada.",
    )
```

The feature starts at the default maturity, `experimental`. Its boolean setting defaults to false, and its required greeting has the nonempty default `Welcome`. A required setting's effective value cannot be `None` or an empty string when enabling. The default satisfies this check, so enable can succeed before an explicit greeting is saved.

The enabled flag is not in `settings` because users change it through enable and disable. The declaration permits only user scope, which includes an explicit `--file` destination.

Keep this hook cheap. It yields local declarations without contacting a service, reading credentials, or performing setup. Import its `hookimpl` from `conda_features.hooks`. The hooks in `plugin.py` use conda's decorator.

## 4. Install in a disposable conda runtime

Set these variables to the absolute paths of your existing checkout and the provider directory you just created:

```sh
CONDA_FEATURES_SOURCE=/absolute/path/to/conda-features
PROVIDER_SOURCE=/absolute/path/to/conda-provider-demo
DEMO=$(mktemp -d "${TMPDIR:-/tmp}/conda-provider-demo.XXXXXX") || exit 1
test -n "$DEMO" && test -d "$DEMO"
```

Stop if directory creation or the check fails. Keep this shell open so the following commands use the same variables.

Provision the host runtime through conda:

```sh
conda create --prefix "$DEMO/runtime" --override-channels --channel conda-forge \
  python=3.12 conda=26.9.4 pip "hatchling>=1.26" "filelock>=3.16" "pluggy>=1.5" --yes
```

This installs packages in the disposable prefix and can update conda's package caches and environment registry. It does not install the demo into your ordinary conda environment. Package acquisition is an explicit setup operation, separate from feature enable.

Install both projects with the new runtime's Python:

```sh
"$DEMO/runtime/bin/python" -m pip install --no-deps --no-build-isolation \
  -e "$CONDA_FEATURES_SOURCE" -e "$PROVIDER_SOURCE"
```

`--no-deps --no-build-isolation` relies on the dependencies provisioned above. Both editable projects are discovered by that same interpreter. Use `"$DEMO/runtime/bin/python" -m conda` for the remaining commands to run them in the disposable runtime.

Use a fresh configuration filename. Its parent already exists:

```sh
CONFIG="$DEMO/demo.yaml"
unset CONDA_PLUGINS_DEMO_ENABLED CONDA_PLUGINS_DEMO_GREETING
```

The explicit feature destination reads only that file plus environment-variable overrides. Do not set `CONDA_NO_PLUGINS=true`, which disables the conda hooks needed by this example. Other inherited conda variables can still influence startup, so diagnose unexpected overrides before changing the provider.

## 5. Discover and preview

```sh
"$DEMO/runtime/bin/python" -m conda feature list --file "$CONFIG"
"$DEMO/runtime/bin/python" -m conda feature explain demo-greeting --file "$CONFIG" --json
"$DEMO/runtime/bin/python" -m conda provider-demo --file "$CONFIG" --name Ada
"$DEMO/runtime/bin/python" -m conda feature enable demo-greeting --file "$CONFIG" --dry-run
```

The catalog contains `demo-greeting` from provider `conda-provider-demo`. With no saved configuration or overrides, explain reports `requested: unset`, `effective: disabled`, `readiness: ready`, and `runtime: unknown`. The demonstration command prints:

```text
Hello, Ada!
```

The dry-run previews setting `plugins.demo_enabled` to true. It does not write the configuration. There are no package or shell steps in this provider.

## 6. Configure, enable, and run

Preview a greeting change, then explicitly approve it:

```sh
"$DEMO/runtime/bin/python" -m conda feature config demo-greeting \
  --set plugins.demo_greeting Goodbye --file "$CONFIG" --dry-run
"$DEMO/runtime/bin/python" -m conda feature config demo-greeting \
  --set plugins.demo_greeting Goodbye --file "$CONFIG" --yes
"$DEMO/runtime/bin/python" -m conda feature enable demo-greeting --file "$CONFIG" --yes
"$DEMO/runtime/bin/python" -m conda provider-demo --file "$CONFIG" --name Ada --json
```

The last command emits:

```json
{"message": "Goodbye, Ada!", "feature_enabled": true}
```

The selected YAML file now holds these values, although formatting may differ:

```yaml
plugins:
  demo_greeting: Goodbye
  demo_enabled: true
```

Each command starts a fresh process, so the consumer sees the saved change on its next invocation. Without `--yes`, an interactive mutation asks for confirmation. A noninteractive mutation without confirmation refuses to write. Use `--json` for structured results from feature commands too.

Check saved and effective state separately:

```sh
"$DEMO/runtime/bin/python" -m conda feature explain demo-greeting --file "$CONFIG" --json
```

Both choices should now be enabled. `runtime` remains `unknown` even after the demonstration command ran, because `conda-features` does not observe or record that execution.

## 7. Disable and preserve configuration

```sh
"$DEMO/runtime/bin/python" -m conda feature disable demo-greeting --file "$CONFIG" --dry-run
"$DEMO/runtime/bin/python" -m conda feature disable demo-greeting --file "$CONFIG" --yes
"$DEMO/runtime/bin/python" -m conda provider-demo --file "$CONFIG" --name Ada --json
```

The command returns:

```json
{"message": "Hello, Ada!", "feature_enabled": false}
```

Disable saves a false flag. It does not remove `demo_greeting`, uninstall either project, or delete the configuration file. A later enable reuses `Goodbye`. Boolean features do not create deployment receipts.

## 8. Repeat the setup in another file

Read the saved greeting, then configure and enable the feature in a second standalone file:

```sh
"$DEMO/runtime/bin/python" -m conda feature config demo-greeting \
  --get plugins.demo_greeting --file "$CONFIG"
"$DEMO/runtime/bin/python" -m conda feature config demo-greeting \
  --set plugins.demo_greeting Goodbye --file "$DEMO/other.yaml" --dry-run
"$DEMO/runtime/bin/python" -m conda feature config demo-greeting \
  --set plugins.demo_greeting Goodbye --file "$DEMO/other.yaml" --yes
"$DEMO/runtime/bin/python" -m conda feature enable demo-greeting \
  --file "$DEMO/other.yaml" --dry-run
"$DEMO/runtime/bin/python" -m conda feature enable demo-greeting \
  --file "$DEMO/other.yaml" --yes
"$DEMO/runtime/bin/python" -m conda provider-demo --file "$DEMO/other.yaml" --name Ada
```

The last command prints `Goodbye, Ada!`. The original file remains disabled with its greeting preserved. The second file now saves the greeting and an enabled flag. To repeat this setup on another machine, install the provider in the conda runtime there first, then run the configuration and enable commands with that machine's destination.

## Adapt the provider

Choose distinctive feature IDs and setting names before publishing. Feature IDs, setting ownership, and declared channel claims must not collide with another installed provider. Prefer settings owned by your plugin over unrelated conda options used as demonstration switches.

If the real feature needs files, channels, or package prerequisites, replace the boolean flag model with a `steps` tuple and omit `enabled_setting`. Reuse `InstallPackages`, `SetSetting`, and `EnsureChannel` before writing custom steps. Use `ManagedBlock` for a generated block whose exact content and ownership can be checked. See the [step reference](../reference/providers.md#custom-step-interface) and [deployment explanation](../explanation/deployment.md).

`--file` does not isolate package installation or shell paths. Use a disposable host runtime and home for deployment tests. Keep step IDs stable, checkpoint ownership before effects, preserve pre-existing resources, and test interrupted enable and disable. Do not add a shell installer to this example and run it against your normal home.

## Troubleshoot

| Symptom | Check |
| --- | --- |
| `feature` is not a recognized subcommand | The interpreter running conda must have `conda-features` installed and conda plugins enabled. |
| `provider-demo` is not a recognized subcommand | Check the `conda` entry point and editable installation in the host interpreter. Start a new process after installation. |
| The feature list is empty | Check the `conda_features` entry point, its module path, and the decorator imported by `features.py`. Installing source only in another target environment does not register it here. |
| A setting is not registered | Check the `conda_settings` hook and names. Registration omits `plugins.`, while feature declarations include it. |
| A provider cannot load or collect features | Import the named module with the host Python and fix its import or hook error. Discovery does not skip broken providers. |
| A write is overridden | Check explain's configuration sources and inherited environment variables. Do not force-write around the effective-value check. |
| A required value is missing | Configure a nonempty greeting, then enable again. The consumer also rejects an empty effective greeting while enabled. |
| An environment-scope command is refused | This example deliberately declares only user scope. Add another scope only when the actual provider behavior supports it. |

## Check before publishing

Exercise installed discovery and the complete configure, enable, consume, disable sequence in fresh processes. Verify text and JSON output, empty required settings, environment overrides, dry-run, and cancellation. Use conda's test fixtures and temporary configuration paths instead of reading the developer's normal settings. Add platform-specific tests before claiming support beyond the environments you have exercised.

These commands install a development checkout. Publish and version your distribution through your project's normal process. Testing this checkout does not verify compatibility with future conda versions allowed by its dependency specifier.

## Remove the disposable runtime

After finishing, close processes using the demo runtime and remove that environment with the original conda installation:

```sh
conda remove --prefix "$DEMO/runtime" --all --yes
```

The temporary directory still contains your demonstration configuration and lock files. Inspect and delete only the directory recorded in `$DEMO` when no longer needed. Your provider source directory and `conda-features` checkout remain unchanged by environment removal. Conda's shared package caches may remain as well.
