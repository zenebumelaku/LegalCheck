import json
import os
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.db.models import LegalProvision, LegalSource
from app.schemas.legal_retrieval import LegalReviewContext
from app.services.legal_retrieval import retrieve_legal_evidence

pytestmark = [
    pytest.mark.legal_evaluation,
    pytest.mark.postgres_integration,
]

DATASET_PATH = Path(__file__).with_name("dataset.json")


def test_real_source_retrieval_evaluation() -> None:
    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    assert dataset["schema_version"] == 1
    assert isinstance(dataset["cases"], list)
    assert {
        "case_id",
        "question",
        "review_context",
        "top_k",
        "expected_provisions",
        "manual_review",
    } <= set(dataset["case_schema"])
    if dataset["status"] == "placeholder_no_verified_source_material":
        assert dataset["cases"] == []
        pytest.skip(
            "Legal evaluation unavailable: no verified source dataset or reviewed cases."
        )
    assert dataset["status"] == "ready_with_manual_review"
    database_url = os.getenv("LEGAL_QA_EVALUATION_DATABASE_URL")
    if not database_url:
        pytest.skip("Set LEGAL_QA_EVALUATION_DATABASE_URL to the evaluation database.")

    engine = create_engine(database_url)
    try:
        assert engine.dialect.name == "postgresql", (
            "Legal evaluation requires PostgreSQL with pgvector enabled."
        )
        with Session(engine) as db:
            assert db.scalar(
                text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
            ), "The evaluation database must have the pgvector extension enabled."

            for case in dataset["cases"]:
                assert case["manual_review"]["reviewer_qualification"]
                assert case["manual_review"]["reviewed_at"]
                assert case["manual_review"]["reference"]
                expected: set[UUID] = set()
                for gold in case["expected_provisions"]:
                    provision_id = UUID(gold["provision_id"])
                    expected.add(provision_id)
                    row = db.execute(
                        select(LegalProvision, LegalSource)
                        .join(
                            LegalSource,
                            LegalSource.id == LegalProvision.legal_source_id,
                        )
                        .where(
                            LegalProvision.id == provision_id,
                            LegalSource.id == UUID(gold["source_id"]),
                            LegalSource.version_label == gold["source_version"],
                        )
                    ).one_or_none()
                    assert row is not None, (
                        f"Expected provision {provision_id} and source version "
                        "must exist in the evaluation database."
                    )
                    _, source = row
                    assert source.eligible_for_findings
                    assert source.verification_status == "verified"

                context = LegalReviewContext.model_validate(case["review_context"])
                response = retrieve_legal_evidence(
                    case["question"],
                    context,
                    case["top_k"],
                    db=db,
                )
                retrieved = {result.provision_id for result in response.results}
                assert expected <= retrieved, (
                    "Retrieval missed manually reviewed expected provisions "
                    f"for case {case['case_id']}."
                )
    finally:
        engine.dispose()
