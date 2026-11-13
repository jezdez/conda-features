# conda-features

A conda plugin for discovering and managing optional features supplied by installed providers. Inspect saved choices and readiness, preview changes, deploy prerequisites, and recover interrupted setup without claiming to observe provider execution.

The core package ships no feature catalog. The separate `conda-features-examples` distribution provides real PyPI and shell-completion deployments. These can install packages and change configuration or shell files after confirmation.

## Install and use

Use Python 3.12 or newer with conda 26.9.4 or newer. Install into the Python environment running conda, not just an environment you want to configure. These packages are not published on PyPI yet. The current installation method is from Git, which requires Git and pip:

```sh
python -m conda --version
python -m pip install "conda-features @ git+https://github.com/jezdez/conda-features.git@main"
python -m pip install "conda-features-examples @ git+https://github.com/jezdez/conda-features.git@main#subdirectory=packages/conda-features-examples"
```

Use that installation's conda command:

```sh
conda feature list
conda feature explain conda-pypi
conda feature enable conda-pypi --user --dry-run
```

The first distribution supplies the command. The second supplies real deployment declarations. Enabling a feature can then install missing upstream prerequisites after confirmation. See [Installation](docs/how-to/install.md) for choosing the correct host interpreter and [the tutorial](docs/tutorials/first-deployment.md) for a complete preview, enable, and disable sequence.

## Documentation

The documentation is published to [GitHub Pages](https://jezdez.github.io/conda-features/) from `main`. Pull requests build the site without deploying it.

Start with the [documentation index](docs/index.md) or the [first deployment tutorial](docs/tutorials/first-deployment.md), which uses your installed plugin and a temporary configuration file.

The Sphinx documentation follows Diátaxis: tutorials, how-to guides, reference, and explanation. Contributor setup and documentation build commands are in [Development](docs/how-to/develop.md).

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
