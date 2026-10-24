import React from 'react';
import {
  LayoutDashboard,
  FileCheck2,
  FilePlus2,
  BookOpen,
  Settings,
  User as UserIcon,
  LogOut,
  ShieldCheck,
  ChevronRight,
  Scale
} from 'lucide-react';
import { User } from '../../types';

interface AppSidebarProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  currentUser: User | null;
  onLogout: () => void;
}

export function AppSidebar({
  currentPath,
  onNavigate,
  currentUser,
  onLogout
}: AppSidebarProps) {
  const navItems = [
    {
      label: 'Overview',
      path: '/dashboard',
      icon: LayoutDashboard,
      exact: true
    },
    {
      label: 'New Audit',
      path: '/audits/new',
      icon: FilePlus2
    },
    {
      label: 'Audit History',
      path: '/audits',
      icon: FileCheck2,
      exact: true
    },
    {
      label: 'Legal Sources',
      path: '/legal-sources',
      icon: BookOpen
    },
    {
      label: 'Settings',
      path: '/settings',
      icon: Settings
    },
    {
      label: 'Profile',
      path: '/profile',
      icon: UserIcon
    }
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 min-h-screen border-r border-slate-800">
      {/* Brand */}
      <div className="p-5 border-b border-slate-800">
        <button
          onClick={() => onNavigate('/dashboard')}
          className="flex items-center gap-3 text-left w-full group focus:outline-none"
        >
          <div className="w-9 h-9 rounded bg-slate-950 border border-amber-500/40 text-amber-400 flex items-center justify-center font-bold text-sm shadow-xs group-hover:border-amber-400 transition-colors">
            <Scale className="w-5 h-5 text-amber-400" />
          </div>
          <div className="truncate">
            <div className="font-serif-legal text-xs font-bold text-white tracking-wider">LEGALCHECK</div>
            <div className="text-[10px] text-amber-400/90 font-medium tracking-widest uppercase">Ethiopia Compliance</div>
          </div>
        </button>
      </div>

      {/* Navigation */}
      <div className="flex-1 py-4 px-3 space-y-1">
        <div className="px-3 pb-2 text-[11px] font-semibold tracking-wider text-slate-500 uppercase">
          Workspace
        </div>
        {navItems.map(item => {
          const isActive = item.exact
            ? currentPath === item.path
            : currentPath.startsWith(item.path);
          const Icon = item.icon;

          return (
            <button
              key={item.path}
              onClick={() => onNavigate(item.path)}
              className={`w-full flex items-center justify-between px-3 py-2 text-xs font-medium rounded-lg transition-colors text-left ${
                isActive
                  ? 'bg-slate-800 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-400' : 'text-slate-400'}`} />
                <span>{item.label}</span>
              </div>
              {isActive && <ChevronRight className="w-3.5 h-3.5 text-slate-500" />}
            </button>
          );
        })}
      </div>

      {/* Jurisdiction Tag & Legal Scope */}
      <div className="p-3 mx-3 mb-3 rounded-lg bg-slate-800/60 border border-slate-800 text-[11px] text-slate-400">
        <div className="font-semibold text-slate-300 mb-1">Labour Law Scope</div>
        <div>FDRE Proc. No. 1156/2019</div>
        <div className="text-[10px] text-emerald-400 mt-0.5">Verified Articles & Annotations</div>
      </div>

      {/* Current User & Logout */}
      <div className="p-3 border-t border-slate-800">
        <div className="p-2 rounded-lg bg-slate-800/40 border border-slate-800/60 mb-2">
          <div className="text-xs font-semibold text-slate-200 truncate">
            {currentUser?.fullName || 'Tewodros Kassahun'}
          </div>
          <div className="text-[11px] text-slate-400 truncate">
            {currentUser?.organization || 'Addis Tech Solutions PLC'}
          </div>
        </div>

        <button
          onClick={onLogout}
          className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-400 hover:text-rose-400 hover:bg-slate-800/60 rounded-lg transition-colors text-left"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
}
