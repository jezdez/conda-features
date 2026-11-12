"""Atomic deployment receipts and configuration writes."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from conda import CondaError


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
