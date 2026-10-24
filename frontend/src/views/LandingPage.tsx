import React, { useState } from 'react';
import {
  Scale,
  ShieldCheck,
  FileText,
  Clock,
  BookOpen,
  Download,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Building2,
  Check,
  Award,
  HelpCircle,
  FileCheck,
  Briefcase,
  Users,
  ChevronRight
} from 'lucide-react';
import { SAMPLE_ETHIOPIAN_CONTRACTS } from '../data/sample-contracts';

interface LandingPageProps {
  onNavigate: (path: string) => void;
}

export function LandingPage({ onNavigate }: LandingPageProps) {
  // Quick intake form state
  const [selectedDocType, setSelectedDocType] = useState('EMPLOYMENT_CONTRACT');
  const [companyName, setCompanyName] = useState('');
  const [companyEmail, setCompanyEmail] = useState('');

  const handleQuickAuditStart = (e: React.FormEvent) => {
    e.preventDefault();
    onNavigate('/audits/new');
  };

  return (
    <div className="space-y-20 pb-20 bg-slate-50 text-slate-800">
      {/* 1. HERO SECTION (Right-of-Law Stately Dark Banner) */}
      <section className="relative bg-slate-900 text-white overflow-hidden py-16 sm:py-24 border-b-4 border-amber-500">
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#c5a880_1px,transparent_1px)] [background-size:24px_24px] pointer-events-none" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            {/* Left Content */}
            <div className="lg:col-span-7 space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-500/10 border border-amber-500/30 rounded text-amber-400 text-xs font-semibold tracking-widest uppercase">
                <Scale className="w-3.5 h-3.5 text-amber-400" />
                <span>FDRE Proclamation No. 1156/2019 Compliance</span>
              </div>

              <h1 className="font-serif-legal text-3xl sm:text-5xl font-bold tracking-wide text-white leading-[1.2]">
                Defending Enterprise Integrity Through Verified Ethiopian Labour Law.
              </h1>

              <p className="text-sm sm:text-base text-slate-300 leading-relaxed max-w-2xl">
                LegalCheck Ethiopia audits employment agreements before execution. Verify statutory probation periods, overtime pay multipliers, 120-day maternity coverage, and non-compete reasonableness with deterministic citations from the Federal Negarit Gazeta.
              </p>

              <div className="flex flex-wrap items-center gap-4 pt-2">
                <button
                  onClick={() => onNavigate('/audits/new')}
                  className="inline-flex items-center gap-2.5 px-6 py-3.5 text-xs sm:text-sm font-bold uppercase tracking-wider text-slate-900 bg-amber-400 hover:bg-amber-300 rounded shadow-md transition-all focus:outline-none"
                >
                  <ShieldCheck className="w-4 h-4 text-slate-900" />
                  <span>Audit an Employment Contract</span>
                  <ArrowRight className="w-4 h-4" />
                </button>

                <button
                  onClick={() => onNavigate('/legal-sources')}
                  className="inline-flex items-center gap-2 px-6 py-3.5 text-xs sm:text-sm font-bold uppercase tracking-wider text-slate-200 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 hover:border-amber-500/50 rounded transition-all focus:outline-none"
                >
                  <BookOpen className="w-4 h-4 text-amber-400" />
                  <span>Browse Negarit Gazeta Library</span>
                </button>
              </div>

              {/* Trust Indicators */}
              <div className="pt-6 border-t border-slate-800 grid grid-cols-2 sm:grid-cols-4 gap-4 text-slate-300">
                <div>
                  <div className="font-serif-legal font-bold text-lg text-amber-400">193 Articles</div>
                  <div className="text-[11px] text-slate-400">Proc. No. 1156/2019</div>
                </div>
                <div>
                  <div className="font-serif-legal font-bold text-lg text-amber-400">60 Days</div>
                  <div className="text-[11px] text-slate-400">Statutory Probation Cap</div>
                </div>
                <div>
                  <div className="font-serif-legal font-bold text-lg text-amber-400">120 Days</div>
                  <div className="text-[11px] text-slate-400">Maternity Mandate</div>
                </div>
                <div>
                  <div className="font-serif-legal font-bold text-lg text-amber-400">100%</div>
                  <div className="text-[11px] text-slate-400">Statutory Citation Match</div>
                </div>
              </div>
            </div>

            {/* Right Visual Image Box (Right-of-Law stately presentation) */}
            <div className="lg:col-span-5">
              <div className="relative rounded-lg p-2 bg-slate-800/60 border-2 border-amber-500/30 shadow-2xl">
                <div className="relative overflow-hidden rounded bg-slate-950">
                  <img
                    src="/src/assets/images/legalcheck_hero_banner_1792788473802.jpg"
                    alt="Ethiopian Legal Chamber and Employment Compliance Auditing"
                    className="w-full h-84 lg:h-96 object-cover opacity-90"
                    referrerPolicy="no-referrer"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent flex flex-col justify-end p-6">
                    <div className="flex items-center gap-2 mb-1.5 text-amber-400 text-xs font-serif-legal font-bold tracking-wider uppercase">
                      <Award className="w-4 h-4" />
                      <span>Official Regulatory Grounding</span>
                    </div>
                    <div className="text-white font-serif-legal font-bold text-base">
                      House of Peoples' Representatives of FDRE
                    </div>
                    <div className="text-xs text-slate-300 mt-1">
                      Federal Negarit Gazeta 25th Year No. 89 · In Force Since Sept 5, 2019
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. ABOUT THE PLATFORM / WELCOME SECTION (Right-of-Law Welcome block) */}
      <section id="about" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 sm:p-12">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
            {/* Left Column: Mission & Identity */}
            <div className="lg:col-span-7 space-y-4">
              <div className="text-xs font-bold uppercase tracking-widest text-amber-700">
                Welcome to LegalCheck Ethiopia
              </div>
              <h2 className="font-serif-legal text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight leading-snug">
                Eliminating Contractual Ambiguity Before the Labour Relations Board.
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                In Ethiopia, employment disputes frequently arise from non-compliant contract drafting: outdated 90-day probation terms, illegal working hour structures exceeding 48 hours per week, unlawful overtime waivers, or references to repealed legislation like Proclamation No. 377/2003.
              </p>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                LegalCheck Ethiopia functions as an automated statutory auditing bridge for Ethiopian commercial enterprises, manufacturing facilities, tech startups, and legal advisors. Every audit provides side-by-side evidence contrasting the contract text against authoritative Negarit Gazeta provisions.
              </p>

              <div className="pt-2 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-slate-700">
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>No Hallucinated Citations</span>
                </div>
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Dual English & Amharic Wording</span>
                </div>
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Strict Corporate Confidentiality</span>
                </div>
                <div className="flex items-center gap-2">
                  <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>Official PDF Report Export</span>
                </div>
              </div>
            </div>

            {/* Right Column: Statutory Credentials Callout */}
            <div className="lg:col-span-5 bg-slate-900 text-white p-7 rounded-lg border-2 border-amber-500/40 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="font-serif-legal font-bold text-sm tracking-wider text-amber-400">
                  STATUTORY PEDIGREE
                </div>
                <Scale className="w-5 h-5 text-amber-400" />
              </div>

              <div className="space-y-3 text-xs text-slate-300">
                <div>
                  <div className="font-bold text-white">Governing Legislation:</div>
                  <div className="text-slate-400">Labour Proclamation No. 1156/2019</div>
                </div>
                <div>
                  <div className="font-bold text-white">Subsidiary Contract Law:</div>
                  <div className="text-slate-400">Civil Code of Ethiopia (1960) Title XVI</div>
                </div>
                <div>
                  <div className="font-bold text-white">Commercial Registry Mandate:</div>
                  <div className="text-slate-400">Proclamation No. 980/2016 Article 22</div>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-800">
                <button
                  onClick={() => onNavigate('/legal-sources')}
                  className="w-full py-2.5 px-3 text-center text-xs font-bold uppercase tracking-wider text-slate-900 bg-amber-400 hover:bg-amber-300 rounded transition-colors"
                >
                  Inspect Annotated Statutes
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 3. PRACTICE AREAS / COMPLIANCE DOMAINS (Right-of-Law Practice Areas Grid) */}
      <section id="practice-areas" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-12">
          <div className="text-xs font-bold uppercase tracking-widest text-amber-700 mb-2">
            Practice Areas & Compliance Domains
          </div>
          <h2 className="font-serif-legal text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Comprehensive Ethiopian Labour Law Coverage
          </h2>
          <p className="mt-2 text-xs sm:text-sm text-slate-600">
            Our rules engine is meticulously cross-referenced with every fundamental division of the 2019 Labour Proclamation.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Card 1: Probation */}
          <div className="bg-white p-6 rounded-lg border border-slate-200 hover:border-amber-500/80 shadow-xs transition-all hover:shadow-md group">
            <div className="w-10 h-10 rounded bg-slate-900 text-amber-400 flex items-center justify-center mb-4 group-hover:bg-amber-400 group-hover:text-slate-900 transition-colors">
              <Clock className="w-5 h-5" />
            </div>
            <div className="text-[11px] font-mono font-semibold text-amber-700 uppercase mb-1">
              Article 9 & 10 · Maximum 60 Days
            </div>
            <h3 className="font-serif-legal text-base font-bold text-slate-900 mb-2">
              Probation Period Auditing
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed mb-4">
              Strict statutory ceiling: probation may not exceed sixty (60) working days. Clauses providing 90 days or 3 months automatically convert workers to permanent status under law.
            </p>
            <button
              onClick={() => onNavigate('/legal-sources')}
              className="text-xs font-bold uppercase text-slate-900 group-hover:text-amber-800 flex items-center gap-1"
            >
              <span>View Article 9 Statutory Text</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Card 2: Hours & Overtime */}
          <div className="bg-white p-6 rounded-lg border border-slate-200 hover:border-amber-500/80 shadow-xs transition-all hover:shadow-md group">
            <div className="w-10 h-10 rounded bg-slate-900 text-amber-400 flex items-center justify-center mb-4 group-hover:bg-amber-400 group-hover:text-slate-900 transition-colors">
              <Briefcase className="w-5 h-5" />
            </div>
            <div className="text-[11px] font-mono font-semibold text-amber-700 uppercase mb-1">
              Article 61 & 66 · 48 Hrs/Wk Max
            </div>
            <h3 className="font-serif-legal text-base font-bold text-slate-900 mb-2">
              Working Hours & Overtime Multipliers
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed mb-4">
              Normal working hours are capped at 8 hrs/day and 48 hrs/week. Overtime must be remunerated at statutory scales (1.5x daytime, 1.75x night, 2.0x rest days, 2.5x holidays).
            </p>
            <button
              onClick={() => onNavigate('/legal-sources')}
              className="text-xs font-bold uppercase text-slate-900 group-hover:text-amber-800 flex items-center gap-1"
            >
              <span>View Article 66 Overtime Scales</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Card 3: Maternity & Special Leaves */}
          <div className="bg-white p-6 rounded-lg border border-slate-200 hover:border-amber-500/80 shadow-xs transition-all hover:shadow-md group">
            <div className="w-10 h-10 rounded bg-slate-900 text-amber-400 flex items-center justify-center mb-4 group-hover:bg-amber-400 group-hover:text-slate-900 transition-colors">
              <Users className="w-5 h-5" />
            </div>
            <div className="text-[11px] font-mono font-semibold text-amber-700 uppercase mb-1">
              Article 88 · 120 Consecutive Days
            </div>
            <h3 className="font-serif-legal text-base font-bold text-slate-900 mb-2">
              Maternity & Family Leave Rights
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed mb-4">
              Maternity leave was expanded from 90 to 120 consecutive paid days (30 days prenatal + 90 days postnatal). Also audits statutory 3-day paternity and mourning leave under Article 81.
            </p>
            <button
              onClick={() => onNavigate('/legal-sources')}
              className="text-xs font-bold uppercase text-slate-900 group-hover:text-amber-800 flex items-center gap-1"
            >
              <span>View Article 88 Mandates</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Card 4: Termination & Severance */}
          <div className="bg-white p-6 rounded-lg border border-slate-200 hover:border-amber-500/80 shadow-xs transition-all hover:shadow-md group">
            <div className="w-10 h-10 rounded bg-slate-900 text-amber-400 flex items-center justify-center mb-4 group-hover:bg-amber-400 group-hover:text-slate-900 transition-colors">
              <Scale className="w-5 h-5" />
            </div>
            <div className="text-[11px] font-mono font-semibold text-amber-700 uppercase mb-1">
              Articles 27, 35 & 39 · Severance
            </div>
            <h3 className="font-serif-legal text-base font-bold text-slate-900 mb-2">
              Termination Notice & Severance
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed mb-4">
              Evaluates statutory graduated notice periods (1 to 3 months based on tenure under Article 35) and verifies severance pay entitlements for non-culpable contract terminations.
            </p>
            <button
              onClick={() => onNavigate('/legal-sources')}
              className="text-xs font-bold uppercase text-slate-900 group-hover:text-amber-800 flex items-center gap-1"
            >
              <span>View Termination Rules</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Card 5: Non-Compete & Restrictive Covenants */}
          <div className="bg-white p-6 rounded-lg border border-slate-200 hover:border-amber-500/80 shadow-xs transition-all hover:shadow-md group">
            <div className="w-10 h-10 rounded bg-slate-900 text-amber-400 flex items-center justify-center mb-4 group-hover:bg-amber-400 group-hover:text-slate-900 transition-colors">
              <FileCheck className="w-5 h-5" />
            </div>
            <div className="text-[11px] font-mono font-semibold text-amber-700 uppercase mb-1">
              Civil Code (1960) · Article 2589
            </div>
            <h3 className="font-serif-legal text-base font-bold text-slate-900 mb-2">
              Non-Compete Restraint Limits
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed mb-4">
              Restraints cannot excessively endanger the economic future of the employee. Unreasonable blanket nationwide or multi-year covenants are void under Ethiopian jurisprudence.
            </p>
            <button
              onClick={() => onNavigate('/legal-sources')}
              className="text-xs font-bold uppercase text-slate-900 group-hover:text-amber-800 flex items-center gap-1"
            >
              <span>View Civil Code Article 2589</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Card 6: Occupational Safety & PPE */}
          <div className="bg-white p-6 rounded-lg border border-slate-200 hover:border-amber-500/80 shadow-xs transition-all hover:shadow-md group">
            <div className="w-10 h-10 rounded bg-slate-900 text-amber-400 flex items-center justify-center mb-4 group-hover:bg-amber-400 group-hover:text-slate-900 transition-colors">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div className="text-[11px] font-mono font-semibold text-amber-700 uppercase mb-1">
              Article 92 · Employer PPE Mandate
            </div>
            <h3 className="font-serif-legal text-base font-bold text-slate-900 mb-2">
              Occupational Safety & Health
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed mb-4">
              Employers must provide certified personal protective equipment (PPE) free of charge. Contracts requiring workers to purchase safety gear violate Article 92(1).
            </p>
            <button
              onClick={() => onNavigate('/legal-sources')}
              className="text-xs font-bold uppercase text-slate-900 group-hover:text-amber-800 flex items-center gap-1"
            >
              <span>View Safety Provisions</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </section>

      {/* 4. CASE AUDITS & PRECEDENT STUDIES (Right-of-Law Case Studies showcase) */}
      <section id="case-studies" className="bg-slate-900 text-white py-16 border-y border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-12">
            <div className="text-xs font-bold uppercase tracking-widest text-amber-400 mb-2">
              Audit Case Studies
            </div>
            <h2 className="font-serif-legal text-2xl sm:text-3xl font-bold tracking-tight">
              Real Ethiopian Commercial Contract Audits
            </h2>
            <p className="mt-2 text-xs sm:text-sm text-slate-400">
              Explore how common contract errors in Addis Ababa businesses are flagged and corrected.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
            {SAMPLE_ETHIOPIAN_CONTRACTS.map((contract, i) => (
              <div
                key={contract.id}
                className="bg-slate-800/90 rounded-lg border border-slate-700/80 p-6 flex flex-col justify-between shadow-sm hover:border-amber-500/60 transition-all h-full"
              >
                <div className="flex-1 flex flex-col">
                  <div className="flex items-center justify-between text-xs font-mono text-amber-400 mb-2 pb-1 border-b border-slate-700/60">
                    <span>Case Study 0{i + 1}</span>
                    <span className="text-slate-400 truncate max-w-[150px]">{contract.organization}</span>
                  </div>

                  <h3 className="font-serif-legal font-bold text-base text-white mb-2 min-h-[44px] leading-snug">
                    {contract.title}
                  </h3>

                  <p className="text-xs text-slate-300 leading-relaxed mb-5 min-h-[52px]">
                    {contract.description}
                  </p>

                  <div className="bg-slate-900/80 rounded-lg border border-slate-700/70 p-3.5 mb-6 flex-1 flex flex-col justify-between">
                    <div className="flex items-center justify-between text-[11px] font-bold text-slate-400 uppercase tracking-wider pb-2 border-b border-slate-800">
                      <span>Statutory Analysis Scope</span>
                      <span className="text-amber-400 font-mono text-[10px]">3 Provisions</span>
                    </div>

                    <div className="space-y-2.5 pt-2.5">
                      {contract.knownIssues.slice(0, 3).map((issue, idx) => {
                        const isCompliant = issue.toLowerCase().includes('compliance confirmed');
                        const match = issue.match(/^(.*?)\s*\((.*?)\)$/);
                        const mainText = match ? match[1] : issue;
                        const citation = match ? match[2] : null;

                        return (
                          <div key={idx} className="flex items-start gap-2.5 text-xs py-1 border-b border-slate-800/60 last:border-0">
                            {isCompliant ? (
                              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                            ) : (
                              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                            )}
                            <span className="flex-1 min-w-0 text-slate-200 leading-snug">
                              <span className="font-medium text-slate-200 block text-xs leading-snug">{mainText}</span>
                              {citation && (
                                <span className="text-[10px] font-mono text-amber-400/90 font-medium block mt-0.5">
                                  {citation}
                                </span>
                              )}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => onNavigate('/audits/new')}
                  className="w-full py-2.5 px-3 text-center text-xs font-bold uppercase tracking-wider text-slate-900 bg-amber-400 hover:bg-amber-300 rounded shadow-xs transition-colors"
                >
                  Test This Audit Live
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 5. HOW IT WORKS WORKFLOW */}
      <section id="how-it-works" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-12">
          <div className="text-xs font-bold uppercase tracking-widest text-amber-700 mb-2">
            Audit Methodology
          </div>
          <h2 className="font-serif-legal text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
            Three Steps to Guaranteed Statutory Alignment
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="bg-white p-6 rounded-lg border border-slate-200 text-center">
            <div className="w-12 h-12 mx-auto rounded-full bg-slate-900 text-amber-400 font-serif-legal font-bold text-xl flex items-center justify-center mb-4">
              01
            </div>
            <h3 className="font-serif-legal font-bold text-base text-slate-900 mb-2">
              Upload Employment Document
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Upload any PDF, DOCX, or text agreement. Text is parsed securely in-memory without persistent training storage.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg border border-slate-200 text-center">
            <div className="w-12 h-12 mx-auto rounded-full bg-slate-900 text-amber-400 font-serif-legal font-bold text-xl flex items-center justify-center mb-4">
              02
            </div>
            <h3 className="font-serif-legal font-bold text-base text-slate-900 mb-2">
              Cross-Reference Proclamation 1156
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Clauses are evaluated against statutory limits: probation, overtime multipliers, leave periods, and termination notice tiers.
            </p>
          </div>

          <div className="bg-white p-6 rounded-lg border border-slate-200 text-center">
            <div className="w-12 h-12 mx-auto rounded-full bg-slate-900 text-amber-400 font-serif-legal font-bold text-xl flex items-center justify-center mb-4">
              03
            </div>
            <h3 className="font-serif-legal font-bold text-base text-slate-900 mb-2">
              Export Official PDF Compliance Report
            </h3>
            <p className="text-xs text-slate-600 leading-relaxed">
              Receive itemized severity levels, exact Negarit Gazeta provision numbers, and downloadable client-ready documentation.
            </p>
          </div>
        </div>
      </section>

      {/* 6. QUICK CONSULTATION / AUDIT INTAKE FORM (Right-of-Law Consultation Module) */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-xl border-2 border-slate-300 shadow-md p-8 sm:p-12">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
            <div className="lg:col-span-6 space-y-4">
              <div className="text-xs font-bold uppercase tracking-widest text-amber-700">
                Direct Legal Consultation & Audit Request
              </div>
              <h2 className="font-serif-legal text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight">
                Request an Immediate Compliance Assessment
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                Whether you are drafting a new employment contract for executive staff, factory operators, or updating your entire corporate template library, LegalCheck gives you clarity before signing.
              </p>
              <div className="p-4 bg-slate-50 rounded border border-slate-200 text-xs text-slate-700 space-y-2">
                <div className="font-bold text-slate-900">Chamber Physical Registry Office:</div>
                <div>Kirkos Sub-City, Woreda 04, Addis Ababa, Ethiopia</div>
                <div>Direct Hotline: +251 (0) 11 551 8820 · compliance@legalcheck.et</div>
              </div>
            </div>

            <form onSubmit={handleQuickAuditStart} className="lg:col-span-6 space-y-4 bg-slate-50 p-6 rounded-lg border border-slate-200">
              <div className="font-serif-legal font-bold text-sm text-slate-900 border-b border-slate-200 pb-2">
                Start Audit Verification
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Organization / Enterprise Name
                </label>
                <input
                  type="text"
                  required
                  value={companyName}
                  onChange={e => setCompanyName(e.target.value)}
                  placeholder="E.g., Ethiopian Logistics S.C."
                  className="w-full text-xs rounded border border-slate-300 p-2.5 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Corporate Email
                </label>
                <input
                  type="email"
                  required
                  value={companyEmail}
                  onChange={e => setCompanyEmail(e.target.value)}
                  placeholder="legal@organization.et"
                  className="w-full text-xs rounded border border-slate-300 p-2.5 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Contract Category
                </label>
                <select
                  value={selectedDocType}
                  onChange={e => setSelectedDocType(e.target.value)}
                  className="w-full text-xs rounded border border-slate-300 p-2.5 bg-white text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900"
                >
                  <option value="EMPLOYMENT_CONTRACT">Indefinite Employment Contract (Proc. 1156/2019)</option>
                  <option value="PROBATION">Probationary Letter (Max 60 Working Days)</option>
                  <option value="TERMINATION">Termination & Severance Agreement</option>
                  <option value="NON_COMPETE">Restrictive Covenant / Non-Compete</option>
                </select>
              </div>

              <button
                type="submit"
                className="w-full py-3 px-4 text-xs font-bold uppercase tracking-wider text-slate-900 bg-amber-400 hover:bg-amber-300 rounded shadow-xs transition-colors flex items-center justify-center gap-2 mt-4"
              >
                <ShieldCheck className="w-4 h-4 text-slate-900" />
                <span>Launch Audit Upload Wizard</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          </div>
        </div>
      </section>

      {/* 7. FREQUENTLY ASKED QUESTIONS */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6">
        <div className="text-center mb-10">
          <div className="text-xs font-bold uppercase tracking-widest text-amber-700 mb-1.5">
            Legal Guidance
          </div>
          <h2 className="font-serif-legal text-2xl font-bold text-slate-900">
            Frequently Asked Questions
          </h2>
        </div>

        <div className="space-y-3">
          {[
            {
              q: 'Does LegalCheck Ethiopia replace an advocate or legal counsel?',
              a: 'No. LegalCheck is an automated compliance intelligence tool that assists HR managers, compliance officers, and legal teams by highlighting statutory provisions and potential discrepancies under Labour Proclamation No. 1156/2019. It does not replace the counsel of a licensed Ethiopian advocate.'
            },
            {
              q: 'What is the maximum legal probation period under Ethiopian law?',
              a: 'Under Article 9(2) of Labour Proclamation No. 1156/2019, the probationary period cannot exceed sixty (60) working days. Any clause specifying 90 days, 3 months, or 6 months is invalid under Ethiopian law.'
            },
            {
              q: 'What is the statutory maternity leave entitlement in Ethiopia?',
              a: 'Under Article 88(2) of Proclamation No. 1156/2019, female employees are entitled to 120 consecutive days of paid maternity leave (30 days prenatal + 90 days postnatal). The previous 90-day standard under repealed Proclamation 377/2003 is obsolete.'
            },
            {
              q: 'Can an Ethiopian business waive overtime compensation in the contract?',
              a: 'No. Article 66 establishes statutory minimum overtime rates (1.5x to 2.5x). Individual employment contracts cannot waive statutory overtime compensation for eligible workers.'
            }
          ].map((faq, idx) => (
            <div key={idx} className="bg-white p-5 rounded-lg border border-slate-200">
              <h3 className="font-serif-legal font-bold text-sm text-slate-900 mb-2 flex items-start gap-2">
                <HelpCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                <span>{faq.q}</span>
              </h3>
              <p className="text-xs text-slate-600 leading-relaxed pl-6">
                {faq.a}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
