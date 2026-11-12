import { LegalSourceService } from '../services/legal-source.service';
import { ETHIOPIAN_LEGAL_SOURCES } from '../data/legal-sources-db';

function assert(condition: boolean, message: string): void {
  if (!condition) throw new Error(`TEST FAILED: ${message}`);
  console.log(`✓ PASS: ${message}`);
}

async function runTests(): Promise<void> {
  console.log('\n--- Running Legal Source API Client Tests ---');
  const originalFetch = globalThis.fetch;
  const requests: string[] = [];
  globalThis.fetch = async input => {
    const url = String(input);
    requests.push(url);
    if (url.includes('/provisions')) {
      return new Response(
        JSON.stringify({
          items: [
            {
              id: 'provision-1',
              article_number: '1',
              sub_article_reference: null,
              section_title: 'Purpose',
              text: 'Synthetic legal provision text.'
            }
          ],
          limit: 500,
          offset: 0,
          total: 1
        }),
        { status: 200 }
      );
    }
    return new Response(
      JSON.stringify({
        items: [
          {
            id: 'source-1',
            title: 'Synthetic legal source',
            law_number: 'SYN-1',
            source_type: 'proclamation',
            jurisdiction: 'ET',
            language: 'en',
            publication_date: '2025-01-01',
            effective_date: '2025-02-01',
            original_source_url: 'https://example.test/source.pdf',
            legal_status: 'current',
            version_label: 'v1',
            verification_status: 'verified',
            verified_at: '2025-02-01T00:00:00Z',
            verified_by: 'reviewer-1'
          }
        ],
        limit: 100,
        offset: 0,
        total: 1
      }),
      { status: 200 }
    );
  };

  try {
    const labourProclamation = ETHIOPIAN_LEGAL_SOURCES.find(
      source => source.proclamationNumber === 'No. 1156/2019'
    );
    assert(
      labourProclamation?.articles.length === 193,
      'Includes all 193 Labour Proclamation articles in the website source data'
    );
    assert(
      labourProclamation?.articles[0].articleNumber === 'Article 1' &&
        labourProclamation?.articles[192].articleNumber === 'Article 193',
      'Displays the full Labour Proclamation article range'
    );

    const sources = await LegalSourceService.listLegalSources({
      query: 'SYN-1',
      status: 'IN_FORCE'
    });
    assert(sources.length === 1, 'Maps the backend page response into a source list');
    assert(sources[0].status === 'IN_FORCE', 'Maps backend legal status to UI status');
    assert(
      sources[0].articles[0].text === 'Synthetic legal provision text.',
      'Loads backend provisions for the source'
    );
    assert(
      requests[0].includes('q=SYN-1') &&
        requests[0].includes('legal_status=current'),
      'Uses the backend source-search and legal-status query parameters'
    );
    assert(
      requests[1].endsWith('/api/v1/legal-sources/source-1/provisions?limit=500'),
      'Requests the source provisions endpoint'
    );

    await LegalSourceService.reviewApplicability('source-1', {
      legal_status: 'current',
      effective_date: '2025-02-01',
      end_date: null,
      verification_notes: 'Confirmed against the official legal registry.'
    });
    assert(
      requests[2].endsWith(
        '/api/v1/legal-sources/source-1/applicability-review'
      ),
      'Submits applicability reviews to the admin review endpoint'
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
}

runTests().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
