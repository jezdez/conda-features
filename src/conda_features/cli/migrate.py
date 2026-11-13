"""Preview migration to a provider-declared replacement."""

from __future__ import annotations


def configure_parser(parser):
    parser.add_argument("feature")


def execute(args, catalog, ctx, path, scope):
    from .common import confirm_and_apply, select_feature

    feature = select_feature(catalog, args.feature)
    return confirm_and_apply(
        args, catalog, ctx, feature.migrate(catalog, ctx, path, scope)
    )
