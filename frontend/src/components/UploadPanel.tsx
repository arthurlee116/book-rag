import { useRef, useState } from "react";
import { Button, Upload, Typography, Alert, Space } from "antd";
import { UploadOutlined, DeleteOutlined } from "@ant-design/icons";
import { useErrStore } from "@/lib/store";

const { Text } = Typography;

export function UploadPanel() {
  const backendUrl = useErrStore((s) => s.backendUrl);
  const sessionId = useErrStore((s) => s.sessionId);
  const setSessionId = useErrStore((s) => s.setSessionId);
  const uploadStatus = useErrStore((s) => s.uploadStatus);
  const setUploadStatus = useErrStore((s) => s.setUploadStatus);
  const clearLogs = useErrStore((s) => s.clearLogs);
  const setActiveChunk = useErrStore((s) => s.setActiveChunk);
  const closeRightPanel = useErrStore((s) => s.closeRightPanel);

  const fileRef = useRef<File | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const canUpload = uploadStatus !== "processing";

  const onUpload = async () => {
    const file = fileRef.current;
    if (!file) return;

    setError(null);
    clearLogs();
    setActiveChunk(null);
    closeRightPanel();
    setUploadStatus("processing");

    const fd = new FormData();
    fd.append("file", file);

    const resp = await fetch(`${backendUrl}/upload`, {
      method: "POST",
      headers: sessionId ? { "X-Session-Id": sessionId } : {},
      body: fd,
    });

    if (!resp.ok) {
      const msg = await resp.text();
      setUploadStatus("error");
      setError(msg || `Upload failed (${resp.status})`);
      return;
    }

    const data = (await resp.json()) as { session_id: string };
    setSessionId(data.session_id);
  };

  const onClear = () => {
    fileRef.current = null;
    setFileName(null);
    setError(null);
  };

  return (
    <div
      style={{
        background: "#2c2c2e",
        borderRadius: 12,
        padding: 16,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div>
          <Text strong style={{ color: "#f5f5f7", fontSize: 13 }}>Upload Document</Text>
          <br />
          <Text style={{ color: "#6e6e73", fontSize: 12 }}>
            .txt, .md, .docx, .epub, .mobi
          </Text>
        </div>
        <Button
          icon={<DeleteOutlined />}
          onClick={onClear}
          size="small"
          style={{ background: "#3a3a3c", borderColor: "transparent" }}
        >
          Clear
        </Button>
      </div>

      <Space size={12}>
        <Upload
          accept=".txt,.md,.docx,.epub,.mobi"
          beforeUpload={(file) => {
            fileRef.current = file;
            setFileName(file.name);
            return false;
          }}
          showUploadList={false}
          disabled={!canUpload}
        >
          <Button disabled={!canUpload} style={{ background: "#3a3a3c", borderColor: "transparent" }}>
            Select File
          </Button>
        </Upload>
        <Button
          type="primary"
          icon={<UploadOutlined />}
          onClick={onUpload}
          disabled={!canUpload || !fileName}
        >
          Upload
        </Button>
      </Space>

      {fileName && (
        <div style={{ marginTop: 12 }}>
          <Text style={{ color: "#a1a1a6", fontSize: 12 }}>
            {fileName}
          </Text>
        </div>
      )}

      {error && (
        <Alert type="error" message={error} style={{ marginTop: 12 }} showIcon />
      )}
    </div>
  );
}
