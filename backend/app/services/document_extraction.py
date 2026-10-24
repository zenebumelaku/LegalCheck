from dataclasses import dataclass
from io import BytesIO
from typing import Iterator, List, Optional, Protocol, Union
from zipfile import BadZipFile, ZipFile
import zlib

import fitz
from docx import Document as DocxDocument
from docx.opc.exceptions import PackageNotFoundError
from docx.table import Table
from docx.text.paragraph import Paragraph
from lxml.etree import XMLSyntaxError
import defusedxml.ElementTree as _defused_et  # noqa: F401 – activates defusedxml protections

MAX_EXTRACTED_CHARACTERS = 2_000_000


class _BlockContainer(Protocol):
    def iter_inner_content(self) -> Iterator[Union[Paragraph, Table]]: ...


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
    page_number: Optional[int]
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
        if document.page_count > 1000:
            raise UnsupportedDocumentError("The PDF document contains too many pages.")

        pages: List[ExtractedPage] = []
        total_characters = 0
        for page_index, page in enumerate(document, start=1):
            try:
                blocks = page.get_text("blocks", sort=True)
            except (RuntimeError, ValueError) as exc:
                raise CorruptedDocumentError(
                    "The PDF contains a page that cannot be read."
                ) from exc
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
                    if total_characters > MAX_EXTRACTED_CHARACTERS:
                        raise UnsupportedDocumentError(
                            "The extracted PDF text exceeds safe processing limits."
                        )
            pages.append(ExtractedPage(page_number=page_index, paragraphs=paragraphs))

        warnings = (
            ["This PDF appears to be scanned or contains very little extractable text."]
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
    except (BadZipFile, NotImplementedError, RuntimeError, zlib.error, OSError) as exc:
        raise CorruptedDocumentError("The DOCX file is corrupted or invalid.") from exc


def _extract_docx(content: bytes, max_uncompressed_bytes: int) -> ExtractionResult:
    _validate_docx_package(content, max_uncompressed_bytes)
    try:
        document = DocxDocument(BytesIO(content))
    except (
        PackageNotFoundError,
        NotImplementedError,
        RuntimeError,
        ValueError,
        KeyError,
        OSError,
        XMLSyntaxError,
        zlib.error,
    ) as exc:
        raise CorruptedDocumentError("The DOCX file is corrupted or invalid.") from exc

    paragraphs: List[ExtractedParagraph] = []
    total_characters = 0
    paragraph_number = 0

    def collect_paragraphs(container: _BlockContainer) -> None:
        nonlocal paragraph_number, total_characters
        for block in container.iter_inner_content():
            if isinstance(block, Paragraph):
                paragraph_number += 1
                text = block.text.strip()
                if text:
                    paragraphs.append(
                        ExtractedParagraph(
                            paragraph_number=paragraph_number,
                            text=text,
                        )
                    )
                    total_characters += len(text)
                    if total_characters > MAX_EXTRACTED_CHARACTERS:
                        raise UnsupportedDocumentError(
                            "The extracted DOCX text exceeds safe processing limits."
                        )
            elif isinstance(block, Table):
                for row in block.rows:
                    for cell in row.cells:
                        collect_paragraphs(cell)

    try:
        collect_paragraphs(document)
    except (ValueError, KeyError, OSError, XMLSyntaxError, zlib.error) as exc:
        raise CorruptedDocumentError("The DOCX file is corrupted or invalid.") from exc

    return ExtractionResult(
        pages=[ExtractedPage(page_number=None, paragraphs=paragraphs)],
        warnings=[],
        extracted_characters=total_characters,
    )


def extract_document(
    content: bytes,
    document_type: str,
    max_docx_uncompressed_bytes: int,
    ocr_enabled: bool = False,
) -> ExtractionResult:
    if document_type == "pdf":
        result = _extract_pdf(content)
        if result.warnings:
            if ocr_enabled:
                warning = (
                    "OCR is enabled in configuration, but no OCR provider is "
                    "integrated in this deployment."
                )
            else:
                warning = "OCR is not enabled."
            return ExtractionResult(
                pages=result.pages,
                warnings=[*result.warnings, warning],
                extracted_characters=result.extracted_characters,
            )
        return result
    if document_type == "docx":
        return _extract_docx(content, max_docx_uncompressed_bytes)
    raise UnsupportedDocumentError("Only PDF and DOCX files are supported.")
