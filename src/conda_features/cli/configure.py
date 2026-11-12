"""Validate and change a feature's declared settings."""

from conda import CondaError


def configure_parser(parser):
    parser.add_argument("feature")
    parser.add_argument("settings", nargs="+", metavar="KEY=VALUE")


def execute(args, catalog, ctx, path, scope):
    from .common import confirm_and_apply, select_feature

    feature = select_feature(catalog, args.feature)
    settings = {}
    for item in args.settings:
        key, separator, new_value = item.partition("=")
        if not separator or not key or key in settings:
            raise CondaError("Provide distinct declared settings as KEY=VALUE.")
        settings[key] = new_value
    plan = feature.configure(catalog, ctx, path, scope, settings)
    return confirm_and_apply(args, catalog, ctx, plan)
