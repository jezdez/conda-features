"""Preview and execute one conda package transaction."""

import sys
from contextlib import redirect_stdout
from dataclasses import dataclass

from conda import CondaError
from conda.base.constants import UpdateModifier
from conda.base.context import context
from conda.core.prefix_data import PrefixData
from conda.models.channel import Channel
from conda.models.match_spec import MatchSpec

from .base import Step, StepPlan


def missing_packages(specs):
    PrefixData._cache_.clear()
    records = tuple(PrefixData(sys.prefix).iter_records())
    return [
        spec
        for spec in specs
        if not any(MatchSpec(spec).match(record) for record in records)
    ]


def installed_records():
    PrefixData._cache_.clear()
    return sorted(
        (record.name, record.version, record.build)
        for record in PrefixData(sys.prefix).iter_records()
    )


@dataclass(frozen=True, init=False)
class InstallPackages(Step):
    specs: tuple[str, ...]

    def __init__(self, *specs: str):
        if not specs:
            raise ValueError("InstallPackages requires package specifications")
        for spec in specs:
            MatchSpec(spec)
        object.__setattr__(self, "specs", specs)

    @property
    def id(self):
        return "packages:" + ",".join(self.specs)

    def check(self, ctx, path):
        return [
            f"Install required package: {spec}" for spec in missing_packages(self.specs)
        ]

    def plan(self, ctx, path, operation, saved):
        if operation == "disable":
            return StepPlan(state=saved or {})
        missing = missing_packages(self.specs)
        if not missing:
            return StepPlan(state=saved or {})
        installed = installed_records()
        with redirect_stdout(sys.stderr):
            runtime = [
                MatchSpec(f"{name}=={version}={build}")
                for name, version, build in installed
                if name in ("conda", "python")
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
        return StepPlan(
            change={
                "prefix": sys.prefix,
                "LINK": [
                    {
                        "name": record.name,
                        "version": record.version,
                        "build": record.build,
                        "channel": "conda-forge",
                    }
                    for record in setup.link_precs
                ],
            },
            data={"transaction": transaction, "installed": installed},
        )

    def apply(self, plan, ctx, checkpoint):
        if not plan.change:
            return
        if installed_records() != plan.data["installed"]:
            raise CondaError(
                "Installed packages changed after preview. Review the plan again."
            )
        with redirect_stdout(sys.stderr):
            plan.data["transaction"].download_and_extract()
            plan.data["transaction"].execute()
        PrefixData._cache_.clear()
