from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class MemoryConfig:
    backend: str = "in_memory"
    profiles_db_path: str = "data/profiles.db"
    events_db_path: str = "data/events.db"


@dataclass
class PromptConfig:
    backend: str = "file"
    base_dir: str = "src/context/prompts/templates"


@dataclass
class LoggingConfig:
    name: str = "finance-advisor"
    level: str = "INFO"
    file_path: str | None = "data/logs/app.log"


@dataclass
class OrchestratorConfig:
    enabled: bool = True
    strategy: str = "default"


@dataclass
class AppConfig:
    memory: MemoryConfig
    prompts: PromptConfig
    logging: LoggingConfig
    orchestrator: OrchestratorConfig


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError("config.yml must contain a top-level mapping")
    return data


def load_config(path: str | Path = "config.yml") -> AppConfig:
    data = _load_yaml(Path(path))

    context = data.get("context", {})
    observability = data.get("observability", {})
    agents = data.get("agents", {})

    memory_data = context.get("memory", {})
    prompt_data = context.get("prompts", {})
    logging_data = observability.get("logging", {})
    orchestrator_data = agents.get("orchestrator", {})

    return AppConfig(
        memory=MemoryConfig(
            backend=memory_data.get("backend", "in_memory"),
            profiles_db_path=memory_data.get("profiles_db_path", "data/profiles.db"),
            events_db_path=memory_data.get("events_db_path", "data/events.db"),
        ),
        prompts=PromptConfig(
            backend=prompt_data.get("backend", "file"),
            base_dir=prompt_data.get("base_dir", "src/context/prompts/templates"),
        ),
        logging=LoggingConfig(
            name=logging_data.get("name", "finance-advisor"),
            level=logging_data.get("level", "INFO"),
            file_path=logging_data.get("file_path", "data/logs/app.log"),
        ),
        orchestrator=OrchestratorConfig(
            enabled=orchestrator_data.get("enabled", True),
            strategy=orchestrator_data.get("strategy", "default"),
        ),
    )
