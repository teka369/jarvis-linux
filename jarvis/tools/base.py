from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..core.permissions import Capability


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    capabilities: list[Capability]
    handler: Callable[[dict[str, Any], Any], str]
    confirm_param: str | None = None
    schema_required: list[str] = field(default_factory=list)

    def openai_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
