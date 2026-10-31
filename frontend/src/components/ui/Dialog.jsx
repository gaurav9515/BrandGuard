import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export default function Dialog({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  maxWidth = 'max-w-lg',
  showClose = true,
}) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/45 backdrop-blur-xs animate-fade-in"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className={`bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-card)] w-full ${maxWidth} shadow-2xl overflow-hidden animate-scale-in text-left`}
      >
        {(title || showClose) && (
          <div className="flex items-start justify-between p-5 border-b border-[var(--border)]/70">
            <div>
              {title && (
                <h3 className="text-base font-bold text-[var(--text)] tracking-tight font-serif">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="text-xs text-[var(--text-muted)] mt-0.5">{subtitle}</p>
              )}
            </div>
            {showClose && (
              <button
                type="button"
                onClick={onClose}
                aria-label="Close dialog"
                className="text-[var(--text-muted)] hover:text-[var(--text)] p-1 rounded-md hover:bg-[var(--surface-alt)] transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        )}

        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

