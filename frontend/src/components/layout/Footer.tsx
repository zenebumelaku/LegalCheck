import React from 'react';
import { Scale, MapPin, Phone, Mail, Clock, ArrowRight, BookOpen, MessageSquareText } from 'lucide-react';

export function Footer({ onNavigate }: { onNavigate: (path: string) => void }) {
  return (
    <footer className="bg-slate-950 text-slate-400 border-t-4 border-amber-500 text-xs">
      <div className="bg-slate-900 border-b border-slate-800 py-6 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded bg-slate-950 border border-amber-500/40 text-amber-400 flex items-center justify-center font-bold">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <div className="font-serif-legal font-bold text-sm text-white">
                LEGALCHECK ETHIOPIA · SOURCE-GROUNDED LEGAL Q&A
              </div>
              <div className="text-[11px] text-amber-400">
                Ethiopian labour law questions backed by reviewed legal-source evidence
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => onNavigate('/legal-chat')}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900 bg-amber-400 hover:bg-amber-300 rounded transition-colors"
            >
              <span>Ask a Legal Question</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-12">
          <div className="space-y-3">
            <div className="font-serif-legal font-bold text-sm text-white flex items-center gap-2">
              <span>About LegalCheck</span>
            </div>
            <p className="text-slate-400 leading-relaxed text-xs">
              LegalCheck helps users explore Ethiopian labour law through reviewed source records, article-level citations, and a legal Q&A workflow grounded in the available legal corpus.
            </p>
            <div className="text-[11px] text-amber-400/90 font-medium pt-1">
              Source-backed answers are not legal advice.
            </div>
          </div>

          <div>
            <h4 className="font-serif-legal font-bold text-xs uppercase tracking-wider text-amber-400 mb-3.5">
              Explore
            </h4>
            <ul className="space-y-2">
              <li>
                <button onClick={() => onNavigate('/legal-chat')} className="hover:text-white transition-colors flex items-center gap-2">
                  <MessageSquareText className="w-3.5 h-3.5 text-amber-400" />
                  Legal Q&A
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('/legal-sources')} className="hover:text-white transition-colors flex items-center gap-2">
                  <BookOpen className="w-3.5 h-3.5 text-amber-400" />
                  Legal Sources
                </button>
              </li>
            </ul>
          </div>

          <div>
            <h4 className="font-serif-legal font-bold text-xs uppercase tracking-wider text-amber-400 mb-3.5">
              Platform Links
            </h4>
            <ul className="space-y-2">
              <li><button onClick={() => onNavigate('/')} className="hover:text-white transition-colors">Home Overview</button></li>
              <li><button onClick={() => onNavigate('/dashboard')} className="hover:text-white transition-colors">Workspace Dashboard</button></li>
              <li><button onClick={() => onNavigate('/legal-sources')} className="hover:text-white transition-colors">Annotated Source Library</button></li>
            </ul>
          </div>

          <div>
            <h4 className="font-serif-legal font-bold text-xs uppercase tracking-wider text-amber-400 mb-3.5">
              Office
            </h4>
            <ul className="space-y-2.5 text-xs text-slate-300">
              <li className="flex items-start gap-2"><MapPin className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" /><span>Kirkos Sub-City, Woreda 04, Addis Ababa, Ethiopia</span></li>
              <li className="flex items-center gap-2"><Clock className="w-4 h-4 text-amber-400 shrink-0" /><span>Mon – Fri: 8:30 AM – 5:30 PM (EAT)</span></li>
              <li className="flex items-center gap-2"><Phone className="w-4 h-4 text-amber-400 shrink-0" /><span>+251 (0) 11 551 8820</span></li>
              <li className="flex items-center gap-2"><Mail className="w-4 h-4 text-amber-400 shrink-0" /><span>compliance@legalcheck.et</span></li>
            </ul>
          </div>
        </div>

        <div className="pt-8 border-t border-slate-800 text-[11px] text-slate-400 space-y-2">
          <p className="font-semibold text-slate-300">LEGAL DISCLAIMER</p>
          <p className="leading-relaxed">
            LegalCheck Ethiopia provides source-grounded legal information and article references for research and review. It does not replace legal counsel or guarantee the current applicability of a rule to a specific situation.
          </p>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pt-4 text-slate-400 text-xs gap-2">
            <div>© 2026 LegalCheck Ethiopia. All rights reserved.</div>
            <div className="flex items-center gap-4">
              <span>Federal Democratic Republic of Ethiopia</span>
              <span>·</span>
              <button onClick={() => onNavigate('/legal-sources')} className="hover:text-white">Source Repository</button>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
