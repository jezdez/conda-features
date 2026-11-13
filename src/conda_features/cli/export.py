"""Export portable choices as one versioned JSON document."""

from __future__ import annotations


def configure_parser(parser):
    parser.add_argument(
        "features",
        nargs="*",
        help="Feature IDs to export. Defaults to all saved choices at this scope.",
    )


def execute(args, catalog, ctx, path, scope):
    from .common import select_feature

    names = args.features or list(catalog)
    entries = [
        select_feature(catalog, name).export_intent(catalog, ctx, path, scope)
        for name in names
    ]
    return {
        "version": 1,
        "scope": scope,
        "features": [entry for entry in entries if entry is not None],
    }
