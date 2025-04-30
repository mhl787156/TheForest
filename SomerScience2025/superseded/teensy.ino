#include <FastTouch.h>

#define NUM_CAPS 6

// Timings
unsigned long startMillis1; 
unsigned long startMillis2; 
unsigned long currentMillis;
const unsigned long period = 10; 

// Cap sensors
const int cap_pins [6] = {6,7,8,9,10,11};
const int cap_values [6] = {0,0,0,0,0,0};
const int capThresholds [6] = {60,60,60,60,60,60};
bool capStatus [6] = {0,0,0,0,0,0};

void readCap (long sensorVal, int capnum) {

  if (sensorVal > capThresholds[capnum])
  {
    // Cap activated
    capStatus[capnum] = 1;
  }
  else
  {
    // Cap not activated
    capStatus[capnum] = 0;
  }
}

void readallcaps ()
// Read capacitor sensors and send to Serial
// Serial message in the form: "CAP,0,0,0,0,0,0,0"
// Where each bool in array represents the cap status for each sensor (0 for off, 1 for on)
{
  for (int i=0; i<NUM_CAPS ; i++)
  {
    int pin = cap_pins[i];
    int sensorVal = fastTouchRead(pin);
    readCap(sensorVal, i);
  }

  // Send array of capStatus for each tube to Serial
  String capmsg = "CAP";
  for (int i : capStatus)
  {
    capmsg += ",";
    capmsg += i;
  }
  Serial.println(capmsg);
}

void setup() {
  Serial.begin(9600);  
}

void loop() {
  
  currentMillis = millis(); 
  
  if (currentMillis - startMillis1 >= period) 
  {
    startMillis1 = currentMillis;
    readallcaps();
  }
}