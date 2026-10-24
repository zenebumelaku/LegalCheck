export type AuditStatus = 'PENDING' | 'ANALYZING' | 'EXTRACTING_PROVISIONS' | 'COMPLETED' | 'FAILED';

export type FindingSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFORMATIONAL';

export type FindingType =
  | 'POTENTIAL_LEGAL_CONFLICT'
  | 'MISSING_OR_INCOMPLETE_CLAUSE'
  | 'OUTDATED_OR_UNVERIFIED_REFERENCE'
  | 'INFORMATIONAL_OBSERVATION'
  | 'INSUFFICIENT_EVIDENCE';

export type FindingCategory =
  | 'PROBATION'
  | 'WORKING_HOURS'
  | 'LEAVES_AND_REST'
  | 'MATERNITY_AND_WOMEN'
  | 'TERMINATION_AND_SEVERANCE'
  | 'REMUNERATION_AND_DEDUCTIONS'
  | 'SAFETY_AND_HEALTH'
  | 'DISPUTE_RESOLUTION'
  | 'GENERAL_CONTRACT_TERMS';

export interface LegalArticle {
  id: string;
  articleNumber: string;
  subArticle?: string;
  title: string;
  text: string;
  amharicText?: string;
  notes?: string;
}

export interface LegalSource {
  id: string;
  proclamationNumber: string;
  title: string;
  officialGazeta: string;
  publicationDate: string;
  effectiveDate: string;
  status: 'IN_FORCE' | 'AMENDED' | 'REPEALED' | 'PROPOSED' | 'UNKNOWN';
  description: string;
  category: string;
  sourceUrl?: string;
  articlesCount: number;
  articles: LegalArticle[];
  provenance: {
    publisher: string;
    verifiedBy: string;
    lastVerifiedDate: string;
    gazetaVolume: string;
  };
}

export interface AuditFinding {
  id: string;
  auditId: string;
  title: string;
  severity: FindingSeverity;
  type: FindingType;
  category: FindingCategory;
  contractExcerpt: string;
  contractLocation?: string;
  issueExplanation: string;
  legalProvision: {
    proclamationTitle: string;
    proclamationNumber: string;
    articleNumber: string;
    subArticle?: string;
    provisionText: string;
    sourceId: string;
    sourceUrl?: string;
    effectiveDate: string;
  };
  suggestedAction: string;
  confidenceScore: number; // 0 to 1 confidence of provision match
  userReported?: boolean;
  userReportNote?: string;
}

export interface AuditDocument {
  id: string;
  userId: string;
  documentName: string;
  documentType: 'EMPLOYMENT_CONTRACT' | 'COLLECTIVE_AGREEMENT' | 'COMPANY_BYLAW' | 'CONSULTANCY_AGREEMENT';
  documentLanguage: 'ENGLISH' | 'AMHARIC' | 'MIXED';
  fileSize: number; // in bytes
  fileFormat: 'PDF' | 'DOCX' | 'TXT';
  createdAt: string;
  updatedAt: string;
  completedAt?: string;
  status: AuditStatus;
  progressPercent: number;
  reviewOptions: {
    checkLegalConflicts: boolean;
    checkMissingClauses: boolean;
    checkOutdatedReferences: boolean;
  };
  description?: string;
  overallSummary?: string;
  totalFindings: number;
  criticalCount: number;
  highCount: number;
  mediumCount: number;
  lowCount: number;
  infoCount: number;
  findings?: AuditFinding[];
  rawTextPreview?: string;
}

export interface User {
  id: string;
  email: string;
  fullName: string;
  organization: string;
  role: 'COMPLIANCE_OFFICER' | 'HR_MANAGER' | 'LEGAL_COUNSEL' | 'BUSINESS_OWNER';
  createdAt: string;
  dataRetentionDays: number;
}

export interface AuthSession {
  user: User | null;
  token?: string;
  isAuthenticated: boolean;
}

export interface AuditStatistics {
  totalAudits: number;
  completedAudits: number;
  awaitingAudits: number;
  criticalIssuesFound: number;
  complianceRate: number;
}
