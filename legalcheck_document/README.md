# LegalCheck source package — Labour Proclamation No. 1156/2019

## Files
- `metadata.json` — ingestion metadata based on the uploaded Gazette PDF.
- `provisions.json` — English text-layer extraction grouped by detected article headings.
- `review_manifest.json` — extraction statistics and unresolved legal-review flags.
- `source.pdf` — copy of the original uploaded PDF.

## Document facts read from the PDF
- Title: Labour Proclamation
- Law number: Proclamation No. 1156/2019
- Publication: Federal Negarit Gazette, 25th Year, No. 89
- Date: 5 September 2019
- PDF pages: 103

## Extraction result
- Article headings detected: 193
- Missing article numbers in the 1–193 sequence: None
- Extracted language: English only (right-hand column)
- `page_number` is the 1-based PDF page index where the article heading begins, not the printed Gazette page number.

## Important limitations
This is a machine-extracted preparation package, **not a legally verified corpus**. The English text layer is extracted from the bilingual PDF, but line order, column flow, punctuation, and some text may require comparison with the rendered PDF. Sub-articles are not separately segmented. The Amharic column has not been extracted into parallel provisions. Article boundaries are heading-based and must be reviewed. The Ethiopian Ministry of Justice official law record is available at https://justice.gov.et/en/law/labour-proclamation/. It identifies Proclamation No. 1156/2019, dates it 5 September 2019, and currently labels it **In Force**. The page does not establish a complete amendment history, so amendment status remains unverified. The Ministry record is a status indicator, not a substitute for reviewing later amending instruments and provision-level applicability.

The PDF's Article 193 says the Proclamation enters into force on publication in the Federal Negarit Gazette. That is evidence of its stated commencement rule, **not proof that this is the current consolidated version**.

## LegalCheck ingestion
Use `metadata.json`, `provisions.json`, and `source.pdf` with the repository's `POST /api/v1/legal-sources/ingest` endpoint (multipart fields: `metadata_json`, `provisions_json`, `file`). Check the live schema for nullability of `original_source_url`; if it requires a URL, do not invent one—obtain the official URL first.

Expected lifecycle:
1. Ingest as pending/unverified.
2. An authorized reviewer other than the submitter checks the source provenance, version/amendment status, article and sub-article boundaries, and extracted text against the PDF.
3. Only after successful independent verification, mark the source verified using the repository's verification endpoint.
4. Generate embeddings only for the verified source, using the project's documented embedding command.

Do not use this package as a final legal authority until those checks are complete.


## Official provenance
- Ministry of Justice law record: https://justice.gov.et/en/law/labour-proclamation/
- Ministry of Justice currently labels the proclamation **In Force** and gives the date 5 September 2019. Amendment history still needs a separate official review.
