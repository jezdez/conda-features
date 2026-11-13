# Deploy PyPI support and shell completion

The providers in `conda-features-examples` deploy real PyPI support and shell completion. You need this separate distribution for their feature declarations. Installing `conda-pypi` or `conda-completion` alone does not supply this feature interface.

First [install the plugin and deployment declarations](install.md) in the conda installation you use. Run the commands below with that installation's `conda`, or its host interpreter's `python -m conda`. Enabling a feature checks for missing upstream prerequisites and proposes installing them. Packages always go into the Python environment hosting the command, even when configuration goes elsewhere.

## PyPI support

The provider has three steps:

1. Install missing `conda-pypi>=0.13` and `conda-rattler-solver>=26.10` prerequisites from conda-forge.
2. Set `solver` to `rattler` at the selected configuration destination.
3. Add the `conda-pypi` channel if it is absent.

For an existing environment:

```sh
conda feature explain conda-pypi --prefix /path/to/environment
conda feature enable conda-pypi --prefix /path/to/environment --dry-run
conda feature enable conda-pypi --prefix /path/to/environment --yes
```

You can also use user scope, but not installation-wide feature settings. If packages are missing, the preview lists the host prefix and exact packages to install. The package step preserves the running conda and Python versions and refuses any transaction that would unlink existing packages. If this blocks setup, install compatible prerequisites separately and preview again.

After enabling, check `feature explain` at the same scope. Make sure the solver and channel configuration take effect. Values in a lower-priority file may be overridden. Follow [conda-pypi's upstream usage guide](https://github.com/conda/conda-pypi) to install packages. This plugin's readiness check does not try a PyPI installation.

Disable at the original scope:

```sh
conda feature disable conda-pypi --prefix /path/to/environment --dry-run
conda feature disable conda-pypi --prefix /path/to/environment --yes
```

The setting step restores the previous solver only if it owns that change and the value has not been replaced by a later user edit. The channel step removes its channel while preserving later additions. If it created a local channel list from inherited channels, it can remove that local list when only the unchanged inherited list remains. Packages remain installed.

## Shell completion

Completion setup supports user scope. Choose the shell before enabling:

These commands use the development version's `config --set`. On release 0.1.0, use `conda feature configure conda-completion plugins.feature_completion_shell=zsh` with the same scope and confirmation flags.

```sh
conda feature config conda-completion \
  --set plugins.feature_completion_shell zsh --user --dry-run
conda feature config conda-completion \
  --set plugins.feature_completion_shell zsh --user --yes
conda feature enable conda-completion --user --dry-run
conda feature enable conda-completion --user --yes
```

The default shell selection is `bash`. Other accepted values are `zsh`, `fish`, and `powershell`. The adapter is pinned to `conda-completion==0.3.2` because it uses that version's hook-rendering and installation behavior.

Setup installs missing prerequisites, generates completion data without repodata, and records the expected hook before calling the upstream installer. It uses a dedicated cache under `~/.cache/conda-features/completion`. Conda configuration set through environment variables can still affect subprocesses.

| Shell | Previewed file |
| --- | --- |
| Bash | Existing `~/.bashrc`, otherwise existing `~/.bash_profile`, otherwise `~/.bashrc` |
| Zsh | `~/.zshrc` |
| Fish | `~/.config/fish/completions/conda.fish` |
| PowerShell on Windows | An existing profile under `Documents/PowerShell` or `Documents/WindowsPowerShell`, otherwise the PowerShell profile path |
| PowerShell elsewhere | `~/.config/powershell/Microsoft.PowerShell_profile.ps1` |

Check the exact path in the preview. Before writing, the adapter checks the path chosen by the installed upstream package. The generated hook invokes the command name `conda`, so the shell's `conda` must resolve to the installation hosting completion support. Restart the shell after setup.

Disable before selecting a different shell:

```sh
conda feature disable conda-completion --user --dry-run
conda feature disable conda-completion --user --yes
```

Disabling removes only a block matching the receipt and preserves text added outside that block. It can do this even if the completion package is missing, without reinstalling it. Setup refuses pre-existing hooks because it does not own them. Remove packages and caches separately if you no longer need them.

## Experiment without touching your normal setup

`--file` changes where conda settings and receipts go. The completion hook still goes into the current home directory, so this flag alone does not isolate a test installation. Start with `--dry-run` to inspect the exact destinations without changing managed resources. Setup may still need to install missing prerequisites when you approve it.

For a full installation experiment, use a separate conda installation and isolated home. Activating a project environment does not necessarily isolate the conda host or shell configuration. See the [contributor guide](develop.md) for automated tests and disposable runtime setup.
