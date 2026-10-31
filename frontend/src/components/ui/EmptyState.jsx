import React from 'react';
import Button from './Button';

export default function EmptyState({
  title = 'No items found',
  description = 'There are no active records in this section.',
  actionLabel,
  onAction,
  icon: CustomIcon,
  className = '',
}) {
  return (
    <div
      className={`bg-[var(--surface)] border border-[var(--border)] rounded-[var(--radius-card)] p-10 text-center flex flex-col items-center justify-center max-w-md mx-auto relative overflow-hidden shadow-2xs ${className}`}
    >
      {/* Subtle Low-Opacity Forest Leaf Illustration Background */}
      <div className="w-16 h-16 rounded-full bg-[var(--surface-alt)] flex items-center justify-center mb-4 border border-[var(--border)] relative">
        <svg
          viewBox="0 0 48 48"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className="w-8 h-8 text-[var(--accent)] opacity-85"
        >
          <path
            d="M24 6 C28 14 38 18 42 24 C38 30 28 34 24 42 C20 34 10 30 6 24 C10 18 20 14 24 6 Z"
            fill="currentColor"
            fillOpacity="0.25"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M24 6 L24 42"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <path
            d="M24 20 L32 26"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <path
            d="M24 28 L16 34"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
        </svg>
      </div>

      <h3 className="text-sm font-bold text-[var(--text)] tracking-tight font-serif mb-1">
        {title}
      </h3>
      <p className="text-xs text-[var(--text-muted)] leading-relaxed mb-5 max-w-xs">
        {description}
      </p>

      {actionLabel && onAction && (
        <Button variant="primary" size="sm" onClick={onAction}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}

