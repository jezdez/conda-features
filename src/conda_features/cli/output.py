"""Human-readable and JSON command output."""

import json

from conda.base.context import context


def render(result: dict) -> None:
    if context.json:
        print(json.dumps(result, default=str))
    elif "changes" in result:
        print(f"Configuration: {result['path']} ({result['scope']})")
        for key, new_value in result["changes"].items():
            print(f"  {key} = {new_value}")
        print(result["message"])
    elif isinstance(result.get("features"), list):
        if not result["features"]:
            print("No feature providers installed.")
        else:
            print("Feature  Maturity  Requested  Readiness  Description")
            for feature in result["features"]:
                print(
                    "  ".join(
                        str(feature[key])
                        for key in (
                            "name",
                            "maturity",
                            "requested",
                            "readiness",
                            "description",
                        )
                    )
                )
    else:
        print(f"{result['name']}: {result['description']}")
        for key in ("provider", "maturity", "requested", "effective", "readiness"):
            print(f"{key.capitalize()}: {result[key]}")
        for key, sources in result["sources"].items():
            print(f"{key}: sources {', '.join(sources) or 'default'}")
        for reason in result["reasons"]:
            print(reason)
        if result["settings"]:
            print("Configurable settings: " + ", ".join(result["settings"]))
        if result["guidance"]:
            print(result["guidance"])
