import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tech Support AI Agent",
  description: "AI-powered technical support assistant",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[var(--background)] text-[var(--foreground)] antialiased">
        {children}
      </body>
    </html>
  );
}
