from __future__ import annotations

from src.ingestion.parsers.pdf_parser import parse_pdf_statement
from src.tools.registry import ToolDefinition
from src.tools.schemas.tool_definitions import PdfIngestionInput, PdfIngestionOutput


PDF_INGESTION_TOOL = ToolDefinition(
    name="pdf_ingestion",
    description=(
        "Parse PDF bank statements or portfolio statements and return normalized records, "
        "text preview, and ingestion diagnostics."
    ),
    input_model=PdfIngestionInput,
    output_model=PdfIngestionOutput,
    handler=parse_pdf_statement,
)
