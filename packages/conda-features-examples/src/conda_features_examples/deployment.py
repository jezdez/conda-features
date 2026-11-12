"""Package installation and durable receipts shared by the two providers."""

import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

from conda import CondaError
from conda.base.constants import UpdateModifier
from conda.base.context import context
from conda.core.prefix_data import PrefixData
from conda.models.channel import Channel
from conda.models.match_spec import MatchSpec


def run_conda(arguments, *, env=None):
    result = subprocess.run(
        [sys.executable, "-m", "conda", *arguments],
        env=env,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    if result.returncode:
        raise CondaError(
            "Conda deployment command failed. Completed package installations are retained. "
            "Correct the problem and retry.\n"
            + (result.stderr or result.stdout).strip()
        )
    return result.stdout


def missing_packages(specs):
    records = tuple(PrefixData(sys.prefix).iter_records())
    return [
        spec
        for spec in specs
        if not any(MatchSpec(spec).match(record) for record in records)
    ]


def package_plan(specs):
    missing = missing_packages(specs)
    if not missing:
        return {"arguments": [], "actions": {}}
    with redirect_stdout(sys.stderr):
        runtime = [
            MatchSpec(f"{record.name}=={record.version}={record.build}")
            for record in PrefixData(sys.prefix).iter_records()
            if record.name in ("conda", "python")
        ]
        solver = context.plugin_manager.get_solver_backend("libmamba")(
            sys.prefix,
            channels=(Channel("https://conda.anaconda.org/conda-forge"),),
            specs_to_add=(*runtime, *(MatchSpec(spec) for spec in missing)),
        )
        transaction = solver.solve_for_transaction(
            update_modifier=UpdateModifier.FREEZE_INSTALLED
        )
    setup = transaction.prefix_setups[sys.prefix]
    if setup.unlink_precs:
        raise CondaError(
            "Provider installation would replace existing packages in the running conda installation. Install compatible prerequisites separately and retry."
        )
    return {
        "arguments": missing,
        "transaction": transaction,
        "installed": installed_records(),
        "actions": {
            "LINK": [
                {
                    "name": record.name,
                    "version": record.version,
                    "build": record.build,
                    "channel": "conda-forge",
                }
                for record in setup.link_precs
            ]
        },
    }


def installed_records():
    PrefixData._cache_.clear()
    return sorted(
        (record.name, record.version, record.build)
        for record in PrefixData(sys.prefix).iter_records()
    )


def install_packages(plan):
    if not plan["arguments"]:
        return
    if installed_records() != plan["installed"]:
        raise CondaError(
            "Installed packages changed after preview. Run enable again to review it."
        )
    with redirect_stdout(sys.stderr):
        plan["transaction"].download_and_extract()
        plan["transaction"].execute()
    PrefixData._cache_.clear()


def receipt_path(path, name):
    return Path(str(path) + f".{name}.json")


def read_receipt(path):
    if path.is_symlink():
        raise CondaError("Refusing a symbolic-link deployment receipt.")
    return json.loads(path.read_text()) if path.exists() else None


def write_receipt(path, data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, prefix=".feature-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            json.dump(data, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def write_configuration(path, content, ctx):
    from conda.cli.condarc import ConfigurationFile

    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".feature-", delete=False
        ) as stream:
            temporary = Path(stream.name)
        ConfigurationFile(content=content, context=ctx).write(temporary)
        if path.exists():
            temporary.chmod(path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def write_text(path, content):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, prefix=".feature-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        temporary.chmod(path.stat().st_mode & 0o777)
        os.replace(temporary, path)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def summary(feature, catalog, *, enabled, reasons, requested="unset"):
    return {
        "name": feature.name,
        "provider": catalog[feature.name][0],
        "description": feature.description,
        "maturity": feature.maturity,
        "requested": requested,
        "effective": "enabled" if enabled else "disabled",
        "runtime": "unknown",
        "readiness": "setup required" if reasons else "ready",
        "reasons": reasons,
        "sources": {},
        "guidance": feature.guidance,
        "settings": list(feature.settings),
    }
