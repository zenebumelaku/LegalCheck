import React from 'react';
import { Plus, ChevronRight, Menu, Shield } from 'lucide-react';
import { User } from '../../types';

interface DashboardHeaderProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  currentUser: User | null;
  onToggleMobileNav?: () => void;
}

export function DashboardHeader({
  currentPath,
  onNavigate,
  currentUser,
  onToggleMobileNav
}: DashboardHeaderProps) {
  // Compute breadcrumbs
  const getBreadcrumbs = () => {
    if (currentPath === '/dashboard') return ['Dashboard', 'Overview'];
    if (currentPath === '/audits/new') return ['Audits', 'New Audit'];
    if (currentPath === '/audits') return ['Audits', 'Audit History'];
    if (currentPath.startsWith('/audits/')) return ['Audits', 'Audit Results'];
    if (currentPath === '/legal-sources') return ['Legal Library', 'Proclamations'];
    if (currentPath.startsWith('/legal-sources/')) return ['Legal Library', 'Source Details'];
    if (currentPath === '/settings') return ['Configuration', 'Settings'];
    if (currentPath === '/profile') return ['Account', 'User Profile'];
    return ['Dashboard'];
  };

  const crumbs = getBreadcrumbs();

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-4 sm:px-6 flex items-center justify-between gap-4 sticky top-0 z-30">
      <div className="flex items-center gap-3">
        {onToggleMobileNav && (
          <button
            onClick={onToggleMobileNav}
            className="md:hidden p-2 text-slate-600 hover:text-slate-900 rounded-lg hover:bg-slate-100 focus:outline-none"
            aria-label="Toggle Navigation"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {/* Breadcrumb Trail */}
        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-xs text-slate-500">
          {crumbs.map((crumb, idx) => (
            <React.Fragment key={crumb}>
              {idx > 0 && <ChevronRight className="w-3.5 h-3.5 text-slate-400" />}
              <span className={idx === crumbs.length - 1 ? 'font-semibold text-slate-800' : 'text-slate-500'}>
                {crumb}
              </span>
            </React.Fragment>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <div className="hidden sm:flex items-center gap-1.5 text-xs text-slate-500 border border-slate-200 px-2.5 py-1 rounded-md bg-slate-50">
          <Shield className="w-3.5 h-3.5 text-emerald-600" />
          <span className="font-medium text-slate-700">{currentUser?.organization || 'Addis Tech Solutions PLC'}</span>
        </div>

        {currentPath !== '/audits/new' && (
          <button
            onClick={() => onNavigate('/audits/new')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors whitespace-nowrap shadow-xs"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Audit</span>
          </button>
        )}
      </div>
    </header>
  );
}
