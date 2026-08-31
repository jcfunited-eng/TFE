import { NextResponse } from "next/server";
import { S3Client, GetObjectCommand } from "@aws-sdk/client-s3";
import { getCurrentServerUser } from "@/lib/server-auth";

// The machinery's pulse sheet, published beside the channel books by
// the local publication loop every minute. A missing or stale sheet is
// itself the signal (2026-08-31: two loops died in a weekend restart
// and trading stopped silently for two days).

const BUCKET = "tfe-codebuild-src-418384447921-us-east-1";
const KEY = "runtime-refresh-checkpoints/channel-books/heartbeats.json";

export type PulseRow = {
  key: string;
  label: string;
  last: string | null;
  minutes_ago: number | null;
  expect_minutes: number;
  stale: boolean;
};

export async function GET() {
  const user = await getCurrentServerUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  try {
    const s3 = new S3Client({ region: "us-east-1" });
    const res = await s3.send(new GetObjectCommand({ Bucket: BUCKET, Key: KEY }));
    const body = JSON.parse(await res.Body!.transformToString()) as {
      generated_at?: string;
      pulses?: Record<string, { last?: string | null; expect_minutes?: number; label?: string }>;
    };
    const now = Date.now();
    const rows: PulseRow[] = [];
    const genAt = new Date(body.generated_at ?? 0).getTime();
    const genAgo = Number.isFinite(genAt) ? (now - genAt) / 60000 : null;
    rows.push({
      key: "publisher",
      label: "pulse publisher",
      last: body.generated_at ?? null,
      minutes_ago: genAgo === null ? null : Math.round(genAgo),
      expect_minutes: 10,
      stale: genAgo === null || genAgo > 10,
    });
    for (const [key, p] of Object.entries(body.pulses ?? {})) {
      const t = p.last ? new Date(p.last).getTime() : NaN;
      const ago = Number.isFinite(t) ? (now - t) / 60000 : null;
      const expect = Number(p.expect_minutes ?? 60);
      rows.push({
        key,
        label: String(p.label ?? key),
        last: p.last ?? null,
        minutes_ago: ago === null ? null : Math.round(ago),
        expect_minutes: expect,
        stale: ago === null || ago > expect,
      });
    }
    return NextResponse.json({ rows, fetched_at: new Date(now).toISOString() });
  } catch {
    // the sheet itself unreachable — everything reads stale, loudly
    return NextResponse.json({
      rows: [{
        key: "publisher", label: "pulse publisher", last: null,
        minutes_ago: null, expect_minutes: 10, stale: true,
      }],
      fetched_at: new Date().toISOString(),
      error: "heartbeat sheet unreachable",
    });
  }
}
