# ArcLoom PYNQ Deployment — Lessons Learned

## Session: April 18-19, 2026

---

### Vivado Block Design

1. **Vivado caches module reference parameters aggressively.** Changing `C_S_AXI_ADDR_WIDTH` in the source file does NOT update the Block Design cell. You must either:
   - Delete the cell and re-add it after clearing the cache (`arcloom_pynq.cache` folder)
   - Use `set_property CONFIG.C_S_AXI_ADDR_WIDTH <value> [get_bd_cells arcloom_0]`

2. **ADDR_WIDTH=4 is what works.** The AXI interconnect on PYNQ Block Design assigns 4K address ranges by default. ADDR_WIDTH=6 (64 bytes) causes the interconnect to not pass upper address bits, resulting in Vivado optimizing away ALL logic connected to registers > 0x0F. We fought this for hours. Stick with ADDR_WIDTH=4 and pack data into 4 registers.

3. **Vivado will optimize away logic it considers unused.** If a combinational chain only appears in one branch of a case statement, Vivado may prune the entire chain. The fix: register (latch) the outputs every clock cycle so they're always "used." Registered outputs survived; wire-only outputs did not.

4. **When the Block Design gets corrupted from parameter changes, start over.** Don't try incremental fixes. Create a fresh project with a clean Tcl script. The working script is `create_block_design.tcl`.

5. **The working Vivado project is `arcloom_pynq2`.** Not `vivado_pynq` or `arcloom`. Those are corrupted from earlier attempts.

6. **`generate_target` must run AFTER all parameter changes.** Setting address range after generate_target is too late.

### PYNQ Overlay Loading

7. **Files must be named identically.** `arcloom.bit` and `arcloom.hwh` — both must have the same base name. The `.hwh` file must match the Block Design that generated the `.bit`.

8. **File location matters.** Files uploaded via Jupyter go to `/home/xilinx/jupyter_notebooks/ArcLoom/`, not `/home/xilinx/`. Use the full path in `Overlay()`.

9. **Can't load two overlays simultaneously.** The base overlay (for Arduino_Analog sensor reads and Pmod_IO motor control) and the ArcLoom overlay can't coexist. Swapping overlays takes ~15-30 seconds. This is the ARM-mediated path penalty.

10. **The ArcLoom overlay does NOT include Pmod controllers.** `ol.PMODA` doesn't exist on the ArcLoom overlay. Motor control requires loading the base overlay. Sensor reads via Arduino_Analog also require the base overlay.

### AXI Register Interface

11. **Register map (ADDR_WIDTH=4, 4 registers):**
    - 0x00 WRITE: `[11:0]` sensor ADC, `[16]` valid pulse
    - 0x04 WRITE: `[7:0]` MathLoom operand A
    - 0x08 WRITE: `[7:0]` MathLoom operand B
    - 0x0C WRITE: `[5:0]` cam_edge, `[11:6]` cam_motion
    - 0x00 READ: Decision + flags (steer, speed, conf, SL-1, safe_mode, dsf_D, etc.)
    - 0x04 READ: loom_state[31:0]
    - 0x08 READ: MathLoom add + compare results
    - 0x0C READ: MathLoom multiply product[15:0] + loom_state[47:32]

12. **sensor_valid pulse must be stretched.** A single-cycle AXI write produces a pulse too fast for BSIL to latch. The wrapper stretches it to 4 clock cycles via a countdown counter.

13. **MathLoom results are latched every clock cycle** as registered outputs. This prevents Vivado from optimizing them away and ensures they're always readable.

### XADC Limitations

14. **XADC DOES work from PL via the raw primitive.** The Zynq's XADC auxiliary input pins are hardwired in silicon to the XADC hard block. Instantiate the XADC primitive directly, configure INIT_40 with the correct channel (VAUX3 = 0x13 in CH[4:0]), and tie VAUXP/VAUXN to 16'b0. Do NOT create top-level ports for the analog pins — Vivado inserts IBUFs that conflict with the XADC shape. No XDC constraints needed for analog pins. **PROVEN April 21, 2026.**

15. **XADC `channel_out` is NOT ADC data.** It's a 5-bit channel number indicating which channel was just sampled. The actual ADC data is only accessible through AXI register reads.

16. **XADC `eoc_out` fires continuously** when enabled, overriding the software sensor path if connected to `hw_sensor_valid`. Disconnect XADC from ArcLoom until a real PL-side ADC (Pmod AD5) is available.

### Motor Driver

17. **DRV8835 (Pololu) didn't work.** Had power (6.9V on VM), had control signals (3.3V from Pmod), but zero output on motor pins. Possibly defective board.

18. **TB6612FNG works.** Wiring:
    - AIN1→Pmod A pin 0, AIN2→pin 1, BIN1→pin 2, BIN2→pin 3
    - PWMA, PWMB→3.3V (Pmod B, since Pmod A 3.3V pins used by VCC and STBY)
    - VCC, STBY→3.3V (Pmod A)
    - VM→Battery+ (~6.9V), GND→Battery- AND Pmod GND
    - AO1/AO2→left motor, BO1/BO2→right motor

19. **Motor control uses `base.PMODA` from the base overlay**, not the ArcLoom overlay. The ArcLoom overlay doesn't have Pmod controllers.

20. **Arduino_IO crashes the microblaze.** Use `Pmod_IO` instead for all digital GPIO.

### Sensor

21. **Sharp GP2Y0A41SK0F on Arduino AR0** reads via `Arduino_Analog(base.ARDUINO, [0])`. Returns a scalar float (voltage), not a list. Use `v = analog.read()` then `adc = int(v * 4096 / 3.3)`.

22. **BSIL thresholds don't match the sensor's useful range.** The coupling weights and BSIL thresholds were approximated, not calibrated to the Sharp sensor's actual voltage-to-distance curve. The loom makes decisions but they don't always make physical sense (e.g., says "retreat" when object is at medium distance).

### Critical Process Notes

23. **When downloading updated .v files from the Codespace**, the browser may cache the old file. Delete the old file from Downloads first, then download fresh. Verify file size changed.

24. **When Vivado says "Synthesis results are not added to the cache due to CRITICAL WARNING"**, the next incremental synthesis may use stale results. Always `reset_runs synth_1` before rebuilding.

25. **Keep all .v files in Downloads together.** The Tcl script uses `glob C:/Users/joeta/Downloads/*.v` to find them. Don't have extra copies (like `ARC1_arcloom_ternary_loom.v`) or testbench files (`arcloom_tb.v`) in the same folder — they'll get included and may cause duplicate module errors.

---

## What Works (Proven on Hardware)

- 8-strand SPPU combinational decisions from sensor input
- MathLoom: 19,683/19,683 operations (add+multiply+compare) zero errors
- L6 structural lock at Euler knee
- BSIL distance/direction/acceleration encoding
- Krimelack commit gating
- TB6612FNG motor control (all 4 directions)
- Sensor → loom → motor decision chain (ARM-mediated)

## What Doesn't Work Yet

- ~~Direct HW sensor path~~ **PROVEN April 21** (XADC primitive, no Pmod AD5 needed)
- Coupling weight calibration for Sharp sensor
- Camera BSIL encoding
- Continuous autonomous loop (overlay swapping too slow)

## Hardware State

- PYNQ-Z2 at 192.168.2.99:9090
- Working Vivado project: `C:\Users\joeta\arcloom_pynq2`
- Bitstream on PYNQ: `/home/xilinx/jupyter_notebooks/ArcLoom/arcloom.bit`
- TB6612FNG wired and tested on Pmod A (control) + Pmod B (PWM power)
- Sharp sensor on Arduino AR0
- Battery pack: 4xAA Energizer lithium (~6.9V)
- DRV8835: wired but non-functional (set aside)
