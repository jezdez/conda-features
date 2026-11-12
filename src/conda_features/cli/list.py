"""List installed feature declarations and their state."""


def configure_parser(parser):
    pass


def execute(args, catalog, ctx, path, scope):
    return {
        "features": [
            feature.status(catalog, ctx, scope, path=path)
            for _, feature in catalog.values()
        ]
    }
