import React from 'react';
import {
  Scale,
  ArrowRight,
  BookOpen,
  MessageSquareText,
  FileText,
  CheckCircle2,
  ShieldCheck,
  Search,
} from 'lucide-react';

interface LandingPageProps {
  onNavigate: (path: string) => void;
}

export function LandingPage({ onNavigate }: LandingPageProps) {
  return (
    <div className="space-y-20 pb-20 bg-slate-50 text-slate-800">
      <section className="relative bg-slate-900 text-white overflow-hidden py-16 sm:py-24 border-b-4 border-amber-500">
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#c5a880_1px,transparent_1px)] [background-size:24px_24px] pointer-events-none" />

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
            <div className="lg:col-span-7 space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-amber-500/10 border border-amber-500/30 rounded text-amber-400 text-xs font-semibold tracking-widest uppercase">
                <Scale className="w-3.5 h-3.5 text-amber-400" />
                <span>Source-grounded legal research</span>
              </div>

              <h1 className="font-serif-legal text-3xl sm:text-5xl font-bold tracking-wide text-white leading-[1.2]">
                Ask Ethiopian labour law questions with traceable source evidence.
              </h1>

              <p className="text-sm sm:text-base text-slate-300 leading-relaxed max-w-2xl">
                LegalCheck helps teams check probation periods, overtime rules, maternity leave, severance, and related provisions using reviewed legal sources and article-level citations.
              </p>

              <div className="flex flex-wrap items-center gap-4 pt-2">
                <button
                  onClick={() => onNavigate('/legal-chat')}
                  className="inline-flex items-center gap-2.5 px-6 py-3.5 text-xs sm:text-sm font-bold uppercase tracking-wider text-slate-900 bg-amber-400 hover:bg-amber-300 rounded shadow-md transition-all focus:outline-none"
                >
                  <MessageSquareText className="w-4 h-4 text-slate-900" />
                  <span>Ask a Legal Question</span>
                  <ArrowRight className="w-4 h-4" />
                </button>

                <button
                  onClick={() => onNavigate('/legal-sources')}
                  className="inline-flex items-center gap-2 px-6 py-3.5 text-xs sm:text-sm font-bold uppercase tracking-wider text-slate-200 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 hover:border-amber-500/50 rounded transition-all focus:outline-none"
                >
                  <BookOpen className="w-4 h-4 text-amber-400" />
                  <span>Browse Legal Sources</span>
                </button>
              </div>
            </div>

            <div className="lg:col-span-5">
              <div className="rounded-xl border border-amber-500/30 bg-slate-800/60 p-5 shadow-2xl">
                <div className="rounded-lg bg-slate-950 p-5 border border-slate-800">
                  <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-400 mb-4">
                    <span>Evidence review</span>
                    <span className="text-emerald-400">Live</span>
                  </div>
                  <div className="space-y-4">
                    <div className="rounded-lg border border-slate-700 bg-slate-900 p-3">
                      <div className="text-[10px] uppercase tracking-wider text-amber-400 mb-2">Question</div>
                      <div className="text-sm text-slate-100">What are the statutory rules for probation and overtime under Ethiopian labour law?</div>
                    </div>
                    <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-3">
                      <div className="text-[10px] uppercase tracking-wider text-emerald-300 mb-2">Answer summary</div>
                      <div className="text-sm text-slate-100">The answer is grounded in the reviewed source library and cites the relevant legal authority.</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid gap-6 md:grid-cols-3">
          {[
            {
              icon: Search,
              title: 'Retrieval and ranking',
              description: 'Combines keyword and semantic search, with cross-encoder reranking when a model is configured.',
            },
            {
              icon: MessageSquareText,
              title: 'Redis answer caching',
              description: 'Caches successful, evidence-supported answers with their source references. A cache hit returns both without repeating retrieval or generation.',
            },
            {
              icon: FileText,
              title: 'Citations and references',
              description: 'Answers can return article-level references and supporting quotes only when the evidence is validated against the reviewed source records.',
            },
            {
              icon: ShieldCheck,
              title: 'Clear legal limits',
              description: 'The service is designed for legal research support and does not replace qualified legal review or attorney advice.',
            },
          ].map(({ icon: Icon, title, description }) => (
            <div key={title} className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-4 inline-flex rounded-lg bg-amber-100 p-2 text-amber-700">
                <Icon className="w-5 h-5" />
              </div>
              <h2 className="font-serif-legal text-xl font-bold text-slate-900 mb-2">{title}</h2>
              <p className="text-sm text-slate-600 leading-relaxed">{description}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="about" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8 sm:p-12">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
            <div className="lg:col-span-7 space-y-4">
              <div className="text-xs font-bold uppercase tracking-widest text-amber-700">Why LegalCheck</div>
              <h2 className="font-serif-legal text-2xl sm:text-3xl font-bold text-slate-900 tracking-tight leading-snug">
                A clearer way to answer legal questions from the source library.
              </h2>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                LegalCheck is built for source-grounded review of Ethiopian labour law. It surfaces relevant provisions, keeps the evidence trail visible, and helps reviewers check whether the answer is supported before acting on it.
              </p>
              <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                Answers are generated from retrieved legal passages, with the supporting evidence trail visible for users to review.
              </p>
            </div>

            <div className="lg:col-span-5 rounded-xl bg-slate-900 text-white p-6">
              <div className="space-y-4">
                {[
                  'Reviewed legal-source records and article references',
                  'Hybrid retrieval and reranking for relevant evidence',
                  'Transparent citations and no unsupported fallback answers',
                ].map((item) => (
                  <div key={item} className="flex items-start gap-3 text-sm text-slate-200">
                    <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
