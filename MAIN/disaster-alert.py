import json
import time
import subprocess
import os

JSON_FILE = "/tmp/mq3_latest.json"

# ----------------------
# THRESHOLDS
# ----------------------
GAS_THRESHOLD = 350        # ppm-equivalent from MQ3
FIRE_THRESHOLD = 60.0      # Celsius

# ----------------------
# HOTSPOT CONTROL
# ----------------------
def start_alert_wifi():
    print("🚨 Starting DISASTER ALERT WiFi hotspot...")

    # Disable normal WiFi
    subprocess.run(["sudo", "nmcli", "radio", "wifi", "off"])
    subprocess.run(["sudo", "rfkill", "unblock", "wifi"])
    time.sleep(1)

    # Start AP
    subprocess.run(["sudo", "systemctl", "start", "hostapd"])
    subprocess.run(["sudo", "systemctl", "start", "dnsmasq"])

def stop_alert_wifi():
    print("Alert cleared. Stopping hotspot...")

    # Stop AP
    subprocess.run(["sudo", "systemctl", "stop", "hostapd"])
    subprocess.run(["sudo", "systemctl", "stop", "dnsmasq"])

    # Re-enable normal WiFi
    subprocess.run(["sudo", "nmcli", "radio", "wifi", "on"])


# ----------------------
def read_json():
    try:
        with open(JSON_FILE, "r") as f:
            return json.load(f)
    except:
        return None


# ----------------------
def main():
    hotspot_on = False

    print("Unified DISASTER alert watcher started...")

    while True:
        data = read_json()

        danger = False  # assume safe unless proven otherwise

        if data:
            gas = data.get("MQ3", 0)
            temp = data.get("TEMP", 0)
            dist_gas = data.get("DIST_MQ3", 0)
            dist_temp = data.get("DIST_TEMP", 0)

            # -----------------------------
            # Show distances (for debugging)
            # -----------------------------
            print(f"DIST_MQ3 = {dist_gas} m | DIST_TEMP = {dist_temp} m")

            # -----------------------------
            # GAS danger logic
            # -----------------------------
            if gas >= GAS_THRESHOLD:
                print(f"⚠ GAS HIGH: {gas}")
                danger = True

            # -----------------------------
            # FIRE danger logic
            # -----------------------------
            if temp >= FIRE_THRESHOLD:
                print(f"🔥 TEMP HIGH: {temp} °C")
                danger = True

        # -----------------------------
        # Start hotspot if ANY danger
        # -----------------------------
        if danger and not hotspot_on:
            start_alert_wifi()
            hotspot_on = True

        # -----------------------------
        # Stop hotspot when all safe
        # -----------------------------
        elif not danger and hotspot_on:
            stop_alert_wifi()
            hotspot_on = False

        time.sleep(1)


if __name__ == "__main__":
    main()