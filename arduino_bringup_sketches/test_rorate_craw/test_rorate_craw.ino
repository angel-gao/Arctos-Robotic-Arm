// ===============================
//   Arduino CNC Shield - Z & X Axis
// ===============================

const int StepZ = 8;
const int DirZ  = 9;
const int StepX = 6;
const int DirX  = 7;

// -------- SETTINGS -------------
bool clockwise = true;     // true = CW, false = CCW
int speedDelay = 500;      // microseconds (smaller = faster)
// --------------------------------

void setup() {
  pinMode(StepZ, OUTPUT);
  pinMode(DirZ, OUTPUT);
  pinMode(StepX, OUTPUT);
  pinMode(DirX, OUTPUT);

  digitalWrite(DirZ, clockwise ? HIGH : LOW);
  digitalWrite(DirX, clockwise ? HIGH : LOW);
}

void loop() {
  digitalWrite(StepZ, HIGH);
  digitalWrite(StepX, HIGH);
  delayMicroseconds(speedDelay);

  digitalWrite(StepZ, LOW);
  digitalWrite(StepX, LOW);
  delayMicroseconds(speedDelay);
}