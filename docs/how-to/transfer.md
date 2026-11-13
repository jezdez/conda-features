# Migrate and transfer feature choices

Use migration to switch from an old feature to the replacement declared by its provider. Use export/apply to move saved choices between configurations. Review the preview before approving changes, including any replacement behavior.

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

## Export saved intent

```sh
conda feature export --file source.yaml > intent.json
```

Export always writes JSON, even without `--json`. To select feature IDs:

```sh
conda feature export FEATURE_A FEATURE_B --file source.yaml > intent.json
```

Export includes only enabled/disabled choices saved at that scope and omits unset choices. Providers must allow portable settings separately, so a configurable setting may not be portable. Receipts and runtime observations are never included.

Keep stdout separate from stderr when saving the document. Export may fail if it cannot safely inspect the configuration, or if a portable value contains an authenticated URL, unsupported numeric value, or machine-specific absolute path. Check that export succeeded before using the file. A redirected error or empty file is not a valid export.

## Apply to an explicit destination

```sh
conda feature apply intent.json --file destination.yaml --dry-run --json
conda feature apply intent.json --file destination.yaml --yes --json
```

The file's parent directory must exist. You can also choose `--user`, `--system`, or `--prefix PATH` explicitly. The scope recorded in the source document tells you where the choices came from. You still need to choose and authorize the destination.

Apply requires installed declarations with matching provider identities. It rejects unknown features, duplicate entries, unsupported scopes, retired or replaced IDs, incompatible enabled features, and non-portable settings. Migrate old IDs before exporting new intent. Renaming them in a manifest is not a substitute for migration.

Apply validates boolean choices and settings together, then writes them once. You can apply only one deployment feature at a time, without deployment settings in the document. If an exported deployment includes settings, configure those values explicitly at the destination first. Then change the single-feature document's `settings` object to `{}` and review it before applying the saved choice. If you exported several deployments together, export each one separately before applying.

Transferring intent does not lock package builds, copy ownership, or verify readiness on another machine. You still need to handle package resolution and authentication separately. See the [format reference](../reference/intent.md) for the exact schema.
