# Diagnose and recover setup

Start with the same scope or file used for deployment:

```sh
conda feature explain FEATURE --file /path/to/feature.yaml --json
conda feature diagnose --file /path/to/feature.yaml --json
```

`explain` inspects one declaration. `diagnose` reports problems with selected features and nearby deployment receipts, including those left by a missing provider. Both run trusted provider declarations and local checks. The built-in checks do not solve packages, install resources, or verify authentication.

## Interpret a diagnostic

| Kind | Meaning | Next action |
| --- | --- | --- |
| `overridden` | An enabled boolean choice is saved, but the effective setting is disabled | Inspect the reported sources and remove or change the overriding value |
| `not-ready` | A selected feature has unmet local prerequisites | Review the reasons, then preview repair |
| `incomplete` | A deployment receipt lacks completed checkpoints, even if resources already exist | Retry the operation you intended: repair for enable, disable for cleanup |
| `inspection-error` | A present provider could not inspect its state safely | Preserve the receipt and investigate the local error |
| `missing-provider` | A supported receipt remains for a feature absent from discovery | Reinstall the provider that understands the receipt |
| `invalid-receipt` | An orphan receipt has an unsupported format or cannot be read safely | Restore the matching provider version and inspect locally |

An empty problem list means the local checks passed. These checks do not verify provider execution, network access, or credentials. `diagnose` can return exit status 0 even when it finds problems, since the query itself succeeded. In scripts, inspect the `problems` array.

## Retry interrupted setup

After interrupted enable, use `repair` as shown below. After interrupted disable, rerun `disable FEATURE` at the same scope or file, starting with `--dry-run`. The receipt continues to record an enabled choice until cleanup finishes. Do not use `repair` to finish disabling: it calls enable and can reinstall resources you already removed.

```sh
conda feature repair FEATURE --file /path/to/feature.yaml --dry-run
conda feature repair FEATURE --file /path/to/feature.yaml --yes
```

Repair requires an enabled choice saved at that scope. It follows the normal enable plan, with the same compatibility checks, ownership rules, and checks of affected environments. If a resource already has the expected value, repair can finish its receipt checkpoints without rewriting it.

If setup installs packages and then fails to write configuration, the packages stay installed. On retry, the receipt identifies which work is complete and what remains. Package installation, conda configuration, and shell files are not part of a single transaction.

## Preserve user edits

If a setting or hook has changed since deployment, the command stops to protect your edits. Do not remove the receipt or force a replacement to bypass the error. Compare the current resource with the recorded change locally and decide which value to keep. If restoring the provider's expected state is appropriate, do that before retrying disable or repair.

A stale preview means an input changed after planning. Run the command again and inspect the new preview. Other tools may ignore this plugin's locks, so do not rely on an old preview to approve later changes.

## Handle missing or older providers

Reinstall the provider that wrote the receipt before trying cleanup. Receipts contain the feature ID and step state, but not a complete package installation recipe. You may need to identify the original distribution and version yourself.

The current receipt format is version 2. The plugin rejects older formats and unknown step IDs with recovery guidance. If a new provider cannot read the receipt, disable the deployment with the earlier provider version before upgrading. Back up the relevant configuration and receipts before manual recovery.

## Use conda doctor

```sh
conda doctor features --prefix /path/to/environment
conda doctor features --fix --prefix /path/to/environment
```

The doctor adapter inspects that environment's `.condarc` and receipts. It prints a local report and previews repairs, using conda to handle confirmation and cancellation. It does not scan arbitrary user files or all receipt locations. Use `feature diagnose --file ... --json` for a structured result at another destination.

## Common setup errors

- Unknown feature: install its declaration provider in the Python environment running conda, then run the command again.
- Wrong hook decorator: use `conda_features.hooks.hookimpl` for feature declarations and conda's decorator for conda hooks.
- Unsupported scope: preview at a scope the provider supports. Review the new destination before making changes.
- Package replacement refused: install compatible prerequisites outside feature deployment, then preview again. The package step will not replace existing packages in the running installation.
- Pre-existing completion hook: the adapter will not claim ownership of it. Manage the installation through its original tool, or deliberately remove it before redeploying.
- Sanitized config error: configuration validation errors can contain private values. Inspect invalid configuration locally instead of posting it unredacted.
