from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ToolInputModel(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)


class ToolOutputModel(BaseModel):
    success: bool
    message: str = Field(..., min_length=1, max_length=1000)


PdfDocumentType = Literal["auto", "bank_statement", "portfolio_statement"]
NormalizedRecordType = Literal["transaction", "holding", "summary", "unknown"]


class PdfIngestionInput(ToolInputModel):
    file_path: str = Field(..., min_length=3, max_length=500)
    document_type: PdfDocumentType = "auto"
    password: str | None = Field(default=None, min_length=1, max_length=128)
    max_pages: int = Field(default=30, ge=1, le=300)


class NormalizedPdfRecord(BaseModel):
    record_type: NormalizedRecordType
    data: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0, le=1)


class PdfIngestionOutput(ToolOutputModel):
    document_type_detected: PdfDocumentType = "auto"
    pages_processed: int = Field(default=0, ge=0, le=300)
    text_preview: str = Field(default="", max_length=20000)
    records: list[NormalizedPdfRecord] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
