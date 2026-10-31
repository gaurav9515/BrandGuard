import React from 'react';

export default function Card({
  children,
  accent, // 'BLOCKER' | 'WARNING' | 'CLEARED' | 'INFO' | null
  className = '',
  hover = false,
  onClick,
  ...props
}) {
  const accentClasses = {
    BLOCKER: 'border-l-4 border-l-[var(--blocker)] border-[var(--blocker)]/30',
    WARNING: 'border-l-4 border-l-[var(--warning-text)] border-[var(--warning-text)]/30',
    CLEARED: 'border-l-4 border-l-[var(--cleared)] border-[var(--cleared)]/30',
    INFO: 'border-l-4 border-l-[var(--info)] border-[var(--info)]/30',
  };

  const borderClass = accent ? accentClasses[accent] || '' : 'border border-[var(--border)]';

  return (
    <div
      onClick={onClick}
      className={`bg-[var(--surface)] ${borderClass} rounded-[var(--radius-card)] shadow-xs transition-all ${
        hover ? 'hover:shadow-md hover:border-[var(--text-muted)] cursor-pointer' : ''
      } ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}

export function CardHeader({ children, className = '' }) {
  return (
    <div className={`p-5 pb-3 border-b border-[var(--border)]/60 ${className}`}>
      {children}
    </div>
  );
}

export function CardContent({ children, className = '' }) {
  return <div className={`p-5 ${className}`}>{children}</div>;
}

export function CardFooter({ children, className = '' }) {
  return (
    <div className={`p-4 bg-[var(--surface-alt)]/40 rounded-b-[var(--radius-card)] border-t border-[var(--border)]/60 ${className}`}>
      {children}
    </div>
  );
}

