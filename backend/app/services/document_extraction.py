from dataclasses import dataclass
from io import BytesIO
import logging
import math
import shutil
import subprocess
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
OCR_MAX_PAGES = 100
OCR_PAGE_TIMEOUT_SECONDS = 20
OCR_DPI = 160
OCR_MAX_PIXELS = 12_000_000
logger = logging.getLogger(__name__)


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


def _ocr_page(page: fitz.Page, executable: str) -> str:
    page_area = max(page.rect.width * page.rect.height, 1)
    scale = min(OCR_DPI / 72, math.sqrt(OCR_MAX_PIXELS / page_area))
    pixmap = page.get_pixmap(
        matrix=fitz.Matrix(scale, scale),
        alpha=False,
    )
    result = subprocess.run(
        [executable, "stdin", "stdout", "-l", "eng", "--psm", "3"],
        input=pixmap.tobytes("png"),
        capture_output=True,
        check=False,
        timeout=OCR_PAGE_TIMEOUT_SECONDS,
    )
    if result.returncode != 0:
        raise RuntimeError("The OCR process failed.")
    return result.stdout.decode("utf-8", errors="replace").strip()


def _extract_pdf(content: bytes, ocr_enabled: bool = False) -> ExtractionResult:
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
        warnings: list[str] = []
        ocr_executable = shutil.which("tesseract") if ocr_enabled else None
        ocr_unavailable_warning_added = False
        ocr_attempts = 0
        ocr_failures = 0
        ocr_empty_pages = 0
        ocr_page_limit_reached = False
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
            page_text_characters = sum(len(paragraph.text) for paragraph in paragraphs)
            if ocr_enabled and page_text_characters < 20:
                if ocr_executable is None:
                    if not ocr_unavailable_warning_added:
                        warnings.append(
                            "OCR is enabled, but the Tesseract executable is "
                            "unavailable; scanned pages were not recognized."
                        )
                        ocr_unavailable_warning_added = True
                elif not ocr_page_limit_reached:
                    if ocr_attempts >= OCR_MAX_PAGES:
                        ocr_page_limit_reached = True
                        warnings.append(
                            f"OCR stopped after {OCR_MAX_PAGES} scanned pages; "
                            "remaining pages may have no extractable text."
                        )
                    else:
                        ocr_attempts += 1
                        try:
                            recognized_text = _ocr_page(page, ocr_executable)
                        except (
                            OSError,
                            RuntimeError,
                            ValueError,
                            subprocess.TimeoutExpired,
                        ) as exc:
                            ocr_failures += 1
                            logger.warning(
                                "OCR failed for PDF page %s",
                                page_index,
                                extra={"error_type": type(exc).__name__},
                            )
                        else:
                            if recognized_text:
                                next_paragraph_number = (
                                    paragraphs[-1].paragraph_number + 1
                                    if paragraphs
                                    else 1
                                )
                                paragraphs.append(
                                    ExtractedParagraph(
                                        paragraph_number=next_paragraph_number,
                                        text=recognized_text,
                                    )
                                )
                                total_characters += len(recognized_text)
                                if total_characters > MAX_EXTRACTED_CHARACTERS:
                                    raise UnsupportedDocumentError(
                                        "The extracted PDF text exceeds safe processing limits."
                                    )
                            else:
                                ocr_empty_pages += 1
            pages.append(ExtractedPage(page_number=page_index, paragraphs=paragraphs))

        if total_characters < 20:
            warnings.append(
                "This PDF appears to be scanned or contains very little extractable text."
            )
        if not ocr_enabled and total_characters < 20:
            warnings.append("OCR is not enabled.")
        if ocr_failures:
            warnings.append(
                f"OCR could not process {ocr_failures} page(s); extracted text may be incomplete."
            )
        if ocr_empty_pages:
            warnings.append(
                f"OCR returned no text for {ocr_empty_pages} page(s); those pages may be blank or unreadable."
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
        return _extract_pdf(content, ocr_enabled)
    if document_type == "docx":
        return _extract_docx(content, max_docx_uncompressed_bytes)
    raise UnsupportedDocumentError("Only PDF and DOCX files are supported.")
