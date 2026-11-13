"""Load the selected subcommand and render its result."""

import json
import sys
from argparse import Namespace
from importlib import import_module

from conda import CondaError
from conda.base.context import context

from ..operations.discovery import discover
from ..operations.intent import IntentError
from ..operations.validation import validate_catalog
from .output import render
from .targets import target


def execute(args: Namespace) -> int:
    try:
        catalog = discover()
        path, scope, ctx = target(args)
        validate_catalog(catalog, ctx)
        command = import_module(f".{args.operation}", package=__package__)
        result = command.execute(args, catalog, ctx, path, scope)
    except (CondaError, OSError, ValueError, TypeError, OverflowError) as exc:
        message = str(exc)
        if args.operation in ("export", "apply") and not isinstance(exc, IntentError):
            message = "Intent operation failed. Inspect the local configuration and providers. Review with --dry-run and pass --yes only after approving the changes. Configuration values are omitted from this error."
        if context.json:
            print(json.dumps({"error": message}))
        else:
            print(message, file=sys.stderr)
        return 1
    render(result)
    return 0
