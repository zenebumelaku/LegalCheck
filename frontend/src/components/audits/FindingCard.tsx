import React, { useState } from 'react';
import { ChevronDown, ChevronUp, ExternalLink, Flag, CheckCircle, Scale, Quote, Sparkles } from 'lucide-react';
import { AuditFinding } from '../../types';
import { SeverityBadge, FindingTypeBadge, FindingCategoryBadge } from '../ui/AuditBadges';

interface FindingCardProps {
  finding: AuditFinding;
  index: number;
  onViewSource: (provision: AuditFinding['legalProvision']) => void;
  onReportFinding: (finding: AuditFinding) => void;
}

export function FindingCard({
  finding,
  index,
  onViewSource,
  onReportFinding
}: FindingCardProps) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden transition-shadow hover:shadow-xs">
      {/* Header Bar */}
      <div className="p-4 sm:p-5 flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="text-xs font-mono font-semibold text-slate-500 tabular-nums">
              #{index + 1}
            </span>
            <SeverityBadge severity={finding.severity} />
            <FindingTypeBadge type={finding.type} />
            <span className="text-slate-300">·</span>
            <FindingCategoryBadge category={finding.category} />
          </div>

          <h3 className="text-sm sm:text-base font-semibold text-slate-900 leading-snug">
            {finding.title}
          </h3>

          {finding.contractLocation && (
            <p className="mt-1 text-xs text-slate-500">
              Location: {finding.contractLocation}
            </p>
          )}
        </div>

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition-colors shrink-0"
          aria-label={isExpanded ? 'Collapse finding details' : 'Expand finding details'}
        >
          {isExpanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
        </button>
      </div>

      {isExpanded && (
        <div className="px-4 pb-5 sm:px-5 border-t border-slate-100 pt-4 space-y-4">
          {/* Contract Excerpt */}
          <div className="bg-slate-50 rounded-lg p-3.5 border border-slate-200">
            <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 mb-1.5">
              <Quote className="w-3.5 h-3.5 text-slate-500" />
              <span>Contract Excerpt Under Review</span>
            </div>
            <p className="text-xs text-slate-800 font-mono bg-white p-2.5 rounded border border-slate-200 leading-relaxed">
              "{finding.contractExcerpt}"
            </p>
          </div>

          {/* Legal Analysis Explanation */}
          <div>
            <h4 className="text-xs font-semibold text-slate-900 uppercase tracking-wider mb-1.5">
              Potential Legal Issue Analysis
            </h4>
            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">
              {finding.issueExplanation}
            </p>
          </div>

          {/* Supporting Legal Provision */}
          <div className="p-3.5 rounded-lg bg-emerald-50/50 border border-emerald-200">
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-emerald-900">
                <Scale className="w-4 h-4 text-emerald-700" />
                <span>
                  {finding.legalProvision.proclamationTitle} · {finding.legalProvision.articleNumber}
                  {finding.legalProvision.subArticle ? ` (${finding.legalProvision.subArticle})` : ''}
                </span>
              </div>
              <button
                onClick={() => onViewSource(finding.legalProvision)}
                className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-800 hover:text-emerald-950 hover:underline"
              >
                <span>View Full Article</span>
                <ExternalLink className="w-3 h-3" />
              </button>
            </div>
            <p className="text-xs text-emerald-950 font-serif italic leading-relaxed">
              "{finding.legalProvision.provisionText}"
            </p>
            <div className="mt-2 text-[10px] text-emerald-700">
              Effective Date: {finding.legalProvision.effectiveDate} · Federal Negarit Gazeta
            </div>
          </div>

          {/* Suggested Remedial Action */}
          <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200">
            <div className="text-xs font-semibold text-slate-900 mb-1">
              Recommended Remedial Action
            </div>
            <p className="text-xs text-slate-700 leading-relaxed">
              {finding.suggestedAction}
            </p>
          </div>

          {/* Card Footer: Confidence & Reporting */}
          <div className="pt-2 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500 border-t border-slate-100">
            <div className="flex items-center gap-2">
              <span className="text-[11px]">AI Provision Match Confidence:</span>
              <span className="font-mono font-medium text-slate-700 tabular-nums">
                {Math.round(finding.confidenceScore * 100)}%
              </span>
            </div>

            <div className="flex items-center gap-3">
              {finding.userReported ? (
                <span className="inline-flex items-center gap-1 text-[11px] text-amber-700 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  <CheckCircle className="w-3 h-3" />
                  <span>Report Under Human Review</span>
                </span>
              ) : (
                <button
                  onClick={() => onReportFinding(finding)}
                  className="inline-flex items-center gap-1 text-[11px] text-slate-500 hover:text-slate-800"
                >
                  <Flag className="w-3 h-3 text-slate-400" />
                  <span>Report Inaccuracy</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
