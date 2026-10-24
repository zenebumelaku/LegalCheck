import React from 'react';
import { Scale, MapPin, Phone, Mail, Clock, ShieldCheck, ExternalLink, ArrowRight } from 'lucide-react';

export function Footer({ onNavigate }: { onNavigate: (path: string) => void }) {
  return (
    <footer className="bg-slate-950 text-slate-400 border-t-4 border-amber-500 text-xs">
      {/* Top Banner strip */}
      <div className="bg-slate-900 border-b border-slate-800 py-6 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded bg-slate-950 border border-amber-500/40 text-amber-400 flex items-center justify-center font-bold">
              <Scale className="w-5 h-5" />
            </div>
            <div>
              <div className="font-serif-legal font-bold text-sm text-white">
                LEGALCHECK ETHIOPIA · LABOUR LAW AUDITING
              </div>
              <div className="text-[11px] text-amber-400">
                FDRE Negarit Gazeta Proclamation No. 1156/2019 Legal Engine
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => onNavigate('/audits/new')}
              className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold uppercase tracking-wider text-slate-900 bg-amber-400 hover:bg-amber-300 rounded transition-colors"
            >
              <span>Start Contract Audit</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Main 4-Column Footer */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 mb-12">
          {/* Col 1: About & Registry */}
          <div className="space-y-3">
            <div className="font-serif-legal font-bold text-sm text-white flex items-center gap-2">
              <span>About LegalCheck</span>
            </div>
            <p className="text-slate-400 leading-relaxed text-xs">
              Specialized legal tech compliance platform assisting Ethiopian businesses, HR departments, and authorized legal reviewers in preventing labour disputes through automated statutory verification.
            </p>
            <div className="text-[11px] text-amber-400/90 font-medium pt-1">
              Federal Negarit Gazeta 25th Year No. 89
            </div>
          </div>

          {/* Col 2: Practice Areas */}
          <div>
            <h4 className="font-serif-legal font-bold text-xs uppercase tracking-wider text-amber-400 mb-3.5">
              Practice Areas
            </h4>
            <ul className="space-y-2">
              <li>
                <button onClick={() => onNavigate('/legal-sources')} className="hover:text-white transition-colors">
                  Probation Clauses (Max 60 Days)
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('/legal-sources')} className="hover:text-white transition-colors">
                  Working Hours (Cap 48 Hrs/Wk)
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('/legal-sources')} className="hover:text-white transition-colors">
                  Statutory Overtime Scales (Art. 66)
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('/legal-sources')} className="hover:text-white transition-colors">
                  Maternity Coverage (120 Days)
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('/legal-sources')} className="hover:text-white transition-colors">
                  Severance & Termination Notice
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('/legal-sources')} className="hover:text-white transition-colors">
                  Restrictive Covenants (Civil Code 2589)
                </button>
              </li>
            </ul>
          </div>

          {/* Col 3: Navigation */}
          <div>
            <h4 className="font-serif-legal font-bold text-xs uppercase tracking-wider text-amber-400 mb-3.5">
              Platform Links
            </h4>
            <ul className="space-y-2">
              <li>
                <button onClick={() => onNavigate('/')} className="hover:text-white transition-colors">
                  Home Overview
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('/dashboard')} className="hover:text-white transition-colors">
                  Compliance Dashboard
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('/audits/new')} className="hover:text-white transition-colors">
                  Document Audit Wizard
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('/audits')} className="hover:text-white transition-colors">
                  Audit History Records
                </button>
              </li>
              <li>
                <button onClick={() => onNavigate('/legal-sources')} className="hover:text-white transition-colors">
                  Annotated Statutes Repository
                </button>
              </li>
            </ul>
          </div>

          {/* Col 4: Contact & Office */}
          <div>
            <h4 className="font-serif-legal font-bold text-xs uppercase tracking-wider text-amber-400 mb-3.5">
              Chamber Office
            </h4>
            <ul className="space-y-2.5 text-xs text-slate-300">
              <li className="flex items-start gap-2">
                <MapPin className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                <span>Kirkos Sub-City, Woreda 04, Addis Ababa, Ethiopia</span>
              </li>
              <li className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-amber-400 shrink-0" />
                <span>Mon – Fri: 8:30 AM – 5:30 PM (EAT)</span>
              </li>
              <li className="flex items-center gap-2">
                <Phone className="w-4 h-4 text-amber-400 shrink-0" />
                <span>+251 (0) 11 551 8820</span>
              </li>
              <li className="flex items-center gap-2">
                <Mail className="w-4 h-4 text-amber-400 shrink-0" />
                <span>compliance@legalcheck.et</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Legal Disclaimer Box */}
        <div className="pt-8 border-t border-slate-800 text-[11px] text-slate-400 space-y-2">
          <p className="font-semibold text-slate-300">STATUTORY DISCLAIMER & REGULATORY NOTICE:</p>
          <p className="leading-relaxed">
            LegalCheck Ethiopia is an automated legal compliance auditing tool engineered to assist enterprise HR departments and corporate reviewers by flagging statutory provisions under Ethiopian Labour Proclamation No. 1156/2019 and relevant Civil Code sections. It does NOT constitute formal advocate representation, attorney-client privilege, or formal legal advice. The platform does not guarantee complete compliance or replace consultation with licensed Ethiopian advocates.
          </p>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pt-4 text-slate-400 text-xs gap-2">
            <div>
              © 2026 LegalCheck Ethiopia. All rights reserved.
            </div>
            <div className="flex items-center gap-4">
              <span>Federal Democratic Republic of Ethiopia</span>
              <span>·</span>
              <button onClick={() => onNavigate('/legal-sources')} className="hover:text-white">
                Proclamation Repository
              </button>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
