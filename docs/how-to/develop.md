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
