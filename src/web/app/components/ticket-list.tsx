"use client";

import { useCallback, useEffect, useState } from "react";
import { FileText } from "lucide-react";
import { fetchTickets, Ticket } from "@/lib/api";

export function TicketPanel({
  token,
  refreshKey,
}: {
  token: string;
  refreshKey?: number;
}) {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const loadTickets = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchTickets(token);
      setTickets(data);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tickets");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    loadTickets();
  }, [loadTickets, refreshKey]);

  const toggleTicket = (ticketNumber: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(ticketNumber)) {
        next.delete(ticketNumber);
      } else {
        next.add(ticketNumber);
      }
      return next;
    });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-[var(--border)]">
        <h2 className="text-sm font-semibold flex items-center gap-2">
          <FileText className="h-4 w-4" />
          Your Tickets
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && (
          <p className="p-4 text-sm text-[var(--muted-foreground)]">Loading tickets...</p>
        )}
        {error && (
          <p className="p-4 text-sm text-red-500">{error}</p>
        )}
        {!loading && !error && tickets.length === 0 && (
          <p className="p-4 text-sm text-[var(--muted-foreground)]">No tickets found.</p>
        )}
        {tickets.map((ticket) => (
          <div
            key={ticket.ticket_number}
            className="border-b border-[var(--border)]"
          >
            <button
              onClick={() => toggleTicket(ticket.ticket_number)}
              className="w-full text-left px-4 py-3 hover:bg-[var(--muted)] transition-colors"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium truncate">
                  {ticket.subject}
                </span>
                <span
                  className={`shrink-0 text-xs px-2 py-0.5 rounded-full ${
                    ticket.status === "closed"
                      ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                      : "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300"
                  }`}
                >
                  {ticket.status}
                </span>
              </div>
              <p className="text-xs text-[var(--muted-foreground)] mt-1">
                #{ticket.ticket_number} · {new Date(ticket.created_at).toLocaleDateString()}
              </p>
            </button>
            {expanded.has(ticket.ticket_number) && (
              <div className="px-4 pb-3">
                <p className="text-xs text-[var(--muted-foreground)] leading-relaxed">
                  {ticket.resolution || "No resolution recorded yet."}
                </p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
