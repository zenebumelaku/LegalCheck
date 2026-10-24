from dataclasses import dataclass
from io import BytesIO
from typing import List
from zipfile import BadZipFile, ZipFile

import fitz
from docx import Document as DocxDocument
from docx.opc.exceptions import PackageNotFoundError


class UnsupportedDocumentError(ValueError):
    pass


class CorruptedDocumentError(ValueError):
    pass


class EncryptedDocumentError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedParagraph:
    paragraph_number: int
    text: str


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int
    paragraphs: List[ExtractedParagraph]


@dataclass(frozen=True)
class ExtractionResult:
    pages: List[ExtractedPage]
    warnings: List[str]
    extracted_characters: int


def _extract_pdf(content: bytes) -> ExtractionResult:
    try:
        document = fitz.open(stream=content, filetype="pdf")
    except (fitz.FileDataError, RuntimeError, ValueError) as exc:
        raise CorruptedDocumentError("The PDF file is corrupted or invalid.") from exc

    try:
        if document.needs_pass:
            raise EncryptedDocumentError("Password-protected PDF files are not supported.")
        if document.page_count == 0:
            raise CorruptedDocumentError("The PDF file contains no pages.")

        pages: List[ExtractedPage] = []
        total_characters = 0
        for page_index, page in enumerate(document, start=1):
            blocks = page.get_text("blocks", sort=True)
            paragraphs: List[ExtractedParagraph] = []
            for paragraph_number, block in enumerate(blocks, start=1):
                text = block[4].strip()
                if text:
                    paragraphs.append(
                        ExtractedParagraph(
                            paragraph_number=paragraph_number,
                            text=text,
                        )
                    )
                    total_characters += len(text)
            pages.append(ExtractedPage(page_number=page_index, paragraphs=paragraphs))

        warnings = (
            ["This PDF appears to be scanned or contains very little extractable text; OCR is not enabled."]
            if total_characters < 20
            else []
        )
        return ExtractionResult(
            pages=pages,
            warnings=warnings,
            extracted_characters=total_characters,
        )
    finally:
        document.close()


def _validate_docx_package(content: bytes, max_uncompressed_bytes: int) -> None:
    try:
        with ZipFile(BytesIO(content)) as archive:
            names = set(archive.namelist())
            if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                raise UnsupportedDocumentError("The file is not a valid DOCX document.")
            if len(names) > 2000 or sum(info.file_size for info in archive.infolist()) > max_uncompressed_bytes:
                raise UnsupportedDocumentError("The DOCX document exceeds safe processing limits.")
            if archive.testzip() is not None:
                raise CorruptedDocumentError("The DOCX file is corrupted.")
    except BadZipFile as exc:
        raise CorruptedDocumentError("The DOCX file is corrupted or invalid.") from exc


def _extract_docx(content: bytes, max_uncompressed_bytes: int) -> ExtractionResult:
    _validate_docx_package(content, max_uncompressed_bytes)
    try:
        document = DocxDocument(BytesIO(content))
    except (PackageNotFoundError, ValueError, KeyError, OSError) as exc:
        raise CorruptedDocumentError("The DOCX file is corrupted or invalid.") from exc

    paragraphs: List[ExtractedParagraph] = []
    total_characters = 0
    for paragraph_number, paragraph in enumerate(document.paragraphs, start=1):
        text = paragraph.text.strip()
        if text:
            paragraphs.append(
                ExtractedParagraph(paragraph_number=paragraph_number, text=text)
            )
            total_characters += len(text)

    return ExtractionResult(
        pages=[ExtractedPage(page_number=1, paragraphs=paragraphs)],
        warnings=[],
        extracted_characters=total_characters,
    )


def extract_document(
    content: bytes,
    document_type: str,
    max_docx_uncompressed_bytes: int,
) -> ExtractionResult:
    if document_type == "pdf":
        return _extract_pdf(content)
    if document_type == "docx":
        return _extract_docx(content, max_docx_uncompressed_bytes)
    raise UnsupportedDocumentError("Only PDF and DOCX files are supported.")
