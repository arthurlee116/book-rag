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
