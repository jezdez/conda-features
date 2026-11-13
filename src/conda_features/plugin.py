"""Register the command without loading providers or configuration operations."""

from argparse import ArgumentParser, Namespace

from conda.plugins import hookimpl
from conda.plugins.types import CondaHealthCheck, CondaSubcommand


def configure_parser(parser: ArgumentParser) -> None:
    from .cli.parser import configure_parser as configure

    configure(parser)


def run(args: Namespace) -> int:
    from .cli.commands import execute

    return execute(args)


@hookimpl
def conda_subcommands():
    yield CondaSubcommand(
        name="feature",
        summary="Discover and configure features from installed providers.",
        action=run,
        configure_parser=configure_parser,
    )


def check_features(prefix: str, verbose: bool) -> None:
    from .operations.doctor import health_check

    health_check(prefix, verbose)


def fix_features(prefix, args, confirm):
    from .operations.doctor import fix

    return fix(prefix, args, confirm)


@hookimpl
def conda_health_checks():
    yield CondaHealthCheck(
        name="features",
        action=check_features,
        fixer=fix_features,
        summary="Inspect local feature readiness and deployment receipts",
        fix="Preview and retry saved feature setup",
    )
