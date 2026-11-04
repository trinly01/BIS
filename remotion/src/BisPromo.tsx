import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

// BIS brand tokens — barangay blue on near-black (portal theme)
const C = {
  bg: "#0c1424",
  card: "#16233f",
  primary: "#7cc4ff",
  muted: "#9db4d8",
  accent: "#5ce6a0",
};

const FEATURES = [
  "Resident & Household Registry",
  "Certificates with QR Verification",
  "Blotter & Katarungang Pambarangay",
  "Resident Portal + Tracking",
  "Multi-Barangay Dashboards",
];

const Title: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14 } });
  return (
    <div style={{ transform: `translateY(${interpolate(s, [0, 1], [60, 0])}px)`, opacity: s }}>
      <div style={{ fontSize: 96, fontWeight: 900, color: "#fff", letterSpacing: -2 }}>
        <span style={{ color: C.primary }}>BIS</span>
        <span style={{ color: C.muted, fontSize: 40, fontWeight: 600, marginLeft: 24 }}>
          Barangay Information System
        </span>
      </div>
      <div style={{ color: C.muted, fontSize: 32, marginTop: 16 }}>
        San Fabian, Pangasinan — every barangay, one platform
      </div>
    </div>
  );
};

export const BisPromo: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background: C.bg, fontFamily: "Segoe UI, system-ui, sans-serif", padding: 96, justifyContent: "center" }}>
      <Title />
      <div style={{ display: "flex", flexWrap: "wrap", gap: 24, marginTop: 72 }}>
        {FEATURES.map((f, i) => {
          const s = spring({ frame: frame - 40 - i * 12, fps, config: { damping: 16 } });
          return (
            <div
              key={f}
              style={{
                background: C.card,
                border: `1px solid ${C.primary}33`,
                borderRadius: 16,
                padding: "28px 36px",
                fontSize: 28,
                fontWeight: 600,
                color: "#e8f0ff",
                opacity: s,
                transform: `translateY(${interpolate(s, [0, 1], [40, 0])}px)`,
              }}
            >
              <span style={{ color: C.accent, marginRight: 12 }}>●</span>
              {f}
            </div>
          );
        })}
      </div>
      <div
        style={{
          position: "absolute",
          bottom: 64,
          left: 96,
          color: C.muted,
          fontSize: 22,
          opacity: interpolate(frame, [240, 270], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        }}
      >
        trinly01.github.io/BIS
      </div>
    </AbsoluteFill>
  );
};
