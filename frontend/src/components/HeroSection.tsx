import { ReactNode } from "react";
import { Space, Typography } from "antd";
import {
  SecurityScanOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";

const { Title, Text, Paragraph } = Typography;

/**
 * Feature highlight item for the hero section
 */
interface FeatureItemProps {
  icon: ReactNode;
  title: string;
  description: string;
  delay?: string;
}

function FeatureItem({ icon, title, description, delay = "0s" }: FeatureItemProps) {
  return (
    <div
      className="feature-card animate-fade-in-up"
      style={{
        opacity: 0,
        animationDelay: delay,
        padding: "24px",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        minHeight: "160px",
      }}
    >
      <div
        style={{
          fontSize: "28px",
          color: "#00d4ff",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: "56px",
          height: "56px",
          background: "rgba(0, 212, 255, 0.1)",
          borderRadius: "12px",
        }}
      >
        {icon}
      </div>
      <div>
        <Title level={5} style={{ margin: 0, fontSize: "16px", fontWeight: 600 }}>
          {title}
        </Title>
        <Paragraph
          style={{
            margin: "8px 0 0",
            fontSize: "13px",
            color: "#9ca3af",
            lineHeight: "1.7",
          }}
        >
          {description}
        </Paragraph>
      </div>
    </div>
  );
}

/**
 * Hero section component - Landing page with value proposition and features
 */
export function HeroSection() {
  const features = [
    {
      icon: <SecurityScanOutlined />,
      title: "In-Memory Only",
      description: "Your document is processed entirely in RAM. No disk writes, no database storage.",
      delay: "0.1s",
    },
    {
      icon: <DatabaseOutlined />,
      title: "Session Auto-Cleanup",
      description: "All data is automatically purged after 30 minutes of inactivity. Zero traces.",
      delay: "0.2s",
    },
    {
      icon: <CheckCircleOutlined />,
      title: "Strict RAG",
      description: "Every answer is grounded in retrieved passages. No hallucinations, no fabrications.",
      delay: "0.3s",
    },
    {
      icon: <ThunderboltOutlined />,
      title: "Instant Setup",
      description: "No registration required. Upload, ask questions, get answers. Then it's all gone.",
      delay: "0.4s",
    },
  ];

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "60px 20px",
        background:
          "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0, 212, 255, 0.08), transparent), #050507",
      }}
    >
      {/* Background grid effect */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px)",
          backgroundSize: "50px 50px",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      <div style={{ position: "relative", zIndex: 1, maxWidth: "1200px", width: "100%" }}>
        {/* Header */}
        <div
          className="animate-fade-in-up"
          style={{
            opacity: 0,
            textAlign: "center",
            marginBottom: "60px",
          }}
        >
          <Space direction="vertical" size="large" style={{ width: "100%" }}>
            <div>
              <div className="badge" style={{ marginBottom: "20px" }}>
                <span className="status-dot ready" />
                Session-Based • In-Memory • Zero Persistence
              </div>
              <Title
                style={{
                  fontSize: "clamp(36px, 5vw, 64px)",
                  fontWeight: 700,
                  lineHeight: "1.1",
                  marginBottom: "20px",
                  background: "linear-gradient(135deg, #00d4ff 0%, #8b5cf6 50%, #3b82f6 100%)",
                  backgroundSize: "200% 200%",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                  animation: "gradientShift 4s ease infinite",
                }}
              >
                Privacy-First Document Q&A
              </Title>
              <Title
                level={2}
                style={{
                  fontSize: "clamp(18px, 2.5vw, 24px)",
                  fontWeight: 400,
                  color: "#9ca3af",
                  maxWidth: "700px",
                  margin: "0 auto",
                  lineHeight: "1.6",
                }}
              >
                Upload any document. Ask questions. Get answers with citations.
                <br />
                Everything disappears when you're done.
              </Title>
            </div>

            <div
              style={{
                display: "flex",
                gap: "16px",
                justifyContent: "center",
                flexWrap: "wrap",
              }}
            >
              <div className="badge">
                <span style={{ marginRight: "6px" }}>●</span>
                .txt .md .docx .epub .mobi
              </div>
              <div className="badge">
                <span style={{ marginRight: "6px" }}>●</span>
                No account required
              </div>
              <div className="badge">
                <span style={{ marginRight: "6px" }}>●</span>
                Open source
              </div>
            </div>
          </Space>
        </div>

        {/* Features Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: "20px",
            marginBottom: "60px",
          }}
        >
          {features.map((feature, index) => (
            <FeatureItem
              key={index}
              icon={feature.icon}
              title={feature.title}
              description={feature.description}
              delay={feature.delay}
            />
          ))}
        </div>

        {/* Privacy Notice */}
        <div
          className="animate-fade-in-up"
          style={{
            opacity: 0,
            animationDelay: "0.5s",
            textAlign: "center",
            padding: "20px",
            background: "rgba(13, 13, 18, 0.5)",
            border: "1px solid rgba(0, 212, 255, 0.1)",
            borderRadius: "12px",
            maxWidth: "600px",
            margin: "0 auto",
          }}
        >
          <Text style={{ color: "#6b7280", fontSize: "13px" }}>
            <SecurityScanOutlined style={{ marginRight: "8px", color: "#00d4ff" }} />
            Your document is processed in-memory and automatically deleted after 30 minutes of
            inactivity. No data is ever written to disk or stored in a database.
          </Text>
        </div>
      </div>
    </div>
  );
}
