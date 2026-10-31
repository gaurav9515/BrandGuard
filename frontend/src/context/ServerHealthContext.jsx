import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { API_BASE } from '../config/api';

const ServerHealthContext = createContext(null);

export function ServerHealthProvider({ children }) {
  // 'checking' | 'online' | 'waking' | 'offline'
  const [status, setStatus] = useState('checking');
  const [latency, setLatency] = useState(null);
  const [wakingElapsed, setWakingElapsed] = useState(0);
  const [lastChecked, setLastChecked] = useState(null);
  const [serverData, setServerData] = useState(null);
  const [readinessData, setReadinessData] = useState(null);
  const [checkingReadiness, setCheckingReadiness] = useState(false);
  const [isWakingBannerDismissed, setIsWakingBannerDismissed] = useState(false);

  const wakingTimerRef = useRef(null);
  const pollIntervalRef = useRef(null);
  const keepAliveIntervalRef = useRef(null);

  // Ping the server endpoint (/healthz or fallback to /api/health/)
  const checkHealth = useCallback(async (isInitial = false) => {
    const startTime = performance.now();
    const controller = new AbortController();
    // 3.5s timeout for fast responsiveness - if Render is sleeping, it will abort and show waking indicator
    const timeoutId = setTimeout(() => controller.abort(), 3500);

    try {
      const res = await fetch(`${API_BASE}/healthz`, {
        signal: controller.signal,
        cache: 'no-store'
      });
      clearTimeout(timeoutId);

      if (res.ok) {
        const data = await res.json();
        const duration = Math.round(performance.now() - startTime);
        setLatency(duration);
        setStatus('online');
        setServerData(data);
        setLastChecked(new Date());
        setWakingElapsed(0);
        return true;
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (err) {
      clearTimeout(timeoutId);
      // If request timed out (Render free tier cold start) or failed connection
      setStatus('waking');
      return false;
    }
  }, []);

  // Deep readiness probe (/readyz)
  const checkReadiness = useCallback(async () => {
    setCheckingReadiness(true);
    try {
      const res = await fetch(`${API_BASE}/readyz`, { cache: 'no-store' });
      const data = await res.json();
      setReadinessData(data);
      return data;
    } catch (err) {
      const fallbackErr = {
        status: 'not_ready',
        error: err.message,
        timestamp: new Date().toISOString()
      };
      setReadinessData(fallbackErr);
      return fallbackErr;
    } finally {
      setCheckingReadiness(false);
    }
  }, []);

  // Waking counter and aggressive polling when waking
  useEffect(() => {
    if (status === 'waking') {
      // Start seconds counter
      if (!wakingTimerRef.current) {
        wakingTimerRef.current = setInterval(() => {
          setWakingElapsed((prev) => prev + 1);
        }, 1000);
      }

      // Retry every 3 seconds to catch the moment it wakes up
      if (!pollIntervalRef.current) {
        pollIntervalRef.current = setInterval(async () => {
          const success = await checkHealth();
          if (success) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
            clearInterval(wakingTimerRef.current);
            wakingTimerRef.current = null;
          }
        }, 3000);
      }
    } else {
      if (wakingTimerRef.current) {
        clearInterval(wakingTimerRef.current);
        wakingTimerRef.current = null;
      }
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }
    }

    return () => {
      if (wakingTimerRef.current) clearInterval(wakingTimerRef.current);
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [status, checkHealth]);

  // Server Health Check: Initial check on mount (background keep-alive heartbeat disabled to ensure Render server stays off/hibernated when idle)
  useEffect(() => {
    checkHealth(true);

    return () => {
      if (keepAliveIntervalRef.current) clearInterval(keepAliveIntervalRef.current);
    };
  }, [checkHealth]);

  const wakeServer = () => {
    setStatus('waking');
    setWakingElapsed(0);
    setIsWakingBannerDismissed(false);
    checkHealth();
  };

  return (
    <ServerHealthContext.Provider
      value={{
        status, // 'checking' | 'online' | 'waking' | 'offline'
        latency,
        wakingElapsed,
        lastChecked,
        serverData,
        readinessData,
        checkingReadiness,
        isWakingBannerDismissed,
        setIsWakingBannerDismissed,
        checkHealth,
        checkReadiness,
        wakeServer
      }}
    >
      {children}
    </ServerHealthContext.Provider>
  );
}

export function useServerHealth() {
  const context = useContext(ServerHealthContext);
  if (!context) {
    throw new Error('useServerHealth must be used within a ServerHealthProvider');
  }
  return context;
}
