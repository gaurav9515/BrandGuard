import React from 'react';
import { Loader2 } from 'lucide-react';

export default function Button({
  children,
  variant = 'primary', // 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
  size = 'md',        // 'sm' | 'md' | 'lg'
  icon: Icon,
  iconPosition = 'left',
  loading = false,
  disabled = false,
  className = '',
  type = 'button',
  onClick,
  ...props
}) {
  const baseStyles =
    'inline-flex items-center justify-center font-semibold rounded-lg transition-all focus:outline-hidden focus-visible:ring-2 focus-visible:ring-[var(--primary)] focus-visible:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer';

  const sizeStyles = {
    sm: 'text-xs px-2.5 py-1.5 gap-1.5 min-h-[30px]',
    md: 'text-xs px-3.5 py-2 gap-2 min-h-[36px]',
    lg: 'text-sm px-5 py-2.5 gap-2.5 min-h-[42px]',
  };

  const variantStyles = {
    primary:
      'bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] shadow-2xs active:scale-[0.98]',
    secondary:
      'bg-[var(--surface-alt)] text-[var(--text)] hover:bg-[var(--border)] border border-[var(--border)]',
    outline:
      'bg-transparent border border-[var(--border)] text-[var(--text)] hover:bg-[var(--surface-alt)] active:scale-[0.98]',
    ghost:
      'bg-transparent text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)]',
    danger:
      'bg-[var(--blocker)] text-white hover:opacity-90 active:scale-[0.98] shadow-2xs',
  };

  return (
    <button
      type={type}
      disabled={disabled || loading}
      onClick={onClick}
      className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {loading ? (
        <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
      ) : Icon && iconPosition === 'left' ? (
        <Icon className="w-3.5 h-3.5 shrink-0" />
      ) : null}
      <span>{children}</span>
      {!loading && Icon && iconPosition === 'right' ? (
        <Icon className="w-3.5 h-3.5 shrink-0" />
      ) : null}
    </button>
  );
}

