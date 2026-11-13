# Provider API reference

A provider is an installed Python distribution that declares optional features. `conda-features` discovers those declarations, checks local readiness, and plans configuration or deployment changes. The provider implements the optional behavior and enforces its requirements when that behavior runs.

For a complete small package, see [Build your first provider](../tutorials/create-provider.md). See the [CLI reference](../reference/cli.md) for commands and [Deployment and recovery](../explanation/deployment.md) for the user-facing recovery model. Return to the [documentation index](../index.md).

## Registration and trust

Providers can register in two entry-point groups:

```toml
[project.entry-points.conda]
my-provider = "my_provider.plugin"

[project.entry-points.conda_features]
my-provider = "my_provider.features"
```

Conda loads the `conda` entry point to register settings and behavior through its own hooks. `conda-features` loads the `conda_features` entry point through a separate Pluggy manager. A feature provider that uses only already-registered settings does not need its own `conda` entry point. A provider that registers its own settings or commands does.

Use the decorator from the matching hook system:

```python
# my_provider/features.py
from __future__ import annotations

from collections.abc import Iterable

from conda_features.hooks import hookimpl
from conda_features.models import Feature


@hookimpl
def conda_features() -> Iterable[Feature]:
    yield Feature(
        name="sample",
        description="Use the provider's optional behavior",
        enabled_setting="plugins.sample_enabled",
    )
```

`conda_features.hooks.hookimpl` marks implementations for the `conda_features` project. `conda.plugins.hookimpl` does not register this hook. The hook takes no arguments and returns an iterable of `Feature` instances, usually by yielding them. `FeatureSpecs` and `hookspec` define this interface in `conda_features.hooks`.

Discovery loads each installed entry point, registers its module, checks hook declarations, collects features, and returns a catalog sorted by feature ID. A missing decorator, failed import, exception while collecting declarations, invalid declaration type, or duplicate feature ID fails discovery. Providers are not silently skipped. Entry-point names must also be unique within the feature provider manager.

The provider identity shown in status is the name on the left of the `conda_features` entry point, such as `my-provider`. It is not the distribution version, an import path, or a cryptographic identity.

Install the distribution in the Python environment running conda. Installing it only in an environment selected with `--prefix` does not make the hosting conda discover it. Declare `conda-features` as a dependency and provision conda through conda or Pixi. The current package requires Python 3.12 or newer and conda 26.9.4 or newer.

Installed providers are trusted Python code. Loading an entry point executes imports, and calling a hook executes provider code. There is no sandbox, remote catalog, signature check, or automatic guarantee that a provider honors dry-run. Keep initializers, registration modules, and declarations free of setup, credential reads, network access, and cache creation. Load expensive or optional implementations only at the operation that needs them.

## Feature declaration

Import `Feature` from `conda_features.models`. This frozen dataclass holds the feature declaration. Runtime status is reported separately.

| Field | Type | Default | Meaning and constraints |
| --- | --- | --- | --- |
| `name` | `str` | Required | Unique feature ID matching `[a-z][a-z0-9_-]*`. It need not match the package name. Keep it stable across releases. |
| `description` | `str` | Required | Human-readable description used in status and list output. There is no additional nonempty-description validator. |
| `enabled_setting` | `str \| None` | `None` | Registered boolean setting for a settings-backed feature. Use `plugins.NAME` for plugin settings. Mutually exclusive with a nonempty `steps` tuple. |
| `maturity` | `str` | `"experimental"` | Exactly `"experimental"`, `"preview"`, or `"stable"`. This label does not enable the feature, observe execution, or make functionality unconditional. |
| `scopes` | `tuple[str, ...]` | `("user",)` | Nonempty selection from `"user"`, `"system"`, and `"environment"`. `--file` is a user-scope destination. |
| `settings` | `tuple[str, ...]` | `()` | Allowlist of registered, non-secret primitive settings accepted by `config --set`. Excludes `enabled_setting`. Sequence and mapping settings are rejected. |
| `required_settings` | `tuple[str, ...]` | `()` | Subset of `settings`. Effective values of `None` or `""` require setup. `False` and `0` count as configured. |
| `requires` | `tuple[str, ...]` | `()` | Feature IDs that must be effective and ready. An unconditional prerequisite does not need an enabled obsolete flag, but still needs ready status. Missing dependencies and cycles block enable. |
| `conflicts` | `tuple[str, ...]` | `()` | Feature IDs that cannot be effective at the same time. A declaration on either feature is enough to detect a conflict. |
| `conda_version` | `str` | `">=26.9.4"` | A valid conda `VersionSpec`, checked against the running conda version. It is not a Python packaging version specifier. |
| `platforms` | `tuple[str, ...]` | `()` | Allowed conda subdirs, checked against `ctx.subdir`, such as `"osx-arm64"` or `"linux-64"`. Empty means unrestricted. This is a configuration check, not proof of native-platform testing. |
| `retired` | `bool` | `False` | Marks a feature retired and blocks new enable operations. Keep declarations installed so users can inspect and disable existing choices. |
| `replacement` | `str \| None` | `None` | Replacement feature ID for explicit migration. Does not install a provider or migrate automatically. Merely setting this field does not set `retired=True`. |
| `guidance` | `str` | `""` | Provider-authored next steps shown in status. Keep instructions specific and free of secrets. |
| `steps` | `tuple[Step, ...]` | `()` | Deployment steps in enable order. Disable runs them in reverse. Each must implement `Step` and have a unique ID within the feature. |
| `migration_settings` | `tuple[tuple[str, str], ...]` | `()` | Explicit old-setting/new-setting pairs for replacement migration. Destination names must be unique. Migration checks that both ends are in the respective features' `settings` allowlists. |
| `graduation` | `str \| None` | `None` | `None`, `"optional"`, or `"unconditional"`. Unconditional graduation supports obsolete boolean flags only, not step-backed resource removal. |

Type annotations describe the supported input shapes. Catalog validation checks the constraints listed here, but it is not a general schema validator for arbitrary Python objects.

### Setting ownership

Register settings with conda before referring to them in a feature. A plugin registers `sample_enabled` with `CondaSetting` and refers to it as `plugins.sample_enabled` in a declaration. The enabled setting must be a primitive with exactly the boolean element type. Other declared settings must be primitive values that conda can normalize and validate.

Feature setting ownership is global within the discovered catalog. The enabled flag, configurable settings, and keys written by `SetSetting` cannot also belong to another feature. Repeating a declared setting is rejected. A `SetSetting` key may also appear in that same feature's `settings` tuple, but users must disable a saved deployment before configuring it.

The allowlist is an author assertion that values are safe to display and persist. The validator cannot identify an arbitrary secret string. Do not declare tokens, passwords, authenticated endpoints, or credentials as configurable, managed, or migratable settings. Normal previews may include setting values. A `SetSetting` receipt records the previous value of its own key so that disable can restore it.

Use canonical setting names. Conda performs type normalization, alias handling, validation, and precedence resolution. Providers should not add another `.condarc` parser.

### Dependencies and scopes

`requires` names features, not package specifications. Use `InstallPackages` for package prerequisites. Enabling a feature normally requires its dependencies to be enabled already. `enable --with-dependencies` can plan explicit prerequisite choices at the same scope and reuse already-effective inherited choices.

Combined prerequisite plans support settings and channels. Missing package installations, custom setup, and shell hooks must be deployed separately before retrying dependent setup. Features with custom `enable` methods cannot participate in a multi-feature prerequisite enable plan.

An environment scope chooses a configuration destination. It does not redirect package installation from the hosting conda environment, and it does not redirect shell-file edits to a different home. Shared user and installation mutations inspect known environments for dependent features, but they do not scan every environment or other users' registries. See [Deployment and recovery](../explanation/deployment.md).

## Boolean settings and deployment steps

A boolean feature supplies `enabled_setting` and leaves `steps` empty. Enable and disable plan writes of `True` and `False`. Disable preserves the feature's other settings. The `config --set` command changes only its declared `settings`. Conda normalizes all proposed values and validates the combined prospective configuration before mutation.

The provider reads the effective flag through conda, typically `context.plugins.sample_enabled`, before executing optional behavior. `conda-features` does not intercept hooks or prevent a provider from running when readiness is blocked. Runtime requirements, including authentication or access to a service, remain the provider's responsibility.

A step-backed feature leaves `enabled_setting=None` and supplies `steps`. Its saved request comes from a deployment receipt. Effective status is enabled when every step's `check` returns no reasons, even if the resources were installed outside this feature. Readiness also includes version, platform, dependency, conflict, retirement, and required-setting checks. A pre-existing resource can therefore be effective without being owned.

| Status field | Meaning |
| --- | --- |
| `requested` | Saved choice at the selected path. Boolean features use `enabled`, `disabled`, or `unset`. Step-backed features use `enabled` when a receipt exists and `unset` otherwise. Without a path, this is `unknown`. |
| `effective` | Current boolean value or aggregate result of step checks, expressed as `enabled` or `disabled`. |
| `readiness` | `blocked` for compatibility or dependency problems, `setup required` for missing required values or step prerequisites, otherwise `ready`. |
| `runtime` | Always `unknown` in the base implementation. Status does not observe execution. |
| `lifecycle` | `graduated` if graduation is declared, otherwise `replaced` if a replacement is declared, otherwise `retired` if retired, otherwise `available`. |

### Feature methods

`Catalog` is `dict[str, tuple[str, Feature]]`, mapping a feature ID to its provider identity and declaration. The standard methods use a conda `Context`, selected configuration `Path`, and scope string:

```text
enable(catalog, ctx, path, scope, *, with_dependencies=False) -> dict
disable(catalog, ctx, path, scope) -> dict
configure(catalog, ctx, path, scope, settings: dict[str, str], *, remove_keys=()) -> dict
config_query(catalog, ctx, path, scope, action, keys=None) -> dict
repair(catalog, ctx, path, scope) -> dict
migrate(catalog, ctx, path, scope) -> dict
cleanup(catalog, ctx, path, scope) -> dict
status(catalog, ctx, scope, visiting=(), *, path=None) -> dict
apply(plan, ctx) -> None
```

The mutation methods return plans. The CLI obtains confirmation and then calls `apply`. The `config --set` and `--remove-key` commands use the Python `configure` method. Removal uses `remove_keys` and restores inherited values or defaults rather than writing a replacement. Read actions use `config_query`, which accepts `get`, `show`, `show-sources`, `describe`, and `validate`. It never calls deployment planning. `repair` requires an enabled choice saved at that path and calls the normal enable planner, preserving its ownership and user-edit checks. For step-backed features, `configure` refuses while a receipt exists, including an incomplete deployment.

Prefer composition with steps. A subclass with neither an enabled flag nor steps must override `enable`, `disable`, `status`, and `apply`. Validation checks that those methods are overridden. It does not supply receipt handling or validate the subclass's side effects. Such providers must integrate with the existing CLI plan and output handling themselves and need their own recovery tests.

## Built-in steps

Import `Step`, `StepPlan`, `InstallPackages`, `SetSetting`, and `EnsureChannel` from `conda_features.steps`. Import `ManagedBlock` separately from `conda_features.steps.block`.

### InstallPackages

```python
InstallPackages("conda-pypi>=0.13", "conda-rattler-solver>=26.10")
```

The constructor accepts one or more conda `MatchSpec` strings and validates their syntax. The ID is `packages:` followed by the comma-joined specifications. Changing specifications or their order changes the receipt key.

`check` inspects conda package records in `sys.prefix`, the Python installation hosting conda. It does not solve or install. `plan` solves missing specifications through the `libmamba` solver using conda-forge, pins the existing conda and Python records, and requests frozen installed packages. A transaction that unlinks any existing package is rejected. Users must arrange compatible prerequisites separately when that restriction prevents installation.

The public change describes the host prefix and packages to link. The private plan retains the actual transaction and installed-record snapshot. `apply` checks that installed records still match, then downloads, extracts, and executes that transaction without a second solve. Solver progress is sent to stderr.

Planning can fetch repodata and refresh package-manager caches, including during dry-run. Disable leaves installed packages in place. Use exactly one package step per feature and pass all specifications together.

### SetSetting

```python
SetSetting("solver", "rattler")
```

The constructor takes `key` and `value`. Its ID is `setting:KEY`. Conda normalizes the target value, including enum values, before checks and comparisons. The key must refer to a registered scalar setting.

If the effective value already matches, the step records that it does not own a change. Otherwise it records the prior local key's presence and value, the normalized target, and ownership. A higher-priority override that prevents the target from becoming effective blocks enable.

Disable restores the prior local value or removes the local key if it was originally absent. It preserves a later user edit by refusing to overwrite it. If a previous disable restored the value but failed to update the receipt, retry recognizes the already-restored value. A receipt that never owned the setting cannot later claim it silently. A changed declared target requires disabling the old deployment first.

### EnsureChannel

```python
EnsureChannel("conda-pypi")
```

The constructor takes one channel string. Its ID is `channel:CHANNEL`. Checks compare that string with effective `ctx.channels`. Use a public, non-authenticated channel identifier.

The step appends a missing channel while retaining effective channels. If it creates a local list from inherited channels, it stores a digest of the original effective list for cleanup comparisons. It does not copy those inherited URLs into the receipt.

Disable removes only a channel the receipt owns. If the step created the local list and its remainder matches the original digest, disable removes the local key so inheritance resumes. Later channel additions are retained. A channel already present before deployment remains unowned.

Use at most one channel step per feature. The same channel string cannot be claimed by two features. Put a shared channel in a prerequisite feature and make its consumers require that feature. Use `EnsureChannel` for channels rather than trying to configure the sequence through scalar `SetSetting`.

## Custom Step interface

`Step` is an abstract base class. A concrete step must supply a stable `id`, `check`, `plan`, and `apply`:

```python
from collections.abc import Callable
from pathlib import Path

from conda.base.context import Context

from conda_features.steps import Step, StepPlan


class ProviderStep(Step):
    id = "provider-resource-v1"

    def check(self, ctx: Context, path: Path | None) -> list[str]: ...

    def plan(
        self, ctx: Context, path: Path, operation: str, saved: dict | None
    ) -> StepPlan: ...

    def apply(
        self, plan: StepPlan, ctx: Context, checkpoint: Callable[[dict], None]
    ) -> None: ...
```

This is an interface sketch, not a working deployment step.

### Check and plan

`check` returns human-readable unmet prerequisites. An empty list means the local checks succeeded. It can receive `path=None` during dependency inspection, so it must handle that case. It must not access the network, write files, install packages, or perform setup. Report only what was inspected.

`plan` receives `operation="enable"` or `operation="disable"` and this step's saved receipt dictionary, or `None`. It must inspect current resources, reject incompatible saved state, and describe the approved change without mutating managed resources. All steps are planned before any step is applied. A later step cannot assume an earlier package step has already installed an importable dependency during planning.

`StepPlan` is a mutable dataclass with independent empty dictionaries for its defaults:

| Field | Default | Use |
| --- | --- | --- |
| `change: Any` | `None` | Public change description. Use `None` for no advertised resource change. Descriptions must be safe for text and JSON output. |
| `data: dict` | `{}` | Private, in-memory apply data, such as a transaction object, exact target, or file fingerprint. It is not saved as a receipt. |
| `state: dict` | `{}` | JSON-serializable ownership and recovery state. Store only what the step needs to retry or undo its own work. |

The runner validates planned recovery state with JSON serialization and rejects non-finite numbers. Keep checkpoint state serializable too. Private `data` is not an encrypted secret store. Do not place credentials in descriptions, recovery state, subprocess errors, or logs.

The runner composes `SetSetting` and `EnsureChannel` plans into a prospective configuration and asks conda to validate it before application. Arbitrary custom steps do not automatically participate in that projection. Use the built-in configuration steps instead of hiding configuration writes inside a custom installer.

### Apply and checkpoint

`apply` receives the same approved `StepPlan`. It must verify that any provider-specific target or external resource still matches the preview before changing it. Execute only the approved action. Do not select a different action or run another unconstrained package solve.

When a deployment plan is applied, the runner invokes each step's `apply`, including items with `change=None`. A no-op step must therefore return without mutation. On enable, the runner writes initial `state` before calling `apply`. If additional ownership information becomes known during apply, call `checkpoint(new_state)` before its corresponding side effect. The callback replaces this step's entire saved dictionary, so include existing fields that must be retained.

For example, an installer that can compute exact generated text only after a package is installed must checkpoint that text before writing the managed file. If installation succeeds and the final receipt write fails, the next invocation must be able to recognize and preserve or remove its own text. A return from a subprocess is not sufficient recovery evidence on its own.

The runner writes `completed=True` after successful enable. A missing completion flag can mean either that no effect occurred or that the effect occurred before the final checkpoint failed. Check the real resource when retrying. Custom receipt fields and any step-specific schema version remain the provider's responsibility.

## ManagedBlock interface

`ManagedBlock` implements the shared `plan` and `apply` methods for a generated block in a user file. Subclasses still implement `id` and `check`, plus these methods:

| Method | Required behavior |
| --- | --- |
| `target(ctx)` | Return `(Path, options_dict)` without writes. Options identify the provider-specific selection and must be safe to save in a receipt. |
| `blocks(content)` | Return a list of complete managed block strings, including their markers. Cleanup compares exact strings. |
| `has_marker(content)` | Detect existing or incomplete installations that must not be adopted without ownership. Be conservative about recognizing the provider's markers. |
| `render(options)` | Return the exact block that installation will write. This runs during approved apply, not during preview. It may prepare provider data, but must not edit the target file. |
| `install(options)` | Invoke the provider's installation operation for the already-resolved options. Honor the previewed destination and preserve unrelated text. |

The completion adapter supplies shell-path selection, block recognition, upstream rendering, and installation. `ManagedBlock` supplies ownership comparisons and receipt checkpoints.

### Block lifecycle

1. Planning resolves the destination and options, fingerprints the file, and reads its blocks. A symbolic-link target is refused by the fingerprint helper.
2. A saved target or options mismatch blocks the operation. Without saved ownership, any recognized pre-existing marker is preserved and setup is refused. Changed or additional complete owned blocks are also refused.
3. Enable apply resolves the destination again and checks options and the file fingerprint against the preview.
4. `render` prepares the block. The file fingerprint is checked again so rendering cannot silently change the target. A block that differs from a previously saved block requires disabling before upgrading.
5. The step checkpoints its target, options, and exact block before calling `install`.
6. After installation, it requires `blocks(target.read_text()) == [block]`. A mismatch fails and retains the receipt for recovery.
7. Disable rechecks ownership, removes one exact owned block through the shared atomic text writer, and preserves surrounding text. If the block is already absent, cleanup can finish without removing unrelated content.

Provider caches created during rendering are not automatically owned or removed. Target-parent creation and the installer itself remain provider responsibilities. The post-install check verifies the expected block, not every unrelated byte in the file. The provider must choose an installer that preserves user content and test partial-marker and interrupted-install behavior. `ManagedBlock` does not turn an arbitrary upstream writer into an atomic operation.

## Receipts and recovery

For configuration path `demo.yaml` and feature `sample`, the receipt is `demo.yaml.sample.json`. The current top-level format is version 2 with a `steps` mapping keyed by stable step IDs. The runner does not write private `StepPlan.data` into it.

Enable applies steps in declaration order. Before each effect, it saves ownership state, then records completion after success. Disable applies steps in reverse order, removes each step's saved entry after cleanup, and removes the receipt after all cleanup succeeds.

Configuration and receipt fingerprints are checked under a sidecar lock named after the configuration path with `.lock` appended. The runner also checks the configuration between steps. Shared writers use temporary files and atomic replacement. Custom steps must check and protect their own targets. Other editors do not honor this lock, and deployments using different configuration paths do not share it.

A failed step stops execution. Completed work and the receipt remain. There is no automatic rollback of previous steps, atomic transaction across package installation and files, server-side undo, or automatic package removal. Design disable so it remains safe after partial enable and after a cleanup side effect succeeds but its next receipt write fails.

Use `repair` to preview another enable attempt for saved intent, or disable to preview reverse cleanup. Neither operation may claim a pre-existing resource or overwrite later edits. Missing providers must be reinstalled before their steps can interpret receipts. Diagnostics can report a receipt whose feature is no longer installed, but cannot safely invent its cleanup procedure.

The runner rejects unsupported receipt versions and saved step IDs absent from the current declaration. Renaming or removing a step can therefore strand old receipts until the previous provider is restored. That check permits new step IDs, but authors must still plan upgrades explicitly. Changing a managed setting target or generated block can also require the old provider. Tell users to disable with the previous provider version before upgrading when recovery data will no longer be understood.

Built-in ownership checks cover declared setting keys and channel strings. They cannot detect two arbitrary custom steps writing the same external resource. Avoid multiple writers, use a shared prerequisite feature for shared resources, and test that disabling one consumer preserves resources still needed by another.

## Replacement and graduation metadata

For a renamed or replaced boolean feature, retain the old declaration and registered flag. Set `retired=True` when new opt-ins must stop, `replacement="new-feature"`, and actionable `guidance`. An explicit migration requires both declarations installed and both supporting the selected scope.

```python
migration_settings = (("plugins.old_format", "plugins.new_format"),)
```

Only source values saved in the selected file are transferred. Inherited defaults and environment overrides are not copied. Both keys must be declared non-secret settings. Conda normalizes source and destination types. A different existing mapped destination setting blocks migration, while an equivalent saved setting is preserved. Migration explicitly enables the replacement even if its boolean flag was saved as false. Multiple saved aliases require reconciliation. Source settings remain in the file.

Migration plans the old flag off and the replacement flag on in one configuration write. It checks the combined configuration, replacement readiness, overrides, and dependents before mutation. Generic migration refuses deployments because their package and shell cleanup needs explicit handling.

`graduation="optional"` reports graduation while retaining enable and disable. `graduation="unconditional"` means the provider's behavior no longer consults its obsolete opt-in. The provider must implement that behavior change itself. Enable and disable then refuse flag changes and direct users to `cleanup`.

Cleanup removes the saved obsolete flag, including recognized aliases, at the selected path. It leaves other settings and deployment resources alone. Keep registering the old boolean setting while supporting cleanup. Maturity `"stable"` alone does not imply graduation, and metadata never triggers automatic migration or cleanup.

## Provider verification

Test the installed entry points in a fresh conda process. A direct call to the hook does not test discovery. Check every supported scope, default values, configuration normalization, effective overrides, missing prerequisites, and runtime consumption of the flag.

For deployments, cover dry-run and cancelled confirmation, pre-existing resources, stale previews, missing receipts, unsupported versions, user edits, and repeated enable/disable. Inject failures before and after each side effect and receipt checkpoint. Test cleanup after a successful mutation whose completion write failed.

Use disposable conda installations, temporary homes, and isolated configuration search paths. `--file` isolates feature configuration reads and writes, but still allows environment-variable overrides and does not isolate host package installation or shell files. Setting `CONDARC` alone does not exclude all normal conda configuration sources. Only claim conda versions, upstream adapter versions, and native platforms that the provider's tests actually exercised.
