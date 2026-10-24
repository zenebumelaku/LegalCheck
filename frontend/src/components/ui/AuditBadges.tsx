import React from 'react';
import { AuditStatus, FindingSeverity, FindingCategory, FindingType } from '../../types';
import { getSeverityStyles, getFindingTypeLabel } from '../../lib/utils';
import { AlertCircle, AlertTriangle, CheckCircle2, Clock, Info, ShieldAlert } from 'lucide-react';

export function AuditStatusBadge({ status }: { status: AuditStatus }) {
  switch (status) {
    case 'COMPLETED':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
          <span>Completed</span>
        </span>
      );
    case 'ANALYZING':
    case 'EXTRACTING_PROVISIONS':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md bg-blue-50 text-blue-800 border border-blue-200">
          <Clock className="w-3.5 h-3.5 text-blue-600 animate-spin" />
          <span>Processing Provisions</span>
        </span>
      );
    case 'PENDING':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md bg-slate-100 text-slate-700 border border-slate-200">
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          <span>Queued</span>
        </span>
      );
    case 'FAILED':
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-md bg-rose-50 text-rose-800 border border-rose-200">
          <AlertCircle className="w-3.5 h-3.5 text-rose-600" />
          <span>Analysis Failed</span>
        </span>
      );
    default:
      return null;
  }
}

export function SeverityBadge({ severity }: { severity: FindingSeverity }) {
  const styles = getSeverityStyles(severity);

  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 text-xs font-semibold rounded ${styles.badgeBg}`}>
      {severity === 'CRITICAL' && <ShieldAlert className="w-3 h-3 text-rose-600 shrink-0" />}
      {severity === 'HIGH' && <AlertTriangle className="w-3 h-3 text-amber-600 shrink-0" />}
      {severity === 'MEDIUM' && <AlertCircle className="w-3 h-3 text-yellow-600 shrink-0" />}
      {severity === 'LOW' && <Info className="w-3 h-3 text-blue-600 shrink-0" />}
      {severity === 'INFORMATIONAL' && <Info className="w-3 h-3 text-slate-500 shrink-0" />}
      <span>{styles.label}</span>
    </span>
  );
}

export function FindingTypeBadge({ type }: { type: FindingType }) {
  const label = getFindingTypeLabel(type);
  let bg = 'bg-slate-100 text-slate-700 border-slate-200';
  if (type === 'POTENTIAL_LEGAL_CONFLICT') bg = 'bg-rose-50 text-rose-800 border-rose-200';
  else if (type === 'MISSING_OR_INCOMPLETE_CLAUSE') bg = 'bg-amber-50 text-amber-800 border-amber-200';
  else if (type === 'OUTDATED_OR_UNVERIFIED_REFERENCE') bg = 'bg-orange-50 text-orange-800 border-orange-200';

  return (
    <span className={`inline-flex items-center px-2 py-0.5 text-[11px] font-medium rounded border ${bg}`}>
      {label}
    </span>
  );
}

export function FindingCategoryBadge({ category }: { category: FindingCategory }) {
  const labels: Record<FindingCategory, string> = {
    PROBATION: 'Probation Clause',
    WORKING_HOURS: 'Working Hours & Overtime',
    LEAVES_AND_REST: 'Leaves & Weekly Rest',
    MATERNITY_AND_WOMEN: 'Maternity & Special Protections',
    TERMINATION_AND_SEVERANCE: 'Termination & Severance',
    REMUNERATION_AND_DEDUCTIONS: 'Remuneration & Deductions',
    SAFETY_AND_HEALTH: 'Occupational Safety (PPE)',
    DISPUTE_RESOLUTION: 'Dispute Settlement',
    GENERAL_CONTRACT_TERMS: 'Contract Form & Citation'
  };

  return (
    <span className="text-xs text-slate-600 font-medium">
      {labels[category] || category}
    </span>
  );
}
