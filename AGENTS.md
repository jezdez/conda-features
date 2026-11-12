# conda-features Coding Guidelines

## Project Structure

- `src/conda_features/` contains the core package. It registers the `conda feature` subcommand through `plugin.py` and the `conda` entry-point group.
- `cli/` has one module per subcommand: `list`, `explain`, `enable`, `disable`, and `configure`. `parser.py` defines shared arguments, `commands.py` dispatches, `common.py` handles confirmation, `targets.py` selects configuration destinations, and `output.py` renders results.
- `models.py` owns `Feature` and its verbs. Keep feature behavior on the model rather than growing procedural command handlers.
- `hooks.py` defines the dedicated Pluggy provider interface. Providers register in the `conda_features` entry-point group and yield declarations from a `conda_features()` hook decorated with `conda_features.hooks.hookimpl`.
- `operations/` owns provider discovery and conda configuration operations. Do not add another configuration parser or dependency solver.
- `steps/` owns reusable deployment behavior: package installation, scalar settings, channels, managed file blocks, planning, and recovery receipts. Providers should declare steps rather than duplicate orchestration.
- `packages/conda-features-examples/` is a separate distribution with real `conda-pypi` and `conda-completion` deployment providers. These are not simulations. Keep only upstream-specific behavior in this package.
- Tests live under `tests/`. Name tests after the source module or behavior they exercise. Put shared fixtures in the nearest appropriate `conftest.py`. Do not reorganize unrelated tests as part of a small change.

## Imports and Dependencies

- Use relative imports within each package. Absolute imports are appropriate in tests, entry points, and between the core and examples distributions.
- Keep plugin registration and parser setup cheap. They must not contact services, inspect credentials, construct solvers, install packages, or create caches.
- Use lazy imports for startup-sensitive paths and optional dependencies. Put ordinary imports at module scope and annotation-only imports under `TYPE_CHECKING`. Fix circular ownership rather than scattering lazy imports throughout the code.
- Prefer stdlib, conda, and existing dependencies. Do not add a library for behavior already provided by one of them.
- Declare minimum supported dependency versions in each package's `pyproject.toml`. Exact pins are appropriate for locked test environments and adapters tied to a verified upstream version. Explain adapter pins before relaxing them.
- Provision conda through Pixi or an existing conda installation. Do not assume pip can bootstrap a conda runtime.

## Typing and Code Structure

- Use modern type annotations, including `str | None`, `list[str]`, and `ClassVar` where appropriate. Use `from __future__ import annotations` in new Python modules.
- Use Ruff for linting and formatting and `ty` for type checking. Keep production interfaces typed, including step inputs, results, and checkpoint callbacks.
- Prefer methods on the class that owns the data. A `Feature` owns its verbs, and a deployment step owns its checks, plan, and application.
- Before adding a helper, check whether conda already provides it, whether an existing model owns its inputs, and whether it is genuinely shared. Keep one-use glue inline when that remains readable.
- Do not add a workflow language, arbitrary shell-command step, or a new Pluggy hook per operation. Extend the small step interface only for a concrete provider requirement.
- Comments explain non-obvious constraints or decisions. Do not use section-divider comments or narrate obvious assignments. Split modules by responsibility rather than adding decorative headers inside them.

## Conda and Provider Integration

- Reuse conda's `Context`, typed settings, configuration precedence, package records, `MatchSpec`, channels, and solver APIs. Normalize values through conda rather than comparing raw input with typed effective values.
- Use `add_output_and_prompt_options` for standard output and confirmation flags. Do not duplicate its `--json`, `--dry-run`, `--yes`, verbosity, or debug arguments.
- Distinguish the conda installation hosting a provider from the environment receiving configuration. Package installation must identify the host installation explicitly in its preview.
- Preserve the meanings of saved choice, effective configuration, readiness, and observed runtime behavior. Do not report provider execution as suppressed or verified when only configuration has been inspected.
- Isolate necessary internal conda API usage in the owning adapter and test it against the supported conda version. Do not claim compatibility with versions or native platforms that were not exercised.
- Provider discovery and step checks must not perform deployment or network operations. Missing optional dependencies should fail at the operation that needs them with an actionable message.

## Deployment Safety

- A preview must describe the approved changes before mutation. Keep private apply data separate from public descriptions. Package solving may refresh caches, but dry-run must not install packages or modify managed configuration or shell hooks.
- Validate the combined prospective configuration before executing any step, including interactions between otherwise valid settings.
- Execute the package transaction that was approved. Do not run another unconstrained solve after confirmation. Protect the running conda and Python installation from replacement.
- Keep credentials, tokens, authenticated URLs, and unrelated configuration values out of public output and receipts. Store only the recovery information actually needed.
- Record ownership before side effects. Preserve pre-existing resources and subsequent user edits. Disabling a feature must not remove resources needed by another enabled feature.
- Keep retry and reverse-order cleanup safe after interruption, including when a side effect succeeds but its final receipt write fails. Do not promise atomicity across package transactions, configuration files, and shell setup.
- Check for stale plans and symbolic links before writes. Use the shared atomic storage helpers and locks rather than implementing a writer in each provider.
- Version persisted receipt formats. Reject unsupported receipts with recovery instructions instead of guessing how to undo them.
- Completion providers change real shell files. Never test deployment against the user's normal home, shell profile, or conda installation.

## Testing

- Use plain pytest functions, not test classes. Prefer parametrized cases with readable IDs over repeated tests for the same behavior.
- Use conda's testing fixtures, including `conda_cli`, `empty_env`, `reset_conda_context`, and context-aware monkeypatching, where they fit. Retain subprocess tests for installed entry-point discovery and fresh-process behavior.
- Do not use `unittest.mock`, `Mock`, `MagicMock`, or `patch`. Use pytest fixtures and small real fakes. Recording closures and `monkeypatch.setattr` are appropriate for external inputs or failure injection.
- Shared setup belongs in fixtures. Assert observable behavior, such as file contents, output, exit status, and preserved user configuration, rather than only checking that a fake was called.
- Isolate configuration search paths, homes, shell files, and target environments in both the pytest process and subprocesses. Merely setting `CONDARC` does not exclude all other conda configuration sources.
- Add a regression that fails before fixing a bug. Cover interruption, ownership, configuration precedence, and noninteractive execution when changing deployment behavior.
- Keep optional real-provider tests separate from the base suite. Do not silently turn an ordinary test run into package installation in the developer's runtime.

## Verification Commands

Run the full core suite and quality checks after changing production code or tests:

```sh
pixi run test
pixi run lint
pixi run format-check
pixi run type-check
```

For shared deployment steps or example-provider changes, also run:

```sh
pixi run -e examples test-examples
pixi run -e integration test-integration
pixi run -e integration ty check packages/conda-features-examples/src
```

`examples` installs the provider distribution. `integration` also installs the real upstream prerequisites. Test skips must be reported separately from passing tests. The missing-package installation test is opt-in through `CONDA_FEATURES_TEST_INSTALL=1` and must run only in a disposable runtime.

For packaging changes, build both distributions:

```sh
pixi run python -m hatchling build -t wheel
pixi run -e integration python -m pip wheel --no-deps --no-build-isolation packages/conda-features-examples --wheel-dir dist
```

- After changing Pixi dependencies, features, tasks, or environments, run `pixi lock` and include the updated `pixi.lock` with the metadata change. Check consistency with `pixi lock --check`.
- Coverage must include subprocesses to measure provider tests accurately. Coverage tooling and thresholds are not currently configured in `pyproject.toml`. Do not present a core-only report as including real-provider integration tests.
- Report local tests, package builds, hosted CI, and native-platform verification separately. Do not poll CI unless explicitly asked.

## Output and Documentation

- `--json` is an output format. Query and mutation commands return one complete structured result on stdout. Nested operations must not corrupt it with progress output. Send diagnostics and confirmation prompts to stderr.
- Keep confirmation explicit. Noninteractive mutations require `--yes`. Cancellation must not change managed resources.
- Read `DESIGN.md` for intent and `README.md` for implemented behavior. Do not rewrite the design document during routine implementation unless requested.
- Document declarations, commands, side effects, recovery, and limitations in plain language. Use Humanizer for prose and Ponytail Ultra to keep changes focused on the requested work.
- Keep reference, explanation, tutorials, and how-to material distinct as documentation grows. Do not introduce a documentation framework solely because another repository uses one.
- Write GitHub issue and PR bodies with one line per paragraph or bullet. Preserve code formatting, use concise titles, and do not include validation steps or verification output in PR descriptions.
- Use the existing checkout, preserve unrelated changes, and commit or push only when requested. Never include credentials, local environment directories, or build artifacts in commits.
