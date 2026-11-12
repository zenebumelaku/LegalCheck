import { LegalArticle, LegalSource } from '../types';
import { ETHIOPIAN_LEGAL_SOURCES } from '../data/legal-sources-db';
import { apiRequest, ApiError } from '../lib/api-client';

interface ApiLegalSource {
  id: string;
  title: string;
  law_number: string | null;
  source_type: string;
  jurisdiction: string;
  language: string;
  publication_date: string | null;
  effective_date: string | null;
  original_source_url: string | null;
  legal_status: 'unknown' | 'current' | 'amended' | 'repealed' | 'superseded';
  version_label: string | null;
  verification_status: string;
  verified_at: string | null;
  verified_by: string | null;
}

interface ApiLegalSourcePage {
  items: ApiLegalSource[];
  limit: number;
  offset: number;
  total: number;
}

interface ApiLegalProvision {
  id: string;
  article_number: string;
  sub_article_reference: string | null;
  section_title: string | null;
  text: string;
}

interface ApiLegalProvisionPage {
  items: ApiLegalProvision[];
  limit: number;
  offset: number;
  total: number;
}

function toUiStatus(
  status: ApiLegalSource['legal_status']
): LegalSource['status'] {
  switch (status) {
    case 'current':
      return 'IN_FORCE';
    case 'amended':
      return 'AMENDED';
    case 'repealed':
    case 'superseded':
      return 'REPEALED';
    default:
      return 'UNKNOWN';
  }
}

function toLegalArticle(provision: ApiLegalProvision): LegalArticle {
  return {
    id: provision.id,
    articleNumber: provision.article_number,
    subArticle: provision.sub_article_reference ?? undefined,
    title: provision.section_title ?? 'Provision',
    text: provision.text
  };
}

async function getProvisions(sourceId: string): Promise<LegalArticle[]> {
  const page = await apiRequest<ApiLegalProvisionPage>(
    `/api/v1/legal-sources/${encodeURIComponent(sourceId)}/provisions`,
    { params: { limit: 500 } }
  );
  return page.items.map(toLegalArticle);
}

async function toLegalSource(source: ApiLegalSource): Promise<LegalSource> {
  const articles = await getProvisions(source.id);
  return {
    id: source.id,
    proclamationNumber: source.law_number ?? 'Law number not recorded',
    title: source.title,
    officialGazeta: source.original_source_url ?? 'Publication details not recorded',
    publicationDate: source.publication_date ?? '',
    effectiveDate: source.effective_date ?? '',
    status: toUiStatus(source.legal_status),
    description: `Source type: ${source.source_type} · Jurisdiction: ${source.jurisdiction} · Language: ${source.language}`,
    category: source.source_type,
    sourceUrl: source.original_source_url ?? undefined,
    articlesCount: articles.length,
    articles,
    provenance: {
      publisher: source.jurisdiction,
      verifiedBy: source.verified_by
        ? `Reviewer ${source.verified_by}`
        : 'Not recorded',
      lastVerifiedDate: source.verified_at ?? 'Not recorded',
      gazetaVolume: source.version_label ?? 'Not recorded'
    }
  };
}

export class LegalSourceService {
  static reviewApplicability(
    sourceId: string,
    payload: {
      legal_status: ApiLegalSource['legal_status'];
      effective_date: string | null;
      end_date: string | null;
      verification_notes: string;
    }
  ): Promise<ApiLegalSource> {
    return apiRequest<ApiLegalSource>(
      `/api/v1/legal-sources/${encodeURIComponent(sourceId)}/applicability-review`,
      {
        method: 'POST',
        body: JSON.stringify(payload)
      }
    );
  }

  static async listLegalSources(filters?: {
    category?: string;
    status?: string;
    query?: string;
  }): Promise<LegalSource[]> {
    const legalStatus =
      filters?.status === 'IN_FORCE'
        ? 'current'
        : filters?.status === 'AMENDED'
          ? 'amended'
          : filters?.status === 'REPEALED'
            ? 'repealed'
            : undefined;
    const page = await apiRequest<ApiLegalSourcePage>('/api/v1/legal-sources', {
      params: {
        q: filters?.query || undefined,
        source_type:
          filters?.category && filters.category !== 'ALL'
            ? filters.category
            : undefined,
        legal_status: legalStatus,
        limit: 100
      }
    });
    return Promise.all(page.items.map(toLegalSource));
  }

  static async getLegalSource(id: string): Promise<LegalSource | null> {
    try {
      const source = await apiRequest<ApiLegalSource>(
        `/api/v1/legal-sources/${encodeURIComponent(id)}`
      );
      return await toLegalSource(source);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) return null;
      throw error;
    }
  }

  static async searchProvisions(query: string): Promise<Array<{
    source: LegalSource;
    article: LegalArticle;
  }>> {
    const normalizedQuery = query.toLowerCase();
    const results: Array<{ source: LegalSource; article: LegalArticle }> = [];
    for (const source of ETHIOPIAN_LEGAL_SOURCES) {
      for (const article of source.articles) {
        if (
          article.title.toLowerCase().includes(normalizedQuery) ||
          article.articleNumber.toLowerCase().includes(normalizedQuery) ||
          article.text.toLowerCase().includes(normalizedQuery) ||
          article.amharicText?.includes(query)
        ) {
          results.push({ source, article });
        }
      }
    }
    return results;
  }
}
