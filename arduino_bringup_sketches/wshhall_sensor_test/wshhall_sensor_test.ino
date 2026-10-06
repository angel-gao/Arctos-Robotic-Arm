const int Npin = 53;
const int Spin = 51;

void setup() {
  Serial.begin(115200);
  pinMode(Npin, INPUT_PULLUP);  // important
  pinMode(Spin, INPUT_PULLUP);  // important
}

void loop() {
  int n = digitalRead(Npin);
  int s = digitalRead(Spin);

  Serial.print("N_OUT=");
  Serial.print(n);
  Serial.print("  S_OUT=");
  Serial.println(s);

  delay(100);
}