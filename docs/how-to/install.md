# Install into the conda runtime

You need Python 3.12 or newer and conda 26.9.4 or newer. Install `conda-features` into the Python environment that runs conda. A different conda executable will not discover a plugin installed only in your project environment.

## Select the host interpreter

Run this with the Python interpreter belonging to your conda installation:

```sh
python -m conda --version
```

If Python cannot import conda, switch to the host interpreter before installing the plugin. In a conventional conda installation, that interpreter is in base. Activating a project environment can put a different Python on your path while the `conda` shell command still uses the original installation. A separately managed conda runtime may use a host other than base.

Use an absolute path to the host Python in the commands below if needed. If bare `conda` selects another installation, use `python -m conda` with that same host interpreter for feature commands too. Do not install into a conda runtime managed by another application without following that application's installation guidance.

## Install release 0.2.0

The core package is distributed through [PyPI](https://pypi.org/project/conda-features/) and [Anaconda.org](https://anaconda.org/jezdez/conda-features). Choose one installation method.

For a conventional conda installation whose runtime is base:

```sh
conda install --name base --override-channels --channel conda-forge \
  --channel jezdez conda-features=0.2.0
```

The conda package declares its conda runtime dependency. Review the proposed transaction before accepting it. If your conda host is not base, select the environment that hosts it. The active project environment may not be the host.

## Optional: install the PyPI wheel through conda-pypi

Use this route if you prefer the PyPI distribution. The native package above does not require `conda-pypi`. To use the wheel channel, first install `conda-pypi` and the Rattler solver in the conda host. For a conventional base-hosted installation:

```sh
conda install --name base --override-channels --channel conda-forge \
  conda-pypi conda-rattler-solver
```

Then install the released wheel with conda:

```sh
conda install --name base --solver rattler --override-channels \
  --channel conda-forge --channel conda-pypi \
  "conda-pypi::conda-features=0.2.0"
```

The channel-qualified package specification selects the PyPI wheel rather than the native conda package. The solver and channels apply to this command only, so these instructions do not change your persistent solver or channel settings. Review both transactions before accepting them. Use the actual host environment instead of base when your installation differs.

This setup must work before installing `conda-features` through PyPI. You cannot use its own feature command to bootstrap it. See [conda-pypi's usage guide](https://github.com/conda/conda-pypi#using-conda-pypi) for wheel-channel support. Neither released-package route needs pip, Pixi, or a source checkout.

## Add the repository's deployment examples

The core installs the command without feature declarations. `conda-features-examples` is available only from source, not from PyPI or Anaconda.org, so the wheel channel cannot supply it. To try its PyPI and completion deployments, install it from the matching repository tag into the same runtime. This separate source-installation step needs Git and pip:

```sh
python -m pip install "conda-features-examples @ git+https://github.com/jezdez/conda-features.git@0.2.0#subdirectory=packages/conda-features-examples"
```

For a fixed source revision, replace the tag with a reviewed commit SHA. Contributors testing unreleased code can install from a checkout using the [development guide](develop.md).

The examples make real changes when enabled. Installing the distribution alone does not select a solver, add a channel, install a completion hook, or preinstall all deployment prerequisites. Review and confirm those changes through `conda feature enable`.

## Check discovery and preview a feature

```sh
conda feature list
conda feature explain conda-pypi
conda feature enable conda-pypi --user --dry-run
```

Use the same host's `python -m conda` if the bare command points elsewhere. The preview lists package changes, the host prefix where they will be installed, and the separate target configuration file. Review it before rerunning without `--dry-run`.

If the subcommand is missing, check your interpreter and whether third-party plugins are disabled. If the command exists but the catalog is empty, check that a feature provider is installed in the same runtime. Provider errors name the failing entry point. A feature hook must use `conda_features.hooks.hookimpl`, not conda's hook marker.

Continue with [your first deployment](../tutorials/first-deployment.md) or the [real provider deployment guide](deploy-providers.md). Repository contributors should use the separate [development guide](develop.md) for Pixi environments and tests.

## Upgrade without losing recovery information

The current deployment receipt format is version 2. Keep receipts when upgrading, since they record the information needed for cleanup. If a new provider cannot read a receipt or no longer declares its step IDs, restore the prior provider version and disable the deployment before upgrading. The plugin refuses to process unsupported receipts.

Removing a provider package leaves its configuration, shell hook, and other resources in place. To remove resources it owns, disable its deployments first. See [recovery](recover.md) for receipts left by removed providers.
