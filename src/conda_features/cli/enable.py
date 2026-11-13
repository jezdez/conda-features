"""Preview and enable an installed feature."""


def configure_parser(parser):
    parser.add_argument("feature")
    parser.add_argument(
        "--with-dependencies",
        action="store_true",
        help="Preview prerequisite opt-ins at the selected scope.",
    )


def execute(args, catalog, ctx, path, scope):
    from .common import confirm_and_apply, select_feature

    feature = select_feature(catalog, args.feature)
    plan = (
        feature.enable(catalog, ctx, path, scope, with_dependencies=True)
        if args.with_dependencies
        else feature.enable(catalog, ctx, path, scope)
    )
    return confirm_and_apply(args, catalog, ctx, plan)
