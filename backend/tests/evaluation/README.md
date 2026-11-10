# Legal Q&A retrieval evaluation

`dataset.json` is a schema/template, not a legal corpus. It has no reviewed
cases because this repository does not include verified legal source material
or legal-review records. Do not fill it with synthetic test fixtures or use
unreviewed legal questions as gold labels.

## Dataset requirements

Each case has a stable, non-sensitive `case_id`, manually reviewed `question`,
`question_type`, `review_context`, requested `top_k`, and
`expected_provisions`. Supported question types are:

- `exact_article`
- `semantic`
- `keyword`
- `multi_provision`
- `unanswerable`

Each expected provision records `source_id`, `source_version`, and
`provision_id` from the exact source version in the evaluation database.
Unanswerable cases have no expected provisions; all other case types must have
at least one. Every case includes a qualified reviewer's qualification,
`reviewed_at`, and auditable review `reference`. The registry entries must be
verified and currently applicable. Exclude client or confidential matter text.

Only mark the dataset `ready_with_manual_review` once all records meet those
requirements. The evaluation runner rejects placeholder datasets, invalid
source/version references, and incomplete review metadata.

## Measures and configurations

The runner compares:

1. `baseline`: existing exact-article, keyword, and vector retrieval.
2. `hybrid_rrf`: exact-article retrieval plus BM25 and vector ranks fused by
   reciprocal rank fusion.
3. `hybrid_rrf_reranked`: the hybrid candidate set reranked with the configured
   local cross-encoder. If the model is unavailable, the output reports
   `unavailable_fallback` and `reranker_applied` remains false.

Retrieval measures are Recall@5, Precision@5, MRR, binary nDCG@5, and
wall-clock retrieval latency. Metrics use provision IDs as binary relevance
labels and deduplicate retrieved provision IDs. Unanswerable cases have
undefined Recall@5 and Precision@5 (excluded from those macro averages) and
zero MRR/nDCG@5. Latencies are measured for each case/configuration.

End-to-end response latency and Redis cache hit rate are optional because they
require configured QA providers/services. `--include-end-to-end` makes two
actual answer-service calls per case/configuration; reports each trial's
latency and `cache_hit`, along with the observed cache hit rate. It does not
assume cache hits or fabricate LLM results. A provider failure is an evaluation
failure, not a synthetic answer.

JSON output includes the dataset SHA-256, timestamp, configurations,
per-case metrics, aggregate metrics, and methodology. CSV output contains
per-case rows. Keep results with the exact dataset version and configuration;
do not compare results from different reviewed datasets as if they were the
same benchmark.

## Running

Configure a PostgreSQL evaluation database containing the exact verified
source/version/provision IDs. PostgreSQL with `pgvector` is required:

```bash
cd backend
LEGAL_QA_EVALUATION_DATABASE_URL='postgresql+psycopg://USER:PASSWORD@HOST/DB' \
  python -m app.scripts.evaluate_legal_retrieval \
  --dataset tests/evaluation/dataset.json \
  --output evaluation-results.json
```

Write CSV instead by using `--output evaluation-results.csv`. To also benchmark
end-to-end requests, configure the LLM, Redis, and normal application
environment, then add `--include-end-to-end`. The command exits with an
explicit error for an empty placeholder dataset or missing evaluation
database; it never reports benchmark scores without running cases.

The test harness remains independently runnable:

```bash
python -m pytest -q -m 'legal_evaluation and postgres_integration' tests/evaluation
```

Until qualified reviewers provide a dataset and the harness/runner actually
executes it, no legal retrieval score or improvement is available. Automated
metrics do not establish legal correctness; a qualified legal reviewer must
also verify source authority, transcription, article/page boundaries,
applicability, and answer support.
