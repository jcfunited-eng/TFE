"""Bounded TFE production observation through an existing ECS Exec session.

No task launches, configuration writes, orders, or database mutations.
Run from a terminal (ECS Session Manager needs an open stdin).
"""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess


QUERIES = {
    "ledger": """SELECT id,ticker,status,shares,entry_filled_price,entry_filled_at,
        exit_filled_price,exit_filled_at,p_l,p_l_pct,exit_reason,vault_equity_at_signal,
        dollar_allocation FROM personal_trade_ledger WHERE signal_class='CH2'
        AND status IN ('filled','closed') ORDER BY entry_filled_at,id""",
    "bars": """SELECT ticker AS "Symbol",to_char(bar_date,'YYYY-MM-DD') AS "Date",
        close AS "Close",volume AS "Volume",source FROM daily_bars
        WHERE ticker IN ('SPY','AGNC') ORDER BY ticker,bar_date""",
    "snapshots": """SELECT ticker,generated_at_utc,snapshot_row_json
        FROM runtime_decisions_latest WHERE ticker IN ('SPY','AGNC')""",
}


def decode_receipt(output):
    header = re.search(r"TFE_BEGIN (\d+) ([0-9a-f]{64})", output)
    parts = re.findall(r"TFE_PART (\d+) ([A-Za-z0-9+/=]+)", output)
    if not header or "TFE_END" not in output:
        raise ValueError("production export transport incomplete")
    expected_offset = 0
    fragments = []
    for offset, fragment in parts:
        if int(offset) != expected_offset:
            raise ValueError("production export transport gap/duplicate")
        fragments.append(fragment)
        expected_offset += len(fragment)
    if expected_offset != int(header.group(1)):
        raise ValueError("production export transport length mismatch")
    raw = gzip.decompress(base64.b64decode("".join(fragments), validate=True))
    if hashlib.sha256(raw).hexdigest() != header.group(2):
        raise ValueError("production export digest mismatch")
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    script = r'''
const {Pool}=require('pg');
const {gzipSync}=require('zlib');
const {createHash}=require('crypto');
const pool=new Pool({ssl:{rejectUnauthorized:false},connectionTimeoutMillis:8000,max:1});
(async()=>{
  const client=await pool.connect();
  try {
    await client.query('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY');
    await client.query('SET LOCAL statement_timeout=8000');
    const out={observed_at:new Date().toISOString()};
    for(const [key,sql] of Object.entries(QUERIES)) out[key]=(await client.query(sql)).rows;
    await client.query('ROLLBACK');
    const raw=Buffer.from(JSON.stringify(out));
    const encoded=gzipSync(raw).toString('base64');
    console.log('TFE_BEGIN '+encoded.length+' '+createHash('sha256').update(raw).digest('hex'));
    for(let i=0;i<encoded.length;i+=500) {
      console.log('TFE_PART '+i+' '+encoded.slice(i,i+500));
      await new Promise(resolve=>setTimeout(resolve,40));
    }
    console.log('TFE_END');
    await new Promise(resolve=>setTimeout(resolve,500));
  } finally {client.release();await pool.end();}
})().catch(error=>{console.error(error.message);process.exitCode=1;});
'''
    command = "node -e " + shlex.quote("const QUERIES=" + json.dumps(QUERIES) + ";" + script)
    result = subprocess.run([
        "aws", "ecs", "execute-command", "--cluster", "tfe-web-cluster",
        "--task", args.task, "--container", "tfe-web", "--interactive",
        "--command", command,
    ], capture_output=True, text=True, timeout=55)
    if result.returncode:
        raise RuntimeError(f"ECS read-only observation failed, exit={result.returncode}")
    raw = decode_receipt(result.stdout)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as out:
        out.write(raw)
    data = json.loads(raw)
    print(json.dumps({"observed_at": data["observed_at"], "ledger_rows": len(data["ledger"]),
                      "bar_rows": len(data["bars"]), "sha256": hashlib.sha256(raw).hexdigest(),
                      "output": str(args.output)}))


if __name__ == "__main__":
    main()
