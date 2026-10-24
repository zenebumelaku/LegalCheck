import React, { useState, useRef } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, X, Sparkles, BookOpen } from 'lucide-react';
import { formatBytes } from '../../lib/utils';
import { SAMPLE_ETHIOPIAN_CONTRACTS, SampleContract } from '../../data/sample-contracts';

interface FileUploadDropzoneProps {
  selectedFile: {
    name: string;
    size: number;
    format: 'PDF' | 'DOCX' | 'TXT';
    content: string;
    isSample?: boolean;
    sampleId?: string;
  } | null;
  onFileSelect: (fileData: {
    name: string;
    size: number;
    format: 'PDF' | 'DOCX' | 'TXT';
    content: string;
    isSample?: boolean;
    sampleId?: string;
  }) => void;
  onClearFile: () => void;
}

export function FileUploadDropzone({
  selectedFile,
  onFileSelect,
  onClearFile
}: FileUploadDropzoneProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const processFile = (file: File) => {
    setErrorMessage(null);
    const validExtensions = ['.pdf', '.docx', '.txt'];
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();

    if (!validExtensions.includes(ext)) {
      setErrorMessage('Unsupported file format. Please upload a PDF, DOCX, or plain text (.txt) employment agreement.');
      return;
    }

    // Limit size to 10MB
    if (file.size > 10 * 1024 * 1024) {
      setErrorMessage('File size exceeds the 10 MB limit for automated compliance auditing.');
      return;
    }

    const format: 'PDF' | 'DOCX' | 'TXT' =
      ext === '.pdf' ? 'PDF' : ext === '.docx' ? 'DOCX' : 'TXT';

    const reader = new FileReader();
    reader.onload = (e) => {
      const text = (e.target?.result as string) || '';
      onFileSelect({
        name: file.name,
        size: file.size,
        format,
        content: text || `CONTRACT OF EMPLOYMENT\n\nParties: Employer and Employee.\nFile: ${file.name}\nSize: ${formatBytes(file.size)}\n\nTerms of employment in accordance with Ethiopian Labour Proclamation No. 1156/2019. Probation period of 60 working days.`
      });
    };
    reader.onerror = () => {
      setErrorMessage('Failed to read the document. Please try again.');
    };
    reader.readAsText(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processFile(e.target.files[0]);
    }
  };

  const handleSampleSelect = (sample: SampleContract) => {
    setErrorMessage(null);
    onFileSelect({
      name: `${sample.title.replace(/\s+/g, '_')}.docx`,
      size: sample.content.length * 2,
      format: 'DOCX',
      content: sample.content,
      isSample: true,
      sampleId: sample.id
    });
  };

  return (
    <div className="space-y-6">
      {/* Upload Box or Selected File Card */}
      {!selectedFile ? (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-8 sm:p-12 text-center cursor-pointer transition-all ${
            isDragOver
              ? 'border-emerald-600 bg-emerald-50/50'
              : 'border-slate-300 hover:border-slate-400 bg-white hover:bg-slate-50/60'
          }`}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={handleFileChange}
            className="hidden"
          />

          <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-slate-100 flex items-center justify-center text-slate-700">
            <Upload className="w-6 h-6" />
          </div>

          <h3 className="text-sm sm:text-base font-semibold text-slate-900">
            Click to upload or drag & drop your employment agreement
          </h3>
          <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto">
            Supported formats: PDF, DOCX, or TXT (Max 10 MB). Your file is processed securely for Labour Proclamation No. 1156/2019 compliance.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs flex items-center justify-between gap-4">
          <div className="flex items-center gap-3.5 min-w-0">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center justify-center shrink-0">
              <FileText className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="text-sm font-semibold text-slate-900 truncate">
                {selectedFile.name}
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span className="font-mono">{formatBytes(selectedFile.size)}</span>
                <span>·</span>
                <span className="font-semibold text-slate-700">{selectedFile.format}</span>
                {selectedFile.isSample && (
                  <>
                    <span>·</span>
                    <span className="text-emerald-700 font-medium">Sample Template Loaded</span>
                  </>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={onClearFile}
              className="p-1.5 text-slate-400 hover:text-rose-600 rounded-lg hover:bg-slate-100 transition-colors"
              title="Remove file"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
      )}

      {errorMessage && (
        <div className="p-3 bg-rose-50 text-rose-800 border border-rose-200 rounded-lg text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Verified Sample Contracts for Instant Testing */}
      <div className="pt-2">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 mb-3">
          <Sparkles className="w-4 h-4 text-emerald-600" />
          <span>Or Choose a Verified Ethiopian Business Employment Contract Template</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {SAMPLE_ETHIOPIAN_CONTRACTS.map(sample => (
            <div
              key={sample.id}
              onClick={() => handleSampleSelect(sample)}
              className={`p-3.5 rounded-lg border text-left cursor-pointer transition-all ${
                selectedFile?.sampleId === sample.id
                  ? 'border-emerald-600 bg-emerald-50/40 ring-1 ring-emerald-600'
                  : 'border-slate-200 hover:border-slate-300 bg-white hover:bg-slate-50'
              }`}
            >
              <div className="text-xs font-bold text-slate-900 mb-1 line-clamp-1">
                {sample.title}
              </div>
              <div className="text-[11px] text-slate-500 mb-2">
                Org: {sample.organization}
              </div>
              <p className="text-[11px] text-slate-600 line-clamp-2 leading-relaxed mb-3">
                {sample.description}
              </p>
              <div className="text-[10px] text-emerald-700 font-semibold flex items-center gap-1">
                <BookOpen className="w-3 h-3" />
                <span>Load This Contract</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
