#include <Arduino.h>
#include <FastLED.h>
#include <FastTouch.h>

#define MAX_LEDS 48
#define NUM_LEDS_0 48
#define NUM_LEDS_1 48
#define NUM_LEDS_2 48
#define NUM_LEDS_3 48
#define NUM_LEDS_4 48
#define NUM_LEDS_5 48

#define LED_PIN_0 1
#define LED_PIN_1 2
#define LED_PIN_2 3
#define LED_PIN_3 4
#define LED_PIN_4 5
#define LED_PIN_5 6

#define NUM_CAPS 6

int buffer_clear_timeout = 100;
int buffer_count = 0;

// Timings
unsigned long startMillis1; 
unsigned long startMillis2; 
unsigned long currentMillis;
const unsigned long period1 = 10; 
const unsigned long period2 = 500; 

// Serial
const unsigned int serial_max_char = 70;

// LEDs
CRGB leds [6][MAX_LEDS];
int led_status [6][3] = {{0,0}, {0,0}, {0,0}, {0,0}, {0,0}, {0,0}};

// Cap sensors
const int cap_pins [6] = {7,8,9,10,11,12};
const int cap_values [6] = {0,0,0,0,0,0};
const int capThresholds [6] = {60,60,60,60,60,60};
bool capStatus [6] = {0,0,0,0,0,0};

// ------- LED code

void light_tube(int tube, int hue, int brightness) {
  int num_leds = NUM_LEDS_0;
  switch (tube) {
    case 0: num_leds = NUM_LEDS_0; break;
    case 1: num_leds = NUM_LEDS_1; break;
    case 2: num_leds = NUM_LEDS_2; break;
    case 3: num_leds = NUM_LEDS_3; break;
    case 4: num_leds = NUM_LEDS_4; break;
    case 5: num_leds = NUM_LEDS_5; break;
  }
  num_leds = min(num_leds, MAX_LEDS); // Ensure we don't go beyond MAX_LEDS
  for (int i = 0; i < num_leds; i++) {
    leds[tube][i] = CHSV(hue, 255, brightness);
  }
}

String readserial() {
  const unsigned int max_message_length = 50;
  static char message[max_message_length + 1]; // +1 for null terminator
  static unsigned int messagePos = 0;
  static unsigned long lastReadTime = 0;
  const unsigned long timeout = 1000; // Timeout in milliseconds

  while (Serial.available() > 0 && messagePos < max_message_length) {
    char byte = Serial.read();
    if (byte == ';') {
      message[messagePos] = '\0'; // Null-terminate the string
      String receivedMessage(message);
      messagePos = 0; // Reset message position for next message
      lastReadTime = millis(); // Reset timeout
      return receivedMessage;
    } else if (byte == '\n' || byte == '\r') {
      // Ignore newline and carriage return characters
      continue;
    } else {
      message[messagePos] = byte;
      messagePos++;
    }
  }

  // Check for timeout
  if (millis() - lastReadTime > timeout) {
    messagePos = 0; // Reset message position
  }

  return ""; // Return empty string if no complete message received
}

void light_tube_number(int tnum, int hue, int brightness) {
  for (int i = 0; i < 6; i++) {
    if (tnum == i || tnum == 999) {
      light_tube(i, hue, brightness);
      led_status[i][0] = hue;
      led_status[i][1] = brightness;
    }
  }
}

void sendledstatus() {
  for (int i = 0; i < 6; i++) {
    Serial.println("LED," + String(i) + "," + String(led_status[i][0]) + "," + String(led_status[i][1]));
  }
}

void parseledfromserial() {
  char receivedMessage[serial_max_char];
  static int messagePos = 0;
 
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    if (inChar == ';') {
      receivedMessage[messagePos] = '\0';
      messagePos = 0;
 
      if (receivedMessage[0] == 'A' && receivedMessage[1] == 'L' && receivedMessage[2] == 'L' && receivedMessage[3] == 'L' && receivedMessage[4] == 'E' && receivedMessage[5] == 'D' && receivedMessage[6] == ',') {
        int hue1, brightness1, hue2, brightness2, hue3, brightness3, hue4, brightness4, hue5, brightness5, hue6, brightness6;
        sscanf(&receivedMessage[7], "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d", &hue1, &brightness1, &hue2, &brightness2, &hue3, &brightness3, &hue4, &brightness4, &hue5, &brightness5, &hue6, &brightness6);
        light_tube(0, hue1, brightness1);
        light_tube(1, hue2, brightness2);
        light_tube(2, hue3, brightness3);
        light_tube(3, hue4, brightness4);
        light_tube(4, hue5, brightness5);
        light_tube(5, hue6, brightness6);
        
      } else if (receivedMessage[0] == 'L' && receivedMessage[1] == 'E' && receivedMessage[2] == 'D' && receivedMessage[3] == ',') {
        int tnum, hue, brightness;
        sscanf(&receivedMessage[4], "%d,%d,%d", &tnum, &hue, &brightness);
        if (tnum >= 0 && tnum < 6) {
          light_tube(tnum, hue, brightness);
        }
      }
    } else if (inChar != '\r' && messagePos < serial_max_char - 1) {
      receivedMessage[messagePos++] = inChar;
    }
  }
  FastLED.show();
}


void clear_buffer() {
   // Clear the buffer
  while (Serial.available()) {
    Serial.read();
  } 
}

// ------- Sensing code

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

// ------- Setup and loop

void setup() {
  Serial.begin(9600);
  FastLED.addLeds<WS2811, LED_PIN_0>(leds[0], NUM_LEDS_0);
  FastLED.addLeds<WS2811, LED_PIN_1>(leds[1], NUM_LEDS_1);
  FastLED.addLeds<WS2811, LED_PIN_2>(leds[2], NUM_LEDS_2);
  FastLED.addLeds<WS2811, LED_PIN_3>(leds[3], NUM_LEDS_3);
  FastLED.addLeds<WS2811, LED_PIN_4>(leds[4], NUM_LEDS_4);
  FastLED.addLeds<WS2811, LED_PIN_5>(leds[5], NUM_LEDS_5);

  // Setup flash
  for (int i = 0; i < 6; i++) {
    light_tube_number(999, i * 20, 100);
    FastLED.show();
    delay(300);
    light_tube_number(999, 0, 0);
    FastLED.show();
    delay(300);
  }

   // Clear buffer
   clear_buffer();

}

void loop() {
  currentMillis = millis(); 
    
  if (currentMillis - startMillis1 >= period1) {

      
    if (Serial.available()) {
          
      startMillis1 = currentMillis;
      readallcaps();
      parseledfromserial();
      buffer_count = 0;
    }
    else {
      buffer_count += 1;
      if (buffer_count > buffer_clear_timeout) {
        clear_buffer();
      }
    }
  }


  /*if (currentMillis - startMillis2 >= period2) {
    startMillis2 = currentMillis;
    // sendledstatus();
  }*/
}
