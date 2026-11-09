import { AuditDocument, AuditFinding, AuditStatistics, FindingSeverity, FindingType } from '../types';
import { SAMPLE_ETHIOPIAN_CONTRACTS } from '../data/sample-contracts';
import { auditContractText } from '../data/audit-rules-engine';
import { apiRequest, isDemoFallbackEnabled } from '../lib/api-client';

const STORAGE_KEY = 'lc_audits_repository_v1';

interface BackendDocument {
  id: string;
  original_filename: string;
  file_size: number;
  content_type: string;
  document_type: string | null;
}

interface BackendFinding {
  id?: string;
  category?: string;
  severity?: string;
  clause_id?: string;
  clause_text?: string;
  explanation?: string;
  recommended_action?: string | null;
  evidence_assessment?: AuditFinding['evidenceAssessment'];
  model_confidence?: number | null;
  citations?: {
    source_id: string;
    source_title: string;
    source_url?: string | null;
    version_label?: string | null;
    article_number: string;
    sub_article_reference?: string | null;
    supporting_quote?: string | null;
    relevance_information?: string | null;
  }[];
}

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
      isDemoOnly: true,
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
      isDemoOnly: true,
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

function normalizeAuditStatus(status: string | undefined): AuditDocument['status'] {
  const value = (status ?? '').toLowerCase();
  switch (value) {
    case 'queued':
      return 'PENDING';
    case 'extracting':
    case 'retrieving_sources':
    case 'generating_report':
      return 'EXTRACTING_PROVISIONS';
    case 'analyzing':
      return 'ANALYZING';
    case 'completed':
      return 'COMPLETED';
    case 'failed':
      return 'FAILED';
    default:
      return 'PENDING';
  }
}

function normalizeSeverity(value: string): FindingSeverity {
  switch ((value || '').toLowerCase()) {
    case 'critical':
      return 'CRITICAL';
    case 'high':
      return 'HIGH';
    case 'medium':
      return 'MEDIUM';
    case 'low':
      return 'LOW';
    default:
      return 'INFORMATIONAL';
  }
}

function normalizeFindingType(value: string): FindingType {
  switch ((value || '').toUpperCase().replace(/[-\s]+/g, '_')) {
    case 'POTENTIAL_LEGAL_CONFLICT':
      return 'POTENTIAL_LEGAL_CONFLICT';
    case 'MISSING_INFORMATION':
      return 'MISSING_OR_INCOMPLETE_CLAUSE';
    case 'OUTDATED_LEGAL_REFERENCE':
      return 'OUTDATED_OR_UNVERIFIED_REFERENCE';
    case 'INFORMATIONAL_OBSERVATION':
      return 'INFORMATIONAL_OBSERVATION';
    case 'INSUFFICIENT_EVIDENCE':
      return 'INSUFFICIENT_EVIDENCE';
    default:
      return 'POTENTIAL_LEGAL_CONFLICT';
  }
}

function normalizeFindingCategory(value: string): AuditFinding['category'] {
  switch ((value || '').toUpperCase().replace(/[-\s]+/g, '_')) {
    case 'PROBATION':
      return 'PROBATION';
    case 'WORKING_HOURS':
      return 'WORKING_HOURS';
    case 'LEAVE':
    case 'LEAVES_AND_REST':
      return 'LEAVES_AND_REST';
    case 'MATERNITY':
    case 'MATERNITY_AND_WOMEN':
      return 'MATERNITY_AND_WOMEN';
    case 'TERMINATION':
    case 'TERMINATION_AND_SEVERANCE':
      return 'TERMINATION_AND_SEVERANCE';
    case 'COMPENSATION':
      return 'REMUNERATION_AND_DEDUCTIONS';
    case 'CONFIDENTIALITY':
      return 'GENERAL_CONTRACT_TERMS';
    case 'SIGNATURES':
      return 'GENERAL_CONTRACT_TERMS';
    case 'DURATION':
      return 'GENERAL_CONTRACT_TERMS';
    case 'NOTICE':
      return 'GENERAL_CONTRACT_TERMS';
    default:
      return 'GENERAL_CONTRACT_TERMS';
  }
}

export function assertDemoInputIsSynthetic(
  demoEnabled: boolean,
  isSample: boolean
): void {
  if (demoEnabled && !isSample) {
    throw new Error(
      'Demo mode accepts only synthetic sample contracts. Disable demo mode to upload a private contract to the authenticated backend.'
    );
  }
}

export class AuditService {
  private static getStoredAudits(): AuditDocument[] {
    if (typeof window === 'undefined') return INITIAL_SEED_AUDITS;
    try {
      const data = localStorage.getItem(STORAGE_KEY);
      if (!data) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(INITIAL_SEED_AUDITS));
        return INITIAL_SEED_AUDITS;
      }
      const savedAudits = JSON.parse(data) as AuditDocument[];
      const demoAudits = savedAudits.filter(audit => audit.isDemoOnly === true);
      if (demoAudits.length === 0) {
        this.saveAudits(INITIAL_SEED_AUDITS);
        return INITIAL_SEED_AUDITS;
      }
      if (demoAudits.length !== savedAudits.length) {
        this.saveAudits(demoAudits);
      }
      return demoAudits;
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

  static mapBackendFinding(
    finding: BackendFinding,
    index: number,
    auditId = 'backend-audit'
  ): AuditFinding {
    const citations = (finding.citations ?? []).map(citation => ({
      sourceId: citation.source_id,
      sourceTitle: citation.source_title,
      sourceUrl: citation.source_url ?? undefined,
      versionLabel: citation.version_label ?? undefined,
      articleNumber: citation.article_number,
      subArticle: citation.sub_article_reference ?? undefined,
      supportingQuote: citation.supporting_quote ?? undefined,
      relevanceInformation: citation.relevance_information ?? undefined
    }));
    const evidenceAssessment =
      finding.evidence_assessment === 'supporting' && citations.length > 0
        ? 'supporting'
        : 'insufficient';
    const userFacingCategory = normalizeFindingCategory(finding.category ?? finding.clause_id ?? 'general_contract_terms');

    return {
      id: String(finding.id ?? `${index}`),
      auditId,
      title: evidenceAssessment === 'supporting'
        ? (finding.clause_id ?? `Finding ${index + 1}`).replace(/_/g, ' ')
        : 'Insufficient evidence for a legal conclusion',
      severity: evidenceAssessment === 'supporting'
        ? normalizeSeverity(finding.severity ?? 'informational')
        : 'INFORMATIONAL',
      type: evidenceAssessment === 'supporting'
        ? normalizeFindingType(finding.category ?? 'potential_legal_conflict')
        : 'INSUFFICIENT_EVIDENCE',
      category: userFacingCategory,
      contractExcerpt: finding.clause_text ?? 'No contract excerpt was provided.',
      issueExplanation: finding.explanation ?? 'No explanation was provided by the audit engine.',
      evidenceAssessment,
      citations,
      suggestedAction: finding.recommended_action ?? 'Have a qualified Ethiopian legal professional review this issue.',
      userReported: false,
      userReportNote: undefined
    };
  }

  private static mapBackendAudit(item: any): AuditDocument {
    const status = normalizeAuditStatus(item.audit_status ?? item.status);
    const reviewOptions = {
      checkLegalConflicts: Boolean(item.review_options?.jurisdiction || item.review_options?.source_type),
      checkMissingClauses: Boolean(item.review_options?.language || item.review_options?.law_number),
      checkOutdatedReferences: Boolean(item.review_options?.review_date || item.review_options?.source_type)
    };

    return {
      id: String(item.id),
      isDemoOnly: false,
      userId: String(item.requested_by ?? 'unknown-user'),
      documentName: item.document_id ? `Document ${String(item.document_id).slice(0, 8)}` : 'Audit document',
      documentType: 'EMPLOYMENT_CONTRACT',
      documentLanguage: 'ENGLISH',
      fileSize: 0,
      fileFormat: 'PDF',
      createdAt: item.created_at ?? new Date().toISOString(),
      updatedAt: item.created_at ?? new Date().toISOString(),
      completedAt: item.completed_at ?? undefined,
      status,
      progressPercent: status === 'COMPLETED' ? 100 : status === 'FAILED' ? 100 : 50,
      reviewOptions,
      description: `Audit for document ${String(item.document_id ?? 'unknown')}`,
      overallSummary: 'Audit record retrieved from the backend.',
      totalFindings: 0,
      criticalCount: 0,
      highCount: 0,
      mediumCount: 0,
      lowCount: 0,
      infoCount: 0,
      findings: [],
      rawTextPreview: '',
      processingWarnings: item.processing_warnings ?? []
    };
  }

  private static applyBackendDocument(audit: AuditDocument, document: BackendDocument): AuditDocument {
    return {
      ...audit,
      documentName: document.original_filename,
      fileSize: document.file_size,
      fileFormat: document.content_type === 'application/pdf' ? 'PDF' : 'DOCX'
    };
  }

  static async listAudits(params?: {
    query?: string;
    status?: string;
    documentType?: string;
    sortBy?: 'date_desc' | 'date_asc' | 'findings_desc';
  }): Promise<AuditDocument[]> {
    if (isDemoFallbackEnabled()) {
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

    const [response, documents] = await Promise.all([
      apiRequest<{ items: any[]; limit: number; offset: number }>('/api/v1/audits'),
      apiRequest<{ items: BackendDocument[] }>('/api/v1/documents', {
        params: { limit: 100 }
      })
    ]);
    const documentsById = new Map(documents.items.map(document => [document.id, document]));
    const mapped = response.items.map(item => {
      const audit = this.mapBackendAudit(item);
      const document = documentsById.get(String(item.document_id));
      return document ? this.applyBackendDocument(audit, document) : audit;
    });

    if (params?.status && params.status !== 'ALL') {
      return mapped.filter(a => a.status === params.status);
    }

    if (params?.documentType && params.documentType !== 'ALL') {
      return mapped.filter(a => a.documentType === params.documentType);
    }

    if (params?.query) {
      const q = params.query.toLowerCase();
      return mapped.filter(a => a.documentName.toLowerCase().includes(q));
    }

    const sortBy = params?.sortBy || 'date_desc';
    mapped.sort((a, b) => {
      if (sortBy === 'date_asc') {
        return new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
      }
      if (sortBy === 'findings_desc') {
        return b.totalFindings - a.totalFindings;
      }
      return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime();
    });

    return mapped;
  }

  static async getAudit(id: string): Promise<AuditDocument | null> {
    if (isDemoFallbackEnabled()) {
      const audits = this.getStoredAudits();
      return audits.find(a => a.id === id) || null;
    }

    const audit = await apiRequest<any>(`/api/v1/audits/${id}`);
    const document = await apiRequest<BackendDocument>(`/api/v1/documents/${audit.document_id}`);
    const mapped = this.applyBackendDocument(this.mapBackendAudit(audit), document);

    if (audit.audit_status === 'completed' || audit.status === 'COMPLETED') {
      const findingsResponse = await apiRequest<{
        findings: BackendFinding[];
        limitations?: { items: string[] };
      }>('/api/v1/audits/' + id + '/findings');
      const findings = (findingsResponse.findings || []).map(
        (finding, index) => this.mapBackendFinding(finding, index, id)
      );
      mapped.findings = findings;
      mapped.totalFindings = findings.length;
      mapped.criticalCount = findings.filter(f => f.severity === 'CRITICAL' && f.evidenceAssessment === 'supporting').length;
      mapped.highCount = findings.filter(f => f.severity === 'HIGH').length;
      mapped.mediumCount = findings.filter(f => f.severity === 'MEDIUM').length;
      mapped.lowCount = findings.filter(f => f.severity === 'LOW').length;
      mapped.infoCount = findings.filter(f => f.severity === 'INFORMATIONAL').length;
      mapped.overallSummary = findings.some(f => f.evidenceAssessment === 'supporting')
        ? `The review returned ${findings.length} finding${findings.length === 1 ? '' : 's'} for human review. They are not determinations of legal liability.`
        : 'No supported findings were returned. This does not establish that the contract complies with applicable law.';
      mapped.limitations = findingsResponse.limitations?.items ?? [];
    }

    return mapped;
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
    file?: File;
    isSample?: boolean;
  }): Promise<AuditDocument> {
    assertDemoInputIsSynthetic(isDemoFallbackEnabled(), Boolean(payload.isSample));
    if (isDemoFallbackEnabled()) {
      const auditId = `aud-eth-${Date.now().toString().slice(-6)}`;
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
        isDemoOnly: true,
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

    if (!payload.file || !['PDF', 'DOCX'].includes(payload.fileFormat)) {
      throw new Error('Select a PDF or DOCX file to upload for a backend audit.');
    }

    const contentType = payload.fileFormat === 'PDF'
      ? 'application/pdf'
      : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
    const uploadFile = new File([payload.file], payload.file.name, { type: contentType });
    const formData = new FormData();
    formData.append('file', uploadFile);

    const document = await apiRequest<{ id: string; original_filename: string; file_size: number; content_type: string }>(
      '/api/v1/documents/upload',
      { method: 'POST', body: formData }
    );

    const audit = await apiRequest<any>('/api/v1/audits', {
      method: 'POST',
      body: JSON.stringify({
        document_id: document.id,
        review_options: {
          jurisdiction: 'ET',
          language: payload.documentLanguage.toLowerCase()
        }
      })
    });

    return {
      ...this.mapBackendAudit(audit),
      documentName: document.original_filename,
      documentType: payload.documentType,
      documentLanguage: payload.documentLanguage,
      fileSize: document.file_size,
      fileFormat: payload.fileFormat,
      description: payload.description,
      reviewOptions: payload.reviewOptions
    };
  }

  static async deleteAudit(id: string): Promise<boolean> {
    if (!isDemoFallbackEnabled()) {
      await apiRequest(`/api/v1/audits/${id}`, { method: 'DELETE' });
      return true;
    }

    const current = this.getStoredAudits().filter(a => a.id !== id);
    this.saveAudits(current);
    return true;
  }

  static async reportIncorrectFinding(auditId: string, findingId: string, note: string): Promise<boolean> {
    if (!isDemoFallbackEnabled()) {
      await apiRequest(`/api/v1/findings/${findingId}/feedback`, {
        method: 'POST',
        body: JSON.stringify({
          feedback_type: 'incorrect_finding',
          description: note
        })
      });
      return true;
    }

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

  static async getStatistics(): Promise<AuditStatistics> {
    if (!isDemoFallbackEnabled()) {
      const audits = await this.listAudits();
      const total = audits.length;
      const completed = audits.filter(a => a.status === 'COMPLETED').length;
      const awaiting = audits.filter(a => a.status === 'PENDING' || a.status === 'ANALYZING').length;
      const critical = audits.reduce((sum, a) => sum + (a.criticalCount || 0), 0);
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

    const audits = this.getStoredAudits();
    const total = audits.length;
    const completed = audits.filter(a => a.status === 'COMPLETED').length;
    const awaiting = audits.filter(a => a.status === 'PENDING' || a.status === 'ANALYZING').length;
    const critical = audits.reduce((sum, a) => sum + (a.criticalCount || 0), 0);
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
