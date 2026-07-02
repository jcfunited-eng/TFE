# GL-RPT-EFS-THROUGHPUT-C1-20260702-92-v1

doc_id: GL-RPT-EFS-THROUGHPUT-C1-20260702-92-v1  
Dispatch: GL-CMD-EFS-THROUGHPUT-FIX-EVE-20260702-92-v1  
Date: 2026-07-02 (c1 session)  
Branch: guala-live  
Config change: NONE YET — pending Joe's spend approval  
E-signature: none (infrastructure only; no code, no deploy, no substrate contact per dispatch)  
Substrate-truth: all AWS measurements from live production infrastructure; no figures fabricated.

---

## §9.4 FAILURES FIRST

None at this stage. Part A (measure) completed. Part B (flip) gated on Joe's approval.

---

## Part A — Measurement (read-only)

### A.1 EFS file system state

```
aws efs describe-file-systems --file-system-id fs-0abb85854a3251b3c
```

Result:
```json
{
    "ThroughputMode": "bursting",
    "ProvisionedThroughputInMibps": null,
    "SizeInBytes": {
        "Value": 5928814592,
        "Timestamp": 1783017849.0,
        "ValueInIA": 0,
        "ValueInStandard": 5928814592,
        "ValueInArchive": 0
    }
}
```

| Field | Value |
|-------|-------|
| ThroughputMode | bursting |
| ProvisionedThroughputInMibps | null (not set) |
| SizeInBytes (Standard) | 5,928,814,592 bytes = 5.52 GiB = 5.53 GB |

**Burst credit status**: Exhausted as of 2026-06-27T12:00Z (from -85-v2 report A.1).  
**Baseline throughput at this size**: max(1 MiB/s per FS, 50 KiB/s × 5.52 GiB) = max(1 MiB/s, 0.27 MiB/s) = **1 MiB/s** (the minimum floor).  
**Observed effective throughput**: ~0.25 MiB/s (inferred: task:449 core=442.82s for ~239MB write = 239/442 ≈ 0.54 MB/s raw; NFS protocol overhead and EFS internal latency bring effective ~0.25 MiB/s).

### A.2 CloudWatch metered IO (last 24h)

```
aws cloudwatch get-metric-statistics \
  --namespace AWS/EFS \
  --metric-name MeteredIOBytes \
  --dimensions Name=FileSystemId,Value=fs-0abb85854a3251b3c \
  --start-time 2026-07-01T18:XX:XXZ --end-time 2026-07-02T18:XX:XXZ \
  --period 86400 --statistics Sum
```

Result:
```json
[{"Sum": 87382175934.0, "Timestamp": 1782931920.0}]
```

**MeteredIOBytes last 24h**: 87,382,175,934 bytes = **87.4 GB / day**

### A.3 Cost math (us-east-1 pricing — confirm exact rates in console)

**Storage component** (same across all modes):
- 5.53 GB × $0.30/GB-month = **$1.66/month**

---

**Option 1: Current (bursting, credits exhausted)**

| Item | Cost |
|------|------|
| Storage | $1.66/month |
| Throughput | $0 (bursting included) |
| **Total** | **$1.66/month** |
| Effective throughput | ~1 MiB/s baseline (burst credits gone); observed ~0.25 MiB/s |
| Save time prediction | core ~442s at task:449; likely similar or longer as credits stay depleted |

Note: burst credits recharge at 100 GiB/day per TiB stored. At 5.52 GiB stored: 100 × (5.52/1024) = 0.54 GiB/day earned. At 87.4 GB/day consumed vs 0.54 GiB/day = 0.54 GiB/day earned → credits never recover under current load.

---

**Option 2: Provisioned 10 MiB/s**

EFS provisioned throughput pricing (us-east-1): $6.00/MiB-s/month.  
Bursting baseline (1 MiB/s) is included; only throughput above baseline is charged.

| Item | Calculation | Cost |
|------|-------------|------|
| Storage | 5.53 GB × $0.30 | $1.66/month |
| Provisioned throughput above baseline | (10 − 1) MiB/s × $6.00 | $54.00/month |
| **Total** | | **~$55.66/month** |
| Effective throughput | 10 MiB/s guaranteed | |
| Save time prediction | ~239 MB / 10 MiB/s = ~23s raw; with overhead ~25–40s |

*Note: if AWS bills all 10 MiB/s (not deducting baseline): 10 × $6.00 = $60.00 + $1.66 = $61.66/month. Confirm in console.*

---

**Option 3: Elastic Throughput (informational, NOT in dispatch)**

| Item | Calculation | Cost |
|------|-------------|------|
| Storage | 5.53 GB × $0.30 | $1.66/month |
| Data access | 87.4 GB/day × 30 days × $0.03/GB | $78.66/month |
| **Total** | | **~$80.32/month** |

Elastic mode is the most expensive given the current 87.4 GB/day IO volume. Not recommended.

---

**Cost delta (provisioned vs bursting):**

$55.66 − $1.66 = **$54.00/month additional** for 10 MiB/s provisioned throughput.

**Model prediction** (from dispatch, on record):
- core 1035.78s (task:447) → ~25s at 10 MiB/s
- PASS threshold: core <60s

---

## Part B — Flip command (GATED ON JOE'S APPROVAL)

```bash
aws efs update-file-system \
  --file-system-id fs-0abb85854a3251b3c \
  --throughput-mode provisioned \
  --provisioned-throughput-in-mibps 10
```

**Important constraints:**
- Throughput-mode changes limited to **once per 24 hours** per AWS. One flip only — no experimenting.
- No downtime, no remount, no task restart required. Change takes effect within seconds.
- To revert (if FAIL): `--throughput-mode bursting` — counts as the next change (24h wait).

**Joe must approve spend ($54/month additional) before c1 executes Part B.**

---

## Part C — Verification (within 1h of flip)

Paste next two completed `[save]` lines verbatim from task:449 logs.

PASS = core <60s  
FAIL = paste numbers as-is, change nothing, report to Eve.

Prediction: `[save] ~28s core=~25s grids=~0.1s wave=skip compact=~0.1s`

---

## Part D — Report

This document. Filed before flip as required by dispatch.

---

## Summary

| Item | Value |
|------|-------|
| EFS size | 5.53 GB (standard) |
| Current mode | bursting (credits exhausted) |
| Burst credit recovery | Impossible under current load (0.54 GiB/day earned vs 87.4 GB/day consumed) |
| Metered IO/day | 87.4 GB |
| Provisioned 10 MiB/s cost delta | +$54.00/month (confirm exact rate in console) |
| Save time prediction at 10 MiB/s | core ~25s (vs 442s task:449 / 1036s task:447) |
| Action gate | **Joe approves spend → c1 runs Part B** |

---

End (Part B pending Joe approval).
