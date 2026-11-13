# Migrate and transfer feature choices

Migration changes from a provider-declared old feature to its replacement. Export/apply moves saved intent between configurations. Neither operation grants permission to install arbitrary replacement behavior without a preview.

## Migrate a replaced feature

```sh
conda feature explain OLD --user
conda feature migrate OLD --user --dry-run
conda feature migrate OLD --user --yes
```

Replace `OLD` with an installed declaration that names a replacement. Both feature providers must be installed and support the selected scope. The old opt-in must be saved as enabled there. The replacement must be available and ready in the prospective configuration. Enabled dependents that still require the old feature block migration.

For boolean-backed features, migration disables the old flag, enables the replacement, and transfers provider-declared settings in one configuration write. Only values saved in the selected file transfer. Inherited values are not copied. Existing mapped destination settings must either match or be reconciled first. Migration explicitly sets the replacement's enabled flag to true, even if it was previously saved as false. Source settings remain untouched for manual cleanup.

The provider's `migration_settings` mapping controls which non-secret settings transfer. Conda validates their types and the combined result. Saved alias spellings are handled explicitly. This command does not migrate generic package or shell deployments. Those need a provider-specific migration path, or explicit replacement enable and old-feature disable commands reviewed separately.

## Clean up a graduated opt-in

```sh
conda feature explain GRADUATED --user
conda feature cleanup GRADUATED --user --dry-run
conda feature cleanup GRADUATED --user --yes
```

An optional graduated feature still supports enable and disable. An unconditional graduated feature does not: its functionality no longer depends on its old boolean flag. Cleanup removes the saved obsolete flag, not the functionality. Dependencies and conflicts still account for the unconditional capability.

The provider must retain its old feature and setting declarations for cleanup to work. Cleanup does not remove package deployments or shell resources. It preserves unrelated configuration and refuses a changed destination after preview.

## Export saved intent

```sh
conda feature export --file source.yaml > intent.json
```

Export always writes JSON, even without `--json`. To select feature IDs:

```sh
conda feature export FEATURE_A FEATURE_B --file source.yaml > intent.json
```

Only saved enabled/disabled choices at that scope are included. Unset choices are omitted. Portable settings require a separate provider allowlist. A setting can be configurable without being portable. Export never includes receipts or runtime observations.

Keep stdout separate from stderr when saving the document. Export may fail if the configuration cannot be inspected safely or a portable value contains an authenticated URL, unsupported numeric value, or machine-specific absolute path. Do not treat a redirected error or empty file as a valid export.

## Apply to an explicit destination

```sh
conda feature apply intent.json --file destination.yaml --dry-run --json
conda feature apply intent.json --file destination.yaml --yes --json
```

The file's parent directory must exist. Alternatively choose `--user`, `--system`, or `--prefix PATH` explicitly. The source document's scope describes where the choices came from. It does not select or authorize a destination.

Apply requires installed declarations with matching provider identities. It rejects unknown features, duplicate entries, unsupported scopes, retired or replaced IDs, incompatible enabled features, and non-portable settings. Migrate old IDs explicitly before exporting new intent rather than changing their names blindly in a manifest.

Boolean choices and settings are validated together and written once. Deployment intent is limited to one feature at a time and cannot carry deployment settings into apply. An exported deployment with nonempty settings cannot be applied unchanged. Configure those values explicitly at the destination, then review a single-feature document with its `settings` object changed to `{}` before applying the saved choice. Several deployments exported together need separate selected exports before applying.

Intent does not lock package builds, copy ownership, or prove readiness on another machine. Package resolution and authentication are separate. See the [format reference](../reference/intent.md) for the exact schema.
