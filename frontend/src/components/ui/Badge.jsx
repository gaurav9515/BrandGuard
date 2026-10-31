import React from 'react';
import { AlertOctagon, AlertTriangle, CheckCircle2, Info, Sparkles, HelpCircle } from 'lucide-react';

export default function Badge({
  status = 'INFO', // 'BLOCKER' | 'WARNING' | 'CLEARED' | 'INFO' | 'NEEDS_CLARIFICATION' | 'TRAINING_GAP' | 'HEALTHY_GOVERNANCE' | 'NOT_ENOUGH_DATA'
  label,
  icon: CustomIcon,
  size = 'md', // 'sm' | 'md'
  className = '',
}) {
  const normalizedStatus = (status || 'INFO').toUpperCase();

  const configs = {
    BLOCKER: {
      icon: AlertOctagon,
      defaultLabel: 'Blocker',
      classes:
        'bg-[var(--blocker-tint)] text-[var(--blocker)] border-[var(--blocker)]/40',
    },
    WARNING: {
      icon: AlertTriangle,
      defaultLabel: 'Warning',
      classes:
        'bg-[var(--warning-tint)] text-[var(--warning-text)] border-[var(--warning-text)]/40',
    },
    CLEARED: {
      icon: CheckCircle2,
      defaultLabel: 'Cleared',
      classes:
        'bg-[var(--cleared-tint)] text-[var(--cleared)] border-[var(--cleared)]/40',
    },
    INFO: {
      icon: Info,
      defaultLabel: 'Info',
      classes:
        'bg-[var(--info-tint)] text-[var(--info)] border-[var(--info)]/40',
    },
    NEEDS_CLARIFICATION: {
      icon: HelpCircle,
      defaultLabel: 'Needs Clarification',
      classes:
        'bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border-purple-300 dark:border-purple-800',
    },
    TRAINING_GAP: {
      icon: AlertTriangle,
      defaultLabel: 'Training Gap',
      classes:
        'bg-[var(--warning-tint)] text-[var(--warning-text)] border-[var(--warning-text)]/40',
    },
    HEALTHY_GOVERNANCE: {
      icon: CheckCircle2,
      defaultLabel: 'Healthy Governance',
      classes:
        'bg-[var(--cleared-tint)] text-[var(--cleared)] border-[var(--cleared)]/40',
    },
    NOT_ENOUGH_DATA: {
      icon: Info,
      defaultLabel: 'Not enough data',
      classes:
        'bg-zinc-100 dark:bg-zinc-800 text-zinc-500 border-zinc-200 dark:border-zinc-700',
    },
  };

  const config = configs[normalizedStatus] || configs.INFO;
  const IconToRender = CustomIcon || config.icon;
  const textLabel = label || config.defaultLabel;

  const sizeClasses =
    size === 'sm'
      ? 'text-[10px] px-2 py-0.5 gap-1 font-mono'
      : 'text-[11px] px-2.5 py-1 gap-1.5 font-medium';

  return (
    <span
      className={`inline-flex items-center rounded-full border font-bold uppercase tracking-wide shrink-0 ${sizeClasses} ${config.classes} ${className}`}
    >
      <IconToRender className={size === 'sm' ? 'w-3 h-3 shrink-0' : 'w-3.5 h-3.5 shrink-0'} />
      <span>{textLabel}</span>
    </span>
  );
}

