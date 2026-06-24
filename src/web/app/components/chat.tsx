"use client";

import { useCallback, useRef, useState } from "react";
import { Send } from "lucide-react";
import { Citation, SSEEvent, streamChat, TicketContextEvent } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  ticketContext: TicketContextEvent[];
  error?: string;
}

export function ChatPanel({
  token,
  onDone,
}: {
  token: string;
  onDone?: () => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
  }, []);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      const query = input.trim();
      if (!query || loading) return;

      setInput("");
      setLoading(true);

      const userMsg: Message = {
        role: "user",
        content: query,
        citations: [],
        ticketContext: [],
      };

      const assistantMsg: Message = {
        role: "assistant",
        content: "",
        citations: [],
        ticketContext: [],
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      scrollToBottom();

      try {
        let content = "";
        const citations: Citation[] = [];
        const ticketContext: TicketContextEvent[] = [];

        for await (const event of streamChat(query, token)) {
          switch (event.type) {
            case "token":
              content += event.content;
              break;
            case "citation":
              citations.push(event);
              break;
            case "ticket_context":
              ticketContext.push(event);
              break;
            case "error":
              setMessages((prev) => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last.role === "assistant") {
                  last.error = event.message;
                  last.content = content;
                  last.citations = citations;
                  last.ticketContext = ticketContext;
                }
                return updated;
              });
              setLoading(false);
              return;
            case "done":
              break;
          }

          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last.role === "assistant") {
              last.content = content;
              last.citations = [...citations];
              last.ticketContext = [...ticketContext];
            }
            return updated;
          });
          scrollToBottom();
        }

        // Notify parent that a chat completed (ticket may have been created)
        onDone?.();
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Unknown error";
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === "assistant") {
            last.error = message;
          }
          return updated;
        });
      } finally {
        setLoading(false);
      }
    },
    [input, loading, token, scrollToBottom, onDone]
  );

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex items-center justify-center h-full text-sm text-[var(--muted-foreground)]">
            Ask a question about Azure Site Recovery, VMware DR, or Hyper-V replication.
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-3 text-sm ${
                msg.role === "user"
                  ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                  : "bg-[var(--muted)] text-[var(--foreground)]"
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content || (loading && i === messages.length - 1 ? "..." : "")}</p>

              {msg.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-[var(--border)]">
                  <p className="text-xs font-medium text-[var(--muted-foreground)] mb-1">
                    Sources
                  </p>
                  {msg.citations.map((cite, ci) => (
                    <div key={ci} className="text-xs text-[var(--muted-foreground)] mt-1">
                      <span className="font-medium">{cite.title}</span>
                      {cite.section_heading && <> — {cite.section_heading}</>}
                    </div>
                  ))}
                </div>
              )}

              {msg.ticketContext.length > 0 && (
                <div className="mt-2 pt-2 border-t border-[var(--border)]">
                  <p className="text-xs font-medium text-[var(--muted-foreground)] mb-1">
                    Related Tickets
                  </p>
                  {msg.ticketContext.map((tc, ti) => (
                    <div key={ti} className="text-xs text-[var(--muted-foreground)]">
                      Ticket #{tc.ticket_number} — {tc.note}
                    </div>
                  ))}
                </div>
              )}

              {msg.error && (
                <p className="mt-2 text-xs text-red-500">Error: {msg.error}</p>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={handleSubmit}
        className="border-t border-[var(--border)] p-4 flex gap-2"
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a technical support question..."
          disabled={loading}
          className="flex-1 rounded border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)] disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="rounded bg-[var(--primary)] px-4 py-2 text-[var(--primary-foreground)] hover:opacity-90 disabled:opacity-50"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </div>
  );
}
