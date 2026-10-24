import React, { useState } from 'react';
import { ArrowLeft, ArrowRight, CheckCircle2, ShieldAlert, FileText, Check, Loader2, Info } from 'lucide-react';
import { FileUploadDropzone } from '../components/audits/FileUploadDropzone';
import { AuditService } from '../services/audit.service';
import { AuditDocument } from '../types';

interface NewAuditPageProps {
  onNavigate: (path: string) => void;
}

export function NewAuditPage({ onNavigate }: NewAuditPageProps) {
  const [currentStep, setCurrentStep] = useState<1 | 2 | 3>(1);

  // Step 1: File
  const [fileData, setFileData] = useState<{
    name: string;
    size: number;
    format: 'PDF' | 'DOCX' | 'TXT';
    content: string;
    isSample?: boolean;
    sampleId?: string;
  } | null>(null);

  // Step 2: Document Info
  const [documentType, setDocumentType] = useState<AuditDocument['documentType']>('EMPLOYMENT_CONTRACT');
  const [documentLanguage, setDocumentLanguage] = useState<AuditDocument['documentLanguage']>('ENGLISH');
  const [description, setDescription] = useState('');
  const [reviewOptions, setReviewOptions] = useState({
    checkLegalConflicts: true,
    checkMissingClauses: true,
    checkOutdatedReferences: true
  });

  // Step 3: Submitting state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submissionProgress, setSubmissionProgress] = useState(0);
  const [progressStatus, setProgressStatus] = useState('');
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleNextFromStep1 = () => {
    if (!fileData) return;
    setCurrentStep(2);
  };

  const handleNextFromStep2 = () => {
    setCurrentStep(3);
  };

  const handleConfirmAndSubmit = async () => {
    if (!fileData) return;
    setIsSubmitting(true);
    setSubmitError(null);
    setSubmissionProgress(15);
    setProgressStatus('Uploading document and parsing textual structure...');

    try {
      await new Promise(r => setTimeout(r, 600));
      setSubmissionProgress(45);
      setProgressStatus('Cross-referencing statutory articles in Labour Proclamation No. 1156/2019...');

      await new Promise(r => setTimeout(r, 700));
      setSubmissionProgress(80);
      setProgressStatus('Classifying severity levels and generating audit citations...');

      const created = await AuditService.createAudit({
        documentName: fileData.name,
        documentType,
        documentLanguage,
        fileSize: fileData.size,
        fileFormat: fileData.format,
        reviewOptions,
        description: description.trim() || undefined,
        rawText: fileData.content
      });

      setSubmissionProgress(100);
      setProgressStatus('Audit finalized successfully. Redirecting to findings...');

      await new Promise(r => setTimeout(r, 500));
      onNavigate(`/audits/${created.id}`);
    } catch (err) {
      setIsSubmitting(false);
      setSubmitError(err instanceof Error ? err.message : 'Failed to finalize audit report. Please try again.');
    }
  };

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 sm:px-6">
      {/* Wizard Header */}
      <div className="mb-8">
        <button
          onClick={() => onNavigate('/dashboard')}
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-800 mb-3 focus:outline-none"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </button>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          New Legal Compliance Audit
        </h1>
        <p className="mt-1 text-xs sm:text-sm text-slate-500">
          Evaluate employment agreements against verified Ethiopian Labour Proclamation No. 1156/2019.
        </p>

        {/* Step Indicator */}
        <div className="mt-6 flex items-center justify-between max-w-xl">
          <div className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
              currentStep === 1
                ? 'bg-slate-900 text-white'
                : currentStep > 1
                ? 'bg-emerald-600 text-white'
                : 'bg-slate-200 text-slate-600'
            }`}>
              {currentStep > 1 ? <Check className="w-4 h-4" /> : '1'}
            </div>
            <span className={`text-xs font-medium ${currentStep === 1 ? 'text-slate-900 font-bold' : 'text-slate-500'}`}>
              Upload Document
            </span>
          </div>

          <div className="flex-1 h-0.5 mx-4 bg-slate-200">
            <div className={`h-full bg-emerald-600 transition-all ${
              currentStep === 1 ? 'w-0' : currentStep === 2 ? 'w-1/2' : 'w-full'
            }`} />
          </div>

          <div className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
              currentStep === 2
                ? 'bg-slate-900 text-white'
                : currentStep > 2
                ? 'bg-emerald-600 text-white'
                : 'bg-slate-200 text-slate-600'
            }`}>
              {currentStep > 2 ? <Check className="w-4 h-4" /> : '2'}
            </div>
            <span className={`text-xs font-medium ${currentStep === 2 ? 'text-slate-900 font-bold' : 'text-slate-500'}`}>
              Audit Parameters
            </span>
          </div>

          <div className="flex-1 h-0.5 mx-4 bg-slate-200">
            <div className={`h-full bg-emerald-600 transition-all ${
              currentStep === 3 ? 'w-full' : 'w-0'
            }`} />
          </div>

          <div className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
              currentStep === 3 ? 'bg-slate-900 text-white' : 'bg-slate-200 text-slate-600'
            }`}>
              3
            </div>
            <span className={`text-xs font-medium ${currentStep === 3 ? 'text-slate-900 font-bold' : 'text-slate-500'}`}>
              Confirm & Run
            </span>
          </div>
        </div>
      </div>

      {/* Wizard Step 1: Upload */}
      {currentStep === 1 && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs">
            <h2 className="text-sm font-bold text-slate-900 mb-1">Step 1: Select Employment Contract</h2>
            <p className="text-xs text-slate-500 mb-4">
              Upload your agreement or pick a pre-loaded real Ethiopian business scenario.
            </p>

            <FileUploadDropzone
              selectedFile={fileData}
              onFileSelect={setFileData}
              onClearFile={() => setFileData(null)}
            />
          </div>

          <div className="flex justify-end">
            <button
              onClick={handleNextFromStep1}
              disabled={!fileData}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg shadow-xs transition-colors"
            >
              <span>Continue to Audit Parameters</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Wizard Step 2: Document Info */}
      {currentStep === 2 && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-6">
            <h2 className="text-sm font-bold text-slate-900 mb-1">Step 2: Document Information & Audit Scope</h2>
            <p className="text-xs text-slate-500">
              Configure jurisdiction scope, document language, and audit rules.
            </p>

            {/* Document Type */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Document Type
              </label>
              <select
                value={documentType}
                onChange={e => setDocumentType(e.target.value as AuditDocument['documentType'])}
                className="w-full text-xs rounded-lg border border-slate-300 p-2.5 text-slate-900 bg-white focus:ring-2 focus:ring-slate-900 focus:outline-none"
              >
                <option value="EMPLOYMENT_CONTRACT">Employment Contract (Labour Proclamation No. 1156/2019)</option>
                <option value="COLLECTIVE_AGREEMENT">Collective Agreement (Articles 134-143)</option>
                <option value="COMPANY_BYLAW">Company Internal Bylaw / Work Rules</option>
                <option value="CONSULTANCY_AGREEMENT">Independent Consultancy Agreement (Civil Code)</option>
              </select>
            </div>

            {/* Document Language */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Document Language
              </label>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { value: 'ENGLISH', label: 'English' },
                  { value: 'AMHARIC', label: 'Amharic (አማርኛ)' },
                  { value: 'MIXED', label: 'Bilingual / Mixed' }
                ].map(opt => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setDocumentLanguage(opt.value as AuditDocument['documentLanguage'])}
                    className={`py-2 px-3 text-xs font-medium rounded-lg border text-center transition-all ${
                      documentLanguage === opt.value
                        ? 'border-slate-900 bg-slate-900 text-white'
                        : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-slate-100'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Review Options */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-2">
                Active Audit Verifications
              </label>
              <div className="space-y-3">
                <label className="flex items-start gap-3 p-3 rounded-lg border border-slate-200 bg-slate-50/50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={reviewOptions.checkLegalConflicts}
                    onChange={e => setReviewOptions({ ...reviewOptions, checkLegalConflicts: e.target.checked })}
                    className="mt-0.5 rounded border-slate-300 text-slate-900 focus:ring-slate-900"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-900 block">
                      Potential Legal Conflicts & Rights Infringements
                    </span>
                    <span className="text-[11px] text-slate-500">
                      Evaluates statutory limits on probation (max 60 days), maximum working hours (48 hrs/wk), mandatory 120-day maternity leave, overtime rates, and rest days.
                    </span>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 rounded-lg border border-slate-200 bg-slate-50/50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={reviewOptions.checkMissingClauses}
                    onChange={e => setReviewOptions({ ...reviewOptions, checkMissingClauses: e.target.checked })}
                    className="mt-0.5 rounded border-slate-300 text-slate-900 focus:ring-slate-900"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-900 block">
                      Missing or Incomplete Mandatory Clauses
                    </span>
                    <span className="text-[11px] text-slate-500">
                      Identifies missing statutory elements: notice periods (Article 35), severance references (Article 39), and paternity leave (Article 81).
                    </span>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-3 rounded-lg border border-slate-200 bg-slate-50/50 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={reviewOptions.checkOutdatedReferences}
                    onChange={e => setReviewOptions({ ...reviewOptions, checkOutdatedReferences: e.target.checked })}
                    className="mt-0.5 rounded border-slate-300 text-slate-900 focus:ring-slate-900"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-900 block">
                      Outdated or Repealed Legal Citations
                    </span>
                    <span className="text-[11px] text-slate-500">
                      Flags references to repealed statutes such as Labour Proclamation No. 377/2003 or obsolete ministerial regulations.
                    </span>
                  </div>
                </label>
              </div>
            </div>

            {/* Optional Description */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                Audit Notes / Document Context (Optional)
              </label>
              <textarea
                value={description}
                onChange={e => setDescription(e.target.value)}
                rows={2}
                placeholder="E.g., Updated employment template for engineering department recruits in Addis Ababa office..."
                className="w-full text-xs rounded-lg border border-slate-300 p-2.5 text-slate-900 focus:ring-2 focus:ring-slate-900 focus:outline-none"
              />
            </div>

            {/* Scope Limitations Callout */}
            <div className="p-3.5 bg-blue-50/60 rounded-lg border border-blue-200 flex items-start gap-3 text-xs text-blue-900">
              <Info className="w-4 h-4 text-blue-700 shrink-0 mt-0.5" />
              <div className="leading-relaxed">
                <span className="font-semibold block mb-0.5">Scope & Limitations:</span>
                This release audits contracts exclusively under Ethiopian Labour Proclamation No. 1156/2019 and relevant Civil Code service principles. Sectoral collective agreements and managerial exemptions may require specialized manual legal review.
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between">
            <button
              onClick={() => setCurrentStep(1)}
              className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded-lg bg-white"
            >
              Back
            </button>
            <button
              onClick={handleNextFromStep2}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 rounded-lg shadow-xs transition-colors"
            >
              <span>Continue to Confirmation</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Wizard Step 3: Confirmation */}
      {currentStep === 3 && (
        <div className="space-y-6">
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-5">
            <h2 className="text-sm font-bold text-slate-900 mb-1">Step 3: Review Audit Parameters & Submit</h2>
            <p className="text-xs text-slate-500">
              Please verify your selections before initiating automated compliance analysis.
            </p>

            <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 space-y-3 text-xs">
              <div className="flex items-center justify-between py-1 border-b border-slate-200">
                <span className="text-slate-500">Document File:</span>
                <span className="font-semibold text-slate-900">{fileData?.name}</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-200">
                <span className="text-slate-500">Document Type:</span>
                <span className="font-semibold text-slate-900">{documentType}</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-200">
                <span className="text-slate-500">Document Language:</span>
                <span className="font-semibold text-slate-900">{documentLanguage}</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-200">
                <span className="text-slate-500">Primary Legal Baseline:</span>
                <span className="font-semibold text-emerald-800">Labour Proclamation No. 1156/2019</span>
              </div>
              <div className="flex items-start justify-between py-1">
                <span className="text-slate-500">Active Checks:</span>
                <div className="text-right space-y-0.5 font-medium text-slate-800">
                  {reviewOptions.checkLegalConflicts && <div>· Potential Legal Conflicts</div>}
                  {reviewOptions.checkMissingClauses && <div>· Missing Mandatory Clauses</div>}
                  {reviewOptions.checkOutdatedReferences && <div>· Repealed Proclamation Citations</div>}
                </div>
              </div>
            </div>

            {/* Submission Progress bar when submitting */}
            {isSubmitting && (
              <div className="p-4 bg-emerald-50/50 rounded-lg border border-emerald-200 space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-emerald-950 flex items-center gap-2">
                    <Loader2 className="w-4 h-4 text-emerald-700 animate-spin" />
                    <span>{progressStatus}</span>
                  </span>
                  <span className="font-mono font-bold text-emerald-800">{submissionProgress}%</span>
                </div>
                <div className="w-full bg-slate-200 h-2 rounded-full overflow-hidden">
                  <div
                    className="bg-emerald-600 h-full transition-all duration-300"
                    style={{ width: `${submissionProgress}%` }}
                  />
                </div>
              </div>
            )}

            {submitError && (
              <div className="p-3 bg-rose-50 text-rose-800 border border-rose-200 rounded-lg text-xs">
                {submitError}
              </div>
            )}
          </div>

          <div className="flex items-center justify-between">
            <button
              onClick={() => setCurrentStep(2)}
              disabled={isSubmitting}
              className="px-4 py-2 text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded-lg bg-white disabled:opacity-50"
            >
              Back
            </button>
            <button
              onClick={handleConfirmAndSubmit}
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 px-6 py-2.5 text-xs font-semibold text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-60 rounded-lg shadow-xs transition-colors"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Auditing Contract...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                  <span>Confirm & Run Compliance Audit</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
