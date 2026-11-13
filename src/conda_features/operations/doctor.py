"""Conda doctor adapter. Structured output remains in feature diagnose."""

from __future__ import annotations

from argparse import Namespace
from collections.abc import Callable
from pathlib import Path

from conda import CondaError
from conda.base.context import Context, context
from conda.common.configuration import YamlRawParameter
from conda.exceptions import CondaSystemExit, DryRunExit

from .dependencies import guard_plan, verify_guard
from .diagnostics import diagnose
from .discovery import discover
from .validation import validate_catalog


def health_check(prefix: str, verbose: bool) -> None:
    catalog = discover()
    ctx = Context(argparse_args=Namespace(prefix=prefix))
    validate_catalog(catalog, ctx)
    result = diagnose(catalog, ctx, Path(prefix) / ".condarc", "environment")
    for problem in result["problems"]:
        print(f"{problem['feature']}: {problem['message']} {problem['action']}")
    if not result["problems"]:
        print("No local feature readiness problems found.")
    print(result["message"])


def fix(prefix: str, args: Namespace, confirm: Callable[[str], object]) -> int:
    catalog = discover()
    ctx = Context(argparse_args=Namespace(prefix=prefix))
    path = Path(prefix) / ".condarc"
    validate_catalog(catalog, ctx)
    problems = diagnose(catalog, ctx, path, "environment")["problems"]
    failed = False
    for problem in problems:
        name = problem["feature"]
        if name not in catalog:
            print(f"{name}: {problem['message']}")
            failed = True
            continue
        feature = catalog[name][1]
        try:
            plan = feature.repair(catalog, ctx, path, "environment")
            guard_plan(
                Namespace(prefix=prefix, file=None, check_prefix=[]), catalog, plan
            )
            print(f"Repair {name} in {path}: {plan['changes']}")
            if context.dry_run or getattr(args, "dry_run", False):
                continue
            confirm(f"Apply this repair for {name}?")
            verify_guard(plan)
            feature.apply(plan, ctx)
            YamlRawParameter.cache_clear()
            ctx = Context(argparse_args=Namespace(prefix=prefix))
        except (CondaSystemExit, DryRunExit):
            raise
        except (CondaError, OSError, ValueError) as exc:
            print(f"{name}: {exc}")
            failed = True
    return int(failed)
