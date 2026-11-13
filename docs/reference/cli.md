# Command reference

Use `conda feature COMMAND --help` for the installed parser's exact options. From this checkout, prefix commands with `pixi run python -m conda` or select an examples environment as described in [installation](../how-to/install.md).

## Shared options

| Option | Behavior |
| --- | --- |
| `--user` | Write or inspect user configuration. Default when no scope is supplied. |
| `--system` | Select the hosting conda root installation's `.condarc`. Does not elevate privileges. |
| `-p PATH`, `--prefix PATH` | Select an existing environment's `.condarc`. |
| `--file PATH` | Select a standalone user-scope YAML configuration file plus environment-variable overrides. |
| `--check-prefix PATH` | Add an existing environment to mutation safety checks. Repeat for multiple environments. Never writes to those environments. |
| `--dry-run` | Preview a mutation without applying it. Package solving can refresh caches. |
| `-y`, `--yes` | Confirm the proposed mutation without an interactive prompt. |
| `--json` | Return one structured result on stdout for feature commands. |
| Verbosity and debug options | Supplied by conda's standard output/prompt argument helper. |

Scope options are mutually exclusive. `--file` accepts `.condarc`, `condarc`, `.yaml`, or `.yml` names recognized by conda. It requires an existing parent directory. Query commands share the parser options, but `--dry-run` does not add another mode to a query.

## Queries

### `list`

```sh
conda feature list [SCOPE] [--json]
```

Lists installed feature declarations and their state. It does not fetch a remote catalog. An empty catalog is valid. Human output shows feature ID, maturity, requested state, effective setting, readiness, and description.

### `explain FEATURE`

```sh
conda feature explain FEATURE [SCOPE] [--json]
```

Reports the provider identity, settings sources, readiness reasons, configurable settings, and guidance. It includes replacement/graduation metadata when present. The `sources` mapping identifies contributing files or environment variables, not a copy of all their values.

### `diagnose`

```sh
conda feature diagnose [SCOPE] [--json]
```

Inspects selected features and deployment receipts adjacent to the chosen configuration file. Returns `path`, `scope`, `problems`, and a message explaining the limits of local checks. Each problem has `feature`, `kind`, `message`, and `action`. Diagnostic kinds and recovery actions are listed in the [recovery guide](../how-to/recover.md).

## Mutations

### `enable FEATURE`

```sh
conda feature enable FEATURE [--with-dependencies] [SCOPE] [--dry-run | --yes]
```

Plans an opt-in or deployment. Checks compatibility, prerequisites, conflicts, scope, and prospective configuration. `--with-dependencies` includes supported prerequisite opt-ins at the selected scope. Package/custom prerequisites must be deployed separately. No implicit cross-scope writes occur.

### `configure FEATURE KEY=VALUE ...`

```sh
conda feature configure FEATURE plugins.limit=4 [SCOPE] [--dry-run | --yes]
```

Changes declared non-secret scalar settings. The example key is illustrative. Each key must appear once. Conda normalizes values and validates their combined configuration. For step-backed deployments, disable before changing settings when an existing receipt is present.

### `disable FEATURE` and `disable --all`

```sh
conda feature disable FEATURE [SCOPE] [--dry-run | --yes]
conda feature disable --all [SCOPE] [--dry-run | --yes]
```

Disables one feature or all boolean-backed features at the selected scope. A feature name and `--all` cannot be combined. Individual disable protects enabled dependents. Bulk disable processes dependents first and identifies deployments that require separate commands. Neither form is an all-plugins emergency switch. Unconditional graduated features are outside disable controls.

### `repair FEATURE`

```sh
conda feature repair FEATURE [SCOPE] [--dry-run | --yes]
```

Retries an enabled choice saved at the selected scope using the normal enable plan. It is not an instruction to overwrite user edits, force readiness, or adopt unowned resources. A fresh opt-in without a saved choice must use `enable`.

### `migrate FEATURE`

```sh
conda feature migrate FEATURE [SCOPE] [--dry-run | --yes]
```

Migrates a saved enabled boolean feature to its installed, provider-declared replacement. Both must support the selected scope. Transfers only mapped saved settings and refuses conflicting mapped destination settings. The replacement's enabled flag is explicitly set to true, including when it was saved as false. Generic deployment migrations are not supported.

### `cleanup FEATURE`

```sh
conda feature cleanup FEATURE [SCOPE] [--dry-run | --yes]
```

Removes saved obsolete boolean opt-ins for features declared unconditionally graduated. It does not remove functionality, packages, or shell resources. The provider must retain the old setting declaration to identify it and its aliases.

## Portable intent

### `export [FEATURE ...]`

```sh
conda feature export [FEATURE ...] [SCOPE] > intent.json
```

Always returns one JSON intent document, including without `--json`. With no IDs, it exports saved choices supported at that scope. Export omits unset choices and settings absent from the provider's portability allowlist. See [intent format](intent.md).

### `apply MANIFEST`

```sh
conda feature apply intent.json --file destination.yaml --dry-run --json
```

Requires an explicit `--user`, `--system`, `--prefix`, or `--file`. Reads version-1 intent and validates providers, settings, compatibility, dependencies, and conflicts. Boolean feature changes share one configuration write. Deployment imports are limited to one feature without imported settings. Apply refuses retired/replaced IDs rather than migrating them silently.

## Results and exit statuses

Mutation results include the operation, selected feature IDs, destination path, scope, public changes, and a message. Depending on the operation, they can also include removal keys, post-operation status, checked environments, and the scope of discovery. Private solved transactions, fingerprints, and recovery data are not returned as public plans.

Successful queries and previews exit `0`. Handled operation errors exit `1`. Argument parsing errors exit `2`. An empty diagnostic problem list is not required for a successful diagnostic query. Unexpected runtime failures or conda-level failures may be handled by conda itself.

Noninteractive writes require `--yes`. JSON output is noninteractive even when stdin is a terminal. A no-op or dry-run does not write. Prompts and diagnostics go to stderr. Do not combine stderr with stdout when saving an intent document. External errors for export/apply are sanitized because conda validation errors can contain configuration values.

## Conda doctor

```sh
conda doctor --list
conda doctor features --prefix /path/to/environment
conda doctor features --fix --prefix /path/to/environment
```

The plugin registers the `features` health check and fixer. Conda owns doctor's parser, text report, and confirmation behavior. For one complete JSON feature report, use `conda feature diagnose --json` instead.
