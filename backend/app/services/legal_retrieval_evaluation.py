import math
from typing import Optional, Sequence
from uuid import UUID


def calculate_retrieval_metrics(
    retrieved_provision_ids: Sequence[UUID | str],
    relevant_provision_ids: set[UUID | str],
    *,
    k: int = 5,
) -> dict[str, Optional[float]]:
    if k < 1:
        raise ValueError("k must be greater than zero.")

    unique_retrieved = list(dict.fromkeys(retrieved_provision_ids))[:k]
    relevant = set(relevant_provision_ids)
    if not relevant:
        return {
            "recall": None,
            "precision": None,
            "mrr": 0.0,
            "ndcg": 0.0,
        }

    relevant_ranks = [
        rank
        for rank, provision_id in enumerate(unique_retrieved, start=1)
        if provision_id in relevant
    ]
    recall = len(relevant_ranks) / len(relevant)
    precision = len(relevant_ranks) / k
    reciprocal_rank = 1.0 / relevant_ranks[0] if relevant_ranks else 0.0
    dcg = sum(1.0 / math.log2(rank + 1) for rank in relevant_ranks)
    ideal_hits = min(len(relevant), k)
    ideal_dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank in range(1, ideal_hits + 1)
    )
    return {
        "recall": recall,
        "precision": precision,
        "mrr": reciprocal_rank,
        "ndcg": dcg / ideal_dcg,
    }
