from __future__ import annotations

import io
import json
import re
from pathlib import Path

import pytest
from rich.console import Console

from conda_features.cli.output import render


def test_list_output_uses_table_without_interpreting_provider_markup():
    stream = io.StringIO()
    console = Console(
        file=stream,
        force_terminal=True,
        width=140,
        color_system="standard",
        no_color=False,
    )
    render(
        {
            "features": [
                {
                    "name": "[red]literal[/red]",
                    "description": "escape\x1b[2J",
                    "maturity": "preview",
                    "requested": "disabled",
                    "effective": "disabled",
                    "readiness": "ready",
                }
            ]
        },
        console=console,
    )
    output = stream.getvalue()
    assert "[red]literal[/red]" in output
    assert "escape\\x1b[2J" in output
    assert "\x1b[2J" not in output
    assert "\x1b[1;36m" in output


def test_redirected_output_has_no_ansi_sequences():
    stream = io.StringIO()
    console = Console(file=stream, force_terminal=False, width=100)
    render(
        {
            "changes": {"plugins.limit": 4},
            "path": "/tmp/test.yaml",
            "scope": "user",
            "message": "Preview only. No changes made.",
        },
        console=console,
    )
    assert "\x1b" not in stream.getvalue()
    assert "Preview only" in stream.getvalue()


def test_json_bypasses_rich_without_changing_values(conda_cli, monkeypatch, capsys):
    from conda.base.context import context

    monkeypatch.setattr(
        type(context), "json", property(lambda self: True), raising=False
    )
    stream = io.StringIO()
    result = {"features": [], "literal": "[red]\x1b[2J"}
    render(result, console=Console(file=stream, force_terminal=True))
    assert stream.getvalue() == ""
    assert json.loads(capsys.readouterr().out) == result


def test_no_color_is_respected(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    stream = io.StringIO()
    console = Console(file=stream, force_terminal=True, width=100)
    render(
        {
            "changes": {},
            "path": "demo.yaml",
            "scope": "user",
            "message": "Preview only. No changes made.",
        },
        console=console,
    )
    assert "\x1b[33m" not in stream.getvalue()
    assert "\x1b[1;33m" not in stream.getvalue()


def test_completed_plan_is_not_labeled_as_pending():
    stream = io.StringIO()
    render(
        {
            "changes": {"offline": True},
            "status": [],
            "path": "demo.yaml",
            "scope": "user",
            "message": "Configuration updated.",
        },
        console=Console(file=stream, force_terminal=False),
    )
    assert "Changed offline" in stream.getvalue()
    assert "Would change" not in stream.getvalue()


@pytest.mark.parametrize("width", [40, 80])
def test_narrow_table_retains_full_feature_ids_and_states(width):
    stream = io.StringIO()
    render(
        {
            "features": [
                {
                    "name": "conda-completion",
                    "description": "Shell completion",
                    "maturity": "preview",
                    "requested": "disabled",
                    "effective": "disabled",
                    "readiness": "setup required",
                }
            ]
        },
        console=Console(file=stream, force_terminal=False, width=width),
    )
    output = stream.getvalue()
    assert "…" not in output
    assert "conda-completion" in output.replace("\n", "").replace(" ", "")
    assert "disabled" in output.replace("\n", "").replace(" ", "")


def test_error_renders_untrusted_text_only_on_stderr(capsys):
    from conda_features.cli.output import render_error

    render_error("[red]literal[/red]\r\x1b[2J")
    out, err = capsys.readouterr()
    assert out == ""
    assert "[red]literal[/red]\\x0d\\x1b[2J" in err
    assert "\r" not in err and "\x1b[2J" not in err


def test_confirmation_retains_all_changes_and_escapes_controls():
    from conda_features.cli.output import render_plan

    stream = io.StringIO()
    changes = {f"setting{index}": "[red]value[/red]\r\x1b[2J" for index in range(8)}
    render_plan(
        {
            "changes": changes,
            "path": str(Path.home() / "demo/.condarc"),
            "scope": "user",
        },
        Console(file=stream, force_terminal=True, width=40, soft_wrap=True),
    )
    output = re.sub(r"\x1b\[[0-9;]*m", "", stream.getvalue())
    assert str(Path("~") / "demo/.condarc") in output
    for key in changes:
        assert key in output
    assert output.count("[red]value[/red]\\x0d\\x1b[2J") == 8
    assert "\r" not in output and "\x1b[2J" not in output
