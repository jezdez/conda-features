# conda-features

A conda plugin for finding, enabling, and configuring optional features. It shows what setup will change before you approve it and records those changes so you can retry or undo them later.

Install a provider to add features to the catalog. The source-only `conda-features-examples` package includes PyPI support and shell completion. Enabling these features can install packages, change conda settings, or edit shell files after confirmation.

## Install and use

`conda-features` 0.1.0 is available on [PyPI](https://pypi.org/project/conda-features/) and the [jezdez Anaconda channel](https://anaconda.org/jezdez/conda-features). Use Python 3.12 or newer with conda 26.9.4 or newer. Install into the Python environment running conda, not just an environment you want to configure. For a conventional installation hosted in base:

```sh
conda install --name base --override-channels --channel conda-forge \
  --channel jezdez conda-features=0.1.0
```

Alternatively, with the host Python:

```sh
python -m conda --version
python -m pip install conda-features==0.1.0
```

The examples distribution is intentionally unpublished. To use its real deployment declarations, install it from the repository into the same runtime:

```sh
python -m pip install "conda-features-examples @ git+https://github.com/jezdez/conda-features.git@0.1.0#subdirectory=packages/conda-features-examples"
```

Then use that installation's conda command:

```sh
conda feature list
conda feature explain conda-pypi
conda feature enable conda-pypi --user --dry-run
```

See [Installation](docs/how-to/install.md) if you have more than one conda installation. The [tutorial](docs/tutorials/first-deployment.md) walks through previewing, enabling, and disabling PyPI support in a temporary configuration file.

## Documentation

See the [changelog](CHANGELOG.md) for released features and publication history.

The documentation is published to [GitHub Pages](https://jezdez.github.io/conda-features/) from `main`. Pull requests build the site without deploying it.

Start with the [documentation index](docs/index.md) or the [first deployment tutorial](docs/tutorials/first-deployment.md), which uses your installed plugin and a temporary configuration file.

Contributor setup and documentation build commands are in [Development](docs/how-to/develop.md).

- [Manage features and scopes](docs/how-to/manage-features.md)
- [Verify release provenance and publication attestations](docs/how-to/verify-release.md)
- [Deploy real PyPI support and shell completion](docs/how-to/deploy-providers.md)
- [Diagnose and recover setup](docs/how-to/recover.md)
- [Migrate and transfer choices](docs/how-to/transfer.md)
- [Build your first provider](docs/tutorials/create-provider.md)
- [Command reference](docs/reference/cli.md)
- [Provider and step API](docs/reference/providers.md)
- [Portable intent format](docs/reference/intent.md)
- [Configuration, ownership, and recovery explained](docs/explanation/deployment.md)
- [Development and verification](docs/how-to/develop.md)

The [design document](DESIGN.md) includes goals beyond the current implementation.

## Commands at a glance

```text
conda feature list
conda feature explain FEATURE
conda feature enable FEATURE --dry-run
conda feature config FEATURE --set KEY VALUE --dry-run
conda feature config FEATURE --get
conda feature config FEATURE --show-sources
conda feature config FEATURE --remove-key KEY --dry-run
conda feature disable FEATURE --dry-run
conda feature diagnose --json
conda feature repair FEATURE --dry-run
conda feature migrate FEATURE --dry-run
conda feature cleanup FEATURE --dry-run
conda feature export --file source.yaml
conda feature apply intent.json --file destination.yaml --dry-run
```

Use an installed feature ID in place of `FEATURE`. Mutations require confirmation or `--yes`. Deployment dry-runs may solve packages and refresh caches without installing packages or writing managed resources. `--file` isolates conda configuration, not package installation or shell files.

`config --set` is new in the development version. Release 0.1.0 uses `conda feature configure FEATURE KEY=VALUE`, which remains supported.

## Current limits

There is no authentication integration, telemetry, remote catalog, or automatic migration. Environment checks cover the targets you select and your conda registry. They can miss unregistered environments. Status reports configuration and setup checks, but does not observe provider execution. Package and shell migrations need provider-specific code. Apply deployment intent one feature at a time.

CI runs core tests on Linux x64, Windows x64, and ARM macOS, with real-provider integration on Linux. Other conda versions and shell/platform combinations may not have been tested. Check the workflow results for the revision you use.
