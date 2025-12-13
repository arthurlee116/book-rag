"use client";

import { useEffect, useMemo } from "react";
import { AlertTriangle } from "lucide-react";

import { ChatPanel } from "@/components/ChatPanel";
import { DocumentPanel } from "@/components/DocumentPanel";
import { TerminalWindow } from "@/components/TerminalWindow";
import { UploadPanel } from "@/components/UploadPanel";
import { useErrStore } from "@/lib/store";

function useIsDesktop() {
  const setIsDesktop = useErrStore((s) => s.setIsDesktop);

  useEffect(() => {
    const check = () => setIsDesktop(window.innerWidth >= 900);
    check();
    window.addEventListener("resize", check);
    return () => window.removeEventListener("resize", check);
  }, [setIsDesktop]);

  return useErrStore((s) => s.isDesktop);
}

export default function HomePage() {
  const isDesktop = useIsDesktop();
  const uploadStatus = useErrStore((s) => s.uploadStatus);
  const rightPanelOpen = useErrStore((s) => s.rightPanelOpen);

  const showTerminal = useMemo(() => uploadStatus === "processing", [uploadStatus]);

  return (
    <main className="mx-auto max-w-[1400px] p-6">
      {!isDesktop ? (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/30 p-4 text-sm text-zinc-200">
          <div className="mb-2 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            <span className="font-medium">Desktop recommended</span>
          </div>
          <p className="text-zinc-300">
            ERR is desktop-first (split view). Mobile support is minimal; please use a wider screen
            for the best experience.
          </p>
        </div>
      ) : null}

      <div className="mt-6 grid grid-cols-12 gap-4">
        <section className={rightPanelOpen ? "col-span-7" : "col-span-12"}>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900/20">
            <div className="border-b border-zinc-800 p-4">
              <h1 className="text-lg font-semibold">Ephemeral RAG Reader (ERR)</h1>
              <p className="mt-1 text-sm text-zinc-400">
                Session-based, in-memory only. Strict RAG: no outside knowledge.
              </p>
            </div>
            <div className="p-4">
              <UploadPanel />
              {showTerminal ? (
                <div className="mt-4">
                  <TerminalWindow />
                </div>
              ) : null}
              <div className="mt-4">
                <ChatPanel />
              </div>
            </div>
          </div>
        </section>

        {rightPanelOpen ? (
          <aside className="col-span-5">
            <DocumentPanel />
          </aside>
        ) : null}
      </div>
    </main>
  );
}

