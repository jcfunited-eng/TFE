#!/usr/bin/env python3
"""
ArcLoom Live Display + Demo Control Server
Serves real-time FPGA state to iPad/laptop with RUN/END demo buttons.

Usage:
  Run in a Jupyter cell:
    %run loom_display_server.py

  Then open on iPad: http://10.0.0.167:5000

The ArcLoom overlay must be loaded first:
  from pynq import Overlay
  ol = Overlay("/home/xilinx/jupyter_notebooks/ArcLoom/arcloom.bit")
"""

from flask import Flask, jsonify, request, Response
from pynq import Overlay
import threading, time

app = Flask(__name__)

ol = Overlay("/home/xilinx/jupyter_notebooks/ArcLoom/arcloom.bit")
arcloom = ol.arcloom_0

TRIT_NAMES = {0: "null", 1: "+1", 2: "-1", 3: "INV"}
TRIT_COLORS = {0: "#555555", 1: "#00ff88", 2: "#ff4444", 3: "#ff00ff"}


def read_loom():
    """Read loom state from FPGA — 8-trit architecture."""
    decision = arcloom.read(0x00)
    loom_lo = arcloom.read(0x04)

    def trit(val, bit):
        return (val >> bit) & 0x3

    # New layout: loom_state[31:0] =
    #   [5:0]   = decision (3 trits: steer, speed, conf)
    #   [11:6]  = context (3 trits)
    #   [17:12] = momentum (3 trits)
    #   [31:18] = start of right_dist (7 trits visible in 32-bit read)
    dcsn = [trit(loom_lo, 0), trit(loom_lo, 2), trit(loom_lo, 4)]
    ctx  = [trit(loom_lo, 6), trit(loom_lo, 8), trit(loom_lo, 10)]
    mmtm = [trit(loom_lo, 12), trit(loom_lo, 14), trit(loom_lo, 16)]

    steer = trit(decision, 0)
    speed = trit(decision, 2)
    conf = trit(decision, 4)

    struct_lock = bool(decision & (1 << 6))
    safe_mode = bool(decision & (1 << 7))

    return {
        "strands": {
            "context":      {"trits": ctx,   "labels": [TRIT_NAMES[t] for t in ctx],   "colors": [TRIT_COLORS[t] for t in ctx]},
            "momentum":     {"trits": mmtm,  "labels": [TRIT_NAMES[t] for t in mmtm],  "colors": [TRIT_COLORS[t] for t in mmtm]},
            "decision":     {"trits": dcsn,  "labels": [TRIT_NAMES[t] for t in dcsn],  "colors": [TRIT_COLORS[t] for t in dcsn]},
        },
        "output": {
            "steer": TRIT_NAMES[steer],
            "speed": TRIT_NAMES[speed],
            "confidence": TRIT_NAMES[conf],
            "steer_color": TRIT_COLORS[steer],
            "speed_color": TRIT_COLORS[speed],
            "conf_color": TRIT_COLORS[conf],
        },
        "flags": {
            "structural_lock": struct_lock,
            "safe_mode": safe_mode,
        },
    }


def read_sensors():
    """Read raw sensor ADC values and status."""
    reg_28 = arcloom.read(0x28)
    front_adc = reg_28 & 0xFFF
    motor_on = bool(reg_28 & (1 << 12))

    reg_1c = arcloom.read(0x1C)
    left_adc = reg_1c & 0xFFF
    right_adc = (reg_1c >> 16) & 0xFFF

    reg_20 = arcloom.read(0x20)
    familiarity = (reg_20 >> 6) & 0xFF
    motif_count = reg_20 & 0x3F

    reg_24 = arcloom.read(0x24)
    cam_frame_active = bool(reg_24 & (1 << 16))
    cam_frame_count = (reg_24 >> 8) & 0xFF

    return {
        "front": front_adc,
        "left": left_adc,
        "right": right_adc,
        "motor_on": motor_on,
        "familiarity": familiarity,
        "motif_count": motif_count,
        "cam_active": cam_frame_active,
        "cam_frames": cam_frame_count,
    }


# ---- BT encoding for 12-trit (range +/-265720) ----
def bt_encode(n, digits=12):
    trits = []
    neg = n < 0
    n = abs(n)
    for _ in range(digits):
        r = n % 3
        if r == 2:
            trits.append(0b10)
            n += 1
        elif r == 1:
            trits.append(0b01)
        else:
            trits.append(0b00)
        n //= 3
    result = 0
    for i, t in enumerate(trits):
        result |= (t << (2 * i))
    if neg:
        nr = 0
        for i in range(digits):
            t = (result >> (2*i)) & 0x3
            if t == 0b01: t = 0b10
            elif t == 0b10: t = 0b01
            nr |= (t << (2*i))
        return nr
    return result


def bt_decode(val, digits=12):
    n = 0
    power = 1
    for i in range(digits):
        t = (val >> (2*i)) & 0x3
        if t == 0b01: n += power
        elif t == 0b10: n -= power
        power *= 3
    return n


def bt_trits(val, digits=12):
    out = []
    for i in range(digits):
        t = (val >> (2*i)) & 0x3
        if t == 0b01: out.append("+1")
        elif t == 0b10: out.append("-1")
        else: out.append("0")
    return out


# ---- Demo run log ----
demo_log = []
demo_logging = False

# ---- API routes ----

@app.route('/api/loom')
def api_loom():
    try:
        data = read_loom()
        data["sensors"] = read_sensors()

        # Log during demo run
        if demo_logging:
            import time as _t
            demo_log.append({
                "t": _t.time(),
                "front": data["sensors"]["front"],
                "left": data["sensors"]["left"],
                "right": data["sensors"]["right"],
                "steer": data["output"]["steer"],
                "speed": data["output"]["speed"],
                "motor": data["sensors"]["motor_on"],
            })

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route('/api/motor', methods=['POST'])
def api_motor():
    """Enable/disable motors. POST with {"enable": true/false}"""
    global demo_logging, demo_log
    try:
        body = request.get_json(force=True)
        if body.get("enable"):
            arcloom.write(0x10, 0x04)
            demo_log = []
            demo_logging = True
        else:
            arcloom.write(0x10, 0x00)
            demo_logging = False
        return jsonify({"motor_on": body.get("enable", False)})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/demo_log')
def api_demo_log():
    """Return the demo run log."""
    return jsonify({"entries": len(demo_log), "log": demo_log[-500:]})


@app.route('/api/calc')
def api_calc():
    """Hardware calculator — 12-trit balanced ternary on FPGA."""
    a = int(request.args.get('a', 0))
    b = int(request.args.get('b', 0))
    op = request.args.get('op', 'add')

    MAX_VAL = 265720
    if abs(a) > MAX_VAL or abs(b) > MAX_VAL:
        return jsonify({"error": f"Range: -{MAX_VAL} to +{MAX_VAL} (12-trit BT)"})

    a_bt = bt_encode(a)
    b_bt = bt_encode(b)

    if op == 'add':
        arcloom.write(0x04, a_bt & 0xFFFFFF)
        arcloom.write(0x08, b_bt & 0xFFFFFF)
        time.sleep(0.001)
        raw = arcloom.read(0x08)
        result = bt_decode(raw & 0xFFFFFF, 12)
        return jsonify({
            "a": a, "b": b, "op": "+", "result": result,
            "a_bt": bt_trits(a_bt), "b_bt": bt_trits(b_bt),
            "result_bt": bt_trits(raw & 0xFFFFFF),
            "hardware": True
        })

    elif op == 'mul':
        arcloom.write(0x04, a_bt & 0xFFFFFF)
        arcloom.write(0x08, b_bt & 0xFFFFFF)
        time.sleep(0.001)
        raw_lo = arcloom.read(0x0C)
        raw_hi = arcloom.read(0x14) & 0xFFFF
        product_48 = (raw_hi << 32) | raw_lo
        result = bt_decode(product_48, 24)
        return jsonify({
            "a": a, "b": b, "op": "\u00d7", "result": result,
            "a_bt": bt_trits(a_bt), "b_bt": bt_trits(b_bt),
            "result_bt": bt_trits(product_48, 24),
            "hardware": True
        })

    elif op == 'div':
        if b == 0:
            return jsonify({"error": "Division by zero"})
        arcloom.write(0x04, a_bt & 0xFFFFFF)
        arcloom.write(0x08, b_bt & 0xFFFFFF)
        arcloom.write(0x0C, 1 << 16)  # trigger division
        time.sleep(0.1)
        raw = arcloom.read(0x0C)
        # When div_result_ready, 0x0C = {6'd0, 1'b1, div_by_zero, quotient[23:0]}
        if not (raw & (1 << 25)):
            time.sleep(0.2)
            raw = arcloom.read(0x0C)
        q = bt_decode(raw & 0xFFFFFF, 12)
        dbz = bool(raw & (1 << 24))
        # Remainder in register 0x10
        rem_raw = arcloom.read(0x10)
        r = bt_decode(rem_raw & 0xFFFFFF, 12)
        cycles = (rem_raw >> 24) & 0xFF
        if dbz:
            return jsonify({"error": "Division by zero (hardware)"})
        return jsonify({
            "a": a, "b": b, "op": "\u00f7", "result": q, "remainder": r,
            "a_bt": bt_trits(a_bt), "b_bt": bt_trits(b_bt),
            "quotient_bt": bt_trits(raw & 0xFFFFFF),
            "cycles": cycles,
            "hardware": True
        })

    elif op == 'sub':
        neg_b = bt_encode(-b)
        arcloom.write(0x04, a_bt & 0xFFFFFF)
        arcloom.write(0x08, neg_b & 0xFFFFFF)
        time.sleep(0.001)
        raw = arcloom.read(0x08)
        result = bt_decode(raw & 0xFFFFFF, 12)
        return jsonify({
            "a": a, "b": b, "op": "\u2212", "result": result,
            "a_bt": bt_trits(a_bt), "b_bt": bt_trits(b_bt),
            "result_bt": bt_trits(raw & 0xFFFFFF),
            "hardware": True
        })

    elif op == 'pow':
        if b < 0:
            return jsonify({"error": "Negative exponents not supported"})
        if b == 0:
            return jsonify({"a": a, "b": b, "op": "^", "result": 1, "hardware": True})
        acc = a
        for i in range(b - 1):
            acc_bt = bt_encode(acc)
            arcloom.write(0x04, acc_bt & 0xFFFFFF)
            arcloom.write(0x08, a_bt & 0xFFFFFF)
            time.sleep(0.001)
            raw_lo = arcloom.read(0x0C)
            raw_hi = arcloom.read(0x14) & 0xFFFF
            product_48 = (raw_hi << 32) | raw_lo
            acc = bt_decode(product_48, 24)
            if abs(acc) > MAX_VAL:
                return jsonify({"error": f"Overflow at step {i+2}"})
        return jsonify({
            "a": a, "b": b, "op": "^", "result": acc,
            "hardware": True, "iterations": b - 1
        })

    elif op == 'sqrt':
        if a < 0:
            return jsonify({"error": "Square root of negative"})
        if a == 0:
            return jsonify({"a": a, "op": "\u221a", "result": 0, "hardware": True})
        x = max(a // 2, 1)
        for _ in range(30):
            x_bt = bt_encode(x)
            arcloom.write(0x04, a_bt & 0xFFFFFF)
            arcloom.write(0x08, x_bt & 0xFFFFFF)
            arcloom.write(0x0C, 1 << 16)
            time.sleep(0.1)
            raw = arcloom.read(0x0C)
            n_over_x = bt_decode(raw & 0xFFFFFF, 12)
            # (x + n/x)
            arcloom.write(0x04, bt_encode(x) & 0xFFFFFF)
            arcloom.write(0x08, bt_encode(n_over_x) & 0xFFFFFF)
            time.sleep(0.001)
            raw = arcloom.read(0x08)
            total = bt_decode(raw & 0xFFFFFF, 12)
            # / 2
            arcloom.write(0x04, bt_encode(total) & 0xFFFFFF)
            arcloom.write(0x08, bt_encode(2) & 0xFFFFFF)
            arcloom.write(0x0C, 1 << 16)
            time.sleep(0.1)
            raw = arcloom.read(0x0C)
            x_new = bt_decode(raw & 0xFFFFFF, 12)
            if abs(x_new - x) <= 1:
                x = x_new
                break
            x = x_new
        if x * x > a:
            x -= 1
        remainder = a - x * x
        return jsonify({
            "a": a, "op": "\u221a", "result": x, "remainder": remainder,
            "hardware": True
        })

    return jsonify({"error": f"Unknown op: {op}"})


@app.route('/report')
def report():
    return Response(REPORT_HTML, mimetype='text/html')


@app.route('/')
def index():
    return Response(DASHBOARD_HTML, mimetype='text/html')


REPORT_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ArcLoom Demo Report</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #0a0a0a; color: #e0e0e0; font-family: 'Menlo', 'Courier New', monospace; padding: 16px; }
h1 { color: #00ff88; font-size: 1.3em; text-align: center; margin-bottom: 4px; }
.subtitle { color: #666; font-size: 0.65em; text-align: center; margin-bottom: 16px; }
.summary { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
.stat { flex: 1; min-width: 120px; background: #111; border-radius: 8px; padding: 12px; text-align: center; border: 1px solid #222; }
.stat-val { font-size: 1.8em; font-weight: bold; color: #00ff88; }
.stat-label { font-size: 0.6em; color: #888; text-transform: uppercase; margin-top: 4px; }
.chart-box { background: #111; border-radius: 8px; padding: 12px; margin-bottom: 12px; border: 1px solid #222; }
.chart-title { font-size: 0.75em; color: #00ff88; margin-bottom: 8px; font-weight: bold; }
canvas { width: 100%; }
table { width: 100%; border-collapse: collapse; font-size: 0.7em; }
th { background: #1a1a1a; color: #00ff88; padding: 6px 8px; text-align: left; border-bottom: 1px solid #333; }
td { padding: 5px 8px; border-bottom: 1px solid #1a1a1a; }
tr:hover { background: #111; }
.pos { color: #00ff88; } .neg { color: #ff4444; } .nul { color: #555; }
.bad { background: #331a1a; }
.no-data { text-align: center; padding: 40px; color: #444; font-size: 1.2em; }
.correct { color: #00ff88; } .wrong { color: #ff4444; font-weight: bold; }
</style>
</head>
<body>
<h1>ArcLoom Demo Report</h1>
<div class="subtitle" id="subtitle">loading...</div>

<div class="summary" id="summary"></div>

<div class="chart-box">
    <div class="chart-title">SENSOR TRACES</div>
    <canvas id="sensorChart" height="180"></canvas>
</div>

<div class="chart-box">
    <div class="chart-title">DECISION LOG</div>
    <div style="max-height: 400px; overflow-y: auto;">
        <table id="logTable">
            <thead><tr><th>#</th><th>Time</th><th>Front</th><th>Left</th><th>Right</th><th>Speed</th><th>Steer</th><th>Check</th></tr></thead>
            <tbody id="logBody"></tbody>
        </table>
    </div>
</div>

<script>
async function loadReport() {
    const resp = await fetch('/api/demo_log');
    const data = await resp.json();
    const log = data.log;

    if (!log || log.length === 0) {
        document.getElementById('subtitle').textContent = 'No demo data — press RUN DEMO first';
        return;
    }

    const dur = (log[log.length-1].t - log[0].t).toFixed(1);
    const t0 = new Date(log[0].t * 1000);
    document.getElementById('subtitle').textContent =
        log.length + ' samples | ' + dur + 's | ' + t0.toLocaleTimeString();

    // Analyze decisions
    let correct = 0, wrong = 0, neutral = 0;
    const issues = [];
    log.forEach((r, i) => {
        let speedOk = true, steerOk = true;

        // Speed: front > 1500 should be +1 (reverse) or null; front < 500 should be -1 (forward)
        if (r.front > 1500 && r.speed === '-1') { speedOk = false; issues.push(i); }
        if (r.front < 500 && r.speed === '+1') { speedOk = false; issues.push(i); }

        // Steer: left high + right low should be +1 (turn right); opposite = -1
        if (r.left > 800 && r.right < 200 && r.steer === '-1') { steerOk = false; issues.push(i); }
        if (r.right > 800 && r.left < 200 && r.steer === '+1') { steerOk = false; issues.push(i); }

        if (r.speed === 'null' && r.steer === 'null') neutral++;
        else if (speedOk && steerOk) correct++;
        else wrong++;
    });

    const pct = log.length > 0 ? Math.round(correct / (correct + wrong) * 100) : 0;

    document.getElementById('summary').innerHTML = `
        <div class="stat"><div class="stat-val">${log.length}</div><div class="stat-label">Samples</div></div>
        <div class="stat"><div class="stat-val">${dur}s</div><div class="stat-label">Duration</div></div>
        <div class="stat"><div class="stat-val" style="color:${pct>70?'#00ff88':'#ff4444'}">${pct}%</div><div class="stat-label">Correct</div></div>
        <div class="stat"><div class="stat-val" style="color:#ff4444">${wrong}</div><div class="stat-label">Wrong</div></div>
        <div class="stat"><div class="stat-val" style="color:#555">${neutral}</div><div class="stat-label">Neutral</div></div>
    `;

    // Sensor chart
    const canvas = document.getElementById('sensorChart');
    const ctx = canvas.getContext('2d');
    canvas.width = canvas.clientWidth * 2;
    canvas.height = 360;
    const W = canvas.width, H = canvas.height;
    const maxADC = 4095;
    const pad = {l:50, r:10, t:10, b:25};
    const cw = W - pad.l - pad.r, ch = H - pad.t - pad.b;

    // Grid
    ctx.strokeStyle = '#222'; ctx.lineWidth = 1;
    for (let v = 0; v <= 4000; v += 1000) {
        const y = pad.t + ch - (v / maxADC) * ch;
        ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke();
        ctx.fillStyle = '#444'; ctx.font = '18px monospace';
        ctx.fillText(v, 4, y + 5);
    }

    function drawLine(data, color) {
        ctx.strokeStyle = color; ctx.lineWidth = 2; ctx.beginPath();
        data.forEach((v, i) => {
            const x = pad.l + (i / (data.length - 1)) * cw;
            const y = pad.t + ch - (v / maxADC) * ch;
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
        });
        ctx.stroke();
    }
    drawLine(log.map(r => r.front), '#00ff88');
    drawLine(log.map(r => r.left), '#4488ff');
    drawLine(log.map(r => r.right), '#ff8844');

    // Legend
    ctx.font = '20px monospace';
    ctx.fillStyle = '#00ff88'; ctx.fillText('Front', pad.l + 10, pad.t + 20);
    ctx.fillStyle = '#4488ff'; ctx.fillText('Left', pad.l + 90, pad.t + 20);
    ctx.fillStyle = '#ff8844'; ctx.fillText('Right', pad.l + 160, pad.t + 20);

    // Table
    const tbody = document.getElementById('logBody');
    log.forEach((r, i) => {
        const tr = document.createElement('tr');
        const isBad = issues.includes(i);
        if (isBad) tr.className = 'bad';

        const elapsed = (r.t - log[0].t).toFixed(1);
        const fmtTrit = (v) => v === '+1' ? '<span class="pos">+1</span>' : v === '-1' ? '<span class="neg">-1</span>' : '<span class="nul">0</span>';

        let check = '';
        if (isBad) check = '<span class="wrong">BAD</span>';
        else if (r.speed === 'null' && r.steer === 'null') check = '<span class="nul">--</span>';
        else check = '<span class="correct">OK</span>';

        tr.innerHTML = `<td>${i+1}</td><td>${elapsed}s</td><td>${r.front}</td><td>${r.left}</td><td>${r.right}</td><td>${fmtTrit(r.speed)}</td><td>${fmtTrit(r.steer)}</td><td>${check}</td>`;
        tbody.appendChild(tr);
    });
}
loadReport();
</script>
</body>
</html>
"""


DASHBOARD_HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>ArcLoom SPPU</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
    background: #0a0a0a;
    color: #e0e0e0;
    font-family: 'Menlo', 'Courier New', monospace;
    height: 100vh;
    width: 100vw;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
}
.container { padding: 12px; max-width: 600px; margin: 0 auto; }
.header { text-align: center; padding: 8px 0; }
.header h1 { font-size: 1.4em; color: #00ff88; letter-spacing: 0.15em; }
.header .subtitle { font-size: 0.65em; color: #666; margin-top: 2px; }

/* Demo control buttons */
.demo-controls {
    display: flex; gap: 12px; margin: 12px 0;
}
.demo-btn {
    flex: 1; padding: 18px 0; border: none; border-radius: 10px;
    font-size: 1.3em; font-weight: bold; font-family: inherit;
    cursor: pointer; letter-spacing: 0.1em;
    -webkit-tap-highlight-color: transparent;
}
.demo-btn:active { transform: scale(0.97); }
#btn-run { background: #00ff88; color: #000; }
#btn-run:active { background: #00cc66; }
#btn-run.active { background: #004422; color: #00ff88; border: 2px solid #00ff88; }
#btn-end { background: #ff4444; color: #fff; }
#btn-end:active { background: #cc2222; }
#btn-end.disabled { background: #331a1a; color: #664444; }

/* Sensor bars */
.sensor-panel {
    background: #111; border-radius: 8px; padding: 10px 12px;
    margin: 8px 0; border: 1px solid #222;
}
.sensor-row {
    display: flex; align-items: center; margin: 6px 0; gap: 8px;
}
.sensor-label { width: 55px; font-size: 0.7em; color: #888; text-transform: uppercase; }
.sensor-bar-bg {
    flex: 1; height: 16px; background: #1a1a1a; border-radius: 8px;
    overflow: hidden; position: relative;
}
.sensor-bar {
    height: 100%; border-radius: 8px; transition: width 0.15s, background 0.15s;
}
.sensor-val { width: 45px; text-align: right; font-size: 0.7em; color: #aaa; }
.sensor-status {
    display: flex; justify-content: space-between; margin-top: 8px;
    font-size: 0.6em; color: #666;
}

/* Loom grid */
.loom-grid { margin: 8px 0; }
.strand-row {
    display: flex; align-items: center; gap: 6px;
    padding: 5px 8px; margin: 3px 0;
    background: #111; border-radius: 6px;
    border-left: 3px solid #333; transition: border-color 0.15s;
}
.strand-row.active { border-left-color: #00ff88; }
.strand-row.negative { border-left-color: #ff4444; }
.strand-label { width: 90px; font-size: 0.65em; color: #888; text-transform: uppercase; }
.trits { display: flex; gap: 5px; flex: 1; }
.trit {
    width: 36px; height: 36px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.8em; font-weight: bold; transition: all 0.15s;
    border: 2px solid transparent;
}
.trit.pos  { background: #00ff88; color: #000; border-color: #00cc66; }
.trit.neg  { background: #ff4444; color: #fff; border-color: #cc2222; }
.trit.null { background: #2a2a2a; color: #555; border-color: #333; }

/* Output panel */
.output-panel {
    display: flex; justify-content: space-around; padding: 10px;
    background: #111; border-radius: 8px; border: 1px solid #222;
    margin: 8px 0;
}
.output-item { text-align: center; }
.output-label { font-size: 0.6em; color: #666; text-transform: uppercase; margin-bottom: 3px; }
.output-value { font-size: 1.6em; font-weight: bold; }

/* Calculator */
.calc-panel {
    margin-top: 12px; padding: 12px;
    background: #111; border-radius: 8px; border: 1px solid #222;
}
.calc-title { text-align: center; font-size: 0.8em; color: #00ff88; font-weight: bold; margin-bottom: 8px; }
.calc-display {
    background: #0a0a0a; border: 1px solid #222; border-radius: 6px;
    padding: 10px 14px; margin-bottom: 10px;
}
#calc-expr { font-size: 0.7em; color: #555; text-align: right; }
#calc-value { font-size: 2em; color: #00ff88; text-align: right; font-weight: bold; }
#calc-detail { font-size: 0.5em; color: #444; text-align: right; margin-top: 2px; }
.cb {
    padding: 12px 0; border: none; border-radius: 6px;
    font-size: 1.1em; font-family: inherit; font-weight: bold;
    cursor: pointer; -webkit-tap-highlight-color: transparent;
}
.cb:active { transform: scale(0.95); }
.cb-num { background: #1a1a1a; color: #e0e0e0; }
.cb-op  { background: #1a3320; color: #00ff88; }
.cb-fn  { background: #1a1a2a; color: #8888ff; }
.cb-eq  { background: #00ff88; color: #000; }
.cb-clear { background: #331a1a; color: #ff4444; }

.status-bar { text-align: center; font-size: 0.55em; color: #333; padding: 8px; }
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>ArcLoom SPPU</h1>
        <div class="subtitle">Ternary Structural Perception &mdash; Live Hardware</div>
    </div>

    <!-- DEMO CONTROLS -->
    <div class="demo-controls">
        <button class="demo-btn" id="btn-run" onclick="startDemo()">RUN DEMO</button>
        <button class="demo-btn disabled" id="btn-end" onclick="endDemo()">END DEMO</button>
    </div>

    <!-- SENSOR BARS -->
    <div class="sensor-panel">
        <div class="sensor-row">
            <span class="sensor-label">Front</span>
            <div class="sensor-bar-bg"><div class="sensor-bar" id="bar-front" style="width:0%;background:#00ff88;"></div></div>
            <span class="sensor-val" id="val-front">0</span>
        </div>
        <div class="sensor-row">
            <span class="sensor-label">Left</span>
            <div class="sensor-bar-bg"><div class="sensor-bar" id="bar-left" style="width:0%;background:#4488ff;"></div></div>
            <span class="sensor-val" id="val-left">0</span>
        </div>
        <div class="sensor-row">
            <span class="sensor-label">Right</span>
            <div class="sensor-bar-bg"><div class="sensor-bar" id="bar-right" style="width:0%;background:#ff8844;"></div></div>
            <span class="sensor-val" id="val-right">0</span>
        </div>
        <div class="sensor-status">
            <span>Familiarity: <b id="val-fam">0</b></span>
            <span>Motifs: <b id="val-motifs">0</b></span>
            <span>Camera: <b id="val-cam">OFF</b></span>
            <span id="motor-status" style="color:#ff4444;">MOTORS OFF</span>
        </div>
    </div>

    <!-- LOOM STATE -->
    <div class="loom-grid" id="loom-grid"></div>

    <!-- DECISION OUTPUT -->
    <div class="output-panel">
        <div class="output-item">
            <div class="output-label">Steer</div>
            <div class="output-value" id="out-steer">--</div>
        </div>
        <div class="output-item">
            <div class="output-label">Speed</div>
            <div class="output-value" id="out-speed">--</div>
        </div>
        <div class="output-item">
            <div class="output-label">Conf</div>
            <div class="output-value" id="out-conf">--</div>
        </div>
    </div>

    <!-- CALCULATOR -->
    <div class="calc-panel">
        <div class="calc-title">HARDWARE CALCULATOR &mdash; 12-TRIT (&plusmn;265,720)</div>
        <div class="calc-display">
            <div id="calc-expr"></div>
            <div id="calc-value">0</div>
            <div id="calc-detail"></div>
        </div>
        <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:5px;">
            <button class="cb cb-fn" onclick="calcBtn('sqrt')">&#8730;</button>
            <button class="cb cb-fn" onclick="calcBtn('pow')">x<sup>y</sup></button>
            <button class="cb cb-fn" onclick="calcBtn('negate')">&#177;</button>
            <button class="cb cb-clear" onclick="calcBtn('clear')">C</button>
            <button class="cb cb-num" onclick="calcBtn('7')">7</button>
            <button class="cb cb-num" onclick="calcBtn('8')">8</button>
            <button class="cb cb-num" onclick="calcBtn('9')">9</button>
            <button class="cb cb-op" onclick="calcBtn('div')">&#247;</button>
            <button class="cb cb-num" onclick="calcBtn('4')">4</button>
            <button class="cb cb-num" onclick="calcBtn('5')">5</button>
            <button class="cb cb-num" onclick="calcBtn('6')">6</button>
            <button class="cb cb-op" onclick="calcBtn('mul')">&#215;</button>
            <button class="cb cb-num" onclick="calcBtn('1')">1</button>
            <button class="cb cb-num" onclick="calcBtn('2')">2</button>
            <button class="cb cb-num" onclick="calcBtn('3')">3</button>
            <button class="cb cb-op" onclick="calcBtn('sub')">&#8722;</button>
            <button class="cb cb-num" onclick="calcBtn('0')">0</button>
            <button class="cb cb-num" onclick="calcBtn('back')">&#9003;</button>
            <button class="cb cb-eq" onclick="calcBtn('eq')">=</button>
            <button class="cb cb-op" onclick="calcBtn('add')">+</button>
        </div>
    </div>

    <div class="status-bar" id="status">connecting...</div>
</div>

<script>
// ---- Demo control ----
let demoRunning = false;

async function startDemo() {
    await fetch('/api/motor', {method:'POST', body:JSON.stringify({enable:true})});
    demoRunning = true;
    document.getElementById('btn-run').classList.add('active');
    document.getElementById('btn-end').classList.remove('disabled');
}

async function endDemo() {
    await fetch('/api/motor', {method:'POST', body:JSON.stringify({enable:false})});
    demoRunning = false;
    document.getElementById('btn-run').classList.remove('active');
    document.getElementById('btn-end').classList.add('disabled');
}

// ---- Loom display ----
const STRAND_ORDER = [
    'context', 'momentum', 'decision'
];
const STRAND_LABELS = {
    context:'CONTEXT', momentum:'MOMENTUM', decision:'DECISION'
};
const TRIT_CLASS = {1:'pos', 2:'neg', 0:'null', 3:'inv'};

const grid = document.getElementById('loom-grid');
STRAND_ORDER.forEach(name => {
    const row = document.createElement('div');
    row.className = 'strand-row'; row.id = 'strand-' + name;
    const label = document.createElement('div');
    label.className = 'strand-label'; label.textContent = STRAND_LABELS[name];
    row.appendChild(label);
    const trits = document.createElement('div');
    trits.className = 'trits';
    for (let i = 0; i < 3; i++) {
        const t = document.createElement('div');
        t.className = 'trit null'; t.id = 'trit-' + name + '-' + i; t.textContent = '0';
        trits.appendChild(t);
    }
    row.appendChild(trits);
    grid.appendChild(row);
});

async function poll() {
    try {
        const resp = await fetch('/api/loom');
        const data = await resp.json();

        // Strands
        STRAND_ORDER.forEach(name => {
            const strand = data.strands[name];
            const row = document.getElementById('strand-' + name);
            const hasPos = strand.trits.some(t => t === 1);
            const hasNeg = strand.trits.some(t => t === 2);
            row.className = 'strand-row' + (hasPos ? ' active' : hasNeg ? ' negative' : '');
            strand.trits.forEach((t, i) => {
                const el = document.getElementById('trit-' + name + '-' + i);
                el.className = 'trit ' + TRIT_CLASS[t];
                el.textContent = strand.labels[i];
            });
        });

        // Outputs
        document.getElementById('out-steer').textContent = data.output.steer;
        document.getElementById('out-steer').style.color = data.output.steer_color;
        document.getElementById('out-speed').textContent = data.output.speed;
        document.getElementById('out-speed').style.color = data.output.speed_color;
        document.getElementById('out-conf').textContent = data.output.confidence;
        document.getElementById('out-conf').style.color = data.output.conf_color;

        // Sensors
        const s = data.sensors;
        const pct = v => Math.min(100, (v / 4095) * 100);
        const barColor = v => v > 2000 ? '#ff4444' : v > 1000 ? '#ffaa00' : '#00ff88';

        document.getElementById('bar-front').style.width = pct(s.front) + '%';
        document.getElementById('bar-front').style.background = barColor(s.front);
        document.getElementById('val-front').textContent = s.front;

        document.getElementById('bar-left').style.width = pct(s.left) + '%';
        document.getElementById('bar-left').style.background = barColor(s.left);
        document.getElementById('val-left').textContent = s.left;

        document.getElementById('bar-right').style.width = pct(s.right) + '%';
        document.getElementById('bar-right').style.background = barColor(s.right);
        document.getElementById('val-right').textContent = s.right;

        document.getElementById('val-fam').textContent = s.familiarity;
        document.getElementById('val-motifs').textContent = s.motif_count;
        document.getElementById('val-cam').textContent = s.cam_active ? 'ACTIVE (' + s.cam_frames + ')' : 'OFF';

        const mstat = document.getElementById('motor-status');
        mstat.textContent = s.motor_on ? 'MOTORS ON' : 'MOTORS OFF';
        mstat.style.color = s.motor_on ? '#00ff88' : '#ff4444';

        document.getElementById('status').textContent =
            'LIVE | ' + new Date().toLocaleTimeString();

    } catch (e) {
        document.getElementById('status').textContent = 'connection error';
    }
}

setInterval(poll, 500);  // 2Hz — prevent AXI bus crash from combinational output glitches
poll();

// ---- Calculator ----
let CS = {input:'0', opA:null, op:null, fresh:true};
const OPS = {add:'+', sub:'\u2212', mul:'\u00d7', div:'\u00f7', pow:'^', sqrt:'\u221a'};

function calcUpdate() {
    document.getElementById('calc-value').textContent = CS.input;
    const expr = document.getElementById('calc-expr');
    expr.textContent = (CS.opA !== null && CS.op) ? CS.opA + ' ' + (OPS[CS.op]||CS.op) : '';
}

async function calcExec(a, b, op) {
    const vel = document.getElementById('calc-value');
    vel.textContent = '...'; vel.style.color = '#888';
    document.getElementById('calc-detail').textContent = '';
    try {
        const r = await (await fetch('/api/calc?a='+a+'&b='+b+'&op='+op)).json();
        if (r.error) {
            vel.textContent = 'ERR'; vel.style.color = '#ff4444';
            document.getElementById('calc-detail').textContent = r.error;
            CS.input = '0'; CS.fresh = true; return;
        }
        let disp = '' + r.result;
        if (r.remainder) disp += ' R ' + r.remainder;
        vel.textContent = disp; vel.style.color = '#00ff88';
        document.getElementById('calc-detail').textContent = 'FPGA silicon' + (r.cycles ? ' | ' + r.cycles + ' folds' : '');
        CS.input = '' + r.result; CS.opA = null; CS.op = null; CS.fresh = true;
    } catch(e) {
        vel.textContent = 'ERR'; vel.style.color = '#ff4444';
        CS.input = '0'; CS.fresh = true;
    }
}

function calcBtn(key) {
    if (key >= '0' && key <= '9') {
        if (CS.fresh) { CS.input = key; CS.fresh = false; }
        else { if (CS.input.replace('-','').length >= 6) return; CS.input = CS.input === '0' ? key : CS.input + key; }
        calcUpdate(); return;
    }
    if (key === 'back') { if (CS.fresh) return; CS.input = CS.input.length > 1 ? CS.input.slice(0,-1) : '0'; calcUpdate(); return; }
    if (key === 'negate') { CS.input = '' + (-(parseInt(CS.input)||0)); calcUpdate(); return; }
    if (key === 'clear') { CS = {input:'0', opA:null, op:null, fresh:true}; document.getElementById('calc-detail').textContent=''; document.getElementById('calc-value').style.color='#00ff88'; calcUpdate(); return; }
    if (key === 'sqrt') { let a = Math.abs(parseInt(CS.input)||0); document.getElementById('calc-expr').textContent = '\u221a'+a; calcExec(a, 0, 'sqrt'); return; }
    if (key === 'add' || key === 'sub' || key === 'mul' || key === 'div' || key === 'pow') {
        CS.opA = parseInt(CS.input) || 0; CS.op = key; CS.fresh = true; calcUpdate(); return;
    }
    if (key === 'eq') {
        if (CS.opA === null || !CS.op) return;
        let a = CS.opA, b = parseInt(CS.input) || 0;
        document.getElementById('calc-expr').textContent = a + ' ' + (OPS[CS.op]||CS.op) + ' ' + b + ' =';
        calcExec(a, b, CS.op); return;
    }
}
calcUpdate();
</script>
</body>
</html>
"""

if __name__ == '__main__':
    print("=" * 50)
    print(" ArcLoom Live Display + Demo Control")
    print(" Open:   http://10.0.0.167:5000")
    print("=" * 50)
    print(" Motors OFF until RUN DEMO pressed")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, threaded=True)
