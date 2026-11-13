# Command reference

Use `conda feature COMMAND --help` for the installed parser's exact options. Run the conda installation where the plugin is installed. If the bare command selects another installation, use that host interpreter's `python -m conda`. See [installation](../how-to/install.md).

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

Reports the provider identity, settings sources, readiness reasons, configurable settings, and guidance. It includes replacement/graduation metadata when present. The `sources` mapping identifies contributing files or environment variables without copying all their values.

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

### `config FEATURE`

```sh
conda feature config FEATURE --set KEY VALUE [--set KEY VALUE ...] [SCOPE] [--dry-run | --yes]
conda feature config FEATURE --set plugins.limit 4 [SCOPE] [--dry-run | --yes]
conda feature config FEATURE --get [KEY ...] [SCOPE]
conda feature config FEATURE --show [KEY ...] [SCOPE]
conda feature config FEATURE --show-sources [SCOPE]
conda feature config FEATURE --describe [KEY ...] [SCOPE]
conda feature config FEATURE --validate [SCOPE]
conda feature config FEATURE --remove-key KEY [--remove-key KEY ...] [SCOPE] [--dry-run | --yes]
```

Changes declared non-secret scalar settings. Repeat `--set` for multiple key/value pairs, using each key only once. The example key is illustrative. Conda normalizes values and validates their combined configuration. For step-backed deployments, disable before changing settings when an existing receipt is present.

Choose one action per invocation. All named keys must be in the feature's declared non-secret settings. Use enable and disable to change its enabled flag.

| Action | Behavior |
| --- | --- |
| `--get [KEY ...]` | Read normalized values saved in the selected file. Omit keys to read all declared settings that are saved there. |
| `--show [KEY ...]` | Read effective values, including defaults and higher-priority overrides. Omit keys to show all declared settings. |
| `--show-sources` | Show contributing values grouped by source, filtered to the feature's declared settings. |
| `--describe [KEY ...]` | Show conda's parameter descriptions, types, and defaults. Omit keys for all declared settings. |
| `--validate` | Validate the combined conda configuration and local feature requirements without writing or solving packages. Unmet requirements produce an error. |
| `--remove-key KEY` | Remove the saved canonical key and any saved aliases, revealing inherited values or defaults. Repeat for several keys. Preview and confirmation are required as for `--set`. |

Removal fails if the key is not saved, would break an enabled feature's required settings, or belongs to an existing deployment that must be disabled first. Queries do not create files or receipts. JSON queries return `values`, `sources`, `descriptions`, or `valid`, alongside operation and feature details. A validation success does not verify runtime execution.

Conda validation errors omit configuration values from command output because those errors can include private, unrelated settings. Inspect invalid configuration locally. `--show-sources` validates and returns only declared settings from each source.

Sequence operations (`--add`, `--prepend`, `--append`, and `--remove`) are not supported because feature configuration currently declares scalar settings only.

The `config` command was added in 0.2.0. Release 0.1.0 supports setting values through the following syntax, which remains available:

```sh
conda feature configure FEATURE KEY=VALUE [KEY=VALUE ...] [SCOPE] [--dry-run | --yes]
```

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

Retries an enabled choice saved at the selected scope using the normal enable plan. It preserves user edits and ownership checks and still requires readiness checks to pass. A fresh opt-in without a saved choice must use `enable`.

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

## Results and exit statuses

Mutation results include the operation, selected feature IDs, destination path, scope, public changes, and a message. Depending on the operation, they can also include removal keys, post-operation status, checked environments, and the scope of discovery. Private solved transactions, fingerprints, and recovery data are not returned as public plans.

Successful queries and previews exit `0`. Handled operation errors exit `1`. Argument parsing errors exit `2`. An empty diagnostic problem list is not required for a successful diagnostic query. Unexpected runtime failures or conda-level failures may be handled by conda itself.

Noninteractive writes require `--yes`. JSON output is noninteractive even when stdin is a terminal. A no-op or dry-run does not write. Prompts and diagnostics go to stderr.

## Conda doctor

```sh
conda doctor --list
conda doctor features --prefix /path/to/environment
conda doctor features --fix --prefix /path/to/environment
```

The plugin registers the `features` health check and fixer. Conda owns doctor's parser, text report, and confirmation behavior. For one complete JSON feature report, use `conda feature diagnose --json` instead.
