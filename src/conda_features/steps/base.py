"""The small interface implemented by deployment steps."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from conda.base.context import Context


@dataclass
class StepPlan:
    """Public change description, private apply data, and durable recovery state."""

    change: Any = None
    data: dict = field(default_factory=dict)
    state: dict = field(default_factory=dict)


class Step(ABC):
    @property
    @abstractmethod
    def id(self) -> str:
        """Stable receipt key. Changing it requires disabling the old deployment."""

    @abstractmethod
    def check(self, ctx: Context, path: Path | None) -> list[str]:
        """Return unmet prerequisites without network access or writes."""

    @abstractmethod
    def plan(
        self, ctx: Context, path: Path, operation: str, saved: dict | None
    ) -> StepPlan:
        """Inspect state and describe changes without mutating managed resources."""

    @abstractmethod
    def apply(
        self, plan: StepPlan, ctx: Context, checkpoint: Callable[[dict], None]
    ) -> None:
        """Apply the approved plan, checkpointing ownership before mutation."""
