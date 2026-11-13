"""Local feature diagnostics without solving packages or changing resources."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from conda import CondaError
from conda.base.context import Context

from ..steps import runner
from ..steps.storage import read_receipt

if TYPE_CHECKING:
    from ..models import Catalog


def diagnose(catalog: Catalog, ctx: Context, path: Path, scope: str) -> dict[str, Any]:
    problems = []
    for name, (_, feature) in catalog.items():
        try:
            status = feature.status(catalog, ctx, None, path=path)
            selected = (
                status["requested"] == "enabled" or status["effective"] == "enabled"
            )
            if (
                feature.enabled_setting
                and status["requested"] == "enabled"
                and status["effective"] != "enabled"
            ):
                sources = status["sources"].get(feature.enabled_setting, [])
                problems.append(
                    {
                        "feature": name,
                        "kind": "overridden",
                        "message": "Saved opt-in is overridden. Configuration sources: "
                        + ", ".join(sources),
                        "action": "Change or remove the overriding value before retrying. Use feature explain for details.",
                    }
                )
            elif selected and status["readiness"] != "ready":
                problems.append(
                    {
                        "feature": name,
                        "kind": "not-ready",
                        "message": " ".join(status["reasons"]),
                        "action": f"Run conda feature repair {name} --dry-run at this scope.",
                    }
                )
            elif feature.steps:
                _, saved = runner.load(feature, path)
                if saved and any(
                    not saved["steps"].get(step.id, {}).get("completed")
                    for step in feature.steps
                ):
                    problems.append(
                        {
                            "feature": name,
                            "kind": "incomplete",
                            "message": "Deployment receipt contains unfinished steps.",
                            "action": f"Run conda feature repair {name} --dry-run at this scope.",
                        }
                    )
        except (CondaError, OSError, ValueError) as exc:
            problems.append(
                {
                    "feature": name,
                    "kind": "inspection-error",
                    "message": str(exc),
                    "action": "Restore the provider version that wrote the receipt before retrying.",
                }
            )
    if path.parent.exists():
        for receipt in path.parent.glob(path.name + ".*.json"):
            name = receipt.name[len(path.name) + 1 : -5]
            if name in catalog or not re.fullmatch(r"[a-z][a-z0-9_-]*", name):
                continue
            try:
                saved = read_receipt(receipt)
                if (
                    isinstance(saved, dict)
                    and saved.get("version") == 2
                    and isinstance(saved.get("steps"), dict)
                    and all(
                        isinstance(state, dict) for state in saved["steps"].values()
                    )
                ):
                    problems.append(
                        {
                            "feature": name,
                            "kind": "missing-provider",
                            "message": "Reinstall the feature provider before repairing or disabling its deployment.",
                            "action": "Preserve this deployment receipt. Do not guess how to remove its resources.",
                        }
                    )
                else:
                    raise CondaError("Unsupported deployment receipt")
            except (CondaError, OSError, ValueError):
                problems.append(
                    {
                        "feature": name,
                        "kind": "invalid-receipt",
                        "message": "Cannot inspect deployment receipt safely.",
                        "action": "Inspect the receipt locally and restore a supported provider version.",
                    }
                )
    return {
        "path": str(path),
        "scope": scope,
        "problems": problems,
        "message": "Local feature checks only. Runtime execution and authentication were not verified.",
    }
