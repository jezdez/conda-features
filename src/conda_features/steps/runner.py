"""Ordered planning and recoverable execution for a feature's steps."""

import json
from pathlib import Path

from conda import CondaError
from conda.cli.condarc import ConfigurationFile
from conda.common.configuration import YamlRawParameter
from filelock import FileLock

from ..operations.settings import fingerprint, prospective_context, value
from .configuration import EnsureChannel, SetSetting
from .storage import read_receipt, receipt_path, write_receipt


def load(feature, path):
    receipt = receipt_path(path, feature.name)
    saved = read_receipt(receipt)
    if saved is not None and (
        saved.get("version") != 2 or not isinstance(saved.get("steps"), dict)
    ):
        raise CondaError(
            "Unsupported deployment receipt version. Disable it with the previous provider version before upgrading. No changes made."
        )
    if saved and set(saved["steps"]) - {step.id for step in feature.steps}:
        raise CondaError(
            "Deployment steps changed. Disable with the previous provider version first."
        )
    return receipt, saved


def plan(feature, catalog, ctx, path, scope, operation):
    if scope not in feature.scopes:
        raise CondaError(f"Unsupported scope: {scope}")
    if operation == "enable":
        missing = [
            key for key in feature.required_settings if value(ctx, key) in (None, "")
        ]
        if missing:
            raise CondaError(
                "Configure required settings before deployment: " + ", ".join(missing)
            )
        status = feature.status(catalog, ctx, scope, path=path)
        if status["readiness"] == "blocked":
            raise CondaError("Cannot enable feature: " + " ".join(status["reasons"]))
    else:
        for name, (_, other) in catalog.items():
            if (
                feature.name in other.requires
                and other.status(catalog, ctx, scope, path=path)["effective"]
                == "enabled"
            ):
                raise CondaError(
                    f"Enabled feature {name} requires {feature.name}. Disable the dependent first."
                )
    receipt, saved = load(feature, path)
    if operation == "disable" and saved is None:
        raise CondaError(
            "No deployment receipt. Pre-existing resources will be preserved."
        )
    steps = feature.steps if operation == "enable" else tuple(reversed(feature.steps))
    plans = [
        (
            step,
            step.plan(
                ctx, path, operation, saved["steps"].get(step.id) if saved else None
            ),
        )
        for step in steps
    ]
    config = ConfigurationFile(path=path, context=ctx)
    for step, item in plans:
        try:
            json.dumps(item.state, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise CondaError(
                f"Step {step.id} has non-serializable recovery state. No changes made."
            ) from exc
        if isinstance(step, (SetSetting, EnsureChannel)):
            step.update_config(config, item)
    candidate = prospective_context(ctx, path, config.content)
    candidate.validate_configuration()
    candidate.plugins.validate_configuration()
    changes = {step.id: item.change for step, item in plans if item.change is not None}
    if (operation == "enable" and saved is None) or operation == "disable":
        changes["receipt"] = (
            "record feature choice"
            if operation == "enable"
            else "remove deployment receipt"
        )
    return {
        "features": [feature.name],
        "operation": operation,
        "path": str(path),
        "scope": scope,
        "changes": changes,
        "steps": plans,
        "receipt": str(receipt),
        "saved": saved,
        "fingerprint": fingerprint(path),
        "receipt_fingerprint": fingerprint(receipt),
    }


def apply(plan, ctx):
    path, receipt = Path(plan["path"]), Path(plan["receipt"])
    with FileLock(str(path) + ".lock", timeout=5):
        if (
            fingerprint(path) != plan["fingerprint"]
            or fingerprint(receipt) != plan["receipt_fingerprint"]
        ):
            raise CondaError(
                "Configuration or receipt changed after preview. Review the plan again."
            )
        saved: dict = plan["saved"] or {"version": 2, "steps": {}}
        expected = fingerprint(path)
        for step, item in plan["steps"]:
            try:
                if fingerprint(path) != expected:
                    raise CondaError("Configuration changed during deployment.")

                def checkpoint(state):
                    saved["steps"][step.id] = dict(state)
                    write_receipt(receipt, saved)

                if plan["operation"] == "enable":
                    checkpoint(item.state)
                step.apply(item, ctx, checkpoint)
                expected = fingerprint(path)
                YamlRawParameter.cache_clear()
                if plan["operation"] == "enable":
                    checkpoint({**saved["steps"][step.id], "completed": True})
                else:
                    saved["steps"].pop(step.id, None)
                    write_receipt(receipt, saved)
            except Exception as exc:
                raise CondaError(
                    f"Step {step.id} failed: {exc}. Completed work and its receipt are retained. Retry after correcting the problem."
                ) from exc
        if plan["operation"] == "disable":
            receipt.unlink(missing_ok=True)
