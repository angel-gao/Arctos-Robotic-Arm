// ===============================
//   Arduino CNC Shield - Z Axis
// ===============================

const int StepZ = 8;
const int DirZ  = 9;


// -------- SETTINGS -------------
bool clockwise = false;     // true = CW, false = CCW
int speedDelay = 300;      // microseconds (smaller = faster)
// --------------------------------

void setup() {
  pinMode(StepZ, OUTPUT);
  pinMode(DirZ, OUTPUT);

  digitalWrite(DirZ, clockwise ? HIGH : LOW);
}

void loop() {

  digitalWrite(StepZ, HIGH);
  delayMicroseconds(speedDelay);
  digitalWrite(StepZ, LOW);
  delayMicroseconds(speedDelay);

}