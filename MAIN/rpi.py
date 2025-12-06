import serial

# Change to the correct port for your ESP32
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200

def main():
  ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
  print("Listening on", SERIAL_PORT)

  try:
    while True:
      line = ser.readline().decode(errors="ignore").strip()
      if not line:
        continue

      # Lines look like: MQ3:123.00 or TEMP:24.50
      print("Raw:", line)

      if ":" in line:
        node_id, value_str = line.split(":", 1)
        try:
          value = float(value_str)
          if node_id == "MQ3":
            print(f"[MQ-3] Gas reading: {value:.2f}")
          elif node_id == "TEMP":
            print(f"[TEMP] Temperature: {value:.2f} °C")
          else:
            print(f"[{node_id}] Value: {value:.2f}")
        except ValueError:
          print("Could not parse value:", value_str)

  except KeyboardInterrupt:
    print("\nStopping.")
  finally:
    ser.close()

if __name__ == "__main__":
  main()
