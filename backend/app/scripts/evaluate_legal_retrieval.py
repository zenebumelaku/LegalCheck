import argparse
import csv
import hashlib
import json
import os
from time import perf_counter
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import LegalProvision, LegalSource
from app.schemas.legal_retrieval import LegalReviewContext
from app.services.legal_question_answering import answer_legal_question
from app.services.legal_reranking import get_legal_evidence_reranker
from app.services.legal_retrieval import retrieve_legal_evidence
from app.services.legal_retrieval_evaluation import calculate_retrieval_metrics

_QUESTION_TYPES = {
    "exact_article",
    "semantic",
    "keyword",
    "multi_provision",
    "unanswerable",
}
_CONFIGURATIONS = (
    ("baseline", "baseline", False),
    ("hybrid_rrf", "hybrid", False),
    ("hybrid_rrf_reranked", "hybrid", True),
)


def _validate_dataset(dataset: dict[str, Any]) -> list[dict[str, Any]]:
    if dataset.get("schema_version") != 1:
        raise ValueError("Unsupported evaluation dataset schema_version.")
    if dataset.get("status") != "ready_with_manual_review":
        raise ValueError(
            "The evaluation dataset is not ready; add manually reviewed legal cases "
            "before running a benchmark."
        )
    cases = dataset.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("The evaluation dataset contains no reviewed cases.")
    case_ids: set[str] = set()
    for case in cases:
        required = {
            "case_id",
            "question",
            "question_type",
            "review_context",
            "top_k",
            "expected_provisions",
            "manual_review",
        }
        if not isinstance(case, dict) or not required <= case.keys():
            raise ValueError("An evaluation case is missing required fields.")
        if not isinstance(case["case_id"], str) or not case["case_id"]:
            raise ValueError("Every evaluation case must have a nonempty case_id.")
        if case["case_id"] in case_ids:
            raise ValueError(f"Duplicate evaluation case_id: {case['case_id']}.")
        case_ids.add(case["case_id"])
        if not isinstance(case["question"], str) or not case["question"].strip():
            raise ValueError(f"Question is empty for case {case['case_id']}.")
        if (
            not isinstance(case["top_k"], int)
            or isinstance(case["top_k"], bool)
            or not 1 <= case["top_k"] <= 100
        ):
            raise ValueError(f"top_k must be between 1 and 100 for {case['case_id']}.")
        if (
            not isinstance(case["question_type"], str)
            or case["question_type"] not in _QUESTION_TYPES
        ):
            raise ValueError(f"Unknown question_type for case {case['case_id']}.")
        expected = case["expected_provisions"]
        if not isinstance(expected, list):
            raise ValueError(f"Expected provisions must be a list for {case['case_id']}.")
        if (case["question_type"] == "unanswerable") != (not expected):
            raise ValueError(
                "Only unanswerable cases must have an empty expected_provisions list."
            )
        if case["question_type"] == "multi_provision" and len(expected) < 2:
            raise ValueError(
                f"Multi-provision case {case['case_id']} needs at least two gold provisions."
            )
        if any(not isinstance(gold, dict) for gold in expected):
            raise ValueError(
                f"Expected provision records must be objects for {case['case_id']}."
            )
        review = case["manual_review"]
        if not isinstance(review, dict):
            raise ValueError(f"Manual review metadata is missing for {case['case_id']}.")
        if not all(
            review.get(field)
            for field in ("reviewer_qualification", "reviewed_at", "reference")
        ):
            raise ValueError(f"Manual review metadata is incomplete for {case['case_id']}.")
    return cases


def _validate_expected_sources(db: Session, case: dict[str, Any]) -> set[str]:
    expected_ids: set[str] = set()
    for gold in case["expected_provisions"]:
        provision_id = UUID(gold["provision_id"])
        source_id = UUID(gold["source_id"])
        row = db.execute(
            select(LegalProvision.id)
            .join(LegalSource, LegalSource.id == LegalProvision.legal_source_id)
            .where(
                LegalProvision.id == provision_id,
                LegalSource.id == source_id,
                LegalSource.version_label == gold["source_version"],
                LegalSource.verification_status == "verified",
                LegalSource.legal_status == "current",
            )
        ).scalar_one_or_none()
        if row is None:
            raise ValueError(
                f"Reviewed provision {provision_id} for case {case['case_id']} "
                "does not match a verified current source in this database."
            )
        expected_ids.add(str(provision_id))
    return expected_ids


def _average(values: list[float]) -> float | None:
    return mean(values) if values else None


def run_evaluation(
    *,
    dataset_path: Path,
    output_path: Path,
    include_end_to_end: bool = False,
) -> dict[str, Any]:
    raw_dataset = dataset_path.read_bytes()
    dataset = json.loads(raw_dataset)
    cases = _validate_dataset(dataset)
    database_url = os.getenv("LEGAL_QA_EVALUATION_DATABASE_URL")
    if not database_url:
        raise ValueError("Set LEGAL_QA_EVALUATION_DATABASE_URL to the reviewed-source database.")

    engine = create_engine(database_url)
    try:
        if engine.dialect.name != "postgresql":
            raise ValueError("Evaluation requires PostgreSQL with pgvector enabled.")
        with Session(engine) as db:
            if not db.scalar(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'")):
                raise ValueError("The evaluation database must have the pgvector extension.")
            settings = get_settings()
            configuration_results: list[dict[str, Any]] = []
            csv_rows: list[dict[str, Any]] = []

            for name, mode, reranking in _CONFIGURATIONS:
                configured_settings = settings.model_copy(
                    update={
                        "legal_retrieval_mode": mode,
                        "legal_reranker_enabled": reranking,
                    }
                )
                reranker_status = (
                    "not_requested"
                    if not reranking
                    else (
                        "available"
                        if get_legal_evidence_reranker(configured_settings)
                        else "unavailable_fallback"
                    )
                )
                case_results: list[dict[str, Any]] = []
                e2e_latencies: list[float] = []
                cache_hits = 0
                cache_trials = 0

                for case in cases:
                    expected_ids = _validate_expected_sources(db, case)
                    context = LegalReviewContext.model_validate(case["review_context"])
                    start = perf_counter()
                    retrieval = retrieve_legal_evidence(
                        case["question"],
                        context,
                        5,
                        db=db,
                        settings=configured_settings,
                    )
                    retrieval_latency_ms = (perf_counter() - start) * 1000
                    metric_values = calculate_retrieval_metrics(
                        [str(result.provision_id) for result in retrieval.results],
                        expected_ids,
                        k=5,
                    )
                    case_result: dict[str, Any] = {
                        "case_id": case["case_id"],
                        "question_type": case["question_type"],
                        **{
                            f"{metric}_at_5" if metric in {"recall", "precision", "ndcg"} else metric:
                            value
                            for metric, value in metric_values.items()
                        },
                        "retrieval_latency_ms": retrieval_latency_ms,
                        "reranker_applied": retrieval.reranker_applied,
                        "end_to_end_response_latency_ms": None,
                        "cache_hit_rate": None,
                    }

                    if include_end_to_end:
                        trials: list[dict[str, Any]] = []
                        answer_settings = configured_settings.model_copy(
                            update={"legal_qa_top_k": case["top_k"]}
                        )
                        for _ in range(2):
                            answer_start = perf_counter()
                            answer = answer_legal_question(
                                case["question"],
                                context,
                                db=db,
                                settings=answer_settings,
                            )
                            latency = (perf_counter() - answer_start) * 1000
                            e2e_latencies.append(latency)
                            cache_trials += 1
                            cache_hits += int(answer.cache_hit)
                            trials.append(
                                {
                                    "latency_ms": latency,
                                    "cache_hit": answer.cache_hit,
                                    "answer_status": answer.status,
                                }
                            )
                        case_result["end_to_end_response_latency_ms"] = _average(
                            [trial["latency_ms"] for trial in trials]
                        )
                        case_result["cache_hit_rate"] = sum(
                            trial["cache_hit"] for trial in trials
                        ) / len(trials)
                        case_result["end_to_end_trials"] = trials

                    case_results.append(case_result)
                    csv_case_result = dict(case_result)
                    if "end_to_end_trials" in csv_case_result:
                        csv_case_result["end_to_end_trials"] = json.dumps(
                            csv_case_result["end_to_end_trials"],
                            ensure_ascii=False,
                        )
                    csv_rows.append({"configuration": name, **csv_case_result})

                numeric_metric_names = ("recall_at_5", "precision_at_5", "mrr", "ndcg_at_5")
                aggregate = {
                    metric: _average(
                        [
                            case_result[metric]
                            for case_result in case_results
                            if case_result[metric] is not None
                        ]
                    )
                    for metric in numeric_metric_names
                }
                aggregate["retrieval_latency_ms"] = _average(
                    [case_result["retrieval_latency_ms"] for case_result in case_results]
                )
                aggregate["end_to_end_response_latency_ms"] = _average(e2e_latencies)
                aggregate["cache_hit_rate"] = (
                    cache_hits / cache_trials if cache_trials else None
                )
                configuration_results.append(
                    {
                        "configuration": name,
                        "retrieval_mode": mode,
                        "reranking_requested": reranking,
                        "reranker_status": reranker_status,
                        "case_count": len(case_results),
                        "aggregate": aggregate,
                        "cases": case_results,
                    }
                )

            output: dict[str, Any] = {
                "dataset_id": dataset.get("dataset_id"),
                "dataset_sha256": hashlib.sha256(raw_dataset).hexdigest(),
                "evaluated_at": datetime.now(timezone.utc).isoformat(),
                "methodology": {
                    "ranking_cutoff": 5,
                    "relevance": "binary manually reviewed provision IDs",
                    "end_to_end_trials_per_case": 2 if include_end_to_end else 0,
                    "cache_hit_rate": (
                        "Observed from LegalQuestionAnswer.cache_hit across all "
                        "end-to-end requests; null when end-to-end mode is disabled."
                    ),
                    "unanswerable_cases": (
                        "Recall@5 and Precision@5 are undefined and excluded from "
                        "their macro averages; MRR and nDCG@5 are zero."
                    ),
                },
                "configurations": configuration_results,
            }
    finally:
        engine.dispose()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() == ".csv":
        fieldnames = list(csv_rows[0].keys())
        with output_path.open("w", encoding="utf-8", newline="") as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
    else:
        output_path.write_text(
            json.dumps(output, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Benchmark legal retrieval on manually reviewed provisions."
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("tests/evaluation/dataset.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evaluation-results.json"),
    )
    parser.add_argument(
        "--include-end-to-end",
        action="store_true",
        help="Also call legal QA twice per case/configuration to measure response "
        "latency and observed Redis cache hits; requires configured QA dependencies.",
    )
    args = parser.parse_args()
    try:
        result = run_evaluation(
            dataset_path=args.dataset,
            output_path=args.output,
            include_end_to_end=args.include_end_to_end,
        )
    except (OSError, ValueError, SQLAlchemyError) as exc:
        parser.error(str(exc))
    print(
        f"Evaluated {len(result['configurations'][0]['cases'])} reviewed cases "
        f"across {len(result['configurations'])} configurations. "
        f"Results: {args.output}"
    )


if __name__ == "__main__":
    main()
