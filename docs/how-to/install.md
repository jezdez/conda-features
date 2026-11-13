# Install into the conda runtime

You need Python 3.12 or newer and conda 26.9.4 or newer. Install `conda-features` into the Python environment that runs conda. Installing it only into a project environment does not make it discoverable by a different conda executable.

## Select the host interpreter

Run this with the Python interpreter belonging to your conda installation:

```sh
python -m conda --version
```

If Python cannot import conda, stop and select the host interpreter rather than installing the plugin there. In a conventional conda installation, that interpreter is in base. Activating a project environment can put a different Python on your path while leaving the `conda` shell command connected to the original installation. Installations with a separate managed conda runtime may have a different host from base.

Use an absolute path to the host Python in the commands below if needed. If bare `conda` selects another installation, use `python -m conda` with that same host interpreter for feature commands too. Do not install into a conda runtime managed by another application without following that application's installation guidance.

## Install release 0.1.0

The core package is published on [PyPI](https://pypi.org/project/conda-features/0.1.0/) and [Anaconda.org](https://anaconda.org/jezdez/conda-features). Choose one installation method.

For a conventional conda installation whose runtime is base:

```sh
conda install --name base --override-channels --channel conda-forge \
  --channel jezdez conda-features=0.1.0
```

The conda package declares its conda runtime dependency. Review the proposed transaction before accepting. If your conda host is not base, select its actual environment instead. Do not use a project environment merely because it is active.

For pip, select the host interpreter as described above:

```sh
python -m pip install conda-features==0.1.0
```

The PyPI package deliberately does not ask pip to install conda. Conda must already be available in that interpreter. Neither method needs Pixi or a source checkout.

## Add the repository's deployment examples

The core installs the command but no feature declarations. `conda-features-examples` is intentionally not published to PyPI or Anaconda.org. To try its real PyPI and completion deployments, install it from the matching repository tag into the same runtime. This step requires Git and pip:

```sh
python -m pip install "conda-features-examples @ git+https://github.com/jezdez/conda-features.git@0.1.0#subdirectory=packages/conda-features-examples"
```

For a fixed source revision, replace the tag with a reviewed commit SHA. Contributors testing unreleased code can install from a checkout using the [development guide](develop.md).

The examples distribution contains working deployment declarations, despite its name. Installing it does not select a solver, add a channel, install a completion hook, or preinstall all deployment prerequisites. Those changes are proposed by `conda feature enable` and require confirmation.

## Check discovery and preview a feature

```sh
conda feature list
conda feature explain conda-pypi
conda feature enable conda-pypi --user --dry-run
```

Use the same host's `python -m conda` instead if the bare command points elsewhere. The preview names package changes and their host prefix separately from the target configuration file. Review it before rerunning without `--dry-run`.

If the subcommand is missing, check your interpreter and whether third-party plugins are disabled. If the command exists but the catalog is empty, check that a feature provider is installed in the same runtime. Provider errors name the failing entry point. A feature hook must use `conda_features.hooks.hookimpl`, not conda's hook marker.

Continue with [your first deployment](../tutorials/first-deployment.md) or the [real provider deployment guide](deploy-providers.md). Repository contributors should use the separate [development guide](develop.md) for Pixi environments and tests.

## Upgrade without losing recovery information

The current deployment receipt format is version 2. Preserve receipts when upgrading. If a new provider cannot read a receipt or no longer declares its step IDs, restore the prior provider version and disable the deployment before upgrading. The plugin refuses unsupported receipts rather than guessing how to undo them.

Removing a provider package does not undo its configuration, shell hook, or other resources. Disable owned deployments first when that is your intent. See [recovery](recover.md) for removed-provider receipts.
