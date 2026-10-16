#include <ESP32Servo.h>

const int TRIG_PIN = 25;
const int ECHO_PIN = 26;
const int SERVO_PIN = 27;

const int MIN_ANGLE = 30;
const int MAX_ANGLE = 150;
const int STEP = 2;

Servo radarServo;

float measureDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);

  long duration = pulseIn(ECHO_PIN, HIGH, 30000);
  if (duration == 0) {
    return -1;
  }
  return duration * 0.0343 / 2;
}

void scanAt(int angle) {
  radarServo.write(angle);
  delay(40);
  float distance = measureDistance();
  Serial.print(angle);
  Serial.print(",");
  Serial.println(distance);
}

void setup() {
  Serial.begin(115200);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  radarServo.attach(SERVO_PIN, 500, 2400);
}

void loop() {
  for (int angle = MIN_ANGLE; angle <= MAX_ANGLE; angle += STEP) {
    scanAt(angle);
  }
  for (int angle = MAX_ANGLE; angle >= MIN_ANGLE; angle -= STEP) {
    scanAt(angle);
  }
}