import SiteFrame from "@/components/SiteFrame";
import { getUiConfig } from "@/lib/ui-config";

const palette = [
  { name: "Forest Base", hex: "#0E1E18" },
  { name: "Forest Mid", hex: "#1B352B" },
  { name: "Sage Accent", hex: "#7FBF9D" },
  { name: "Muted Gold", hex: "#CDBE8A" },
  { name: "Glass Surface", hex: "rgba(241, 250, 245, 0.68)" },
  { name: "Primary Text", hex: "#173328" },
  { name: "Secondary Text", hex: "#4E6A5D" },
];

export default async function ThemePreviewPage() {
  const config = await getUiConfig();

  return (
    <SiteFrame pageBackgroundImage={config.backgroundImages.home}>
      <section
        style={{
          width: "min(1680px, calc(100vw - 20px))",
          margin: "0 auto",
          display: "grid",
          gap: 12,
        }}
      >
        <section
          style={{
            borderRadius: 16,
            border: "1px solid rgba(127,191,157,0.4)",
            background:
              "linear-gradient(132deg, rgba(14,30,24,0.88) 0%, rgba(27,53,43,0.82) 50%, rgba(23,51,40,0.78) 100%)",
            boxShadow: "0 18px 42px rgba(8,18,14,0.35)",
            padding: "20px 22px",
            color: "#e9f5ef",
            overflow: "hidden",
            position: "relative",
          }}
        >
          <div
            aria-hidden="true"
            style={{
              position: "absolute",
              width: 360,
              height: 360,
              right: -80,
              top: -120,
              borderRadius: 999,
              background: "radial-gradient(circle, rgba(127,191,157,0.28) 0%, rgba(127,191,157,0) 70%)",
            }}
          />

          <p style={{ margin: 0, textTransform: "uppercase", letterSpacing: 1.1, fontSize: "0.74rem", color: "#c9e4d6" }}>
            Sage Glass Theme Preview
          </p>
          <h1 style={{ margin: "8px 0 0", fontSize: "2.4rem", lineHeight: 1.02 }}>Calm, Premium, Research-First</h1>
          <p style={{ margin: "12px 0 0", maxWidth: "62ch", color: "#d3e8dc", fontSize: "0.96rem" }}>
            This preview shows the proposed calm-tone direction before any full implementation. Motion style should be smooth and slow,
            with understated depth instead of bright or aggressive effects.
          </p>

          <div style={{ marginTop: 14, display: "flex", gap: 10, flexWrap: "wrap" }}>
            <button
              type="button"
              style={{
                minHeight: 36,
                padding: "7px 12px",
                borderRadius: 10,
                border: "1px solid #5ca17e",
                background: "linear-gradient(180deg, #92cfad 0%, #78ba99 100%)",
                color: "#163126",
                fontWeight: 700,
              }}
            >
              Primary Action
            </button>
            <button
              type="button"
              style={{
                minHeight: 36,
                padding: "7px 12px",
                borderRadius: 10,
                border: "1px solid rgba(205,190,138,0.58)",
                background: "rgba(14,30,24,0.52)",
                color: "#e6dbc0",
                fontWeight: 700,
              }}
            >
              Secondary Action
            </button>
          </div>
        </section>

        <section
          style={{
            borderRadius: 14,
            border: "1px solid rgba(23,58,44,0.2)",
            background: "rgba(241, 250, 245, 0.68)",
            boxShadow: "0 12px 28px rgba(18,40,32,0.16)",
            backdropFilter: "blur(4px)",
            padding: 12,
          }}
        >
          <h2 style={{ margin: 0, fontSize: "1.02rem", color: "#173328" }}>Palette</h2>

          <div
            style={{
              marginTop: 10,
              display: "grid",
              gap: 8,
              gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
            }}
          >
            {palette.map((tone) => (
              <article
                key={tone.name}
                style={{
                  display: "grid",
                  gridTemplateColumns: "56px 1fr",
                  gap: 10,
                  alignItems: "center",
                  border: "1px solid rgba(23,58,44,0.14)",
                  borderRadius: 10,
                  background: "rgba(248,253,249,0.7)",
                  padding: 8,
                }}
              >
                <div
                  style={{
                    width: 56,
                    height: 34,
                    borderRadius: 8,
                    border: "1px solid rgba(23,58,44,0.22)",
                    background: tone.hex,
                  }}
                />
                <div>
                  <div style={{ fontWeight: 700, color: "#1f4d3a", fontSize: "0.82rem" }}>{tone.name}</div>
                  <div style={{ color: "#4E6A5D", fontSize: "0.77rem" }}>{tone.hex}</div>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section
          style={{
            borderRadius: 14,
            border: "1px solid rgba(23,58,44,0.2)",
            background: "rgba(241, 250, 245, 0.68)",
            boxShadow: "0 12px 28px rgba(18,40,32,0.16)",
            backdropFilter: "blur(4px)",
            padding: 12,
          }}
        >
          <h2 style={{ margin: 0, fontSize: "1.02rem", color: "#173328" }}>Interaction Tone</h2>
          <ul style={{ margin: "8px 0 0", color: "#4E6A5D", fontSize: "0.82rem", lineHeight: 1.45, paddingLeft: 18 }}>
            <li>Transitions should run around 500-700ms with gentle easing.</li>
            <li>Depth should come from glass blur and soft shadows, not loud color flashes.</li>
            <li>Accent gold should only appear as a subtle highlight for key labels.</li>
          </ul>
        </section>
      </section>
    </SiteFrame>
  );
}
