import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Flag,
  Quote,
  Scale
} from 'lucide-react';
import { AuditFinding } from '../../types';
import { SeverityBadge, FindingTypeBadge, FindingCategoryBadge } from '../ui/AuditBadges';

interface FindingCardProps {
  finding: AuditFinding;
  index: number;
  demoOnly?: boolean;
  onReportFinding: (finding: AuditFinding) => void;
}

export function FindingCard({
  finding,
  index,
  demoOnly = false,
  onReportFinding
}: FindingCardProps) {
  const [isExpanded, setIsExpanded] = useState(true);
  const citations = finding.citations ?? [];
  const hasValidatedCitation =
    finding.evidenceAssessment === 'supporting' && citations.length > 0;

  return (
    <article className="overflow-hidden rounded-xl border border-slate-200 bg-white transition-shadow hover:shadow-xs">
      <div className="flex items-start justify-between gap-4 p-4 sm:p-5">
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="text-xs font-mono font-semibold tabular-nums text-slate-500">
              #{index + 1}
            </span>
            <SeverityBadge severity={finding.severity} />
            <FindingTypeBadge type={finding.type} />
            <span className="text-slate-300">·</span>
            <FindingCategoryBadge category={finding.category} />
            {finding.evidenceAssessment && (
              <span
                className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                  hasValidatedCitation
                    ? 'bg-emerald-100 text-emerald-900'
                    : 'bg-amber-100 text-amber-950'
                }`}
              >
                {hasValidatedCitation
                  ? 'Retrieved evidence cited'
                  : 'Insufficient validated evidence'}
              </span>
            )}
          </div>

          <h3 className="text-sm font-semibold leading-snug text-slate-900 sm:text-base">
            {finding.title}
          </h3>
          {finding.contractLocation && (
            <p className="mt-1 text-xs text-slate-500">
              Contract location: {finding.contractLocation}
            </p>
          )}
        </div>

        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="shrink-0 rounded-lg p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
          aria-label={isExpanded ? 'Collapse finding details' : 'Expand finding details'}
          aria-expanded={isExpanded}
        >
          {isExpanded ? <ChevronUp aria-hidden="true" className="h-5 w-5" /> : <ChevronDown aria-hidden="true" className="h-5 w-5" />}
        </button>
      </div>

      {isExpanded && (
        <div className="space-y-4 border-t border-slate-100 px-4 pb-5 pt-4 sm:px-5">
          {demoOnly && (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs leading-5 text-amber-950" role="note">
              <strong>DEMO ONLY — unverified client-side rule match.</strong> This illustrative result is not backend legal analysis and must not be relied on as a legal conclusion.
            </div>
          )}

          <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5">
            <div className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold text-slate-700">
              <Quote aria-hidden="true" className="h-3.5 w-3.5 text-slate-500" />
              Contract excerpt under review
            </div>
            <p className="rounded border border-slate-200 bg-white p-2.5 font-mono text-xs leading-relaxed text-slate-800">
              “{finding.contractExcerpt}”
            </p>
          </div>

          <div>
            <h4 className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-slate-900">
              Review notes
            </h4>
            <p className="text-xs leading-relaxed text-slate-700 sm:text-sm">
              {finding.issueExplanation}
            </p>
          </div>

          {citations.length > 0 ? (
            <section className="space-y-3 rounded-lg border border-emerald-200 bg-emerald-50/50 p-3.5" aria-label="Retrieved evidence citations">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold text-emerald-950">
                <Scale aria-hidden="true" className="h-4 w-4 text-emerald-800" />
                Retrieved evidence cited by the backend
              </h4>
              {citations.map((citation, citationIndex) => (
                <div
                  key={`${citation.sourceId}-${citation.articleNumber}-${citationIndex}`}
                  className="rounded-md border border-emerald-100 bg-white p-3"
                >
                  <p className="text-xs font-semibold text-slate-900">
                    {citation.sourceTitle} · Article {citation.articleNumber}
                    {citation.subArticle ? ` (${citation.subArticle})` : ''}
                  </p>
                  {citation.versionLabel && (
                    <p className="mt-1 text-[11px] text-slate-500">
                      Source version: {citation.versionLabel}
                    </p>
                  )}
                  {citation.supportingQuote && (
                    <blockquote className="mt-2 border-l-2 border-emerald-300 pl-3 text-xs leading-relaxed text-slate-700">
                      “{citation.supportingQuote}”
                    </blockquote>
                  )}
                  {citation.sourceUrl && (
                    <a
                      className="mt-2 inline-flex min-h-9 items-center gap-1 text-xs font-medium text-emerald-900 underline underline-offset-2 hover:text-emerald-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
                      href={citation.sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      Open cited source
                      <ExternalLink aria-hidden="true" className="h-3 w-3" />
                    </a>
                  )}
                </div>
              ))}
            </section>
          ) : finding.legalProvision ? (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-3.5">
              <h4 className="flex items-center gap-1.5 text-xs font-semibold text-amber-950">
                <AlertTriangle aria-hidden="true" className="h-4 w-4" />
                Demo rule reference — not verified evidence
              </h4>
              <p className="mt-2 text-xs font-medium text-amber-950">
                {finding.legalProvision.proclamationTitle} · {finding.legalProvision.articleNumber}
                {finding.legalProvision.subArticle
                  ? ` (${finding.legalProvision.subArticle})`
                  : ''}
              </p>
              <blockquote className="mt-2 text-xs italic leading-relaxed text-amber-950">
                “{finding.legalProvision.provisionText}”
              </blockquote>
            </div>
          ) : (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs leading-5 text-amber-950">
              <strong>No validated citation is available.</strong> This item is not evidence of a legal violation.
            </div>
          )}

          {finding.suggestedAction && (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-3.5">
              <div className="mb-1 text-xs font-semibold text-slate-900">
                Suggested next step (not legal advice)
              </div>
              <p className="text-xs leading-relaxed text-slate-700">
                {finding.suggestedAction}
              </p>
            </div>
          )}

          {!demoOnly && (
            <div className="flex flex-wrap items-center justify-end gap-3 border-t border-slate-100 pt-3 text-xs text-slate-500">
              {finding.userReported ? (
                <span className="inline-flex items-center gap-1 rounded border border-amber-200 bg-amber-50 px-2 py-0.5 text-[11px] text-amber-800">
                  <CheckCircle aria-hidden="true" className="h-3 w-3" />
                  Report Under Human Review
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => onReportFinding(finding)}
                  className="inline-flex min-h-9 items-center gap-1 text-[11px] text-slate-600 hover:text-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
                >
                  <Flag aria-hidden="true" className="h-3 w-3" />
                  Report inaccuracy
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </article>
  );
}
