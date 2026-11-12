"""Preview and disable one feature or all features at a scope."""

from .common import confirm_and_apply, select_feature


def configure_parser(parser):
    parser.add_argument("feature", nargs="?")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Disable all declared features at this scope.",
    )


def execute(args, catalog, ctx, path, scope):
    from ..operations.configuration import plan_change

    if args.all:
        plan = plan_change(
            catalog, ctx, path, scope, "disable", args.feature, all_features=True
        )
    else:
        plan = select_feature(catalog, args.feature).disable(catalog, ctx, path, scope)
    return confirm_and_apply(args, catalog, ctx, plan)
