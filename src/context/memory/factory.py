from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class MemoryStore(Protocol):
    def get(self, key: str) -> str | None:
        ...

    def set(self, key: str, value: str) -> None:
        ...


@dataclass
class InMemoryStore:
    _data: dict[str, str] = field(default_factory=dict)

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value


def create_memory_store(kind: str = "in_memory") -> MemoryStore:
    if kind == "in_memory":
        return InMemoryStore()
    raise ValueError(f"Unsupported memory store kind: {kind}")
