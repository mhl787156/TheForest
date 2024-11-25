#include <Arduino.h>
#include <FastLED.h>
#include <CapacitiveSensor.h>

#define NUM_LEDS 48
#define LED_PIN 18
#define CLK_PIN 2
#define BRIGHTNESS 200

// Timings
unsigned long startMillis1; 
unsigned long startMillis2; 
unsigned long currentMillis;
const unsigned long period1 = 50; 
const unsigned long period2 = 500; 

// Serial
const unsigned int serial_max_char = 20;

// Cap sensors
CapacitiveSensor capSensor0 = CapacitiveSensor(0, 1);
CapacitiveSensor capSensor1 = CapacitiveSensor(2, 3);
CapacitiveSensor capSensor2 = CapacitiveSensor(4, 5);
CapacitiveSensor capSensor3 = CapacitiveSensor(6, 7);
CapacitiveSensor capSensor4 = CapacitiveSensor(8, 9);
CapacitiveSensor capSensor5 = CapacitiveSensor(10, 11);
CapacitiveSensor capSensor6 = CapacitiveSensor(12, 13); // TODO: capsensor 6 not reading - cases crashes and slow running

const long capThresholds [7] = {6000, 6000, 6000, 6000, 6000, 6000, 6000};
bool capStatus [7] = {0,0,0,0,0,0,0};

// LEDs
int global_hue = 100;
int pixel = 0;
CRGB leds[NUM_LEDS];
int led_status[7][3] = {{0,0}, {0,0}, {0,0}, {0,0}, {0,0}, {0,0}, {0,0}};

// Define pixel numbers for each tube
const int tube_0 [] = {8, 9, 10, 11, 12, 18, 19, 20, 21, 22, 23, 32, 33, 34, 35, 46, 47, 48};
const int tube_1 [] = {0, 1, 13, 14, 15};
const int tube_2 [] = {16, 17, 29, 30, 31};
const int tube_3 [] = {24, 25, 26, 27, 28};
const int tube_4 [] = {41, 42, 43, 44, 45};
const int tube_5 [] = {36, 37, 38, 39, 40};
const int tube_6 [] = {2, 3, 4, 5, 6, 7};

// Specify lengths of LED arrays
int len_centre = 18;
int len_outer = 5;

void light_tube(const int tube_array[], int size_array, int hue, int brightness)
{
  for (int i = 0; i < size_array; i++) {
    leds[tube_array[i]] = CHSV(hue, 255, brightness);
  FastLED.show();
  } 
}

void light_tube_number(int tnum, int hue, int brightness)
// Changes  light tube display based on tube number from 0 - 6
// Use tnum = 999 for all tubes
{
  if (tnum == 0 || tnum == 999)
  {
    light_tube(tube_0, len_centre, hue, brightness);
    led_status[0][0] = hue;
    led_status[0][1] = brightness;
  }
  else if (tnum == 1 || tnum == 999)
  {
    light_tube(tube_1, len_outer, hue, brightness);
    led_status[1][0] = hue;
    led_status[1][1] = brightness;
  }
  else if (tnum == 2 || tnum == 999)
  {
    light_tube(tube_2, len_outer, hue, brightness);
    led_status[2][0] = hue;
    led_status[2][1] = brightness;
  }
  else if (tnum == 3 || tnum == 999)
  {
    light_tube(tube_3, len_outer, hue, brightness);
    led_status[3][0] = hue;
    led_status[4][1] = brightness;
  }
  else if (tnum == 4 || tnum == 999)
  {
    light_tube(tube_4, len_outer, hue, brightness);
    led_status[4][0] = hue;
    led_status[4][1] = brightness;
  }
  else if (tnum == 5 || tnum == 999)
  {
    light_tube(tube_5, len_outer, hue, brightness);
    led_status[5][0] = hue;
    led_status[5][1] = brightness;
  }
  else if (tnum == 6 || tnum == 999)
  {
    light_tube(tube_6, len_outer, hue, brightness);
    led_status[6][0] = hue;
    led_status[6][1] = brightness;
  }

  FastLED.show();
}

void sendledstatus() {
  for (int i; i<(sizeof(led_status) / sizeof(led_status[0])); i++) 
  {
    Serial.println("LED," + String(i) + "," + String(led_status[i][0]) + "," + String(led_status[i][1]));
  }
}

String readserial()
// Read all serial buffer upto the character ';' or until message length exceeds 20 characters.
{
  const unsigned int max_message_length = 20;
  static unsigned int message_pos =0;
  static char message[max_message_length];

  while (Serial.available() == 0) 
  {
    char byte = Serial.read();

    if (byte != ';' && message_pos < max_message_length)
    {
      message[message_pos] = byte;
      message_pos++;
    }
    else
    {
      message_pos = 0;
      return message;
    }
  }
}  

void parseledfromserial()
// Expects message in form: "LED,<tubenum>,<hue>,<brightness>"
// Where <tubenum>, <hue> and <brightness> are integers
{
  //char receivedMessage[serial_max_char];
  //readserial(receivedMessage, sizeof(receivedMessage));
  String receivedMessage = readserial();

  if (receivedMessage[0] != '\0')
  { 
    //Serial.println(receivedMessage);
    int tubenum;
    int hue;
    int brightness;    
    // Parse message - LED
    if (receivedMessage.startsWith("LED,")) {
      String values = receivedMessage.substring(4); // Skip "LED,"
      int commaIndex1 = values.indexOf(',');
      int commaIndex2 = values.lastIndexOf(',');

      if (commaIndex1 != -1 && commaIndex2 != -1 && commaIndex1 < commaIndex2) {
        tubenum = values.substring(0, commaIndex1).toInt();
        hue = values.substring(commaIndex1 + 1, commaIndex2).toInt();
        brightness = values.substring(commaIndex2 + 1).toInt();
      }
    }

    // Light up tube
    light_tube_number(tubenum, hue, brightness);
  }
}

void readCap (long sensorVal, int capnum) {
  if (sensorVal > capThresholds[capnum])
  {
    // Cap activated
    capStatus[capnum] = 1;
    FastLED.clear();
  }
  else
  {
    // Cap not activated
    capStatus[capnum] = 0;
  }
}

void readallcaps ()
// Read capacitor sensors and send to Serial
// Serial message in the form: "CAP,[0,0,0,0,0,0,0]"
// Where each bool in array represents the cap status for each sensor (0 for off, 1 for on)
{
  long sensorVal = capSensor0.capacitiveSensor(3);
  readCap(sensorVal, 0);
  sensorVal = capSensor1.capacitiveSensor(3);
  readCap(sensorVal, 1);
  sensorVal = capSensor2.capacitiveSensor(3);
  readCap(sensorVal, 2);
  sensorVal = capSensor3.capacitiveSensor(3);
  readCap(sensorVal, 3);
  sensorVal = capSensor4.capacitiveSensor(3);
  readCap(sensorVal, 4);
  sensorVal = capSensor5.capacitiveSensor(3);
  readCap(sensorVal, 5);
  //sensorVal = capSensor6.capacitiveSensor(3);
  //readCap(sensorVal, 6);
  
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
  FastLED.clear();
  FastLED.addLeds<NEOPIXEL, LED_PIN>(leds, NUM_LEDS);  
  
  // TODO: calibration routine for the cap sensors
  
}

void loop() {
  
  currentMillis = millis(); 
  
  if (currentMillis - startMillis1 >= period1) 
  {
    startMillis1 = currentMillis;
    parseledfromserial();
    readallcaps();
  }

  if (currentMillis - startMillis2 >= period2) 
  {
    startMillis2 = currentMillis;
    sendledstatus();
  }

  
}
