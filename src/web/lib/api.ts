export interface Ticket {
  ticket_number: string;
  account_id: string;
  subject: string;
  status: string;
  created_at: string;
  resolution: string | null;
}

export interface Citation {
  type: "citation";
  chunk_id: string;
  document_id: string;
  source_path: string;
  title: string;
  section_heading: string;
  page_number: number | null;
}

export interface TicketContextEvent {
  type: "ticket_context";
  ticket_number: string;
  note: string;
}

export interface TokenEvent {
  type: "token";
  content: string;
}

export interface ErrorEvent {
  type: "error";
  message: string;
  trace_id: string;
}

export interface DoneEvent {
  type: "done";
}

export type SSEEvent =
  | Citation
  | TicketContextEvent
  | TokenEvent
  | ErrorEvent
  | DoneEvent;

const API_BASE = "/api";

export async function fetchTickets(token: string): Promise<Ticket[]> {
  const res = await fetch(`${API_BASE}/tickets`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(`Failed to fetch tickets: ${res.status}`);
  const data = await res.json();
  return data.tickets;
}

export async function* streamChat(
  query: string,
  token: string
): AsyncGenerator<SSEEvent> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ query }),
  });

  if (!res.ok || !res.body) {
    throw new Error(`Chat request failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const event: SSEEvent = JSON.parse(line.slice(6));
          yield event;
        } catch {
          // skip malformed events
        }
      }
    }
  }
}
