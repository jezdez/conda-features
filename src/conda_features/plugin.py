"""Register the command without loading providers or configuration operations."""

from argparse import ArgumentParser, Namespace

from conda.plugins import hookimpl
from conda.plugins.types import CondaSubcommand


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
