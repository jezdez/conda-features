"""Owned scalar settings and channel additions using conda configuration APIs."""

import json
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from hashlib import sha256
from typing import Any

from conda import CondaError
from conda.cli.condarc import ConfigurationFile
from conda.common.configuration import YamlRawParameter

from ..operations.configuration import prospective_context, value
from .base import Step, StepPlan
from .storage import write_configuration


@dataclass(frozen=True)
class SetSetting(Step):
    key: str
    value: Any

    @property
    def id(self):
        return f"setting:{self.key}"

    def check(self, ctx, path):
        target = self.normalized_value(ctx)
        return (
            []
            if self.scalar(value(ctx, self.key)) == target
            else [f"Set {self.key} to {target}."]
        )

    def normalized_value(self, ctx):
        config = ConfigurationFile(content={}, context=ctx)
        config.set_key(self.key, self.value)
        return self.scalar(config.get_key(self.key)[1])

    @staticmethod
    def scalar(value: Any) -> Any:
        return value.value if isinstance(value, Enum) else value

    def plan(self, ctx, path, operation, saved):
        config = ConfigurationFile(path=path, context=ctx)
        owner, _, subkey = self.key.partition(".")
        content = config.content.get(owner, {}) if subkey else config.content
        key = subkey or owner
        current = {"present": key in content, "value": content.get(key)}
        if operation == "enable":
            target = self.normalized_value(ctx)
            needs_change = self.scalar(value(ctx, self.key)) != target
            if saved and saved.get("target") != target:
                raise CondaError(
                    f"Step {self.id} changed. Disable its old deployment first."
                )
            if saved and saved.get("owned"):
                expected = {"present": True, "value": target}
                if current != expected and (
                    saved.get("completed") or current != saved["before"]
                ):
                    raise CondaError(
                        f"Setting {self.key} changed since deployment. User edits are preserved."
                    )
            elif saved and needs_change:
                raise CondaError(
                    f"Existing receipt does not own {self.key}. Disable before taking ownership."
                )
            state = saved or {
                "owned": needs_change,
                "before": current,
                "target": target,
            }
            config.set_key(self.key, target)
            candidate = prospective_context(ctx, path, config.content)
            if self.scalar(value(candidate, self.key)) != target:
                raise CondaError(
                    f"Setting {self.key} is overridden. Change the override before enabling."
                )
            change = f"set {self.key} to {target}" if needs_change else None
        else:
            state = saved or {}
            if not state.get("owned"):
                return StepPlan(state=state)
            expected = {"present": True, "value": state["target"]}
            if current != expected:
                if current == state["before"]:
                    return StepPlan(state=state)
                raise CondaError(
                    f"Setting {self.key} changed since deployment. User edits are preserved."
                )
            change = f"restore previous {self.key}"
        return StepPlan(
            change, {"path": path, "operation": operation, "current": current}, state
        )

    def apply(self, plan, ctx, checkpoint):
        if not plan.change:
            return
        config = ConfigurationFile(path=plan.data["path"], context=ctx)
        self.update_config(config, plan)
        write_configuration(plan.data["path"], config.content, ctx)
        YamlRawParameter.cache_clear()

    def update_config(self, config: ConfigurationFile, plan: StepPlan) -> None:
        """Apply the approved setting to an in-memory prospective configuration."""
        if not plan.change:
            return
        owner, _, subkey = self.key.partition(".")
        content = config.content.setdefault(owner, {}) if subkey else config.content
        key = subkey or owner
        if {"present": key in content, "value": content.get(key)} != plan.data[
            "current"
        ]:
            raise CondaError(f"Setting {self.key} changed after preview.")
        if plan.data["operation"] == "enable":
            config.set_key(self.key, plan.state["target"])
        elif plan.state["before"]["present"]:
            content[key] = plan.state["before"]["value"]
        else:
            content.pop(key, None)


@dataclass(frozen=True)
class EnsureChannel(Step):
    channel: str

    @property
    def id(self):
        return f"channel:{self.channel}"

    def check(self, ctx, path):
        return [] if self.channel in ctx.channels else [f"Add channel {self.channel}."]

    @staticmethod
    def channels_digest(channels) -> str:
        return sha256(
            json.dumps(list(channels), ensure_ascii=True).encode()
        ).hexdigest()

    def plan(self, ctx, path, operation, saved):
        config = ConfigurationFile(path=path, context=ctx)
        current = deepcopy(config.content.get("channels"))
        if operation == "enable":
            if saved and saved.get("completed") and self.check(ctx, path):
                raise CondaError(
                    f"Channel {self.channel} changed since deployment. User edits are preserved."
                )
            if saved and not saved.get("owned") and self.check(ctx, path):
                raise CondaError(
                    "Existing receipt does not own this channel. Disable before taking ownership."
                )
            state = saved or {
                "owned": bool(self.check(ctx, path)),
                "created_list": current is None,
                "seeded_digest": self.channels_digest(ctx.channels)
                if current is None
                else None,
            }
            if not self.check(ctx, path):
                return StepPlan(state=state)
            if current is None:
                for channel in ctx.channels:
                    config.add("channels", channel)
            config.add("channels", self.channel)
            if self.check(prospective_context(ctx, path, config.content), path):
                raise CondaError(
                    "Channel configuration is overridden. Remove the override before enabling."
                )
            change = f"append {self.channel} (preserve existing channels)"
        else:
            state = saved or {}
            if not state.get("owned") or not current or self.channel not in current:
                return StepPlan(state=state)
            change = f"remove owned channel {self.channel}"
        return StepPlan(
            change,
            {
                "path": path,
                "operation": operation,
                "current": current,
                "channels": config.content.get("channels"),
            },
            state,
        )

    def apply(self, plan, ctx, checkpoint):
        if not plan.change:
            return
        config = ConfigurationFile(path=plan.data["path"], context=ctx)
        self.update_config(config, plan)
        write_configuration(plan.data["path"], config.content, ctx)
        YamlRawParameter.cache_clear()

    def update_config(self, config: ConfigurationFile, plan: StepPlan) -> None:
        """Project the channel edit without storing unrelated channel values."""
        if not plan.change:
            return
        if config.content.get("channels") != plan.data["current"]:
            raise CondaError("Channels changed after preview.")
        if plan.data["operation"] == "enable":
            config.content["channels"] = plan.data["channels"]
        else:
            remaining = [
                item for item in config.content["channels"] if item != self.channel
            ]
            if (
                plan.state["created_list"]
                and self.channels_digest(remaining) == plan.state["seeded_digest"]
            ):
                config.content.pop("channels")
            else:
                config.content["channels"] = remaining
