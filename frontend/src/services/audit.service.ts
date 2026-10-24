import { AuditDocument, AuditFinding, AuditStatistics } from '../types';
import { SAMPLE_ETHIOPIAN_CONTRACTS } from '../data/sample-contracts';
import { auditContractText } from '../data/audit-rules-engine';
import { apiRequest } from '../lib/api-client';

const STORAGE_KEY = 'lc_audits_repository_v1';

// Seed initial realistic audit items
const INITIAL_SEED_AUDITS: AuditDocument[] = (() => {
  const seed1Id = 'aud-eth-2026-001';
  const contract1 = SAMPLE_ETHIOPIAN_CONTRACTS[0];
  const audit1Res = auditContractText(seed1Id, contract1.content, {
    checkLegalConflicts: true,
    checkMissingClauses: true,
    checkOutdatedReferences: true
  });

  const seed2Id = 'aud-eth-2026-002';
  const contract2 = SAMPLE_ETHIOPIAN_CONTRACTS[2];
  const audit2Res = auditContractText(seed2Id, contract2.content, {
    checkLegalConflicts: true,
    checkMissingClauses: true,
    checkOutdatedReferences: true
  });

  return [
    {
      id: seed1Id,
      userId: 'usr_eth_991',
      documentName: 'Tech_Lead_Employment_Agreement_2026.docx',
      documentType: 'EMPLOYMENT_CONTRACT',
      documentLanguage: 'ENGLISH',
      fileSize: 48200,
      fileFormat: 'DOCX',
      createdAt: '2026-10-21T09:14:00Z',
      updatedAt: '2026-10-21T09:15:20Z',
      completedAt: '2026-10-21T09:15:20Z',
      status: 'COMPLETED',
      progressPercent: 100,
      reviewOptions: {
        checkLegalConflicts: true,
        checkMissingClauses: true,
        checkOutdatedReferences: true
      },
      description: 'Standard technical lead contract for Addis Tech Solutions PLC engineering department.',
      overallSummary: audit1Res.summary,
      totalFindings: audit1Res.findings.length,
      criticalCount: audit1Res.findings.filter(f => f.severity === 'CRITICAL').length,
      highCount: audit1Res.findings.filter(f => f.severity === 'HIGH').length,
      mediumCount: audit1Res.findings.filter(f => f.severity === 'MEDIUM').length,
      lowCount: audit1Res.findings.filter(f => f.severity === 'LOW').length,
      infoCount: audit1Res.findings.filter(f => f.severity === 'INFORMATIONAL').length,
      findings: audit1Res.findings,
      rawTextPreview: contract1.content
    },
    {
      id: seed2Id,
      userId: 'usr_eth_991',
      documentName: 'Abyssinia_Logistics_Account_Exec.pdf',
      documentType: 'EMPLOYMENT_CONTRACT',
      documentLanguage: 'ENGLISH',
      fileSize: 112400,
      fileFormat: 'PDF',
      createdAt: '2026-10-22T14:30:00Z',
      updatedAt: '2026-10-22T14:31:10Z',
      completedAt: '2026-10-22T14:31:10Z',
      status: 'COMPLETED',
      progressPercent: 100,
      reviewOptions: {
        checkLegalConflicts: true,
        checkMissingClauses: true,
        checkOutdatedReferences: true
      },
      description: 'Commercial sales staff employment agreement based on Proclamation 1156/2019 standards.',
      overallSummary: audit2Res.summary,
      totalFindings: audit2Res.findings.length,
      criticalCount: audit2Res.findings.filter(f => f.severity === 'CRITICAL').length,
      highCount: audit2Res.findings.filter(f => f.severity === 'HIGH').length,
      mediumCount: audit2Res.findings.filter(f => f.severity === 'MEDIUM').length,
      lowCount: audit2Res.findings.filter(f => f.severity === 'LOW').length,
      infoCount: audit2Res.findings.filter(f => f.severity === 'INFORMATIONAL').length,
      findings: audit2Res.findings,
      rawTextPreview: contract2.content
    }
  ];
})();

export class AuditService {
  private static getStoredAudits(): AuditDocument[] {
    if (typeof window === 'undefined') return INITIAL_SEED_AUDITS;
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      if (!data) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(INITIAL_SEED_AUDITS));
        return INITIAL_SEED_AUDITS;
      }
      return JSON.parse(data);
    } catch {
      return INITIAL_SEED_AUDITS;
    }
  }

  private static saveAudits(audits: AuditDocument[]): void {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(audits));
      } catch (e) {
        console.error('Failed to save audits to storage', e);
      }
    }
  }

  static async listAudits(params?: {
    query?: string;
    status?: string;
    documentType?: string;
    sortBy?: 'date_desc' | 'date_asc' | 'findings_desc';
  }): Promise<AuditDocument[]> {
    try {
      return await apiRequest<AuditDocument[]>('/api/v1/audits', {
        params: params as Record<string, string>
      });
    } catch {
      let audits = this.getStoredAudits();

      if (params?.status && params.status !== 'ALL') {
        audits = audits.filter(a => a.status === params.status);
      }

      if (params?.documentType && params.documentType !== 'ALL') {
        audits = audits.filter(a => a.documentType === params.documentType);
      }

      if (params?.query) {
        const q = params.query.toLowerCase();
        audits = audits.filter(
          a =>
            a.documentName.toLowerCase().includes(q) ||
            (a.description && a.description.toLowerCase().includes(q))
        );
      }

      // Sort
      const sortBy = params?.sortBy || 'date_desc';
      audits.sort((a, b) => {
        if (sortBy === 'date_asc') {
          return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        }
        if (sortBy === 'findings_desc') {
          return b.totalFindings - a.totalFindings;
        }
        return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
      });

      return audits;
    }
  }

  static async getAudit(id: string): Promise<AuditDocument | null> {
    try {
      return await apiRequest<AuditDocument>(`/api/v1/audits/${id}`);
    } catch {
      const audits = this.getStoredAudits();
      const audit = audits.find(a => a.id === id);
      return audit || null;
    }
  }

  static async createAudit(payload: {
    documentName: string;
    documentType: AuditDocument['documentType'];
    documentLanguage: AuditDocument['documentLanguage'];
    fileSize: number;
    fileFormat: AuditDocument['fileFormat'];
    reviewOptions: AuditDocument['reviewOptions'];
    description?: string;
    rawText: string;
  }): Promise<AuditDocument> {
    const auditId = `aud-eth-${Date.now().toString().slice(-6)}`;

    // Try backend upload
    try {
      return await apiRequest<AuditDocument>('/api/v1/audits', {
        method: 'POST',
        body: JSON.stringify({ ...payload, id: auditId })
      });
    } catch {
      // Local analysis execution
      const analysis = auditContractText(auditId, payload.rawText, payload.reviewOptions);

      const criticalCount = analysis.findings.filter(f => f.severity === 'CRITICAL').length;
      const highCount = analysis.findings.filter(f => f.severity === 'HIGH').length;
      const mediumCount = analysis.findings.filter(f => f.severity === 'MEDIUM').length;
      const lowCount = analysis.findings.filter(f => f.severity === 'LOW').length;
      const infoCount = analysis.findings.filter(f => f.severity === 'INFORMATIONAL').length;

      const newAudit: AuditDocument = {
        id: auditId,
        userId: 'usr_eth_991',
        documentName: payload.documentName,
        documentType: payload.documentType,
        documentLanguage: payload.documentLanguage,
        fileSize: payload.fileSize,
        fileFormat: payload.fileFormat,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        completedAt: new Date().toISOString(),
        status: 'COMPLETED',
        progressPercent: 100,
        reviewOptions: payload.reviewOptions,
        description: payload.description,
        overallSummary: analysis.summary,
        totalFindings: analysis.findings.length,
        criticalCount,
        highCount,
        mediumCount,
        lowCount,
        infoCount,
        findings: analysis.findings,
        rawTextPreview: payload.rawText
      };

      const existing = this.getStoredAudits();
      this.saveAudits([newAudit, ...existing]);

      return newAudit;
    }
  }

  static async deleteAudit(id: string): Promise<boolean> {
    try {
      await apiRequest(`/api/v1/audits/${id}`, { method: 'DELETE' });
    } catch {
      // Ignore
    }
    const current = this.getStoredAudits().filter(a => a.id !== id);
    this.saveAudits(current);
    return true;
  }

  static async reportIncorrectFinding(auditId: string, findingId: string, note: string): Promise<boolean> {
    try {
      await apiRequest(`/api/v1/audits/${auditId}/findings/${findingId}/report`, {
        method: 'POST',
        body: JSON.stringify({ note })
      });
      return true;
    } catch {
      const audits = this.getStoredAudits();
      const audit = audits.find(a => a.id === auditId);
      if (audit && audit.findings) {
        const finding = audit.findings.find(f => f.id === findingId);
        if (finding) {
          finding.userReported = true;
          finding.userReportNote = note;
          this.saveAudits(audits);
        }
      }
      return true;
    }
  }

  static async getStatistics(): Promise<AuditStatistics> {
    try {
      return await apiRequest<AuditStatistics>('/api/v1/audits/statistics');
    } catch {
      const audits = this.getStoredAudits();
      const total = audits.length;
      const completed = audits.filter(a => a.status === 'COMPLETED').length;
      const awaiting = audits.filter(a => a.status === 'PENDING' || a.status === 'ANALYZING').length;
      const critical = audits.reduce((sum, a) => sum + (a.criticalCount || 0), 0);

      // Audits with 0 critical issues count as fully compliant
      const compliant = audits.filter(a => a.criticalCount === 0).length;
      const complianceRate = total > 0 ? Math.round((compliant / total) * 100) : 100;

      return {
        totalAudits: total,
        completedAudits: completed,
        awaitingAudits: awaiting,
        criticalIssuesFound: critical,
        complianceRate
      };
    }
  }
}
