#!/usr/bin/env python3
"""
Hardware Weight Derivation — Local (PYNQ) Version
===================================================
Same algorithm as dsf-ai.com/static/hw-derive.html backend.
Runs on PYNQ without cloud dependencies.

Usage:
  python3 hw_derive_local.py --mode ir --csv calibration.csv
  python3 hw_derive_local.py --mode camera --csv turntable.csv --bg-y 45 --bg-edge 2 --bg-u 128

Outputs: Verilog parameters + BSIL thresholds + JSON + DSF profiles

TRADE SECRET — DO NOT DISTRIBUTE
"""

import argparse
import csv
import json
import sys
import os
import time
from typing import Dict, List, Tuple, Any

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))
sys.path.insert(0, PROJECT_ROOT)

import numpy as np
from tools.derive_sppu_weights import (
    build_field_series, run_kernel, dsf_to_coupling_profile,
    derive_bsil_thresholds, format_bsil_thresholds,
    ingest_calibration_table, derive_weights, format_verilog, format_json,
)


def derive_ir(csv_path: str, sensor_names: List[str], sensor_roles: Dict[str, str], label: str):
    """IR distance sensor derivation — delegates to derive_weights."""
    # Parse CSV into calibration table
    cal_table = {}
    with open(csv_path) as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if not row:
                continue
            stim = row[0].strip()
            if stim.lower() == 'inf':
                stim_key = 'inf'
            else:
                stim_key = float(stim)
            readings = []
            for v in row[1:]:
                v = v.strip()
                readings.append(None if v == '' else float(v))
            cal_table[stim_key] = tuple(readings)

    weights, bsil_thresholds, metadata = derive_weights(
        calibration_table=cal_table,
        sensor_names=sensor_names,
        sensor_roles=sensor_roles,
        sensor_label=label,
    )

    verilog = format_verilog(weights, metadata)
    verilog += "\n\n" + format_bsil_thresholds(bsil_thresholds)
    json_str = format_json(weights, metadata)

    return verilog, json_str, metadata.get('dsf_profiles', {}), bsil_thresholds


def derive_camera(csv_path: str, bg_y: int, bg_edge: int, bg_u: int, label: str):
    """Camera vision derivation — same math as the cloud endpoint."""
    # Parse turntable CSV
    samples = []
    with open(csv_path) as f:
        reader = csv.reader(f)
        header = next(reader)
        for row in reader:
            if len(row) < 5:
                continue
            samples.append({
                'sample': int(row[0].strip()),
                'orientation': row[1].strip(),
                'y_mean': int(row[2].strip()),
                'edge_count': int(row[3].strip()),
                'u_mean': int(row[4].strip()),
            })

    print(f"Loaded {len(samples)} turntable samples")
    print(f"Background: Y={bg_y}, Edge={bg_edge}, U={bg_u}")

    # Build calibration table: background as 'inf', samples as numbered rows
    cal_table = {'inf': (float(bg_y), float(bg_edge), float(bg_u))}
    for s in samples:
        cal_table[float(s['sample'])] = (
            float(s['y_mean']),
            float(s['edge_count']),
            float(s['u_mean']),
        )

    feature_names = ['y_mean', 'edge_count', 'u_mean']
    sensor_data = ingest_calibration_table(cal_table)

    # Run kernel on each feature independently
    profiles = {}
    bsil_thresholds = {}
    baselines = {'y_mean': float(bg_y), 'edge_count': float(bg_edge), 'u_mean': float(bg_u)}

    for i, name in enumerate(feature_names):
        key = f'sensor_{i}'
        if key not in sensor_data or not sensor_data[key]:
            print(f"  {name}: no data, skipping")
            continue

        print(f"\n--- {name} ---")
        series = build_field_series(sensor_data[key], name)
        print(f"  Field: {len(series)} points, range [{series.min():.0f}, {series.max():.0f}]")

        kernel_out = run_kernel(series)
        dsf = kernel_out['dsf']
        boundaries = kernel_out['boundaries']
        print(f"  DSF outputs: {len(dsf)}")
        print(f"  Gates: {kernel_out['n_gates']}, boundaries: {len(boundaries)}")

        profile = dsf_to_coupling_profile(dsf)
        profiles[name] = profile

        baseline = baselines[name]
        thresholds = derive_bsil_thresholds(boundaries, baseline)
        bsil_thresholds[name] = thresholds

        print(f"  coupling_strength:   {profile['coupling_strength']:.4f}")
        print(f"  momentum_weight:     {profile['momentum_weight']:.4f}")
        print(f"  uncertainty:         {profile['uncertainty']:.4f}")
        print(f"  breathing_magnitude: {profile['breathing_magnitude']:.4f}")
        print(f"  reversal_rate:       {profile['reversal_rate']:.4f}")

    # Build Verilog output — same math as cloud endpoint
    verilog_lines = []
    verilog_lines.append("// ---- Camera Vision Coupling Weights ----")
    verilog_lines.append(f"// Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    verilog_lines.append(f"// Sensor: {label}")
    verilog_lines.append(f"// Features: {', '.join(feature_names)}")
    verilog_lines.append(f"// Role: structural (vision)")
    verilog_lines.append("")

    for name, profile in profiles.items():
        cs = profile['coupling_strength']
        mw = profile['momentum_weight']
        unc = profile['uncertainty']
        bm = profile['breathing_magnitude']
        rr = profile['reversal_rate']

        raw = cs * (1.0 + bm) * (1.0 - unc * 0.5) * (1.0 - rr * 0.3)
        base_w = int(np.clip(raw * 40, 5, 40))

        conf = 1.0 - unc
        stability = 1.0 - min(bm, 1.0) * 0.5
        conf_w = int(np.clip(conf * stability * 25, 5, 30))

        steer_w = int(np.clip(cs * 10, 0, 15))
        speed_w = int(np.clip(cs * mw * 20, 0, 20))

        baseline = baselines.get(name, 0)
        dz = int(np.clip(unc * 50, 5, 100))

        verilog_lines.append(f"// {name}:")
        verilog_lines.append(f"//   coupling_strength = {cs:.4f}")
        verilog_lines.append(f"//   momentum_weight   = {mw:.4f}")
        verilog_lines.append(f"//   uncertainty        = {unc:.4f}")
        verilog_lines.append(f"//   breathing          = {bm:.4f}")
        verilog_lines.append(f"//   reversal_rate      = {rr:.4f}")
        verilog_lines.append(f"parameter [7:0] BASELINE_{name.upper()} = 8'd{int(baseline)};")
        verilog_lines.append(f"parameter [7:0] DEADZONE_{name.upper()} = 8'd{dz};")
        verilog_lines.append(f"parameter [7:0] W_CONFIDENCE_{name.upper()} = 8'd{conf_w};")
        verilog_lines.append(f"parameter signed [7:0] W_STEER_{name.upper()} = 8'sd{steer_w};")
        verilog_lines.append(f"parameter [7:0] W_SPEED_{name.upper()} = 8'd{speed_w};")
        verilog_lines.append("")

    verilog = "\n".join(verilog_lines)
    verilog += "\n\n" + format_bsil_thresholds(bsil_thresholds)

    # JSON output
    json_out = {
        'sensor_label': label,
        'mode': 'camera_structural',
        'features': feature_names,
        'baselines': baselines,
        'profiles': {k: {kk: round(vv, 4) if isinstance(vv, float) else vv
                         for kk, vv in v.items()} for k, v in profiles.items()},
        'bsil_thresholds': bsil_thresholds,
    }
    json_str = json.dumps(json_out, indent=2, default=str)

    return verilog, json_str, profiles, bsil_thresholds


def main():
    parser = argparse.ArgumentParser(
        description='Hardware Weight Derivation — Local (PYNQ) Version'
    )
    parser.add_argument('--mode', choices=['ir', 'camera'], required=True,
                        help='ir = distance sensors, camera = vision features')
    parser.add_argument('--csv', required=True, help='Calibration CSV file')
    parser.add_argument('--label', default='sensor', help='Sensor label')

    # IR-specific
    parser.add_argument('--names', default='front,left,right',
                        help='Comma-separated sensor names (IR mode)')
    parser.add_argument('--roles', default='front:axial,left:lateral,right:lateral',
                        help='name:role pairs (IR mode)')

    # Camera-specific
    parser.add_argument('--bg-y', type=int, default=45, help='Background Y mean')
    parser.add_argument('--bg-edge', type=int, default=2, help='Background edge count')
    parser.add_argument('--bg-u', type=int, default=128, help='Background U mean')

    # Output
    parser.add_argument('--out-dir', default='.', help='Output directory')

    args = parser.parse_args()

    print("=" * 60)
    print("Hardware Weight Derivation — Local")
    print(f"Mode: {args.mode}")
    print(f"CSV:  {args.csv}")
    print("=" * 60)

    t0 = time.time()

    if args.mode == 'ir':
        names = [n.strip() for n in args.names.split(',')]
        roles = {}
        for pair in args.roles.split(','):
            k, v = pair.strip().split(':')
            roles[k.strip()] = v.strip()

        verilog, json_str, profiles, bsil = derive_ir(
            args.csv, names, roles, args.label
        )
    else:
        verilog, json_str, profiles, bsil = derive_camera(
            args.csv, args.bg_y, args.bg_edge, args.bg_u, args.label
        )

    elapsed = time.time() - t0

    # Write outputs
    v_path = os.path.join(args.out_dir, 'derived_weights.v')
    j_path = os.path.join(args.out_dir, 'derived_weights.json')

    with open(v_path, 'w') as f:
        f.write(verilog)
    with open(j_path, 'w') as f:
        f.write(json_str)

    print("\n" + "=" * 60)
    print("OUTPUT")
    print("=" * 60)
    print(verilog)
    print("\n" + "=" * 60)
    print(f"Verilog: {v_path}")
    print(f"JSON:    {j_path}")
    print(f"Time:    {elapsed:.3f}s")
    print("=" * 60)


if __name__ == '__main__':
    main()
