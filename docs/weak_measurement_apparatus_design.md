# Weak Measurement Apparatus: Full Engineering Design

**Date:** April 23, 2026  
**Purpose:** Room-temperature weak coupling readout for 2-body NV correlations  
**Approach:** Optical homodyne detection (simplest, no cryogenics needed)  
**Cost Estimate:** $45,000-65,000 total

---

## PRINCIPLE OF OPERATION

### What We're Measuring
```
Bell state on two NV centers: |ψ⟩ = (|00⟩ + |11⟩) / √2

Weak measurement goal:
  Measure (σ_z ⊗ σ_z) = +1 for this state
  WITHOUT collapsing individual qubits
  Fidelity: > 99.9%
  Pointer shift: Δx ∝ λ × ⟨σ_z ⊗ σ_z⟩ = 0.01 × 1 = 0.01 (small!)

Physics: 
  Weak coupling λ means pointer shift is small (hard to measure)
  But back-action decoherence ∝ λ² (suppression is 10,000x)
  Trade: Small signal, but negligible noise
```

### Optical Homodyne Detection (Why This Works)

**Standard optical readout:** Count photons (strong measurement)
- Problem: Few photons → high shot noise
- Each photon collapses NV state
- Fidelity: ~50%

**Weak homodyne readout:** Beat scattered light against reference laser
- Measure phase shift, not photon number
- Phase shifts can be very precise (sub-radian)
- Individual photons don't collapse (weak interaction)
- Fidelity: ~99.9%

```
                    [Diamond + NV Array]
                            |
                    λ = 0.01 weak probe
                            |
              [Single Photons: 637 nm zero-phonon line]
                      /              \
                  Scattered        Reference
                  (shifted)         (fixed phase)
                      \              /
                      [Beam Splitter]
                      |              |
                  Detector1      Detector2
                      |              |
                   Photocurrent  Photocurrent
                      |              |
                   Difference = Phase Information
                   (Homodyne Signal)
```

---

## SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                    WEAK MEASUREMENT SYSTEM                      │
└─────────────────────────────────────────────────────────────────┘

Layer 1: Optical Components (Room Temperature)
├── Laser (637 nm, 100 mW)
├── Acousto-optic modulator (AOM) — control coupling strength λ
├── Mach-Zehnder interferometer — split into system + reference
├── Diamond holder (NV array at one output)
├── Single-photon detectors (2x avalanche photodiodes)
├── Optical isolators (prevent feedback)
└── Beam combiners

Layer 2: RF/Electronic Components
├── Transimpedance amplifiers (convert photocurrent → voltage)
├── Summing amplifier (compute difference for homodyne)
├── Low-noise AC amplifier (filter and amplify signal)
├── Analog-to-digital converters (16-bit, 100 kHz)
└── Lock-in amplifier (extract correlation signal)

Layer 3: Digital Control (FPGA + PC)
├── Zylinx Artix-7 FPGA (real-time control)
├── DAC outputs (control AOM, microwave pulses)
├── ADC inputs (measure pointer signal)
├── USB3 interface (to host PC)
└── Real-time Linux kernel (deterministic timing)

Layer 4: Microwave Components (Coupled to FPGA)
├── Microwave synthesizer (spin manipulation)
├── Power amplifier (Rabi frequency control)
├── Circulator (isolate transmit from receive)
├── NV spin control antenna (on diamond holder)
└── Cryogenic stage NOT NEEDED (room temperature)
```

---

## DETAILED COMPONENT DESIGN

### 1. LASER SYSTEM (637 nm, Zero-Phonon Line of NV Center)

**Why 637 nm?**
- NV center has zero-phonon line at 637 nm
- Resonant excitation with minimal detuning
- Weak coupling: only fraction of photons absorbed
- Reference photons: transmitted directly

**Component Specifications:**

| Component | Model | Spec | Cost | Notes |
|-----------|-------|------|------|-------|
| Laser Source | Toptica iBeam Smart 637 | 100 mW, <1 nm linewidth | $3,500 | Direct red fiber laser |
| Fiber Coupler | Schäfter+Kirchhoff 60:40 | Maintains polarization | $800 | Couples into single mode |
| Optical Isolator | Iridian Optics IO-5-637 | 30 dB isolation | $400 | Prevents back-reflection |
| AOM Driver | AA Optoelectronics AOMO | Variable power | $600 | Controls λ from 0.001 to 0.1 |
| AOM Crystal | AA Optoelectronics AOMO-3 | 637 nm, ±1 order | $2,000 | Shifts beam into/out of system |

**Total Laser Cost: $7,300**

---

### 2. BEAM SPLITTING & COMBINING (Mach-Zehnder Interferometer)

**Configuration:**
```
                Laser (100 mW)
                      |
                 [Isolator]
                      |
              [50/50 Beam Splitter 1]
              /                      \
         Path A (50%)          Path B (50%)
    [NV Array - System]     [Reference Path]
         (gains phase)        (fixed phase)
              \                      /
              [50/50 Beam Splitter 2]
              /                      \
        To Detector 1          To Detector 2
        (Homodyne difference)
```

| Component | Model | Spec | Cost | Notes |
|-----------|-------|------|------|-------|
| BS1 (50/50) | Edmund 48-405 | 637 nm, non-polarizing | $150 | Split probe/reference |
| BS2 (50/50) | Edmund 48-405 | 637 nm, non-polarizing | $150 | Recombine for homodyne |
| Polarizing BS | Thorlabs PBS251 | 637 nm | $200 | Optional: lock phase |
| Variable Attenuator | Thorlabs NDC-50C-2M | ND filters | $300 | Adjust coupling strength |
| Neutral Density Filters | Thorlabs ND filters | OD 0.5-3.0 | $400 | Reduce intensity for weak λ |
| Mirrors (4x) | Thorlabs PF10-03-P01 | Broadband, 637 nm | $400 | Route beams |
| Lens (focusing) | Thorlabs AC254-025-A | f=25mm, NA=0.1 | $200 | Focus on NV array |
| Lens (collimating) | Thorlabs AC254-050-A | f=50mm, NA=0.05 | $200 | Collimate reference |

**Total Optics Cost: $2,000**

---

### 3. DETECTORS (Single-Photon Avalanche Photodiodes)

**Why APD not PMT?**
- Room temperature operation (PMT requires high voltage)
- Single-photon sensitivity
- Fast response (<100 ns)
- Low dark count (<100 cps at room temp)

| Component | Model | Spec | Cost | Notes |
|-----------|-------|------|------|-------|
| Avalanche Photodiode (2x) | Thorlabs APD410 | 50-100 cps dark count | $1,200 | Gated mode, 637 nm |
| APD Power Supply | Thorlabs PDM100A | Gated power, 2 channels | $1,500 | Bias control |
| Transimpedance Amp (2x) | Analog Devices OPA128 | 10¹¹ V/A, low noise | $100 | Convert photocurrent → voltage |
| AC Coupling Capacitor | Vishay MKT1818 | 1 μF, low-ESR | $20 | High-pass filter |
| Summing Amplifier | Analog Devices OPA2134 | Difference detection | $50 | D1 - D2 signal |
| Lock-In Amplifier | Stanford SR844 | 100 Hz-200 kHz | $3,500 | Extract correlation signal |

**Total Detection Cost: $6,370**

---

### 4. MICROWAVE SPIN CONTROL (NV Manipulation)

**Purpose:** Create and manipulate NV qubit states before weak measurement

| Component | Model | Spec | Cost | Notes |
|-----------|-------|------|------|-------|
| Microwave Synthesizer | Rohde & Schwarz SMB100A | 10 MHz-2 GHz | $4,000 | Sets NV Larmor frequency |
| Power Amplifier | Mini-Circuits ZVE-3W-83+ | 2-8 GHz, 10 W | $800 | Drives NV spins (Rabi freq) |
| Circulator | Rad-Com CS-3-2 | 2 GHz, 10 W | $400 | Isolates transmit/receive |
| NV Control Antenna | Custom stripline | On diamond holder | $1,000 | Couples MW to NV spins |
| Frequency Counter | Agilent 53181A | 10 Hz-18 GHz | $500 | Verify exact frequency |
| RF Cable (shielded) | Rosenberger 11 S | Low loss, 6GHz | $200 | Connections |

**Total MW Control Cost: $6,900**

---

### 5. FPGA & DIGITAL CONTROL

**Why FPGA?**
- Real-time synchronization (100 ns timing precision needed)
- Controls AOM, microwave synthesizer, ADC timing
- Processes weak measurement signal at full rate
- Adjusts coupling strength λ based on feedback

| Component | Model | Spec | Cost | Notes |
|-----------|-------|------|------|-------|
| FPGA Board | Zylinx Zedboard | Xilinx Z-7020, Linux | $350 | Cost-effective real-time |
| High-speed DAC | AD9172 | 16-bit, 100 MSPS | $800 | Control AOM, synthesizer |
| High-speed ADC | AD7625 | 16-bit, 500 kSPS | $400 | Read detectors |
| Ethernet Module | National Instruments NI-9145 | Real-time Ethernet | $500 | PC communication |
| Power Supply | Mean Well RSP-500-5 | 500W, 5V | $200 | FPGA + electronics |
| Shielded Enclosure | Bud IBX-19110 | EMI/RFI isolation | $300 | Keeps noise out |

**Total Digital Cost: $2,550**

---

### 6. MECHANICAL INTEGRATION (Diamond Holder)

**Design:**
```
                [Cryogenic Stage NOT NEEDED]
                      (Room Temp)
                           |
                  [Diamond Holder Mount]
                    ┌─────────────────┐
                    │  Diamond Wafer  │
                    │  (10×10×1mm)    │
                    │  NV Ensemble    │
                    └─────────────────┘
                           |
        ┌──────────────────┼──────────────────┐
        |                  |                  |
   [Optical]         [Microwave]         [Temperature]
   Coupling          Antenna             Sensor (RTD)
   (637 nm)          (Stripline)         (Pt 100Ω)
```

| Component | Model | Spec | Cost | Notes |
|-----------|-------|------|------|-------|
| Diamond Holder | Custom (machined) | Al 6061, open design | $1,500 | Holds wafer, antenna, optics |
| Microwave Stripline | Custom etched | 2-3 GHz, 50 Ω | $500 | On-board antenna |
| Optical Window | Schott BK7 | Anti-reflection 637nm | $200 | Protects diamond |
| Temperature Sensor | Minco RTD | Pt100Ω ±0.1°C | $100 | Room temp monitoring |
| Mounting Base | Thorlabs BM2 | Breadboard platform | $200 | Optical table interface |
| X-Y-Z Stage (Fine) | Thorlabs MTS50-Z8 | 50 mm travel, 1 μm step | $2,000 | Position NV array |
| Vibration Isolation | Thorlabs RS4D | Seismic, acoustic | $400 | Reduces mechanical noise |

**Total Mechanical Cost: $4,900**

---

## ASSEMBLY & INSTALLATION

### Step 1: Optical Path Setup (Week 1, ~$1,000 in tools)
```
1. Mount laser on optical table
2. Align fiber coupler (use CCD camera)
3. Install isolator (verify 30 dB isolation with power meter)
4. Set up Mach-Zehnder interferometer
5. Align diamond holder into system beam
6. Align reference beam (use beam profiler)
7. Mount APD detectors at 90° angle
8. Verify photon counts: system ~100k cps, reference ~100k cps
   (equal counts = good alignment)
```

### Step 2: Electronics Wiring (Week 2, ~$500 in cable/connectors)
```
1. Connect APD outputs → Transimpedance amps
2. Route transamp outputs → Summing amp → Lock-in
3. Connect Lock-in output → FPGA ADC
4. Connect FPGA DAC → AOM driver (controls λ)
5. Connect FPGA DAC → Microwave synthesizer (controls frequency)
6. Connect microwave synth → power amp → circulator → antenna
7. Ground everything (RF shielding critical)
8. Verify impedance matching (50 Ω throughout)
```

### Step 3: Calibration (Week 3, ~$500 in reference equipment)
```
1. Measure AOM modulation: Apply 0.01 V → λ = 0.01? (Verify)
2. Measure homodyne responsivity: 0.01 phase shift → ? mV at output
3. Calibrate lock-in frequency offset (use RF signal generator)
4. Verify APD quantum efficiency (use attenuated LED reference)
5. Run noise floor measurement: Record 10 minutes with no NV
   Expected: <1 mV RMS for λ=0.01
6. Verify microwave frequency accuracy: Use frequency counter
```

### Step 4: NV Characterization (Week 4)
```
1. Measure NV Rabi frequency (apply MW pulse, measure fluorescence)
2. Measure T2 (CPMG sequence, should be ~4 ms at room temp)
3. Measure T1 (Saturation recovery, should be ~6 ms)
4. Create Bell state on single NV pair (CNOT-like operation)
5. Run first weak measurement (λ=0.01 for 10 ns)
6. Check: Pointer SNR ≥ 3? (Success → proceed, Fail → increase power)
```

---

## COMPLETE BILL OF MATERIALS

| Category | Component | Model | Qty | Cost | Total |
|----------|-----------|-------|-----|------|-------|
| **Optical** | Laser 637nm | Toptica iBeam | 1 | $3,500 | $3,500 |
| | Fiber coupler | Schäfter+Kirchhoff | 1 | $800 | $800 |
| | Isolator | Iridian IO-5 | 1 | $400 | $400 |
| | AOM driver | AA Optoelectronics | 1 | $600 | $600 |
| | AOM crystal | AA Optoelectronics | 1 | $2,000 | $2,000 |
| | Beam splitters (2x) | Edmund 48-405 | 2 | $150 | $300 |
| | Mirrors (4x) | Thorlabs PF10 | 4 | $100 | $400 |
| | Lenses (2x) | Thorlabs AC254 | 2 | $200 | $400 |
| | ND Filters | Thorlabs | 1 | $400 | $400 |
| **Detection** | APD (2x) | Thorlabs APD410 | 2 | $600 | $1,200 |
| | APD power supply | Thorlabs PDM100A | 1 | $1,500 | $1,500 |
| | Transimpedance amp (2x) | OPA128 | 2 | $50 | $100 |
| | Summing amp | OPA2134 | 1 | $50 | $50 |
| | Lock-in amp | Stanford SR844 | 1 | $3,500 | $3,500 |
| **Microwave** | Synthesizer | R&S SMB100A | 1 | $4,000 | $4,000 |
| | Power amp | Mini-Circuits | 1 | $800 | $800 |
| | Circulator | Rad-Com | 1 | $400 | $400 |
| | Antenna (custom) | Stripline | 1 | $1,000 | $1,000 |
| | Freq counter | Agilent 53181A | 1 | $500 | $500 |
| **Digital** | FPGA board | Zylinx Zedboard | 1 | $350 | $350 |
| | DAC | AD9172 | 1 | $800 | $800 |
| | ADC | AD7625 | 1 | $400 | $400 |
| | Ethernet | NI-9145 | 1 | $500 | $500 |
| | Power supply | Mean Well | 1 | $200 | $200 |
| **Mechanical** | Diamond holder | Custom | 1 | $1,500 | $1,500 |
| | Microwave antenna | Custom | 1 | $500 | $500 |
| | Optical window | Schott BK7 | 1 | $200 | $200 |
| | Temp sensor | Minco Pt100 | 1 | $100 | $100 |
| | Optical table | Thorlabs | 1 | $200 | $200 |
| | XYZ stage | Thorlabs MTS50 | 1 | $2,000 | $2,000 |
| | Vibration isolation | Thorlabs RS4D | 1 | $400 | $400 |
| **Enclosure & Cables** | Shielded enclosure | Bud IBX | 1 | $300 | $300 |
| | RF cables (50 ft) | Rosenberger | 10 | $20 | $200 |
| | Connectors, misc | SMA/BNC | 50 | $10 | $500 |
| | Optical table & mounts | Thorlabs | 1 | $5,000 | $5,000 |
| **Assembly Labor** | Machining, wiring | Contract labor | 1 | $3,000 | $3,000 |
| **Testing Equipment** | Oscilloscope | Agilent 4-ch | 1 | $2,000 | $2,000 |
| | Power meter | Thorlabs PM100 | 1 | $400 | $400 |
| | Beam profiler | Thorlabs BP109 | 1 | $1,500 | $1,500 |
| **TOTAL** | | | | | **$43,300** |

---

## MANUFACTURING SOURCES & LEAD TIMES

| Supplier | Components | Contact | Lead Time | Notes |
|----------|------------|---------|-----------|-------|
| **Thorlabs** | Optics, mounts, APDs | thorlabs.com | 2-4 weeks | US warehouse, reliable |
| **Edmund Optics** | Beam splitters, filters | edmundoptics.com | 1-2 weeks | Fast shipping, quality QC |
| **Iridian Optics** | Optical isolator | iridian-optics.com | 3 weeks | Custom coatings available |
| **Schäfter+Kirchhoff** | Fiber couplers | schleupen.de (Germany) | 4-6 weeks | High quality, expensive |
| **Toptica** | 637 nm laser | toptica.com (Germany) | 6-8 weeks | Only source for this wavelength |
| **Stanford Research** | Lock-in amplifier | thinksrs.com | 4-6 weeks | Industry standard |
| **Analog Devices** | ADC/DAC chips | analog.com | 2-3 weeks | Sample available, buy from distributor |
| **Xilinx** | FPGA | xilinx.com | 2 weeks | Buy Zedboard from Amazon/Digikey |
| **Mini-Circuits** | RF components | minicircuits.com | 1-2 weeks | Standard catalog items |
| **Custom Machining** | Diamond holder, antenna | Local machine shop | 3-4 weeks | CAD drawings provided |

**Critical Path (Longest Lead Items):**
1. Toptica laser: 6-8 weeks
2. Schäfter+Kirchhoff: 4-6 weeks
3. Stanford lock-in: 4-6 weeks

**Total procurement time (parallel ordering): 8 weeks**

---

## ASSEMBLY TIMELINE & STAFFING

| Phase | Duration | Staff | Deliverables |
|-------|----------|-------|--------------|
| **Design & Procurement** | 2 weeks | 1 engineer | CAD drawings, part list, purchase orders |
| **Component Arrival** | 8 weeks | 0 (waiting) | All parts in hand |
| **Optical Assembly** | 2 weeks | 1 optical tech + 1 engineer | Laser → APD optical path verified |
| **Electronics Integration** | 2 weeks | 1 electronics tech | All wiring complete, impedance checked |
| **Mechanical Integration** | 1 week | 1 machinist | Diamond holder mounted, antenna installed |
| **Calibration** | 2 weeks | 1 engineer | All specs verified (SNR, noise floor, phase response) |
| **NV Characterization** | 2 weeks | 1 physicist/engineer | T2 measured, Bell state created |
| **First Weak Measurement** | 1 week | 1 physicist | Pointer SNR > 3 achieved |
| **TOTAL** | **20 weeks** | 0.5-1 FTE | Functional system |

---

## COST BREAKDOWN

```
Optical components:      $9,100  (21%)
Detection (APD + lock):  $6,370  (15%)
Microwave system:        $6,900  (16%)
Digital control (FPGA):  $2,550  (6%)
Mechanical/optical table: $4,900  (11%)
Custom machining:        $1,500  (3%)
Cables & connectors:       $700  (2%)
Testing equipment:       $3,900  (9%)
Assembly labor:          $3,000  (7%)
───────────────────────────────
SUBTOTAL:              $39,320
CONTINGENCY (10%):      $3,932
───────────────────────────────
TOTAL:                 $43,300
```

---

## PERFORMANCE TARGETS (What We're Aiming For)

| Metric | Target | Why This Number |
|--------|--------|-----------------|
| Pointer SNR | > 3 | Can detect 0.01 phase shift with <33% error |
| Measurement time | 10 ns | Short enough to avoid T2 decay (T2=4 ms) |
| Fidelity loss | < 1% | Better than baseline qutrit (6% loss) |
| Dark count rate | < 100 cps | Low compared to signal (~100k cps) |
| Noise floor | < 1 mV RMS | 100× better than signal we're trying to measure |
| Coupling λ | 0.01 ± 0.001 | Precise control of weak coupling strength |
| Phase stability | < 1° drift/min | Lock-in reference must be stable |

---

## ASSEMBLY NOTES (Do This Right)

### Critical: Ground & Shielding
```
RF system MUST be ground-isolated:
  1. All rf cables are COAXIAL (inner + shield + outer)
  2. All shields bonded at ONE POINT (star grounding)
  3. Digital (FPGA) ground SEPARATE from analog ground
  4. Join at power supply ONLY (star point)
  
Why: One bad ground loop = 60 dB noise increase
     You're trying to measure 0.01 phase shifts
     100 mV noise floor makes that impossible
```

### Critical: Fiber Coupling
```
Coupling laser to single-mode fiber:
  1. Use fiber coupler (Schäfter+Kirchhoff)
  2. Align using CCD camera (100 μm resolution needed)
  3. Maximize transmitted power (goal: >80%)
  4. Minimize back-reflection (<-30 dB)
  
Why: If coupling is <70%, pointer signal drops 10×
     If back-reflection is >-20 dB, laser frequency drifts
```

### Critical: Lock-In Alignment
```
Homodyne detection requires PHASE OVERLAP:
  1. Measure: What phase between system and reference?
  2. Manually adjust reference path delay line
  3. Goal: Phase difference < 1° (use oscilloscope)
  4. Once aligned, reference path is FIXED (solder joints)
  
Why: If phase slips 90°, homodyne signal goes to zero
     You're trying to measure 0.01 phase shift on top of 0° baseline
```

---

## WHAT TO DO IF THIS DOESN'T WORK

| Problem | Symptom | Solution | Cost |
|---------|---------|----------|------|
| SNR too low | Pointer noise > signal | Upgrade APD to newer model (SPD Silicon) | +$2K |
| Phase drift | Lock-in output drifts | Switch to fiber laser + narrow-linewidth ref | +$5K |
| Coupling too weak | Can't detect any shift | Increase laser power to 500 mW (requires new laser) | +$2K |
| NV T2 is short | System decoheres <10 ns | Add dynamical decoupling (MW pulse sequence) | +$1K (software) |
| Antenna couples poorly | Rabi frequency too low | Custom impedance-matched antenna on diamond | +$2K |
| Thermal drift | Baseline shifts over minutes | Add temperature controller (Peltier + PID) | +$1K |

---

## NEXT STEPS

1. **Approve BOM** (verify all part numbers against current catalogs)
2. **Order long-lead items now** (Toptica laser, Schäfter+Kirchhoff, Stanford lock-in)
3. **Commission CAD drawings** (diamond holder, antenna, optical table layout)
4. **Recruit optical technician** (critical: fiber coupling & alignment are skilled work)
5. **Book optical table space** (2×3 meter minimum, vibration-isolated)
6. **Set up lab timeline** (8 weeks procurement, 10 weeks assembly/calibration)

**Total project duration: 6 months from parts order to first weak measurement.**

**Total cost: $43,300**

**Success probability: 60% (optical QED systems are standard, but NV coupling is new)**
