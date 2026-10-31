import React, { forwardRef } from 'react';

const Input = forwardRef(function Input(
  {
    label,
    error,
    helperText,
    icon: Icon,
    className = '',
    type = 'text',
    disabled = false,
    id,
    ...props
  },
  ref
) {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="w-full space-y-1.5 text-left">
      {label && (
        <label
          htmlFor={inputId}
          className="block text-xs font-semibold text-[var(--text)] tracking-tight"
        >
          {label}
        </label>
      )}

      <div className="relative rounded-[var(--radius-input)]">
        {Icon && (
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-[var(--text-muted)]">
            <Icon className="w-4 h-4" />
          </div>
        )}

        <input
          ref={ref}
          id={inputId}
          type={type}
          disabled={disabled}
          className={`w-full rounded-[var(--radius-input)] text-xs bg-[var(--surface)] border text-[var(--text)] placeholder:text-[var(--text-muted)] py-2 ${
            Icon ? 'pl-9 pr-3' : 'px-3'
          } ${
            error
              ? 'border-[var(--blocker)] focus:ring-2 focus:ring-[var(--blocker)] focus:outline-hidden'
              : 'border-[var(--border)] focus:border-[var(--primary)] focus:ring-2 focus:ring-[var(--primary)]/30 focus:outline-hidden'
          } disabled:opacity-50 disabled:bg-[var(--surface-alt)] transition-colors ${className}`}
          {...props}
        />
      </div>

      {error ? (
        <p className="text-[11px] text-[var(--blocker)] font-medium mt-1">{error}</p>
      ) : helperText ? (
        <p className="text-[11px] text-[var(--text-muted)] mt-1">{helperText}</p>
      ) : null}
    </div>
  );
});

export default Input;

