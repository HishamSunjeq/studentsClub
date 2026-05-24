import { useEffect, useRef, useState } from "react";
import { env } from "@/lib/env";
import { useAuthStore } from "@/features/auth/auth.store";

/**
 * Live subject-chat assistant tokens over Server-Sent Events.
 *
 * Subscribes to `GET /api/v1/subjects/{subjectId}/chat/sessions/{sessionId}/events`.
 * EventSource cannot set headers, so the access token rides as a query param
 * (same pattern as useUploadEvents). Reconnects with exponential backoff and
 * closes on the terminal `done` / `error` event.
 */

export interface ChatStreamCitation {
  chunk_id: string;
  upload_id: string | null;
  section_title: string | null;
  text: string;
}

export type ChatStreamEvent =
  | { type: "stream.open" }
  | { type: "retrieve.started" }
  | { type: "retrieve.completed"; hits: number }
  | { type: "token"; delta: string }
  | { type: "done"; citations: ChatStreamCitation[] }
  | { type: "error"; message?: string };

const TERMINAL = new Set(["done", "error"]);
const MAX_BACKOFF_MS = 30_000;

export interface SubjectChatState {
  streaming: boolean;
  retrieving: boolean;
  text: string;
  citations: ChatStreamCitation[];
  errored: boolean;
}

const EMPTY: SubjectChatState = {
  streaming: false,
  retrieving: false,
  text: "",
  citations: [],
  errored: false,
};

export function useSubjectChat(
  subjectId: string,
  sessionId: string | null,
  enabled: boolean,
  onDone?: () => void,
): SubjectChatState {
  const accessToken = useAuthStore((s) => s.accessToken);
  const [state, setState] = useState<SubjectChatState>(EMPTY);

  const onDoneRef = useRef(onDone);
  onDoneRef.current = onDone;

  useEffect(() => {
    if (!enabled || !sessionId || !accessToken) {
      setState(EMPTY);
      return;
    }

    let source: EventSource | null = null;
    let retry = 0;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closed = false;

    setState({ ...EMPTY, streaming: true });

    const connect = () => {
      if (closed) return;
      const url = `${env.apiBaseUrl}/api/v1/subjects/${subjectId}/chat/sessions/${sessionId}/events?token=${encodeURIComponent(
        accessToken,
      )}`;
      source = new EventSource(url);

      source.onopen = () => {
        retry = 0;
      };

      source.onmessage = (evt) => {
        let parsed: ChatStreamEvent;
        try {
          parsed = JSON.parse(evt.data) as ChatStreamEvent;
        } catch {
          return;
        }
        setState((prev) => {
          switch (parsed.type) {
            case "retrieve.started":
              return { ...prev, retrieving: true };
            case "retrieve.completed":
              return { ...prev, retrieving: false };
            case "token":
              return { ...prev, text: prev.text + parsed.delta };
            case "done":
              return {
                ...prev,
                streaming: false,
                citations: parsed.citations ?? [],
              };
            case "error":
              return { ...prev, streaming: false, errored: true };
            default:
              return prev;
          }
        });

        if (TERMINAL.has(parsed.type)) {
          onDoneRef.current?.();
          closed = true;
          source?.close();
        }
      };

      source.onerror = () => {
        source?.close();
        if (closed) return;
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
  }, [subjectId, sessionId, enabled, accessToken]);

  return state;
}
