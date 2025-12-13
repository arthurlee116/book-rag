import "./globals.css";

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "ERR — Ephemeral RAG Reader",
  description: "Privacy-first, session-based document Q&A (strict RAG)."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-zinc-950 text-zinc-100">{children}</body>
    </html>
  );
}

