import os
import sys
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import logging
from datetime import date, datetime, timezone
import uuid
import hashlib

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from sqlalchemy import select
from app.db.session import get_session_factory
from app.db.models import User, Document, LegalSource
from app.services.document_extraction import extract_document
from app.services.document_ingestion import ingest_document_to_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_demo_corpus")


def generate_remote_work_policy_pdf(target_path: Path):
    doc = SimpleDocTemplate(str(target_path), pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    h2_style = styles["Heading2"]
    body_style = styles["BodyText"]

    story = [
        Paragraph("Addis Remote Work and Teleworking Policy 2026", title_style),
        Spacer(1, 14),
        Paragraph("Section 1: Eligibility and Approval", h2_style),
        Paragraph(
            "Employees must complete a minimum of 3 months of continuous full-time service "
            "to be eligible for teleworking arrangements. All remote work requests require prior written authorization "
            "from the department director and HR compliance officer.",
            body_style,
        ),
        Spacer(1, 10),
        Paragraph("Section 2: Equipment and Information Security", h2_style),
        Paragraph(
            "The company shall provision a high-security laptop featuring full-disk AES-256 encryption. "
            "Employees are strictly prohibited from storing customer data or proprietary codebase repositories on personal devices. "
            "Connecting through the corporate Virtual Private Network (VPN) with multi-factor authentication is mandatory at all times.",
            body_style,
        ),
        Spacer(1, 10),
        Paragraph("Section 3: Working Hours and Overtime", h2_style),
        Paragraph(
            "Core working hours for remote staff are 9:00 AM to 4:00 PM East Africa Time (EAT), Monday through Friday. "
            "Any overtime work requires at least 24 hours prior written approval from the direct supervisor. "
            "Overtime hours may not exceed a maximum of 10 hours per calendar week.",
            body_style,
        ),
        Spacer(1, 10),
        Paragraph("Section 4: Allowances and Equipment Stipends", h2_style),
        Paragraph(
            "Remote employees are entitled to a monthly internet connectivity stipend of 1,500 ETB, payable with regular payroll. "
            "Additionally, eligible full-time staff may claim a one-time ergonomic home workstation setup allowance of up to 10,000 ETB "
            "upon submission of valid fiscal receipts.",
            body_style,
        ),
        Spacer(1, 10),
        Paragraph("Section 5: Confidentiality and Data Protection", h2_style),
        Paragraph(
            "Confidential company records and customer personal data must never be downloaded or printed locally. "
            "All non-disclosure and intellectual property protection covenants remain legally binding and survive employment termination for a duration of 3 years.",
            body_style,
        ),
    ]
    doc.build(story)
    logger.info("Generated PDF at %s", target_path)


def generate_consulting_terms_pdf(target_path: Path):
    doc = SimpleDocTemplate(str(target_path), pagesize=letter)
    styles = getSampleStyleSheet()
    title_style = styles["Title"]
    h2_style = styles["Heading2"]
    body_style = styles["BodyText"]

    story = [
        Paragraph("Standard Consulting Services Terms & Conditions", title_style),
        Spacer(1, 14),
        Paragraph("Section 1: Deliverables and Reporting Milestones", h2_style),
        Paragraph(
            "The Consultant shall prepare and deliver detailed project milestone reports every 14 calendar days. "
            "The Client shall have an inspection and acceptance period of 5 business days following delivery to review and approve work product.",
            body_style,
        ),
        Spacer(1, 10),
        Paragraph("Section 2: Payment Terms and Invoicing", h2_style),
        Paragraph(
            "Invoices shall be rendered upon successful completion of each milestone and are payable net 30 calendar days from written acceptance. "
            "Late payments shall accrue statutory interest at the rate of 1.5% per month on outstanding balances.",
            body_style,
        ),
        Spacer(1, 10),
        Paragraph("Section 3: Intellectual Property Assignment", h2_style),
        Paragraph(
            "All software code, documentation, designs, and proprietary inventions authored by Consultant in performance of the Services "
            "shall vest exclusively in and become the sole property of the Client upon payment in full.",
            body_style,
        ),
        Spacer(1, 10),
        Paragraph("Section 4: Termination and Notice Periods", h2_style),
        Paragraph(
            "Either party may terminate this Agreement without cause by providing 30 calendar days prior written notice. "
            "Immediate termination for cause is permitted in the event of an uncured material breach following 10 calendar days written notice.",
            body_style,
        ),
        Spacer(1, 10),
        Paragraph("Section 5: Dispute Resolution and Governing Law", h2_style),
        Paragraph(
            "This Agreement is governed by the laws of the Federal Democratic Republic of Ethiopia. "
            "Any disputes arising hereunder shall first be submitted to 15 days of mandatory amicable negotiation, "
            "failing which disputes shall be resolved through final arbitration in Addis Ababa under the rules of the Addis Ababa Chamber of Commerce and Sectoral Associations Arbitration Center.",
            body_style,
        ),
    ]
    doc.build(story)
    logger.info("Generated PDF at %s", target_path)


def seed_demo_corpus():
    corpus_dir = backend_dir / "demo_corpus"
    corpus_dir.mkdir(parents=True, exist_ok=True)

    remote_pdf = corpus_dir / "addis_remote_work_policy.pdf"
    consulting_pdf = corpus_dir / "standard_consulting_terms.pdf"

    if not remote_pdf.exists():
        generate_remote_work_policy_pdf(remote_pdf)
    if not consulting_pdf.exists():
        generate_consulting_terms_pdf(consulting_pdf)

    session_factory = get_session_factory()
    with session_factory() as db:
        admin_user = db.scalar(select(User).where(User.email == "melakuzenebu@gmail.com"))
        if not admin_user:
            admin_user = User(
                name="Zenebu Melaku",
                email="melakuzenebu@gmail.com",
                password_hash="admin-hash",
                role="admin",
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

        files_to_seed = [
            (remote_pdf, "addis_remote_work_policy.pdf"),
            (consulting_pdf, "standard_consulting_terms.pdf"),
        ]

        for filepath, filename in files_to_seed:
            content = filepath.read_bytes()
            checksum = hashlib.sha256(content).hexdigest()

            # Check if document already exists
            existing_doc = db.scalar(select(Document).where(Document.checksum == checksum, Document.deleted_at.is_(None)))
            storage_key = f"demo-{filename}"

            # Save to storage directory if not present
            storage_path = backend_dir / "var" / "private-documents" / storage_key
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            if not storage_path.exists():
                storage_path.write_bytes(content)

            if existing_doc is None:
                doc_record = Document(
                    id=uuid.uuid4(),
                    owner_user_id=admin_user.id,
                    original_filename=filename,
                    storage_key=storage_key,
                    content_type="application/pdf",
                    file_size=len(content),
                    checksum=checksum,
                    detected_language="en",
                    document_type="pdf",
                    processing_status="completed",
                )
                db.add(doc_record)
                db.flush()
            else:
                doc_record = existing_doc

            # Extract and ingest into vector store
            extraction = extract_document(content, "pdf", 50 * 1024 * 1024, False)
            chunks_count = ingest_document_to_vector_store(db, doc_record, extraction)
            db.commit()
            logger.info("Successfully ingested '%s': %d vector chunks indexed", filename, chunks_count)

    print("Demo corpus preparation and ingestion completed successfully!")


if __name__ == "__main__":
    seed_demo_corpus()
