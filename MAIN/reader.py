import serial
import time
import json
import re
from collections import deque

SERIAL_PORT = "/dev/ttyACM0"
BAUD_RATE = 115200

# Rolling average window size
WINDOW = 5

def extract_first_float(s: str):
    match = re.search(r"-?\d+\.?\d*", s)
    if not match:
        return None
    try:
        return float(match.group(0))
    except:
        return None


def rolling_average(buffer):
    if len(buffer) == 0:
        return 0
    return sum(buffer) / len(buffer)


def main():
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)

    print("Raspberry Pi Receiver Started")

    # Rolling buffers for smoothing
    mq3_buf = deque(maxlen=WINDOW)
    temp_buf = deque(maxlen=WINDOW)
    dist_mq3_buf = deque(maxlen=WINDOW)
    dist_temp_buf = deque(maxlen=WINDOW)

    last_output = time.time()

    while True:

        raw = ser.readline().decode("utf-8", errors="ignore").strip()

        if raw and ":" in raw:
            parts = raw.split(":", 1)
            node = parts[0].strip()
            payload = parts[1].strip()

            value = extract_first_float(payload)
            if value is None:
                continue

            # -----------------------------
            # MQ3 GAS VALUE
            # -----------------------------
            if node == "MQ3":
                if 30 <= value <= 2000:
                    mq3_buf.append(value)

            # -----------------------------
            # GAS BEACON DISTANCE
            # -----------------------------
            elif node == "DIST_MQ3":
                if 0 <= value <= 20:
                    dist_mq3_buf.append(value)

            # -----------------------------
            # TEMP BEACON DISTANCE
            # -----------------------------
            elif node == "DIST_TEMP":
                if 0 <= value <= 20:
                    dist_temp_buf.append(value)

            # -----------------------------
            # TEMPERATURE VALUE
            # -----------------------------
            elif node == "TEMP":
                if -20 <= value <= 150:

                    # TEMP glitch rejection
                    if len(temp_buf) > 0:
                        last_temp = temp_buf[-1]
                        if abs(value - last_temp) > 5:
                            continue

                    temp_buf.append(value)

        # -----------------------------
        # OUTPUT EVERY 1 SECOND
        # -----------------------------
        if time.time() - last_output >= 1:

            safe_data = {
                "MQ3": rolling_average(mq3_buf),
                "TEMP": rolling_average(temp_buf),
                "DIST_MQ3": rolling_average(dist_mq3_buf),
                "DIST_TEMP": rolling_average(dist_temp_buf)
            }

            print(json.dumps(safe_data, indent=2))

            # Save for disaster_alert.py
            with open("/tmp/mq3_latest.json", "w") as f:
                json.dump(safe_data, f)

            last_output = time.time()


if __name__ == "__main__":
    main()