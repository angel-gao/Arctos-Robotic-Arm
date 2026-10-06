const int hallPin1 = 13;
const int hallPin2 = 12;

void setup() {
  pinMode(hallPin1, INPUT);
  pinMode(hallPin2, INPUT);
  Serial.begin(9600);
  Serial.println("KY-003 Dual Hall Sensor Test");
  Serial.println("Bring a magnet close to the sensors...");
}

void loop() {
  int val1 = digitalRead(hallPin1);
  int val2 = digitalRead(hallPin2);

  Serial.print("Sensor 1: ");
  Serial.print(val1 == LOW ? "DETECTED" : "No magnet");
  Serial.print("  |  Sensor 2: ");
  Serial.println(val2 == LOW ? "DETECTED" : "No magnet");

  delay(200);
}