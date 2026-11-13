# conda-features

A conda plugin for discovering and managing optional features supplied by installed providers. Inspect saved choices and readiness, preview changes, deploy prerequisites, and recover interrupted setup without claiming to observe provider execution.

The core package ships no feature catalog. The separate `conda-features-examples` distribution provides real PyPI and shell-completion deployments. These can install packages and change configuration or shell files after confirmation.

## Try the checkout

Requires [Pixi](https://pixi.sh). The development environment pins Python 3.12 and conda 26.9.4.

```sh
pixi install
pixi run python -m conda feature --help
pixi run python -m conda feature list
```

An empty list is expected without a feature provider. To discover the real deployment examples:

```sh
pixi install -e examples
pixi run -e examples python -m conda feature list
pixi run -e examples python -m conda feature explain conda-pypi
```

Install the plugin into the Python environment running conda, not just the environment you want to configure. Source installation and upgrade guidance are in [Installation](docs/how-to/install.md).

## Documentation

The documentation is published to [GitHub Pages](https://jezdez.github.io/conda-features/) from `main`. Pull requests build the site without deploying it.

Start with the [documentation index](docs/index.md) or the [first deployment tutorial](docs/tutorials/first-deployment.md), which uses a temporary configuration file and preinstalled integration prerequisites.

Build the Sphinx site with `pixi run -e docs docs`. The MyST pages use the conda theme and follow Diátaxis: tutorials, how-to guides, reference, and explanation. HTML is written to `docs/_build/dirhtml`.

- [Manage features and scopes](docs/how-to/manage-features.md)
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
conda feature configure FEATURE KEY=VALUE --dry-run
conda feature disable FEATURE --dry-run
conda feature diagnose --json
conda feature repair FEATURE --dry-run
conda feature migrate FEATURE --dry-run
conda feature cleanup FEATURE --dry-run
conda feature export --file source.yaml
conda feature apply intent.json --file destination.yaml --dry-run
```

Use an installed feature ID in place of `FEATURE`. Mutations require confirmation or `--yes`. Deployment dry-runs may solve packages and refresh caches without installing packages or writing managed resources. `--file` isolates conda configuration, not package installation or shell files.

## Current limits

Authentication, telemetry, remote catalogs, and automatic migration are not implemented. Environment checks cover explicit targets and the current user's registry, not a complete machine inventory. Runtime activity remains unknown. Generic package and shell migrations need provider-specific handling, and deployment intent is applied one feature at a time.

CI is configured for Linux x64, Windows x64, and ARM macOS core tests, with real-provider integration on Linux. See the relevant workflow results for the revision you use rather than assuming every newer conda version or shell has been verified.
