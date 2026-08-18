"use client";

import { useEffect, useState } from "react";

type BannerState = {
  conditionKey: string;
  backgroundImagePath: string;
  instructionalText: string;
  textColorHex: string;
  spyDk: -1 | 0 | 1;
  fieldCoverage: "single_observed_D_k";
};

export default function MarketConditionBanner() {
  const [banner, setBanner] = useState<BannerState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/market-banner", { cache: "no-store" })
      .then(async (response) => {
        const data = await response.json() as BannerState & { error?: string; detail?: string };
        if (!response.ok) throw new Error(data.detail ?? data.error ?? `HTTP ${response.status}`);
        return data;
      })
      .then((data: BannerState) => {
        setBanner(data);
        setError(null);
      })
      .catch((reason: unknown) => {
        setError(reason instanceof Error ? reason.message : "Market condition feed failed");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return null;
  if (error || !banner) {
    return (
      <section className="tfe-panel" role="status" style={{ marginBottom: 28, padding: "12px 16px", color: "#a16207" }}>
        Market condition unavailable. No replacement D_k state was inferred. {error ?? "No verified banner payload was received."}
      </section>
    );
  }

  const hasImage = Boolean(banner.backgroundImagePath);

  // Split "HEADING; subtitle text." into two lines
  const semIdx = banner.instructionalText.indexOf(";");
  const heading = semIdx >= 0
    ? banner.instructionalText.slice(0, semIdx).trim()
    : banner.instructionalText.trim();
  const subtitle = semIdx >= 0
    ? banner.instructionalText.slice(semIdx + 1).trim()
    : "";

  return (
    <section
      aria-label="Market condition banner"
      style={{
        position: "relative",
        width: "100%",
        minHeight: "clamp(105px, 16.5vw, 210px)",
        borderRadius: 10,
        overflow: "hidden",
        marginBottom: 28,
        display: "flex",
        alignItems: "center",
        justifyContent: "flex-end",
        background: hasImage ? "transparent" : "#1a1a2e",
        ...(hasImage
          ? {
              backgroundImage: `url(${banner.backgroundImagePath})`,
              backgroundSize: "cover",
              backgroundPosition: "center",
            }
          : {}),
      }}
    >
      {/* Gradient overlay — right-side dark for legibility */}
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          inset: 0,
          background: "linear-gradient(to left, rgba(0,0,0,0.72) 0%, rgba(0,0,0,0.38) 55%, rgba(0,0,0,0.10) 100%)",
          zIndex: 1,
        }}
      />

      {/* Text block — right-aligned */}
      <div
        style={{
          position: "relative",
          zIndex: 2,
          textAlign: "right",
          padding: "clamp(14px, 2.5vw, 28px) clamp(20px, 5vw, 64px)",
          maxWidth: 560,
        }}
      >
        {heading ? (
          <>
            <p
              style={{
                margin: 0,
                color: banner.textColorHex || "#ffffff",
                fontSize: "clamp(1rem, 2.6vw, 1.6rem)",
                fontWeight: 800,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                lineHeight: 1.2,
                textShadow: "0 2px 10px rgba(0,0,0,0.8), 0 1px 3px rgba(0,0,0,0.9)",
              }}
            >
              {heading}
            </p>
            {subtitle && (
              <p
                style={{
                  margin: "6px 0 0",
                  color: banner.textColorHex || "#ffffff",
                  fontSize: "clamp(0.72rem, 1.5vw, 0.95rem)",
                  fontWeight: 400,
                  letterSpacing: "0.01em",
                  lineHeight: 1.4,
                  textShadow: "0 1px 6px rgba(0,0,0,0.8)",
                  opacity: 0.92,
                }}
              >
                {subtitle.charAt(0).toUpperCase() + subtitle.slice(1).toLowerCase()}
              </p>
            )}
          </>
        ) : (
          <p
            style={{
              margin: 0,
              color: "rgba(255,255,255,0.5)",
              fontSize: "clamp(0.75rem, 2vw, 0.95rem)",
              fontStyle: "italic",
            }}
          >
            No banner message configured — set it in Admin → Market Banner CMS.
          </p>
        )}
      </div>
    </section>
  );
}
