# How configuration and deployment fit together

## The host and the target are different

The host is the Python environment running conda and loading its plugins. The target is the configuration destination selected by a command. `--prefix` changes the target configuration, not the host that needs provider code installed.

For example, enabling PyPI support can install the solver plugin into the host while writing solver/channel settings into a project environment. Shell completion also edits the user's shell profile outside `.condarc`. Choosing `--file` changes only the conda configuration destination, so it does not isolate either operation.

## A feature has several kinds of state

| Field | What it says | What it does not say |
| --- | --- | --- |
| `requested` | The choice saved at the selected destination, or an enabled deployment receipt | What higher-priority configuration permits |
| `effective` | The current boolean value, or whether deployment step checks are satisfied | That provider code executed |
| `readiness` | Whether declared versions, platform, dependencies, conflicts, and setup checks permit use | That authentication or remote services were verified |
| `runtime` | Currently `unknown` | A promise of runtime observation or suppression |
| `maturity` | The provider's experimental, preview, or stable classification | Whether the user enabled the feature |
| `lifecycle` | Available, retired, replaced, or graduated metadata | Permission to migrate without confirmation |

An enabled boolean can still read true when prerequisites are missing. Providers must check their own runtime requirements because this plugin does not intercept their operations. A deployment can also report ready without a receipt if its resources already existed. The plugin does not take ownership of those resources just because it found them.

Conda remains responsible for settings types and precedence. The plugin uses its contexts and validators rather than maintaining a second `.condarc` parser. The planner validates combined prospective settings before mutation, including interactions between individually valid settings.

## Steps describe changes and recovery

`InstallPackages`, `SetSetting`, and `EnsureChannel` cover the common operations. `ManagedBlock` handles ownership and recovery around a provider-generated block in a file. A feature coordinates them in declaration order and disables them in reverse order.

A step plan separates what the user approves from the data needed to apply it. The preview shows proposed changes. Private data holds details such as the solved transaction or previous configuration. The receipt stores only the recovery state needed for retry and cleanup.

Package solving may refresh caches during preview. Application executes the approved transaction rather than running another unconstrained solve. Existing packages, including the running conda and Python, are protected from replacement by the built-in package step. Packages remain installed when a feature is disabled because removing them safely requires more knowledge than this feature's ownership record.

## Ownership is narrower than presence

If a setting already has the desired value, the step can record that it does not own a change. If the step changes it, it records enough prior state to restore it, but refuses to replace a later user edit. Channel steps own their added channel, not all channels in the list. They use a digest to compare inherited channel lists without duplicating authenticated URLs in receipts.

Feature declarations cannot claim the same setting or channel independently. A shared resource belongs in a prerequisite feature. This avoids one feature removing a resource another still needs. Cross-environment checks cover explicit targets and the current user's known registry, not a complete machine-wide dependency graph.

## Receipts are not backups or locks on user intent

For `settings.yaml` and feature `example`, the receipt is `settings.yaml.example.json`. Current receipts use version 2 and store state by stable step ID. The exact contents are implementation details, not a public interchange format. Use intent export to move choices between machines.

The runner checkpoints ownership before side effects and marks completion afterward. If an operation succeeds but a final checkpoint fails, a retry can inspect both the resource and saved state. A failed later step does not imply earlier steps were rolled back. Diagnostics can report incomplete checkpoints even when resources already look ready.

File fingerprints and sidecar locks help detect changes made after preview. Package installation, shell setup, and configuration writes can still succeed or fail separately, and external editors do not honor the locks. If a plan is stale, preview again. If a resource was edited, reconcile the edit before cleanup.

## Installed providers are trusted code

Pluggy validates registration and hook signatures. It does not sandbox imports or hook execution. Providers must keep declaration hooks and checks free of setup, network access, and credential inspection. Only install providers you trust.

Providers decide which settings are portable. The plugin rejects recognizable credential-bearing URLs and absolute paths, but cannot find every secret in a string. Keep secrets out of both configurable and portable feature settings.
