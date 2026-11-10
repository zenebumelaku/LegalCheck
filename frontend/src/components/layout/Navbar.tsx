import React, { useState } from 'react';
import {
  Menu,
  X,
  ArrowRight,
  Scale,
  BookOpen,
  MessageSquareText,
} from 'lucide-react';

interface NavbarProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  isAuthenticated: boolean;
}

export function Navbar({ currentPath, onNavigate, isAuthenticated }: NavbarProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-slate-200 shadow-xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-8 h-20">
          <button
            onClick={() => onNavigate('/')}
            className="flex items-center gap-3 text-left whitespace-nowrap shrink-0 group focus:outline-none"
          >
            <div className="w-11 h-11 rounded-lg bg-slate-900 border-2 border-amber-500/40 text-amber-400 flex items-center justify-center shadow-md group-hover:border-amber-400 transition-colors">
              <Scale className="w-6 h-6" />
            </div>
            <div className="leading-tight">
              <span className="font-serif-legal text-lg sm:text-xl font-bold tracking-wider text-slate-900 block group-hover:text-amber-800 transition-colors">
                LEGALCHECK ETHIOPIA
              </span>
              <span className="text-[10px] tracking-widest uppercase font-semibold text-amber-700 block">
                Legal Q&A & Source Library
              </span>
            </div>
          </button>

          <nav className="hidden lg:flex items-center gap-7 text-xs font-semibold uppercase tracking-wider text-slate-700">
            <button
              onClick={() => onNavigate('/')}
              className={`hover:text-amber-700 transition-colors whitespace-nowrap focus:outline-none py-1 border-b-2 ${
                currentPath === '/' ? 'border-amber-600 text-slate-900 font-bold' : 'border-transparent'
              }`}
            >
              Home
            </button>
            <button
              onClick={() => onNavigate('/legal-sources')}
              className={`hover:text-amber-700 transition-colors whitespace-nowrap focus:outline-none py-1 border-b-2 ${
                currentPath === '/legal-sources' ? 'border-amber-600 text-slate-900 font-bold' : 'border-transparent'
              }`}
            >
              Legal Sources
            </button>
            <button
              onClick={() => onNavigate('/legal-chat')}
              className={`hover:text-amber-700 transition-colors whitespace-nowrap focus:outline-none py-1 border-b-2 ${
                currentPath === '/legal-chat' ? 'border-amber-600 text-slate-900 font-bold' : 'border-transparent'
              }`}
            >
              Legal Q&A
            </button>
          </nav>

          <div className="hidden sm:flex items-center gap-3 shrink-0">
            {isAuthenticated ? (
              <button
                onClick={() => onNavigate('/dashboard')}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900 bg-amber-400 hover:bg-amber-300 rounded shadow-xs transition-colors whitespace-nowrap shrink-0"
              >
                <span>Dashboard</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            ) : (
              <div className="flex items-center gap-3">
                <button
                  onClick={() => onNavigate('/login')}
                  className="px-3 py-2 text-xs font-semibold text-slate-700 hover:text-slate-900 transition-colors whitespace-nowrap"
                >
                  Sign In
                </button>
                <button
                  onClick={() => onNavigate('/legal-chat')}
                  className="inline-flex items-center gap-1.5 px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-white bg-slate-900 hover:bg-slate-800 border-b-2 border-amber-500 rounded shadow-xs transition-colors whitespace-nowrap shrink-0"
                >
                  <MessageSquareText className="w-3.5 h-3.5 text-amber-400" />
                  <span>Ask a Legal Question</span>
                </button>
              </div>
            )}
          </div>

          <div className="lg:hidden flex items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg text-slate-700 hover:text-slate-900 hover:bg-slate-100 focus:outline-none"
              aria-label="Toggle navigation menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-slate-200 bg-white px-5 py-4 space-y-3 shadow-xl">
          <button
            onClick={() => {
              onNavigate('/');
              setMobileMenuOpen(false);
            }}
            className="block w-full text-left py-2 text-xs font-bold uppercase text-slate-800 hover:text-amber-700"
          >
            Home
          </button>
          <button
            onClick={() => {
              onNavigate('/legal-sources');
              setMobileMenuOpen(false);
            }}
            className="block w-full text-left py-2 text-xs font-bold uppercase text-slate-800 hover:text-amber-700"
          >
            Legal Sources
          </button>
          <button
            onClick={() => {
              onNavigate('/legal-chat');
              setMobileMenuOpen(false);
            }}
            className="block w-full text-left py-2 text-xs font-bold uppercase text-slate-800 hover:text-amber-700"
          >
            Legal Q&A
          </button>
          <button
            onClick={() => {
              onNavigate(isAuthenticated ? '/dashboard' : '/login');
              setMobileMenuOpen(false);
            }}
            className="block w-full text-left py-2 text-xs font-bold uppercase text-slate-800 hover:text-amber-700"
          >
            {isAuthenticated ? 'Dashboard' : 'Sign In'}
          </button>
        </div>
      )}
    </header>
  );
}
