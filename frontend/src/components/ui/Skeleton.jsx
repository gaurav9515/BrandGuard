import React from 'react';

export default function Skeleton({
  className = '',
  variant = 'rectangular', // 'text' | 'circular' | 'rectangular'
  width,
  height,
}) {
  const variantStyles = {
    text: 'h-3 rounded-[4px] w-full',
    circular: 'rounded-full',
    rectangular: 'rounded-[var(--radius-input)] w-full',
  };

  const style = {
    ...(width ? { width } : {}),
    ...(height ? { height } : {}),
  };

  return (
    <div
      style={style}
      aria-hidden="true"
      className={`animate-pulse bg-[var(--surface-alt)]/80 border border-[var(--border)]/30 ${variantStyles[variant]} ${className}`}
    />
  );
}

