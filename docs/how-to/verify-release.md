# Verify release artifacts

The release workflow follows the same sequence as `conda-skills`: reusable tests, Python builds, provenance, a draft GitHub release, PyPI trusted publishing, conda builds from the published source distribution, conda attestations, Anaconda upload, and finally a public GitHub release.

Only `conda-features` is published. The examples distribution remains source-only. Python artifacts are built once and passed between jobs. The conda recipe downloads the published PyPI sdist and checks the SHA-256 recorded by the Python build.

## Find the evidence

Each [GitHub release](https://github.com/jezdez/conda-features/releases) includes:

- The Python wheel and source distribution.
- `python-provenance.sigstore.json`, containing GitHub build provenance for the Python artifacts.
- `conda-provenance.sigstore.json`, containing GitHub build provenance for the conda artifact.
- `conda-publication.sigstore.json`, containing the CEP 27 publication statement for `https://conda.anaconda.org/jezdez`.

GitHub also stores the attestations by artifact digest. PyPI receives its own attestations through the trusted publisher. The conda package is distributed through the [jezdez channel](https://anaconda.org/jezdez/conda-features), not rebuilt from a GitHub-generated source archive.

## Immutable GitHub releases

Release immutability is enabled for this repository, and `0.1.0` is confirmed immutable. Published release assets cannot be added, replaced, or removed, and the associated tag cannot be moved or deleted while the release exists. Titles and release notes can still be edited. Deleting an immutable release does not permit reusing its tag name.

GitHub automatically creates a release attestation binding the release tag, commit, and asset digests. This is separate from the workflow build-provenance bundles and the CEP 27 publication statement. Verify the release with a current GitHub CLI:

```sh
gh release verify 0.1.0 --repo jezdez/conda-features
```

After downloading an attached asset, verify that its bytes belong to that release:

```sh
gh release verify-asset 0.1.0 conda_features-0.1.0-py3-none-any.whl \
  --repo jezdez/conda-features
```

Use `gh attestation verify` below to check the build workflow and source claims as well. The release attestation does not replace those checks. The conda package is hosted on Anaconda.org rather than attached to this GitHub release, so use its build and publication bundles below, not `gh release verify-asset`, to verify it.

## Verify 0.1.0

Use a current [GitHub CLI](https://cli.github.com/) with attestation support. Download the Python release files and bundles into an empty working directory:

```sh
gh release download 0.1.0 --repo jezdez/conda-features \
  --pattern 'conda_features-0.1.0*' --pattern '*.sigstore.json'
```

Python 0.1.0 was built and published from commit `3098f8ae2cbb0bc15bf28c1ec5ab2573d6c2e408`. A later workflow-only recovery moved the tag to `d853260e26a9543aaee769f92731f0ac5c1d7fc2` to finish Anaconda publication. The Python files were reused byte-for-byte, not replaced or re-attested under the new commit.

After recovery, the mutable GitHub release was recreated as immutable using the same tag and all five existing assets. Their hashes were checked before publication. The release attestation binds that final tag and asset set. Python build provenance still correctly identifies the original build commit. See the [changelog](../changelog.md) for the publication history.

Verify each Python artifact against its original signer and source commit:

```sh
gh attestation verify conda_features-0.1.0-py3-none-any.whl \
  --repo jezdez/conda-features \
  --bundle python-provenance.sigstore.json \
  --signer-workflow jezdez/conda-features/.github/workflows/release.yml \
  --signer-digest 3098f8ae2cbb0bc15bf28c1ec5ab2573d6c2e408 \
  --source-digest 3098f8ae2cbb0bc15bf28c1ec5ab2573d6c2e408 \
  --source-ref refs/tags/0.1.0 --deny-self-hosted-runners
```

Repeat with `conda_features-0.1.0.tar.gz`. The original SHA-256 values are:

| File | SHA-256 |
| --- | --- |
| `conda_features-0.1.0-py3-none-any.whl` | `831232d041e8972a62872a3f314fdbf4321235394afc15c7572e6a71a7e14abf` |
| `conda_features-0.1.0.tar.gz` | `30f2255eb91497f6f26285a7b0515bd518e1e2dbced1524c36add675c72e0c46` |

Download the published conda artifact, then verify its provenance:

```sh
curl --fail --location --proto '=https' --proto-redir '=https' \
  https://conda.anaconda.org/jezdez/noarch/conda-features-0.1.0-pyh4616a5c_0.conda \
  --output conda-features-0.1.0-pyh4616a5c_0.conda

gh attestation verify conda-features-0.1.0-pyh4616a5c_0.conda \
  --repo jezdez/conda-features \
  --bundle conda-provenance.sigstore.json \
  --signer-workflow jezdez/conda-features/.github/workflows/publish-conda.yml \
  --signer-digest d853260e26a9543aaee769f92731f0ac5c1d7fc2 \
  --source-digest d853260e26a9543aaee769f92731f0ac5c1d7fc2 \
  --source-ref refs/tags/0.1.0 --deny-self-hosted-runners \
  --predicate-type https://slsa.dev/provenance/v1
```

Verify the publication statement and inspect its target channel:

```sh
gh attestation verify conda-features-0.1.0-pyh4616a5c_0.conda \
  --repo jezdez/conda-features \
  --bundle conda-publication.sigstore.json \
  --signer-workflow jezdez/conda-features/.github/workflows/publish-conda.yml \
  --signer-digest d853260e26a9543aaee769f92731f0ac5c1d7fc2 \
  --source-digest d853260e26a9543aaee769f92731f0ac5c1d7fc2 \
  --source-ref refs/tags/0.1.0 --deny-self-hosted-runners \
  --predicate-type https://schemas.conda.org/attestations-publish-1.schema.json \
  --format json
```

The verified statement's `predicate.targetChannel` must be `https://conda.anaconda.org/jezdez`. Merely finding a JSON file with that field is not signature verification. Attestations bind artifact bytes to workflow identity and source claims. They do not prove the package is bug-free.

## Future releases

Future releases use the normal pipeline without version-specific recovery branches. Publishing refuses existing release assets or Anaconda versions instead of replacing them. A failed upload can leave a partial release, so inspect which artifacts already exist before retrying. Never move an already published tag as routine recovery.

Workflow bundles are retained as Actions artifacts and attached to the GitHub release before it becomes public. This keeps verification instructions independent of Actions artifact retention periods.

Keep releases as drafts until every package and bundle is attached. Publishing the draft locks its assets and tag. Correct a published package with a new version rather than attempting to replace an immutable asset. The `0.1.0` recovery occurred before immutability was enabled and is not a template for future releases.
