# ArcLoom Update Protocol — from Codespace to the PYNQ-Z2 robot

Compiled 2026-10-05 from the existing records: `PYNQ_DEPLOYMENT_LESSONS.md`
(lessons #1–41, April–May 2026), `arcloom/scripts/create_block_design.tcl`,
`loom_display_server.py`, and `PYNQ_G1_AUDIT_2026-10-04.md`. Each step names
its source. Nothing in this document was re-run on the board when it was written.

## The shape of the work

1. Change the Verilog in the Codespace (`arcloom/hdl/`).
2. Check it in simulation in the Codespace.
3. Zip the `.v` files and download them to the Windows PC.
4. Build a **fresh** Vivado project from `create_block_design.tcl`.
5. Upload `arcloom.bit` + `arcloom.hwh` to the board through Jupyter.
6. Reboot the board, open the iPad page, and test with the motors off first.
7. Write down what was loaded and what happened.

## Step 1 — Change the source

- Robot design files are in `arcloom/hdl/`. The top module Vivado wraps is
  `arcloom_axi_wrapper` (set in `create_block_design.tcl`).
- Check pin choices against the board's master pin file at
  `docs/pynq-z2_v1.0.xdc (1).zip` before you guess. The Arduino A0 = VAUX1
  mistake lasted weeks because nobody checked it. (Lesson #32)
- Analog XADC pins get `PACKAGE_PIN` only, never `IOSTANDARD`. (Lesson #34)
- Register outputs every clock, or Vivado may delete logic it decides is
  unused. (Lessons #3, #13)

## Step 2 — Simulate before building

A build-upload-test cycle takes hours; a simulation catches the same
mistake in seconds. The April 23 sensor thresholds matched hardware on the
first try because they were simulated first. (Lesson #30)

Current checks, run from the repository root (G1 audit, 10-04):

```bash
t=$(mktemp -d /tmp/arcloom-check.XXXXXX)
iverilog -g2012 -s tb_mathloom_exact -o "$t/exact" arcloom/hdl/arcloom_mathloom.v arcloom/hdl/arcloom_mathloom_alu.v arcloom/hdl/arcloom_mathloom_div.v arcloom/sim/tb_mathloom_exact.v
timeout 45s vvp "$t/exact"
iverilog -g2012 -s tb_mathloom_axi -o "$t/axi" arcloom/sim/tb_mathloom_axi.v arcloom/hdl/arcloom_axi_wrapper.v arcloom/hdl/arcloom_mathloom.v arcloom/hdl/arcloom_mathloom_alu.v arcloom/hdl/arcloom_mathloom_div.v arcloom/hdl/arcloom_ternary_loom.v arcloom/hdl/arcloom_bsil_bt.v arcloom/hdl/arcloom_sppu.v arcloom/hdl/arcloom_krimelack.v arcloom/hdl/arcloom_l6_tcl.v
timeout 30s vvp "$t/axi"
timeout 30s python -m unittest discover -s arcloom/sim -p test_mathloom_transport.py -v
```

Do not go on to Vivado while any of these fail.

## Step 3 — Move the files to the PC

In the Codespace, zip the design files in one go instead of downloading them one at a
time (Lesson #31). Leave out testbenches. Also leave out the 8-column octal files,
which were added 09-29 and were never part of the robot build:

```bash
cd arcloom/hdl
rm -f arcloom_hdl.zip
zip arcloom_hdl.zip *.v -x '*_tb.v' 'arcloom_octal_*.v'
```

Download `arcloom_hdl.zip` and `arcloom/scripts/create_block_design.tcl`.

On the PC:

- **Delete the old copies from `C:\Users\joeta\Downloads` first**, then
  download fresh copies, then check that the file sizes changed. Otherwise the browser can
  hand you the cached old file. (Lesson #23)
- Extract the zip into `Downloads`, overwriting old copies.
- `Downloads` must contain **only** the design `.v` files. The script loads every
  `*.v` it finds there, so a stray copy or testbench causes duplicate-module
  errors. (Lesson #25)

## Step 4 — Build in Vivado: always a fresh project

Never patch an existing project. Removing and re-adding files corrupted it even
after a reset, and once broke the MathLoom on a change that touched only the
sensor thresholds. (Lessons #4, #26)

In the Vivado Tcl console:

```tcl
source C:/Users/joeta/Downloads/create_block_design.tcl
```

The script, in order:
- creates `C:\Users\joeta\arcloom_pynq2` fresh (`-force`)
- adds every `.v` from Downloads
- builds the block design (Zynq PS + `arcloom_0` + XADC reader + camera)
- writes its own pin file, `Downloads\arcloom_pins.xdc` (motors on Pmod A
  Y18/Y19/Y16/Y17, sensors on E17/D18, E18/E19, K14/J14, camera on the Arduino
  header)
- synthesizes, implements with power optimization switched off (power analysis hangs
  for hours on this design), and writes the bitstream

When the script finishes, the output is in:

```
C:\Users\joeta\arcloom_pynq2\arcloom_pynq2.runs\impl_1\
```

If Vivado ever says "Synthesis results are not added to the cache due to
CRITICAL WARNING", run `reset_runs synth_1` before any rebuild. (Lesson #24)

**Do not use** `arcloom/scripts/create_project.tcl` or
`arcloom/constraints/pynq_z2.xdc` for the robot. The first is the old,
unused path. The second was rewritten 09-29 into the oscilloscope pin file,
and it puts scope outputs on the **same four pins as the motors**. (G1 audit)

## Step 5 — Load it onto the board

1. Rename the two output files to **exactly** `arcloom.bit` and `arcloom.hwh`.
   Both must have the same base name and come from the same build. (Lesson #7)
2. **Before overwriting, download the board's current `arcloom.bit` and
   `arcloom.hwh` and keep them**, so the last working version can be put back.
   (G1 audit, 10-04)
3. Open Jupyter at `http://192.168.2.99:9090` and upload both files into
   `/home/xilinx/jupyter_notebooks/ArcLoom/`, overwriting the old ones.
   Jupyter uploads land there, not in `/home/xilinx/`. (Lesson #8)

## Step 6 — Start and test

1. **Reboot the board.** Loading a new design over an old one can hang the board.
   (Lesson #36)
2. The autostart service loads `arcloom.bit` and starts the demo server by
   itself. (Lesson #41) If the page doesn't come up, run the server by hand in a
   Jupyter cell in the ArcLoom folder: `%run loom_display_server.py`.
3. Open `http://10.0.0.167:5000` on the iPad. That address was right in April,
   but the router can change it.
4. **Test with the motors off first** (the wheels stay still until RUN DEMO is pressed).
   Check the sensor readings and decisions on the page, and the calculator if the
   MathLoom changed.
5. Then, with the robot on the floor, press RUN DEMO. Press END DEMO to stop.
   Both buttons work by setting or clearing bit 2 of register `0x10`, the motor gate.

## Step 7 — Write down what happened

Add a dated entry to `PYNQ_DEPLOYMENT_LESSONS.md` with:

- the git commit the `.v` files came from
- what changed, and what was seen on the board, both working and failing
- any new lesson, with the next free number

The 10-04 G1 audit also asks for these, so that a board result can be tied to the
exact build (MINE to fold in here, theirs as a requirement):

```bash
sha256sum arcloom.bit arcloom.hwh      # on the board, after upload
```

Also keep Vivado's utilization and timing reports from `impl_1` next to the entry.

## Board facts this protocol relies on

| Item | Value | Source |
|---|---|---|
| Board | PYNQ-Z2, XC7Z020-1CLG400C | build scripts |
| Vivado (historic) | 2024.1 | MathLoom log |
| Board Jupyter | `192.168.2.99:9090` | Lessons, Hardware State |
| Demo page | `10.0.0.167:5000` | `loom_display_server.py` |
| Vivado project | `C:\Users\joeta\arcloom_pynq2` | Lessons #5 |
| Bitstream on board | `/home/xilinx/jupyter_notebooks/ArcLoom/arcloom.bit` | Lessons, Hardware State |
| Motor driver | TB6612FNG on Pmod A | Lessons #18 |
| Wi-Fi fix | reload `rtl8xxxu` before bringing up `wlan0` | Lessons #37 |

## Open on the new ARCLOOM laptop

The Vivado steps above were done on the old Windows PC (`C:\Users\joeta\...`).
The ledger (10-03) says Vivado is not confirmed installed on the new laptop. If
the build moves there, the paths in `create_block_design.tcl` must change to match,
and the Vivado version should match 2024.1.
