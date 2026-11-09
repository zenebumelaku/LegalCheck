import { apiRequest } from '../lib/api-client';

export interface LegalQuestionReviewContext {
  review_date?: string;
  jurisdiction?: string;
  language?: string;
  source_type?: string;
  law_number?: string;
  article_number?: string;
  include_unverified?: false;
}

export interface LegalQuestionCitation {
  source_id: string;
  source_title: string;
  source_version_label?: string | null;
  law_number?: string | null;
  source_url?: string | null;
  provision_id: string;
  article_number: string;
  sub_article_reference?: string | null;
  page_number?: number | null;
  supporting_quote: string;
}

export interface LegalQuestionAnswer {
  status: 'answered' | 'insufficient_evidence';
  question: string;
  answer: string;
  review_date: string;
  citations: LegalQuestionCitation[];
  model_name?: string | null;
  model_version?: string | null;
  cache_hit: boolean;
  disclaimer: string;
}

export interface LegalQuestionMessage {
  id: string;
  turn_index: number;
  role: 'user' | 'assistant';
  content: string;
  answer_status?: 'answered' | 'insufficient_evidence' | null;
  review_date?: string | null;
  disclaimer?: string | null;
  citations: LegalQuestionCitation[];
  model_name?: string | null;
  model_version?: string | null;
  cache_hit?: boolean | null;
  created_at: string;
}

export interface LegalQuestionConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface LegalQuestionConversationDetail extends LegalQuestionConversationSummary {
  messages: LegalQuestionMessage[];
}

export interface LegalQuestionConversationPage {
  items: LegalQuestionConversationSummary[];
  limit: number;
  offset: number;
  total: number;
}

export interface LegalQuestionConversationRequest {
  question: string;
  conversation_id?: string;
  review_context?: LegalQuestionReviewContext;
}

export interface LegalQuestionConversationResult {
  conversation_id: string;
  answer: LegalQuestionAnswer;
}

export class LegalQuestionService {
  static askInConversation(
    payload: LegalQuestionConversationRequest
  ): Promise<LegalQuestionConversationResult> {
    return apiRequest<LegalQuestionConversationResult>(
      '/api/v1/legal-questions/conversations',
      {
        method: 'POST',
        body: JSON.stringify(payload)
      }
    );
  }

  static listConversations(
    limit = 20,
    offset = 0
  ): Promise<LegalQuestionConversationPage> {
    return apiRequest<LegalQuestionConversationPage>(
      '/api/v1/legal-questions/conversations',
      { params: { limit, offset } }
    );
  }

  static getConversation(
    conversationId: string
  ): Promise<LegalQuestionConversationDetail> {
    return apiRequest<LegalQuestionConversationDetail>(
      `/api/v1/legal-questions/conversations/${encodeURIComponent(conversationId)}`
    );
  }

  static async deleteConversation(conversationId: string): Promise<void> {
    await apiRequest<void>(
      `/api/v1/legal-questions/conversations/${encodeURIComponent(conversationId)}`,
      { method: 'DELETE' }
    );
  }
}
