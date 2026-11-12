"""Read conda settings and construct prospective configuration contexts."""

from __future__ import annotations

import hashlib
import os
from copy import copy
from pathlib import Path
from typing import Any

from conda import CondaError
from conda.base.constants import SEARCH_PATH
from conda.base.context import Context
from conda.common.configuration import YamlRawParameter, custom_expandvars
from conda.common.serialize import yaml


def setting_context(ctx: Context, key: str):
    if key.startswith("plugins."):
        return ctx.plugins, key.removeprefix("plugins.")
    return ctx, key


def value(ctx: Context, key: str) -> Any:
    config, name = setting_context(ctx, key)
    return getattr(config, name)


def prospective_context(ctx: Context, path: Path, content: dict) -> Context:
    # Replace this source in place so conda still handles precedence and !final.
    raw = YamlRawParameter.make_raw_parameters(path, yaml.loads(yaml.dumps(content)))
    data = {}
    inserted = False
    # Conda omits nonexistent files from raw_data. Recover their position from
    # its search templates instead of giving a new user file highest priority.
    source_order = []
    for template in SEARCH_PATH:
        expanded = Path(
            custom_expandvars(
                template,
                os.environ,
                CONDA_ROOT=ctx.root_prefix,
                CONDA_PREFIX=ctx.target_prefix,
            )
        ).expanduser()
        if expanded == path:
            source_order.append(path)
        else:
            source_order.extend(ctx._expand_search_path((expanded,)))
    later_sources = (
        set(source_order[source_order.index(path) + 1 :])
        if path in source_order
        else set()
    )
    for source, parameters in ctx.raw_data.items():
        if str(source) == str(path):
            data[path] = raw
            inserted = True
        else:
            if not inserted and (
                source in later_sources or str(source) in ("envvars", "cmd_line")
            ):
                data[path] = raw
                inserted = True
            data[source] = {
                key: copy(parameter) for key, parameter in parameters.items()
            }
    if not inserted:
        data[path] = raw
    result = Context(search_path=())
    result.raw_data.clear()
    result.raw_data.update(data)
    return result


def fingerprint(path: Path) -> str | None:
    if path.is_symlink():
        raise CondaError("Refusing to replace a symbolic-link configuration file.")
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
