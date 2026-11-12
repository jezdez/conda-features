"""Preview and disable one feature or all features at a scope."""


def configure_parser(parser):
    parser.add_argument("feature", nargs="?")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Disable all declared features at this scope.",
    )


def execute(args, catalog, ctx, path, scope):
    from ..operations.configuration import plan_change
    from .common import confirm_and_apply, select_feature

    if args.all:
        deployments = [
            name
            for name, (_, feature) in catalog.items()
            if feature.enabled_setting is None and scope in feature.scopes
        ]
        boolean_catalog = {
            name: item
            for name, item in catalog.items()
            if item[1].enabled_setting is not None
        }
        plan = plan_change(
            boolean_catalog,
            ctx,
            path,
            scope,
            "disable",
            args.feature,
            all_features=True,
        )
    else:
        plan = select_feature(catalog, args.feature).disable(catalog, ctx, path, scope)
    result = confirm_and_apply(args, catalog, ctx, plan)
    if args.all and deployments:
        result["message"] += (
            " Disable deployment features individually: " + ", ".join(deployments) + "."
        )
    return result
