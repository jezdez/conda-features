"""Resolve configuration destinations using conda contexts."""

from argparse import Namespace
from pathlib import Path

from conda import CondaError
from conda.base.context import Context, context, user_rc_path
from conda.common.configuration import CONDARC_FILENAMES, YAML_EXTENSIONS


def target(args: Namespace) -> tuple[Path, str, Context]:
    if args.file:
        path = Path(args.file).expanduser().absolute()
        if path.name not in CONDARC_FILENAMES and path.suffix not in YAML_EXTENSIONS:
            raise CondaError(
                "Configuration filename must be .condarc, condarc, or have a YAML extension."
            )
        return path, "user", Context(search_path=(path,))
    if args.prefix:
        prefix = Path(args.prefix).expanduser().absolute()
        if not (prefix / "conda-meta").is_dir():
            raise CondaError("The target prefix must be an existing conda environment.")
        path, scope = prefix / ".condarc", "environment"
    elif args.system:
        path, scope = Path(context.root_prefix) / ".condarc", "system"
    else:
        path, scope = Path(user_rc_path).expanduser().absolute(), "user"
    return path, scope, Context(argparse_args=args)
