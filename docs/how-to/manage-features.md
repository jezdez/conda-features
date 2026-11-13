# Manage features and scopes

Start by inspecting the feature at the same scope you intend to change:

```sh
conda feature list --user
conda feature explain FEATURE --user
conda feature enable FEATURE --user --dry-run
```

Replace `FEATURE` with an ID returned by `list`. Feature IDs identify capabilities, not necessarily package names. The provider decides which scopes it supports.

## Choose the destination

| Selection | Configuration destination | What it does not select |
| --- | --- | --- |
| `--user` or no scope flag | Conda's user configuration destination | Every user's configuration |
| `--system` | `.condarc` in the conda root installation | A machine-wide service or privileged installation mode |
| `--prefix PATH` | `.condarc` in an existing conda environment | Where deployment prerequisite packages are installed |
| `--file PATH` | A standalone user-scope configuration file | An isolated home, shell profile, or conda runtime |

The scope flags are mutually exclusive. An explicit file must be named `.condarc`, `condarc`, or have a YAML extension, and its parent directory must exist. `--prefix` requires an environment with a `conda-meta` directory. This command does not create environments.

For normal scopes, conda determines configuration precedence. A saved value may lose to another file or an environment variable. `--file` reads the selected file plus environment-variable overrides. It does not automatically make ordinary conda invocations read that file later.

## Enable and configure

```sh
conda feature enable FEATURE --prefix /path/to/environment --dry-run
conda feature enable FEATURE --prefix /path/to/environment --yes
conda feature configure FEATURE plugins.example_limit=4 \
  --prefix /path/to/environment --dry-run
```

The example setting name is a placeholder. `explain` lists the provider's actual configurable settings. Configuration accepts distinct `KEY=VALUE` arguments and passes values through conda's type validation. Only declared non-secret scalar settings can be changed this way.

Configure a step-backed deployment before enabling it. An existing receipt prevents changing its configuration until you disable the deployment. This avoids silently changing the meaning of recorded ownership, such as which shell profile belongs to a completion installation.

## Include prerequisites explicitly

```sh
conda feature enable FEATURE --with-dependencies --user --dry-run
```

The preview names prerequisite opt-ins. They use the selected scope, and no other scope is changed implicitly. Already-enabled prerequisites can be inherited from user or installation configuration. Cycles and unsupported write scopes are rejected.

Combined prerequisite plans support built-in scalar settings and channels. Deploy missing package or custom shell prerequisites individually first, then retry. The command does not claim their readiness merely because a package installation has been planned.

## Protect other environments

```sh
conda feature disable FEATURE --user \
  --check-prefix /path/to/team-env \
  --check-prefix /path/to/another-env --dry-run
```

Shared user and installation changes inspect the current user's registered conda environments and the hosting installation. `--check-prefix` adds an explicit environment without writing to it. The preview lists checked environments. A dependent enabled in a checked environment can block disabling a shared prerequisite or introducing a conflict.

This is not a complete machine inventory. Unregistered environments, inaccessible environments, and other users' registries are not scanned. Explicit files do not trigger registry scanning. Other processes can change files, so the command also checks source membership and fingerprints again before application. If the plan is stale, preview again.

## Disable

```sh
conda feature disable FEATURE --user --dry-run
conda feature disable FEATURE --user --yes
conda feature disable --all --user --dry-run
```

A boolean feature is disabled by saving false. A step-backed feature reverses owned changes in reverse step order. It does not uninstall prerequisite packages. Existing resources that the feature did not create remain.

`disable --all` handles boolean-backed features only. It reports deployment features requiring individual disable commands. It is not a global emergency switch for every conda plugin. Unconditional graduated features cannot be disabled here. Use [graduation cleanup](transfer.md) to remove their obsolete opt-ins.
