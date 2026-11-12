"""Explain a feature's configured state and prerequisites."""

from .common import select_feature


def configure_parser(parser):
    parser.add_argument("feature")


def execute(args, catalog, ctx, path, scope):
    return select_feature(catalog, args.feature).status(catalog, ctx, scope, path=path)
