import React, { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowUp,
  BookOpen,
  ChevronDown,
  ExternalLink,
  LoaderCircle,
  MessageSquareText,
  Plus,
  Scale,
  Trash2
} from 'lucide-react';
import { User } from '../types';
import {
  LegalQuestionAnswer,
  LegalQuestionConversationDetail,
  LegalQuestionConversationSummary,
  LegalQuestionMessage,
  LegalQuestionService
} from '../services/legal-question.service';

const PAGE_SIZE = 20;

interface LegalChatPageProps {
  currentUser: User | null;
  isAuthChecking: boolean;
  onNavigate: (path: string) => void;
}

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
    <details className="mt-4 rounded-lg border border-slate-200 bg-white">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700">
        <span className="inline-flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-emerald-700" />
          Sources ({citations.length})
        </span>
        <ChevronDown aria-hidden="true" className="h-4 w-4 text-slate-500" />
      </summary>
      <ol className="space-y-3 border-t border-slate-200 p-4">
        {citations.map((citation, index) => (
          <li
            key={`${citation.source_id}-${citation.provision_id}-${index}`}
            className="rounded-md bg-slate-50 p-3 text-sm"
          >
            <p className="font-semibold text-slate-900">
              {citation.source_title}
            </p>
            <p className="mt-1 text-slate-600">
              {citation.law_number && <span>{citation.law_number} · </span>}
              Article {citation.article_number}
              {citation.sub_article_reference
                ? `, subsection ${citation.sub_article_reference}`
                : ''}
              {citation.page_number != null
                ? ` · page ${citation.page_number}`
                : ''}
            </p>
            {citation.source_version_label && (
              <p className="mt-1 text-xs text-slate-500">
                Version: {citation.source_version_label}
              </p>
            )}
            <blockquote className="mt-2 border-l-2 border-slate-300 pl-3 text-slate-700">
              {citation.supporting_quote}
            </blockquote>
            {citation.source_url && (
              <a
                className="mt-3 inline-flex min-h-9 items-center gap-1.5 rounded text-emerald-800 underline underline-offset-2 hover:text-emerald-950 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
                href={citation.source_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open source
                <ExternalLink aria-hidden="true" className="h-3.5 w-3.5" />
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
      className={`rounded-xl border p-4 sm:p-5 ${
        insufficient
          ? 'border-amber-300 bg-amber-50'
          : 'border-slate-200 bg-white'
      }`}
      aria-label={
        insufficient ? 'Answer with insufficient evidence' : 'Legal AI answer'
      }
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h3 className="font-semibold text-slate-900">
          {insufficient ? 'Insufficient evidence' : 'Answer'}
        </h3>
        {message.cache_hit != null && (
          <span
            className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
              message.cache_hit
                ? 'bg-sky-100 text-sky-900'
                : 'bg-slate-100 text-slate-700'
            }`}
            aria-label={`Backend cache ${message.cache_hit ? 'hit' : 'miss'}`}
          >
            Cache {message.cache_hit ? 'HIT' : 'MISS'}
          </span>
        )}
      </div>
      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-800">
        {message.content}
      </p>
      {message.citations.length > 0 && (
        <CitationDetails citations={message.citations} />
      )}
      {message.review_date && (
        <p className="mt-3 text-xs text-slate-500">
          Sources reviewed for {message.review_date}
        </p>
      )}
      {message.answer_status === 'answered' && (
        <p className="mt-4 border-t border-slate-200 pt-3 text-xs leading-5 text-slate-500">
          {message.disclaimer ||
            'AI-generated preliminary information. Verify cited materials and consult a qualified legal professional.'}
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

  useEffect(() => {
    if (currentUser) void loadConversations(0);
  }, [currentUser, loadConversations]);

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

  const submitQuestion = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const question = draft.trim();
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
      <div className="p-8 text-sm text-slate-600" role="status">
        Checking your session…
      </div>
    );
  }

  if (!currentUser) {
    return (
      <section className="mx-auto max-w-xl p-6 sm:p-10" aria-labelledby="chat-auth-title">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <h1 id="chat-auth-title" className="text-xl font-bold text-slate-900">
            Sign in to use Legal AI Chat
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Conversation history is private to your account. Sign in to ask a
            question or view your saved conversations.
          </p>
          <button
            type="button"
            onClick={() => onNavigate('/login')}
            className="mt-5 min-h-11 rounded-lg bg-slate-900 px-4 text-sm font-semibold text-white hover:bg-slate-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
          >
            Go to sign in
          </button>
        </div>
      </section>
    );
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <div className="mb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-emerald-800">
          Legal information
        </p>
        <h1 className="mt-2 flex items-center gap-3 text-2xl font-bold text-slate-950 sm:text-3xl">
          <Scale aria-hidden="true" className="h-7 w-7 text-emerald-800" />
          Legal AI Chat
        </h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          No legal corpus is bundled with this page. Answers depend on source
          records marked eligible by the backend, and the system will report
          when the available evidence is insufficient.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-[17rem_minmax(0,1fr)]">
        <aside
          className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm"
          aria-label="Conversation history"
        >
          <div className="flex items-center justify-between gap-2 px-2 py-1">
            <h2 className="text-sm font-bold text-slate-900">History</h2>
            <button
              type="button"
              onClick={startNewConversation}
              className="inline-flex min-h-10 items-center gap-1.5 rounded-lg px-2.5 text-xs font-semibold text-emerald-900 hover:bg-emerald-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
            >
              <Plus aria-hidden="true" className="h-4 w-4" />
              New
            </button>
          </div>

          {historyError && (
            <p className="m-2 rounded-lg bg-rose-50 p-3 text-xs text-rose-900" role="alert">
              History unavailable: {historyError}
            </p>
          )}
          {isLoadingHistory && conversations.length === 0 && (
            <p className="p-3 text-xs text-slate-500" role="status">
              Loading conversation history…
            </p>
          )}
          {!isLoadingHistory && !historyError && conversations.length === 0 && (
            <p className="p-3 text-xs leading-5 text-slate-500">
              Your saved conversations will appear here.
            </p>
          )}

          <ul className="mt-2 space-y-1">
            {conversations.map(conversation => (
              <li key={conversation.id}>
                <button
                  type="button"
                  onClick={() => setSelectedConversationId(conversation.id)}
                  aria-current={
                    selectedConversationId === conversation.id ? 'page' : undefined
                  }
                  className={`w-full rounded-lg px-3 py-2.5 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700 ${
                    selectedConversationId === conversation.id
                      ? 'bg-emerald-50 text-emerald-950'
                      : 'text-slate-700 hover:bg-slate-50'
                  }`}
                >
                  <span className="block truncate text-xs font-semibold">
                    {conversation.title}
                  </span>
                  <span className="mt-1 block text-[11px] text-slate-500">
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
              className="mt-2 min-h-10 w-full rounded-lg px-3 text-xs font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
            >
              {isLoadingHistory ? 'Loading…' : 'Load more'}
            </button>
          )}
        </aside>

        <section className="flex min-h-[34rem] min-w-0 flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3 sm:px-5">
            <div className="flex items-center gap-2">
              <MessageSquareText
                aria-hidden="true"
                className="h-4 w-4 text-emerald-800"
              />
              <h2 className="text-sm font-bold text-slate-900">
                {selectedConversationId ? 'Conversation' : 'New question'}
              </h2>
            </div>
            {selectedConversationId && (
              <button
                type="button"
                onClick={() => void deleteSelectedConversation()}
                aria-label="Delete this conversation"
                className="inline-flex min-h-10 items-center gap-1.5 rounded-lg px-3 text-xs font-semibold text-rose-800 hover:bg-rose-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-rose-700"
              >
                <Trash2 aria-hidden="true" className="h-4 w-4" />
                <span className="hidden sm:inline">Delete</span>
              </button>
            )}
          </div>

          {conversationError && (
            <p className="m-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-900" role="alert">
              {conversationError}
            </p>
          )}

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
              <div className="mx-auto mt-12 max-w-md text-center">
                <MessageSquareText
                  aria-hidden="true"
                  className="mx-auto h-8 w-8 text-slate-400"
                />
                <p className="mt-3 text-sm font-semibold text-slate-800">
                  Ask a legal question
                </p>
                <p className="mt-1 text-sm leading-6 text-slate-500">
                  The backend will search eligible sources and report when it
                  cannot support an answer.
                </p>
              </div>
            )}
            {messages.map(message =>
              message.role === 'user' ? (
                <div key={message.id} className="ml-auto max-w-[90%] sm:max-w-[80%]">
                  <p className="mb-1 text-right text-xs font-semibold text-slate-500">
                    You
                  </p>
                  <p className="whitespace-pre-wrap rounded-xl bg-slate-900 px-4 py-3 text-sm leading-6 text-white">
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
              <p className="flex items-center gap-2 text-sm text-slate-600" role="status">
                <LoaderCircle aria-hidden="true" className="h-4 w-4 animate-spin" />
                Searching eligible sources and preparing an answer…
              </p>
            )}
          </div>

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
              <div className="flex items-end gap-2 rounded-xl border border-slate-300 bg-white p-2 focus-within:border-emerald-700 focus-within:ring-2 focus-within:ring-emerald-700/20">
                <textarea
                  id="legal-question-input"
                  value={draft}
                  onChange={event => setDraft(event.target.value)}
                  onKeyDown={event => {
                    if (event.key === 'Enter' && !event.shiftKey) {
                      event.preventDefault();
                      event.currentTarget.form?.requestSubmit();
                    }
                  }}
                  maxLength={4000}
                  rows={2}
                  disabled={isSubmitting}
                  placeholder="Type your question…"
                  className="max-h-40 min-h-12 flex-1 resize-y border-0 bg-transparent px-2 py-2 text-sm text-slate-900 outline-none placeholder:text-slate-400 disabled:opacity-60"
                />
                <button
                  type="submit"
                  disabled={isSubmitting || !draft.trim()}
                  aria-label="Submit question"
                  className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-emerald-800 text-white hover:bg-emerald-900 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-700"
                >
                  {isSubmitting ? (
                    <LoaderCircle aria-hidden="true" className="h-5 w-5 animate-spin" />
                  ) : (
                    <ArrowUp aria-hidden="true" className="h-5 w-5" />
                  )}
                </button>
              </div>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Press Enter to submit; Shift+Enter for a new line. AI output
                may be incomplete and is not legal advice.
              </p>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}
