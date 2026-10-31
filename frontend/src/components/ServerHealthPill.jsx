import React, { useState } from 'react';
import { Activity, RefreshCw, Zap, CheckCircle2, ChevronDown, ExternalLink } from 'lucide-react';
import { useServerHealth } from '../context/ServerHealthContext';

export default function ServerHealthPill({ compact = false }) {
  const { status, latency, wakingElapsed, checkHealth, wakeServer } = useServerHealth();
  const [open, setOpen] = useState(false);

  const getStatusBadge = () => {
    if (status === 'online') {
      return {
        dotClass: 'bg-emerald-500 animate-pulse',
        textClass: 'text-emerald-700 dark:text-emerald-300',
        bgClass: 'bg-emerald-50 dark:bg-emerald-950/60 border-emerald-200 dark:border-emerald-800',
        label: `API Live · ${latency || '<50'}ms`,
      };
    }
    if (status === 'waking') {
      return {
        dotClass: 'bg-amber-500 animate-ping',
        textClass: 'text-amber-700 dark:text-amber-300',
        bgClass: 'bg-amber-50 dark:bg-amber-950/60 border-amber-300 dark:border-amber-800',
        label: `Waking Server · ${wakingElapsed}s`,
      };
    }
    return {
      dotClass: 'bg-zinc-400',
      textClass: 'text-zinc-600 dark:text-zinc-400',
      bgClass: 'bg-zinc-100 dark:bg-zinc-800 border-zinc-200 dark:border-zinc-700',
      label: 'Connecting...',
    };
  };

  const badge = getStatusBadge();

  return (
    <div className="relative inline-block text-left">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        title="Render Server Health & Sleep Monitor"
        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[11px] font-mono font-medium transition-all cursor-pointer ${badge.bgClass} ${badge.textClass}`}
      >
        <span className={`w-2 h-2 rounded-full ${badge.dotClass}`} />
        <span>{badge.label}</span>
        {!compact && <ChevronDown className="w-3 h-3 opacity-60 ml-0.5" />}
      </button>

      {open && (
        <div
          className="absolute right-0 mt-2 w-72 bg-[var(--surface)] border border-[var(--border)] rounded-xl shadow-xl p-3.5 z-50 text-xs"
          onMouseLeave={() => setOpen(false)}
        >
          <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]">
            <span className="font-semibold text-[var(--text)] flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-[var(--primary)]" />
              Render Health Monitor
            </span>
            <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-bold uppercase ${
              status === 'online' ? 'bg-[var(--cleared-tint,rgba(46,158,91,0.12))] text-[var(--cleared)]' : 'bg-amber-100 text-amber-800'
            }`}>
              {status}
            </span>
          </div>

          <div className="mt-2.5 space-y-1.5 text-[11px] text-[var(--text-muted)]">
            <div className="flex justify-between">
              <span>Host Architecture:</span>
              <span className="font-mono text-[var(--text)] font-medium">Render Cloud (Oregon)</span>
            </div>
            <div className="flex justify-between">
              <span>Sleep Behavior:</span>
              <span className="text-[var(--text)]">Spins down after 15m idle</span>
            </div>
            <div className="flex justify-between">
              <span>Keep-Alive Heartbeat:</span>
              <span className="text-[var(--cleared)] font-semibold">Active (Every 12m)</span>
            </div>
            {latency && (
              <div className="flex justify-between">
                <span>Round-Trip Latency:</span>
                <span className="font-mono text-[var(--text)]">{latency} ms</span>
              </div>
            )}
            {status === 'waking' && (
              <div className="flex justify-between text-amber-600 dark:text-amber-400 font-medium">
                <span>Cold Start Timer:</span>
                <span>{wakingElapsed}s elapsed (~30-50s)</span>
              </div>
            )}
          </div>

          <div className="mt-3 pt-2 border-t border-[var(--border)] flex gap-2">
            <button
              type="button"
              onClick={() => {
                checkHealth();
              }}
              className="flex-1 inline-flex items-center justify-center gap-1.5 py-1 px-2.5 rounded-lg border border-[var(--border)] text-[var(--text)] hover:bg-[var(--surface-alt)] text-[11px] font-medium transition cursor-pointer"
            >
              <RefreshCw className="w-3 h-3" />
              Ping API
            </button>
            {status === 'waking' && (
              <button
                type="button"
                onClick={wakeServer}
                className="inline-flex items-center justify-center gap-1.5 py-1 px-2.5 rounded-lg bg-[var(--primary)] text-white hover:opacity-90 text-[11px] font-medium transition cursor-pointer"
              >
                <Zap className="w-3 h-3" />
                Wake Now
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
