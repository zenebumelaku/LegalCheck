import React, { useState, useEffect } from 'react';
import {
  Plus,
  FileCheck2,
  Clock,
  ShieldAlert,
  ArrowRight,
  BookOpen,
  Settings,
  ShieldCheck,
  FileText,
  AlertTriangle
} from 'lucide-react';
import { AuditDocument, AuditStatistics, User } from '../types';
import { AuditService } from '../services/audit.service';
import { formatDate, formatBytes } from '../lib/utils';
import { AuditStatusBadge } from '../components/ui/AuditBadges';
import { EmptyState, LoadingSkeleton } from '../components/ui/FeedbackModals';

interface DashboardPageProps {
  onNavigate: (path: string) => void;
  currentUser: User | null;
}

export function DashboardPage({ onNavigate, currentUser }: DashboardPageProps) {
  const [stats, setStats] = useState<AuditStatistics | null>(null);
  const [recentAudits, setRecentAudits] = useState<AuditDocument[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadDashboardData() {
      setLoading(true);
      try {
        const [statsData, auditsData] = await Promise.all([
          AuditService.getStatistics(),
          AuditService.listAudits({ sortBy: 'date_desc' })
        ]);
        setStats(statsData);
        setRecentAudits(auditsData.slice(0, 5));
      } catch (err) {
        console.error('Failed to load dashboard metrics', err);
      } finally {
        setLoading(false);
      }
    }
    loadDashboardData();
  }, []);

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 space-y-8">
      {/* Welcome Banner */}
      <div className="bg-slate-900 text-white rounded-xl border-l-4 border-amber-500 p-6 sm:p-8 flex flex-col md:flex-row md:items-center md:justify-between gap-6 shadow-sm">
        <div className="space-y-1.5">
          <div className="text-[11px] font-bold text-amber-400 tracking-widest uppercase">
            Ethiopian Labour Law Compliance Chamber · Proclamation No. 1156/2019
          </div>
          <h1 className="font-serif-legal text-xl sm:text-2xl font-bold tracking-wide text-white">
            Welcome, {currentUser?.fullName || 'Tewodros Kassahun'}
          </h1>
          <p className="text-xs sm:text-sm text-slate-300 max-w-xl leading-relaxed">
            Active compliance console for <span className="text-white font-semibold">{currentUser?.organization || 'Addis Tech Solutions PLC'}</span>. All contracts are verified against controlling Negarit Gazeta provisions.
          </p>
        </div>

        <button
          onClick={() => onNavigate('/audits/new')}
          className="inline-flex items-center justify-center gap-2 px-5 py-3 text-xs font-bold uppercase tracking-wider text-slate-900 bg-amber-400 hover:bg-amber-300 rounded shadow-md transition-colors shrink-0"
        >
          <Plus className="w-4 h-4" />
          <span>New Document Audit</span>
        </button>
      </div>

      {/* Real Statistics Metric Cards */}
      {loading ? (
        <LoadingSkeleton count={3} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Audits */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-medium">Total Audited Contracts</span>
              <FileCheck2 className="w-4 h-4 text-slate-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-slate-900 tabular-nums">
              {stats?.totalAudits || 0}
            </div>
            <div className="mt-1 text-[11px] text-slate-400">
              Employment agreements on record
            </div>
          </div>

          {/* Completed Audits */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-medium">Completed Audits</span>
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
            </div>
            <div className="text-2xl font-bold font-mono text-emerald-800 tabular-nums">
              {stats?.completedAudits || 0}
            </div>
            <div className="mt-1 text-[11px] text-slate-400">
              Finalized compliance reports
            </div>
          </div>

          {/* Critical Issues Identified */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-medium">Critical Issues Flagged</span>
              <AlertTriangle className="w-4 h-4 text-rose-600" />
            </div>
            <div className="text-2xl font-bold font-mono text-rose-800 tabular-nums">
              {stats?.criticalIssuesFound || 0}
            </div>
            <div className="mt-1 text-[11px] text-slate-400">
              Violations needing immediate amendment
            </div>
          </div>

          {/* Audits Awaiting Processing */}
          <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
            <div className="flex items-center justify-between text-slate-500 mb-2">
              <span className="text-xs font-medium">Awaiting Processing</span>
              <Clock className="w-4 h-4 text-slate-400" />
            </div>
            <div className="text-2xl font-bold font-mono text-slate-900 tabular-nums">
              {stats?.awaitingAudits || 0}
            </div>
            <div className="mt-1 text-[11px] text-slate-400">
              Documents in active queue
            </div>
          </div>
        </div>
      )}

      {/* Recent Audits Table Section */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-xs">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Recent Contract Audits</h2>
            <p className="text-xs text-slate-500">Most recent compliance evaluations for your organization</p>
          </div>
          <button
            onClick={() => onNavigate('/audits')}
            className="inline-flex items-center gap-1 text-xs font-semibold text-slate-800 hover:text-slate-950"
          >
            <span>View All Audits</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        {recentAudits.length === 0 ? (
          <div className="p-6">
            <EmptyState
              title="No Audits Performed Yet"
              description="Upload an employment contract to initiate your first verified compliance assessment under Labour Proclamation No. 1156/2019."
              actionLabel="Upload First Contract"
              onAction={() => onNavigate('/audits/new')}
            />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase text-[11px]">
                <tr>
                  <th className="py-3 px-4">Document</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Compliance Issues</th>
                  <th className="py-3 px-4">Date Audited</th>
                  <th className="py-3 px-4 text-right">Report</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 text-slate-700">
                {recentAudits.map(audit => (
                  <tr
                    key={audit.id}
                    onClick={() => onNavigate(`/audits/${audit.id}`)}
                    className="hover:bg-slate-50 cursor-pointer transition-colors"
                  >
                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-900 truncate max-w-xs">
                        {audit.documentName}
                      </div>
                      <div className="text-[11px] text-slate-400">
                        {audit.fileFormat} · {formatBytes(audit.fileSize)}
                      </div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      <AuditStatusBadge status={audit.status} />
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap font-mono">
                      {audit.criticalCount > 0 ? (
                        <span className="text-rose-700 font-semibold">
                          {audit.criticalCount} Critical
                        </span>
                      ) : (
                        <span className="text-emerald-700 font-semibold">0 Critical</span>
                      )}
                      <span className="text-slate-300 mx-1.5">·</span>
                      <span className="text-slate-500">{audit.totalFindings} findings</span>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap text-slate-500">
                      {formatDate(audit.createdAt)}
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={e => {
                          e.stopPropagation();
                          onNavigate(`/audits/${audit.id}`);
                        }}
                        className="px-2.5 py-1 text-xs font-medium text-slate-800 hover:bg-slate-100 rounded-md transition-colors"
                      >
                        Open
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick Access Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Verified Legal Sources Link */}
        <div
          onClick={() => onNavigate('/legal-sources')}
          className="bg-white p-5 rounded-xl border border-slate-200 hover:border-slate-300 transition-all cursor-pointer group shadow-xs"
        >
          <div className="flex items-start justify-between">
            <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center justify-center mb-3">
              <BookOpen className="w-5 h-5" />
            </div>
            <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-slate-900 transition-colors" />
          </div>
          <h3 className="text-sm font-bold text-slate-900 mb-1">
            Browse Verified Ethiopian Legal Sources
          </h3>
          <p className="text-xs text-slate-500 leading-relaxed">
            Inspect Labour Proclamation No. 1156/2019 articles, Civil Code provisions, and Gazeta annotations.
          </p>
        </div>

        {/* Workspace Settings */}
        <div
          onClick={() => onNavigate('/settings')}
          className="bg-white p-5 rounded-xl border border-slate-200 hover:border-slate-300 transition-all cursor-pointer group shadow-xs"
        >
          <div className="flex items-start justify-between">
            <div className="w-9 h-9 rounded-lg bg-slate-100 text-slate-700 border border-slate-200 flex items-center justify-center mb-3">
              <Settings className="w-5 h-5" />
            </div>
            <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-slate-900 transition-colors" />
          </div>
          <h3 className="text-sm font-bold text-slate-900 mb-1">
            Data Retention & Security Settings
          </h3>
          <p className="text-xs text-slate-500 leading-relaxed">
            Configure automated audit deletion windows, organization metadata, and compliance disclaimer records.
          </p>
        </div>
      </div>
    </div>
  );
}
