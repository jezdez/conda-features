# Migrate and transfer feature choices

Use migration to switch to a provider-declared replacement. To repeat a setup elsewhere, inspect the source settings, then configure and enable the feature at the chosen destination. In either case, review the preview before accepting changes.

## Migrate a replaced feature

```sh
conda feature explain OLD --user
conda feature migrate OLD --user --dry-run
conda feature migrate OLD --user --yes
```

Replace `OLD` with an installed declaration that names a replacement. Both providers must be installed and support the selected scope, where the old opt-in must be saved as enabled. The replacement must be available and ready with the proposed configuration. Migration stops if any enabled dependents still require the old feature.

For boolean-backed features, migration disables the old flag, enables the replacement, and transfers provider-declared settings in one configuration write. It copies only values saved in the selected file, leaving inherited values out. If a mapped destination setting already has a different value, reconcile it before migrating. Migration sets the replacement's enabled flag to true even if it was previously saved as false. It leaves source settings in place for you to clean up manually.

The provider's `migration_settings` mapping controls which non-secret settings transfer. Conda validates their types and the combined result, and migration handles settings saved under alias spellings. Package and shell deployments need a provider-specific migration path. Otherwise, enable the replacement and disable the old feature in separate commands, reviewing each preview.

## Clean up a graduated opt-in

```sh
conda feature explain GRADUATED --user
conda feature cleanup GRADUATED --user --dry-run
conda feature cleanup GRADUATED --user --yes
```

You can still enable and disable an optional graduated feature. An unconditional graduated feature no longer depends on its old boolean flag, so you cannot enable or disable it here. Cleanup removes the obsolete saved flag while leaving the functionality in place. Dependencies and conflicts still account for the unconditional capability.

Cleanup requires the provider's old feature and setting declarations. It leaves package deployments, shell resources, and unrelated configuration in place. If the destination changes after preview, cleanup stops.

## Inspect the source configuration

```sh
conda feature explain FEATURE --file source.yaml
conda feature config FEATURE --get --file source.yaml
conda feature config FEATURE --show --file source.yaml
```

Replace `FEATURE` with the installed feature ID. `--get` shows declared settings saved in the selected file. `--show` shows effective values, including defaults and environment-variable overrides. Use `explain` to check the saved enabled choice separately.

Choose which values belong at the destination. A machine-specific path may need changing, and an inherited value may not need to be saved there.

## Configure and enable at the destination

```sh
conda feature config FEATURE --set KEY VALUE --file destination.yaml --dry-run
conda feature config FEATURE --set KEY VALUE --file destination.yaml --yes
conda feature enable FEATURE --file destination.yaml --dry-run
conda feature enable FEATURE --file destination.yaml --yes
conda feature config FEATURE --get --file destination.yaml
conda feature config FEATURE --show --file destination.yaml
```

Replace `KEY VALUE` with a declared setting and its chosen value. Repeat `--set` for additional settings, or skip configuration if the destination's effective values already meet your needs. To save a disabled choice, use `disable` instead of `enable` and review its preview.

The file's parent directory must exist. You can also choose `--user`, `--system`, or `--prefix PATH` explicitly, if the feature supports that scope. The provider must be installed in the conda installation running these commands.

Configuration and enable are separate operations, each with its own preview and confirmation. For an existing step-backed deployment, disable it before changing its settings. Repeat the commands for each feature, setting up prerequisites before dependents.

Enable checks readiness and plans deployment at the destination. It records ownership there rather than copying it from the source. Reusing settings does not lock package builds or verify runtime behavior, so package resolution and authentication still need separate handling.
