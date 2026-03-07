import { useRef, useState, useCallback, useMemo, useEffect } from "react";
import { Button, Upload, Typography, Alert, Space } from "antd";
import {
  UploadOutlined,
  DeleteOutlined,
  FileTextOutlined,
  CloudUploadOutlined,
} from "@ant-design/icons";
import { useErrStore } from "@/lib/store";
import { themeTokens } from "@/theme";

const { Text } = Typography;

/**
 * Upload Panel Component - Enhanced with glassmorphism and animations
 *
 * Features:
 * - Drag and drop support
 * - Visual feedback on hover
 * - Progress indication during upload
 * - Glassmorphism styling
 */
export function UploadPanel() {
  const backendUrl = useErrStore((s) => s.backendUrl);
  const sessionId = useErrStore((s) => s.sessionId);
  const setSessionId = useErrStore((s) => s.setSessionId);
  const uploadStatus = useErrStore((s) => s.uploadStatus);
  const setUploadStatus = useErrStore((s) => s.setUploadStatus);
  const clearLogs = useErrStore((s) => s.clearLogs);
  const setActiveChunk = useErrStore((s) => s.setActiveChunk);
  const closeRightPanel = useErrStore((s) => s.closeRightPanel);
  const logs = useErrStore((s) => s.logs);

  const fileRef = useRef<File | null>(null);
  const isMounted = useRef(true); // P3: unmount guard
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  // P3: Prevent state updates on an unmounted component
  useEffect(() => {
    isMounted.current = true;
    return () => { isMounted.current = false; };
  }, []);

  const canUpload = uploadStatus !== "processing";
  const isProcessing = uploadStatus === "processing";
  const selectedFileSizeKb =
    fileRef.current && Number.isFinite(fileRef.current.size)
      ? (fileRef.current.size / 1024).toFixed(1)
      : "0.0";

  // Parse progress from logs
  const progress = useMemo(() => {
    const progressLog = logs.find((log) => log.includes("Progress:"));
    if (progressLog) {
      const match = progressLog.match(/Progress:\s*(\d+)%/);
      return match ? parseInt(match[1], 10) : 0;
    }
    return isProcessing ? 50 : 0;
  }, [logs, isProcessing]);

  const onUpload = async () => {
    const file = fileRef.current;
    if (!file) return;

    setError(null);
    clearLogs();
    setActiveChunk(null);
    closeRightPanel();
    setUploadStatus("processing");

    const ensureSessionId = () => {
      if (sessionId) return sessionId;
      // P2: Always use a cryptographically secure source — crypto.randomUUID if
      // available, otherwise crypto.getRandomValues() for high-entropy fallback.
      let generated: string;
      if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        generated = crypto.randomUUID();
      } else {
        // Secure fallback: 128 bits from CSPRNG
        const buf = new Uint8Array(16);
        crypto.getRandomValues(buf);
        generated = Array.from(buf, (b) => b.toString(16).padStart(2, "0")).join("-");
      }
      setSessionId(generated);
      return generated;
    };

    const activeSessionId = ensureSessionId();
    const fd = new FormData();
    fd.append("file", file);

    try {
      const resp = await fetch(`${backendUrl}/upload`, {
        method: "POST",
        headers: activeSessionId ? { "X-Session-Id": activeSessionId } : {},
        body: fd,
      });

      if (!resp.ok) {
        const msg = await resp.text();
        if (!isMounted.current) return; // P3: guard
        setUploadStatus("error");
        setError(msg || `Upload failed (${resp.status})`);
        return;
      }

      const data = (await resp.json()) as { session_id: string };
      if (!isMounted.current) return; // P3: guard
      if (data.session_id && data.session_id !== activeSessionId) {
        setSessionId(data.session_id);
      }
    } catch (err) {
      if (!isMounted.current) return; // P3: guard
      setUploadStatus("error");
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  };

  const onClear = () => {
    fileRef.current = null;
    setFileName(null);
    setError(null);
  };

  const handleFile = (file: File) => {
    fileRef.current = file;
    setFileName(file.name);
    setError(null);
    return false;
  };

  // Drag and drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        handleFile(files[0]);
      }
    },
    []
  );

  return (
    <div
      className="glass-panel"
      style={{
        padding: "20px",
        position: "relative",
        overflow: "hidden",
        transition: "all 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
        ...(isDragging && {
          borderColor: themeTokens.accentPrimary,
          boxShadow: `0 0 24px rgba(212, 145, 92, 0.2)`,
        }),
      }}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Progress Bar Overlay */}
      {isProcessing && (
        <div
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: "3px",
            background: themeTokens.surfaceAccentSubtle,
            zIndex: 1,
          }}
        >
          <div
            style={{
              height: "100%",
              background: `linear-gradient(90deg, ${themeTokens.accentPrimary}, ${themeTokens.accentHover})`,
              width: `${progress}%`,
              transition: "width 0.3s ease",
              boxShadow: `0 0 10px rgba(212, 145, 92, 0.4)`,
            }}
          />
        </div>
      )}

      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "16px",
        }}
      >
        <div>
          <Text
            strong
            style={{
              color: themeTokens.textPrimary,
              fontSize: "14px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <CloudUploadOutlined style={{ color: themeTokens.accentPrimary }} />
            Upload Document
          </Text>
          <div style={{ marginTop: "4px" }}>
            <Text style={{ color: themeTokens.textTertiary, fontSize: "12px" }}>
              .txt .md .docx .epub .mobi
            </Text>
          </div>
        </div>
        <Button
          icon={<DeleteOutlined />}
          onClick={onClear}
          size="small"
          disabled={!fileName && !isProcessing}
          style={{
            background: themeTokens.bgElevated,
            borderColor: themeTokens.border,
            color: themeTokens.textSecondary,
          }}
        >
          Clear
        </Button>
      </div>

      {/* Upload Zone */}
      <Upload.Dragger
        accept=".txt,.md,.docx,.epub,.mobi"
        beforeUpload={handleFile}
        showUploadList={false}
        disabled={!canUpload}
        style={{
          background: isDragging ? "rgba(212, 145, 92, 0.04)" : themeTokens.surfaceContainer,
          border: `2px dashed ${isDragging ? themeTokens.accentPrimary : themeTokens.border}`,
          borderRadius: "12px",
          padding: "24px 16px",
          marginBottom: "16px",
        }}
      >
        <div style={{ textAlign: "center" }}>
          {fileName ? (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "12px",
                padding: "12px",
                background: themeTokens.surfaceAccentSubtle,
                borderRadius: "10px",
                border: `1px solid rgba(212, 145, 92, 0.12)`,
              }}
            >
              <FileTextOutlined style={{ fontSize: "24px", color: themeTokens.accentPrimary }} />
              <div style={{ textAlign: "left" }}>
                <Text style={{ color: themeTokens.textPrimary, fontSize: "13px", display: "block" }}>
                  {fileName}
                </Text>
                <Text style={{ color: themeTokens.textTertiary, fontSize: "11px" }}>
                  {selectedFileSizeKb} KB
                </Text>
              </div>
            </div>
          ) : (
            <>
              <p
                className="ant-upload-drag-icon"
                style={{
                  marginBottom: "12px",
                  color: isDragging ? themeTokens.accentPrimary : themeTokens.textTertiary,
                }}
              >
                <CloudUploadOutlined style={{ fontSize: "36px" }} />
              </p>
              <Text style={{ color: themeTokens.textSecondary, fontSize: "13px" }}>
                Click or drag file to upload
              </Text>
            </>
          )}
        </div>
      </Upload.Dragger>

      {/* Action Buttons */}
      <Space size={10} style={{ width: "100%", display: "flex" }}>
        <Upload
          accept=".txt,.md,.docx,.epub,.mobi"
          beforeUpload={handleFile}
          showUploadList={false}
          disabled={!canUpload}
          style={{ flex: 1 }}
        >
          <Button
            disabled={!canUpload}
            block
            style={{
              background: themeTokens.bgElevated,
              borderColor: themeTokens.border,
              color: themeTokens.textPrimary,
              height: "40px",
            }}
          >
            Select File
          </Button>
        </Upload>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          onClick={onUpload}
          disabled={!canUpload || !fileName}
          style={{
            height: "40px",
            minWidth: "100px",
            background: isProcessing ? undefined : themeTokens.gradientAccent,
            border: "none",
            color: themeTokens.textOnAccent,
            fontWeight: 600,
          }}
        >
          {isProcessing ? "Processing…" : "Upload"}
        </Button>
      </Space>

      {/* Error Display */}
      {error && (
        <Alert
          type="error"
          message={error}
          style={{
            marginTop: "16px",
            background: themeTokens.surfaceErrorSubtle,
            borderColor: themeTokens.borderErrorSubtle,
          }}
          showIcon
        />
      )}

      {/* Processing Status */}
      {isProcessing && (
        <div
          style={{
            marginTop: "12px",
            padding: "10px 12px",
            background: "rgba(212, 145, 92, 0.04)",
            border: `1px solid rgba(212, 145, 92, 0.08)`,
            borderRadius: "10px",
            display: "flex",
            alignItems: "center",
            gap: "10px",
          }}
        >
          <span
            className="status-dot processing"
            style={{ margin: 0 }}
          />
          <Text style={{ color: themeTokens.textSecondary, fontSize: "12px" }}>
            Processing document... {progress}%
          </Text>
        </div>
      )}
    </div>
  );
}
