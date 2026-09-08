from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DemoNetwork:
    """In-memory consequence surface used only to demonstrate technical non-completability."""
    effects: dict[str, dict[str, Any]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.lock = threading.RLock()

    def apply(self, effect: dict[str, Any]) -> str:
        effect_id = f"net-effect-{uuid.uuid4().hex[:10]}"
        self.effects[effect_id] = effect
        return effect_id
