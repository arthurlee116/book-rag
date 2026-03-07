import { ReactNode } from "react";
import { Typography } from "antd";
import {
  SecurityScanOutlined,
  DatabaseOutlined,
  ThunderboltOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import { themeTokens } from "@/theme";

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
        padding: "28px 24px",
        display: "flex",
        flexDirection: "column",
        gap: "14px",
        minHeight: "160px",
      }}
    >
      <div
        style={{
          fontSize: "26px",
          color: themeTokens.accentPrimary,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: "52px",
          height: "52px",
          background: "rgba(212, 145, 92, 0.08)",
          borderRadius: "14px",
          border: "1px solid rgba(212, 145, 92, 0.12)",
        }}
      >
        {icon}
      </div>
      <div>
        <Title level={5} style={{ margin: 0, fontSize: "16px", fontWeight: 600, fontFamily: '"Inter", sans-serif' }}>
          {title}
        </Title>
        <Paragraph
          style={{
            margin: "8px 0 0",
            fontSize: "13.5px",
            color: themeTokens.textSecondary,
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
      delay: "0.15s",
    },
    {
      icon: <DatabaseOutlined />,
      title: "Session Auto-Cleanup",
      description: "All data is automatically purged after 30 minutes of inactivity. Zero traces.",
      delay: "0.25s",
    },
    {
      icon: <CheckCircleOutlined />,
      title: "Strict RAG",
      description: "Every answer is grounded in retrieved passages. No hallucinations, no fabrications.",
      delay: "0.35s",
    },
    {
      icon: <ThunderboltOutlined />,
      title: "Instant Setup",
      description: "No registration required. Upload, ask questions, get answers. Then it's all gone.",
      delay: "0.45s",
    },
  ];

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "80px 24px 60px",
        background: themeTokens.bgLayout,
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Warm ambient glow */}
      <div
        style={{
          position: "absolute",
          top: "-30%",
          left: "50%",
          transform: "translateX(-50%)",
          width: "120%",
          height: "60%",
          background:
            "radial-gradient(ellipse 60% 70% at 50% 30%, rgba(212, 145, 92, 0.06), transparent 70%)",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      {/* Subtle dot pattern instead of grid */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          backgroundImage:
            "radial-gradient(circle, rgba(212, 145, 92, 0.04) 1px, transparent 1px)",
          backgroundSize: "32px 32px",
          pointerEvents: "none",
          zIndex: 0,
        }}
      />

      <div style={{ position: "relative", zIndex: 1, maxWidth: "1100px", width: "100%" }}>
        {/* Header Section */}
        <div
          className="animate-fade-in-up"
          style={{
            opacity: 0,
            textAlign: "center",
            marginBottom: "64px",
          }}
        >
          {/* Status Badge */}
          <div style={{ marginBottom: "28px" }}>
            <div className="badge">
              <span className="status-dot ready" style={{ width: "6px", height: "6px" }} />
              Session-Based · In-Memory · Zero Persistence
            </div>
          </div>

          {/* Main Headline */}
          <Title
            style={{
              fontSize: "clamp(38px, 5vw, 62px)",
              fontWeight: 700,
              lineHeight: "1.08",
              marginBottom: "24px",
              color: themeTokens.textPrimary,
              letterSpacing: "-0.03em",
            }}
          >
            Privacy-First
            <br />
            <span
              style={{
                background: "linear-gradient(135deg, #D4915C 0%, #E8A96B 50%, #D4915C 100%)",
                backgroundSize: "200% 200%",
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
                animation: "gradientShift 4s ease infinite",
              }}
            >
              Document Q&A
            </span>
          </Title>

          {/* Sub headline */}
          <p
            style={{
              fontSize: "clamp(16px, 2.2vw, 20px)",
              fontWeight: 400,
              color: themeTokens.textSecondary,
              maxWidth: "580px",
              margin: "0 auto",
              lineHeight: "1.7",
              fontFamily: '"Inter", sans-serif',
            }}
          >
            Upload any document. Ask questions. Get answers with citations.
            <br />
            <span style={{ color: themeTokens.textTertiary }}>
              Everything disappears when you're done.
            </span>
          </p>

          {/* Capability badges */}
          <div
            style={{
              display: "flex",
              gap: "10px",
              justifyContent: "center",
              flexWrap: "wrap",
              marginTop: "32px",
            }}
          >
            <div className="badge" style={{ fontSize: "11px", padding: "5px 12px" }}>
              .txt .md .docx .epub .mobi
            </div>
            <div className="badge" style={{ fontSize: "11px", padding: "5px 12px" }}>
              No account required
            </div>
            <div className="badge" style={{ fontSize: "11px", padding: "5px 12px" }}>
              Open source
            </div>
          </div>
        </div>

        {/* Features Grid */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
            gap: "16px",
            marginBottom: "48px",
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
            animationDelay: "0.55s",
            textAlign: "center",
            padding: "18px 24px",
            background: "rgba(26, 25, 24, 0.6)",
            border: "1px solid rgba(212, 145, 92, 0.06)",
            borderRadius: "14px",
            maxWidth: "560px",
            margin: "0 auto",
          }}
        >
          <Text style={{ color: themeTokens.textTertiary, fontSize: "13px", lineHeight: "1.7" }}>
            <SecurityScanOutlined style={{ marginRight: "8px", color: themeTokens.accentPrimary }} />
            Your document is processed in-memory and automatically deleted after 30 minutes of
            inactivity. No data is ever written to disk or stored in a database.
          </Text>
        </div>
      </div>
    </div>
  );
}
