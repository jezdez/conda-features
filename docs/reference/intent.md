# Feature intent format

An intent document records saved feature choices for transfer to another configuration. It contains no package lock, deployment receipt, file fingerprint, or runtime observation.

## Version 1

```json
{
  "version": 1,
  "scope": "user",
  "features": [
    {
      "name": "sample",
      "provider": "my-provider",
      "requested": "enabled",
      "settings": {
        "plugins.sample_limit": 4
      }
    }
  ]
}
```

This is an illustrative provider, not a built-in feature. The [provider tutorial](../tutorials/create-provider.md) explains declaration and installation.

| Field | Required value |
| --- | --- |
| `version` | Integer `1`, not a boolean or string |
| `scope` | `user`, `system`, or `environment`, describing the source scope |
| `features` | List of entries with distinct feature IDs. An empty list is allowed. |
| Entry `name` | Installed feature ID |
| Entry `provider` | Exact current provider entry-point identity for that feature |
| Entry `requested` | `enabled` or `disabled` |
| Entry `settings` | Object containing only that feature's declared portable setting names |

The root must contain exactly `version`, `scope`, and `features`. Entries must contain exactly `name`, `provider`, `requested`, and `settings`. Additional fields are rejected. The format version is independent of deployment receipt version 2.

## Which values transfer

Export includes values saved in the selected configuration file, normalized through conda. It does not copy effective values inherited from unrelated sources. Canonical setting names appear in the document even when an accepted alias was saved locally.

Portable values are JSON scalars: null, booleans, integers, finite floats, and strings. Lists and objects are not accepted as setting values. Providers must explicitly list portable names in `Feature.portable_settings`, which must be a subset of `Feature.settings`.

The implementation rejects recognizable URL credentials, query strings, fragments, token-style `/t/` paths, local `file:` URLs, and machine-specific absolute paths. It also rejects a numeric string that normalizes to a non-finite float. Even a harmless URL query can be refused, while arbitrary secrets in free-form strings may go undetected. Providers must never mark secret settings portable.

## Applying a document

Select the destination explicitly in the command. A user-scope export can be applied to an environment scope if the provider supports it. The document's source `scope` does not override `--prefix` or choose another user's file.

Provider identities must match. This prevents a different installed provider from silently taking over the same feature ID during import. It is not a cryptographic signature or a trust guarantee for the provider package.

Retired, replaced, and unconditional graduated features are refused. Review their metadata and migrate explicitly. Enabled features must satisfy compatibility and readiness checks in the prospective configuration. Disabling choices still protect enabled dependents.

Applying several boolean features validates their combined configuration before one write. A deployment entry is applied through its existing enable/disable method and must be the only entry in that document. Deployment entries containing imported settings are refused, even if those settings already match the destination. Configure those values explicitly at the destination, then review a single-feature document with `"settings": {}` before applying the saved choice.

## Automation

```sh
conda feature export --file source.yaml > intent.json
conda feature apply intent.json --file target.yaml --dry-run --json
conda feature apply intent.json --file target.yaml --yes --json
```

Check each command's exit status before using its output. Apply returns a mutation result, not a new intent document. Do not store its destination paths or status result as though they were portable input.

Invalid input is not partially applied by the boolean importer. Package and custom deployment operations retain their own partial-failure and recovery semantics. A successful import is not evidence that authentication or remote services work.
