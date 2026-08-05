"use client";

import { useEffect } from "react";

type ErrorPageProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

function isServerActionMismatch(error: Error & { digest?: string }): boolean {
  const text = `${error?.message ?? ""} ${error?.digest ?? ""}`.toLowerCase();
  return text.includes("failed to find server action");
}

export default function AppErrorPage({ error, reset }: ErrorPageProps) {
  const serverActionMismatch = isServerActionMismatch(error);

  useEffect(() => {
    console.error("App error boundary caught error:", error);
  }, [error]);

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "20px",
        background: "#edf4ed",
      }}
    >
      <section
        className="surface-card"
        style={{
          maxWidth: 680,
          width: "100%",
          textAlign: "left",
        }}
      >
        <h1 style={{ marginTop: 0 }}>Application Error</h1>
        <p style={{ marginBottom: 12 }}>
          {serverActionMismatch
            ? "A stale browser state was detected after an update. Reload to re-sync the app."
            : "The app hit an unexpected error. You can retry now."}
        </p>

        <div className="tfe-toolbar-actions" style={{ marginTop: 8 }}>
          <button type="button" className="btn btn-primary" onClick={() => reset()}>
            Retry
          </button>
          <button type="button" className="btn btn-ghost" onClick={() => window.location.reload()}>
            Reload App
          </button>
        </div>

        <p className="tfe-muted" style={{ marginTop: 12, marginBottom: 0 }}>
          If this continues, sign out and sign back in.
        </p>
      </section>
    </main>
  );
}
