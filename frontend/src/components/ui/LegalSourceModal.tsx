import React from 'react';
import { X, Scale, ExternalLink, Calendar, BookOpen } from 'lucide-react';
import { ETHIOPIAN_LEGAL_SOURCES } from '../../data/legal-sources-db';

interface LegalSourceModalProps {
  isOpen: boolean;
  provision: {
    proclamationTitle: string;
    proclamationNumber: string;
    articleNumber: string;
    subArticle?: string;
    provisionText: string;
    sourceId: string;
    sourceUrl?: string;
    effectiveDate: string;
  } | null;
  onClose: () => void;
  onNavigateToFullSource?: (sourceId: string) => void;
}

export function LegalSourceModal({
  isOpen,
  provision,
  onClose,
  onNavigateToFullSource
}: LegalSourceModalProps) {
  if (!isOpen || !provision) return null;

  const fullSource = ETHIOPIAN_LEGAL_SOURCES.find(s => s.id === provision.sourceId);
  const matchedArticle = fullSource?.articles.find(a =>
    a.articleNumber.toLowerCase().includes(provision.articleNumber.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
      <div className="w-full max-w-2xl bg-white rounded-xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900 text-white flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2.5">
            <Scale className="w-5 h-5 text-emerald-400" />
            <div>
              <h3 className="text-sm font-bold tracking-tight">Verified Legal Source Provision</h3>
              <p className="text-[11px] text-slate-400">{provision.proclamationTitle}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-1 rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-slate-800 text-xs sm:text-sm">
          {/* Metadata pill strip */}
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 grid grid-cols-2 sm:grid-cols-3 gap-3 text-xs">
            <div>
              <span className="text-slate-500 block text-[11px]">Proclamation:</span>
              <span className="font-semibold text-slate-900">{provision.proclamationNumber}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[11px]">Effective Date:</span>
              <span className="font-semibold text-slate-900">{provision.effectiveDate}</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[11px]">Publication:</span>
              <span className="font-semibold text-slate-900">
                {fullSource?.officialGazeta || 'Federal Negarit Gazeta'}
              </span>
            </div>
          </div>

          {/* Article Header */}
          <div>
            <div className="text-xs font-semibold text-emerald-800 uppercase tracking-wider mb-1">
              Official Statutory Text
            </div>
            <h4 className="text-base font-bold text-slate-900">
              {provision.articleNumber}: {matchedArticle?.title || 'Provision Text'}
            </h4>
          </div>

          {/* English Text */}
          <div className="p-4 bg-emerald-50/40 rounded-lg border border-emerald-100 font-serif leading-relaxed text-slate-900">
            {matchedArticle ? matchedArticle.text : provision.provisionText}
          </div>

          {/* Amharic Text if available */}
          {matchedArticle?.amharicText && (
            <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
              <div className="text-[11px] font-semibold text-slate-500 mb-1">
                የአማርኛ የሕግ ድንጋጌ (Official Amharic Gazeta Text)
              </div>
              <p className="font-serif text-slate-800 leading-relaxed text-sm">
                {matchedArticle.amharicText}
              </p>
            </div>
          )}

          {/* Statutory Notes & Legislative Intent */}
          {matchedArticle?.notes && (
            <div className="p-3 bg-blue-50/60 rounded-lg border border-blue-100 text-xs text-blue-900">
              <span className="font-semibold block mb-0.5">Statutory Context & Application:</span>
              <p>{matchedArticle.notes}</p>
            </div>
          )}

          {/* Provenance Details */}
          {fullSource && (
            <div className="pt-3 border-t border-slate-100 text-[11px] text-slate-500 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                Verified By: {fullSource.provenance.verifiedBy} (Last audited: {fullSource.provenance.lastVerifiedDate})
              </div>
              {provision.sourceUrl && (
                <a
                  href={provision.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-slate-700 hover:text-slate-900 font-medium"
                >
                  <span>Official Gazette Archive</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between shrink-0">
          {onNavigateToFullSource && fullSource ? (
            <button
              onClick={() => {
                onClose();
                onNavigateToFullSource(fullSource.id);
              }}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-800 hover:text-slate-950"
            >
              <BookOpen className="w-3.5 h-3.5" />
              <span>Browse All Articles in this Proclamation</span>
            </button>
          ) : <div />}
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-medium text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
