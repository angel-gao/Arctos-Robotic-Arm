// ===============================
//   Arduino CNC Shield - Z & X Axis
// ===============================

const int StepZ = 8;
const int DirZ  = 9;
const int StepX = 6;
const int DirX  = 7;

// -------- SETTINGS -------------
bool forward = true;     // true = rotate both forward, false = rotate backward
int speedDelay = 300;      // microseconds (smaller = faster)
// --------------------------------

void setup() {
  pinMode(StepZ, OUTPUT);
  pinMode(DirZ, OUTPUT);
  pinMode(StepX, OUTPUT);
  pinMode(DirX, OUTPUT);

  digitalWrite(DirZ, forward ? LOW : HIGH);
  digitalWrite(DirX, forward ? HIGH : LOW);
}

void loop() {
  digitalWrite(StepZ, HIGH);
  digitalWrite(StepX, HIGH);
  delayMicroseconds(speedDelay);

  digitalWrite(StepZ, LOW);
  digitalWrite(StepX, LOW);
  delayMicroseconds(speedDelay);
}