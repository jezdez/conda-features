"""Human-readable and JSON command output."""

import json

from conda.base.context import context


def render(result: dict) -> None:
    if context.json or (
        result.get("version") == 1 and "features" in result and "scope" in result
    ):
        print(json.dumps(result, default=str))
    elif "problems" in result:
        for problem in result["problems"]:
            print(f"{problem['feature']}: {problem['message']} {problem['action']}")
        if not result["problems"]:
            print("No local feature readiness problems found.")
        print(result["message"])
    elif "feature" in result:
        if "values" in result:
            for key, item in result["values"].items():
                print(f"{key}: {json.dumps(item, default=str)}")
        elif "sources" in result:
            for source, values in result["sources"].items():
                print(f"==> {source} <==")
                for key, item in values.items():
                    print(f"{key}: {json.dumps(item, default=str)}")
        elif "descriptions" in result:
            for key, description in result["descriptions"].items():
                print(f"{key} ({', '.join(description['element_types'])})")
                print(
                    f"  Default: {json.dumps(description['default_value'], default=str)}"
                )
                print(f"  {description['description']}")
        else:
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
        if result.get("lifecycle") not in (None, "available"):
            print(f"Lifecycle: {result['lifecycle']}")
        if result.get("replacement"):
            print(
                f"Replacement: {result['replacement']}. Use feature migrate to preview the change."
            )
        if result.get("graduation") == "unconditional":
            print(
                "Functionality is now unconditional. Cleanup removes only the obsolete opt-in, not the functionality."
            )
        for key, sources in result["sources"].items():
            print(f"{key}: sources {', '.join(sources) or 'default'}")
        for reason in result["reasons"]:
            print(reason)
        if result["settings"]:
            print("Configurable settings: " + ", ".join(result["settings"]))
        if result["guidance"]:
            print(result["guidance"])
