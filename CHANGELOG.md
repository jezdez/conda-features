# Changelog

## 0.2.0 - 2026-11-13

- Breaking: remove `conda feature export`, `conda feature apply`, the custom intent JSON format, and `Feature.portable_settings`/`export_intent`. There is no deprecation period or replacement manifest. Use conda configuration and explicit feature commands. Existing local deployment receipts, `--json` output, and the provider's `Feature.apply` method are unchanged. Release 0.1.0 artifacts retain the old commands.

- Add `conda feature config FEATURE --set KEY VALUE`, following `conda config` argument syntax. Repeat `--set` for multiple settings. The released `configure FEATURE KEY=VALUE` command remains supported.
- Add feature-scoped `--get`, `--show`, `--show-sources`, `--describe`, `--validate`, and confirmed `--remove-key`. Queries expose only declared settings. Removing an override preserves inherited configuration and checks feature requirements.
- Rewrite the README and documentation in plainer language while retaining setup and recovery guidance.

## 0.1.0 - 2026-11-13

Initial public release of `conda-features`, available on [PyPI](https://pypi.org/project/conda-features/0.1.0/) and [Anaconda.org](https://anaconda.org/jezdez/conda-features).

### Feature management

- Discover installed providers through the `conda_features` Pluggy hook.
- List and explain saved choices, effective configuration, readiness, and lifecycle metadata without claiming to observe provider execution.
- Enable, configure, and disable features with previews, explicit confirmation, and JSON output.
- Select user, installation, environment, or standalone-file configuration destinations using conda's typed settings and precedence.
- Plan explicit prerequisite opt-ins and protect dependents in checked environments. Shared changes inspect the current user's registry and explicit targets, not every environment on the machine.

### Deployment and recovery

- Declare reusable package, scalar-setting, channel, and managed-file-block steps.
- Execute approved package transactions while protecting the running conda and Python installation from replacement.
- Record resource ownership in versioned receipts for retry and reverse-order cleanup. Preserve pre-existing resources and later user edits.
- Diagnose local drift, missing providers, overrides, and incomplete checkpoints through `feature diagnose` and `conda doctor features`.
- Repair saved setup through the existing preview and confirmation flow. Interrupted disable must be resumed with disable, not repair.

### Lifecycle and portability

- Preview explicit migration between boolean-backed features using provider-declared setting mappings.
- Distinguish optional graduation from unconditional functionality and clean up obsolete boolean opt-ins.
- Export versioned feature intent with explicitly portable settings. Apply validates provider identity, configuration, compatibility, dependencies, and conflicts before mutation.
- Reject recognizable credential-bearing URLs, absolute machine paths, and non-finite values in portable settings. Generic deployment migration and deployment-setting round-tripping remain limited.

### Documentation and distribution

- Provide Sphinx documentation organized into tutorials, how-to guides, reference, and explanation, published through GitHub Pages.
- Add native core CI for Linux, Windows, and ARM macOS, with separate real-provider integration tests.
- Publish the core package under BSD-3-Clause. The repository-only `conda-features-examples` package supplies real PyPI-support and shell-completion deployments but is not published to either registry.
- Attach Python build provenance, conda build provenance, and CEP 27 publication evidence to the [GitHub release](https://github.com/jezdez/conda-features/releases/tag/0.1.0).

### Publication history

The Python artifacts were published from commit `3098f8ae2cbb0bc15bf28c1ec5ab2573d6c2e408`. An Anaconda workflow-secret fix required moving the then-mutable `0.1.0` tag to `d853260e26a9543aaee769f92731f0ac5c1d7fc2`. The recovery reused the published Python files byte-for-byte and built the conda package from the same published sdist.

The GitHub release was subsequently recreated with release immutability enabled. Its five assets retained their SHA-256 digests, and the recovery tag was preserved. The release is now immutable. This change did not replace packages on PyPI or Anaconda.org. The documentation's release-verification guide explains the distinct original Python and recovery conda source commits.
