"""Inspect local feature readiness and retained deployment receipts."""

from __future__ import annotations


def configure_parser(parser):
    pass


def execute(args, catalog, ctx, path, scope):
    from ..operations.diagnostics import diagnose

    return diagnose(catalog, ctx, path, scope)
