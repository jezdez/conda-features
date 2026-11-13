"""Rich terminal output with conda-workspaces' blue, cyan, and yellow palette."""

from __future__ import annotations

import json
import re
from pathlib import Path

from conda.base.context import context
from rich.console import Console
from rich.table import Table
from rich.text import Text


def text(value: object, style: str = "") -> Text:
    """Keep provider markup literal and terminal controls visible."""
    value = re.sub(
        r"[\x00-\x1f\x7f-\x9f]", lambda match: f"\\x{ord(match[0]):02x}", str(value)
    )
    return Text(value, style=style)


def state_style(value: str) -> str:
    if value in ("enabled", "ready"):
        return "bold cyan"
    if value in ("blocked", "setup required", "preview", "experimental"):
        return "bold yellow"
    return "dim"


def display_path(value: str) -> str:
    path = Path(value)
    try:
        return str(Path("~") / path.relative_to(Path.home()))
    except ValueError:
        return value


def render_error(message: str) -> None:
    Console(stderr=True, highlight=False, soft_wrap=True).print(
        Text.assemble(("Error: ", "bold red"), text(message))
    )


def render_plan(result: dict, console: Console) -> None:
    console.print(
        Text.assemble(
            ("Configuration: ", "bold"),
            text(display_path(result["path"])),
            text(f" ({result['scope']})", "dim"),
        )
    )
    if "checked_environments" in result:
        console.print(
            text(
                "Checked environments: "
                + (", ".join(result["checked_environments"]) or "none"),
                "dim",
            )
        )
        console.print(text(result["discovery"], "dim"))
    for key, value in result["changes"].items():
        console.print(
            Text.assemble(
                ("  Changed ", "bold cyan")
                if "status" in result
                else ("  Would change ", "bold yellow"),
                text(key, "bold"),
                text(f" = {value}"),
            )
        )


def render(result: dict, *, console: Console | None = None) -> None:
    if context.json:
        print(json.dumps(result, default=str))
        return
    console = console or Console(highlight=False, soft_wrap=True)
    if "problems" in result:
        for problem in result["problems"]:
            console.print(
                Text.assemble(
                    text(problem["feature"], "bold yellow"),
                    ": ",
                    text(problem["message"]),
                )
            )
            console.print(
                Text.assemble(("Hint: ", "bold cyan"), text(problem["action"]))
            )
        if not result["problems"]:
            console.print(
                text("No local feature readiness problems found.", "bold cyan")
            )
        console.print(text(result["message"], "dim"))
    elif "feature" in result:
        if "values" in result:
            for key, item in result["values"].items():
                console.print(
                    Text.assemble(
                        text(key, "bold"), ": ", text(json.dumps(item, default=str))
                    )
                )
        elif "sources" in result:
            for source, values in result["sources"].items():
                console.print(text(f"==> {display_path(source)} <==", "bold cyan"))
                for key, item in values.items():
                    console.print(
                        Text.assemble(
                            text(key, "bold"), ": ", text(json.dumps(item, default=str))
                        )
                    )
        elif "descriptions" in result:
            for key, description in result["descriptions"].items():
                console.print(
                    Text.assemble(
                        text(key, "bold"),
                        text(f" ({', '.join(description['element_types'])})", "dim"),
                    )
                )
                console.print(
                    text(
                        f"  Default: {json.dumps(description['default_value'], default=str)}",
                        "dim",
                    )
                )
                console.print(text(description["description"]))
        else:
            console.print(text(result["message"], "bold cyan"))
    elif "changes" in result:
        render_plan(result, console)
        console.print(
            text(
                result["message"],
                "bold yellow" if "Preview only" in result["message"] else "bold cyan",
            )
        )
    elif isinstance(result.get("features"), list):
        if not result["features"]:
            console.print(text("No feature providers installed.", "dim"))
        else:
            if console.width < 100:
                for feature in result["features"]:
                    console.print(text(feature["name"], "bold"), soft_wrap=True)
                    for key in ("maturity", "requested", "effective", "readiness"):
                        console.print(
                            Text.assemble(
                                f"  {key}: ",
                                text(feature[key], state_style(feature[key])),
                            ),
                            soft_wrap=True,
                        )
                    console.print(text(feature["description"], "dim"), soft_wrap=True)
                return
            table = Table(show_edge=False, pad_edge=False, box=None, expand=False)
            for heading in (
                "Feature",
                "Maturity",
                "Requested",
                "Effective setting",
                "Readiness",
                "Description",
            ):
                table.add_column(heading, header_style="bold blue", overflow="fold")
            for feature in result["features"]:
                table.add_row(
                    text(feature["name"], "bold"),
                    *(
                        text(feature[key], state_style(feature[key]))
                        for key in ("maturity", "requested", "effective", "readiness")
                    ),
                    text(feature["description"], "dim"),
                )
            console.print(table)
    else:
        console.print(
            Text.assemble(
                text(result["name"], "bold"), ": ", text(result["description"])
            )
        )
        for key in ("provider", "maturity", "requested", "readiness"):
            console.print(
                Text.assemble(
                    f"{key.capitalize()}: ", text(result[key], state_style(result[key]))
                )
            )
        console.print(
            Text.assemble(
                "Effective setting: ",
                text(result["effective"], state_style(result["effective"])),
            )
        )
        console.print(
            text("Runtime: unknown (provider execution is not observed)", "dim")
        )
        if result.get("lifecycle") not in (None, "available"):
            console.print(text(f"Lifecycle: {result['lifecycle']}", "bold yellow"))
        if result.get("replacement"):
            console.print(
                text(
                    f"Replacement: {result['replacement']}. Use feature migrate to preview the change.",
                    "bold cyan",
                )
            )
        if result.get("graduation") == "unconditional":
            console.print(
                text(
                    "Functionality is now unconditional. Cleanup removes only the obsolete opt-in, not the functionality.",
                    "bold yellow",
                )
            )
        for key, sources in result["sources"].items():
            console.print(
                text(
                    f"{key}: sources {', '.join(display_path(source) for source in sources) or 'default'}",
                    "dim",
                )
            )
        for reason in result["reasons"]:
            console.print(text(reason, "bold yellow"))
        if result["settings"]:
            console.print(
                text("Configurable settings: " + ", ".join(result["settings"]))
            )
        if result["guidance"]:
            console.print(text(result["guidance"], "bold cyan"))
