"""Shared feature selection and confirmed configuration writes."""

import sys
from pathlib import Path

from conda import CondaError
from conda.base.context import context
from conda.common.configuration import YamlRawParameter

from ..models import Catalog, Feature
from ..operations.configuration import apply_change
from ..operations.dependencies import guard_plan, projected_context, verify_guard
from ..operations.settings import fingerprint
from .targets import target


def select_feature(catalog: Catalog, name: str) -> Feature:
    if name not in catalog:
        raise CondaError(f"Unknown feature: {name}")
    return catalog[name][1]


def confirm_and_apply(args, catalog, ctx, plan):
    guard_plan(args, catalog, plan)
    result = {
        key: plan[key]
        for key in (
            "operation",
            "features",
            "scope",
            "path",
            "changes",
            "checked_environments",
            "discovery",
            "remove",
        )
        if key in plan
    }
    if args.dry_run:
        result["message"] = "Preview only. No changes made."
    elif not plan["changes"]:
        result["message"] = "No changes needed."
    else:
        if not context.always_yes:
            if context.json or not sys.stdin.isatty():
                raise CondaError(
                    "Review with --dry-run, then pass --yes to apply noninteractively."
                )
            print(f"Configuration: {plan['path']} ({plan['scope']})", file=sys.stderr)
            if plan["checked_environments"]:
                print(
                    "Checked environments: " + ", ".join(plan["checked_environments"]),
                    file=sys.stderr,
                )
            print(plan["discovery"], file=sys.stderr)
            for key, new_value in plan["changes"].items():
                print(f"  {key} = {new_value}", file=sys.stderr)
            print("Proceed? [y/N] ", end="", file=sys.stderr, flush=True)
            if sys.stdin.readline().strip().lower() not in ("y", "yes"):
                raise CondaError("Cancelled. No changes made.")
        verify_guard(plan)
        if "plans" in plan:
            current = ctx
            expected = plan["fingerprint"]
            for child in plan["plans"]:
                if fingerprint(Path(child["path"])) != expected:
                    raise CondaError(
                        "Configuration changed after preview. Review the plan again."
                    )
                child["fingerprint"] = expected
                next_context = projected_context(child, current)
                catalog[child["features"][-1]][1].apply(child, current)
                expected = fingerprint(Path(child["path"]))
                current = next_context
        elif len(plan["features"]) == 1:
            catalog[plan["features"][0]][1].apply(plan, ctx)
        else:
            apply_change(plan, ctx)
        YamlRawParameter.cache_clear()
        _, _, updated = target(args)
        result["status"] = [
            catalog[name][1].status(
                catalog, updated, plan["scope"], path=Path(plan["path"])
            )
            for name in plan["features"]
        ]
        result["message"] = (
            "Configuration updated. Takes effect in the next conda invocation."
        )
    return result
