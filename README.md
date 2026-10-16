# ESP32 Ultrasonic Radar

An ESP32 sweeps an HC-SR04 ultrasonic sensor on an SG90 servo and sends angle and distance readings to the computer over USB. A Python program draws them on a live radar screen.

## Parts
- ESP32 (NodeMCU-32S)
- HC-SR04 ultrasonic sensor
- SG90 servo
- 1k and 2.2k resistors (voltage divider on the Echo pin)
- Breadboard and jumper wires

## Wiring
| Part | ESP32 pin |
|------|-----------|
| TRIG | GPIO 25 |
| ECHO | GPIO 26 (through the voltage divider) |
| Servo signal | GPIO 27 |

The HC-SR04 and the servo are powered from the 5V pin. Echo outputs 5 V, so it must go through the divider before reaching the ESP32.

## How to run
1. Open `radar_firmware/radar_firmware.ino` in the Arduino IDE and upload it to the ESP32.
2. Install the Python libraries: `py -m pip install pygame-ce pyserial`
3. Set `PORT` in `radar_view.py` to your ESP32's COM port.
4. Run `py radar_view.py`.

Keys: + / - zoom, D flip left/right, F filter, M mute, Esc quit.

## How it works
The ESP32 turns the servo from 30° to 150° and back. At each step it fires the ultrasonic sensor, works out the distance from the echo time, and prints a line like `90,42.5` (angle, distance in cm) over USB serial. If no echo comes back, it prints -1 as the distance.

The Python program reads those lines, splits each one into an angle and a distance, and converts them to a position on the screen with sin and cos. Objects show up as green dots that fade over a few seconds. A missing echo shows as a gray hollow circle at the edge. It also beeps when something is close.