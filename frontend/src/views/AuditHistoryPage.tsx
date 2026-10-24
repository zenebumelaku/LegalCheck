import React, { useState, useEffect } from 'react';
import {
  Search,
  Filter,
  Plus,
  FileText,
  Trash2,
  ExternalLink,
  ShieldCheck,
  Calendar,
  AlertCircle,
  FileCheck,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { AuditDocument } from '../types';
import { AuditService } from '../services/audit.service';
import { formatDate, formatBytes } from '../lib/utils';
import { AuditStatusBadge } from '../components/ui/AuditBadges';
import { ConfirmDialog, EmptyState, LoadingSkeleton } from '../components/ui/FeedbackModals';

interface AuditHistoryPageProps {
  onNavigate: (path: string) => void;
}

export function AuditHistoryPage({ onNavigate }: AuditHistoryPageProps) {
  const [audits, setAudits] = useState<AuditDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [sortBy, setSortBy] = useState<'date_desc' | 'date_asc' | 'findings_desc'>('date_desc');

  // Deletion state
  const [auditToDelete, setAuditToDelete] = useState<AuditDocument | null>(null);

  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 8;

  const loadAudits = async () => {
    setLoading(true);
    try {
      const data = await AuditService.listAudits({
        query: searchQuery,
        status: statusFilter,
        documentType: typeFilter,
        sortBy
      });
      setAudits(data);
    } catch (err) {
      console.error('Failed to load audits', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAudits();
  }, [searchQuery, statusFilter, typeFilter, sortBy]);

  const confirmDelete = async () => {
    if (!auditToDelete) return;
    await AuditService.deleteAudit(auditToDelete.id);
    setAuditToDelete(null);
    await loadAudits();
  };

  // Pagination slice
  const totalPages = Math.ceil(audits.length / itemsPerPage) || 1;
  const paginatedAudits = audits.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">
            Compliance Audit History
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-slate-500">
            All evaluated employment agreements and compliance reports across your organization.
          </p>
        </div>

        <button
          onClick={() => onNavigate('/audits/new')}
          className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-xs transition-colors self-start sm:self-auto"
        >
          <Plus className="w-4 h-4" />
          <span>New Audit</span>
        </button>
      </div>

      {/* Search and Filters Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between shadow-xs">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={e => {
              setSearchQuery(e.target.value);
              setCurrentPage(1);
            }}
            placeholder="Search audits by document name or description..."
            className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-slate-200 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900"
          />
        </div>

        {/* Filter controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <select
            value={statusFilter}
            onChange={e => {
              setStatusFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="text-xs rounded-lg border border-slate-200 p-2 bg-slate-50 text-slate-700 focus:outline-none"
          >
            <option value="ALL">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="PENDING">Pending</option>
            <option value="FAILED">Failed</option>
          </select>

          <select
            value={sortBy}
            onChange={e => {
              setSortBy(e.target.value as any);
              setCurrentPage(1);
            }}
            className="text-xs rounded-lg border border-slate-200 p-2 bg-slate-50 text-slate-700 focus:outline-none"
          >
            <option value="date_desc">Newest First</option>
            <option value="date_asc">Oldest First</option>
            <option value="findings_desc">Most Findings</option>
          </select>
        </div>
      </div>

      {/* Audits Table / List */}
      {loading ? (
        <LoadingSkeleton count={4} />
      ) : audits.length === 0 ? (
        <EmptyState
          title="No Audits Found"
          description={
            searchQuery
              ? `No audit documents match "${searchQuery}". Try a different keyword or reset filters.`
              : 'You have not uploaded any contracts for legal compliance auditing yet.'
          }
          actionLabel="Start Your First Audit"
          onAction={() => onNavigate('/audits/new')}
        />
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-[11px]">
                <tr>
                  <th className="py-3 px-4">Document Details</th>
                  <th className="py-3 px-4">Audit Status</th>
                  <th className="py-3 px-4">Compliance Issues</th>
                  <th className="py-3 px-4">Created Date</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {paginatedAudits.map(item => (
                  <tr
                    key={item.id}
                    className="hover:bg-slate-50/80 transition-colors cursor-pointer group"
                    onClick={() => onNavigate(`/audits/${item.id}`)}
                  >
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-slate-100 text-slate-700 border border-slate-200 flex items-center justify-center shrink-0 group-hover:bg-slate-200 transition-colors">
                          <FileText className="w-4 h-4 text-slate-600" />
                        </div>
                        <div className="min-w-0">
                          <div className="font-semibold text-slate-900 truncate">
                            {item.documentName}
                          </div>
                          <div className="text-[11px] text-slate-400 flex items-center gap-2">
                            <span>{item.fileFormat}</span>
                            <span>·</span>
                            <span>{formatBytes(item.fileSize)}</span>
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <AuditStatusBadge status={item.status} />
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap">
                      <div className="flex items-center gap-2 font-mono">
                        {item.criticalCount > 0 ? (
                          <span className="text-rose-700 font-semibold">
                            {item.criticalCount} Critical
                          </span>
                        ) : (
                          <span className="text-emerald-700 font-semibold flex items-center gap-1">
                            <ShieldCheck className="w-3.5 h-3.5" />
                            <span>0 Critical</span>
                          </span>
                        )}
                        <span className="text-slate-300">·</span>
                        <span className="text-slate-500">{item.totalFindings} total</span>
                      </div>
                    </td>

                    <td className="py-3.5 px-4 whitespace-nowrap text-slate-500">
                      {formatDate(item.createdAt)}
                    </td>

                    <td className="py-3.5 px-4 text-right whitespace-nowrap" onClick={e => e.stopPropagation()}>
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => onNavigate(`/audits/${item.id}`)}
                          className="px-2.5 py-1 text-xs font-medium text-slate-700 hover:text-slate-950 hover:bg-slate-100 rounded-md transition-colors"
                        >
                          View Report
                        </button>
                        <button
                          onClick={() => setAuditToDelete(item)}
                          className="p-1.5 text-slate-400 hover:text-rose-600 rounded-md hover:bg-rose-50 transition-colors"
                          title="Delete audit"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
              <div>
                Page <span className="font-semibold text-slate-800">{currentPage}</span> of{' '}
                <span className="font-semibold text-slate-800">{totalPages}</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="p-1.5 rounded border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="p-1.5 rounded border border-slate-200 bg-white hover:bg-slate-100 disabled:opacity-40"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <ConfirmDialog
        isOpen={!!auditToDelete}
        title="Delete Audit Document"
        description={`Are you sure you want to delete "${auditToDelete?.documentName}"? All extracted findings and analysis will be permanently removed.`}
        confirmLabel="Delete Audit"
        cancelLabel="Cancel"
        variant="danger"
        onConfirm={confirmDelete}
        onCancel={() => setAuditToDelete(null)}
      />
    </div>
  );
}
