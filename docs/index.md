# conda-features documentation

`conda-features` adds `conda feature` commands for managing optional capabilities supplied by installed providers. A provider describes the feature, its prerequisites, and either a boolean conda setting or a sequence of deployment steps. You can inspect its state, preview changes, enable it, and later disable resources the deployment owns.

Release 0.1.0 is available on [PyPI](https://pypi.org/project/conda-features/0.1.0/) and the [jezdez Anaconda channel](https://anaconda.org/jezdez/conda-features). See [installation](how-to/install.md) for the correct host environment and the separate source-only examples package.

The core package ships no feature catalog. The separate `conda-features-examples` distribution contains real deployment providers for PyPI support and shell completion. Installing that distribution makes their declarations discoverable. Enabling them can install packages and change configuration or shell files.

## Start here

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} First deployment
:link: tutorials/first-deployment
:link-type: doc

Preview, enable, and reverse a real deployment in temporary configuration.
:::

:::{grid-item-card} Manage features
:link: how-to/manage-features
:link-type: doc

Choose scopes, configure options, and protect dependent environments.
:::

:::{grid-item-card} Build a provider
:link: tutorials/create-provider
:link-type: doc

Publish a complete feature provider using conda settings and Pluggy.
:::

:::{grid-item-card} Command reference
:link: reference/cli
:link-type: doc

Look up command arguments, output formats, and exit statuses.
:::
::::

```{toctree}
:hidden:
:caption: Tutorials

tutorials/first-deployment
tutorials/create-provider
```

```{toctree}
:hidden:
:caption: How-to guides

how-to/install
how-to/manage-features
how-to/deploy-providers
how-to/recover
how-to/transfer
how-to/develop
```

```{toctree}
:hidden:
:caption: Reference

reference/cli
reference/providers
reference/intent
```

```{toctree}
:hidden:
:caption: Explanation

explanation/deployment
design
```

| Your task | Read |
| --- | --- |
| Try a complete deployment without editing your usual configuration | [First deployment tutorial](tutorials/first-deployment.md) |
| Install the plugin into your conda runtime | [Installation](how-to/install.md) |
| Choose a scope and protect other environments | [Manage features](how-to/manage-features.md) |
| Deploy PyPI support or shell completion | [Real providers](how-to/deploy-providers.md) |
| Diagnose drift or recover interrupted setup | [Troubleshooting and recovery](how-to/recover.md) |
| Migrate a retired feature or move choices between machines | [Migrate and transfer choices](how-to/transfer.md) |
| Learn to publish a feature provider | [Build your first provider](tutorials/create-provider.md) |

## Look up a detail

- [Command reference](reference/cli.md): commands, arguments, scopes, output, and exit statuses.
- [Provider API](reference/providers.md): `Feature`, Pluggy hooks, built-in steps, and custom deployment steps.
- [Intent format](reference/intent.md): the versioned export/apply document and its validation rules.
- [Deployment model](explanation/deployment.md): configuration precedence, readiness, ownership, and recovery.
- [Development](how-to/develop.md): test environments, quality checks, and package builds.

## Current scope

These pages describe the implementation in this checkout. The [design goals](design.md) also include longer-term work. The repository declares Python 3.12 or newer and conda 26.9.4 or newer, while its test environments pin Python 3.12 and conda 26.9.4. CI is configured for Linux x64, Windows x64, and ARM macOS core tests, with real-provider integration on Linux. Those jobs do not establish compatibility with every newer conda release or every shell on every operating system.

Authentication, telemetry, remote feature catalogs, and automatic migration are not implemented. Runtime provider execution is not observed. A ready configuration is not proof that a remote service works or that a provider executed successfully.
