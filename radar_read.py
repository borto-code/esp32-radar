import serial

PORT = "COM6"
BAUD = 115200

ser = serial.Serial(PORT, BAUD, timeout=1)

while True:
    line = ser.readline().decode("utf-8", errors="ignore").strip()
    parts = line.split(",")
    if len(parts) != 2:
        continue
    try:
        angle = int(parts[0])
        distance = float(parts[1])
    except ValueError:
        continue
    print(angle, distance)