import { useMemo, useState } from "react";
import { Button, Collapse, Table, Tag, Typography } from "antd";
import { useErrStore } from "@/lib/store";
import type { Evaluation, RetrievalStepData } from "@/lib/types";

const { Text } = Typography;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function getRecordArray(value: unknown): Record<string, unknown>[] | null {
  if (!Array.isArray(value)) return null;
  if (value.every((item) => isRecord(item))) return value as Record<string, unknown>[];
  return null;
}

function buildSimpleTable(
  rows: Record<string, unknown>[],
  columns: { key: string; title: string }[],
) {
  return (
    <Table
      size="small"
      pagination={false}
      dataSource={rows.map((row, idx) => ({ key: `${idx}`, ...row }))}
      columns={columns.map((col) => ({
        title: col.title,
        dataIndex: col.key,
        key: col.key,
        render: (value: unknown) => (value === undefined || value === null ? "-" : String(value)),
      }))}
    />
  );
}

function renderStepDetails(step: RetrievalStepData) {
  const data = step.data ?? {};
  if (!isRecord(data)) return <Text type="secondary">No data recorded.</Text>;

  const chunks = getRecordArray(data.chunks);
  if (chunks) {
    return buildSimpleTable(chunks, [
      { key: "chunk_id", title: "Chunk" },
      { key: "rank", title: "Rank" },
      { key: "score", title: "Score" },
      { key: "preview", title: "Preview" },
    ]);
  }

  const topkChunks = getRecordArray(data.topk_chunks);
  if (topkChunks) {
    return buildSimpleTable(topkChunks, [
      { key: "chunk_id", title: "Chunk" },
      { key: "chunk_idx", title: "Idx" },
      { key: "final_score", title: "Final" },
      { key: "vector_score", title: "Vector" },
      { key: "bm25_norm", title: "BM25" },
    ]);
  }

  const rankedIds = Array.isArray(data.ranked_ids) ? data.ranked_ids : null;
  if (rankedIds) {
    const rows = rankedIds.map((chunkId, idx) => ({
      rank: idx + 1,
      chunk_id: chunkId,
    }));
    return buildSimpleTable(rows, [
      { key: "rank", title: "Rank" },
      { key: "chunk_id", title: "Chunk" },
    ]);
  }

  const filteredIds = Array.isArray(data.filtered) ? data.filtered : null;
  if (filteredIds) {
    const rows = filteredIds.map((chunkId, idx) => ({
      rank: idx + 1,
      chunk_id: chunkId,
      reason: "filtered",
    }));
    return buildSimpleTable(rows, [
      { key: "rank", title: "Rank" },
      { key: "chunk_id", title: "Chunk" },
      { key: "reason", title: "Reason" },
    ]);
  }

  const topkIndices = Array.isArray(data.topk_indices) ? data.topk_indices : null;
  const rawScores = Array.isArray(data.raw_scores) ? data.raw_scores : null;
  if (topkIndices && rawScores) {
    const rows = topkIndices.map((idx, i) => ({
      index: idx,
      score: rawScores[i],
    }));
    return buildSimpleTable(rows, [
      { key: "index", title: "Index" },
      { key: "score", title: "Score" },
    ]);
  }

  return (
    <pre style={{ margin: 0, whiteSpace: "pre-wrap", color: "#a1a1a6" }}>
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function buildPanels(evaluation: Evaluation) {
  return evaluation.steps.map((step, idx) => ({
    key: `${step.name}-${idx}`,
    label: (
      <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Text style={{ color: "#f5f5f7" }}>{step.name}</Text>
        {step.skipped ? (
          <Tag color="red">skipped</Tag>
        ) : (
          <Tag color="green">enabled</Tag>
        )}
      </span>
    ),
    children: (
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {step.reason && (
          <Text type="secondary">Reason: {step.reason}</Text>
        )}
        {renderStepDetails(step)}
      </div>
    ),
  }));
}

export function EvaluationPanel() {
  const sessionId = useErrStore((s) => s.sessionId);
  const evaluation = useErrStore((s) => s.evaluation);
  const fetchEvaluation = useErrStore((s) => s.fetchEvaluation);
  const isDesktop = useErrStore((s) => s.isDesktop);
  const [loading, setLoading] = useState(false);

  const panels = useMemo(
    () => (evaluation ? buildPanels(evaluation) : []),
    [evaluation],
  );

  const onFetch = async () => {
    if (!sessionId || loading) return;
    setLoading(true);
    await fetchEvaluation();
    setLoading(false);
  };

  return (
    <div
      style={{
        background: "#1c1c1e",
        borderRadius: 12,
        padding: 16,
        border: "1px solid #2c2c2e",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
        <Text strong style={{ color: "#f5f5f7", fontSize: 13 }}>Retrieval Evaluation</Text>
        <Button
          size="small"
          onClick={onFetch}
          disabled={!sessionId || loading}
          style={{ background: "#3a3a3c", borderColor: "transparent", color: "#a1a1a6" }}
        >
          {loading ? "Loading..." : "Load Latest"}
        </Button>
      </div>

      {!sessionId ? (
        <Text style={{ color: "#6e6e73" }}>Upload a document to start a session.</Text>
      ) : !evaluation ? (
        <Text style={{ color: "#6e6e73" }}>No evaluation loaded yet.</Text>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <Tag color={evaluation.mode === "fast" ? "gold" : "blue"}>
              {evaluation.mode === "fast" ? "fast mode" : "normal mode"}
            </Tag>
            <Text style={{ color: "#a1a1a6", fontSize: 12 }}>
              {new Date(evaluation.timestamp).toLocaleString()}
            </Text>
          </div>
          <div style={{ background: "#2c2c2e", borderRadius: 8, padding: 12 }}>
            <Text style={{ color: "#a1a1a6", fontSize: 12 }}>User Query</Text>
            <div style={{ color: "#f5f5f7", marginTop: 6 }}>{evaluation.user_query}</div>
          </div>
          <Collapse
            size="small"
            items={panels}
            style={{ background: "#1c1c1e" }}
          />
          {!isDesktop && (
            <Text style={{ color: "#6e6e73", fontSize: 12 }}>
              Tip: expand steps for ranking details.
            </Text>
          )}
        </div>
      )}
    </div>
  );
}
