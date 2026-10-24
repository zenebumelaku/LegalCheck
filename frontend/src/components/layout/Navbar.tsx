import React, { useState } from 'react';
import {
  Menu,
  X,
  ArrowRight,
  Scale,
  Phone,
  Mail,
  Clock,
  MapPin,
  ShieldCheck,
  BookOpen
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
      {/* Top Utility Bar (Right-of-Law classic legal header) */}
      <div className="bg-slate-900 text-slate-300 text-[11px] py-1.5 px-4 sm:px-6 border-b border-slate-800 hidden sm:block">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-1.5 text-slate-300">
              <MapPin className="w-3 h-3 text-amber-500" />
              <span>Addis Ababa, Ethiopia · Federal Negarit Gazeta Registry</span>
            </div>
            <div className="hidden lg:flex items-center gap-1.5 text-slate-400">
              <Clock className="w-3 h-3 text-slate-400" />
              <span>Mon – Fri: 8:30 AM – 5:30 PM (EAT)</span>
            </div>
          </div>

          <div className="flex items-center gap-5">
            <div className="flex items-center gap-1.5 text-slate-300">
              <Mail className="w-3 h-3 text-amber-500" />
              <span>compliance@legalcheck.et</span>
            </div>
            <div className="flex items-center gap-1.5 text-amber-400 font-medium">
              <Phone className="w-3 h-3" />
              <span>+251 (0) 11 551 8820</span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Navigation Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-8 h-20">
          {/* Brand Mark: Right-of-Law Stately Emblem */}
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
                Labour Law Compliance & Audit
              </span>
            </div>
          </button>

          {/* Nav Links */}
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
              onClick={() => onNavigate('/#practice-areas')}
              className="hover:text-amber-700 transition-colors whitespace-nowrap focus:outline-none py-1 border-b-2 border-transparent"
            >
              Practice Areas
            </button>
            <button
              onClick={() => onNavigate('/#how-it-works')}
              className="hover:text-amber-700 transition-colors whitespace-nowrap focus:outline-none py-1 border-b-2 border-transparent"
            >
              How It Works
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
              onClick={() => onNavigate('/#case-studies')}
              className="hover:text-amber-700 transition-colors whitespace-nowrap focus:outline-none py-1 border-b-2 border-transparent"
            >
              Audit Cases
            </button>
            <button
              onClick={() => onNavigate('/#about')}
              className="hover:text-amber-700 transition-colors whitespace-nowrap focus:outline-none py-1 border-b-2 border-transparent"
            >
              About
            </button>
          </nav>

          {/* Actions */}
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
                  onClick={() => onNavigate('/audits/new')}
                  className="inline-flex items-center gap-1.5 px-4 py-2.5 text-xs font-bold uppercase tracking-wider text-white bg-slate-900 hover:bg-slate-800 border-b-2 border-amber-500 rounded shadow-xs transition-colors whitespace-nowrap shrink-0"
                >
                  <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                  <span>Request Audit</span>
                </button>
              </div>
            )}
          </div>

          {/* Mobile menu trigger */}
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

      {/* Mobile Drawer */}
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
              onNavigate('/#practice-areas');
              setMobileMenuOpen(false);
            }}
            className="block w-full text-left py-2 text-xs font-bold uppercase text-slate-800 hover:text-amber-700"
          >
            Practice Areas
          </button>
          <button
            onClick={() => {
              onNavigate('/#how-it-works');
              setMobileMenuOpen(false);
            }}
            className="block w-full text-left py-2 text-xs font-bold uppercase text-slate-800 hover:text-amber-700"
          >
            How It Works
          </button>
          <button
            onClick={() => {
              onNavigate('/legal-sources');
              setMobileMenuOpen(false);
            }}
            className="block w-full text-left py-2 text-xs font-bold uppercase text-slate-800 hover:text-amber-700"
          >
            Verified Legal Sources
          </button>
          <button
            onClick={() => {
              onNavigate('/#case-studies');
              setMobileMenuOpen(false);
            }}
            className="block w-full text-left py-2 text-xs font-bold uppercase text-slate-800 hover:text-amber-700"
          >
            Audit Cases
          </button>
          <button
            onClick={() => {
              onNavigate('/#about');
              setMobileMenuOpen(false);
            }}
            className="block w-full text-left py-2 text-xs font-bold uppercase text-slate-800 hover:text-amber-700"
          >
            About & Disclaimers
          </button>

          <div className="pt-3 border-t border-slate-100 flex flex-col gap-2">
            {isAuthenticated ? (
              <button
                onClick={() => {
                  onNavigate('/dashboard');
                  setMobileMenuOpen(false);
                }}
                className="w-full text-center py-2.5 text-xs font-bold uppercase text-slate-900 bg-amber-400 rounded"
              >
                Go to Dashboard
              </button>
            ) : (
              <>
                <button
                  onClick={() => {
                    onNavigate('/login');
                    setMobileMenuOpen(false);
                  }}
                  className="w-full text-center py-2 text-xs font-semibold text-slate-700 border border-slate-300 rounded"
                >
                  Sign In
                </button>
                <button
                  onClick={() => {
                    onNavigate('/audits/new');
                    setMobileMenuOpen(false);
                  }}
                  className="w-full text-center py-2.5 text-xs font-bold uppercase text-white bg-slate-900 rounded"
                >
                  Request Contract Audit
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
