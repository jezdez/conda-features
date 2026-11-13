# Your first feature deployment

This tutorial enables and disables real PyPI support using a temporary conda configuration file. You will see a preview, inspect the resulting state, and restore the settings the deployment changed. You will not install a package from PyPI or modify shell startup files.

You need this repository checkout and [Pixi](https://pixi.sh). Run the commands from the repository root. The examples below use a POSIX shell. On PowerShell, create a temporary directory with `New-Item`, assign its path to `$demo`, and use `Join-Path $demo demo.yaml` wherever the examples use `"$demo/demo.yaml"`.

## 1. Prepare the runtime

```sh
pixi install -e integration
```

This creates the project's integration environment, installing conda, this plugin, the feature declarations, and the real upstream prerequisites. It can download packages. It does not install a completion hook or opt your usual conda installation into PyPI support.

Create a temporary file with explicit starting settings:

```sh
demo=$(mktemp -d) || exit 1
printf 'solver: libmamba\nchannels: [conda-forge]\n' > "$demo/demo.yaml"
```

Keep using this same file for every command. Deployment receipts are stored beside it. `--file` selects a standalone configuration file plus environment-variable overrides. It does not isolate package installation or shell files. In this tutorial, the integration environment already has the required packages, and only the PyPI provider is enabled.

If you have conda environment variables that override the solver or channels, the preview may refuse the change. Use a fresh shell without those overrides rather than changing your normal configuration to make the tutorial pass.

## 2. Discover the feature

```sh
pixi run -e integration python -m conda feature list --file "$demo/demo.yaml"
pixi run -e integration python -m conda feature explain conda-pypi --file "$demo/demo.yaml"
```

The catalog contains `conda-pypi` and `conda-completion`. For PyPI support, `requested` is initially `unset`: this file has no deployment receipt. Readiness lists the solver and channel setup still needed. The package prerequisites should already be satisfied by the integration environment.

The completion feature can also appear in this listing. Listing it does not install a hook.

## 3. Preview the deployment

```sh
pixi run -e integration python -m conda feature enable conda-pypi \
  --file "$demo/demo.yaml" --dry-run --json
```

The result describes setting `solver` to `rattler`, appending `conda-pypi`, and recording the feature choice. Its destination is your temporary file. With the integration prerequisites installed, there should be no package installation step to apply.

This is a preview, not a saved approval token. Running enable again constructs and confirms a fresh plan. A missing-package preview can solve and update package caches, but it does not install packages or write managed configuration.

## 4. Apply and inspect

```sh
pixi run -e integration python -m conda feature enable conda-pypi \
  --file "$demo/demo.yaml" --yes
pixi run -e integration python -m conda feature explain conda-pypi \
  --file "$demo/demo.yaml" --json
```

The file now selects Rattler and contains both channels. A file named `demo.yaml.conda-pypi.json` records the deployment's ownership and completed steps.

Expected status fields include:

```json
{
  "requested": "enabled",
  "effective": "enabled",
  "readiness": "ready",
  "runtime": "unknown"
}
```

This is an excerpt, not the complete command output. For a step-backed feature, `effective` reflects the step checks. `runtime` remains unknown because the plugin has not watched a PyPI transaction execute.

Enable it once more:

```sh
pixi run -e integration python -m conda feature enable conda-pypi \
  --file "$demo/demo.yaml" --yes
```

With no intervening changes, the command reports that no changes are needed.

## 5. Disable and clean up

```sh
pixi run -e integration python -m conda feature disable conda-pypi \
  --file "$demo/demo.yaml" --dry-run
pixi run -e integration python -m conda feature disable conda-pypi \
  --file "$demo/demo.yaml" --yes
```

Disable restores `solver: libmamba`, removes the channel added by this feature, and removes the completed deployment receipt. It leaves prerequisite packages installed in the integration environment. Existing channels and unrelated settings remain.

After checking the result, remove the temporary tutorial directory:

```sh
rm -r -- "$demo"
unset demo
```

Do not delete a real deployment receipt as a substitute for disabling a feature. Its recovery information may be needed to remove resources safely.

Continue with [real provider deployment](../how-to/deploy-providers.md) to use your own target environment, or [build your first provider](create-provider.md) to expose your own optional behavior.
