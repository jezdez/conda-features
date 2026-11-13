"""Apply a portable intent document to an explicitly selected destination."""

from __future__ import annotations

import json
from pathlib import Path


def configure_parser(parser):
    parser.add_argument("manifest", type=Path)


def execute(args, catalog, ctx, path, scope):
    from ..operations.intent import IntentError, plan_intent
    from .common import confirm_and_apply

    if not (args.user or args.system or args.prefix or args.file):
        raise IntentError(
            "Applying intent requires an explicit --user, --system, --prefix, or --file destination."
        )
    try:
        document = json.loads(args.manifest.read_text())
    except (OSError, ValueError) as exc:
        raise IntentError("Cannot read feature intent JSON.") from exc
    plan = plan_intent(document, catalog, ctx, path, scope)
    return confirm_and_apply(args, catalog, ctx, plan)
