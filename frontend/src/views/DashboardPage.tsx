import React, { useState, useEffect, useRef, FormEvent } from 'react';
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Database,
  FileText,
  HelpCircle,
  LoaderCircle,
  MessageSquareText,
  Plus,
  Scale,
  Search,
  Sparkles,
  Trash2,
  Upload,
  Zap
} from 'lucide-react';
import { User } from '../types';
import { formatBytes, formatDate } from '../lib/utils';
import {
  BackendDocumentItem,
  DocumentService,
  DocumentUploadResult
} from '../services/document.service';

interface DashboardPageProps {
  onNavigate: (path: string) => void;
  currentUser: User | null;
}

const QUICK_PROMPTS = [
  'What are the employee job duties in the agreement?',
  'What is the probation period in the employment agreement?',
  'What is the gross monthly salary and payment schedule?',
  'What is the monthly internet allowance for remote workers?',
  'Within how many days must consulting milestone reports be delivered?'
];

export function DashboardPage({ onNavigate, currentUser }: DashboardPageProps) {
  const [documents, setDocuments] = useState<BackendDocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const res = await DocumentService.listDocuments(50, 0);
      setDocuments(res.items);
    } catch (err) {
      console.error('Failed to load documents', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadDocuments();
  }, []);

  const handleFileUpload = async (file: File) => {
    setUploadError(null);
    setUploadStatus(null);

    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (ext !== '.pdf' && ext !== '.docx') {
      setUploadError('Please select a PDF (.pdf) or Word document (.docx).');
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
    setUploadStatus('Extracting text and generating vector chunks...');

    try {
      const result: DocumentUploadResult = await DocumentService.uploadDocument(file);
      const chunks = result.chunks_created || 0;
      setUploadStatus(
        `Successfully added "${result.original_filename}" to knowledge base (${chunks} chunks created). You can now ask questions about it!`
      );
      await loadDocuments();
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : 'Upload and indexing failed. Please try again.'
      );
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Remove "${name}" from the AI knowledge base?`)) return;
    try {
      await DocumentService.deleteDocument(id);
      await loadDocuments();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to delete document');
    }
  };

  const handleSearchSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    onNavigate('/legal-chat');
  };

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Welcome Header */}
      <div className="bg-slate-900 text-white rounded-2xl p-6 sm:p-8 shadow-sm border border-slate-800 flex flex-col md:flex-row md:items-center md:justify-between gap-6">
        <div className="space-y-2">
         
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
            {currentUser ? `Welcome back, ${currentUser.fullName}` : 'Document AI Assistant'}
          </h1>
          <p className="text-sm text-slate-300 max-w-2xl leading-relaxed">
            Upload your employment agreements, company policies, or consulting terms.
            Ask questions in plain English and receive instant, source-cited answers powered by
            semantic vector retrieval and high-speed Redis caching.
          </p>
        </div>

        
      </div>

      {/* Primary Actions: Search & Quick Ask */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-emerald-600" />
            <span>Ask a Question</span>
          </h2>
          <span className="text-xs text-slate-400">Grounded with citations</span>
        </div>

        <form onSubmit={handleSearchSubmit} className="relative">
          <input
            type="text"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            placeholder="Type your question here (e.g. 'What are the employee job duties?')..."
            className="w-full rounded-xl border border-slate-300 bg-slate-50/50 py-3.5 pl-4 pr-28 text-sm text-slate-900 outline-none focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20 transition-all placeholder:text-slate-400"
          />
          <button
            type="submit"
            onClick={() => onNavigate('/legal-chat')}
            className="absolute right-2 top-2 bottom-2 inline-flex items-center gap-1.5 rounded-lg bg-emerald-800 px-4 text-xs font-semibold text-white hover:bg-emerald-900 transition-colors"
          >
            <span>Ask AI</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </form>

        {/* Clickable Quick Prompts */}
        <div className="pt-1">
          <p className="text-xs font-semibold text-slate-500 mb-2">Try asking these sample questions:</p>
          <div className="flex flex-wrap gap-2">
            {QUICK_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => onNavigate('/legal-chat')}
                className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-700 hover:border-emerald-400 hover:bg-emerald-50/60 hover:text-emerald-900 transition-all text-left"
              >
                "{prompt}"
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* System Status Metric Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Active Documents */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold">Indexed Documents</span>
            <FileText className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold font-mono text-slate-900 tabular-nums">
            {documents.length}
          </div>
          <div className="mt-1 text-[11px] text-slate-400">Ready for instant search</div>
        </div>

        {/* Redis Cache */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold">Redis Cache</span>
            <Zap className="w-4 h-4 text-emerald-600 fill-emerald-600" />
          </div>
          <div className="text-sm font-bold text-emerald-800 mt-2 flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>Active & Ready</span>
          </div>
          <div className="mt-1 text-[11px] text-slate-400">&lt;100ms response time</div>
        </div>

        {/* Vector Embeddings */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold">Vector Index</span>
            <Database className="w-4 h-4 text-slate-500" />
          </div>
          <div className="text-sm font-bold text-slate-900 mt-2">
            384-dim Dense Vectors
          </div>
          <div className="mt-1 text-[11px] text-slate-400">SentenceTransformers CPU</div>
        </div>

        {/* AI Model */}
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between text-slate-500 mb-1">
            <span className="text-xs font-semibold">AI Synthesis</span>
            <Scale className="w-4 h-4 text-amber-600" />
          </div>
          <div className="text-sm font-bold text-slate-900 mt-2">
            Google Gemini
          </div>
          <div className="mt-1 text-[11px] text-slate-400">Grounded with citations</div>
        </div>
      </div>

      {/* Document Ingestion Dropzone */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-xs space-y-4">
        <div>
          <h2 className="text-base font-bold text-slate-900">Upload New Document to Knowledge Base</h2>
          <p className="text-xs text-slate-500">
            Drag and drop any PDF or Word agreement. Text is extracted, split into chunks, embedded into the vector database, and immediately made searchable.
          </p>
        </div>

        {/* Feedback Banners */}
        {uploadStatus && (
          <div className="flex items-center justify-between rounded-xl border border-emerald-300 bg-emerald-50 p-4 text-xs font-semibold text-emerald-900">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-600" />
              <span>{uploadStatus}</span>
            </div>
            <button
              onClick={() => setUploadStatus(null)}
              className="text-emerald-800 hover:text-emerald-950 font-bold ml-2"
            >
              ✕
            </button>
          </div>
        )}

        {uploadError && (
          <div className="flex items-center justify-between rounded-xl border border-rose-300 bg-rose-50 p-4 text-xs font-semibold text-rose-900">
            <span>{uploadError}</span>
            <button
              onClick={() => setUploadError(null)}
              className="text-rose-800 hover:text-rose-950 font-bold ml-2"
            >
              ✕
            </button>
          </div>
        )}

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
              void handleFileUpload(e.dataTransfer.files[0]);
            }
          }}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
            isDragOver
              ? 'border-emerald-600 bg-emerald-50/70'
              : 'border-slate-300 hover:border-slate-400 bg-slate-50/50 hover:bg-slate-50'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx"
            onChange={e => {
              if (e.target.files && e.target.files[0]) {
                void handleFileUpload(e.target.files[0]);
              }
            }}
            className="hidden"
          />

          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-800">
            {isUploading ? (
              <LoaderCircle className="h-6 w-6 animate-spin" />
            ) : (
              <Upload className="h-6 w-6" />
            )}
          </div>

          <p className="text-sm font-bold text-slate-900">
            {isUploading ? 'Indexing document into vector store...' : 'Click to upload or drag & drop documents'}
          </p>
          <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
            Supported formats: PDF and Word (.docx) up to 10 MB. No developer setup or manual restart required.
          </p>
        </div>
      </div>

      {/* Ingested Documents List */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Knowledge Base Documents</h2>
            <p className="text-xs text-slate-500">Currently indexed and retrievable documents</p>
          </div>
          <button
            onClick={() => onNavigate('/legal-chat')}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-800 hover:text-emerald-950"
          >
            <span>Ask questions about these</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {loading ? (
          <div className="p-8 text-center text-xs text-slate-500">Loading documents...</div>
        ) : documents.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-500">
            No custom documents uploaded yet. Default verified proclamations are ready.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[11px]">
                <tr>
                  <th className="py-3 px-4">Document</th>
                  <th className="py-3 px-4">Size</th>
                  <th className="py-3 px-4">Type</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Date Added</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {documents.map(doc => (
                  <tr key={doc.id} className="hover:bg-slate-50 transition-colors">
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900 truncate max-w-md">
                        {doc.original_filename}
                      </div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap text-slate-500 font-mono">
                      {formatBytes(doc.file_size)}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap uppercase font-semibold text-slate-600">
                      {doc.document_type || 'PDF'}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2 py-0.5 text-[10px] font-semibold text-emerald-800">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        Vector Indexed
                      </span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap text-slate-500">
                      {formatDate(doc.created_at)}
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap space-x-2">
                      <button
                        onClick={() => onNavigate('/legal-chat')}
                        className="px-2.5 py-1 text-xs font-semibold text-emerald-800 hover:bg-emerald-50 rounded-md transition-colors"
                      >
                        Ask
                      </button>
                      <button
                        onClick={() => void handleDelete(doc.id, doc.original_filename)}
                        className="px-2.5 py-1 text-xs font-semibold text-rose-700 hover:bg-rose-50 rounded-md transition-colors"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
