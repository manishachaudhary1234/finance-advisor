from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class PromptRepository(Protocol):
    def get(self, name: str) -> str:
        ...


@dataclass
class FilePromptRepository:
    base_dir: Path

    def get(self, name: str) -> str:
        prompt_path = self.base_dir / f"{name}.txt"
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")


def create_prompt_repository(kind: str = "file", base_dir: str | Path = "src/context/prompts/templates") -> PromptRepository:
    if kind == "file":
        return FilePromptRepository(base_dir=Path(base_dir))
    raise ValueError(f"Unsupported prompt repository kind: {kind}")
