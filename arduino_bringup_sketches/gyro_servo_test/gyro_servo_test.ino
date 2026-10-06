#include <Servo.h>

Servo gyro;

const int SERVO_PIN = 9;   // change to 13 if you really want
const int LEFT_US  = 800;  // one extreme
const int RIGHT_US = 2200; // the other extreme

void setup() {
  gyro.attach(SERVO_PIN);
}

void loop() {
  gyro.writeMicroseconds(LEFT_US);
  delay(2000);            // stay at extreme

  gyro.writeMicroseconds(RIGHT_US);
  delay(2000);
}