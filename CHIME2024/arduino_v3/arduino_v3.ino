#include <Arduino.h>
#include <FastLED.h>

#define MAX_LEDS 48
#define NUM_LEDS_0 48
#define NUM_LEDS_1 48
#define NUM_LEDS_2 48
#define NUM_LEDS_3 48
#define NUM_LEDS_4 48
#define NUM_LEDS_5 48

#define LED_PIN_0 2
#define LED_PIN_1 3
#define LED_PIN_2 4
#define LED_PIN_3 5
#define LED_PIN_4 6
#define LED_PIN_5 7


// Timings
unsigned long startMillis1; 
unsigned long startMillis2; 
unsigned long currentMillis;
const unsigned long period1 = 10; 
const unsigned long period2 = 500; 

// Serial
const unsigned int serial_max_char = 20;

// LEDs
CRGB leds [6][MAX_LEDS];
int led_status [6][3] = {{0,0}, {0,0}, {0,0}, {0,0}, {0,0}, {0,0}};


int fetch_num_leds(int tube)
{
  if (tube == 0) {
    return NUM_LEDS_0;
  } else if (tube == 1) {
    return NUM_LEDS_1;
  } else if (tube == 2) {
    return NUM_LEDS_2;
  } else if (tube == 3) {
    return NUM_LEDS_3;
  } else if (tube == 4) {
    return NUM_LEDS_4;
  } else if (tube == 5) {
    return NUM_LEDS_5;
  } else {
    return MAX_LEDS;
  }
}

void light_tube(int tube, int hue, int brightness)
{
  int num_leds = fetch_num_leds(tube);
  for (int i = 0; i < num_leds; i++) {
    leds[tube][i] = CHSV(hue, 255, brightness);
    //FastLED.show();
  } 
}

void light_tube_number(int tnum, int hue, int brightness)
// Changes  light tube display based on tube number from 0 - 6
// Use tnum = 999 for all tubes
{
  if (tnum == 0 || tnum == 999)
  {
    light_tube(0, hue, brightness);
    led_status[0][0] = hue;
    led_status[0][1] = brightness;
  }
  if (tnum == 1 || tnum == 999)
  {
    light_tube(1, hue, brightness);
    led_status[1][0] = hue;
    led_status[1][1] = brightness;
  }
  if (tnum == 2 || tnum == 999)
  {
    light_tube(2, hue, brightness);
    led_status[2][0] = hue;
    led_status[2][1] = brightness;
  }
  if (tnum == 3 || tnum == 999)
  {
    light_tube(3, hue, brightness);
    led_status[3][0] = hue;
    led_status[3][1] = brightness;
  }
  if (tnum == 4 || tnum == 999)
  {
    light_tube(4, hue, brightness);
    led_status[4][0] = hue;
    led_status[4][1] = brightness;
  }
  if (tnum == 5 || tnum == 999)
  {
    light_tube(5, hue, brightness);
    led_status[5][0] = hue;
    led_status[5][1] = brightness;
  }

  //FastLED.show();
}

void sendledstatus() {
  int s = (sizeof(led_status) / sizeof(led_status[0]));
  for (int i=0; i<s; i++) 
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

  while (Serial.available() > 0) 
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

  return "";
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
  receivedMessage.trim();
  const int numTubes = 6;

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

void setup() {
  Serial.begin(9600);
  FastLED.addLeds<NEOPIXEL, LED_PIN_0>(leds[0], NUM_LEDS_0);
  FastLED.addLeds<NEOPIXEL, LED_PIN_1>(leds[1], NUM_LEDS_1);
  FastLED.addLeds<NEOPIXEL, LED_PIN_2>(leds[2], NUM_LEDS_2);
  FastLED.addLeds<NEOPIXEL, LED_PIN_3>(leds[3], NUM_LEDS_3);
  FastLED.addLeds<NEOPIXEL, LED_PIN_4>(leds[4], NUM_LEDS_4);
  FastLED.addLeds<NEOPIXEL, LED_PIN_5>(leds[5], NUM_LEDS_5);

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
  }

  if (currentMillis - startMillis2 >= period2) 
  {
    startMillis2 = currentMillis;
    // sendledstatus();
  }
    
}
