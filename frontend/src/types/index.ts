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

export interface User {
  id: string;
  email: string;
  fullName: string;
  organization: string;
  role: 'COMPLIANCE_OFFICER' | 'HR_MANAGER' | 'LEGAL_COUNSEL' | 'BUSINESS_OWNER' | 'ADMIN';
  createdAt: string;
  dataRetentionDays: number;
}

export interface AuthSession {
  user: User | null;
  token?: string;
  isAuthenticated: boolean;
}
