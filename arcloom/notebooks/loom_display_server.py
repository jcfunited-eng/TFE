#!/usr/bin/env python3
"""
ArcLoom Live Loom State Display Server
Serves real-time FPGA loom state to any browser (iPad, laptop, etc.)

Usage:
  Run in a Jupyter cell:
    %run loom_display_server.py

  Then open on iPad: http://10.0.0.135:5000

The ArcLoom overlay must be loaded first:
  from pynq import Overlay
  ol = Overlay("/home/xilinx/jupyter_notebooks/ArcLoom/arcloom.bit")
"""

from flask import Flask, jsonify, Response
from pynq import Overlay
import threading, time

app = Flask(__name__)

# Always load overlay fresh — ensures FPGA has ArcLoom bitstream
ol = Overlay("/home/xilinx/jupyter_notebooks/ArcLoom/arcloom.bit")

arcloom = ol.arcloom_0

TRIT_NAMES = {0: "null", 1: "+1", 2: "-1", 3: "INV"}
TRIT_COLORS = {0: "#555555", 1: "#00ff88", 2: "#ff4444", 3: "#ff00ff"}

def read_loom():
    """Read full loom state from FPGA."""
    decision = arcloom.read(0x00)
    loom_lo = arcloom.read(0x04)
    loom_hi = arcloom.read(0x0C)

    def trit(val, bit):
        return (val >> bit) & 0x3

    # Distance strand (3 trits)
    dist = [trit(loom_lo, 0), trit(loom_lo, 2), trit(loom_lo, 4)]
    # Direction strand (3 trits)
    dirn = [trit(loom_lo, 6), trit(loom_lo, 8), trit(loom_lo, 10)]
    # Acceleration strand (3 trits)
    accl = [trit(loom_lo, 12), trit(loom_lo, 14), trit(loom_lo, 16)]
    # Camera edge strand (3 trits)
    cedge = [trit(loom_lo, 18), trit(loom_lo, 20), trit(loom_lo, 22)]
    # Camera motion strand (3 trits)
    cmot = [trit(loom_lo, 24), trit(loom_lo, 26), trit(loom_lo, 28)]
    # Context strand (3 trits)
    ctx = [trit(loom_lo, 30), trit(loom_hi >> 16, 0), trit(loom_hi >> 16, 2)]
    # Momentum strand (3 trits)
    mmtm = [trit(loom_hi >> 16, 4), trit(loom_hi >> 16, 6), trit(loom_hi >> 16, 8)]
    # Decision strand (3 trits)
    dcsn = [trit(loom_hi >> 16, 10), trit(loom_hi >> 16, 12), trit(loom_hi >> 16, 14)]

    steer = trit(decision, 0)
    speed = trit(decision, 2)
    conf = trit(decision, 4)

    # Status flags
    struct_lock = bool(decision & (1 << 6))
    safe_mode = bool(decision & (1 << 7))

    return {
        "strands": {
            "distance":     {"trits": dist,  "labels": [TRIT_NAMES[t] for t in dist],  "colors": [TRIT_COLORS[t] for t in dist]},
            "direction":    {"trits": dirn,  "labels": [TRIT_NAMES[t] for t in dirn],  "colors": [TRIT_COLORS[t] for t in dirn]},
            "acceleration": {"trits": accl,  "labels": [TRIT_NAMES[t] for t in accl],  "colors": [TRIT_COLORS[t] for t in accl]},
            "cam_edge":     {"trits": cedge, "labels": [TRIT_NAMES[t] for t in cedge], "colors": [TRIT_COLORS[t] for t in cedge]},
            "cam_motion":   {"trits": cmot,  "labels": [TRIT_NAMES[t] for t in cmot],  "colors": [TRIT_COLORS[t] for t in cmot]},
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
        "raw": {
            "decision_reg": f"0x{decision:08X}",
            "loom_lo": f"0x{loom_lo:08X}",
            "loom_hi": f"0x{(loom_hi >> 16) & 0xFFFF:04X}",
        }
    }


def bt_encode(n, digits=4):
    """Encode integer to balanced ternary."""
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

def bt_decode(val, digits=4):
    """Decode balanced ternary to integer."""
    n = 0
    power = 1
    for i in range(digits):
        t = (val >> (2*i)) & 0x3
        if t == 0b01: n += power
        elif t == 0b10: n -= power
        power *= 3
    return n

def bt_trits(val, digits=4):
    """Get trit list for display."""
    out = []
    for i in range(digits):
        t = (val >> (2*i)) & 0x3
        if t == 0b01: out.append("+1")
        elif t == 0b10: out.append("-1")
        else: out.append("0")
    return out


@app.route('/api/loom')
def api_loom():
    return jsonify(read_loom())


@app.route('/api/calc')
def api_calc():
    """Hardware calculator — sends math to FPGA, returns result."""
    from flask import request
    a = int(request.args.get('a', 0))
    b = int(request.args.get('b', 0))
    op = request.args.get('op', 'add')

    # Range check: 4-trit BT = -40 to +40
    if abs(a) > 40 or abs(b) > 40:
        return jsonify({"error": "Range: -40 to +40 (4-trit balanced ternary)"})

    a_bt = bt_encode(a)
    b_bt = bt_encode(b)

    import time

    if op == 'add':
        arcloom.write(0x04, a_bt)
        arcloom.write(0x08, b_bt)
        time.sleep(0.01)
        raw = arcloom.read(0x08)
        result = bt_decode(raw & 0xFF)
        return jsonify({
            "a": a, "b": b, "op": "+", "result": result,
            "a_bt": bt_trits(a_bt), "b_bt": bt_trits(b_bt),
            "result_bt": bt_trits(raw & 0xFF),
            "hardware": True
        })

    elif op == 'mul':
        arcloom.write(0x04, a_bt)
        arcloom.write(0x08, b_bt)
        time.sleep(0.01)
        raw = arcloom.read(0x0C)
        result = bt_decode(raw & 0xFFFF, 8)
        return jsonify({
            "a": a, "b": b, "op": "\u00d7", "result": result,
            "a_bt": bt_trits(a_bt), "b_bt": bt_trits(b_bt),
            "result_bt": bt_trits(raw & 0xFFFF, 8),
            "hardware": True
        })

    elif op == 'div':
        if b == 0:
            return jsonify({"error": "Division by zero"})
        arcloom.write(0x04, a_bt)
        arcloom.write(0x08, b_bt)
        arcloom.write(0x0C, 1 << 16)  # trigger division
        time.sleep(0.05)
        raw = arcloom.read(0x0C)
        q = bt_decode(raw & 0xFF)
        r = bt_decode((raw >> 8) & 0xFF)
        cycles = (raw >> 17) & 0x3F
        return jsonify({
            "a": a, "b": b, "op": "\u00f7", "result": q, "remainder": r,
            "a_bt": bt_trits(a_bt), "b_bt": bt_trits(b_bt),
            "quotient_bt": bt_trits(raw & 0xFF),
            "remainder_bt": bt_trits((raw >> 8) & 0xFF),
            "cycles": cycles,
            "hardware": True
        })

    elif op == 'sub':
        # Subtraction: a + (-b) on FPGA
        neg_b = bt_encode(-b)
        arcloom.write(0x04, a_bt)
        arcloom.write(0x08, neg_b)
        time.sleep(0.01)
        raw = arcloom.read(0x08)
        result = bt_decode(raw & 0xFF)
        return jsonify({
            "a": a, "b": b, "op": "\u2212", "result": result,
            "a_bt": bt_trits(a_bt), "b_bt": bt_trits(b_bt),
            "result_bt": bt_trits(raw & 0xFF),
            "hardware": True
        })

    elif op == 'pow':
        # Power: repeated multiply on FPGA. a^b where b >= 0.
        if b < 0:
            return jsonify({"error": "Negative exponents not supported (integer only)"})
        if b == 0:
            return jsonify({
                "a": a, "b": b, "op": "^", "result": 1,
                "a_bt": bt_trits(a_bt), "b_bt": bt_trits(b_bt),
                "result_bt": bt_trits(bt_encode(1)),
                "hardware": True, "iterations": 0
            })
        acc = a
        for i in range(b - 1):
            acc_bt = bt_encode(acc)
            arcloom.write(0x04, acc_bt)
            arcloom.write(0x08, a_bt)
            time.sleep(0.01)
            raw = arcloom.read(0x0C)
            acc = bt_decode(raw & 0xFFFF, 8)
            if abs(acc) > 9841:  # 8-trit BT max
                return jsonify({"error": f"Overflow at iteration {i+2} (8-trit BT max \u00b19841)"})
        return jsonify({
            "a": a, "b": b, "op": "^", "result": acc,
            "a_bt": bt_trits(a_bt), "b_bt": bt_trits(b_bt),
            "result_bt": bt_trits(bt_encode(acc, 8), 8),
            "hardware": True, "iterations": b - 1
        })

    elif op == 'sqrt':
        # Square root via Newton iteration on FPGA: x = (x + N/x) / 2
        if a < 0:
            return jsonify({"error": "Square root of negative number"})
        if a == 0:
            return jsonify({
                "a": a, "b": 0, "op": "\u221a", "result": 0,
                "a_bt": bt_trits(a_bt), "result_bt": bt_trits(0),
                "hardware": True, "iterations": 0
            })
        # Initial guess: a // 2 or 1, whichever is larger
        x = max(a // 2, 1)
        iterations = 0
        for _ in range(20):  # max 20 iterations
            # N / x on FPGA
            x_bt = bt_encode(x)
            arcloom.write(0x04, a_bt)
            arcloom.write(0x08, x_bt)
            arcloom.write(0x0C, 1 << 16)  # trigger division
            time.sleep(0.05)
            raw = arcloom.read(0x0C)
            n_over_x = bt_decode(raw & 0xFF)

            # (x + N/x) on FPGA
            sum_bt_a = bt_encode(x)
            sum_bt_b = bt_encode(n_over_x)
            arcloom.write(0x04, sum_bt_a)
            arcloom.write(0x08, sum_bt_b)
            time.sleep(0.01)
            raw = arcloom.read(0x08)
            total = bt_decode(raw & 0xFF)

            # / 2 on FPGA
            total_bt = bt_encode(total)
            two_bt = bt_encode(2)
            arcloom.write(0x04, total_bt)
            arcloom.write(0x08, two_bt)
            arcloom.write(0x0C, 1 << 16)
            time.sleep(0.05)
            raw = arcloom.read(0x0C)
            x_new = bt_decode(raw & 0xFF)

            iterations += 1
            if x_new == x or x_new == x - 1 or x_new == x + 1:
                x = x_new
                break
            x = x_new

        # Pick floor sqrt: largest integer where i*i <= a
        if x * x > a:
            x -= 1
        remainder = a - x * x
        return jsonify({
            "a": a, "b": 0, "op": "\u221a", "result": x, "remainder": remainder,
            "a_bt": bt_trits(a_bt),
            "result_bt": bt_trits(bt_encode(x)),
            "hardware": True, "iterations": iterations
        })

    return jsonify({"error": f"Unknown operation: {op}"})


@app.route('/')
def index():
    return Response(DASHBOARD_HTML, mimetype='text/html')


DASHBOARD_HTML = """<!DOCTYPE html>
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
    overflow: hidden;
    height: 100vh;
    width: 100vw;
}
.container {
    display: flex;
    flex-direction: column;
    height: 100vh;
    padding: 12px;
    gap: 8px;
}
.header {
    text-align: center;
    padding: 8px 0;
}
.header h1 {
    font-size: 1.4em;
    color: #00ff88;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}
.header .subtitle {
    font-size: 0.7em;
    color: #666;
    margin-top: 2px;
}
.loom-grid {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 4px;
    justify-content: center;
}
.strand-row {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 8px;
    background: #111;
    border-radius: 6px;
    border-left: 3px solid #333;
    transition: border-color 0.15s;
}
.strand-row.active { border-left-color: #00ff88; }
.strand-row.negative { border-left-color: #ff4444; }
.strand-label {
    width: 100px;
    font-size: 0.72em;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    flex-shrink: 0;
}
.trits {
    display: flex;
    gap: 6px;
    flex: 1;
}
.trit {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9em;
    font-weight: bold;
    transition: all 0.15s;
    border: 2px solid transparent;
}
.trit.pos  { background: #00ff88; color: #000; border-color: #00cc66; }
.trit.neg  { background: #ff4444; color: #fff; border-color: #cc2222; }
.trit.null { background: #2a2a2a; color: #555; border-color: #333; }
.trit.inv  { background: #ff00ff; color: #fff; }

.output-panel {
    display: flex;
    justify-content: space-around;
    padding: 12px;
    background: #111;
    border-radius: 8px;
    border: 1px solid #222;
}
.output-item {
    text-align: center;
}
.output-label {
    font-size: 0.65em;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 4px;
}
.output-value {
    font-size: 1.8em;
    font-weight: bold;
    transition: color 0.15s;
}
.flags {
    display: flex;
    justify-content: center;
    gap: 20px;
    padding: 6px;
    font-size: 0.7em;
}
.flag { padding: 3px 10px; border-radius: 4px; }
.flag.on  { background: #ff4444; color: #fff; }
.flag.off { background: #1a1a1a; color: #444; }
.status-bar {
    text-align: center;
    font-size: 0.6em;
    color: #333;
    padding: 4px;
}
/* Calculator buttons */
.cb {
    padding: 14px 0;
    border: none;
    border-radius: 6px;
    font-size: 1.2em;
    font-family: 'Menlo', 'Courier New', monospace;
    font-weight: bold;
    cursor: pointer;
    transition: background 0.1s, transform 0.05s;
    -webkit-tap-highlight-color: transparent;
    user-select: none;
}
.cb:active { transform: scale(0.95); }
.cb-num { background: #1a1a1a; color: #e0e0e0; }
.cb-num:active { background: #2a2a2a; }
.cb-op  { background: #1a3320; color: #00ff88; }
.cb-op:active { background: #264d33; }
.cb-fn  { background: #1a1a2a; color: #8888ff; }
.cb-fn:active { background: #2a2a3a; }
.cb-eq  { background: #00ff88; color: #000; }
.cb-eq:active { background: #00cc66; }
.cb-clear { background: #331a1a; color: #ff4444; }
.cb-clear:active { background: #4d2626; }
/* BT trit chips in display */
.bt-chip {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    font-size: 0.55em;
    font-weight: bold;
}
.bt-pos  { background: #00ff88; color: #000; }
.bt-neg  { background: #ff4444; color: #fff; }
.bt-null { background: #2a2a2a; color: #555; }
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>ArcLoom SPPU</h1>
        <div class="subtitle">8-Strand Ternary Loom &mdash; Live Hardware State</div>
    </div>

    <div class="loom-grid" id="loom-grid"></div>

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
            <div class="output-label">Confidence</div>
            <div class="output-value" id="out-conf">--</div>
        </div>
    </div>

    <div class="flags">
        <span class="flag off" id="flag-lock">STRUCTURAL LOCK</span>
        <span class="flag off" id="flag-safe">SAFE MODE</span>
    </div>

    <div class="status-bar" id="status">connecting...</div>

    <!-- Scientific Calculator -->
    <div id="calc-panel" style="margin-top:12px; padding:12px; background:#111; border-radius:8px; border:1px solid #222;">
        <div style="text-align:center; margin-bottom:10px;">
            <div style="font-size:0.9em; color:#00ff88; font-weight:bold; letter-spacing:0.1em;">HARDWARE CALCULATOR</div>
            <div style="font-size:0.5em; color:#555; margin-top:2px;">All arithmetic executes on FPGA silicon (XC7Z020) via balanced ternary MathLoom</div>
        </div>

        <!-- Display -->
        <div id="calc-display" style="background:#0a0a0a; border:1px solid #222; border-radius:6px; padding:10px 14px; margin-bottom:10px; min-height:80px;">
            <div id="calc-expr" style="font-size:0.7em; color:#555; text-align:right; min-height:1.2em;"></div>
            <div id="calc-value" style="font-size:2.2em; color:#00ff88; text-align:right; font-weight:bold; font-family:monospace;">0</div>
            <div id="calc-trits" style="display:flex; justify-content:flex-end; gap:4px; margin-top:4px; min-height:22px;"></div>
            <div id="calc-detail" style="font-size:0.55em; color:#444; text-align:right; margin-top:2px;"></div>
        </div>

        <!-- Button grid -->
        <div style="display:grid; grid-template-columns:repeat(4,1fr); gap:6px;">
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

        <div style="text-align:center; margin-top:8px; font-size:0.45em; color:#333;">Range: &minus;40 to +40 (4-trit BT) &bull; Results computed in hardware, not software</div>
    </div>
</div>

<script>
const STRAND_ORDER = [
    'distance', 'direction', 'acceleration',
    'cam_edge', 'cam_motion',
    'context', 'momentum', 'decision'
];

const STRAND_LABELS = {
    distance: 'DISTANCE',
    direction: 'DIRECTION',
    acceleration: 'ACCEL',
    cam_edge: 'CAM EDGE',
    cam_motion: 'CAM MOTION',
    context: 'CONTEXT',
    momentum: 'MOMENTUM',
    decision: 'DECISION'
};

const TRIT_CLASS = {1: 'pos', 2: 'neg', 0: 'null', 3: 'inv'};

// Build grid
const grid = document.getElementById('loom-grid');
STRAND_ORDER.forEach(name => {
    const row = document.createElement('div');
    row.className = 'strand-row';
    row.id = 'strand-' + name;

    const label = document.createElement('div');
    label.className = 'strand-label';
    label.textContent = STRAND_LABELS[name];
    row.appendChild(label);

    const trits = document.createElement('div');
    trits.className = 'trits';
    for (let i = 0; i < 3; i++) {
        const t = document.createElement('div');
        t.className = 'trit null';
        t.id = 'trit-' + name + '-' + i;
        t.textContent = '0';
        trits.appendChild(t);
    }
    row.appendChild(trits);
    grid.appendChild(row);
});

let errorCount = 0;

async function poll() {
    try {
        const resp = await fetch('/api/loom');
        const data = await resp.json();
        errorCount = 0;

        // Update strands
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

        // Update outputs
        document.getElementById('out-steer').textContent = data.output.steer;
        document.getElementById('out-steer').style.color = data.output.steer_color;
        document.getElementById('out-speed').textContent = data.output.speed;
        document.getElementById('out-speed').style.color = data.output.speed_color;
        document.getElementById('out-conf').textContent = data.output.confidence;
        document.getElementById('out-conf').style.color = data.output.conf_color;

        // Update flags
        const lockEl = document.getElementById('flag-lock');
        lockEl.className = 'flag ' + (data.flags.structural_lock ? 'on' : 'off');
        const safeEl = document.getElementById('flag-safe');
        safeEl.className = 'flag ' + (data.flags.safe_mode ? 'on' : 'off');

        document.getElementById('status').textContent =
            'LIVE | ' + data.raw.decision_reg + ' | ' + new Date().toLocaleTimeString();

    } catch (e) {
        errorCount++;
        document.getElementById('status').textContent = 'connection error (' + errorCount + ')';
    }
}

setInterval(poll, 150);  // ~7 fps
poll();

// ---- Calculator state machine ----
let calcState = {
    input: '0',        // current number being typed
    operandA: null,    // first operand (after operator pressed)
    operator: null,    // pending operator
    fresh: true,       // true = next digit replaces display
    lastResult: null   // for chaining
};

const OP_SYMBOLS = {add:'+', sub:'\u2212', mul:'\u00d7', div:'\u00f7', pow:'^', sqrt:'\u221a'};

function calcUpdate() {
    document.getElementById('calc-value').textContent = calcState.input;
    // Show expression line
    const exprEl = document.getElementById('calc-expr');
    if (calcState.operandA !== null && calcState.operator) {
        exprEl.textContent = calcState.operandA + ' ' + (OP_SYMBOLS[calcState.operator]||calcState.operator);
    } else {
        exprEl.textContent = '';
    }
}

function renderTrits(trits) {
    if (!trits) return '';
    return trits.map(t => {
        if (t === '+1') return '<span class="bt-chip bt-pos">+1</span>';
        if (t === '-1') return '<span class="bt-chip bt-neg">\u22121</span>';
        return '<span class="bt-chip bt-null">0</span>';
    }).join(' ');
}

async function calcExecute(a, b, op) {
    const valueEl = document.getElementById('calc-value');
    const tritsEl = document.getElementById('calc-trits');
    const detailEl = document.getElementById('calc-detail');

    valueEl.textContent = '...';
    valueEl.style.color = '#888';
    tritsEl.innerHTML = '';
    detailEl.textContent = '';

    try {
        const resp = await fetch('/api/calc?a=' + a + '&b=' + b + '&op=' + op);
        const data = await resp.json();

        if (data.error) {
            valueEl.textContent = 'ERR';
            valueEl.style.color = '#ff4444';
            detailEl.textContent = data.error;
            calcState.input = '0';
            calcState.fresh = true;
            return;
        }

        let display = '' + data.result;
        if (op === 'div' && data.remainder) display += ' R ' + data.remainder;
        if (op === 'sqrt' && data.remainder) display += ' R ' + data.remainder;

        valueEl.textContent = display;
        valueEl.style.color = '#00ff88';

        // Show result trits
        tritsEl.innerHTML = renderTrits(data.result_bt || data.quotient_bt);

        // Detail line
        let detail = '';
        if (op === 'sqrt') {
            detail = '\u221a' + a + ' = ' + data.result + ' | ' + data.iterations + ' Newton steps | FPGA';
        } else if (op === 'pow') {
            detail = a + '^' + b + ' = ' + data.result + ' | ' + (data.iterations||0) + ' multiplies | FPGA';
        } else if (op === 'div') {
            detail = a + '\u00f7' + b + ' = ' + data.result + (data.remainder ? ' R'+data.remainder : '') +
                     ' | ' + data.cycles + ' folds | FPGA';
        } else {
            detail = '[' + (data.a_bt||[]).join(',') + '] ' + data.op +
                     ' [' + (data.b_bt||[]).join(',') + '] = [' + (data.result_bt||[]).join(',') + '] | FPGA';
        }
        detailEl.textContent = detail;

        calcState.input = '' + data.result;
        calcState.lastResult = data.result;
        calcState.operandA = null;
        calcState.operator = null;
        calcState.fresh = true;

    } catch (e) {
        valueEl.textContent = 'ERR';
        valueEl.style.color = '#ff4444';
        detailEl.textContent = e.message;
        calcState.input = '0';
        calcState.fresh = true;
    }
}

function calcBtn(key) {
    // Digits
    if (key >= '0' && key <= '9') {
        if (calcState.fresh) {
            calcState.input = key;
            calcState.fresh = false;
        } else {
            if (calcState.input.replace('-','').length >= 3) return; // max 3 digits (range limit)
            calcState.input = calcState.input === '0' ? key : calcState.input + key;
        }
        calcUpdate();
        return;
    }

    if (key === 'back') {
        if (calcState.fresh) return;
        calcState.input = calcState.input.length > 1 ? calcState.input.slice(0,-1) : '0';
        if (calcState.input === '-') calcState.input = '0';
        calcUpdate();
        return;
    }

    if (key === 'negate') {
        let n = parseInt(calcState.input) || 0;
        calcState.input = '' + (-n);
        calcUpdate();
        return;
    }

    if (key === 'clear') {
        calcState = {input:'0', operandA:null, operator:null, fresh:true, lastResult:null};
        document.getElementById('calc-trits').innerHTML = '';
        document.getElementById('calc-detail').textContent = '';
        document.getElementById('calc-value').style.color = '#00ff88';
        calcUpdate();
        return;
    }

    // sqrt is unary — execute immediately
    if (key === 'sqrt') {
        let a = parseInt(calcState.input) || 0;
        if (a < 0) { a = Math.abs(a); } // sqrt of |a|
        calcState.operandA = null;
        calcState.operator = null;
        document.getElementById('calc-expr').textContent = '\u221a' + a;
        calcExecute(a, 0, 'sqrt');
        return;
    }

    // Binary operators
    if (key === 'add' || key === 'sub' || key === 'mul' || key === 'div' || key === 'pow') {
        // If there's already a pending op, execute it first
        if (calcState.operandA !== null && calcState.operator && !calcState.fresh) {
            // Chain: execute pending, then set new operator
            let a = calcState.operandA;
            let b = parseInt(calcState.input) || 0;
            // We can't easily chain here with async, so just set the new op
        }
        calcState.operandA = parseInt(calcState.input) || 0;
        calcState.operator = key;
        calcState.fresh = true;
        calcUpdate();
        return;
    }

    // Equals
    if (key === 'eq') {
        if (calcState.operandA === null || !calcState.operator) return;
        let a = calcState.operandA;
        let b = parseInt(calcState.input) || 0;
        let op = calcState.operator;
        document.getElementById('calc-expr').textContent = a + ' ' + (OP_SYMBOLS[op]||op) + ' ' + b + ' =';
        calcExecute(a, b, op);
        return;
    }
}

calcUpdate();
</script>
</body>
</html>
"""

if __name__ == '__main__':
    print("=" * 50)
    print(" ArcLoom Live Display")
    print(" Open on iPad: http://10.0.0.135:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, threaded=True)
