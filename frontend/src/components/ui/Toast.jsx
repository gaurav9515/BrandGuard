import React, { useEffect, useState } from 'react';
import { CheckCircle2, RotateCcw, X } from 'lucide-react';

export default function Toast({
  message,
  onUndo,
  onDismiss,
  duration = 10000, // 10 seconds default
  undoLabel = 'Undo Patch',
}) {
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    if (!message) return;

    const interval = 50; // update progress every 50ms
    const decrement = (interval / duration) * 100;

    const timer = setInterval(() => {
      setProgress((prev) => {
        if (prev <= decrement) {
          clearInterval(timer);
          if (onDismiss) onDismiss();
          return 0;
        }
        return prev - decrement;
      });
    }, interval);

    return () => clearInterval(timer);
  }, [message, duration, onDismiss]);

  if (!message) return null;

  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed bottom-6 right-6 z-50 bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-card)] shadow-xl overflow-hidden min-w-[320px] max-w-md animate-slide-up"
    >
      <div className="p-3.5 flex items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5 text-[var(--text)] font-medium">
          <CheckCircle2 className="w-4 h-4 text-[var(--cleared)] shrink-0" />
          <span>{message}</span>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {onUndo && (
            <button
              type="button"
              onClick={onUndo}
              className="flex items-center gap-1 px-2.5 py-1 rounded-md bg-[var(--surface-alt)] hover:bg-[var(--primary)] hover:text-white text-[var(--primary)] font-bold transition-all text-xs cursor-pointer border border-[var(--border)]"
            >
              <RotateCcw className="w-3 h-3" />
              <span>{undoLabel}</span>
            </button>
          )}

          {onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              aria-label="Dismiss toast"
              className="text-[var(--text-muted)] hover:text-[var(--text)] p-1 rounded-md cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* 10s Countdown Progress Bar */}
      <div className="h-1 bg-[var(--surface-alt)] w-full">
        <div
          className="h-full bg-[var(--primary)] transition-all duration-75"
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}

