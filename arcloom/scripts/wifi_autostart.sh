#!/bin/bash
# ArcLoom WiFi Autostart for PYNQ-Z2
# Handles the rtl8xxxu driver cold-boot failure (~50% of the time)
# by cycling modprobe with retries before running wpa_supplicant.
#
# Install:
#   sudo cp wifi_autostart.sh /usr/local/bin/arcloom-wifi
#   sudo chmod +x /usr/local/bin/arcloom-wifi
#   sudo cp arcloom-wifi.service /etc/systemd/system/
#   sudo systemctl enable arcloom-wifi
#
# Config: edit SSID/PSK below or use /etc/wpa_supplicant/wpa_supplicant.conf

IFACE="wlan0"
MAX_RETRIES=5
RETRY_DELAY=3
WPA_CONF="/etc/wpa_supplicant/wpa_supplicant.conf"

log() { echo "[arcloom-wifi] $(date '+%H:%M:%S') $1"; }

# Kill any existing wpa_supplicant / dhclient on this interface
cleanup() {
    killall wpa_supplicant 2>/dev/null
    killall dhclient 2>/dev/null
    ip link set "$IFACE" down 2>/dev/null
}

# Cycle the driver — this is the fix for rtl8xxxu cold boot failures
cycle_driver() {
    log "Cycling rtl8xxxu driver..."
    modprobe -r rtl8xxxu 2>/dev/null
    sleep 1
    modprobe rtl8xxxu
    sleep 2
}

# Check if wlan0 exists
wait_for_interface() {
    for i in $(seq 1 10); do
        if ip link show "$IFACE" > /dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    return 1
}

# Main connect sequence
connect() {
    ip link set "$IFACE" up
    sleep 1

    # Start wpa_supplicant
    wpa_supplicant -B -i "$IFACE" -c "$WPA_CONF" -D nl80211,wext
    sleep 2

    # Check association
    if iw dev "$IFACE" link 2>/dev/null | grep -q "Connected"; then
        log "Associated to AP"
        # Get IP
        dhclient "$IFACE"
        sleep 2
        # Verify
        if ip addr show "$IFACE" | grep -q "inet "; then
            local addr=$(ip addr show "$IFACE" | grep "inet " | awk '{print $2}' | cut -d/ -f1)
            log "Connected: $addr"
            return 0
        fi
    fi
    return 1
}

# --- Main ---
log "Starting WiFi (rtl8xxxu retry mode)..."

cleanup

for attempt in $(seq 1 $MAX_RETRIES); do
    log "Attempt $attempt/$MAX_RETRIES"

    cycle_driver

    if ! wait_for_interface; then
        log "Interface $IFACE not found after driver cycle"
        continue
    fi

    cleanup
    if connect; then
        log "WiFi UP on attempt $attempt"
        exit 0
    fi

    log "Attempt $attempt failed, retrying in ${RETRY_DELAY}s..."
    cleanup
    sleep "$RETRY_DELAY"
done

log "FAILED after $MAX_RETRIES attempts. Use manual startup from Jupyter."
exit 1
