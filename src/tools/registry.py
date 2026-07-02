from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any, Callable

from pydantic import BaseModel

from src.schemas.tool_calls import ToolCallRequest, ToolCallResult, ToolCallStatus


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: Callable[[BaseModel], BaseModel | dict[str, Any]]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition) -> None:
        if definition.name in self._tools:
            raise ValueError(f"Tool '{definition.name}' is already registered")
        self._tools[definition.name] = definition

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())

    def invoke(self, request: ToolCallRequest) -> ToolCallResult:
        if request.tool_name not in self._tools:
            return ToolCallResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolCallStatus.ERROR,
                error_message=f"Tool '{request.tool_name}' is not registered",
            )

        definition = self._tools[request.tool_name]
        started = perf_counter()

        try:
            validated_input = definition.input_model.model_validate(request.arguments)
            raw_output = definition.handler(validated_input)
            if isinstance(raw_output, BaseModel):
                validated_output = definition.output_model.model_validate(raw_output.model_dump())
            else:
                validated_output = definition.output_model.model_validate(raw_output)
            latency_ms = int((perf_counter() - started) * 1000)

            return ToolCallResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolCallStatus.SUCCESS,
                output=validated_output.model_dump(mode="json"),
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = int((perf_counter() - started) * 1000)
            return ToolCallResult(
                request_id=request.request_id,
                tool_name=request.tool_name,
                status=ToolCallStatus.ERROR,
                error_message=str(exc),
                latency_ms=latency_ms,
            )
