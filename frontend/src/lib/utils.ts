import { jsPDF } from 'jspdf';
import { AuditDocument, FindingSeverity, FindingType } from '../types';

export function cn(...inputs: (string | boolean | undefined | null | { [key: string]: boolean })[]): string {
  const classes: string[] = [];

  for (const input of inputs) {
    if (!input) continue;
    if (typeof input === 'string') {
      classes.push(input);
    } else if (typeof input === 'object') {
      for (const [key, value] of Object.entries(input)) {
        if (value) classes.push(key);
      }
    }
  }

  return classes.join(' ');
}

export function formatDate(dateStr?: string): string {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    });
  } catch {
    return dateStr;
  }
}

export function formatDateTime(dateStr?: string): string {
  if (!dateStr) return '—';
  try {
    const d = new Date(dateStr);
    return d.toLocaleString('en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateStr;
  }
}

export function formatBytes(bytes: number, decimals = 1): string {
  if (!+bytes) return '0 Bytes';
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

export function getSeverityStyles(severity: FindingSeverity) {
  switch (severity) {
    case 'CRITICAL':
      return {
        badgeBg: 'bg-rose-50 text-rose-700 border border-rose-200',
        text: 'text-rose-700',
        border: 'border-rose-300',
        label: 'Critical Risk'
      };
    case 'HIGH':
      return {
        badgeBg: 'bg-amber-50 text-amber-800 border border-amber-200',
        text: 'text-amber-800',
        border: 'border-amber-300',
        label: 'High Concern'
      };
    case 'MEDIUM':
      return {
        badgeBg: 'bg-yellow-50 text-yellow-800 border border-yellow-200',
        text: 'text-yellow-800',
        border: 'border-yellow-300',
        label: 'Medium Attention'
      };
    case 'LOW':
      return {
        badgeBg: 'bg-blue-50 text-blue-700 border border-blue-200',
        text: 'text-blue-700',
        border: 'border-blue-300',
        label: 'Low Priority'
      };
    case 'INFORMATIONAL':
    default:
      return {
        badgeBg: 'bg-slate-100 text-slate-700 border border-slate-200',
        text: 'text-slate-600',
        border: 'border-slate-200',
        label: 'Informational'
      };
  }
}

export function getFindingTypeLabel(type: FindingType): string {
  switch (type) {
    case 'POTENTIAL_LEGAL_CONFLICT':
      return 'Potential Legal Conflict';
    case 'MISSING_OR_INCOMPLETE_CLAUSE':
      return 'Missing or Incomplete Clause';
    case 'OUTDATED_OR_UNVERIFIED_REFERENCE':
      return 'Outdated Legal Reference';
    case 'INFORMATIONAL_OBSERVATION':
      return 'Informational Observation';
    case 'INSUFFICIENT_EVIDENCE':
      return 'Insufficient Evidence to Determine';
  }
}

export function generateAuditPdf(audit: AuditDocument): void {
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  let y = 20;

  // Header Banner
  doc.setFillColor(15, 23, 42); // deep navy #0f172a
  doc.rect(0, 0, pageWidth, 28, 'F');

  doc.setTextColor(255, 255, 255);
  doc.setFontSize(14);
  doc.setFont('helvetica', 'bold');
  doc.text('LEGALCHECK ETHIOPIA', 14, 14);

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(203, 213, 225);
  doc.text('Legal Compliance Audit Report · Labour Proclamation No. 1156/2019', 14, 21);

  y = 38;

  // Document Metadata Table
  doc.setTextColor(15, 23, 42);
  doc.setFontSize(16);
  doc.setFont('helvetica', 'bold');
  doc.text(audit.documentName, 14, y);
  y += 6;

  doc.setFontSize(9);
  doc.setFont('helvetica', 'normal');
  doc.setTextColor(100, 116, 139);
  doc.text(`Audit ID: ${audit.id}  |  Generated: ${formatDateTime(new Date().toISOString())}  |  Format: ${audit.fileFormat}`, 14, y);
  y += 10;

  // Summary box
  doc.setFillColor(248, 250, 252);
  doc.setDrawColor(226, 232, 240);
  doc.roundedRect(14, y, pageWidth - 28, 24, 2, 2, 'FD');

  doc.setFontSize(9);
  doc.setFont('helvetica', 'bold');
  doc.setTextColor(30, 41, 59);
  doc.text('AUDIT FINDINGS SUMMARY', 18, y + 7);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8);
  doc.setTextColor(71, 85, 105);
  const summaryLines = doc.splitTextToSize(audit.overallSummary || 'Audit analysis complete.', pageWidth - 36);
  doc.text(summaryLines, 18, y + 13);

  y += 32;

  // Stats Grid
  doc.setFontSize(9);
  doc.setFont('helvetica', 'bold');
  doc.text(`Total Issues Identified: ${audit.totalFindings} (Critical: ${audit.criticalCount}, High: ${audit.highCount}, Medium: ${audit.mediumCount}, Low: ${audit.lowCount})`, 14, y);
  y += 8;

  // Findings List
  if (audit.findings && audit.findings.length > 0) {
    audit.findings.forEach((f, idx) => {
      // Check page overflow
      if (y > 250) {
        doc.addPage();
        y = 20;
      }

      doc.setDrawColor(226, 232, 240);
      doc.setFillColor(255, 255, 255);
      doc.roundedRect(14, y, pageWidth - 28, 38, 2, 2, 'FD');

      // Title & Severity
      doc.setFontSize(9);
      doc.setFont('helvetica', 'bold');
      doc.setTextColor(15, 23, 42);
      doc.text(`${idx + 1}. ${f.title}`, 18, y + 6);

      doc.setFontSize(8);
      doc.setFont('helvetica', 'bold');
      if (f.severity === 'CRITICAL') doc.setTextColor(190, 18, 60);
      else if (f.severity === 'HIGH') doc.setTextColor(180, 83, 9);
      else doc.setTextColor(71, 85, 105);
      doc.text(`[${f.severity}] - ${getFindingTypeLabel(f.type)}`, 18, y + 11);

      // Excerpt & Provision
      doc.setFont('helvetica', 'normal');
      doc.setFontSize(7.5);
      doc.setTextColor(51, 65, 85);

      const lawText = `Citation: ${f.legalProvision.articleNumber}, ${f.legalProvision.proclamationTitle}`;
      doc.text(lawText, 18, y + 17);

      const recText = `Action: ${f.suggestedAction}`;
      const recLines = doc.splitTextToSize(recText, pageWidth - 38);
      doc.text(recLines, 18, y + 23);

      y += 42;
    });
  }

  // Legal Disclaimer Footer
  const footerY = doc.internal.pageSize.getHeight() - 14;
  doc.setFontSize(7);
  doc.setFont('helvetica', 'italic');
  doc.setTextColor(148, 163, 184);
  doc.text('Disclaimer: LegalCheck Ethiopia provides automated legal analysis based on Labour Proclamation No. 1156/2019. It does not constitute formal legal counsel.', 14, footerY);

  doc.save(`LegalCheck_Ethiopia_${audit.documentName.replace(/[^a-zA-Z0-9]/g, '_')}_Audit.pdf`);
}
