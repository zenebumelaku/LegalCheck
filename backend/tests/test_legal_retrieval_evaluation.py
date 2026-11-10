import json
from pathlib import Path

import pytest

from app.scripts.evaluate_legal_retrieval import _validate_dataset
from app.services.legal_retrieval_evaluation import calculate_retrieval_metrics

pytestmark = pytest.mark.unit


def test_retrieval_metrics_at_five() -> None:
    metrics = calculate_retrieval_metrics(
        ["irrelevant", "relevant-a", "relevant-b"],
        {"relevant-a", "relevant-b"},
        k=5,
    )

    assert metrics["recall"] == 1.0
    assert metrics["precision"] == 0.4
    assert metrics["mrr"] == 0.5
    assert metrics["ndcg"] == pytest.approx(
        (1 / 2 + 1 / 1.584962500721156)
        / (1 + 1 / 1.584962500721156)
    )


def test_duplicate_retrieved_passages_do_not_inflate_metrics() -> None:
    metrics = calculate_retrieval_metrics(
        ["relevant-a", "relevant-a", "irrelevant"],
        {"relevant-a", "relevant-b"},
        k=5,
    )

    assert metrics["recall"] == 0.5
    assert metrics["precision"] == 0.2
    assert metrics["mrr"] == 1.0
    assert metrics["ndcg"] == pytest.approx(1 / (1 + 1 / 1.584962500721156))


def test_unanswerable_questions_have_undefined_precision_and_recall() -> None:
    metrics = calculate_retrieval_metrics(
        ["retrieved-provision"],
        set(),
        k=5,
    )

    assert metrics == {
        "recall": None,
        "precision": None,
        "mrr": 0.0,
        "ndcg": 0.0,
    }


def test_retrieval_metrics_reject_nonpositive_cutoff() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        calculate_retrieval_metrics([], set(), k=0)


def test_evaluation_runner_refuses_empty_unreviewed_template() -> None:
    dataset_path = Path(__file__).parent / "evaluation" / "dataset.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))

    with pytest.raises(ValueError, match="not ready"):
        _validate_dataset(dataset)
