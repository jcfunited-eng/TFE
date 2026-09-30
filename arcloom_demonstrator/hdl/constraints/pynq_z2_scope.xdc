## ============================================================
## ArcLoom PYNQ-Z2 Constraints (XC7Z020-1CLG400C)
## Hardware Substrate: 8-Column Balanced Octet & Instrumentation
## Oscilloscope Interface: Siglent SDS1104X-E 4-Channel (Pmod A)
## ============================================================

## Clock — 125 MHz system clock (H16)
set_property -dict { PACKAGE_PIN H16  IOSTANDARD LVCMOS33 } [get_ports clk]
create_clock -period 8.000 -name sys_clk [get_ports clk]

## Reset — active-low, BTN0 (D19)
set_property -dict { PACKAGE_PIN D19  IOSTANDARD LVCMOS33 } [get_ports rst_n]

## ============================================================
## 4-Channel Analog Oscilloscope Probing — Pmod A Header (JA)
## Direct BNC probe pins for Siglent SDS1104X-E (125 MHz Sigma-Delta PDM)
## Configured as high-slew, high-drive (12 mA) for clean 0-3.3V analog reconstruction
## ============================================================
## Pin 1 (JA1): Ch1 (Yellow)  — A1 Cochlear Acoustic Formant Resonance
set_property -dict { PACKAGE_PIN Y18  IOSTANDARD LVCMOS33 SLEW FAST DRIVE 12 } [get_ports scope_ch1_a1_cochlear]

## Pin 2 (JA2): Ch2 (Cyan)    — V1 Optical Foveal Target / Recurrent Spatial Attractor
set_property -dict { PACKAGE_PIN Y19  IOSTANDARD LVCMOS33 SLEW FAST DRIVE 12 } [get_ports scope_ch2_v1_optical]

## Pin 3 (JA3): Ch3 (Magenta) — S2 Contact Barrier Yield Stress (|sigma| - Y)
set_property -dict { PACKAGE_PIN Y16  IOSTANDARD LVCMOS33 SLEW FAST DRIVE 12 } [get_ports scope_ch3_s2_yield_stress]

## Pin 4 (JA4): Ch4 (Blue)    — M1 Motor Airway Vocal Pulse / Exhaust Discharge
set_property -dict { PACKAGE_PIN Y17  IOSTANDARD LVCMOS33 SLEW FAST DRIVE 12 } [get_ports scope_ch4_m1_vocal_efferent]

## ============================================================
## Afferent Sensory Transduction — Pmod A Bottom Row (JA7-JA10) & Pmod B (JB)
## ============================================================
set_property -dict { PACKAGE_PIN U18  IOSTANDARD LVCMOS33 } [get_ports {sensor_optical_focal[0]}]
set_property -dict { PACKAGE_PIN U19  IOSTANDARD LVCMOS33 } [get_ports {sensor_optical_focal[1]}]
set_property -dict { PACKAGE_PIN W18  IOSTANDARD LVCMOS33 } [get_ports {sensor_optical_focal[2]}]
set_property -dict { PACKAGE_PIN W19  IOSTANDARD LVCMOS33 } [get_ports {sensor_optical_focal[3]}]

set_property -dict { PACKAGE_PIN W14  IOSTANDARD LVCMOS33 } [get_ports {sensor_barrier_force[0]}]
set_property -dict { PACKAGE_PIN Y14  IOSTANDARD LVCMOS33 } [get_ports {sensor_barrier_force[1]}]
set_property -dict { PACKAGE_PIN T11  IOSTANDARD LVCMOS33 } [get_ports {sensor_barrier_force[2]}]
set_property -dict { PACKAGE_PIN T10  IOSTANDARD LVCMOS33 } [get_ports {sensor_barrier_force[3]}]
set_property -dict { PACKAGE_PIN V16  IOSTANDARD LVCMOS33 } [get_ports sample_tick]

## ============================================================
## Substrate Diagnostic LEDs — LD0-LD3
## ============================================================
## LD0 [R14]: Motor vocal valve discharge pulse ('say' syllable fired)
set_property -dict { PACKAGE_PIN R14  IOSTANDARD LVCMOS33 } [get_ports led_vocal_discharge]

## LD1 [P14]: Continuum von Mises barrier yield refusal (|sigma| > Y)
set_property -dict { PACKAGE_PIN P14  IOSTANDARD LVCMOS33 } [get_ports led_barrier_refusal]

## LD2 [N16]: Recurrent Layer 5 spatial potential well persistent (target tracking)
set_property -dict { PACKAGE_PIN N16  IOSTANDARD LVCMOS33 } [get_ports led_spatial_locked]

## LD3 [M14]: Somatic strain flag (S_UF <= 0 or P_k > B_k)
set_property -dict { PACKAGE_PIN M14  IOSTANDARD LVCMOS33 } [get_ports led_somatic_strained]

## ============================================================
## Mode Selection & Control Switches — SW0
## ============================================================
## SW0 [M20]: Sleep mode toggle (0 = Awake sensorimotor mesh, 1 = Nocturnal dream consolidation)
set_property -dict { PACKAGE_PIN M20  IOSTANDARD LVCMOS33 } [get_ports sleep_mode]

## ============================================================
## Timing Constraints
## ============================================================
set_output_delay -clock sys_clk -max 2.0 [get_ports {scope_ch1_a1_cochlear scope_ch2_v1_optical scope_ch3_s2_yield_stress scope_ch4_m1_vocal_efferent}]
set_output_delay -clock sys_clk -min 0.5 [get_ports {scope_ch1_a1_cochlear scope_ch2_v1_optical scope_ch3_s2_yield_stress scope_ch4_m1_vocal_efferent}]
set_output_delay -clock sys_clk -max 3.0 [get_ports {led_vocal_discharge led_barrier_refusal led_spatial_locked led_somatic_strained}]

## ============================================================
## Bitstream Generation Constraints
## ============================================================
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
