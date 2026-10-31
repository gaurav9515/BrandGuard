import React from 'react';
import { RefreshCw, Zap, X, AlertCircle } from 'lucide-react';
import { useServerHealth } from '../context/ServerHealthContext';

export default function ServerHealthBanner() {
  const { status, wakingElapsed, isWakingBannerDismissed, setIsWakingBannerDismissed, checkHealth } = useServerHealth();

  if (status !== 'waking' || isWakingBannerDismissed) {
    return null;
  }

  return (
    <div className="bg-[var(--surface)] text-[var(--text)] border-b border-amber-500/40 px-4 py-2.5 shadow-xs flex items-center justify-between text-xs z-50 sticky top-0 transition-all">
      <div className="flex items-center gap-3 max-w-4xl">
        <div className="w-7 h-7 rounded-lg bg-amber-500/15 text-amber-700 dark:text-amber-400 flex items-center justify-center shrink-0 border border-amber-500/30">
          <RefreshCw className="w-3.5 h-3.5 animate-spin" />
        </div>
        <div>
          <div className="font-semibold flex items-center gap-2 text-[var(--text)]">
            <span>Render Backend Server is Waking Up</span>
            <span className="font-mono bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-300 px-2 py-0.5 rounded text-[10px] font-bold border border-amber-300 dark:border-amber-800">
              {wakingElapsed}s elapsed
            </span>
          </div>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5 leading-snug">
            Free-tier instances hibernate after 15 minutes of inactivity and take ~30–50s to spin up. Offline rules and client linters remain active while connection establishes.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 ml-4 shrink-0">
        <button
          type="button"
          onClick={() => checkHealth()}
          className="px-2.5 py-1 rounded-lg bg-[var(--primary)] text-white hover:opacity-95 text-[11px] font-medium transition cursor-pointer flex items-center gap-1 shadow-xs"
        >
          <Zap className="w-3 h-3 text-amber-300" />
          <span>Ping API</span>
        </button>
        <button
          type="button"
          onClick={() => setIsWakingBannerDismissed(true)}
          className="p-1 hover:bg-[var(--surface-alt)] rounded-md text-[var(--text-muted)] transition cursor-pointer"
          title="Dismiss notification"
          aria-label="Dismiss banner"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
