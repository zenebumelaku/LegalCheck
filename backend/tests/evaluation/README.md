# Legal Q&A retrieval evaluation

This is a placeholder evaluation harness, not a legal corpus. The repository
currently contains no verified legal source dataset, so legal evaluation is
blocked and no accuracy score is available.

`dataset.json` is intentionally empty and marked
`placeholder_no_verified_source_material`. Do not fill it with synthetic test
fixtures. To prepare a real evaluation dataset:

1. Use source documents independently verified and explicitly eligible in the
   existing legal-source registry.
2. Record source IDs, provision IDs, and version labels from that registry in
   each case. The evaluation database must contain those same records.
3. Have a qualified legal professional manually review each expected provision
   for the case and record their qualification, review date, and an auditable
   review reference in `manual_review`.
4. Change dataset `status` to `ready_with_manual_review` only after cases meet
   that bar. Do not record client or confidential matter text in the dataset.

Run the harness with the evaluation dataset and a PostgreSQL-backed legal-source
registry configured:

```bash
cd backend
LEGAL_QA_EVALUATION_DATABASE_URL='postgresql+psycopg://…' \
  python -m pytest -q -m legal_evaluation tests/evaluation
```

The harness checks retrieval against manually reviewed provision IDs only. It
does not call an LLM, grade answer correctness, or establish legal correctness.
An empty placeholder is reported as a skipped test, not a passing evaluation.

## Manual legal review (separate from automated tests)

Before using any benchmark outcome or answer in a legal workflow, a qualified
reviewer must confirm the source is authoritative, the source/version and
effective dates are correct, the provision transcription and article/page
references match the document, applicability is appropriate to the case, and
the answer does not exceed the cited support. Record disagreements and
limitations. Automated retrieval tests are not a substitute for this review.
