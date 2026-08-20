import "server-only";

import { createHash } from "node:crypto";
import { GetObjectCommand, S3Client } from "@aws-sdk/client-s3";

export type ChannelCode = "CH3" | "CH4" | "CH6";

export type ChannelPositionView = {
  symbol: string;
  side: 1 | -1;
  shares: number;
  entryPrice: number;
  currentPrice: number | null;
  notional: number;
  unrealizedPnl: number | null;
  returnPct: number | null;
  enteredAt: string;
  status: string;
};

export type ChannelClosedView = {
  symbol: string;
  side: 1 | -1;
  shares: number;
  entryPrice: number;
  exitPrice: number | null;
  pnl: number | null;
  returnPct: number | null;
  enteredAt: string;
  exitedAt: string;
  reason: string;
};

export type StagedEntryView = {
  symbol: string;
  decidedClose: number;
  decidedDate: string;
};

export type ChannelBookView = {
  channel: ChannelCode;
  title: string;
  engine: string;
  sourceSha256: string;
  sourceUpdatedAt: string;
  publishedAt: string;
  startingCapital: number;
  cash: number;
  equity: number | null;
  realizedPnl: number;
  unrealizedPnl: number | null;
  positions: ChannelPositionView[];
  closed: ChannelClosedView[];
  staged: StagedEntryView[];
  rules: string[];
  markAsOf: string | null;
  markSource: string;
};

type SnapshotEnvelope = {
  schema: "tfe.channel-book.snapshot.v1";
  channel: ChannelCode;
  source_name: string;
  source_sha256: string;
  source_updated_at: string;
  published_at: string;
  source_bytes_base64: string;
};

type GenericRecord = Record<string, unknown>;

const DEFAULT_S3_URI =
  "s3://tfe-codebuild-src-418384447921-us-east-1/runtime-refresh-checkpoints/channel-books";

const CHANNEL_META: Record<ChannelCode, { title: string; rules: string[] }> = {
  CH3: {
    title: "CH3 — Shadow Hunter",
    rules: [
      "Simulated short channel; no real orders.",
      "Reduced entry projection: completed-close gain of at least 8%, volume at least 3× the preceding 20-session mean, price at least $5, and an explicit same-day gband=0 herd reading. Missing herd coverage is unknown and refused.",
      "Harvest at the first completed daily close 5% below entry; anomaly-cut at the first completed daily close 20% above entry; fifth-session close is the backstop. The 20% level is a trigger, not a guaranteed loss cap across gaps.",
      "After an anomaly cut, the symbol remains refuted until a later completed daily close returns to or below the original entry. The cut bar cannot be re-entered.",
      "Declared gross exposure is capped at 2× starting capital; borrow costs are not modeled.",
    ],
  },
  CH4: {
    title: "CH4 — Paper Structural Channel",
    rules: [
      "Simulated structural channel; no real orders.",
      "The book is a frozen experiment and is updated from closed daily bars.",
      "Positions resolve under the recorded K3/boundary law; page display does not create or alter a decision.",
    ],
  },
  CH6: {
    title: "CH6 — Fast Harvest",
    rules: [
      "Simulated short channel; no real orders.",
      "Reduced entry projection: completed-close gain of at least 8%, volume at least 3× the preceding 20-session mean, price at least $5, and an explicit same-day gband=0 herd reading. Missing herd coverage is unknown and refused.",
      "Positions size to $2,500 per entity maximum, best-ranked first across as many entities as supply and cash allow, capped at 1% of each entity's normal-day traded money. Operating companies only — funds and baskets are the zombie category and are refused. Winners arm at +5% and trail one percentage point from their best observed mark; the end-of-day sweep banks anything at +2% or better (the fast-cash law); the fifth completed session is the backstop.",
      "The anomaly-cut trigger is checked at every five-minute mark and completed-close settlement. Marks and gaps can cross 20%, so the level is a trigger rather than a guaranteed realized-loss ceiling.",
      "After an anomaly cut, the symbol remains refuted until a later completed daily close returns to or below the original entry. The cut bar cannot be re-entered. Borrow costs are not modeled.",
    ],
  },
};

let s3Client: S3Client | null = null;

function record(value: unknown): GenericRecord {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as GenericRecord)
    : {};
}

function finite(value: unknown, fallback = 0): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function nullableFinite(value: unknown): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function side(value: unknown): 1 | -1 {
  return Number(value) === -1 ? -1 : 1;
}

function parseS3Uri(uri: string): { bucket: string; prefix: string } {
  const parsed = new URL(uri);
  if (parsed.protocol !== "s3:" || !parsed.hostname) {
    throw new Error("TFE_CHANNEL_BOOK_S3_URI must be an s3://bucket/prefix URI");
  }
  return { bucket: parsed.hostname, prefix: parsed.pathname.replace(/^\/+|\/+$/g, "") };
}

function channelObjectKey(prefix: string, channel: ChannelCode): string {
  const filename = `${channel.toLowerCase()}.json`;
  return prefix ? `${prefix}/${filename}` : filename;
}

function client(): S3Client {
  if (!s3Client) {
    s3Client = new S3Client({ region: process.env.AWS_REGION ?? "us-east-1" });
  }
  return s3Client;
}

function validateEnvelope(value: unknown, expectedChannel: ChannelCode): SnapshotEnvelope {
  const envelope = record(value);
  if (envelope.schema !== "tfe.channel-book.snapshot.v1") {
    throw new Error(`${expectedChannel} snapshot schema is missing or unsupported`);
  }
  if (envelope.channel !== expectedChannel) {
    throw new Error(`${expectedChannel} snapshot channel identity does not match its object key`);
  }
  for (const field of ["source_name", "source_sha256", "source_updated_at", "published_at", "source_bytes_base64"]) {
    if (typeof envelope[field] !== "string" || !(envelope[field] as string).trim()) {
      throw new Error(`${expectedChannel} snapshot is missing ${field}`);
    }
  }
  return envelope as SnapshotEnvelope;
}

async function readSnapshot(
  channel: ChannelCode,
  objectFilename?: string,
): Promise<{ envelope: SnapshotEnvelope; book: GenericRecord }> {
  const uri = String(process.env.TFE_CHANNEL_BOOK_S3_URI ?? DEFAULT_S3_URI).trim();
  const { bucket, prefix } = parseS3Uri(uri);
  const key = objectFilename
    ? (prefix ? `${prefix}/${objectFilename}` : objectFilename)
    : channelObjectKey(prefix, channel);
  const response = await client().send(
    new GetObjectCommand({ Bucket: bucket, Key: key }),
  );
  if (!response.Body) throw new Error(`${channel} snapshot object has no body`);

  const envelopeBytes = Buffer.from(await response.Body.transformToByteArray());
  const envelope = validateEnvelope(JSON.parse(envelopeBytes.toString("utf-8")), channel);
  const sourceBytes = Buffer.from(envelope.source_bytes_base64, "base64");
  const digest = createHash("sha256").update(sourceBytes).digest("hex");
  if (digest !== envelope.source_sha256) {
    throw new Error(`${channel} snapshot failed its SHA-256 receipt`);
  }

  const book = JSON.parse(sourceBytes.toString("utf-8"));
  if (!book || typeof book !== "object" || Array.isArray(book)) {
    throw new Error(`${channel} authoritative book is not one JSON object`);
  }
  return { envelope, book: book as GenericRecord };
}

async function fetchMarks(symbols: string[]): Promise<{ prices: Record<string, number>; asOf: string | null }> {
  if (!symbols.length) return { prices: {}, asOf: null };
  const key = process.env.APCA_API_KEY_ID ?? process.env.ALPACA_API_KEY ?? "";
  const secret = process.env.APCA_API_SECRET_KEY ?? process.env.ALPACA_SECRET_KEY ?? "";
  if (!key || !secret) return { prices: {}, asOf: null };

  const prices: Record<string, number> = {};
  let asOf: string | null = null;
  const batches: string[][] = [];
  for (let index = 0; index < symbols.length; index += 100) batches.push(symbols.slice(index, index + 100));

  for (const batch of batches) {
    const query = batch.map(encodeURIComponent).join(",");
    const response = await fetch(
      `https://data.alpaca.markets/v2/stocks/snapshots?symbols=${query}&feed=iex`,
      {
        headers: { "APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret },
        cache: "no-store",
        signal: AbortSignal.timeout(8_000),
      },
    );
    if (!response.ok) throw new Error(`Alpaca snapshot request failed with HTTP ${response.status}`);
    const payload = (await response.json()) as Record<
      string,
      { latestTrade?: { p?: number; t?: string }; minuteBar?: { c?: number; t?: string }; dailyBar?: { c?: number; t?: string } }
    >;
    for (const [symbol, snapshot] of Object.entries(payload)) {
      const price = nullableFinite(snapshot.latestTrade?.p ?? snapshot.minuteBar?.c ?? snapshot.dailyBar?.c);
      if (price !== null && price > 0) prices[symbol] = price;
      const timestamp = snapshot.latestTrade?.t ?? snapshot.minuteBar?.t ?? snapshot.dailyBar?.t ?? null;
      if (timestamp && (!asOf || timestamp > asOf)) asOf = timestamp;
    }
  }
  return { prices, asOf };
}

function positionView(
  symbol: string,
  rawPosition: GenericRecord,
  currentPrice: number | null,
  channel: ChannelCode,
): ChannelPositionView {
  const positionSide = side(rawPosition.side);
  const entryPrice = finite(rawPosition.entry_px);
  const shares = Math.max(0, Math.trunc(finite(rawPosition.shares)));
  const notional = finite(rawPosition.notional, entryPrice * shares);
  const unrealizedPnl = currentPrice === null ? null : (currentPrice - entryPrice) * shares * positionSide;
  const returnPct = currentPrice === null || entryPrice <= 0
    ? null
    : 100 * (currentPrice / entryPrice - 1) * positionSide;
  let status = "OPEN";
  if (channel === "CH3" && returnPct !== null) {
    if (returnPct <= -20) status = "ANOMALY TRIGGER EXCEEDED — DAILY CLOSE REQUIRED";
    else if (returnPct >= 5) status = "HARVEST AT NEXT DAILY CLOSE";
  }
  if (channel === "CH6" && returnPct !== null) {
    if (returnPct <= -20) status = "ANOMALY CUT DUE AT NEXT POLL";
    else if (returnPct >= 5) status = "ARMED — TRAILING";
    else if (returnPct >= 2) status = "BANKS AT NEXT DAY-END SWEEP";
    else if (rawPosition.armed === true) status = "ARMED";
  }
  return {
    symbol,
    side: positionSide,
    shares,
    entryPrice,
    currentPrice,
    notional,
    unrealizedPnl,
    returnPct,
    enteredAt: text(rawPosition.entry_date ?? rawPosition.date ?? rawPosition.opened_at),
    status,
  };
}

function closedView(rawTrade: GenericRecord): ChannelClosedView {
  return {
    symbol: text(rawTrade.symbol ?? rawTrade.sym),
    side: side(rawTrade.side),
    shares: Math.max(0, Math.trunc(finite(rawTrade.shares))),
    entryPrice: finite(rawTrade.entry_px),
    exitPrice: nullableFinite(rawTrade.exit_px),
    pnl: nullableFinite(rawTrade.pnl),
    returnPct: nullableFinite(rawTrade.ret_pct),
    enteredAt: text(rawTrade.entry_date ?? rawTrade.date),
    exitedAt: text(rawTrade.exit_at ?? rawTrade.exit_date ?? rawTrade.resolved),
    reason: text(rawTrade.reason ?? rawTrade.status),
  };
}

function normalizeRawBook(channel: ChannelCode, book: GenericRecord): {
  engine: string;
  startingCapital: number;
  cash: number;
  positions: Array<{ symbol: string; value: GenericRecord }>;
  closed: GenericRecord[];
} {
  if (channel === "CH3") {
    const bookAccount = record(book.book);
    const finds = Array.isArray(book.finds) ? book.finds.map(record) : [];
    return {
      engine: text(book.engine),
      startingCapital: finite(bookAccount.start, 100_000),
      cash: finite(bookAccount.cash, 100_000),
      positions: finds
        .filter((item) => item.status === "OPEN")
        .map((item) => ({ symbol: text(item.symbol), value: item })),
      closed: finds.filter((item) => item.status !== "OPEN"),
    };
  }

  const rawPositions = record(book.positions);
  return {
    engine: text(book.engine),
    startingCapital: finite(book.start, 100_000),
    cash: finite(book.cash, 100_000),
    positions: Object.entries(rawPositions).map(([symbol, value]) => ({ symbol, value: record(value) })),
    closed: Array.isArray(book.closed) ? book.closed.map(record) : [],
  };
}

export type PerceptionVerdictView = {
  symbol: string;
  structure: string;
  verdict: string;
  outcome: string;
};

export type PerceptionScoreRow = {
  verdict: string;
  filed: number;
  faded: number;
  ran: number;
  flat: number;
  pending: number;
};

export type ChannelPerceptionView = {
  sourceSha256: string;
  sourceUpdatedAt: string;
  publishedAt: string;
  asOfClose: string;
  layerLives: number;
  layerThrough: string;
  eventsDecade: number;
  payStructures: number;
  avoidStructures: number;
  payShare: number;
  avoidShare: number;
  tonight: PerceptionVerdictView[];
  scoreboard: PerceptionScoreRow[];
  law: string;
};

export async function getChannelPerceptionView(): Promise<ChannelPerceptionView | null> {
  try {
    const { envelope, book } = await readSnapshot("CH6", "ch6-perception.json");
    if (envelope.source_name !== "ch6_perception.json") {
      return null; // a book envelope at the perception key is refused
    }
    const layer = record(book.layer);
    const standing = record(book.standing_census);
    const tonightRaw = Array.isArray(book.tonight) ? book.tonight.map(record) : [];
    const scoreboardRaw = record(book.scoreboard);
    const scoreboard: PerceptionScoreRow[] = ["PAY", "AVOID", "UNDECIDED"]
      .filter((verdict) => verdict in scoreboardRaw)
      .map((verdict) => {
        const row = record(scoreboardRaw[verdict]);
        return {
          verdict,
          filed: finite(row.n),
          faded: finite(row.FADED),
          ran: finite(row.RAN),
          flat: finite(row.FLAT),
          pending: finite(row.PENDING),
        };
      });
    return {
      sourceSha256: envelope.source_sha256,
      sourceUpdatedAt: envelope.source_updated_at,
      publishedAt: envelope.published_at,
      asOfClose: text(book.as_of_close),
      layerLives: finite(layer.lives),
      layerThrough: text(layer.through),
      eventsDecade: finite(standing.events_decade),
      payStructures: finite(standing.pay_structures),
      avoidStructures: finite(standing.avoid_structures),
      payShare: finite(standing.pay_share_of_supply),
      avoidShare: finite(standing.avoid_share_of_supply),
      tonight: tonightRaw.map((item) => ({
        symbol: text(item.symbol),
        structure: text(item.structure),
        verdict: text(item.verdict),
        outcome: text(item.outcome),
      })),
      scoreboard,
      law: text(book.law),
    };
  } catch {
    return null; // the book page never fails because perception is absent
  }
}

export async function getChannelBookView(channel: ChannelCode): Promise<ChannelBookView> {
  const { envelope, book } = await readSnapshot(channel);
  const normalized = normalizeRawBook(channel, book);
  const symbols = [...new Set(normalized.positions.map((position) => position.symbol).filter(Boolean))].sort();
  let marks: { prices: Record<string, number>; asOf: string | null } = { prices: {}, asOf: null };
  let markSource = "Alpaca IEX latest trade, then latest minute/daily bar";
  try {
    marks = await fetchMarks(symbols);
  } catch (error) {
    markSource = `Unavailable: ${error instanceof Error ? error.message : String(error)}`;
  }

  const positions = normalized.positions
    .map(({ symbol, value }) => positionView(symbol, value, marks.prices[symbol] ?? null, channel))
    .sort((a, b) => a.symbol.localeCompare(b.symbol));
  const stagedRaw = Array.isArray(book.staged_entries) ? book.staged_entries.map(record) : [];
  const staged = stagedRaw
    .map((item) => ({
      symbol: text(item.symbol),
      decidedClose: finite(item.decided_close),
      decidedDate: text(item.decided_date),
    }))
    .filter((item) => item.symbol);
  const closed = normalized.closed
    .map(closedView)
    .filter((trade) => trade.symbol)
    .sort((a, b) => b.exitedAt.localeCompare(a.exitedAt));
  const realizedPnl = closed.reduce((sum, trade) => sum + (trade.pnl ?? 0), 0);
  const markedPositions = positions.filter((position) => position.unrealizedPnl !== null);
  const hasCompleteMarks = markedPositions.length === positions.length;
  const unrealizedPnl = hasCompleteMarks
    ? markedPositions.reduce((sum, position) => sum + (position.unrealizedPnl ?? 0), 0)
    : null;
  const heldNotional = positions.reduce((sum, position) => sum + position.notional, 0);
  const equity = unrealizedPnl === null ? null : normalized.cash + heldNotional + unrealizedPnl;

  return {
    channel,
    title: CHANNEL_META[channel].title,
    engine: normalized.engine,
    sourceSha256: envelope.source_sha256,
    sourceUpdatedAt: envelope.source_updated_at,
    publishedAt: envelope.published_at,
    startingCapital: normalized.startingCapital,
    cash: normalized.cash,
    equity,
    realizedPnl,
    unrealizedPnl,
    positions,
    closed,
    staged,
    rules: CHANNEL_META[channel].rules,
    markAsOf: marks.asOf,
    markSource,
  };
}
