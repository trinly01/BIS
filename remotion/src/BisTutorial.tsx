import { AbsoluteFill, Audio, interpolate, staticFile, useCurrentFrame, Sequence } from "remotion";

// BIS portal theme — matches portal/src/index.css
const C = { bg: "#0c1424", card: "#16233f", primary: "#7cc4ff", muted: "#9db4d8", accent: "#5ce6a0", warn: "#ffd166", border: "#24365c", input: "#1a2a4a" };
const FONT = "Segoe UI, system-ui, sans-serif";

const fade = (f: number, s: number, e: number, d = 10) =>
  interpolate(f, [s, s + d, e - d, e], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

// cute cursor — travels along waypoints, pulses a ring on click frames
const Cursor: React.FC<{ pts: [number, number, number][]; clicks?: number[] }> = ({ pts, clicks = [] }) => {
  const f = useCurrentFrame();
  const flat = pts.flatMap((p, i) => (i === 0 ? [p[0], p[1]] : [p[0], p[1]]));
  const times = pts.map((p) => p[2]);
  const x = interpolate(f, times, pts.map((p) => p[0]), { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const y = interpolate(f, times, pts.map((p) => p[1]), { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const clickT = clicks.find((c) => f >= c && f < c + 14);
  const ring = clickT !== undefined ? interpolate(f, [clickT, clickT + 14], [0, 1]) : 0;
  return (
    <div style={{ position: "absolute", left: x, top: y, zIndex: 50 }}>
      {clickT !== undefined && (
        <div style={{ position: "absolute", left: -30, top: -30, width: 60, height: 60, borderRadius: 30, border: `4px solid ${C.accent}`, opacity: 1 - ring, transform: `scale(${0.4 + ring * 1.4})` }} />
      )}
      <div style={{ position: "absolute", width: 22, height: 22, borderRadius: 11, background: "#fff", boxShadow: "0 2px 10px rgba(0,0,0,.6)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: 8, height: 8, borderRadius: 4, background: "#334155" }} />
      </div>
    </div>
  );
};

const Card: React.FC<{ w?: number; children: React.ReactNode; style?: any }> = ({ w = 620, children, style }) => (
  <div style={{ width: w, background: C.card, border: `2px solid ${C.border}`, borderRadius: 18, padding: 28, boxShadow: "0 8px 30px rgba(0,0,0,.4)", ...style }}>{children}</div>
);
const Badge: React.FC<{ children: React.ReactNode; color?: string }> = ({ children, color = C.muted }) => (
  <span style={{ background: `${color}22`, color, border: `1px solid ${color}55`, borderRadius: 8, padding: "4px 12px", fontSize: 20, fontWeight: 700 }}>{children}</span>
);
const Input: React.FC<{ v?: string; ph: string; hl?: boolean }> = ({ v, ph, hl }) => (
  <div style={{ height: 52, background: C.bg, border: `2px solid ${hl ? C.primary : C.input}`, borderRadius: 10, padding: "0 16px", display: "flex", alignItems: "center", fontSize: 22, color: v ? "#fff" : C.muted }}>
    {v ?? ph}{hl && <span style={{ marginLeft: 2, color: C.primary, fontWeight: 900 }}>|</span>}
  </div>
);
const Btn: React.FC<{ children: React.ReactNode; press?: boolean }> = ({ children, press }) => (
  <div style={{ height: 56, background: press ? "#5fa8e0" : C.primary, color: "#0c1424", borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, fontWeight: 800, transform: press ? "scale(.96)" : "none" }}>{children}</div>
);
const Scene: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ background: C.bg, fontFamily: FONT, display: "flex", alignItems: "center", justifyContent: "center" }}>{children}</AbsoluteFill>
);
const Caption: React.FC<{ t: string }> = ({ t }) => {
  const f = useCurrentFrame();
  return <div style={{ position: "absolute", bottom: 48, left: 0, right: 0, textAlign: "center", fontSize: 30, fontWeight: 700, color: C.muted, opacity: fade(f, 6, 70) }}>{t}</div>;
};

export const BisTutorial: React.FC = () => {
  return (
    <AbsoluteFill>
      <Audio src={staticFile("sfx/music.wav")} volume={0.12} />
      {/* 0 — intro: what is BIS (0-200) */}
      <Sequence from={0} durationInFrames={200}>
        <Scene>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 130, fontWeight: 900, color: C.primary, opacity: fade(useCurrentFrame(), 0, 50) }}>BIS</div>
            <div style={{ fontSize: 44, fontWeight: 800, color: "#fff", opacity: fade(useCurrentFrame(), 10, 52) }}>Barangay Information System</div>
            <div style={{ fontSize: 30, color: C.muted, marginTop: 12, opacity: fade(useCurrentFrame(), 20, 55) }}>Government services, streamlined.</div>
          </div>
          <Audio src={staticFile("vo/s2_intro.mp3")} />
        </Scene>
      </Sequence>
      {/* 1 — portal home, click Request (60-140) */}
      <Sequence from={200} durationInFrames={210}>
        <Scene>
          <div style={{ opacity: 1 }}>
            <div style={{ textAlign: "center", fontSize: 44, fontWeight: 900, color: "#fff", marginBottom: 8 }}><span style={{ color: C.primary }}>BIS</span> Portal</div>
            <div style={{ textAlign: "center", fontSize: 20, color: C.muted, marginBottom: 28 }}>Municipality of San Fabian, Pangasinan</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {["Request a document", "Track a request", "Benefits & programs"].map((t, i) => (
                <Card key={t} w={560} style={{ padding: 22, border: i === 0 ? `2px solid ${C.primary}` : `2px solid ${C.border}` }}>
                  <div style={{ fontSize: 26, fontWeight: 700, color: "#fff" }}>{t}</div>
                  <div style={{ fontSize: 18, color: C.muted, marginTop: 4 }}>{i === 0 ? "Clearance, indigency, residency & more" : i === 1 ? "Request number + mobile" : "Aid you've received"}</div>
                </Card>
              ))}
            </div>
          </div>
          <Cursor pts={[[1100, 700, 0], [1100, 700, 18], [640, 400, 46], [640, 400, 70]]} clicks={[52]} />
          <Audio src={staticFile("vo/t1_home.mp3")} />
          {useCurrentFrame() >= 52 && <Audio src={staticFile("sfx/click.wav")} />}
          <Caption t="Step 1 — open the portal, tap Request a Document" />
        </Scene>
      </Sequence>
      {/* 2 — request form fills itself (140-230) */}
      <Sequence from={410} durationInFrames={165}>
        <Scene>
          <Card w={640}>
            <div style={{ fontSize: 30, fontWeight: 800, color: "#fff", marginBottom: 18 }}>Request a document</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <Typed f0={10} text="Poblacion, San Fabian" ph="Select your barangay" />
              <Typed f0={24} text="Barangay Clearance — ₱50 · ~3 days" ph="Select document type" />
              <Typed f0={38} text="Maria Santos" ph="Full name" />
              <Typed f0={50} text="0917 123 4567" ph="Mobile number" />
              <div style={{ marginTop: 4, transform: `scale(${useCurrentFrame() >= 66 ? 0.97 : 1})` }}><Btn press={useCurrentFrame() >= 66}>Submit request</Btn></div>
            </div>
          </Card>
          <Cursor pts={[[900, 300, 0], [520, 250, 14], [520, 470, 36], [520, 470, 50], [540, 640, 62], [540, 640, 80]]} clicks={[18, 40, 66]} />
          <Audio src={staticFile("vo/t2_form.mp3")} />
          {useCurrentFrame() >= 66 && <Audio src={staticFile("sfx/click.wav")} />}
          <Caption t="Step 2 — pick barangay + document, name and mobile" />
        </Scene>
      </Sequence>
      {/* 3 — success card (230-300) */}
      <Sequence from={575} durationInFrames={180}>
        <Scene>
          <Card w={560} style={{ textAlign: "center" }}>
            <div style={{ fontSize: 64, opacity: fade(useCurrentFrame(), 4, 60) }}>✅</div>
            <div style={{ fontSize: 30, fontWeight: 800, color: "#fff", margin: "10px 0" }}>Request received</div>
            <div style={{ fontSize: 42, fontWeight: 900, color: C.primary, fontFamily: "monospace", margin: "10px 0" }}>DOC-POB-2026-0007</div>
            <div style={{ fontSize: 20, color: C.muted }}>Barangay Clearance · Fee ₱50 · ETA Nov 7</div>
          </Card>
          <Audio src={staticFile("vo/t3_submit.mp3")} />
          <Audio src={staticFile("sfx/chime.wav")} />
          <Caption t="Step 3 — instant request number + release date" />
        </Scene>
      </Sequence>
      {/* 4 — track timeline (300-380) */}
      <Sequence from={755} durationInFrames={195}>
        <Scene>
          <Card w={560}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
              <div style={{ fontSize: 26, fontWeight: 800, color: "#fff" }}>Barangay Clearance</div>
              <Badge color={C.warn}>For Signature</Badge>
            </div>
            {["Received", "Requirements Check", "For Payment", "For Signature", "Released"].map((s, i) => {
              const f = useCurrentFrame();
              const done = i < 3 || (i === 3 && f > 34);
              return (
                <div key={s} style={{ display: "flex", gap: 14, alignItems: "flex-start", opacity: i <= 3 ? 1 : 0.4 }}>
                  <div style={{ width: 22, display: "flex", flexDirection: "column", alignItems: "center" }}>
                    <div style={{ width: 16, height: 16, borderRadius: 8, background: done ? C.accent : i === 3 ? C.warn : C.border }} />
                    {i < 4 && <div style={{ width: 2, height: 26, background: C.border }} />}
                  </div>
                  <div style={{ fontSize: 22, color: i <= 3 ? "#fff" : C.muted }}>{s}</div>
                </div>
              );
            })}
          </Card>
          <Audio src={staticFile("vo/t4_track.mp3")} />
          <Caption t="Step 4 — track with request number + mobile" />
        </Scene>
      </Sequence>
      {/* 5 — staff side (380-460) */}
      <Sequence from={950} durationInFrames={200}>
        <Scene>
          <div style={{ width: 720 }}>
            <div style={{ fontSize: 26, color: C.muted, marginBottom: 14 }}>Staff Dashboard · Document Requests</div>
            <Card w={720} style={{ padding: 0 }}>
              {[["DOC-POB-2026-0007", "Maria Santos", "received"], ["DOC-POB-2026-0006", "Juan Dela Cruz", "released"], ["DOC-BIN-2026-0002", "Ana Aquino", "for_payment"]].map(([no, n, st], i) => (
                <div key={no} style={{ display: "flex", alignItems: "center", gap: 16, padding: "16px 24px", borderBottom: i < 2 ? `1px solid ${C.border}` : "none", background: i === 0 ? `${C.primary}11` : "transparent" }}>
                  <span style={{ fontFamily: "monospace", fontSize: 20, color: C.primary }}>{no}</span>
                  <span style={{ fontSize: 20, color: "#fff", flex: 1 }}>{n}</span>
                  <Badge color={st === "released" ? C.accent : st === "received" ? C.primary : C.warn}>{st}</Badge>
                </div>
              ))}
            </Card>
            <div style={{ display: "flex", gap: 12, marginTop: 18 }}>
              {["Review", "Collect Payment", "Print", "Release"].map((a, i) => (
                <Badge key={a} color={i <= useCurrentFrame() / 14 ? C.accent : C.muted}>{a}</Badge>
              ))}
            </div>
          </div>
          <Audio src={staticFile("vo/t5_admin.mp3")} />
          <Caption t="Staff side — review, collect, print, release" />
        </Scene>
      </Sequence>
      {/* 6 — QR verify (460-540) */}
      <Sequence from={1150} durationInFrames={215}>
        <Scene>
          <Card w={560} style={{ textAlign: "center" }}>
            <div style={{ width: 120, height: 120, margin: "0 auto 16px", background: "#fff", borderRadius: 12, display: "grid", placeItems: "center", fontSize: 60 }}>▦</div>
            <div style={{ fontSize: 56, opacity: fade(useCurrentFrame(), 8, 70) }}>🛡️</div>
            <div style={{ fontSize: 30, fontWeight: 800, color: C.accent }}>Authentic document</div>
            <div style={{ fontSize: 20, color: C.muted, marginTop: 8 }}>Barangay Clearance · issued to Maria S. · valid until Feb 2027</div>
          </Card>
          <Audio src={staticFile("vo/t6_verify.mp3")} />
          {useCurrentFrame() >= 8 && <Audio src={staticFile("sfx/chime.wav")} />}
          <Caption t="Every certificate has a QR — scan to verify" />
        </Scene>
      </Sequence>
      {/* 7 — feature grid (1365-1560) */}
      <Sequence from={1365} durationInFrames={195}>
        <Scene>
          <div style={{ textAlign: "center", fontSize: 34, fontWeight: 800, color: "#fff", marginBottom: 26, opacity: fade(useCurrentFrame(), 4, 185) }}>And that's not all</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 18, justifyContent: "center", maxWidth: 900 }}>
            {["Resident & Household Registry", "Blotter & KP Mediation", "Business Permits", "Announcements", "Barangay Assets", "Benefits Tracking"].map((t, i) => {
              const f = useCurrentFrame();
              return (
                <div key={t} style={{ background: C.card, border: `1.5px solid ${C.primary}44`, borderRadius: 14, padding: "20px 28px", fontSize: 24, fontWeight: 600, color: "#e8f0ff", opacity: fade(f, 6 + i * 6, 190) }}>
                  <span style={{ color: C.accent, marginRight: 10 }}>●</span>{t}
                </div>
              );
            })}
          </div>
          <Audio src={staticFile("vo/t7_features.mp3")} />
          <Caption t="Everything your barangay needs, one system" />
        </Scene>
      </Sequence>
      {/* 8 — analytics mock (1560-1755) */}
      <Sequence from={1560} durationInFrames={195}>
        <Scene>
          <div style={{ width: 860 }}>
            <div style={{ fontSize: 28, color: C.muted, marginBottom: 16, opacity: fade(useCurrentFrame(), 4, 185) }}>For admins — live dashboards</div>
            <div style={{ display: "flex", gap: 16, marginBottom: 18 }}>
              {[["Residents", "1,248"], ["Households", "412"], ["Certs Issued", "96"]].map(([l, v], i) => {
                const f = useCurrentFrame();
                return (
                  <Card key={l} w={270} style={{ padding: 18, opacity: fade(f, 6 + i * 5, 188) }}>
                    <div style={{ fontSize: 17, color: C.muted }}>{l}</div>
                    <div style={{ fontSize: 38, fontWeight: 900, color: C.primary }}>{v}</div>
                  </Card>
                );
              })}
            </div>
            <div style={{ display: "flex", gap: 18 }}>
              <Card w={480} style={{ padding: 18 }}>
                <div style={{ fontSize: 16, color: C.muted, marginBottom: 10 }}>Issuance trend</div>
                <div style={{ display: "flex", alignItems: "flex-end", gap: 10, height: 110 }}>
                  {[40, 55, 48, 70, 62, 85, 78, 95].map((h, i) => {
                    const f = useCurrentFrame();
                    return <div key={i} style={{ flex: 1, background: `linear-gradient(180deg, ${C.primary}, ${C.primary}55)`, borderRadius: 4, height: h * fade(f, 8 + i * 3, 185) }} />;
                  })}
                </div>
              </Card>
              <Card w={360} style={{ padding: 18 }}>
                <div style={{ fontSize: 16, color: C.muted, marginBottom: 10 }}>By barangay</div>
                <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: 110 }}>
                  <div style={{ width: 100, height: 100, borderRadius: 50, background: `conic-gradient(${C.primary} 0 55%, ${C.accent} 55% 80%, ${C.warn} 80% 100%)`, opacity: fade(useCurrentFrame(), 14, 185) }}>
                    <div style={{ width: 56, height: 56, borderRadius: 28, background: C.card, margin: 22 }} />
                  </div>
                </div>
              </Card>
            </div>
          </div>
          <Audio src={staticFile("vo/t8_analytics.mp3")} />
          <Caption t="Live dashboards — per barangay or municipality-wide" />
        </Scene>
      </Sequence>
      {/* 9 — closer (1755-1915) */}
      <Sequence from={1755} durationInFrames={160}>
        <Scene>
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 60, fontWeight: 900, color: "#fff", opacity: fade(useCurrentFrame(), 4, 150) }}>Your barangay, digital.</div>
            <div style={{ fontSize: 36, fontWeight: 800, color: C.primary, marginTop: 14, opacity: fade(useCurrentFrame(), 20, 152) }}>trinly01.github.io/BIS</div>
            <div style={{ fontSize: 24, color: C.muted, marginTop: 14, opacity: fade(useCurrentFrame(), 34, 155) }}>San Fabian, Pangasinan</div>
          </div>
          <Audio src={staticFile("vo/s6_outro.mp3")} />
        </Scene>
      </Sequence>
    </AbsoluteFill>
  );
};

// little self-typing input
const Typed: React.FC<{ f0: number; text: string; ph: string }> = ({ f0, text, ph }) => {
  const f = useCurrentFrame();
  const n = Math.max(0, Math.min(text.length, Math.floor((f - f0) / 2)));
  const typing = n < text.length && f >= f0;
  return <Input v={f < f0 ? undefined : text.slice(0, n)} ph={ph} hl={typing} />;
};
