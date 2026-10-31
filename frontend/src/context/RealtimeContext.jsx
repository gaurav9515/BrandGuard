import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { useAuth } from './AuthContext';
import { API_BASE } from '../config/api';

const RealtimeContext = createContext(null);

export function RealtimeProvider({ children }) {
  const { user, token } = useAuth();
  const [status, setStatus] = useState('connecting'); // 'live' | 'reconnecting' | 'fallback'
  const [lastEvent, setLastEvent] = useState(null);
  const eventSourceRef = useRef(null);
  const fallbackPollRef = useRef(null);

  useEffect(() => {
    if (!user || !token) {
      setStatus('idle');
      return;
    }

    let isUnmounted = false;

    const startEventSource = () => {
      try {
        const streamUrl = `${API_BASE}/api/realtime/stream/?token=${encodeURIComponent(token)}`;
        const es = new EventSource(streamUrl);
        eventSourceRef.current = es;

        es.onopen = () => {
          if (!isUnmounted) {
            setStatus('live');
            if (fallbackPollRef.current) {
              clearInterval(fallbackPollRef.current);
              fallbackPollRef.current = null;
            }
          }
        };

        es.addEventListener('connected', () => {
          if (!isUnmounted) setStatus('live');
        });

        es.addEventListener('ping', () => {
          if (!isUnmounted) setStatus('live');
        });

        es.addEventListener('job_progress', (e) => {
          if (!isUnmounted && e.data) {
            try {
              const parsed = JSON.parse(e.data);
              setLastEvent({ type: 'job_progress', payload: parsed });
            } catch (_) {}
          }
        });

        es.addEventListener('fact_change_proposed', (e) => {
          if (!isUnmounted && e.data) {
            try {
              const parsed = JSON.parse(e.data);
              setLastEvent({ type: 'fact_change_proposed', payload: parsed });
            } catch (_) {}
          }
        });

        es.addEventListener('fact_change_approved', (e) => {
          if (!isUnmounted && e.data) {
            try {
              const parsed = JSON.parse(e.data);
              setLastEvent({ type: 'fact_change_approved', payload: parsed });
            } catch (_) {}
          }
        });

        es.onerror = () => {
          if (!isUnmounted) {
            setStatus('reconnecting');
            es.close();
            // Start 10-second polling fallback
            if (!fallbackPollRef.current) {
              startFallbackPolling();
            }
            // Retry SSE after 5 seconds
            setTimeout(() => {
              if (!isUnmounted) startEventSource();
            }, 5000);
          }
        };
      } catch (err) {
        if (!isUnmounted) {
          setStatus('fallback');
          startFallbackPolling();
        }
      }
    };

    const startFallbackPolling = () => {
      fallbackPollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/api/telemetry/`, {
            headers: { Authorization: `Bearer ${token}` }
          });
          if (res.ok && !isUnmounted) {
            setStatus('fallback');
          }
        } catch (_) {}
      }, 10000);
    };

    startEventSource();

    return () => {
      isUnmounted = true;
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (fallbackPollRef.current) {
        clearInterval(fallbackPollRef.current);
      }
    };
  }, [user, token]);

  return (
    <RealtimeContext.Provider value={{ status, lastEvent }}>
      {children}
    </RealtimeContext.Provider>
  );
}

export function useRealtime() {
  const ctx = useContext(RealtimeContext);
  return ctx || { status: 'idle', lastEvent: null };
}

