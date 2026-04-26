#!/bin/bash
# ArcLoom Autostart — runs on PYNQ boot
# Loads overlay + starts WiFi + starts display server
# Install: sudo cp arcloom_autostart.sh /etc/init.d/arcloom && sudo chmod +x /etc/init.d/arcloom && sudo update-rc.d arcloom defaults

# Wait for system to settle
sleep 15

# Connect WiFi
ip link set wlan0 up 2>/dev/null
sleep 2
wpa_supplicant -B -i wlan0 -c /etc/wpa_supplicant/wpa_supplicant.conf 2>/dev/null
sleep 3
dhclient wlan0 2>/dev/null
sleep 3

# Start display server (loads overlay automatically)
cd /home/xilinx/jupyter_notebooks/ArcLoom
python3 loom_display_server.py &

echo "ArcLoom autostart complete"
