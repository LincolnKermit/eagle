from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Literal, Optional

import httpx

InputType = Literal["email", "username", "phone", "domain", "bssid", "person"]


@dataclass
class Finding:
    label: str
    value: str
    url: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Result:
    source: str
    target: str
    found: bool
    findings: list[Finding] = field(default_factory=list)
    error: Optional[str] = None
    elapsed_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "found": self.found,
            "findings": [asdict(f) for f in self.findings],
            "error": self.error,
            "elapsed_ms": self.elapsed_ms,
        }


class Source(ABC):
    name: str = ""
    description: str = ""
    input_types: tuple[InputType, ...] = ()

    @abstractmethod
    async def lookup(self, target: str, client: httpx.AsyncClient) -> Result:
        ...
