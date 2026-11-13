# Develop and verify the plugin

Use the existing checkout and Pixi environments. The core and real-provider distributions are separate to keep ordinary tests from installing deployment prerequisites into your runtime.

```sh
pixi install
pixi run python -m conda feature --help
pixi install -e integration
pixi run -e integration test-integration
```

The integration environment includes upstream dependencies for testing provider code in a controlled environment. Plugin users should follow [Install into the conda runtime](install.md) instead of the contributor setup commands above.

## Environments

| Environment | Includes | Main use |
| --- | --- | --- |
| `default` | Core plugin, conda, pytest, Ruff, ty, build tools | Core tests and quality checks |
| `examples` | Default dependencies plus `conda-features-examples` | Provider discovery and isolated adapter tests |
| `integration` | Example providers plus real PyPI, Rattler, and completion prerequisites | Real configuration and shell deployment tests |
| `demos` | Integration dependencies plus VHS, ttyd, ffmpeg, and Bash | Optional terminal recordings on Linux x64 or ARM macOS |

The lockfile supports `linux-64`, `win-64`, and `osx-arm64`. Core CI uses native runners for those platforms. Provider integration tests and wheel builds run on Linux in CI. Test platform-specific shell behavior on the platform it targets, even when local tests pass.

## Run checks

```sh
pixi run test
pixi run lint
pixi run format-check
pixi run type-check
pixi run -e examples test-examples
pixi run -e integration test-integration
pixi run -e integration ty check packages/conda-features-examples/src
```

Core tests skip provider integration when the examples distribution is absent. Report skips separately from passing tests. The examples environment may also lack upstream packages, so a test skipped there may run in integration.

Tests use conda's `conda_cli`, `empty_env`, context reset, and context-aware monkeypatch fixtures. Subprocess tests check installed entry points and fresh-process behavior. Isolate homes, configuration search paths, and shell files in both parent and child processes. Setting only `CONDARC` does not exclude every normal conda configuration source.

## Build both distributions

```sh
pixi run python -m hatchling build -t wheel
pixi run -e integration python -m pip wheel --no-deps --no-build-isolation \
  packages/conda-features-examples --wheel-dir dist
```

After changing Pixi dependencies or environments, run `pixi lock` and include `pixi.lock` with the metadata change. Check that they agree with `pixi lock --check`.

## Release notes and immutability

Before a release, add user-visible changes to the root `CHANGELOG.md`, which Sphinx includes as the documentation changelog. Describe limitations and changes to recovery, and make clear which features ship in the published core and which need the source-only example providers.

GitHub releases are immutable once published. The workflow keeps each release as a draft until registry publication succeeds and all provenance bundles are attached. Publishing the release locks its assets and tag. Do not retag a published version or plan to add assets afterward. See [release verification](verify-release.md) for artifact verification commands and the exceptional `0.1.0` recovery history.

## Missing-package installation test

`CONDA_FEATURES_TEST_INSTALL=1` enables a test that installs completion prerequisites into the runtime running it. Use only a disposable examples runtime that starts without those prerequisites. The test isolates its home directory but changes the host environment's installed packages. Regular test runs skip it.

## Coverage and workflow checks

The project currently has no declared coverage task or dependency. To measure coverage, enable it for subprocesses and report core and real-provider coverage separately. A core-only percentage leaves out upstream completion code running in child processes.

The dedicated `Workflow security` GitHub Actions workflow audits workflows with a pinned zizmor action. The test workflow runs Ruff, formatting, ty, native core tests, integration tests, and builds. Both workflows use pinned actions and limited permissions. They do not run the opt-in missing-package test.

## Documentation changes

Documentation uses Sphinx, MyST Markdown, the conda Sphinx theme, and sphinx-design. The navigation follows Diátaxis: tutorials teach through a guided exercise, how-to guides complete tasks, reference pages describe exact interfaces, and explanations describe the underlying model.

```sh
pixi run -e docs docs
```

The build writes directory-style HTML to `docs/_build/dirhtml`, treats warnings as errors, and checks unresolved references. It does not execute shell examples, so verify commands separately against the installed plugin. Use temporary configuration and homes for anything with side effects, never your normal shell profile. Check the rendered navigation and code blocks at desktop and mobile sizes.

## Record terminal demos

Install [JetBrains Mono](https://www.jetbrains.com/lp/mono/) locally before recording. The recording tools come from conda-forge, but the font is a separate prerequisite. VHS also needs a working Chromium browser and may download one on its first run. Native Windows recording is not configured.

```sh
pixi install -e demos
pixi run -e demos test-demos
pixi run -e demos demos
pixi run -e demos demos configuration
```

Run these commands from the checkout root. With no name, the task records both `demos/feature-management.gif` and `demos/configuration.gif`. Pass `feature-management` or `configuration` to regenerate one. Each tape sources `demos/_settings.tape`, which uses the conda-workspaces font, dimensions, theme, and green prompt.

The tapes execute the installed development plugin and source-only example providers. Prerequisite packages are installed by Pixi before recording. Hidden preparation refuses to continue if any are missing, so the GIFs do not include package installation. The feature-management recording previews, enables, and disables PyPI support in `~/demo/.condarc`. The configuration recording reads and changes the completion shell setting without deploying a completion hook.

Preparation creates a disposable home, configuration, and caches under `demos/.scratch/`. A private Python startup module restricts conda's configuration search paths in every recording subprocess, including default arguments captured during import. Inherited conda settings are cleared. Bash runs without profiles, and cleanup removes only the directory allocated for that recording. `test-demos` checks this isolation, real command execution, unchanged installed packages, and the absence of shell hooks. Do not source `_prep.sh` into your normal interactive shell.

Keep the tapes and generated GIFs together in version control. After recording, inspect the playback for errors, clipped text, personal paths, and enough reading time, then build the docs with `pixi run -e docs docs`. These recordings demonstrate behavior, not command timings. An interrupted recording may leave a directory under the ignored `demos/.scratch/` directory for manual cleanup.
