import React from 'react';
import { ShieldAlert } from 'lucide-react';

export function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  icon: Icon = ShieldAlert
}: {
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ElementType;
}) {
  return (
    <div className="text-center py-12 px-4 rounded-xl border border-dashed border-slate-200 bg-white">
      <div className="w-12 h-12 mx-auto rounded-lg bg-slate-50 border border-slate-200 flex items-center justify-center text-slate-400 mb-3">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-semibold text-slate-900">{title}</h3>
      <p className="mt-1 text-xs text-slate-500 max-w-sm mx-auto leading-relaxed">{description}</p>
      {actionLabel && onAction && (
        <div className="mt-4">
          <button
            onClick={onAction}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors"
          >
            {actionLabel}
          </button>
        </div>
      )}
    </div>
  );
}

export function LoadingSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="bg-white p-4 rounded-xl border border-slate-200 animate-pulse">
          <div className="flex items-center justify-between mb-3">
            <div className="h-4 bg-slate-200 rounded w-1/3"></div>
            <div className="h-4 bg-slate-100 rounded w-16"></div>
          </div>
          <div className="h-3 bg-slate-100 rounded w-3/4 mb-2"></div>
          <div className="h-3 bg-slate-100 rounded w-1/2"></div>
        </div>
      ))}
    </div>
  );
}
