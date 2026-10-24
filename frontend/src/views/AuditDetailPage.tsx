import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  Download,
  Share2,
  AlertTriangle,
  Scale,
  Calendar,
  FileText,
  Clock,
  Filter,
  RefreshCw,
  Trash2,
  CheckCircle2,
  ShieldCheck,
  ChevronDown
} from 'lucide-react';
import { AuditDocument, AuditFinding, FindingSeverity, FindingType } from '../types';
import { AuditService } from '../services/audit.service';
import { formatDate, formatDateTime, formatBytes, generateAuditPdf } from '../lib/utils';
import { AuditStatusBadge, SeverityBadge, FindingTypeBadge } from '../components/ui/AuditBadges';
import { FindingCard } from '../components/audits/FindingCard';
import { LegalSourceModal } from '../components/ui/LegalSourceModal';
import { ReportFindingDialog, ConfirmDialog, LoadingSkeleton, EmptyState } from '../components/ui/FeedbackModals';

interface AuditDetailPageProps {
  auditId: string;
  onNavigate: (path: string) => void;
}

export function AuditDetailPage({ auditId, onNavigate }: AuditDetailPageProps) {
  const [audit, setAudit] = useState<AuditDocument | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [typeFilter, setTypeFilter] = useState<string>('ALL');
  const [categoryFilter, setCategoryFilter] = useState<string>('ALL');

  // Modals state
  const [selectedProvision, setSelectedProvision] = useState<AuditFinding['legalProvision'] | null>(null);
  const [reportingFinding, setReportingFinding] = useState<AuditFinding | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isExportingPdf, setIsExportingPdf] = useState(false);

  const fetchAuditData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await AuditService.getAudit(auditId);
      if (!data) {
        setError('Audit report not found or removed.');
      } else {
        setAudit(data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retrieve audit details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditData();
  }, [auditId]);

  useEffect(() => {
    if (!audit || !['PENDING', 'ANALYZING', 'EXTRACTING_PROVISIONS'].includes(audit.status)) {
      return;
    }

    const intervalId = window.setInterval(async () => {
      try {
        const updated = await AuditService.getAudit(auditId);
        if (updated) setAudit(updated);
      } catch (err) {
        console.error('Failed to refresh audit status', err);
      }
    }, 5000);

    return () => window.clearInterval(intervalId);
  }, [audit?.status, auditId]);

  const handleExportPdf = () => {
    if (!audit) return;
    setIsExportingPdf(true);
    try {
      generateAuditPdf(audit);
    } catch (e) {
      console.error(e);
    } finally {
      setIsExportingPdf(false);
    }
  };

  const handleDeleteAudit = async () => {
    if (!audit) return;
    await AuditService.deleteAudit(audit.id);
    setShowDeleteConfirm(false);
    onNavigate('/audits');
  };

  const handleReportFindingSubmit = async (note: string) => {
    if (!audit || !reportingFinding) return;
    await AuditService.reportIncorrectFinding(audit.id, reportingFinding.id, note);
    await fetchAuditData();
  };

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6">
        <LoadingSkeleton count={4} />
      </div>
    );
  }

  if (error || !audit) {
    return (
      <div className="max-w-4xl mx-auto py-12 px-4">
        <EmptyState
          title="Audit Report Not Available"
          description={error || 'The requested audit ID does not exist or has been deleted.'}
          actionLabel="Return to Audit History"
          onAction={() => onNavigate('/audits')}
        />
      </div>
    );
  }

  // Filter findings
  const findings = audit.findings || [];
  const filteredFindings = findings.filter(f => {
    if (severityFilter !== 'ALL' && f.severity !== severityFilter) return false;
    if (typeFilter !== 'ALL' && f.type !== typeFilter) return false;
    if (categoryFilter !== 'ALL' && f.category !== categoryFilter) return false;
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 space-y-6">
      {/* Top Bar Navigation & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <button
          onClick={() => onNavigate('/audits')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-900 focus:outline-none"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Audits List</span>
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="p-2 text-slate-400 hover:text-rose-600 rounded-lg border border-slate-200 bg-white hover:bg-rose-50 transition-colors"
            title="Delete this audit record"
          >
            <Trash2 className="w-4 h-4" />
          </button>
          <button
            onClick={handleExportPdf}
            disabled={isExportingPdf}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-xs transition-colors"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Download Audit PDF</span>
          </button>
        </div>
      </div>

      {/* Document Overview Header Card */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-6">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span className="font-mono font-medium text-slate-700">{audit.id}</span>
              <span>·</span>
              <AuditStatusBadge status={audit.status} />
              <span>·</span>
              <span>Audited on {formatDateTime(audit.createdAt)}</span>
            </div>

            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
              {audit.documentName}
            </h1>

            {audit.description && (
              <p className="text-xs sm:text-sm text-slate-600 max-w-2xl">
                {audit.description}
              </p>
            )}

            <div className="flex flex-wrap items-center gap-4 pt-2 text-xs text-slate-500">
              <div className="flex items-center gap-1.5">
                <FileText className="w-4 h-4 text-slate-400" />
                <span>Format: {audit.fileFormat} ({formatBytes(audit.fileSize)})</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Scale className="w-4 h-4 text-emerald-600" />
                <span className="text-slate-700 font-medium">Labour Proclamation No. 1156/2019</span>
              </div>
            </div>
          </div>

          {/* Issue Counts Summary Matrix */}
          <div className="grid grid-cols-4 gap-2 sm:gap-3 bg-slate-50 p-3 rounded-lg border border-slate-200 text-center shrink-0">
            <div className="px-2">
              <div className="text-[11px] font-semibold text-rose-700">Critical</div>
              <div className="text-lg font-bold font-mono text-rose-800 tabular-nums">
                {audit.criticalCount}
              </div>
            </div>
            <div className="px-2 border-l border-slate-200">
              <div className="text-[11px] font-semibold text-amber-700">High</div>
              <div className="text-lg font-bold font-mono text-amber-800 tabular-nums">
                {audit.highCount}
              </div>
            </div>
            <div className="px-2 border-l border-slate-200">
              <div className="text-[11px] font-semibold text-yellow-700">Medium</div>
              <div className="text-lg font-bold font-mono text-yellow-800 tabular-nums">
                {audit.mediumCount}
              </div>
            </div>
            <div className="px-2 border-l border-slate-200">
              <div className="text-[11px] font-semibold text-slate-600">Total</div>
              <div className="text-lg font-bold font-mono text-slate-900 tabular-nums">
                {audit.totalFindings}
              </div>
            </div>
          </div>
        </div>

        {/* Overall Legal Assessment Box */}
        {audit.overallSummary && (
          <div className="mt-6 p-4 rounded-lg bg-slate-50 border border-slate-200">
            <div className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-1">
              Overall Legal Compliance Finding Summary
            </div>
            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed">
              {audit.overallSummary}
            </p>
          </div>
        )}
      </div>

      {/* Filter and Control Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5 text-slate-500 font-medium">
            <Filter className="w-3.5 h-3.5" />
            <span>Filter By:</span>
          </div>

          {/* Severity selector */}
          <select
            value={severityFilter}
            onChange={e => setSeverityFilter(e.target.value)}
            className="text-xs rounded-lg border border-slate-200 p-1.5 bg-slate-50 text-slate-800 focus:outline-none"
          >
            <option value="ALL">All Severities ({findings.length})</option>
            <option value="CRITICAL">Critical Only ({audit.criticalCount})</option>
            <option value="HIGH">High Only ({audit.highCount})</option>
            <option value="MEDIUM">Medium Only ({audit.mediumCount})</option>
            <option value="LOW">Low Priority ({audit.lowCount})</option>
          </select>

          {/* Type selector */}
          <select
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value)}
            className="text-xs rounded-lg border border-slate-200 p-1.5 bg-slate-50 text-slate-800 focus:outline-none"
          >
            <option value="ALL">All Finding Types</option>
            <option value="POTENTIAL_LEGAL_CONFLICT">Potential Legal Conflict</option>
            <option value="MISSING_OR_INCOMPLETE_CLAUSE">Missing/Incomplete Clause</option>
            <option value="OUTDATED_OR_UNVERIFIED_REFERENCE">Outdated Reference</option>
            <option value="INFORMATIONAL_OBSERVATION">Informational</option>
          </select>
        </div>

        <div className="text-xs text-slate-500 font-mono">
          Showing {filteredFindings.length} of {findings.length} findings
        </div>
      </div>

      {/* Findings List */}
      {filteredFindings.length > 0 ? (
        <div className="space-y-4">
          {filteredFindings.map((finding, idx) => (
            <FindingCard
              key={finding.id}
              finding={finding}
              index={idx}
              onViewSource={prov => setSelectedProvision(prov)}
              onReportFinding={fnd => setReportingFinding(fnd)}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title="No Matching Findings"
          description="No compliance findings match your active filters. Try selecting 'All Severities' or reset filter criteria."
          actionLabel="Reset Filters"
          onAction={() => {
            setSeverityFilter('ALL');
            setTypeFilter('ALL');
            setCategoryFilter('ALL');
          }}
        />
      )}

      {/* Legal Source Proclamation Modal */}
      <LegalSourceModal
        isOpen={!!selectedProvision}
        provision={selectedProvision}
        onClose={() => setSelectedProvision(null)}
        onNavigateToFullSource={sourceId => onNavigate(`/legal-sources/${sourceId}`)}
      />

      {/* Report Finding Dialog */}
      <ReportFindingDialog
        isOpen={!!reportingFinding}
        findingTitle={reportingFinding?.title || ''}
        onClose={() => setReportingFinding(null)}
        onSubmitReport={handleReportFindingSubmit}
      />

      {/* Safe Delete Confirm Dialog */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="Delete Compliance Audit Record"
        description="Are you sure you want to delete this compliance report? This action cannot be undone. Exported PDF reports will remain on your device."
        confirmLabel="Yes, Delete Audit"
        cancelLabel="Cancel"
        variant="danger"
        onConfirm={handleDeleteAudit}
        onCancel={() => setShowDeleteConfirm(false)}
      />
    </div>
  );
}
