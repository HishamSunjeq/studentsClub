import { useEffect, useRef, useState } from "react";
import { env } from "@/lib/env";
import { useAuthStore } from "@/features/auth/auth.store";

/**
 * Live AI-generation progress over Server-Sent Events.
 *
 * Subscribes to `GET /api/v1/uploads/{id}/events` (see backend
 * `uploads_events.py`). EventSource cannot set an Authorization header, so the
 * access token rides as a query param. Reconnects with exponential backoff on
 * transport errors, and stops once a terminal event (`generate.completed` /
 * `error`) arrives.
 */

export type UploadEvent =
  | { type: "stream.open"; ts?: string }
  | { type: "analyze.started"; ts?: string }
  | {
      type: "analyze.completed";
      doc_type: string;
      language: string;
      target_questions: number;
      ts?: string;
    }
  | { type: "segment.completed"; sections: number; ts?: string }
  | {
      type: "generate.section.started";
      section: number;
      title: string;
      ts?: string;
    }
  | { type: "retrieve.completed"; section: number; chunks: number; ts?: string }
  | {
      type: "generate.section.completed";
      section: number;
      questions: number;
      ts?: string;
    }
  | { type: "judge.completed"; scored: number; auto_rejected: number; ts?: string }
  | { type: "dedupe.completed"; kept: number; dropped: number; ts?: string }
  | {
      type: "generate.completed";
      inserted?: number;
      auto_rejected?: number;
      dropped?: number;
      kept?: number;
      ts?: string;
    }
  | { type: "error"; question_set_id?: string; message?: string; ts?: string };

const TERMINAL = new Set(["generate.completed", "error"]);
const MAX_BACKOFF_MS = 30_000;

export interface UploadEventsState {
  events: UploadEvent[];
  latest: UploadEvent | null;
  connected: boolean;
  done: boolean;
  errored: boolean;
}

export function useUploadEvents(
  uploadId: string | undefined,
  enabled: boolean,
  onTerminal?: (event: UploadEvent) => void,
): UploadEventsState {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [state, setState] = useState<UploadEventsState>({
    events: [],
    latest: null,
    connected: false,
    done: false,
    errored: false,
  });

  // Keep the latest callback without re-subscribing.
  const onTerminalRef = useRef(onTerminal);
  onTerminalRef.current = onTerminal;

  useEffect(() => {
    if (!enabled || !uploadId || !accessToken) return;

    let source: EventSource | null = null;
    let retry = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

    // Reset state for a fresh subscription.
    setState({
      events: [],
      latest: null,
      connected: false,
      done: false,
      errored: false,
    });

    const connect = () => {
      if (closed) return;
      const url = `${env.apiBaseUrl}/api/v1/uploads/${uploadId}/events?token=${encodeURIComponent(
        accessToken,
      )}`;
      source = new EventSource(url);

      source.onopen = () => {
        retry = 0;
        setState((prev) => ({ ...prev, connected: true }));
      };

      source.onmessage = (evt) => {
        let parsed: UploadEvent;
        try {
          parsed = JSON.parse(evt.data) as UploadEvent;
        } catch {
          return;
        }
        setState((prev) => ({
          ...prev,
          events: [...prev.events, parsed],
          latest: parsed,
          done: prev.done || parsed.type === "generate.completed",
          errored: prev.errored || parsed.type === "error",
        }));

        if (TERMINAL.has(parsed.type)) {
          onTerminalRef.current?.(parsed);
          closed = true;
          source?.close();
        }
      };

      source.onerror = () => {
        setState((prev) => ({ ...prev, connected: false }));
        source?.close();
        if (closed) return;
        // Exponential backoff with jitter, capped.
        const delay = Math.min(MAX_BACKOFF_MS, 1000 * 2 ** retry);
        retry += 1;
        reconnectTimer = setTimeout(connect, delay + Math.random() * 250);
      };
    };

    connect();

    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      source?.close();
    };
  }, [uploadId, enabled, accessToken]);

  return state;
}
