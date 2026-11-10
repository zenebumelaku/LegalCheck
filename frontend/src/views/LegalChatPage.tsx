import React, { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowUp,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  Database,
  ExternalLink,
  FileText,
  HelpCircle,
  LoaderCircle,
  MessageSquareText,
  Plus,
  Scale,
  Sparkles,
  Trash2,
  Upload,
  Zap
} from 'lucide-react';
import { User } from '../types';
import {
  LegalQuestionAnswer,
  LegalQuestionConversationDetail,
  LegalQuestionConversationSummary,
  LegalQuestionMessage,
  LegalQuestionService
} from '../services/legal-question.service';
import {
  BackendDocumentItem,
  DocumentService,
  DocumentUploadResult
} from '../services/document.service';
import { formatBytes } from '../lib/utils';

const PAGE_SIZE = 20;

interface LegalChatPageProps {
  currentUser: User | null;
  isAuthChecking: boolean;
  onNavigate: (path: string) => void;
}

const DEMO_QUESTIONS = [
  {
    doc: 'Addis Remote Work Policy',
    query: 'What is the monthly internet allowance for remote workers?',
    badge: 'Remote Work'
  },
  {
    doc: 'Standard Consulting Terms',
    query: 'Within how many days must consulting milestone reports be delivered?',
    badge: 'Consulting'
  },
  {
    doc: 'Labour Proclamation No. 1156/2019',
    query: 'What is the maximum probation period under Ethiopian Labour Law?',
    badge: 'Labour Law'
  },
  {
    doc: 'Negative Test (Scenario 6)',
    query: 'What are the safety requirements for operating quantum teleporters?',
    badge: 'Out of Corpus'
  }
];

function formatConversationDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? 'Date unavailable'
    : date.toLocaleDateString();
}

function CitationDetails({
  citations
}: {
  citations: LegalQuestionAnswer['citations'];
}) {
  if (!citations.length) return null;

  return (
    <details className="mt-4 rounded-lg border border-slate-200 bg-white shadow-xs">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-slate-800 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700">
        <span className="inline-flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-emerald-700" />
          Retrieved Citations & Evidence ({citations.length})
        </span>
        <ChevronDown aria-hidden="true" className="h-4 w-4 text-slate-500" />
      </summary>
      <ol className="space-y-3 border-t border-slate-200 p-4">
        {citations.map((citation, index) => (
          <li
            key={`${citation.source_id}-${citation.provision_id}-${index}`}
            className="rounded-lg border border-slate-100 bg-slate-50/80 p-3.5 text-sm"
          >
            <div className="flex items-center justify-between gap-2">
              <p className="font-semibold text-slate-900">
                {citation.source_title}
              </p>
              {citation.law_number && (
                <span className="rounded bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-800">
                  {citation.law_number}
                </span>
              )}
            </div>
            <p className="mt-1 text-xs text-slate-600">
              Article {citation.article_number}
              {citation.sub_article_reference
                ? `, section ${citation.sub_article_reference}`
                : ''}
              {citation.page_number != null
                ? ` · page ${citation.page_number}`
                : ''}
              {citation.source_version_label && (
                <span> · Version: {citation.source_version_label}</span>
              )}
            </p>
            <blockquote className="mt-2.5 border-l-3 border-emerald-600 bg-white p-2.5 rounded-r text-xs leading-relaxed text-slate-700 italic">
              "{citation.supporting_quote}"
            </blockquote>
            {citation.source_url && (
              <a
                className="mt-2.5 inline-flex min-h-8 items-center gap-1.5 rounded text-xs font-medium text-emerald-800 underline underline-offset-2 hover:text-emerald-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
                href={citation.source_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <span>View document source</span>
                <ExternalLink aria-hidden="true" className="h-3 w-3" />
              </a>
            )}
          </li>
        ))}
      </ol>
    </details>
  );
}

function AnswerMessage({ message }: { message: LegalQuestionMessage }) {
  const insufficient = message.answer_status === 'insufficient_evidence';
  return (
    <article
      className={`rounded-xl border p-4 sm:p-5 shadow-xs transition-colors ${
        insufficient
          ? 'border-amber-300 bg-amber-50/70'
          : 'border-slate-200 bg-white'
      }`}
      aria-label={
        insufficient ? 'Answer with insufficient evidence' : 'Legal AI answer'
      }
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {insufficient ? (
            <AlertCircle className="h-5 w-5 text-amber-600" />
          ) : (
            <Sparkles className="h-5 w-5 text-emerald-600" />
          )}
          <h3 className="font-semibold text-slate-900">
            {insufficient ? 'Insufficient Evidence in Corpus' : 'Grounded Answer'}
          </h3>
        </div>

        {/* Redis Cache Indicator Badge */}
        {message.cache_hit != null && (
          <div className="flex items-center">
            {message.cache_hit ? (
              <span
                className="inline-flex items-center gap-1.5 rounded-full border border-emerald-300 bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-900 shadow-xs"
                title="Returned from Redis without repeating retrieval or generation"
              >
                <Zap className="h-3.5 w-3.5 fill-emerald-600 text-emerald-700" />
                Redis Cache HIT
              </span>
            ) : (
              <span
                className="inline-flex items-center gap-1.5 rounded-full border border-slate-300 bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700"
                title="Cache miss; the request continues through retrieval and answer generation"
              >
                <Database className="h-3.5 w-3.5 text-slate-500" />
                Cache MISS (Fresh retrieval)
              </span>
            )}
          </div>
        )}
      </div>

      <p className="mt-3.5 whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
        {message.content}
      </p>

      {message.citations.length > 0 && (
        <CitationDetails citations={message.citations} />
      )}

      {insufficient && (
        <div className="mt-3 rounded-lg border border-amber-200 bg-white/80 p-3 text-xs leading-5 text-amber-900">
          <strong>Note:</strong> The system strictly validates retrieved evidence and prevents hallucinated citations. If the requested information is not in the uploaded documents or eligible legal proclamations, this negative response is returned.
        </div>
      )}

      {message.review_date && (
        <p className="mt-3 text-xs text-slate-500">
          Knowledge base evaluated on {message.review_date}
        </p>
      )}

      {message.answer_status === 'answered' && (
        <p className="mt-4 border-t border-slate-200 pt-3 text-[11px] leading-5 text-slate-500">
          {message.disclaimer ||
            'AI-generated preliminary information based on retrieved vector provisions. Verify cited materials with official gazette copies.'}
        </p>
      )}
    </article>
  );
}

function answerToMessage(answer: LegalQuestionAnswer): LegalQuestionMessage {
  return {
    id: `response-${Date.now()}`,
    turn_index: 0,
    role: 'assistant',
    content: answer.answer,
    answer_status: answer.status,
    review_date: answer.review_date,
    disclaimer: answer.disclaimer,
    citations: answer.citations,
    model_name: answer.model_name,
    model_version: answer.model_version,
    cache_hit: answer.cache_hit,
    created_at: new Date().toISOString()
  };
}

export function LegalChatPage({
  currentUser,
  isAuthChecking,
  onNavigate
}: LegalChatPageProps) {
  // Sidebar tab: 'chats' or 'corpus'
  const [activeTab, setActiveTab] = useState<'chats' | 'corpus'>('chats');

  // Conversations
  const [conversations, setConversations] = useState<
    LegalQuestionConversationSummary[]
  >([]);
  const [selectedConversationId, setSelectedConversationId] = useState<
    string | null
  >(null);
  const [messages, setMessages] = useState<LegalQuestionMessage[]>([]);
  const [draft, setDraft] = useState('');
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isLoadingConversation, setIsLoadingConversation] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [conversationError, setConversationError] = useState<string | null>(
    null
  );
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [historyOffset, setHistoryOffset] = useState(0);
  const [historyTotal, setHistoryTotal] = useState(0);
  const skipNextConversationLoad = useRef<string | null>(null);

  // Document Corpus & Upload State
  const [documents, setDocuments] = useState<BackendDocumentItem[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatusText, setUploadStatusText] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadConversations = useCallback(async (offset: number) => {
    setIsLoadingHistory(true);
    setHistoryError(null);
    try {
      const page = await LegalQuestionService.listConversations(
        PAGE_SIZE,
        offset
      );
      setConversations(current =>
        offset === 0 ? page.items : [...current, ...page.items]
      );
      setHistoryOffset(offset);
      setHistoryTotal(page.total);
    } catch (error) {
      setHistoryError(
        error instanceof Error
          ? error.message
          : 'Conversation history could not be loaded.'
      );
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  const loadDocuments = useCallback(async () => {
    setIsLoadingDocs(true);
    try {
      const result = await DocumentService.listDocuments(50, 0);
      setDocuments(result.items);
    } catch (error) {
      console.error('Failed to load documents', error);
    } finally {
      setIsLoadingDocs(false);
    }
  }, []);

  useEffect(() => {
    if (currentUser) {
      void loadConversations(0);
      void loadDocuments();
    }
  }, [currentUser, loadConversations, loadDocuments]);

  useEffect(() => {
    if (!selectedConversationId) {
      setMessages([]);
      setConversationError(null);
      return;
    }
    if (skipNextConversationLoad.current === selectedConversationId) {
      skipNextConversationLoad.current = null;
      return;
    }

    let active = true;
    setIsLoadingConversation(true);
    setConversationError(null);
    LegalQuestionService.getConversation(selectedConversationId)
      .then((conversation: LegalQuestionConversationDetail) => {
        if (active) setMessages(conversation.messages);
      })
      .catch(error => {
        if (active) {
          setConversationError(
            error instanceof Error
              ? error.message
              : 'This conversation could not be loaded.'
          );
        }
      })
      .finally(() => {
        if (active) setIsLoadingConversation(false);
      });

    return () => {
      active = false;
    };
  }, [selectedConversationId]);

  const startNewConversation = () => {
    setSelectedConversationId(null);
    setMessages([]);
    setSubmitError(null);
    setConversationError(null);
  };

  const handleProcessUpload = async (file: File) => {
    setUploadError(null);
    setUploadSuccess(null);

    // Validation
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (ext !== '.pdf' && ext !== '.docx') {
      setUploadError('Unsupported format. Please upload a PDF (.pdf) or Word document (.docx).');
      return;
    }

    if (file.size === 0) {
      setUploadError('The selected file is empty.');
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setUploadError('File size exceeds the 10 MB limit.');
      return;
    }

    setIsUploading(true);
    setUploadStatusText('Extracting text and chunking document...');

    try {
      setUploadStatusText('Generating dense vector embeddings & saving to vector store...');
      const result: DocumentUploadResult = await DocumentService.uploadDocument(file);

      const chunkCount = result.chunks_created || 0;
      setUploadSuccess(
        `Successfully indexed "${result.original_filename}"! Created ${chunkCount} vector chunks. Redis cache invalidated for immediate retrieval.`
      );
      await loadDocuments();
    } catch (error) {
      setUploadError(
        error instanceof Error
          ? error.message
          : 'Document upload and vector indexing failed.'
      );
    } finally {
      setIsUploading(false);
      setUploadStatusText('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteDocument = async (id: string, name: string) => {
    if (!window.confirm(`Remove "${name}" from the vector store? This will also invalidate Redis cache.`)) {
      return;
    }

    try {
      await DocumentService.deleteDocument(id);
      setUploadSuccess(`Deleted "${name}". Associated vector chunks removed and cache invalidated.`);
      await loadDocuments();
    } catch (error) {
      setUploadError(
        error instanceof Error
          ? error.message
          : 'Failed to delete document from vector store.'
      );
    }
  };

  const executeQuestion = async (questionText: string) => {
    const question = questionText.trim();
    if (!question || isSubmitting) return;

    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const result = await LegalQuestionService.askInConversation({
        question,
        ...(selectedConversationId
          ? { conversation_id: selectedConversationId }
          : {})
      });
      setDraft('');
      if (!selectedConversationId) {
        skipNextConversationLoad.current = result.conversation_id;
      }
      setSelectedConversationId(result.conversation_id);
      setMessages(current => [
        ...current,
        {
          id: `question-${Date.now()}`,
          turn_index: current.length,
          role: 'user',
          content: result.answer.question,
          citations: [],
          created_at: new Date().toISOString()
        },
        answerToMessage(result.answer)
      ]);
      void loadConversations(0);
    } catch (error) {
      setSubmitError(
        error instanceof Error
          ? error.message
          : 'Your question could not be sent. Please try again.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const submitQuestion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    await executeQuestion(draft);
  };

  const deleteSelectedConversation = async () => {
    if (!selectedConversationId) return;
    try {
      await LegalQuestionService.deleteConversation(selectedConversationId);
      setSelectedConversationId(null);
      setMessages([]);
      setConversationError(null);
      await loadConversations(0);
    } catch (error) {
      setConversationError(
        error instanceof Error
          ? error.message
          : 'The conversation could not be deleted.'
      );
    }
  };

  if (isAuthChecking) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-8 text-sm text-slate-600" role="status">
        <LoaderCircle className="h-6 w-6 animate-spin text-emerald-700 mr-2" />
        Checking session…
      </div>
    );
  }

  if (!currentUser) {
    return (
      <section className="mx-auto max-w-xl p-6 sm:p-10" aria-labelledby="chat-auth-title">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <h1 id="chat-auth-title" className="text-xl font-bold text-slate-900">
            Sign in to use RAG & Document Q&A
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Document ingestion, vector search, and Redis cached responses are
            tied to your authenticated workspace.
          </p>
          <button
            type="button"
            onClick={() => onNavigate('/login')}
            className="mt-5 min-h-11 rounded-lg bg-emerald-800 px-4 text-sm font-semibold text-white hover:bg-emerald-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
          >
            Go to sign in
          </button>
        </div>
      </section>
    );
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      {/* Page Header */}
      <div className="mb-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="mt-2 flex items-center gap-3 text-2xl font-bold text-slate-950 sm:text-3xl">
            <Scale aria-hidden="true" className="h-7 w-7 text-emerald-800" />
            RAG Q&A & Document Ingestion
          </h1>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-slate-600">
            Upload custom PDF/Word documents to automatically generate dense vector embeddings.
            Ask questions with source citations, live vector retrieval, and active Redis caching.
          </p>
        </div>

        {/* Ingestion Dropdown Quick Trigger */}
        <div className="flex items-center gap-2 self-start md:self-auto">
          <button
            type="button"
            onClick={() => {
              setActiveTab('corpus');
              fileInputRef.current?.click();
            }}
            disabled={isUploading}
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-800 px-4 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-emerald-900 disabled:opacity-50"
          >
            <Upload className="h-4 w-4" />
            <span>Upload Document</span>
          </button>
        </div>
      </div>

      {/* Global Ingestion Notifications */}
      {uploadSuccess && (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-emerald-300 bg-emerald-50 p-3.5 text-xs font-medium text-emerald-900">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
            <span>{uploadSuccess}</span>
          </div>
          <button
            type="button"
            onClick={() => setUploadSuccess(null)}
            className="ml-2 font-bold text-emerald-800 hover:text-emerald-950"
          >
            ✕
          </button>
        </div>
      )}
      {uploadError && (
        <div className="mb-4 flex items-center justify-between rounded-lg border border-rose-300 bg-rose-50 p-3.5 text-xs font-medium text-rose-900">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-600" />
            <span>{uploadError}</span>
          </div>
          <button
            type="button"
            onClick={() => setUploadError(null)}
            className="ml-2 font-bold text-rose-800 hover:text-rose-950"
          >
            ✕
          </button>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid gap-5 lg:grid-cols-[19rem_minmax(0,1fr)]">
        {/* Left Side Panel: Tabs for History and Corpus */}
        <aside
          className="flex flex-col rounded-xl border border-slate-200 bg-white p-3 shadow-xs"
          aria-label="Sidebar workspace"
        >
          {/* Tab Selector */}
          <div className="flex rounded-lg bg-slate-100 p-1 mb-3">
            <button
              type="button"
              onClick={() => setActiveTab('chats')}
              className={`flex-1 rounded-md py-1.5 text-xs font-semibold transition-all ${
                activeTab === 'chats'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Conversations
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('corpus')}
              className={`flex-1 flex items-center justify-center gap-1.5 rounded-md py-1.5 text-xs font-semibold transition-all ${
                activeTab === 'corpus'
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <span>Corpus</span>
              <span className="rounded-full bg-emerald-100 px-1.5 py-0.2 text-[10px] font-bold text-emerald-800">
                {documents.length}
              </span>
            </button>
          </div>

          {/* TAB 1: Chat History */}
          {activeTab === 'chats' && (
            <div className="flex-1 flex flex-col">
              <div className="flex items-center justify-between gap-2 px-1 pb-2">
                <span className="text-xs font-bold text-slate-800">Saved Chats</span>
                <button
                  type="button"
                  onClick={startNewConversation}
                  className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-semibold text-emerald-900 hover:bg-emerald-50"
                >
                  <Plus aria-hidden="true" className="h-3.5 w-3.5" />
                  New
                </button>
              </div>

              {historyError && (
                <p className="m-1 rounded-lg bg-rose-50 p-2.5 text-xs text-rose-900" role="alert">
                  {historyError}
                </p>
              )}
              {isLoadingHistory && conversations.length === 0 && (
                <p className="p-3 text-xs text-slate-500" role="status">
                  Loading chats…
                </p>
              )}
              {!isLoadingHistory && !historyError && conversations.length === 0 && (
                <p className="p-3 text-xs leading-relaxed text-slate-500">
                  Your questions and answers will be saved here.
                </p>
              )}

              <ul className="mt-1 space-y-1 overflow-y-auto max-h-[30rem]">
                {conversations.map(conversation => (
                  <li key={conversation.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedConversationId(conversation.id)}
                      aria-current={
                        selectedConversationId === conversation.id ? 'page' : undefined
                      }
                      className={`w-full rounded-lg px-3 py-2 text-left focus-visible:outline-2 focus-visible:outline-emerald-700 ${
                        selectedConversationId === conversation.id
                          ? 'bg-emerald-50 text-emerald-950 font-semibold'
                          : 'text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      <span className="block truncate text-xs">
                        {conversation.title}
                      </span>
                      <span className="mt-0.5 block text-[10px] text-slate-500">
                        {formatConversationDate(conversation.updated_at)}
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
              {conversations.length < historyTotal && (
                <button
                  type="button"
                  disabled={isLoadingHistory}
                  onClick={() => void loadConversations(historyOffset + PAGE_SIZE)}
                  className="mt-2 min-h-8 w-full rounded-lg px-2 text-xs font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-50"
                >
                  {isLoadingHistory ? 'Loading…' : 'Load more'}
                </button>
              )}
            </div>
          )}

          {/* TAB 2: Document Corpus & Vector Store */}
          {activeTab === 'corpus' && (
            <div className="flex-1 flex flex-col space-y-3">
              {/* Dropzone */}
              <div
                onDragOver={e => {
                  e.preventDefault();
                  setIsDragOver(true);
                }}
                onDragLeave={() => setIsDragOver(false)}
                onDrop={e => {
                  e.preventDefault();
                  setIsDragOver(false);
                  if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                    void handleProcessUpload(e.dataTransfer.files[0]);
                  }
                }}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-all ${
                  isDragOver
                    ? 'border-emerald-600 bg-emerald-50/70'
                    : 'border-slate-300 hover:border-slate-400 bg-slate-50/50'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx"
                  onChange={e => {
                    if (e.target.files && e.target.files[0]) {
                      void handleProcessUpload(e.target.files[0]);
                    }
                  }}
                  className="hidden"
                />
                <div className="mx-auto mb-2 flex h-9 w-9 items-center justify-center rounded-full bg-emerald-100 text-emerald-800">
                  <Upload className="h-4 w-4" />
                </div>
                <p className="text-xs font-semibold text-slate-900">
                  Upload PDF or DOCX
                </p>
                <p className="mt-1 text-[11px] text-slate-500">
                  Auto-chunks & embeds into vector DB (Max 10 MB)
                </p>
              </div>

              {isUploading && (
                <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-900">
                  <div className="flex items-center gap-2 font-semibold">
                    <LoaderCircle className="h-4 w-4 animate-spin text-emerald-700" />
                    <span>Indexing document...</span>
                  </div>
                  <p className="mt-1 text-[11px] text-emerald-800">{uploadStatusText}</p>
                </div>
              )}

              {/* Indexed Documents List */}
              <div className="mt-2 flex-1">
                <div className="flex items-center justify-between pb-1 text-xs font-bold text-slate-800">
                  <span>Indexed Documents ({documents.length})</span>
                  <button
                    type="button"
                    onClick={() => void loadDocuments()}
                    className="text-[11px] text-emerald-700 hover:underline"
                  >
                    Refresh
                  </button>
                </div>

                {isLoadingDocs && documents.length === 0 && (
                  <p className="p-2 text-xs text-slate-500">Loading indexed documents…</p>
                )}

                {!isLoadingDocs && documents.length === 0 && (
                  <p className="p-2 text-xs text-slate-500 leading-relaxed">
                    No custom documents uploaded yet. Default verified proclamations are active.
                  </p>
                )}

                <ul className="mt-1.5 space-y-1.5 overflow-y-auto max-h-[22rem]">
                  {documents.map(doc => (
                    <li
                      key={doc.id}
                      className="group rounded-lg border border-slate-200 bg-white p-2.5 text-xs shadow-2xs hover:border-slate-300"
                    >
                      <div className="flex items-start justify-between gap-1.5">
                        <div className="min-w-0 flex-1">
                          <p className="font-semibold text-slate-900 truncate" title={doc.original_filename}>
                            {doc.original_filename}
                          </p>
                          <div className="mt-1 flex items-center gap-1.5 text-[10px] text-slate-500">
                            <span>{formatBytes(doc.file_size)}</span>
                            <span>•</span>
                            <span className="uppercase">{doc.document_type || 'DOC'}</span>
                            <span>•</span>
                            <span className="text-emerald-700 font-medium">Vector Indexed</span>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={() => void handleDeleteDocument(doc.id, doc.original_filename)}
                          className="p-1 text-slate-400 hover:text-rose-600 rounded transition-colors"
                          title="Remove from vector store"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </aside>

        {/* Right Chat Panel */}
        <section className="flex min-h-[38rem] min-w-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs">
          {/* Chat Header */}
          <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3 sm:px-5">
            <div className="flex items-center gap-2">
              <MessageSquareText
                aria-hidden="true"
                className="h-4 w-4 text-emerald-800"
              />
              <h2 className="text-sm font-bold text-slate-900">
                {selectedConversationId ? 'Conversation' : 'New Legal Question'}
              </h2>
            </div>

            <div className="flex items-center gap-2">
              <span className="hidden sm:inline-flex items-center gap-1 rounded bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-700">
                <Database className="h-3 w-3 text-emerald-700" />
                Redis Cache: Active
              </span>

              {selectedConversationId && (
                <button
                  type="button"
                  onClick={() => void deleteSelectedConversation()}
                  aria-label="Delete this conversation"
                  className="inline-flex min-h-8 items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold text-rose-800 hover:bg-rose-50"
                >
                  <Trash2 aria-hidden="true" className="h-3.5 w-3.5" />
                  <span className="hidden sm:inline">Delete</span>
                </button>
              )}
            </div>
          </div>

          {conversationError && (
            <p className="m-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-900" role="alert">
              {conversationError}
            </p>
          )}

          {/* Messages Area */}
          <div
            className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-5"
            aria-live="polite"
            aria-relevant="additions text"
          >
            {isLoadingConversation && (
              <p className="text-sm text-slate-500" role="status">
                Loading conversation…
              </p>
            )}

            {!isLoadingConversation && !conversationError && messages.length === 0 && (
              <div className="mx-auto mt-6 max-w-xl text-center">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-emerald-800">
                  <Scale className="h-6 w-6" />
                </div>
                <h3 className="text-base font-bold text-slate-900">
                  Ask a question with RAG Vector Retrieval & Redis
                </h3>
                <p className="mt-1.5 text-xs sm:text-sm leading-relaxed text-slate-600">
                  Answers cite verified legal evidence from your uploaded documents or proclamation statutes.
                  Supported answers may be served from Redis when the question, legal sources, and answer settings match.
                </p>

                {/* Quick Demo Prompts */}
                <div className="mt-6 text-left">
                  <div className="mb-2.5 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-slate-500">
                    <Sparkles className="h-3.5 w-3.5 text-emerald-700" />
                    <span>Try Demo Corpus Questions (Click to Ask)</span>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {DEMO_QUESTIONS.map((item, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => void executeQuestion(item.query)}
                        className="flex flex-col text-left rounded-lg border border-slate-200 bg-slate-50/70 p-3 hover:border-emerald-400 hover:bg-emerald-50/40 transition-colors"
                      >
                        <div className="flex items-center justify-between gap-1 text-[10px] font-semibold text-slate-500 mb-1">
                          <span>{item.doc}</span>
                          <span className="rounded bg-slate-200/80 px-1.5 py-0.2 text-[9px] text-slate-700">
                            {item.badge}
                          </span>
                        </div>
                        <span className="text-xs font-medium text-slate-900 leading-snug">
                          "{item.query}"
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {messages.map(message =>
              message.role === 'user' ? (
                <div key={message.id} className="ml-auto max-w-[90%] sm:max-w-[80%]">
                  <p className="mb-1 text-right text-xs font-semibold text-slate-500">
                    You
                  </p>
                  <p className="whitespace-pre-wrap rounded-xl bg-slate-900 px-4 py-3 text-sm leading-6 text-white shadow-xs">
                    {message.content}
                  </p>
                </div>
              ) : (
                <div key={message.id} className="mr-auto w-full max-w-3xl">
                  <AnswerMessage message={message} />
                </div>
              )
            )}

            {isSubmitting && (
              <div className="flex items-center gap-2.5 rounded-xl border border-emerald-100 bg-emerald-50/50 p-4 text-sm text-slate-700" role="status">
                <LoaderCircle aria-hidden="true" className="h-5 w-5 animate-spin text-emerald-800" />
                <div>
                  <p className="font-semibold text-slate-900">Checking Redis, then retrieving and ranking legal passages…</p>
                  <p className="text-xs text-slate-500">Answers are checked against retrieved evidence and citations are validated before they are shown.</p>
                </div>
              </div>
            )}
          </div>

          {/* Question Input Form */}
          <div className="border-t border-slate-200 p-4 sm:p-5">
            {submitError && (
              <p className="mb-3 flex items-start gap-2 rounded-lg bg-rose-50 p-3 text-sm text-rose-900" role="alert">
                <AlertCircle aria-hidden="true" className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{submitError}</span>
              </p>
            )}
            <form onSubmit={submitQuestion}>
              <label htmlFor="legal-question-input" className="sr-only">
                Your legal question
              </label>
              <div className="flex items-end gap-2 rounded-xl border border-slate-300 bg-white p-2 focus-within:border-emerald-700 focus-within:ring-2 focus-within:ring-emerald-700/20 shadow-2xs">
                <textarea
                  id="legal-question-input"
                  value={draft}
                  onChange={event => setDraft(event.target.value)}
                  onKeyDown={event => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault();
                      if (draft.trim() && !isSubmitting) {
                        event.currentTarget.form?.requestSubmit();
                      }
                    }
                  }}
                  maxLength={4000}
                  rows={2}
                  disabled={isSubmitting}
                  placeholder="Ask a question about your uploaded documents or Ethiopian labour law..."
                  className="max-h-40 min-h-12 flex-1 resize-y border-0 bg-transparent px-2 py-2 text-sm text-slate-900 outline-none placeholder:text-slate-400 disabled:opacity-60"
                />
                <button
                  type="submit"
                  disabled={isSubmitting || !draft.trim()}
                  aria-label="Submit question"
                  className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-emerald-800 text-white hover:bg-emerald-900 disabled:cursor-not-allowed disabled:opacity-40 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 shadow-xs"
                >
                  {isSubmitting ? (
                    <LoaderCircle aria-hidden="true" className="h-5 w-5 animate-spin" />
                  ) : (
                    <ArrowUp aria-hidden="true" className="h-5 w-5" />
                  )}
                </button>
              </div>
              <div className="mt-2 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
                <p>Press Enter to submit; Shift+Enter for a new line.</p>
                <p className="text-[11px] text-slate-400">Empty queries rejected • Grounded with source citations</p>
              </div>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}
