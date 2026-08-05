"use client";

import { useEffect, useRef, useState } from "react";
import {
  BRAIN_WIRING_PANEL_SPECS,
  type ObservationDisplay,
  type OperatorObservationView,
  projectOperatorObservation,
} from "@/lib/operator-observation-view";

const OBSERVATION_ROUTE =
  "/api/admin/guala-listening/observation";
const ACTION_START_ROUTE = "/api/admin/guala-listening/start";
const ACTION_POLL_ROUTE = "/api/admin/guala-listening/poll";
const CSRF_HEADER = "x-tfe-operator-listening-csrf";
const CSRF_VALUE = "tfe.guala.operator_listening.csrf.v1";
const START_REQUEST_SCHEMA =
  "tfe.guala.operator_listening.start.request.v1";
const START_RESPONSE_SCHEMA =
  "tfe.guala.operator_listening.start.response.v1";
const POLL_REQUEST_SCHEMA =
  "tfe.guala.operator_listening.poll.request.v1";
const POLL_RESPONSE_SCHEMA =
  "tfe.guala.operator_listening.poll.response.v1";
const OBSERVATION_POLL_MS = 2_000;
const MAX_ACTION_WINDOW_MS = 180_000;
const MIN_DURATION_US = 1_000;
const MAX_DURATION_US = 5_000_000;
const MIN_POSITION_MM = -(2 ** 31);
const MAX_POSITION_MM = (2 ** 31) - 1;

type MaterialAction = Record<string, unknown>;

type StartResponse = {
  schema?: unknown;
  task_id?: unknown;
  status?: unknown;
  poll_after_ms?: unknown;
  error?: unknown;
};

type PollResponse = {
  schema?: unknown;
  task_id?: unknown;
  status?: unknown;
  poll_after_ms?: unknown;
  failure_code?: unknown;
  error?: unknown;
};

function exactInteger(
  text: string,
  minimum: number,
  maximum: number,
): number | null {
  if (!/^-?\d+$/.test(text)) return null;
  const value = Number(text);
  if (!Number.isSafeInteger(value) || value < minimum || value > maximum) {
    return null;
  }
  return value;
}

function positionFrom(
  xText: string,
  yText: string,
  zText: string,
): { x_mm: number; y_mm: number; z_mm: number } | null {
  const x = exactInteger(xText, MIN_POSITION_MM, MAX_POSITION_MM);
  const y = exactInteger(yText, MIN_POSITION_MM, MAX_POSITION_MM);
  const z = exactInteger(zText, MIN_POSITION_MM, MAX_POSITION_MM);
  if (x === null || y === null || z === null) return null;
  return { x_mm: x, y_mm: y, z_mm: z };
}

function boundedPollDelay(value: unknown): number {
  const parsed = Number(value);
  if (!Number.isInteger(parsed) || parsed < 250 || parsed > 5_000) {
    throw new Error("The action service returned an invalid poll interval.");
  }
  return parsed;
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}

async function postJson(
  route: string,
  body: Record<string, unknown>,
): Promise<Response> {
  return fetch(route, {
    method: "POST",
    credentials: "same-origin",
    cache: "no-store",
    redirect: "error",
    headers: {
      "Content-Type": "application/json",
      [CSRF_HEADER]: CSRF_VALUE,
    },
    body: JSON.stringify(body),
  });
}

function DisplayBlock({
  title,
  value,
}: {
  title: string;
  value: ObservationDisplay;
}) {
  const colors = {
    available: "#193f32",
    quiescent: "#4d3e78",
    unknown: "#6f5410",
    unavailable: "#742c25",
  } as const;
  return (
    <section
      style={{
        minWidth: 0,
        border: "1px solid #c7d1d8",
        borderRadius: 8,
        padding: "0.9rem",
        background: "#fff",
      }}
    >
      <h2
        style={{
          margin: "0 0 0.5rem",
          fontSize: "0.82rem",
          letterSpacing: "0.04em",
          textTransform: "uppercase",
        }}
      >
        {title}
      </h2>
      <pre
        data-observation-state={value.state}
        style={{
          margin: 0,
          color: colors[value.state],
          font: "0.78rem/1.45 var(--font-geist-mono), monospace",
          whiteSpace: "pre-wrap",
          overflowWrap: "anywhere",
        }}
      >
        {value.text}
      </pre>
    </section>
  );
}

function GualaObservationPanel() {
  const [view, setView] = useState<OperatorObservationView | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [lastReadAt, setLastReadAt] = useState<string>("not yet read");

  useEffect(() => {
    let active = true;
    let timer: number | null = null;
    let controller: AbortController | null = null;

    async function readObservation(): Promise<void> {
      controller = new AbortController();
      try {
        const response = await fetch(OBSERVATION_ROUTE, {
          method: "GET",
          credentials: "same-origin",
          cache: "no-store",
          redirect: "error",
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
        const payload: unknown = await response.json();
        if (!response.ok) {
          const error =
            payload !== null &&
            typeof payload === "object" &&
            !Array.isArray(payload) &&
            typeof (payload as Record<string, unknown>).error === "string"
              ? String((payload as Record<string, unknown>).error)
              : `HTTP ${response.status}`;
          throw new Error(error);
        }
        const nextView = projectOperatorObservation(payload);
        if (!active) return;
        setView(nextView);
        setFailure(null);
        setLastReadAt(new Date().toISOString());
      } catch (error) {
        if (!active || controller?.signal.aborted) return;
        setView(null);
        setFailure(
          error instanceof Error
            ? error.message
            : "observation unavailable",
        );
      } finally {
        controller = null;
        if (active) {
          timer = window.setTimeout(readObservation, OBSERVATION_POLL_MS);
        }
      }
    }

    void readObservation();
    return () => {
      active = false;
      if (timer !== null) window.clearTimeout(timer);
      controller?.abort();
    };
  }, []);

  const unknown: ObservationDisplay = {
    state: failure ? "unavailable" : "unknown",
    text: failure
      ? `unavailable · ${failure}`
      : "awaiting observation_snapshot.v5",
  };

  return (
    <section
      aria-labelledby="guala-observation-heading"
      style={{ display: "grid", gap: "1rem" }}
    >
      <div>
        <p style={{ margin: 0, color: "#49657a", fontWeight: 700 }}>
          Authenticated read-only conduit
        </p>
        <h1 id="guala-observation-heading" style={{ margin: "0.35rem 0" }}>
          Guala live physical observation
        </h1>
        <p style={{ margin: 0, lineHeight: 1.6 }}>
          This panel reads only <code>guala.observation_snapshot.v5</code>.
          It does not teach, mutate, recognize words, or make a browser
          decision from the field.
        </p>
      </div>

      <div
        style={{
          border: "1px solid #c7d1d8",
          borderLeft: "5px solid #2d7898",
          borderRadius: 8,
          padding: "0.9rem",
          background: "#f4f8fa",
        }}
      >
        <strong>Current ingress truth:</strong> the live browser audiovisual
        transport supplies sight and sound. The core passive owner is
        modality-neutral and admits any settled experience with at least two
        observed senses.
      </div>

      <dl
        style={{
          display: "grid",
          gridTemplateColumns: "max-content minmax(0, 1fr)",
          gap: "0.4rem 0.8rem",
          margin: 0,
        }}
      >
        <dt>Identity</dt>
        <dd style={{ margin: 0 }}>{view?.identity ?? "unknown"}</dd>
        <dt>Observed tick</dt>
        <dd style={{ margin: 0 }}>{view?.tick ?? "unknown"}</dd>
        <dt>Snapshot receipt</dt>
        <dd style={{ margin: 0, overflowWrap: "anywhere" }}>
          {view?.receipt ?? "unknown"}
        </dd>
        <dt>Last browser read</dt>
        <dd style={{ margin: 0 }}>{lastReadAt}</dd>
      </dl>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
          gap: "0.8rem",
        }}
      >
        <DisplayBlock
          title="Passive whole-organism learning"
          value={view?.passiveLearning ?? unknown}
        />
        <DisplayBlock
          title="Permanent whole-organism wiring"
          value={view?.permanentWiring ?? unknown}
        />
        <DisplayBlock
          title="Latest passive resolution"
          value={view?.latestResolution ?? unknown}
        />
        <DisplayBlock
          title="Reciprocal exact trace"
          value={view?.reciprocalExactTrace ?? unknown}
        />
        <DisplayBlock
          title="No-master status"
          value={view?.masterSense ?? unknown}
        />
        <DisplayBlock
          title="Persistence diary"
          value={view?.persistenceDiary ?? unknown}
        />
        <DisplayBlock
          title="Physical storage bytes"
          value={view?.physicalBytes ?? unknown}
        />
        <DisplayBlock
          title="Whole-organism cognitive progression"
          value={view?.cognitiveProgression ?? unknown}
        />
        <DisplayBlock
          title="Dreaming"
          value={view?.dreaming ?? unknown}
        />
        {BRAIN_WIRING_PANEL_SPECS.map((panel) => (
          <DisplayBlock
            key={panel.key}
            title={panel.title}
            value={
              view?.brainWiringPanels.find(
                (observed) => observed.key === panel.key,
              )?.value ?? unknown
            }
          />
        ))}
        <DisplayBlock
          title="Full-field contract"
          value={view?.fullFieldContract ?? unknown}
        />
      </div>

      <section
        style={{
          border: "1px solid #c7d1d8",
          borderRadius: 8,
          padding: "0.9rem",
          overflowX: "auto",
          background: "#fff",
        }}
      >
        <h2 style={{ marginTop: 0 }}>Exact latest full-field tuples</h2>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {["Sense", "State", "Substream", "Tuple", "D/M/R/U/C/P/B"].map(
                (heading) => (
                  <th
                    key={heading}
                    style={{
                      textAlign: "left",
                      padding: "0.45rem",
                      borderBottom: "1px solid #c7d1d8",
                    }}
                  >
                    {heading}
                  </th>
                ),
              )}
            </tr>
          </thead>
          <tbody>
            {view && view.fullFieldRows.length > 0 ? (
              view.fullFieldRows.map((row, index) => (
                <tr key={`${row.sense}:${row.substream}:${row.tuple}:${index}`}>
                  {[row.sense, row.state, row.substream, row.tuple, row.fields].map(
                    (value, cellIndex) => (
                      <td
                        key={cellIndex}
                        style={{
                          padding: "0.45rem",
                          borderBottom: "1px solid #e1e7eb",
                          verticalAlign: "top",
                          overflowWrap: "anywhere",
                        }}
                      >
                        {value}
                      </td>
                    ),
                  )}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5} style={{ padding: "0.6rem" }}>
                  {failure
                    ? `unavailable · ${failure}`
                    : "no current field tuples supplied"}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </section>
  );
}

function NonCognitiveActionTrial() {
  const [state, setState] = useState<
    "idle" | "starting" | "running" | "complete" | "failed"
  >("idle");
  const [taskId, setTaskId] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);
  const [operation, setOperation] = useState<"" | "move" | "pick" | "place">(
    "",
  );
  const [durationText, setDurationText] = useState("");
  const [objectId, setObjectId] = useState("");
  const [xText, setXText] = useState("");
  const [yText, setYText] = useState("");
  const [zText, setZText] = useState("");
  const [headingText, setHeadingText] = useState("");
  const runNumber = useRef(0);

  function selectedAction(): MaterialAction | null {
    const duration = exactInteger(
      durationText,
      MIN_DURATION_US,
      MAX_DURATION_US,
    );
    if (duration === null) return null;
    if (operation === "move") {
      const position = positionFrom(xText, yText, zText);
      const heading = exactInteger(headingText, 0, 359_999);
      if (position === null || heading === null) return null;
      return {
        schema: START_REQUEST_SCHEMA,
        operation,
        duration_microseconds: duration,
        target_pose: {
          position,
          heading_millidegrees: heading,
        },
      };
    }
    if (operation === "pick") {
      if (!objectId || objectId.trim() !== objectId) return null;
      return {
        schema: START_REQUEST_SCHEMA,
        operation,
        duration_microseconds: duration,
        object_id: objectId,
      };
    }
    if (operation === "place") {
      const targetPosition = positionFrom(xText, yText, zText);
      if (
        !objectId ||
        objectId.trim() !== objectId ||
        targetPosition === null
      ) {
        return null;
      }
      return {
        schema: START_REQUEST_SCHEMA,
        operation,
        duration_microseconds: duration,
        object_id: objectId,
        target_position: targetPosition,
      };
    }
    return null;
  }

  async function runActionTrial(action: MaterialAction): Promise<void> {
    const thisRun = runNumber.current + 1;
    runNumber.current = thisRun;
    setState("starting");
    setTaskId(null);
    setFailure(null);
    try {
      const startResponse = await postJson(ACTION_START_ROUTE, action);
      const start = (await startResponse.json()) as StartResponse;
      if (
        !startResponse.ok ||
        start.schema !== START_RESPONSE_SCHEMA ||
        start.status !== "accepted" ||
        typeof start.task_id !== "string"
      ) {
        throw new Error(
          typeof start.error === "string"
            ? start.error
            : "The physical action trial was not accepted.",
        );
      }
      const acceptedTaskId = start.task_id;
      let pollAfterMs = boundedPollDelay(start.poll_after_ms);
      const deadline = Date.now() + MAX_ACTION_WINDOW_MS;
      setTaskId(acceptedTaskId);
      setState("running");
      while (Date.now() < deadline && runNumber.current === thisRun) {
        await delay(pollAfterMs);
        const pollResponse = await postJson(ACTION_POLL_ROUTE, {
          schema: POLL_REQUEST_SCHEMA,
          task_id: acceptedTaskId,
        });
        const poll = (await pollResponse.json()) as PollResponse;
        if (
          !pollResponse.ok ||
          poll.schema !== POLL_RESPONSE_SCHEMA ||
          poll.task_id !== acceptedTaskId
        ) {
          throw new Error(
            typeof poll.error === "string"
              ? poll.error
              : "The physical action trial could not be read.",
          );
        }
        if (poll.status === "complete") {
          setState("complete");
          return;
        }
        if (poll.status === "failed") {
          throw new Error(
            typeof poll.failure_code === "string"
              ? poll.failure_code
              : "The physical action trial failed.",
          );
        }
        if (poll.status !== "accepted" && poll.status !== "processing") {
          throw new Error("The physical action trial returned an invalid state.");
        }
        pollAfterMs = boundedPollDelay(poll.poll_after_ms);
      }
      if (runNumber.current === thisRun) {
        throw new Error(
          "The bounded physical action window ended before completion.",
        );
      }
    } catch (error) {
      if (runNumber.current !== thisRun) return;
      setFailure(
        error instanceof Error ? error.message : "Physical action trial failed.",
      );
      setState("failed");
    }
  }

  const action = selectedAction();
  const busy = state === "starting" || state === "running";
  const fieldStyle = {
    display: "grid",
    gap: "0.3rem",
  } as const;

  return (
    <details
      style={{
        border: "1px solid #b8c4cc",
        borderRadius: 8,
        padding: "1rem",
        background: "#fafafa",
      }}
    >
      <summary style={{ cursor: "pointer", fontWeight: 700 }}>
        Separate physical action trial — non-cognitive
      </summary>
      <p>
        This optional control asks the embodied runtime to execute one selected
        physical action. Completion does not prove hearing, word learning,
        recognition, meaning, or cognition. Its result is not used as the
        observation panel&apos;s authority.
      </p>
      <fieldset
        disabled={busy}
        style={{ display: "grid", gap: "0.9rem", padding: "1rem" }}
      >
        <legend>Operator-selected material action</legend>
        <label style={fieldStyle}>
          Operation
          <select
            value={operation}
            onChange={(event) => {
              const value = event.target.value;
              if (
                value === "" ||
                value === "move" ||
                value === "pick" ||
                value === "place"
              ) {
                setOperation(value);
              }
            }}
          >
            <option value="">Select an action</option>
            <option value="move">Move</option>
            <option value="pick">Pick</option>
            <option value="place">Place</option>
          </select>
        </label>
        <label style={fieldStyle}>
          Duration in microseconds (1,000–5,000,000)
          <input
            type="number"
            min={MIN_DURATION_US}
            max={MAX_DURATION_US}
            step={1}
            value={durationText}
            onChange={(event) => setDurationText(event.target.value)}
          />
        </label>
        {operation === "pick" || operation === "place" ? (
          <label style={fieldStyle}>
            Physical object identifier
            <input
              type="text"
              maxLength={256}
              value={objectId}
              onChange={(event) => setObjectId(event.target.value)}
            />
          </label>
        ) : null}
        {operation === "move" || operation === "place" ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              gap: "0.75rem",
            }}
          >
            {[
              ["X millimetres", xText, setXText],
              ["Y millimetres", yText, setYText],
              ["Z millimetres", zText, setZText],
            ].map(([label, value, setter]) => (
              <label key={String(label)} style={fieldStyle}>
                {String(label)}
                <input
                  type="number"
                  min={MIN_POSITION_MM}
                  max={MAX_POSITION_MM}
                  step={1}
                  value={String(value)}
                  onChange={(event) =>
                    (setter as (next: string) => void)(event.target.value)
                  }
                />
              </label>
            ))}
          </div>
        ) : null}
        {operation === "move" ? (
          <label style={fieldStyle}>
            Heading in millidegrees (0–359,999)
            <input
              type="number"
              min={0}
              max={359_999}
              step={1}
              value={headingText}
              onChange={(event) => setHeadingText(event.target.value)}
            />
          </label>
        ) : null}
      </fieldset>
      <button
        type="button"
        disabled={busy || action === null}
        onClick={() => {
          if (action) void runActionTrial(action);
        }}
        style={{
          marginTop: "0.8rem",
          border: 0,
          borderRadius: 8,
          padding: "0.7rem 1rem",
          background: busy || action === null ? "#7990a0" : "#123f5a",
          color: "white",
          fontWeight: 700,
        }}
      >
        {busy ? "Physical action running…" : "Start non-cognitive action trial"}
      </button>
      <dl
        style={{
          display: "grid",
          gridTemplateColumns: "max-content minmax(0, 1fr)",
          gap: "0.4rem 0.8rem",
        }}
      >
        <dt>Trial status</dt>
        <dd style={{ margin: 0 }}>{state}</dd>
        <dt>Operation receipt</dt>
        <dd style={{ margin: 0, overflowWrap: "anywhere" }}>
          {taskId ?? "not started"}
        </dd>
      </dl>
      {state === "complete" ? (
        <p role="status">
          The material action trial completed. No cognitive interpretation is
          made from that completion.
        </p>
      ) : null}
      {failure ? (
        <p role="alert" style={{ color: "#8a1f11" }}>
          {failure}
        </p>
      ) : null}
    </details>
  );
}

export default function GualaOperatorListeningClient() {
  return (
    <main
      style={{
        maxWidth: 1180,
        margin: "0 auto",
        padding: "2rem",
        display: "grid",
        gap: "1.5rem",
      }}
    >
      <GualaObservationPanel />
      <NonCognitiveActionTrial />
    </main>
  );
}
