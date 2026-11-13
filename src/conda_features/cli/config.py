"""Read and change declared feature settings with conda config-style arguments."""

from __future__ import annotations

from argparse import ArgumentParser, Namespace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from conda import CondaError

if TYPE_CHECKING:
    from conda.base.context import Context

    from ..models import Catalog


def configure_parser(parser: ArgumentParser) -> None:
    parser.add_argument("feature")
    actions = parser.add_mutually_exclusive_group(required=True)
    actions.add_argument(
        "--set",
        dest="settings",
        nargs=2,
        action="append",
        metavar=("KEY", "VALUE"),
        help="Set a declared scalar setting. Repeat for multiple settings.",
    )
    for option, help_text in (
        ("get", "Read saved values from the selected file."),
        ("show", "Show effective values, including defaults and overrides."),
        ("describe", "Describe setting types and defaults using conda metadata."),
    ):
        actions.add_argument(f"--{option}", nargs="*", metavar="KEY", help=help_text)
    actions.add_argument(
        "--show-sources",
        action="store_true",
        help="Show contributing values for declared settings only.",
    )
    actions.add_argument(
        "--validate",
        action="store_true",
        help="Validate configuration and local feature requirements without writes.",
    )
    actions.add_argument(
        "--remove-key",
        action="append",
        metavar="KEY",
        help="Remove a saved override. Repeat for multiple keys.",
    )


def execute(
    args: Namespace, catalog: Catalog, ctx: Context, path: Path, scope: str
) -> dict[str, Any]:
    from .common import confirm_and_apply, select_feature

    feature = select_feature(catalog, args.feature)
    for action in ("get", "show", "describe"):
        keys = getattr(args, action)
        if keys is not None:
            return feature.config_query(catalog, ctx, path, scope, action, keys)
    if args.show_sources or args.validate:
        return feature.config_query(
            catalog,
            ctx,
            path,
            scope,
            "show-sources" if args.show_sources else "validate",
        )
    if args.remove_key:
        plan = feature.configure(
            catalog, ctx, path, scope, {}, remove_keys=tuple(args.remove_key)
        )
        return confirm_and_apply(args, catalog, ctx, plan)
    settings = {}
    for key, value in args.settings:
        if key in settings:
            raise CondaError(f"Setting {key} was supplied more than once.")
        settings[key] = value
    plan = feature.configure(catalog, ctx, path, scope, settings)
    return confirm_and_apply(args, catalog, ctx, plan)
