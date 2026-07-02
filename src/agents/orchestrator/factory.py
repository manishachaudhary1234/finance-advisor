from __future__ import annotations

from dataclasses import dataclass

from src.context.memory.factory import create_memory_store
from src.context.prompts.factory import create_prompt_repository
from src.observability.logging.factory import create_logger


@dataclass
class Orchestrator:
    memory_store_kind: str
    prompt_repo_kind: str
    prompt_base_dir: str
    logger_name: str
    logger_level: str
    logger_file_path: str | None

    def __post_init__(self) -> None:
        self.memory = create_memory_store(self.memory_store_kind)
        self.prompts = create_prompt_repository(
            kind=self.prompt_repo_kind,
            base_dir=self.prompt_base_dir,
        )
        self.logger = create_logger(
            name=self.logger_name,
            level=self.logger_level,
            file_path=self.logger_file_path,
        )

    def prepare_context(self, user_id: str) -> dict[str, str | None]:
        summary = self.memory.get(f"summary:{user_id}")
        system_prompt = self.prompts.get("system_prompt")
        return {
            "summary": summary,
            "system_prompt": system_prompt,
        }


def create_orchestrator(
    memory_store_kind: str = "in_memory",
    prompt_repo_kind: str = "file",
    prompt_base_dir: str = "src/context/prompts/templates",
    logger_name: str = "finance-advisor",
    logger_level: str = "INFO",
    logger_file_path: str | None = "data/logs/app.log",
) -> Orchestrator:
    return Orchestrator(
        memory_store_kind=memory_store_kind,
        prompt_repo_kind=prompt_repo_kind,
        prompt_base_dir=prompt_base_dir,
        logger_name=logger_name,
        logger_level=logger_level,
        logger_file_path=logger_file_path,
    )
