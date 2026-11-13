# Diagnose and recover setup

Start with the same scope or file used for deployment:

```sh
conda feature explain FEATURE --file /path/to/feature.yaml --json
conda feature diagnose --file /path/to/feature.yaml --json
```

`explain` inspects one declaration. `diagnose` reports problems with selected features and nearby deployment receipts, including receipts whose provider is missing. Both run trusted provider declarations and local checks. Built-in checks do not solve packages, install resources, or verify authentication.

## Interpret a diagnostic

| Kind | Meaning | Next action |
| --- | --- | --- |
| `overridden` | An enabled boolean choice is saved, but the effective setting is disabled | Inspect the reported sources and remove or change the overriding value |
| `not-ready` | A selected feature has unmet local prerequisites | Review the reasons, then preview repair |
| `incomplete` | A deployment receipt lacks completed checkpoints, even if resources already exist | Retry the operation you intended: repair for enable, disable for cleanup |
| `inspection-error` | A present provider could not inspect its state safely | Preserve the receipt and investigate the local error |
| `missing-provider` | A supported receipt remains for a feature absent from discovery | Reinstall the provider that understands the receipt |
| `invalid-receipt` | An orphan receipt has an unsupported format or cannot be read safely | Restore the matching provider version and inspect locally |

An empty problem list means these local checks found no problem. It does not prove that provider code executed, that a network service is reachable, or that credentials are valid. `diagnose` can return exit status 0 while reporting problems, because the query itself succeeded. Automation should inspect the `problems` array.

## Retry interrupted setup

First identify which operation was interrupted. After interrupted enable, use `repair` as shown below. After interrupted disable, rerun `disable FEATURE` at the same scope or file, starting with `--dry-run`. A retained receipt still represents an enabled choice until cleanup finishes. `repair` calls enable and can reinstall resources already removed during an interrupted disable.

```sh
conda feature repair FEATURE --file /path/to/feature.yaml --dry-run
conda feature repair FEATURE --file /path/to/feature.yaml --yes
```

Repair requires an enabled choice saved at that scope. It uses the normal enable plan, including compatibility checks, ownership rules, and checks of affected environments. A receipt-only repair can finish checkpoints without rewriting a resource that already has the expected value.

If setup installed packages and later failed to write configuration, those packages remain installed. The receipt lets a retry distinguish completed work from work still needed. There is no single transaction spanning package installation, conda configuration, and shell files.

## Preserve user edits

An error that a setting or hook changed since deployment is deliberate protection. Do not remove the receipt or force a replacement to silence it. Compare the current resource with the recorded change locally, decide which value you want, and restore the provider's expected state only if appropriate before retrying disable or repair.

A stale preview is different: some input changed after planning. Run the command again and inspect the new preview. Concurrent tools may not honor this plugin's locks, so a preview is not a long-lived approval artifact.

## Handle missing or older providers

Restore the provider that wrote a receipt before asking it to clean up. A receipt records a feature ID and step state, not a complete package installation recipe. The plugin cannot always determine which distribution or version must be restored.

Receipt format version 2 is current. Older versions and unknown step IDs are rejected with recovery guidance. Disable using the earlier provider version before upgrading when the new provider cannot interpret the receipt. Keep backups of the relevant configuration and receipts before manual recovery.

## Use conda doctor

```sh
conda doctor features --prefix /path/to/environment
conda doctor features --fix --prefix /path/to/environment
```

The doctor adapter inspects that environment's `.condarc` and its receipts. It prints a local report and previews repairs through conda's confirmation flow. Cancellation is handled by conda. It does not scan arbitrary user files or all receipt locations. Use `feature diagnose --file ... --json` when you need a structured result for another destination.

## Common setup errors

- **Unknown feature:** install its declaration provider in the Python environment running conda, then start a fresh invocation.
- **Wrong hook decorator:** use `conda_features.hooks.hookimpl` for feature declarations and conda's decorator for conda hooks.
- **Unsupported scope:** preview at a scope the provider declares. Do not silently substitute another destination.
- **Package replacement refused:** provision compatible prerequisites outside feature deployment, then preview again. The package step will not replace existing packages in the running installation.
- **Pre-existing completion hook:** the adapter will not claim ownership of it. Manage that installation through its original tool or remove it deliberately before redeploying.
- **Sanitized intent error:** export/apply omits configuration values from external errors because they can contain credentials. Inspect the local configuration privately instead of posting it unredacted.
