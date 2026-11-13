# Deploy PyPI support and shell completion

These are working deployment providers, not simulations. Their declarations currently live in the separate `conda-features-examples` distribution. Installing `conda-pypi` or `conda-completion` alone does not imply those upstream packages already publish this feature interface.

Use `pixi run -e examples python -m conda` in place of `conda` below when working from the examples environment. Use `integration` if you want Pixi to supply the tested upstream prerequisites first. Package installation always targets the Python environment hosting the command, regardless of the configuration destination.

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

The provider also supports user scope. It does not support installation-wide feature settings. If packages are missing, the preview identifies the host prefix and exact packages. The package step protects the running conda and Python versions and refuses a transaction that would unlink existing packages. If that restriction blocks setup, provision compatible prerequisites separately and preview again.

After enabling, check `feature explain` at the same scope. The solver and channel configuration must be effective, not merely written to a lower-priority file. Follow [conda-pypi's upstream usage guide](https://github.com/conda/conda-pypi) for actual package operations. This plugin's readiness check does not run a PyPI installation.

Disable at the original scope:

```sh
conda feature disable conda-pypi --prefix /path/to/environment --dry-run
conda feature disable conda-pypi --prefix /path/to/environment --yes
```

The setting step restores the previous solver only if it owns that change and the value has not been replaced by a later user edit. The channel step removes its channel while preserving later additions. If it created a local channel list from inherited channels, it can remove that local list when only the unchanged inherited list remains. Packages remain installed.

## Shell completion

Completion setup supports user scope. Choose the shell before enabling:

```sh
conda feature configure conda-completion \
  plugins.feature_completion_shell=zsh --user --dry-run
conda feature configure conda-completion \
  plugins.feature_completion_shell=zsh --user --yes
conda feature enable conda-completion --user --dry-run
conda feature enable conda-completion --user --yes
```

The default shell selection is `bash`. Other accepted values are `zsh`, `fish`, and `powershell`. The adapter is pinned to `conda-completion==0.3.2` because it uses that version's hook-rendering and installation behavior.

Setup installs missing prerequisites, generates completion data without repodata, records the expected hook, then calls upstream installation. The dedicated cache is under `~/.cache/conda-features/completion`. Conda environment-variable configuration can still affect subprocesses.

| Shell | Previewed file |
| --- | --- |
| Bash | Existing `~/.bashrc`, otherwise existing `~/.bash_profile`, otherwise `~/.bashrc` |
| Zsh | `~/.zshrc` |
| Fish | `~/.config/fish/completions/conda.fish` |
| PowerShell on Windows | An existing profile under `Documents/PowerShell` or `Documents/WindowsPowerShell`, otherwise the PowerShell profile path |
| PowerShell elsewhere | `~/.config/powershell/Microsoft.PowerShell_profile.ps1` |

Read the exact path in the preview. The adapter checks the installed upstream package's path before writing. The generated hook invokes the command name `conda`, so the shell's `conda` must resolve to the installation hosting completion support. Restart the shell after setup.

Disable before selecting a different shell:

```sh
conda feature disable conda-completion --user --dry-run
conda feature disable conda-completion --user --yes
```

Disable removes only a block matching the receipt. It does not need to reinstall a missing completion package. Pre-existing hooks are refused rather than adopted. Later text outside the owned block is preserved. Package and cache removal are separate decisions.

## Experiment without touching your normal setup

`--file` alone is insufficient isolation for completion. It changes where conda settings and receipts go, but the hook still targets the current home directory. Use a disposable runtime and isolated home, or run the maintained integration tests:

```sh
pixi run -e integration test-integration
```

Those tests prepare temporary homes and real shell files. The opt-in missing-package test actually installs into its test runtime and must not run against your normal conda installation. See [development](develop.md).
