"use client";

import { useCallback, useEffect, useState } from "react";
import { getAccessToken, useUser } from "@auth0/nextjs-auth0";
import { ChatPanel } from "./components/chat";
import { TicketPanel } from "./components/ticket-list";

export default function Home() {
  const { user, error: authError, isLoading } = useUser();
  const [token, setToken] = useState<string>("");
  const [email, setEmail] = useState("");
  const [tokenLoading, setTokenLoading] = useState(false);
  const [tokenError, setTokenError] = useState("");
  const [ticketRefreshKey, setTicketRefreshKey] = useState(0);

  const refreshTickets = useCallback(() => {
    setTicketRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    if (user && !token && !tokenError) {
      setTokenLoading(true);
      setTokenError("");
      getAccessToken()
        .then((t) => setToken(t as string))
        .catch((e) => {
          const msg = e instanceof Error ? e.message : String(e);
          console.error("Failed to get access token:", msg);
          setTokenError(msg);
        })
        .finally(() => setTokenLoading(false));
    }
  }, [user, token, tokenError]);

  if (isLoading || tokenLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <p className="text-sm text-[var(--muted-foreground)]">Loading...</p>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center p-4">
        <div className="w-full max-w-md space-y-6">
          <div className="text-center">
            <h1 className="text-2xl font-bold tracking-tight">
              Tech Support AI Agent
            </h1>
            <p className="mt-2 text-sm text-[var(--muted-foreground)]">
              Sign in with your email to continue
            </p>
          </div>

          {tokenError && (
            <div className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700">
              Failed to get API token: {tokenError}
              {" "}—{" "}
              <button
                onClick={() => setTokenError("")}
                className="underline hover:no-underline"
              >
                Retry
              </button>
            </div>
          )}

          {authError && !user && (
            <div className="rounded border border-amber-300 bg-amber-50 p-3 text-sm text-amber-700">
              Auth session check failed: {authError.message}
              {" "}—{" "}
              <a href="/auth/login" className="underline hover:no-underline">
                Sign in again
              </a>
            </div>
          )}

          {user && (
            <div className="rounded border border-green-300 bg-green-50 p-3 text-sm text-green-700">
              ✓ Signed in as {user.email || user.name}. Fetching API token…
            </div>
          )}

          <div className="rounded-lg border border-[var(--border)] bg-[var(--background)] p-6">
            <div className="space-y-4">
              <p className="text-sm font-medium text-[var(--foreground)]">
                Please sign-in with your email:
              </p>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full rounded border border-[var(--border)] bg-[var(--background)] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              />
              <a
                href={`/auth/login?login_hint=${encodeURIComponent(email)}`}
                className="block w-full rounded bg-[var(--primary)] px-4 py-2 text-center text-sm font-medium text-[var(--primary-foreground)] hover:opacity-90"
              >
                Send Magic Link
              </a>
              <p className="text-xs text-[var(--muted-foreground)]">
                You'll be redirected to Auth0 to complete sign-in via email
                magic link.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen">
      <aside className="w-80 shrink-0 border-r border-[var(--border)] overflow-y-auto">
        <TicketPanel token={token} refreshKey={ticketRefreshKey} />
      </aside>
      <main className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center justify-between border-b border-[var(--border)] px-6 py-3">
          <h1 className="text-lg font-semibold">Tech Support AI</h1>
          <div className="flex items-center gap-4">
            {user && (
              <span className="text-sm text-[var(--muted-foreground)]">
                {user.email || user.name}
              </span>
            )}
            <a
              href="/auth/logout"
              className="text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
            >
              Sign out
            </a>
          </div>
        </header>
        <ChatPanel token={token} onDone={refreshTickets} />
      </main>
    </div>
  );
}
