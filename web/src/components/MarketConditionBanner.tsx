"use client";

import { useEffect, useState } from "react";

type BannerState = {
  conditionKey: string;
  backgroundImagePath: string;
  instructionalText: string;
  textColorHex: string;
  spyDk: number | null;
  isMarketLocked: boolean;
};

const DK_LABEL: Record<string, string> = {
  D_k_plus_1:  "D_k = +1  ·  EXPANSION",
  D_k_0:       "D_k = 0   ·  NEUTRAL",
  D_k_minus_1: "D_k = −1  ·  CONTRACTION",
};

const DK_ACCENT: Record<string, string> = {
  D_k_plus_1:  "rgba(22, 163, 74, 0.85)",   // green
  D_k_0:       "rgba(161, 98, 7, 0.85)",    // amber
  D_k_minus_1: "rgba(185, 28, 28, 0.85)",   // red
};

export default function MarketConditionBanner() {
  const [banner, setBanner] = useState<BannerState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/market-banner")
      .then((res) => (res.ok ? res.json() : null))
      .then((data: BannerState | null) => {
        if (data) setBanner(data);
      })
      .catch(() => { /* silent — banner optional */ })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return null;
  if (!banner) return null;

  const hasImage = Boolean(banner.backgroundImagePath);
  const accentColor = DK_ACCENT[banner.conditionKey] ?? "rgba(30,30,30,0.85)";
  const label = DK_LABEL[banner.conditionKey] ?? banner.conditionKey;

  return (
    <section
      aria-label="Market condition banner"
      style={{
        position: "relative",
        width: "100%",
        minHeight: "clamp(140px, 22vw, 280px)",
        borderRadius: 10,
        overflow: "hidden",
        marginBottom: 28,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
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
      {/* Gradient overlay — ensures text legibility on any image */}
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          inset: 0,
          background: hasImage
            ? "linear-gradient(135deg, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0.30) 100%)"
            : "linear-gradient(135deg, rgba(0,0,0,0.7) 0%, rgba(0,0,0,0.45) 100%)",
          zIndex: 1,
        }}
      />

      {/* D_k state pill — top right */}
      <div
        aria-label={`SPY market state: ${label}`}
        style={{
          position: "absolute",
          top: 14,
          right: 16,
          zIndex: 3,
          background: accentColor,
          backdropFilter: "blur(4px)",
          borderRadius: 20,
          padding: "4px 12px",
          fontSize: "clamp(0.55rem, 1.1vw, 0.68rem)",
          fontWeight: 700,
          letterSpacing: "0.08em",
          color: "#fff",
          fontFamily: "var(--font-geist-mono, monospace)",
        }}
      >
        SPY {label}
      </div>

      {/* Main text content */}
      <div
        style={{
          position: "relative",
          zIndex: 2,
          textAlign: "center",
          padding: "clamp(20px, 4vw, 48px) clamp(20px, 6vw, 80px)",
          maxWidth: 900,
        }}
      >
        {banner.instructionalText ? (
          <p
            style={{
              margin: 0,
              color: banner.textColorHex,
              fontSize: "clamp(0.9rem, 3vw, 1.45rem)",
              fontWeight: 800,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
              lineHeight: 1.35,
              textShadow: "0 2px 12px rgba(0,0,0,0.7), 0 1px 3px rgba(0,0,0,0.9)",
              fontFamily: "'Open Sans', 'Roboto', system-ui, sans-serif",
            }}
          >
            {banner.instructionalText}
          </p>
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
