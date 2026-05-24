import { useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router";
import { toast } from "sonner";
import { FileText, Loader2, MessageSquarePlus, Send, Sparkles } from "lucide-react";
import {
  getSubjectChatMessagesListQueryKey,
  getSubjectChatSessionsListQueryKey,
  useSubjectChatMessagesList,
  useSubjectChatSend,
  useSubjectChatSessionsCreate,
  useSubjectChatSessionsList,
} from "@/api/generated/endpoints/subject-chat/subject-chat";
import type { ChatCitation, ChatMessageResponse } from "@/api/generated/schemas";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import {
  useSubjectChat,
  type ChatStreamCitation,
} from "./useSubjectChat";

export function SubjectChatPanel({
  subjectId,
  enrolled,
}: {
  subjectId: string;
  enrolled: boolean;
}) {
  const queryClient = useQueryClient();
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [streamingFor, setStreamingFor] = useState<string | null>(null);
  const [pendingUserText, setPendingUserText] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { data: sessionsData } = useSubjectChatSessionsList(subjectId, {
    query: { enabled: enrolled },
  });
  const sessions = sessionsData?.items ?? [];

  const { data: messagesData, isLoading: loadingMessages } =
    useSubjectChatMessagesList(subjectId, activeSessionId ?? "", {
      query: { enabled: enrolled && !!activeSessionId },
    });
  const messages = messagesData?.items ?? [];

  const createSession = useSubjectChatSessionsCreate();
  const send = useSubjectChatSend();
  const busy = createSession.isPending || send.isPending;

  const stream = useSubjectChat(
    subjectId,
    streamingFor,
    streamingFor !== null,
  );

  useEffect(() => {
    if (!stream.streaming && streamingFor && pendingUserText === null) {
      // Stream terminated — clear our local streaming bubble so the persisted
      // assistant message (refetched by the send mutation) takes over.
      setStreamingFor(null);
    }
  }, [stream.streaming, streamingFor, pendingUserText]);

  function invalidateSessions() {
    void queryClient.invalidateQueries({
      queryKey: getSubjectChatSessionsListQueryKey(subjectId),
    });
  }

  async function handleSend() {
    const content = draft.trim();
    if (!content || busy) return;
    setDraft("");
    try {
      let sessionId = activeSessionId;
      if (!sessionId) {
        const created = await createSession.mutateAsync({
          subjectId,
          data: { title: null },
        });
        sessionId = created.id;
        setActiveSessionId(sessionId);
        invalidateSessions();
      }
      // Surface the user turn + start the SSE subscription before the POST
      // resolves so tokens stream into the UI as the backend produces them.
      setPendingUserText(content);
      setStreamingFor(sessionId);
      await send.mutateAsync({ subjectId, sessionId, data: { content } });
      setPendingUserText(null);
      void queryClient.invalidateQueries({
        queryKey: getSubjectChatMessagesListQueryKey(subjectId, sessionId),
      });
      invalidateSessions();
      requestAnimationFrame(() =>
        scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight }),
      );
    } catch {
      toast.error("Couldn't get an answer. Try again.");
      setDraft(content);
      setPendingUserText(null);
      setStreamingFor(null);
    }
  }

  function startNewChat() {
    setActiveSessionId(null);
    setDraft("");
  }

  if (!enrolled) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
        <Sparkles className="size-10 text-muted-foreground/40" />
        <p className="text-sm font-medium text-foreground">
          Enrol to chat with this subject
        </p>
        <p className="max-w-xs text-xs text-muted-foreground">
          The assistant answers from this subject's uploaded material, with
          citations to the source.
        </p>
      </div>
    );
  }

  return (
    <div className="flex h-[60vh] gap-4">
      {/* Session list */}
      <aside className="hidden w-56 shrink-0 flex-col gap-2 sm:flex">
        <Button
          variant="outline"
          size="sm"
          className="justify-start"
          onClick={startNewChat}
        >
          <MessageSquarePlus className="size-3.5" strokeWidth={1.5} />
          New chat
        </Button>
        <div className="flex-1 space-y-1 overflow-y-auto">
          {sessions.map((s) => (
            <button
              key={s.id}
              onClick={() => setActiveSessionId(s.id)}
              className={cn(
                "w-full truncate rounded-lg px-3 py-2 text-left text-xs transition-colors",
                activeSessionId === s.id
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:bg-muted/50",
              )}
            >
              {s.title}
            </button>
          ))}
        </div>
      </aside>

      {/* Thread */}
      <div className="flex flex-1 flex-col rounded-xl border border-border bg-surface-low">
        <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4">
          {!activeSessionId ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
              <Sparkles className="size-8 text-primary/40" />
              <p className="text-sm font-medium text-foreground">
                Ask anything about this subject
              </p>
              <p className="max-w-sm text-xs text-muted-foreground">
                Answers are grounded in the uploaded material and cite their
                sources.
              </p>
            </div>
          ) : loadingMessages ? (
            <div className="space-y-3">
              <Skeleton className="h-16 w-2/3 rounded-lg" />
              <Skeleton className="ml-auto h-16 w-2/3 rounded-lg" />
            </div>
          ) : (
            <>
              {messages.map((m) => (
                <MessageBubble key={m.id} message={m} />
              ))}
              {pendingUserText && (
                <PendingUserBubble text={pendingUserText} />
              )}
              {streamingFor && (
                <StreamingAssistantBubble
                  text={stream.text}
                  retrieving={stream.retrieving}
                  done={!stream.streaming}
                  citations={stream.citations}
                />
              )}
            </>
          )}
        </div>

        {/* Composer */}
        <div className="border-t border-border p-3">
          <div className="flex items-end gap-2">
            <Textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void handleSend();
                }
              }}
              rows={1}
              placeholder="Ask a question…"
              className="max-h-32 min-h-[2.5rem] resize-none"
              disabled={busy}
            />
            <Button
              onClick={() => void handleSend()}
              disabled={busy || !draft.trim()}
              size="icon"
              className="shrink-0"
            >
              {busy ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Send className="size-4" strokeWidth={1.5} />
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function PendingUserBubble({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-end gap-2">
      <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl bg-primary px-4 py-2.5 text-sm text-primary-foreground">
        {text}
      </div>
    </div>
  );
}

function StreamingAssistantBubble({
  text,
  retrieving,
  done,
  citations,
}: {
  text: string;
  retrieving: boolean;
  done: boolean;
  citations: ChatStreamCitation[];
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl border border-border bg-card px-4 py-2.5 font-study text-sm text-foreground">
        {!text && retrieving && (
          <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" />
            Searching the material…
          </span>
        )}
        {!text && !retrieving && !done && (
          <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="size-3.5 animate-spin" />
            Thinking…
          </span>
        )}
        {text}
        {!done && text && (
          <span className="ml-0.5 inline-block h-3.5 w-1 animate-pulse bg-foreground/40 align-middle" />
        )}
      </div>
      {done && citations.length > 0 && (
        <div className="flex max-w-[85%] flex-wrap gap-1.5">
          {citations.map((c, i) => (
            <CitationChip
              key={c.chunk_id}
              citation={{
                chunk_id: c.chunk_id,
                upload_id: c.upload_id ?? null,
                section_title: c.section_title ?? null,
                text: c.text,
              }}
              index={i + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessageResponse }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex flex-col gap-2", isUser && "items-end")}>
      <div
        className={cn(
          "max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm",
          isUser
            ? "bg-primary text-primary-foreground"
            : "border border-border bg-card font-study text-foreground",
        )}
      >
        {message.content}
      </div>
      {!isUser && message.citations && message.citations.length > 0 && (
        <div className="flex max-w-[85%] flex-wrap gap-1.5">
          {message.citations.map((c, i) => (
            <CitationChip key={c.chunk_id} citation={c} index={i + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

function CitationChip({
  citation,
  index,
}: {
  citation: ChatCitation;
  index: number;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] font-medium text-muted-foreground transition-colors hover:bg-muted/70"
      >
        <FileText className="size-2.5" />
        {citation.section_title || `Source ${index}`}
      </button>
      {open && (
        <div className="absolute left-0 top-full z-20 mt-1 w-72 rounded-lg border border-border bg-popover p-3 shadow-lg">
          <p className="mb-2 font-study text-xs leading-relaxed text-muted-foreground">
            {citation.text.slice(0, 400)}
            {citation.text.length > 400 ? "…" : ""}
          </p>
          {citation.upload_id && (
            <Link
              to={`/uploads/${citation.upload_id}`}
              className="text-[10px] font-medium text-primary hover:underline"
            >
              Open source →
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
