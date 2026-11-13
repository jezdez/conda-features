# Install into the conda runtime

Install `conda-features` into the Python environment that runs conda. Installing it only into a project environment does not make it discoverable by a different conda executable.

## From this checkout with Pixi

```sh
pixi install
pixi run python -m conda feature --help
```

The default environment installs the core plugin but no example providers. An empty result from `feature list` is expected.

To make the real provider declarations available:

```sh
pixi install -e examples
pixi run -e examples python -m conda feature list
```

The `examples` environment contains the declarations, not necessarily the upstream deployment prerequisites. An enable preview may propose installing those prerequisites into that environment. Use `integration` instead to provision the prerequisites through Pixi before trying a deployment.

## Into an existing installation

Use that installation's Python, with conda 26.9.4 or newer already installed:

```sh
python -m pip install .
python -m conda feature --help
```

These are source-checkout instructions, not a claim that a release is available on PyPI or a conda channel. Pip is not a way to bootstrap the required conda runtime.

To install the example declarations from the checkout into the same runtime:

```sh
python -m pip install ./packages/conda-features-examples
python -m conda feature list
```

Installing declarations alone does not enable either feature. Read the [provider deployment guide](deploy-providers.md) before confirming their setup.

## Check discovery

```sh
python -m conda feature list --json
python -m conda feature explain conda-pypi --json
```

The second command requires the examples distribution. If the subcommand is missing, check which Python and conda executables your shell selects and whether third-party plugins have been disabled. If the command exists but the catalog is empty, install a feature provider into the same runtime. Provider errors name the failing entry point. A feature hook must use `conda_features.hooks.hookimpl`, not conda's hook marker.

## Upgrade without losing recovery information

The current deployment receipt format is version 2. Preserve receipts when upgrading. If a new provider cannot read a receipt or no longer declares its step IDs, restore the prior provider version and disable the deployment before upgrading. The plugin refuses unsupported receipts rather than guessing how to undo them.

Removing a provider package does not undo its configuration, shell hook, or other resources. Disable owned deployments first when that is your intent. See [recovery](recover.md) for removed-provider receipts.
