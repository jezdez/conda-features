# Develop and verify the plugin

Use the existing checkout and Pixi environments. The core distribution and real-provider distribution are separate so ordinary tests do not silently install deployment prerequisites into the developer's runtime.

```sh
pixi install
pixi run python -m conda feature --help
pixi install -e integration
pixi run -e integration test-integration
```

These are contributor setup commands, not the installation path for plugin users. The integration environment preinstalls upstream dependencies to exercise provider code under controlled conditions. For normal installation and use, follow [Install into the conda runtime](install.md).

## Environments

| Environment | Includes | Main use |
| --- | --- | --- |
| `default` | Core plugin, conda, pytest, Ruff, ty, build tools | Core tests and quality checks |
| `examples` | Default dependencies plus `conda-features-examples` | Provider discovery and isolated adapter tests |
| `integration` | Example providers plus real PyPI, Rattler, and completion prerequisites | Real configuration and shell deployment tests |

The lockfile supports `linux-64`, `win-64`, and `osx-arm64`. Core CI uses native runners for those platforms. Provider integration and wheel building run on Linux in CI. Local success does not replace native coverage for platform-specific shell behavior.

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

Core tests intentionally skip provider integration when the examples distribution is absent. Report skips separately. The examples environment may lack upstream packages, so some tests can skip there while running in integration.

Tests use conda's `conda_cli`, `empty_env`, context reset, and context-aware monkeypatch fixtures. Subprocess tests check installed entry points and fresh-process behavior. Isolate homes, configuration search paths, and shell files in both parent and child processes. Setting only `CONDARC` does not exclude every normal conda configuration source.

## Build both distributions

```sh
pixi run python -m hatchling build -t wheel
pixi run -e integration python -m pip wheel --no-deps --no-build-isolation \
  packages/conda-features-examples --wheel-dir dist
```

After changing Pixi dependencies or environments, run `pixi lock` and keep `pixi.lock` with the metadata change. Check it with `pixi lock --check`.

## Missing-package installation test

`CONDA_FEATURES_TEST_INSTALL=1` enables a test that really installs completion prerequisites into its current runtime. Run it only in a disposable examples runtime that starts without those prerequisites. The test uses an isolated home but still changes the host environment's installed packages. A regular test run leaves this test skipped.

## Coverage and workflow checks

Coverage tooling is not currently a declared project task or dependency. When measuring it, enable subprocess coverage and distinguish core coverage from the real-provider environment. A core-only percentage does not include upstream completion execution in child processes.

The dedicated `Workflow security` GitHub Actions workflow audits workflows with a pinned zizmor action. The test workflow runs Ruff, formatting, ty, native core tests, integration tests, and builds. Both workflows use pinned actions and limited permissions. They do not run the opt-in missing-package test.

## Documentation changes

Documentation uses Sphinx, MyST Markdown, the conda Sphinx theme, and sphinx-design. The navigation follows Diátaxis: tutorials teach through a guided exercise, how-to guides complete tasks, reference pages describe exact interfaces, and explanations describe the underlying model.

```sh
pixi run -e docs docs
```

This builds directory-style HTML in `docs/_build/dirhtml`, with warnings treated as errors and unresolved references checked. Verify command examples separately against the installed plugin, use temporary configuration and homes for side effects, and inspect rendered navigation and code blocks at desktop and mobile sizes. A successful HTML build does not execute shell examples. Do not turn a documentation update into deployment against your normal shell profile.
