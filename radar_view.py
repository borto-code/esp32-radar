import array
import math
import time
from collections import deque

import pygame
import serial

PORT = "COM6"
BAUD = 115200

WIDTH = 900
HEIGHT = 540
CENTER = (WIDTH // 2, HEIGHT - 50)
RADIUS = 400

RANGES = [50, 100, 200, 400]
FADE_SECONDS = 4.0
TRAIL_LENGTH = 14
ALERT_DIST = 100

BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RING_GREEN = (0, 120, 0)
TEXT_GREEN = (190, 255, 190)
HELP_GRAY = (110, 140, 110)

settings = {
    "range_index": 2,
    "mirror": False,
    "filter": True,
    "sound": True,
}


def max_dist():
    return RANGES[settings["range_index"]]


def polar_to_screen(angle_deg, distance_cm):
    """Turn (angle, distance) into (x, y) pixels on the window."""
    if settings["mirror"]:
        angle_deg = 180 - angle_deg
    r = distance_cm / max_dist() * RADIUS
    a = math.radians(angle_deg)
    x = CENTER[0] + r * math.cos(a)
    y = CENTER[1] - r * math.sin(a)
    return int(x), int(y)


def read_new_data(ser):
    """Read every line the ESP32 has sent so far and return (angle, distance) pairs."""
    results = []
    while ser.in_waiting:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        parts = line.split(",")
        if len(parts) != 2:
            continue
        try:
            angle = int(parts[0])
            distance = float(parts[1])
        except ValueError:
            continue
        results.append((angle, distance))
    return results


def make_beep(freq, ms=80, volume=0.4):
    """Build a short beep as a sine wave, so we don't need any sound files."""
    sample_rate = 44100
    n = int(sample_rate * ms / 1000)
    samples = array.array("h")
    for i in range(n):
        envelope = min(1, i / 200, (n - i) / 200)
        value = int(32767 * volume * envelope * math.sin(2 * math.pi * freq * i / sample_rate))
        samples.append(value)
    return pygame.mixer.Sound(buffer=samples.tobytes())


def draw_trail(screen, trail):
    """Draw the fading wedge behind the sweep line."""
    angles = list(trail)
    for i in range(1, len(angles)):
        if abs(angles[i] - angles[i - 1]) > 6:
            continue
        fade = i / len(angles)
        color = (0, int(80 * fade), 0)
        corners = [
            CENTER,
            polar_to_screen(angles[i - 1], max_dist()),
            polar_to_screen(angles[i], max_dist()),
        ]
        pygame.draw.polygon(screen, color, corners)


def draw_grid(screen, font):
    """Draw the rings, the angle lines, and their labels."""
    for step in range(1, 5):
        dist = max_dist() * step / 4
        r = int(dist / max_dist() * RADIUS)
        rect = (CENTER[0] - r, CENTER[1] - r, 2 * r, 2 * r)
        pygame.draw.arc(screen, RING_GREEN, rect, 0, math.pi, 1)
        label = font.render(f"{dist:g} cm", True, RING_GREEN)
        screen.blit(label, (CENTER[0] + 4, CENTER[1] - r - 18))
    for angle in range(0, 181, 30):
        pygame.draw.line(screen, RING_GREEN, CENTER, polar_to_screen(angle, max_dist()), 1)
        x, y = polar_to_screen(angle, max_dist() * 1.07)
        screen.blit(font.render(f"{angle}", True, RING_GREEN), (x - 10, y - 8))


def draw_points(screen, points, now):
    """Draw detected objects (green dots) and missing echoes (gray hollow circles)."""
    for angle, (distance, stamp) in points.items():
        age = now - stamp
        if age > FADE_SECONDS:
            continue
        fade = 1 - age / FADE_SECONDS
        if 2 <= distance <= max_dist():
            pygame.draw.circle(screen, (0, int(255 * fade), 0), polar_to_screen(angle, distance), 5)
        else:
            g = int(130 * fade)
            pygame.draw.circle(screen, (g, g, g), polar_to_screen(angle, max_dist()), 4, 1)


def handle_key(key):
    """Change settings when a key is pressed. Returns False when it is time to quit."""
    if key == pygame.K_ESCAPE:
        return False
    if key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
        settings["range_index"] = max(0, settings["range_index"] - 1)
    elif key in (pygame.K_MINUS, pygame.K_KP_MINUS):
        settings["range_index"] = min(len(RANGES) - 1, settings["range_index"] + 1)
    elif key == pygame.K_d:
        settings["mirror"] = not settings["mirror"]
    elif key == pygame.K_f:
        settings["filter"] = not settings["filter"]
    elif key == pygame.K_m:
        settings["sound"] = not settings["sound"]
    return True


def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=0.1)
    except serial.SerialException as error:
        print(f"Could not open {PORT}: {error}")
        print("Check that the ESP32 is plugged in, the port number is right in Device Manager,")
        print("and that the Arduino Serial Monitor and radar_read.py are closed.")
        return

    pygame.mixer.pre_init(44100, -16, 1, 512)
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("ESP32 Radar")
    font = pygame.font.SysFont("consolas", 16)
    big_font = pygame.font.SysFont("consolas", 22)
    clock = pygame.time.Clock()

    try:
        far_beep = make_beep(700)
        near_beep = make_beep(1200)
        sound_works = True
    except pygame.error:
        sound_works = False
        print("No sound device found, so the radar will run silently.")

    points = {}
    recent = deque(maxlen=3)
    trail = deque(maxlen=TRAIL_LENGTH)
    current_angle = 90
    current_distance = -1
    last_beep = 0
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                running = handle_key(event.key) and running

        for angle, distance in read_new_data(ser):
            if settings["filter"]:
                recent.append((angle, distance))
                if len(recent) < 3:
                    continue
                angle = recent[1][0]
                distance = sorted(d for _, d in recent)[1]

            points[angle] = (distance, time.time())
            trail.append(angle)
            current_angle = angle
            current_distance = distance

            if sound_works and settings["sound"] and 2 <= distance <= ALERT_DIST:
                gap = 0.15 + 0.6 * distance / ALERT_DIST
                if time.time() - last_beep >= gap:
                    if distance < ALERT_DIST / 3:
                        near_beep.play()
                    else:
                        far_beep.play()
                    last_beep = time.time()

        screen.fill(BLACK)
        draw_trail(screen, trail)
        draw_grid(screen, font)
        draw_points(screen, points, time.time())
        pygame.draw.line(screen, GREEN, CENTER, polar_to_screen(current_angle, max_dist()), 2)

        if 2 <= current_distance <= max_dist():
            dist_text = f"{current_distance:.1f} cm"
        else:
            dist_text = "no echo"
        readout = big_font.render(f"Angle: {current_angle}   Distance: {dist_text}", True, TEXT_GREEN)
        screen.blit(readout, (20, 20))

        status = (f"{max_dist()} cm | filter {'on' if settings['filter'] else 'off'}"
                  f" | sound {'on' if settings['sound'] and sound_works else 'off'}"
                  f" | {'mirrored' if settings['mirror'] else 'normal'}")
        screen.blit(font.render(status, True, TEXT_GREEN), (20, 50))
        help_text = "+ / -  zoom      D  flip left/right      F  filter      M  mute      Esc  quit"
        screen.blit(font.render(help_text, True, HELP_GRAY), (20, HEIGHT - 26))

        pygame.display.flip()
        clock.tick(60)

    ser.close()
    pygame.quit()


main()