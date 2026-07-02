from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from src.tools.schemas.tool_definitions import (
    NormalizedPdfRecord,
    PdfDocumentType,
    PdfIngestionInput,
    PdfIngestionOutput,
)


def _detect_document_type(text: str, requested: PdfDocumentType) -> PdfDocumentType:
    if requested != "auto":
        return requested

    low = text.lower()
    bank_signals = ["debit", "credit", "ifsc", "statement period", "account number"]
    portfolio_signals = ["isin", "folio", "units", "nav", "holdings", "portfolio"]

    bank_score = sum(1 for token in bank_signals if token in low)
    portfolio_score = sum(1 for token in portfolio_signals if token in low)

    if bank_score == 0 and portfolio_score == 0:
        return "auto"
    if bank_score >= portfolio_score:
        return "bank_statement"
    return "portfolio_statement"


def parse_pdf_statement(payload: PdfIngestionInput) -> PdfIngestionOutput:
    path = Path(payload.file_path)
    if not path.exists() or not path.is_file():
        return PdfIngestionOutput(
            success=False,
            message="PDF file does not exist or is not a file",
            warnings=[f"path={payload.file_path}"],
        )

    try:
        reader = PdfReader(str(path), password=payload.password)
    except Exception as exc:
        return PdfIngestionOutput(
            success=False,
            message="Unable to open PDF",
            warnings=[str(exc)],
        )

    pages = reader.pages[: payload.max_pages]
    extracted_chunks: list[str] = []

    for page in pages:
        try:
            extracted_chunks.append(page.extract_text() or "")
        except Exception:
            extracted_chunks.append("")

    full_text = "\n".join(extracted_chunks).strip()
    doc_type = _detect_document_type(full_text, payload.document_type)
    preview = full_text[:20000]

    records: list[NormalizedPdfRecord] = []
    if full_text:
        records.append(
            NormalizedPdfRecord(
                record_type="summary",
                data={
                    "source_file": path.name,
                    "characters_extracted": len(full_text),
                },
                confidence=0.5,
            )
        )

    warnings: list[str] = []
    if not full_text:
        warnings.append("No extractable text found. The PDF may be scanned/image-only.")

    return PdfIngestionOutput(
        success=True,
        message="PDF ingestion completed",
        document_type_detected=doc_type,
        pages_processed=len(pages),
        text_preview=preview,
        records=records,
        warnings=warnings,
    )
