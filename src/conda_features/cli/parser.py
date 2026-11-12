"""Argument definitions for the feature subcommand."""

from argparse import ArgumentParser
from importlib import import_module


def configure_parser(parser: ArgumentParser) -> None:
    from conda.cli.helpers import add_output_and_prompt_options

    parser.description = "Manage features declared by installed providers. Deployment providers may install prerequisites after confirmation."
    parser.epilog = "Providers register a conda_features hook in the conda_features entry-point group. See help(conda_features) in Python for setup and usage."
    commands = parser.add_subparsers(dest="operation", required=True)
    for name in ("list", "explain", "enable", "disable", "configure"):
        command = commands.add_parser(name)
        add_output_and_prompt_options(command)
        scope = command.add_mutually_exclusive_group()
        scope.add_argument(
            "--user", action="store_true", help="Use user configuration (default)."
        )
        scope.add_argument(
            "--system",
            action="store_true",
            help="Use this conda installation's configuration.",
        )
        scope.add_argument(
            "-p", "--prefix", help="Target an existing conda environment."
        )
        scope.add_argument(
            "--file", help="Use an explicit user-scope configuration file."
        )
        import_module(f".{name}", package=__package__).configure_parser(command)
