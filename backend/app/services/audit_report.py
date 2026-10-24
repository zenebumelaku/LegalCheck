from collections import Counter
from html import escape
from io import BytesIO
from pathlib import Path
from typing import Iterable, Optional
from uuid import uuid4

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFError, TTFont
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Audit, Document, Finding
from app.schemas.audits import (
    AuditReportCitation,
    AuditReportDocument,
    AuditReportFinding,
    AuditReportResponse,
    AuditReportSummary,
    AuditReviewOptions,
)
from app.schemas.compliance_analysis import AnalysisLimitations

_DISCLAIMERS = [
    "This AI-assisted review is not a certified legal opinion or legal advice.",
    (
        "Have a qualified Ethiopian legal professional review this report "
        "before making consequential employment or legal decisions."
    ),
    (
        "Analysis reflects the saved audit result and cited source versions at "
        "the time of review; it is not refreshed when this report is downloaded."
    ),
    (
        "A finding's severity is a review priority, not a determination of "
        "legal liability. Unverified evidence and extraction warnings require "
        "independent review."
    ),
]
_ETHIOPIC_RANGES = ((0x1200, 0x137F), (0x1380, 0x139F), (0x2D80, 0x2DDF))


class AuditReportUnavailable(ValueError):
    pass


class UnicodeReportFontUnavailable(ValueError):
    pass


def build_audit_report(db: Session, audit: Audit) -> AuditReportResponse:
    if audit.completed_at is None:
        raise AuditReportUnavailable("The audit does not have a completion record.")
    document = db.get(Document, audit.document_id)
    if document is None:
        raise AuditReportUnavailable("The audit document metadata is unavailable.")

    findings = db.scalars(
        select(Finding)
        .where(Finding.audit_id == audit.id)
        .order_by(Finding.created_at, Finding.id)
    ).all()
    report_findings: list[AuditReportFinding] = []
    finding_types: Counter[str] = Counter()
    severities: Counter[str] = Counter()

    for finding in findings:
        finding_type = finding.finding_type.split(":", 1)[0]
        finding_types[finding_type] += 1
        severities[finding.severity] += 1
        citations: list[AuditReportCitation] = []
        for citation in finding.citations:
            provision = citation.legal_provision
            source = provision.legal_source if provision is not None else None
            if provision is None or source is None:
                raise AuditReportUnavailable(
                    "A saved finding citation is unavailable."
                )
            citations.append(
                AuditReportCitation(
                    source_id=source.id,
                    provision_id=provision.id,
                    source_title=(
                        citation.source_title_snapshot
                        if citation.source_title_snapshot is not None
                        else source.title
                    ),
                    source_version=(
                        citation.source_version_snapshot
                        if citation.source_version_snapshot is not None
                        else source.version_label
                    ),
                    source_url=(
                        citation.source_url_snapshot
                        if citation.source_url_snapshot is not None
                        else source.original_source_url
                    ),
                    article_number=(
                        citation.article_number_snapshot
                        if citation.article_number_snapshot is not None
                        else provision.article_number
                    ),
                    sub_article_reference=(
                        citation.sub_article_reference_snapshot
                        if citation.sub_article_reference_snapshot is not None
                        else provision.sub_article_reference
                    ),
                    provision_text=(
                        citation.provision_text_snapshot
                        if citation.provision_text_snapshot is not None
                        else provision.text
                    ),
                    supporting_quote=citation.supporting_quote,
                    relevance_information=citation.relevance_information,
                )
            )
        report_findings.append(
            AuditReportFinding(
                id=finding.id,
                finding_type=finding_type,
                severity=finding.severity,
                clause_excerpt=finding.clause_text,
                explanation=finding.explanation,
                recommended_next_steps=finding.recommended_action,
                evidence_status=finding.evidence_status,
                citations=citations,
                created_at=finding.created_at,
            )
        )

    warnings = list(audit.processing_warnings or [])
    limitations = _DISCLAIMERS.copy()
    if warnings:
        limitations.append(
            "Extraction or processing warnings are listed below and may affect "
            "the completeness of the review."
        )
    if any(finding.evidence_status != "supported" for finding in findings):
        limitations.append(
            "One or more findings have unverified or insufficient supporting evidence."
        )
    if document.deleted_at is not None:
        limitations.append(
            "The original file has been deleted; this report uses retained audit "
            "results and document metadata."
        )

    return AuditReportResponse(
        audit_id=audit.id,
        audit_created_at=audit.created_at,
        audit_completed_at=audit.completed_at,
        document=AuditReportDocument(
            id=document.id,
            original_filename=document.original_filename,
            content_type=document.content_type,
            document_type=document.document_type,
            file_size=document.file_size,
            detected_language=document.detected_language,
            created_at=document.created_at,
        ),
        review_scope=AuditReviewOptions.model_validate(audit.review_options or {}),
        analysis_version=audit.analysis_version,
        model_identifier=audit.model_identifier,
        summary=AuditReportSummary(
            finding_count=len(report_findings),
            severity_counts=dict(sorted(severities.items())),
            finding_type_counts=dict(sorted(finding_types.items())),
        ),
        findings=report_findings,
        processing_warnings=warnings,
        limitations=AnalysisLimitations(items=limitations),
    )


def _report_strings(value: object) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _report_strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _report_strings(nested)


def _has_ethiopic_characters(texts: Iterable[str]) -> bool:
    return any(
        start <= ord(character) <= end
        for value in texts
        for character in value
        for start, end in _ETHIOPIC_RANGES
    )


def _get_pdf_font(report: AuditReportResponse, font_path: Optional[Path]) -> str:
    texts = list(_report_strings(report.model_dump(mode="json")))
    requires_unicode_font = False
    for value in texts:
        try:
            value.encode("cp1252")
        except UnicodeEncodeError:
            requires_unicode_font = True
            break

    if font_path is None:
        if requires_unicode_font:
            raise UnicodeReportFontUnavailable(
                "This report contains characters outside the built-in PDF font "
                "encoding. Configure REPORT_UNICODE_FONT_PATH with a Unicode "
                "TrueType font that supports the report's scripts."
            )
        return "Helvetica"

    if not font_path.is_file() or font_path.suffix.lower() != ".ttf":
        raise UnicodeReportFontUnavailable(
            "REPORT_UNICODE_FONT_PATH must point to a readable TrueType .ttf font."
        )
    font_name = f"LegalCheckUnicode{uuid4().hex}"
    try:
        font = TTFont(font_name, str(font_path))
    except (OSError, TTFError) as exc:
        raise UnicodeReportFontUnavailable(
            "The configured report font could not be loaded."
        ) from exc
    required_characters = {
        ord(character)
        for value in texts
        for character in value
        if not character.isspace()
    }
    available_characters = font.face.charWidths
    if not required_characters.issubset(available_characters):
        if _has_ethiopic_characters(texts):
            message = (
                "The configured report font does not include the Ethiopic "
                "characters used in this report."
            )
        else:
            message = (
                "The configured report font does not include every character "
                "used in this report."
            )
        raise UnicodeReportFontUnavailable(message)
    try:
        pdfmetrics.registerFont(font)
    except (TTFError, ValueError) as exc:
        raise UnicodeReportFontUnavailable(
            "The configured report font could not be registered."
        ) from exc
    return font_name


def _paragraph(text: Optional[str], style: ParagraphStyle) -> Paragraph:
    safe_text = escape(text or "").replace("\n", "<br/>")
    return Paragraph(safe_text or "—", style)


def render_audit_report_pdf(
    report: AuditReportResponse,
    *,
    font_path: Optional[Path] = None,
) -> bytes:
    font_name = _get_pdf_font(report, font_path)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "AuditReportTitle",
        parent=styles["Title"],
        fontName=font_name,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17324D"),
        spaceAfter=14,
    )
    heading_style = ParagraphStyle(
        "AuditReportHeading",
        parent=styles["Heading2"],
        fontName=font_name,
        textColor=colors.HexColor("#17324D"),
        spaceBefore=12,
        spaceAfter=6,
    )
    subheading_style = ParagraphStyle(
        "AuditReportSubheading",
        parent=styles["Heading3"],
        fontName=font_name,
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "AuditReportBody",
        parent=styles["BodyText"],
        fontName=font_name,
        leading=14,
        spaceAfter=5,
        wordWrap="CJK",
    )
    muted_style = ParagraphStyle(
        "AuditReportMuted",
        parent=body_style,
        textColor=colors.HexColor("#4B5563"),
        fontSize=8,
    )

    content = BytesIO()
    pdf = SimpleDocTemplate(
        content,
        pagesize=letter,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.7 * inch,
        title=f"LegalCheck audit report {report.audit_id}",
        author="LegalCheck Ethiopia",
    )
    story: list[Flowable] = [
        _paragraph("AI-Assisted Employment Contract Review", title_style),
        _paragraph(f"Audit ID: {report.audit_id}", body_style),
        _paragraph(
            f"Audit created: {report.audit_created_at.isoformat()}",
            body_style,
        ),
        _paragraph(
            f"Audit completed: {report.audit_completed_at.isoformat()}",
            body_style,
        ),
        _paragraph("Document", heading_style),
        _paragraph(f"Filename: {report.document.original_filename}", body_style),
        _paragraph(f"Document ID: {report.document.id}", body_style),
        _paragraph(f"Type: {report.document.document_type or 'Unknown'}", body_style),
        _paragraph(f"Content type: {report.document.content_type}", body_style),
        _paragraph(f"Size: {report.document.file_size} bytes", body_style),
        _paragraph(
            f"Detected language: {report.document.detected_language or 'Unknown'}",
            body_style,
        ),
        _paragraph("Review scope", heading_style),
        _paragraph(
            report.review_scope.model_dump_json(exclude_none=True),
            body_style,
        ),
        _paragraph("Summary", heading_style),
        _paragraph(
            f"Findings: {report.summary.finding_count}; severity counts: "
            f"{report.summary.severity_counts}; finding types: "
            f"{report.summary.finding_type_counts}",
            body_style,
        ),
        _paragraph("Limitations and disclaimer", heading_style),
    ]
    for limitation in report.limitations.items:
        story.append(_paragraph(f"• {limitation}", body_style))
    story.append(_paragraph(report.limitations.disclaimer, body_style))
    if report.processing_warnings:
        story.append(_paragraph("Extraction and processing warnings", heading_style))
        for warning in report.processing_warnings:
            story.append(_paragraph(f"• {warning}", body_style))

    story.append(_paragraph("Findings", heading_style))
    if not report.findings:
        story.append(_paragraph("No findings were saved for this audit.", body_style))
    for number, finding in enumerate(report.findings, start=1):
        story.extend(
            [
                Spacer(1, 5),
                _paragraph(
                    f"{number}. {finding.finding_type} — {finding.severity}",
                    subheading_style,
                ),
                _paragraph(
                    f"Evidence status: {finding.evidence_status}",
                    muted_style,
                ),
                _paragraph("Original contract excerpt:", body_style),
                _paragraph(finding.clause_excerpt, body_style),
                _paragraph("Explanation:", body_style),
                _paragraph(finding.explanation, body_style),
                _paragraph("Recommended next steps:", body_style),
                _paragraph(finding.recommended_next_steps, body_style),
            ]
        )
        if not finding.citations:
            story.append(
                _paragraph(
                    "No supporting legal citation was saved for this finding.",
                    muted_style,
                )
            )
        for citation in finding.citations:
            article_reference = citation.article_number
            if citation.sub_article_reference:
                article_reference += f" ({citation.sub_article_reference})"
            story.extend(
                [
                    _paragraph(
                        f"Supporting provision: {citation.source_title}, "
                        f"{article_reference}",
                        body_style,
                    ),
                    _paragraph(
                        f"Version: {citation.source_version or 'Not specified'}",
                        body_style,
                    ),
                    _paragraph(
                        f"Original source URL: {citation.source_url or 'Not recorded'}",
                        body_style,
                    ),
                ]
            )
            if citation.supporting_quote:
                story.extend(
                    [
                        _paragraph("Supporting quotation:", body_style),
                        _paragraph(citation.supporting_quote, body_style),
                    ]
                )
            story.extend(
                [
                    _paragraph("Saved legal provision text:", body_style),
                    _paragraph(citation.provision_text, body_style),
                ]
            )
    footer = (
        f"LegalCheck Ethiopia · Audit {report.audit_id} · "
        "AI-assisted; professional review required"
    )

    def draw_footer(canvas, _document) -> None:
        canvas.saveState()
        canvas.setFont(font_name, 7)
        canvas.setFillColor(colors.HexColor("#4B5563"))
        canvas.drawString(0.7 * inch, 0.38 * inch, footer)
        canvas.drawRightString(7.8 * inch, 0.38 * inch, str(canvas.getPageNumber()))
        canvas.restoreState()

    pdf.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return content.getvalue()
