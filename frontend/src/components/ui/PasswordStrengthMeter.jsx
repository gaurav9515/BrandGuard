import React from 'react';
import { Check, X } from 'lucide-react';

export default function PasswordStrengthMeter({ password = '' }) {
  const hasLength = password.length >= 12;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasSpecial = /[^A-Za-z0-9]/.test(password) || /[0-9]/.test(password);

  const criteria = [
    { label: 'Minimum 12 characters', met: hasLength },
    { label: 'Uppercase letter (A-Z)', met: hasUpper },
    { label: 'Lowercase letter (a-z)', met: hasLower },
    { label: 'Number or symbol (0-9, !@#$)', met: hasSpecial },
  ];

  const score = criteria.filter((c) => c.met).length;

  const strengthLabels = ['Very Weak', 'Weak', 'Moderate', 'Strong', 'Very Strong'];
  const strengthColors = [
    'bg-[var(--blocker)]',
    'bg-[var(--blocker)]',
    'bg-[var(--warning-text)]',
    'bg-[var(--accent)]',
    'bg-[var(--cleared)]',
  ];

  return (
    <div className="space-y-2 mt-1.5" role="region" aria-label="Password Strength">
      {/* 4-segment strength bar */}
      <div className="grid grid-cols-4 gap-1.5 h-1.5">
        {[0, 1, 2, 3].map((idx) => {
          const filled = idx < score;
          return (
            <div
              key={idx}
              className={`rounded-full transition-all duration-300 ${
                filled ? strengthColors[score] : 'bg-[var(--border)]/60'
              }`}
            />
          );
        })}
      </div>

      <div className="flex items-center justify-between text-[11px] font-mono">
        <span className="text-[var(--text-muted)]">Entropy Score:</span>
        <span className={`font-semibold ${score >= 4 ? 'text-[var(--cleared)]' : score >= 3 ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'}`}>
          {password ? strengthLabels[score] : 'Enter password'}
        </span>
      </div>

      {/* Criteria Checklist */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1 text-[11px]">
        {criteria.map((c, i) => (
          <div key={i} className="flex items-center gap-1.5">
            {c.met ? (
              <Check className="w-3.5 h-3.5 text-[var(--cleared)] shrink-0" />
            ) : (
              <X className="w-3.5 h-3.5 text-[var(--border)] shrink-0" />
            )}
            <span className={c.met ? 'text-[var(--text)] font-medium' : 'text-[var(--text-muted)]'}>
              {c.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

