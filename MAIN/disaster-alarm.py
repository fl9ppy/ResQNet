import json
import time
import subprocess

JSON_FILE = "/tmp/mq3_latest.json"

GAS_THRESHOLD = 350
FIRE_THRESHOLD = 60.0

def start_alert_wifi():
    print("🚨 Starting DISASTER ALERT hotspot...")
    subprocess.run(["sudo", "nmcli", "radio", "wifi", "off"])
    subprocess.run(["sudo", "rfkill", "unblock", "wifi"])
    time.sleep(1)
    subprocess.run(["sudo", "systemctl", "start", "hostapd"])
    subprocess.run(["sudo", "systemctl", "start", "dnsmasq"])

def stop_alert_wifi():
    print("Alert cleared. Stopping hotspot...")
    subprocess.run(["sudo", "systemctl", "stop", "hostapd"])
    subprocess.run(["sudo", "systemctl", "stop", "dnsmasq"])
    subprocess.run(["sudo", "nmcli", "radio", "wifi", "on"])

def read_json():
    try:
        with open(JSON_FILE, "r") as f:
            return json.load(f)
    except:
        return None

def main():
    hotspot_on = False
    print("Unified DISASTER alert watcher running...")

    while True:
        data = read_json()
        danger = False

        if data:
            gas = data.get("MQ3", 0)
            temp = data.get("TEMP", 0)

            if gas >= GAS_THRESHOLD:
                print(f"⚠ HIGH GAS: {gas}")
                danger = True

            if temp >= FIRE_THRESHOLD:
                print(f"🔥 HIGH TEMP: {temp}")
                danger = True

        if danger and not hotspot_on:
            start_alert_wifi()
            hotspot_on = True

        elif not danger and hotspot_on:
            stop_alert_wifi()
            hotspot_on = False

        time.sleep(1)

if __name__ == "__main__":
    main()
