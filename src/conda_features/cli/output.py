"""Human-readable and JSON command output."""

import json

from conda.base.context import context


def render(result: dict) -> None:
    if context.json:
        print(json.dumps(result, default=str))
    elif "problems" in result:
        for problem in result["problems"]:
            print(f"{problem['feature']}: {problem['message']} {problem['action']}")
        if not result["problems"]:
            print("No local feature readiness problems found.")
        print(result["message"])
    elif "changes" in result:
        print(f"Configuration: {result['path']} ({result['scope']})")
        if "checked_environments" in result:
            print(
                "Checked environments: "
                + (", ".join(result["checked_environments"]) or "none")
            )
            print(result["discovery"])
        for key, new_value in result["changes"].items():
            print(f"  {key} = {new_value}")
        print(result["message"])
    elif isinstance(result.get("features"), list):
        if not result["features"]:
            print("No feature providers installed.")
        else:
            print(
                "Feature  Maturity  Requested  Effective setting  Readiness  Description"
            )
            for feature in result["features"]:
                print(
                    "  ".join(
                        str(feature[key])
                        for key in (
                            "name",
                            "maturity",
                            "requested",
                            "effective",
                            "readiness",
                            "description",
                        )
                    )
                )
    else:
        print(f"{result['name']}: {result['description']}")
        for key in ("provider", "maturity", "requested", "readiness"):
            print(f"{key.capitalize()}: {result[key]}")
        print(f"Effective setting: {result['effective']}")
        print("Runtime: unknown (provider execution is not observed)")
        for key, sources in result["sources"].items():
            print(f"{key}: sources {', '.join(sources) or 'default'}")
        for reason in result["reasons"]:
            print(reason)
        if result["settings"]:
            print("Configurable settings: " + ", ".join(result["settings"]))
        if result["guidance"]:
            print(result["guidance"])
