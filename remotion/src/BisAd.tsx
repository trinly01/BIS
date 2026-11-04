import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig, Sequence } from "remotion";

const C = {
  bg: "#0c1424", card: "#16233f", primary: "#7cc4ff",
  muted: "#9db4d8", accent: "#5ce6a0", warn: "#ffd166",
};

const FADE = 12;
const at = (f: number, s: number, e: number) =>
  interpolate(f, [s, s + FADE, e - FADE, e], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

const Scene: React.FC<{ children: React.ReactNode; center?: boolean }> = ({ children, center }) => (
  <AbsoluteFill style={{ background: C.bg, fontFamily: "Segoe UI, system-ui, sans-serif", padding: 72, justifyContent: "center", alignItems: center ? "center" : "flex-start" }}>
    {children}
  </AbsoluteFill>
);

const Line: React.FC<{ t: string; size?: number; color?: string; delay?: number; center?: boolean }> = ({ t, size = 52, color = "#fff", delay = 0, center }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame: frame - delay, fps, config: { damping: 15 } });
  return (
    <div style={{ fontSize: size, fontWeight: 800, color, lineHeight: 1.25, textAlign: center ? "center" : "left", opacity: s, transform: `translateY(${(1 - s) * 30}px)` }}>
      {t}
    </div>
  );
};

export const BisAd: React.FC<{ vertical?: boolean }> = ({ vertical }) => {
  return (
    <AbsoluteFill>
      {/* 0-70: the pain */}
      <Sequence durationInFrames={70}>
        <Scene center>
          <Line t="Pila sa barangay hall?" size={vertical ? 64 : 76} center delay={4} />
          <Line t="Balik-balik para sa clearance?" size={vertical ? 44 : 52} color={C.muted} center delay={18} />
          <Line t="Not anymore." size={vertical ? 56 : 64} color={C.warn} center delay={38} />
        </Scene>
      </Sequence>
      {/* 70-130: what is BIS */}
      <Sequence from={70} durationInFrames={60}>
        <Scene center>
          <Line t="BIS" size={vertical ? 110 : 120} color={C.primary} center delay={2} />
          <Line t="Barangay Information System" size={vertical ? 40 : 46} center delay={10} />
          <Line t="Government services, streamlined." size={vertical ? 34 : 38} color={C.muted} center delay={20} />
        </Scene>
      </Sequence>
      {/* 130-250: 3 easy steps */}
      {[
        { n: "1", t: "Request online", d: "Fill the form at trinly01.github.io/BIS — pick your barangay, doc type, done in a minute." },
        { n: "2", t: "Track by mobile", d: "Check status anytime with your request number + mobile. No line, no guessing." },
        { n: "3", t: "Claim & verify", d: "Get your printed certificate — QR code proves it's authentic, anywhere." },
      ].map((s, i) => (
        <Sequence key={s.n} from={130 + i * 40} durationInFrames={40}>
          <Scene>
            <div style={{ fontSize: 90, fontWeight: 900, color: C.accent, opacity: at(0, 0, 30) }}>{s.n}</div>
            <Line t={s.t} size={vertical ? 58 : 66} delay={6} />
            <Line t={s.d} size={vertical ? 30 : 34} color={C.muted} delay={14} />
          </Scene>
        </Sequence>
      ))}
      {/* 250-300: closer */}
      <Sequence from={250} durationInFrames={50}>
        <Scene center>
          <Line t="Your barangay, digital." size={vertical ? 52 : 60} center delay={4} />
          <Line t="trinly01.github.io/BIS" size={vertical ? 40 : 44} color={C.primary} center delay={16} />
          <Line t="San Fabian, Pangasinan" size={28} color={C.muted} center delay={26} />
        </Scene>
      </Sequence>
    </AbsoluteFill>
  );
};
