"""Ownership and recovery for provider-generated blocks in user files."""

from abc import abstractmethod

from conda import CondaError

from ..operations.settings import fingerprint
from .base import Step, StepPlan
from .storage import write_text


class ManagedBlock(Step):
    @abstractmethod
    def target(self, ctx):
        """Resolve the file and provider-specific options without writes."""

    @abstractmethod
    def blocks(self, content):
        """Return complete managed blocks in the file."""

    @abstractmethod
    def has_marker(self, content):
        """Recognize existing or incomplete installations that must be preserved."""

    @abstractmethod
    def render(self, options):
        """Prepare provider data and return the exact block before installing it."""

    @abstractmethod
    def install(self, options):
        """Invoke the provider's installation operation."""

    def plan(self, ctx, path, operation, saved):
        target, options = self.target(ctx)
        stamp = fingerprint(target)
        content = target.read_text() if target.exists() else ""
        blocks = self.blocks(content)
        if saved and (saved["target"] != str(target) or saved["options"] != options):
            raise CondaError(
                "Shell destination changed. Restore the saved selection before disabling."
            )
        if not saved and self.has_marker(content):
            raise CondaError("A pre-existing hook was found. It will be preserved.")
        if saved and blocks and blocks != [saved.get("block")]:
            raise CondaError(
                "Owned hook changed since deployment. User edits are preserved."
            )
        if operation == "disable" and not saved:
            return StepPlan()
        change = (
            f"{operation} hook in {target}"
            if operation == "disable" or not blocks or self.check(ctx, path)
            else None
        )
        return StepPlan(
            change,
            {
                "target": target,
                "options": options,
                "operation": operation,
                "fingerprint": stamp,
            },
            saved or {"target": str(target), "options": options},
        )

    def apply(self, plan, ctx, checkpoint):
        if not plan.change:
            return
        target = plan.data["target"]
        resolved, options = self.target(ctx)
        if (
            resolved != target
            or options != plan.data["options"]
            or fingerprint(target) != plan.data["fingerprint"]
        ):
            raise CondaError("Shell destination changed after preview.")
        if plan.data["operation"] == "enable":
            block = self.render(options)
            if fingerprint(target) != plan.data["fingerprint"]:
                raise CondaError("Shell file changed during setup.")
            if plan.state.get("block") and plan.state["block"] != block:
                raise CondaError(
                    "Generated hook differs from the saved deployment. Disable before upgrading."
                )
            checkpoint({**plan.state, "block": block})
            self.install(options)
            if self.blocks(target.read_text()) != [block]:
                raise CondaError(
                    "Provider did not install the expected hook. Receipt retained."
                )
        elif target.exists():
            content = target.read_text()
            blocks = self.blocks(content)
            if not blocks:
                return
            if blocks != [plan.state.get("block")]:
                raise CondaError("Owned hook changed. User edits are preserved.")
            write_text(target, content.replace(plan.state["block"], "", 1))
