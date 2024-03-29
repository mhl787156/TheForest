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
const unsigned long period1 = 10; 
const unsigned long period2 = 500; 

// Serial
const unsigned int serial_max_char = 20;

// Cap sensors
CapacitiveSensor capSensor6 = CapacitiveSensor(0, 1);
CapacitiveSensor capSensor1 = CapacitiveSensor(2, 3);
CapacitiveSensor capSensor2 = CapacitiveSensor(4, 5);
CapacitiveSensor capSensor3 = CapacitiveSensor(6, 7);
CapacitiveSensor capSensor4 = CapacitiveSensor(8, 9);
CapacitiveSensor capSensor5 = CapacitiveSensor(10, 11);
//CapacitiveSensor capSensor6 = CapacitiveSensor(13, 12); // TODO: capsensor 6 not reading - swapped with 0 and removed for now

const long capThresholds [7] = {10000, 10000, 10000, 10000, 10000, 10000, 10000};
bool capStatus [7] = {0,0,0,0,0,0,0};

// LEDs
int global_hue = 100;
int pixel = 0;
CRGB leds[NUM_LEDS];
int led_status[7][3] = {{0,0}, {0,0}, {0,0}, {0,0}, {0,0}, {0,0}, {0,0}};

// Define pixel numbers for each tube
const int tube_0 [] = {7, 8, 9, 10, 11, 12, 18, 19, 20, 21, 22, 23, 32, 33, 34, 35, 47, 48};
const int tube_1 [] = {24, 25, 26, 27, 28};
const int tube_2 [] = {46, 42, 43, 44, 45};
const int tube_3 [] = {36, 37, 38, 39, 40};
const int tube_4 [] = {2, 3, 4, 5, 6, 1};
const int tube_5 [] = {0, 12, 13, 14, 15};
const int tube_6 [] = {16, 17, 29, 30, 31};

// Specify lengths of LED arrays
int len_centre = 18;
int len_outer = 5;

void light_tube(const int tube_array[], int size_array, int hue, int brightness)
{
  for (int i = 0; i < size_array; i++) {
    leds[tube_array[i]] = CHSV(hue, 255, brightness);
    //FastLED.show();
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
  if (tnum == 1 || tnum == 999)
  {
    light_tube(tube_1, len_outer, hue, brightness);
    led_status[1][0] = hue;
    led_status[1][1] = brightness;
  }
  if (tnum == 2 || tnum == 999)
  {
    light_tube(tube_2, len_outer, hue, brightness);
    led_status[2][0] = hue;
    led_status[2][1] = brightness;
  }
  if (tnum == 3 || tnum == 999)
  {
    light_tube(tube_3, len_outer, hue, brightness);
    led_status[3][0] = hue;
    led_status[4][1] = brightness;
  }
  if (tnum == 4 || tnum == 999)
  {
    light_tube(tube_4, len_outer, hue, brightness);
    led_status[4][0] = hue;
    led_status[4][1] = brightness;
  }
  if (tnum == 5 || tnum == 999)
  {
    light_tube(tube_5, len_outer, hue, brightness);
    led_status[5][0] = hue;
    led_status[5][1] = brightness;
  }
  if (tnum == 6 || tnum == 999)
  {
    light_tube(tube_6, len_outer, hue, brightness);
    led_status[6][0] = hue;
    led_status[6][1] = brightness;
  }

  //FastLED.show();
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
  const unsigned int max_message_length = 100;
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

// Function to parse a string into an array of substrings
int splitString(String input, char separator, String* output, int outputSize) {
  int partCount = 0;
  int startIndex = 0;
  int endIndex = input.indexOf(separator);

  while (endIndex >= 0 && partCount < outputSize) {
    output[partCount] = input.substring(startIndex, endIndex);
    partCount++;
    startIndex = endIndex + 1;
    endIndex = input.indexOf(separator, startIndex);
  }

  // Add the last part of the string if there is room in the output array
  if (partCount < outputSize) {
    output[partCount] = input.substring(startIndex);
    partCount++;
  }

  return partCount;
}

void parseledfromserial()
{
  String receivedMessage = readserial();
  const int numTubes = 7;

  // Check if message is for all tubes
  // Messageformat: 'ALLLED,hue0,brightness0,hue1,brightness1,hue2,brightness2,hue3,brightness3,hue4,brightness4,hue5,brightness5,hue6,brightness6'
  char messageArray[256];
  receivedMessage.toCharArray(messageArray, 256);

  char *token = strtok(messageArray, ",");
  if (token != NULL && strcmp(token, "ALLLED") == 0) {
    int ledHue[numTubes];
    int ledBrightness[numTubes];
    for (int i = 0; i < numTubes; i++) {
      token = strtok(NULL, ",");
      if (token != NULL) {
        ledHue[i] = atoi(token);
      }
      token = strtok(NULL, ",");
      if (token != NULL) {
        ledBrightness[i] = atoi(token);
      }
    }
    
    for (int i = 0; i < numTubes; i++) {
      int hue = ledHue[i];
      int brightness = ledBrightness[i];
      
      // Call the lightuptube function to light up the LED
      light_tube_number(i, hue, brightness); // Pass the LED index as 'tnum'
    }   
  }

  // Check if message is for single tube
  // Messageformat: 'LED,tnum,hue,brightness'
  else if (receivedMessage.startsWith("LED,")) {
      String values = receivedMessage.substring(4); // Skip "LED,"
      int commaIndex1 = values.indexOf(',');
      int commaIndex2 = values.lastIndexOf(',');

      if (commaIndex1 != -1 && commaIndex2 != -1 && commaIndex1 < commaIndex2) {
        int tnum = values.substring(0, commaIndex1).toInt();
        int hue = values.substring(commaIndex1 + 1, commaIndex2).toInt();
        int brightness = values.substring(commaIndex2 + 1).toInt();
        // Light up tube
        light_tube_number(tnum, hue, brightness);
      }
  }

  FastLED.show();

}

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
  long sensorVal = capSensor6.capacitiveSensor(3);
  readCap(sensorVal, 6);
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
  FastLED.addLeds<NEOPIXEL, LED_PIN>(leds, NUM_LEDS);  

  // Setup flash
  for (int i = 0; i<6; i++) {
    light_tube_number(999, i*20, 100);
    FastLED.show();
    delay(300);
    light_tube_number(999, 0, 0);
    FastLED.show();
    delay(300);
  }
  
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
    //sendledstatus();
  }
    
}
