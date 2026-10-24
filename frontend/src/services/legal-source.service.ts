import { LegalSource } from '../types';
import { ETHIOPIAN_LEGAL_SOURCES } from '../data/legal-sources-db';
import { apiRequest } from '../lib/api-client';

export class LegalSourceService {
  static async listLegalSources(filters?: {
    category?: string;
    status?: string;
    query?: string;
  }): Promise<LegalSource[]> {
    try {
      return await apiRequest<LegalSource[]>('/api/v1/legal-sources', {
        params: filters as Record<string, string>
      });
    } catch {
      let sources = [...ETHIOPIAN_LEGAL_SOURCES];

      if (filters?.category && filters.category !== 'ALL') {
        sources = sources.filter(s => s.category.toLowerCase().includes(filters.category!.toLowerCase()));
      }

      if (filters?.status && filters.status !== 'ALL') {
        sources = sources.filter(s => s.status === filters.status);
      }

      if (filters?.query) {
        const q = filters.query.toLowerCase();
        sources = sources.filter(
          s =>
            s.title.toLowerCase().includes(q) ||
            s.proclamationNumber.toLowerCase().includes(q) ||
            s.description.toLowerCase().includes(q) ||
            s.articles.some(a => a.title.toLowerCase().includes(q) || a.text.toLowerCase().includes(q) || a.articleNumber.toLowerCase().includes(q))
        );
      }

      return sources;
    }
  }

  static async getLegalSource(id: string): Promise<LegalSource | null> {
    try {
      return await apiRequest<LegalSource>(`/api/v1/legal-sources/${id}`);
    } catch {
      const found = ETHIOPIAN_LEGAL_SOURCES.find(s => s.id === id);
      return found || null;
    }
  }

  static async searchProvisions(query: string): Promise<Array<{
    source: LegalSource;
    article: LegalSource['articles'][0];
  }>> {
    const q = query.toLowerCase();
    const results: Array<{ source: LegalSource; article: LegalSource['articles'][0] }> = [];

    ETHIOPIAN_LEGAL_SOURCES.forEach(source => {
      source.articles.forEach(article => {
        if (
          article.title.toLowerCase().includes(q) ||
          article.articleNumber.toLowerCase().includes(q) ||
          article.text.toLowerCase().includes(q) ||
          (article.amharicText && article.amharicText.includes(query))
        ) {
          results.push({ source, article });
        }
      });
    });

    return results;
  }
}
