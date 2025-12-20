export type ChunkModel = {
  id: string;
  content: string;
  rich_content: string;
  prev_content?: string | null;
  next_content?: string | null;
  metadata: Record<string, unknown>;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  citations?: ChunkModel[];
};

export interface ChunkPreview {
  chunk_id: string;
  rank: number;
  score: number;
  preview: string;
}

export interface RetrievalStepData {
  name: string;
  skipped: boolean;
  reason?: string | null;
  data?: Record<string, unknown> | null;
}

export interface Evaluation {
  session_id: string;
  user_query: string;
  mode: "fast" | "normal";
  timestamp: string;
  steps: RetrievalStepData[];
  final_context: ChunkPreview[];
}
