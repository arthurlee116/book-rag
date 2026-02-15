import { useMemo, useState } from "react";
import { Button, Collapse, Table, Tag, Typography } from "antd";
import { DownOutlined, UpOutlined, BarChartOutlined } from "@ant-design/icons";
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
      style={{ background: "transparent" }}
    />
  );
}

function renderStepDetails(step: RetrievalStepData) {
  const data = step.data ?? {};
  if (!isRecord(data)) return <Text style={{ color: "#6b7280" }}>No data recorded.</Text>;

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
    <pre style={{ margin: 0, whiteSpace: "pre-wrap", color: "#9ca3af", fontSize: "12px" }}>
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

function buildPanels(evaluation: Evaluation) {
  return evaluation.steps.map((step, idx) => ({
    key: `${step.name}-${idx}`,
    label: (
      <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <Text style={{ color: "#e5e5e5" }}>{step.name}</Text>
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
          <Text style={{ color: "#6b7280", fontSize: "12px" }}>Reason: {step.reason}</Text>
        )}
        {renderStepDetails(step)}
      </div>
    ),
  }));
}

/**
 * Evaluation Panel Component - Displays retrieval pipeline metrics
 *
 * Shows detailed breakdown of each retrieval step including
 * query expansion, vector search, BM25, fusion, and reranking.
 */
export function EvaluationPanel() {
  const sessionId = useErrStore((s) => s.sessionId);
  const evaluation = useErrStore((s) => s.evaluation);
  const fetchEvaluation = useErrStore((s) => s.fetchEvaluation);

  const isDesktop = useErrStore((s) => s.isDesktop);
  const [loading, setLoading] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

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
      className="glass-panel"
      style={{
        padding: "16px",
        border: "1px solid #1f2937",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <BarChartOutlined style={{ color: "#00d4ff", fontSize: "14px" }} />
          <Text strong style={{ color: "#e5e5e5", fontSize: "14px" }}>Retrieval Evaluation</Text>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Button
            size="small"
            type="text"
            icon={collapsed ? <DownOutlined /> : <UpOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            style={{ color: "#9ca3af" }}
          />
          <Button
            size="small"
            onClick={onFetch}
            disabled={!sessionId || loading}
            style={{
              background: "#14141a",
              borderColor: "#1f2937",
              color: "#9ca3af",
              height: "32px",
            }}
          >
            {loading ? "Loading..." : "Load Latest"}
          </Button>
        </div>
      </div>

      {!collapsed && (
        !sessionId ? (
          <Text style={{ color: "#6b7280", fontSize: "13px" }}>Upload a document to start a session.</Text>
        ) : !evaluation ? (
          <Text style={{ color: "#6b7280", fontSize: "13px" }}>No evaluation loaded yet.</Text>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
              <Tag
                color={evaluation.mode === "fast" ? "gold" : "blue"}
                style={{
                  background: evaluation.mode === "fast"
                    ? "rgba(245, 158, 11, 0.15)"
                    : "rgba(59, 130, 246, 0.15)",
                  borderColor: evaluation.mode === "fast"
                    ? "rgba(245, 158, 11, 0.3)"
                    : "rgba(59, 130, 246, 0.3)",
                  color: evaluation.mode === "fast" ? "#f59e0b" : "#3b82f6",
                }}
              >
                {evaluation.mode === "fast" ? "fast mode" : "normal mode"}
              </Tag>
              <Text style={{ color: "#6b7280", fontSize: "11px" }}>
                {new Date(evaluation.timestamp).toLocaleString()}
              </Text>
            </div>
            <div
              style={{
                background: "rgba(20, 20, 26, 0.5)",
                borderRadius: 8,
                padding: "12px",
                border: "1px solid #1f2937",
              }}
            >
              <Text style={{ color: "#6b7280", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                User Query
              </Text>
              <div style={{ color: "#e5e5e5", marginTop: "6px", fontSize: "13px" }}>
                {evaluation.user_query}
              </div>
            </div>
            <Collapse
              size="small"
              items={panels}
              style={{ background: "transparent" }}
            />
            {!isDesktop && (
              <Text style={{ color: "#6b7280", fontSize: "12px" }}>
                Tip: expand steps for ranking details.
              </Text>
            )}
          </div>
        )
      )}
    </div>
  );
}
