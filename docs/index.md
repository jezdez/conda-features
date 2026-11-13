# conda-features documentation

`conda-features` adds commands to inspect, enable, and configure optional features. Installed providers describe each feature's prerequisites and setup. You review the changes before enabling a feature, and the plugin records which resources it can safely remove on disable.

The core package is distributed through [PyPI](https://pypi.org/project/conda-features/) and the [jezdez Anaconda channel](https://anaconda.org/jezdez/conda-features). See [installation](how-to/install.md) for the correct host environment and the separate source-only examples package.

The catalog is empty until you install a provider. The source-only `conda-features-examples` distribution supplies PyPI support and shell completion. Enabling either can install packages and change configuration or shell files.

## Start here

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} First deployment
:link: tutorials/first-deployment
:link-type: doc

Try PyPI setup with a temporary configuration file, then undo it.
:::

:::{grid-item-card} Manage features
:link: how-to/manage-features
:link-type: doc

Choose scopes, configure options, and protect dependent environments.
:::

:::{grid-item-card} Build a provider
:link: tutorials/create-provider
:link-type: doc

Build a working provider using conda settings and Pluggy.
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
how-to/verify-release
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
changelog
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
| Verify downloaded artifacts and publication evidence | [Verify a release](how-to/verify-release.md) |
| Choose a scope and protect other environments | [Manage features](how-to/manage-features.md) |
| Deploy PyPI support or shell completion | [Real providers](how-to/deploy-providers.md) |
| Diagnose drift or recover interrupted setup | [Troubleshooting and recovery](how-to/recover.md) |
| Migrate a retired feature or move choices between machines | [Migrate and transfer choices](how-to/transfer.md) |
| Learn to publish a feature provider | [Build your first provider](tutorials/create-provider.md) |

## Look up a detail

- [Command reference](reference/cli.md): commands, arguments, scopes, output, and exit statuses.
- [Provider API](reference/providers.md): `Feature`, Pluggy hooks, built-in steps, and custom deployment steps.
- [Deployment model](explanation/deployment.md): configuration precedence, readiness, ownership, and recovery.
- [Development](how-to/develop.md): test environments, quality checks, and package builds.

## Current scope

The command examples use 0.2.0's `config FEATURE --set KEY VALUE` syntax. On release 0.1.0, use `configure FEATURE KEY=VALUE`. The older command remains supported. The custom intent format and export/apply commands were removed in 0.2.0.

These pages cover the development version. The [design goals](design.md) include future work. Python 3.12 or newer and conda 26.9.4 or newer are required. Tests pin Python 3.12 and conda 26.9.4, with core CI on Linux x64, Windows x64, and ARM macOS and real-provider integration on Linux. Other conda versions and shell/platform combinations may not have been tested.

Authentication, telemetry, remote feature catalogs, and automatic migration are not implemented. Readiness covers configuration and local setup checks. It cannot tell you whether a provider ran successfully or a remote service works.
