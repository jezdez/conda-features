"""Deploy PyPI support using the Rattler solver and conda-pypi channel."""

from copy import deepcopy
from pathlib import Path

from conda import CondaError
from conda.cli.condarc import ConfigurationFile
from conda.common.configuration import YamlRawParameter
from filelock import FileLock

from conda_features.models import Feature
from conda_features.operations.configuration import fingerprint, prospective_context

from .deployment import (
    install_packages,
    missing_packages,
    package_plan,
    read_receipt,
    receipt_path,
    summary,
    write_receipt,
)


class PyPIFeature(Feature):
    def status(self, catalog, ctx, scope, visiting=(), *, path=None):
        enabled = ctx.solver == "rattler" and "conda-pypi" in ctx.channels
        reasons = (
            []
            if enabled
            else [
                "Enable to select the Rattler solver and append the conda-pypi channel."
            ]
        )
        reasons.extend(
            f"Install required package: {spec}"
            for spec in missing_packages(
                ("conda-pypi>=0.13", "conda-rattler-solver>=26.10")
            )
        )
        receipt = read_receipt(receipt_path(path, self.name)) if path else None
        return summary(
            self,
            catalog,
            enabled=enabled,
            reasons=reasons,
            requested="enabled" if receipt else "unset",
        )

    def enable(self, catalog, ctx, path, scope):
        if scope not in self.scopes:
            raise CondaError(f"Unsupported scope: {scope}")
        config = ConfigurationFile(path=path, context=ctx)
        before = deepcopy(config.content)
        saved = read_receipt(receipt_path(path, self.name))
        if saved and any(
            config.content.get(key)
            not in (saved["after"].get(key), saved["before"].get(key))
            for key in saved["owned"]
        ):
            raise CondaError(
                "Owned PyPI settings changed. Reconcile the receipt before enabling again."
            )
        config.set_key("solver", "rattler")
        if "conda-pypi" not in ctx.channels:
            if "channels" not in config.content:
                for channel in ctx.channels:
                    config.add("channels", channel)
            config.add("channels", "conda-pypi")
        candidate = prospective_context(ctx, path, config.content)
        if saved and any(
            key not in saved["owned"] and config.content.get(key) != before.get(key)
            for key in ("solver", "channels")
        ):
            raise CondaError(
                "PyPI deployment already has a receipt. Disable it before changing additional settings."
            )
        if candidate.solver != "rattler" or "conda-pypi" not in candidate.channels:
            raise CondaError(
                "Solver or channel configuration is overridden. Remove the override before enabling PyPI support."
            )
        packages = package_plan(("conda-pypi>=0.13", "conda-rattler-solver>=26.10"))
        receipt = receipt_path(path, self.name)
        return {
            "features": [self.name],
            "operation": "enable",
            "path": str(path),
            "scope": scope,
            "changes": {
                **({"packages": packages["actions"]} if packages["arguments"] else {}),
                **{
                    key: "append conda-pypi (preserve existing channels)"
                    if key == "channels"
                    else config.content[key]
                    for key in ("solver", "channels")
                    if config.content.get(key) != before.get(key)
                },
            },
            "packages": packages,
            "before": before,
            "after": config.content,
            "fingerprint": fingerprint(path),
            "receipt_fingerprint": fingerprint(receipt),
            "receipt": str(receipt),
        }

    def disable(self, catalog, ctx, path, scope):
        if scope not in self.scopes:
            raise CondaError(f"Unsupported scope: {scope}")
        receipt = receipt_path(path, self.name)
        saved = read_receipt(receipt)
        config = ConfigurationFile(path=path, context=ctx)
        before = deepcopy(config.content)
        if not saved:
            raise CondaError(
                "No deployment receipt. Existing solver and channel settings were not changed by this provider and will be preserved."
            )
        for key in saved["owned"]:
            if config.content.get(key) != saved["after"].get(key):
                raise CondaError(
                    f"Setting {key} changed since deployment. Preserve the user edit and disable it manually."
                )
            if key in saved["before"]:
                config.content[key] = saved["before"][key]
            else:
                config.content.pop(key, None)
        return {
            "features": [self.name],
            "operation": "disable",
            "path": str(path),
            "scope": scope,
            "changes": {"restore": saved["owned"]},
            "before": before,
            "after": config.content,
            "packages": {"arguments": [], "actions": {}},
            "fingerprint": fingerprint(path),
            "receipt_fingerprint": fingerprint(receipt),
            "receipt": str(receipt),
        }

    def configure(self, catalog, ctx, path, scope, settings):
        raise CondaError(
            "PyPI support uses solver=rattler and channel conda-pypi. Use conda config for other settings."
        )

    def apply(self, plan, ctx):
        from .deployment import write_configuration

        path, receipt = Path(plan["path"]), Path(plan["receipt"])
        with FileLock(str(path) + ".lock", timeout=5):
            if (
                fingerprint(path) != plan["fingerprint"]
                or fingerprint(receipt) != plan["receipt_fingerprint"]
            ):
                raise CondaError(
                    "Configuration or receipt changed after preview. Retry to review the new plan."
                )
            install_packages(plan["packages"])
            if fingerprint(path) != plan["fingerprint"]:
                raise CondaError(
                    "Configuration changed during package installation. Packages were retained. Review the new plan before retrying."
                )
            if plan["operation"] == "enable" and not receipt.exists():
                owned = [
                    key
                    for key in ("solver", "channels")
                    if plan["before"].get(key) != plan["after"].get(key)
                ]
                write_receipt(
                    receipt,
                    {
                        "before": {
                            key: plan["before"][key]
                            for key in owned
                            if key in plan["before"]
                        },
                        "after": {
                            key: plan["after"][key]
                            for key in owned
                            if key in plan["after"]
                        },
                        "owned": owned,
                    },
                )
            write_configuration(path, plan["after"], ctx)
            if plan["operation"] == "disable":
                receipt.unlink()
            YamlRawParameter.cache_clear()
