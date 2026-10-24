import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  Scale,
  BookOpen,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  CheckCircle2,
  AlertTriangle,
  FileText,
  Calendar,
  ShieldCheck,
  Building2
} from 'lucide-react';
import { LegalSource, LegalArticle } from '../types';
import { LegalSourceService } from '../services/legal-source.service';
import { formatDate } from '../lib/utils';
import { EmptyState, LoadingSkeleton } from '../components/ui/FeedbackModals';

export function LegalSourcesPage() {
  const [sources, setSources] = useState<LegalSource[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [expandedSourceId, setExpandedSourceId] = useState<string>('eth-labour-proc-1156-2019');
  const [selectedArticle, setSelectedArticle] = useState<LegalArticle | null>(null);

  useEffect(() => {
    async function fetchSources() {
      setLoading(true);
      try {
        const data = await LegalSourceService.listLegalSources({
          query: searchQuery,
          status: statusFilter
        });
        setSources(data);
      } catch (err) {
        console.error('Failed to load legal sources', err);
      } finally {
        setLoading(false);
      }
    }
    fetchSources();
  }, [searchQuery, statusFilter]);

  const getStatusBadge = (status: LegalSource['status']) => {
    switch (status) {
      case 'IN_FORCE':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
            <CheckCircle2 className="w-3 h-3 text-emerald-600" />
            <span>In Force</span>
          </span>
        );
      case 'AMENDED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold rounded bg-amber-50 text-amber-800 border border-amber-200">
            <AlertTriangle className="w-3 h-3 text-amber-600" />
            <span>Partially Amended</span>
          </span>
        );
      case 'REPEALED':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold rounded bg-rose-50 text-rose-800 border border-rose-200">
            <AlertTriangle className="w-3 h-3 text-rose-600" />
            <span>Repealed / Superseded</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold rounded bg-slate-100 text-slate-700 border border-slate-200">
            <span>Status Unknown</span>
          </span>
        );
    }
  };

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 space-y-6">
      {/* Page Title */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
          Verified Ethiopian Legal Sources
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-500">
          Authoritative database of Ethiopian labour and commercial proclamations, Gazeta publication provenance, and statutory articles.
        </p>
      </div>

      {/* Search & Filters */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between shadow-xs">
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Search by title, proclamation number, article number (e.g. Article 88, 60 days, probation)..."
            className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-slate-200 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
        </div>

        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={e => setStatusFilter(e.target.value)}
            className="text-xs rounded-lg border border-slate-200 p-2 bg-slate-50 text-slate-700 focus:outline-none"
          >
            <option value="ALL">All Legal Statuses</option>
            <option value="IN_FORCE">In Force Only</option>
            <option value="AMENDED">Amended</option>
            <option value="REPEALED">Repealed</option>
          </select>
        </div>
      </div>

      {/* Sources List */}
      {loading ? (
        <LoadingSkeleton count={3} />
      ) : sources.length === 0 ? (
        <EmptyState
          title="No Legal Sources Found"
          description={`No legal sources matched your query "${searchQuery}". Reset filters to browse all statutes.`}
          actionLabel="Clear Search Filter"
          onAction={() => {
            setSearchQuery('');
            setStatusFilter('ALL');
          }}
        />
      ) : (
        <div className="space-y-6">
          {sources.map(source => {
            const isExpanded = expandedSourceId === source.id;

            return (
              <div
                key={source.id}
                className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs transition-shadow"
              >
                {/* Source Header */}
                <div
                  onClick={() => setExpandedSourceId(isExpanded ? '' : source.id)}
                  className="p-5 sm:p-6 cursor-pointer hover:bg-slate-50/70 transition-colors flex items-start justify-between gap-4"
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-900">
                        {source.proclamationNumber}
                      </span>
                      <span>·</span>
                      {getStatusBadge(source.status)}
                      <span>·</span>
                      <span className="text-xs text-slate-500">{source.category}</span>
                    </div>

                    <h2 className="text-base sm:text-lg font-bold text-slate-900">
                      {source.title}
                    </h2>

                    <p className="text-xs sm:text-sm text-slate-600 line-clamp-2 leading-relaxed">
                      {source.description}
                    </p>

                    <div className="pt-2 flex flex-wrap items-center gap-4 text-xs text-slate-500">
                      <div className="flex items-center gap-1.5">
                        <Building2 className="w-3.5 h-3.5 text-slate-400" />
                        <span>{source.officialGazeta}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5 text-slate-400" />
                        <span>Effective: {formatDate(source.effectiveDate)}</span>
                      </div>
                      <div className="text-emerald-700 font-medium">
                        {source.articles.length} Annotated Articles Available
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 pt-1">
                    <button
                      className="p-1 text-slate-400 hover:text-slate-600"
                      aria-label={isExpanded ? 'Collapse proclamation articles' : 'Expand proclamation articles'}
                    >
                      {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                {/* Expanded Articles View */}
                {isExpanded && (
                  <div className="px-5 pb-6 sm:px-6 border-t border-slate-100 pt-5 space-y-6">
                    {/* Provenance Box */}
                    <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 grid grid-cols-1 sm:grid-cols-3 gap-3">
                      <div>
                        <span className="block text-[11px] text-slate-400">Legislative Publisher:</span>
                        <span className="font-medium text-slate-800">{source.provenance.publisher}</span>
                      </div>
                      <div>
                        <span className="block text-[11px] text-slate-400">Verified By:</span>
                        <span className="font-medium text-slate-800">{source.provenance.verifiedBy}</span>
                      </div>
                      <div>
                        <span className="block text-[11px] text-slate-400">Gazette Archive Volume:</span>
                        <span className="font-medium text-slate-800">{source.provenance.gazetaVolume}</span>
                      </div>
                    </div>

                    {/* Article Search or Direct List */}
                    <div>
                      <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">
                        Statutory Articles in this Proclamation
                      </h3>

                      <div className="space-y-3">
                        {source.articles.map(article => (
                          <div
                            key={article.id}
                            className="p-4 rounded-lg border border-slate-200 bg-white hover:border-slate-300 transition-colors"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-sm text-slate-900">
                                  {article.articleNumber}: {article.title}
                                </span>
                                {article.subArticle && (
                                  <span className="text-xs font-medium text-slate-500">
                                    ({article.subArticle})
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* English Text */}
                            <p className="text-xs sm:text-sm text-slate-800 font-serif leading-relaxed mb-3">
                              "{article.text}"
                            </p>

                            {/* Amharic Text if present */}
                            {article.amharicText && (
                              <div className="bg-slate-50 p-3 rounded border border-slate-200 mb-3">
                                <div className="text-[11px] font-semibold text-slate-500 mb-1">
                                  የአማርኛ የሕግ ጽሑፍ:
                                </div>
                                <p className="font-serif text-xs text-slate-900 leading-relaxed">
                                  {article.amharicText}
                                </p>
                              </div>
                            )}

                            {/* Statutory Commentary / Practice Notes */}
                            {article.notes && (
                              <div className="text-xs text-slate-600 bg-emerald-50/40 p-2.5 rounded border border-emerald-100 flex items-start gap-2">
                                <Scale className="w-4 h-4 text-emerald-700 shrink-0 mt-0.5" />
                                <div>
                                  <span className="font-semibold text-emerald-950">Statutory Analysis Note: </span>
                                  <span>{article.notes}</span>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* External Gazette Link */}
                    {source.sourceUrl && (
                      <div className="pt-2 flex justify-end">
                        <a
                          href={source.sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900"
                        >
                          <span>Open Official Gazette Record (ILO NATLEX / Gazeta)</span>
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
