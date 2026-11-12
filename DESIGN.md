# Conda Feature and Configuration Management

This document describes the system architecture and design decisions for a new conda plugin dedicated to a feature and configuration management system.

## Overview

The plugin provides a structured approach to managing feature flags and configuration settings across conda environments, enabling controlled rollout of features and centralized configuration management.

## Goals

- Lower the barrier of discovery and configuration for complex features that require additional setup or plugin installations.
- Provide clear, actionable feedback to users during feature transitions.
- Preserve feature dependencies by preventing users from disabling features required by enabled features.
- Introduce a safe way to roll out new features for users and maintainers.
- Support feature deprecation and graceful migration paths.
- Provide clear guidance for users when features are retired or replaced.
- Later, allow conditional rollout based on environment context and separately consented analytics for improvement.

## Scope

- Cover multiple configuration functionalities and conda APIs.
- Focus on user interaction, not server-side feature toggles at first.
- Support optional feature rollouts for features that are part of conda or conda plugins.
- Allow features to live in plugin packages or conda itself.
- Keep conda-build out of scope for now.

## Features and Design Considerations

### Feature State and Lifecycle

- Users should be able to enable, disable, and configure features.
- Distinguish maintainer-controlled maturity (`experimental`, `preview`, `stable`), the user's enabled/disabled choice, and readiness (`ready`, `setup required`, `blocked`). Forward-only maturity progression should not prevent disabling optional features.
- Features may graduate to regular conda or plugin functionality, but some may never graduate and always stay optional, even when considered stable.
- Features may be explicitly retired or replaced with other features.
- Preserve migration choices: retain retired-feature metadata, explain replacements, preview migrations, and carry compatible settings forward. Acceptance of one feature should not imply consent to a materially different replacement.
- Explain graduation: notify users when an opt-in becomes default functionality, identify obsolete settings, and offer safe cleanup. Distinguish this from stable features that remain optional.

### Discovery and Configuration

- The system should report the status of available features.
- Distinguish feature IDs from package names, such as `pypi` and `conda-pypi`. List output should show separate columns for feature ID, maturity, requested state, readiness, and description.
- Discovery before provider installation requires metadata available outside the provider package. Start with bundled metadata for known integrations and declarations from installed providers, with stable feature IDs, provider identity, supported versions, and package sources.
- Feature discovery should not install packages, retrieve credentials, or run setup. Keep a remote catalog for later.
- Features should declare supported configuration scopes: conda installation, user, or target environment. Show where each change applies and distinguish the installation hosting a plugin from the environment receiving settings.
- Reuse conda's typed settings and configuration precedence, and explain which source determines the effective value.
- Explain effective status: `conda feature explain pypi` should show requested and effective state, configuration sources, unmet prerequisites, and the next action.

### Setup and Recovery

- Some features may require additional configuration or a server action such as login.
- Features may automatically or optionally install plugins needed for a feature as part of confirmed setup.
- Preview setup: `conda feature enable pypi --dry-run` should show package changes, channels, settings, affected scopes, and login requirements without making changes. Flag changes to conda itself explicitly.
- Validate compatibility and conflicts before mutation: check conda/provider versions, platforms, feature prerequisites, mutually exclusive features, and dependency cycles. Leave package dependency solving to conda.
- Treat partial setup as an explicit outcome. Record completed steps, make retries idempotent, and do not report a feature as ready when configuration or login failed.
- Detect configuration drift through `conda doctor`, including removed providers, changed settings, and missing prerequisites. Offer repair through the same preview and setup operations with confirmation.

### Disabling and Cleanup

- The system must allow disabling all features that remain under its control.
- Bulk disable should process dependents before prerequisites. Distinguish temporary suppression, persisted disable, and package removal. Graduated unconditional core functionality is outside this system's disable controls.
- Disabling or cleaning up a feature should preserve pre-existing channels and settings, subsequent user edits, and resources required by another feature. Do not promise to reverse server-side actions.

### Feedback and Automation

- Support friendly state-change messages so users know what changed and what to do next.
- Provide getting-started guidance or suggested next steps.
- Support automation with one complete `--json` result, documented exit statuses, and explicit noninteractive confirmation behavior. Missing authentication should fail actionably rather than wait indefinitely.
- Export and apply feature intent: transfer selected feature IDs and non-secret settings to another machine or CI with compatibility checks. This represents desired configuration, not a package lockfile or proof of successful setup.

### Privacy and Conditional Rollout

- Separate local diagnostic history from separately consented telemetry. Keep secrets out of logs, status, and exports.
- Later, allow features to be rolled out to a subset of the user base, conditional on channel, locale, timezone, customer ID, and similar context. Treat customer-based targeting as a privacy-sensitive addition.

## Integrations

- Work well with the `conda plugins` subcommand and its features, and with `conda-self`.
- Integrate with other user experience improvements such as a design system.
- Reuse conda's subcommand, settings, health-check, and reporting hooks. Verify the intended `conda plugins` and `conda-self` APIs and supported versions before implementing those integrations.

## Conceptual User Interaction

The following example is illustrative, not a claim about existing `conda-pypi` behavior. Enabling the `pypi` feature installs its provider, configures its channel, and prints usage guidance. Actual output should identify the conda installation and configuration scope being modified.

```text
$ conda feature list

Available capabilities:

Feature       Maturity  Requested  Readiness       Description
pypi          stable    disabled   setup required  Install PyPI packages with conda
cool-feature  preview   disabled   setup required  Experimental new capability

$ conda feature enable pypi

Enable PyPI package installation?

This will:
  Install the conda-pypi plugin
  Add the conda-pypi channel
  Apply required settings

Proceed? [y/N] y

Plugin installed
Channel configured
Readiness checks passed
Feature enabled

PyPI package installation is ready to use.

Getting started: conda.org/.../installing-pypi-packages
```

## Suggested Priorities

- Initial release: discover, explain, preview, enable, configure, disable, and recover, including compatibility checks and automation support.
- Next: drift detection and repair, consented migration assistance, and graduation cleanup.
- Later: export/apply of feature intent, remote catalogs, conditional rollout, telemetry, and automatic migration. Avoid a general-purpose setup workflow engine.
