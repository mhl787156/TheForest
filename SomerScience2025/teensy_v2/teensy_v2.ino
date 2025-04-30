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

#define LED_PIN_0 2
#define LED_PIN_1 4
#define LED_PIN_2 6
#define LED_PIN_3 18
#define LED_PIN_4 20
#define LED_PIN_5 22

#define NUM_CAPS 6

int buffer_clear_timeout = 100;
int buffer_count = 0;

// Timings
unsigned long startMillis0 = 0;
unsigned long startMillis1 = 0;
unsigned long startMillis2 = 0;
unsigned long currentMillis;
const unsigned long period0 = 200;  // Polling for colour changes from python
const unsigned long period1 = 50;   // Checking touch sensor status
const unsigned long period2 = 50;   // Updating lights based on touch sensor status (effect speed)

// Serial
const unsigned int serial_max_char = 150;

// LEDs
CRGB leds[6][MAX_LEDS];
int led_status[6][3] = { { 0, 0 }, { 0, 0 }, { 0, 0 }, { 0, 0 }, { 0, 0 }, { 0, 0 } };
int tube[6][3] = { { 0, 200, 0 }, { 0, 200, 0 }, { 0, 200, 0 }, { 0, 200, 0 }, { 0, 200, 0 }, { 0, 200, 0 } };
int tube1[3] = { 0, 200, 0 };
int tube2[3] = { 0, 200, 0 };
int tube3[3] = { 0, 200, 0 };
int tube4[3] = { 0, 200, 0 };
int tube5[3] = { 0, 200, 0 };
int tube6[3] = { 0, 200, 0 };

// Star effects
#define star_brightness 240
#define MAX_STARS 3       // Max number of active stars per tube
#define STAR_ON_TIME 500  // Time a star stays ON (milliseconds)
int star_id[6] = { 0 };
#define STAR_SIZE 3 

// Cap sensors
const int cap_pins[6] = { 1, 3, 5, 17, 19, 21 };  //17 nbot 16
const int cap_values[6] = { 0, 0, 0, 0, 0, 0 };
const int capThresholds[6] = { 60, 60, 60, 60, 60, 60 };
bool capStatus[6] = { 0, 0, 0, 0, 0, 0 };
int capDecay_LED[6] = { 0, 0, 0, 0, 0, 0 };
int capDecay_Serial[6] = { 0, 0, 0, 0, 0, 0 };
int progress[NUM_CAPS] = { 0, 0, 0, 0, 0, 0 };

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
  num_leds = min(num_leds, MAX_LEDS);  // Ensure we don't go beyond MAX_LEDS
  for (int i = 0; i < num_leds; i++) {
    leds[tube][i] = CHSV(hue, 255, brightness);
  }
}

String readserial() {
  const unsigned int max_message_length = 50;
  static char message[max_message_length + 1];  // +1 for null terminator
  static unsigned int messagePos = 0;
  static unsigned long lastReadTime = 0;
  const unsigned long timeout = 1000;  // Timeout in milliseconds

  while (Serial.available() > 0 && messagePos < max_message_length) {
    char byte = Serial.read();
    if (byte == ';') {
      message[messagePos] = '\0';  // Null-terminate the string
      String receivedMessage(message);
      messagePos = 0;           // Reset message position for next message
      lastReadTime = millis();  // Reset timeout
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
    messagePos = 0;  // Reset message position
  }

  return "";  // Return empty string if no complete message received
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
    led_status[i][0] = tube[i][0];
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

      if (strncmp(receivedMessage, "ALLLED,", 7) == 0) {
        int hue1, brightness1, effect1, hue2, brightness2, effect2, hue3, brightness3, effect3, hue4, brightness4, effect4, hue5, brightness5, effect5, hue6, brightness6, effect6;
        sscanf(&receivedMessage[7], "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d",
               &hue1, &brightness1, &effect1,
               &hue2, &brightness2, &effect2,
               &hue3, &brightness3, &effect3,
               &hue4, &brightness4, &effect4,
               &hue5, &brightness5, &effect5,
               &hue6, &brightness6, &effect6);

        // Update global variables for tube settings
        tube[0][0] = hue1;
        tube[0][1] = brightness1;
        tube[0][2] = effect1;
        tube[1][0] = hue2;
        tube[1][1] = brightness2;
        tube[1][2] = effect2;
        tube[2][0] = hue3;
        tube[2][1] = brightness3;
        tube[2][2] = effect3;
        tube[3][0] = hue4;
        tube[3][1] = brightness4;
        tube[3][2] = effect4;
        tube[4][0] = hue5;
        tube[4][1] = brightness5;
        tube[4][2] = effect5;
        tube[5][0] = hue6;
        tube[5][1] = brightness6;
        tube[5][2] = effect6;
      }
    } else if (inChar != '\r' && messagePos < serial_max_char - 1) {
      receivedMessage[messagePos++] = inChar;
    }
  }
}

void clear_buffer() {
  // Clear the buffer
  while (Serial.available()) {
    Serial.read();
  }
}

void flickerStars(int t) {
  static int starPositions[6][MAX_STARS] = { 0 };
  static unsigned long starTimers[6][MAX_STARS] = { 0 };
  static bool starStates[6][MAX_STARS] = { false };

  unsigned long now = millis();

  for (int i = 0; i < MAX_STARS; i++) {
    if (starStates[t][i]) {
      if (now - starTimers[t][i] > STAR_ON_TIME) {
        starStates[t][i] = false;
        // Turn off all LEDs in this star's range
        for (int j = 0; j < STAR_SIZE; j++) {
          int pos = starPositions[t][i] + j;
          if (pos < MAX_LEDS) {
            leds[t][pos] = CRGB::Black;
          }
        }
      }
    } else {
      if (random(0, 100) < 5) {
        int startPos = random(0, MAX_LEDS - STAR_SIZE + 1);  // Avoid overflow
        starPositions[t][i] = startPos;
        starStates[t][i] = true;
        starTimers[t][i] = now;
      }
    }

    // Apply star effect if active
    if (starStates[t][i]) {
      for (int j = 0; j < STAR_SIZE; j++) {
        int pos = starPositions[t][i] + j;
        if (pos < MAX_LEDS) {
          leds[t][pos] = CHSV(tube[i][0], 250, star_brightness);
        }
      }
    }
  }
}


// ------- Sensing code

void readCap(long sensorVal, int capnum) {

  if (sensorVal > capThresholds[capnum]) {
    // Cap activated
    capStatus[capnum] = 1;
  } else {
    // Cap not activated
    capStatus[capnum] = 0;
  }
}

void readallcaps() {
  // Read capacitor sensors
  for (int i = 0; i < NUM_CAPS; i++) {
    int pin = cap_pins[i];
    int sensorVal = fastTouchRead(pin);
    readCap(sensorVal, i);  // Updates capStatus[i] based on threshold

    // Use 'decay' to avoid noisy signals
    // The touch sensors when held down return a mix of 1s and 0s instead of only 1s
    // They decay means that for each 1 that is received, the system will return 5 more 1s, overwriting groups of 1-4 0s in a row
    // If 50s or more are received - return back to 0
    if (capStatus[i]) {
      capDecay_Serial[i] = 5;
    } else {
      capDecay_Serial[i] = max(capDecay_Serial[i] - 1, 0);
    }
  }

  // Send array of capStatus with serial-specific filtering applied
  String capmsg = "CAP";
  for (int i = 0; i < NUM_CAPS; i++) {
    int filteredCapStatus = (capDecay_Serial[i] > 0) ? 1 : 0;  // Keep it at 1 unless decay reaches 0
    capmsg += "," + String(filteredCapStatus);
  }

  Serial.println(capmsg);
}

// ------- Setup and loop

void setup() {
  Serial.begin(9600);
  FastLED.addLeds<WS2811, LED_PIN_0, GRB>(leds[0], NUM_LEDS_0);
  FastLED.addLeds<WS2811, LED_PIN_1, GRB>(leds[1], NUM_LEDS_1);
  FastLED.addLeds<WS2811, LED_PIN_2, GRB>(leds[2], NUM_LEDS_2);
  FastLED.addLeds<WS2811, LED_PIN_3, GRB>(leds[3], NUM_LEDS_3);
  FastLED.addLeds<WS2811, LED_PIN_4, GRB>(leds[4], NUM_LEDS_4);
  FastLED.addLeds<WS2811, LED_PIN_5, GRB>(leds[5], NUM_LEDS_5);

  // Setup flash
  for (int i = 0; i < 6; i++) {
    light_tube_number(999, i * 20, 100);
    FastLED.show();
    delay(200);
    light_tube_number(999, 0, 0);
    FastLED.show();
    delay(200);
  }

  // Clear buffer
  clear_buffer();
}

void loop() {
  currentMillis = millis();


  // Read serial data to update tube colors and effects
  if (currentMillis - startMillis0 >= period0) {
    startMillis0 = currentMillis;
    parseledfromserial();
  }

  // Read capacitive sensors
  if (currentMillis - startMillis1 >= period1) {
    startMillis1 = currentMillis;
    readallcaps();
    sendledstatus();
  }

  // Loop through each tube and update LEDs
  if (currentMillis - startMillis2 >= period2) {
    startMillis2 = currentMillis;

    for (int i = 0; i < NUM_CAPS; i++) {

      // Use 'decay' to avoid noisy signals
      // The touch sensors when held down return a mix of 1s and 0s instead of only 1s
      // They decay means that for each 1 that is received, the system will return 5 more 1s, overwriting groups of 1-4 0s in a row
      // If 50s or more are received - return back to 0
      if (!capStatus[i]) {
        capDecay_LED[i] = max(capDecay_LED[i] - 1, 0);
      } else {
        capDecay_LED[i] = 3;  // Reset decay counter when touch is detected
        
      }

      if (capStatus[i] || capDecay_LED[i] > 0) {

        for (int j = 0; j < MAX_LEDS; j++) {
          leds[i][j] = CRGB::Black;
        }

        // If the sensor is active OR still in decay period, keep the tube lighting up
        progress[i] = min(progress[i] + 2, MAX_LEDS);

        for (int j = 0; j < progress[i]; j++) {
          leds[i][j] = CHSV(tube[i][0], 255, tube[i][1]);  // Use stored hue & brightness
        }

      } else {
        // Turn off LEDs and go back to flicker stars
        if (progress[i] > 0) {
          progress[i] = 0;
          for (int j = 0; j < MAX_LEDS; j++) {
            leds[i][j] = CRGB::Black;
          }
          tube[i][0] += 10 % 255;
        }
        flickerStars(i);
      }
    }
  }

  // Update LEDs
  FastLED.show();
}
