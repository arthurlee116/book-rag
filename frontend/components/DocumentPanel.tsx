"use client";

import { BookOpen, X } from "lucide-react";

import { useErrStore } from "@/lib/store";

export function DocumentPanel() {
  const activeChunk = useErrStore((s) => s.activeChunk);
  const closeRightPanel = useErrStore((s) => s.closeRightPanel);

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/20">
      <div className="flex items-center justify-between border-b border-zinc-800 p-4">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-zinc-300" />
          <div className="text-sm font-medium text-zinc-200">Document Viewer</div>
        </div>
        <button
          type="button"
          onClick={closeRightPanel}
          className="rounded-md border border-zinc-800 bg-zinc-900/30 p-2 text-zinc-200 hover:bg-zinc-900"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="p-4">
        {!activeChunk ? (
          <div className="text-sm text-zinc-500">
            Click a citation like <span className="font-mono">[1]</span> to open the “Island View”.
          </div>
        ) : (
          <div className="space-y-4 text-sm">
            {activeChunk.prev_content ? (
              <div className="rounded-md border border-zinc-800 bg-zinc-950/30 p-3 text-zinc-500">
                {activeChunk.prev_content}
              </div>
            ) : null}

            <div className="rounded-md border border-indigo-600/40 bg-indigo-950/20 p-3 text-zinc-100">
              <div className="mb-2 text-xs font-medium text-indigo-200">Current Chunk</div>
              <div className="font-medium">{activeChunk.content}</div>
            </div>

            {activeChunk.next_content ? (
              <div className="rounded-md border border-zinc-800 bg-zinc-950/30 p-3 text-zinc-500">
                {activeChunk.next_content}
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

