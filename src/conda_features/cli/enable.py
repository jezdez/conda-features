"""Preview and enable an installed feature."""


def configure_parser(parser):
    parser.add_argument("feature")


def execute(args, catalog, ctx, path, scope):
    from .common import confirm_and_apply, select_feature

    plan = select_feature(catalog, args.feature).enable(catalog, ctx, path, scope)
    return confirm_and_apply(args, catalog, ctx, plan)
