## ============================================================
## ArcLoom PYNQ-Z2 Constraints (XC7Z020-1CLG400C)
## Minimal pin-out for first bitstream
## ============================================================

## Clock — 125 MHz system clock
set_property -dict { PACKAGE_PIN H16  IOSTANDARD LVCMOS33 } [get_ports clk]
create_clock -period 8.000 -name sys_clk [get_ports clk]

## Reset — active-low, BTN0
set_property -dict { PACKAGE_PIN D19  IOSTANDARD LVCMOS33 } [get_ports rst_n]

## ============================================================
## Sensor ADC input — Pmod Header JA + JB
## ============================================================
set_property -dict { PACKAGE_PIN Y18  IOSTANDARD LVCMOS33 } [get_ports {sensor_adc[0]}]
set_property -dict { PACKAGE_PIN Y19  IOSTANDARD LVCMOS33 } [get_ports {sensor_adc[1]}]
set_property -dict { PACKAGE_PIN Y16  IOSTANDARD LVCMOS33 } [get_ports {sensor_adc[2]}]
set_property -dict { PACKAGE_PIN Y17  IOSTANDARD LVCMOS33 } [get_ports {sensor_adc[3]}]
set_property -dict { PACKAGE_PIN U18  IOSTANDARD LVCMOS33 } [get_ports {sensor_adc[4]}]
set_property -dict { PACKAGE_PIN U19  IOSTANDARD LVCMOS33 } [get_ports {sensor_adc[5]}]
set_property -dict { PACKAGE_PIN W18  IOSTANDARD LVCMOS33 } [get_ports {sensor_adc[6]}]
set_property -dict { PACKAGE_PIN W19  IOSTANDARD LVCMOS33 } [get_ports {sensor_adc[7]}]
set_property -dict { PACKAGE_PIN W14  IOSTANDARD LVCMOS33 } [get_ports {sensor_adc[8]}]
set_property -dict { PACKAGE_PIN Y14  IOSTANDARD LVCMOS33 } [get_ports {sensor_adc[9]}]
set_property -dict { PACKAGE_PIN T11  IOSTANDARD LVCMOS33 } [get_ports {sensor_adc[10]}]
set_property -dict { PACKAGE_PIN T10  IOSTANDARD LVCMOS33 } [get_ports {sensor_adc[11]}]
set_property -dict { PACKAGE_PIN V16  IOSTANDARD LVCMOS33 } [get_ports sensor_valid]

## ============================================================
## Decision outputs — LEDs LD0-LD3
## ============================================================
set_property -dict { PACKAGE_PIN R14  IOSTANDARD LVCMOS33 } [get_ports {decision_steer[0]}]
set_property -dict { PACKAGE_PIN P14  IOSTANDARD LVCMOS33 } [get_ports {decision_steer[1]}]
set_property -dict { PACKAGE_PIN N16  IOSTANDARD LVCMOS33 } [get_ports {decision_speed[0]}]
set_property -dict { PACKAGE_PIN M14  IOSTANDARD LVCMOS33 } [get_ports {decision_speed[1]}]

## RGB LEDs — confidence
set_property -dict { PACKAGE_PIN L15  IOSTANDARD LVCMOS33 } [get_ports {decision_conf[0]}]
set_property -dict { PACKAGE_PIN G17  IOSTANDARD LVCMOS33 } [get_ports {decision_conf[1]}]

## ============================================================
## Status outputs — Pmod JC
## ============================================================
set_property -dict { PACKAGE_PIN V15  IOSTANDARD LVCMOS33 } [get_ports structural_lock]
set_property -dict { PACKAGE_PIN W15  IOSTANDARD LVCMOS33 } [get_ports dsf_safe_mode]
set_property -dict { PACKAGE_PIN T9   IOSTANDARD LVCMOS33 } [get_ports dsf_valid]
set_property -dict { PACKAGE_PIN U10  IOSTANDARD LVCMOS33 } [get_ports {dsf_D[0]}]
set_property -dict { PACKAGE_PIN V17  IOSTANDARD LVCMOS33 } [get_ports {dsf_D[1]}]
set_property -dict { PACKAGE_PIN V18  IOSTANDARD LVCMOS33 } [get_ports dsf_R_rev]

## ============================================================
## XADC Analog Inputs — VAUX3 (Arduino A0)
## Dedicated analog pins route directly to the XADC hard block.
## No PACKAGE_PIN or IOSTANDARD — Vivado handles placement
## automatically when the XADC primitive references VAUX3.
## ============================================================

## ============================================================
## Timing
## ============================================================
set_input_delay  -clock sys_clk -max 3.0 [get_ports {sensor_adc[*]}]
set_input_delay  -clock sys_clk -min 0.5 [get_ports {sensor_adc[*]}]
set_input_delay  -clock sys_clk -max 3.0 [get_ports sensor_valid]
set_input_delay  -clock sys_clk -min 0.5 [get_ports sensor_valid]
set_output_delay -clock sys_clk -max 2.0 [get_ports {decision_steer[*]}]
set_output_delay -clock sys_clk -max 2.0 [get_ports {decision_speed[*]}]
set_output_delay -clock sys_clk -max 2.0 [get_ports {decision_conf[*]}]

## ============================================================
## Bitstream
## ============================================================
set_property CFGBVS VCCO [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
