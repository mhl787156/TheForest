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
#define LED_PIN_1 6
#define LED_PIN_2 4
#define LED_PIN_3 18
#define LED_PIN_4 20
#define LED_PIN_5 22

#define NUM_CAPS 6

int buffer_clear_timeout = 100;
int buffer_count = 0;

// Timings
unsigned long startMillis1 = 0;
unsigned long currentMillis = 0;
const unsigned long period1 = 50;

// LEDs
CRGB leds[6][MAX_LEDS];
int led_status[6][3] = {{0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}, {0, 0, 0}}; // Add an extra element to track touch status
int touch_count[6] = {0, 0, 0, 0, 0, 0}; // Track the number of touches for each tube

// Cap sensors
const int cap_pins[6] = {1, 3, 5, 17, 19, 21};
const long capThresholds[6] = {64, 64, 64, 64, 64, 64}; // Adjusted threshold values for better performance
bool capStatus[6] = {0, 0, 0, 0, 0, 0};

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
  FastLED.show();
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

// const int fade[3] = {100, 25, 255};

// void feedback_flash(int tube, int hue) {
//   int hue_0 = (hue+125)%255;
//   light_tube_number(tube, hue_0, 255);
//   delay(300);
//   light_tube_number(tube, hue_0, 255);
//   delay(300);
// }

int fade_direction[6] = {1,1,1,1,1,1};

void parseledfromserial(bool capStatus[]) {
  for (int i = 0; i < 6; i++) {
    if (capStatus[i]) {
      touch_count[i]++;
      int hue = (touch_count[i] * 5) % 255; // Change color based on the number of touches
      // feedback_flash(i, hue);
      light_tube(i, hue, 255); // Bright flash with new color
      led_status[i][0] = hue;
      led_status[i][1] = 255;
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

long readCapWithAveraging(int pin) {
  long total = 0;
  const int numReadings = 5; // Number of readings to average

  for (int i = 0; i < numReadings; i++) {
    total += fastTouchRead(pin);
  }

  return total / numReadings; // Return the average reading
}

void readCap(long sensorVal, int capnum) {
  static long lastSensorVals[NUM_CAPS] = {0}; // For debouncing
  const long debounceThreshold = 5; // Adjust debounce threshold as needed

  if (abs(sensorVal - lastSensorVals[capnum]) > debounceThreshold) {
    lastSensorVals[capnum] = sensorVal;

    if (sensorVal >= capThresholds[capnum]) {
      // Cap activated
      capStatus[capnum] = 1;
    } else {
      // Cap not activated
      capStatus[capnum] = 0;
    }
  }
}

void readallcaps() {
  // Read capacitor sensors and send to Serial
  // Serial message in the form: "CAP,0,0,0,0,0,0"
  // Where each bool in array represents the cap status for each sensor (0 for off, 1 for on)
  for (int i = 0; i < NUM_CAPS; i++) {
    int pin = cap_pins[i];
    long sensorVal = readCapWithAveraging(pin);
    Serial.print("VAL");
    Serial.println(sensorVal);
    readCap(sensorVal, i);
  }

  // Send array of capStatus for each tube to Serial
  String capmsg = "CAP";
  for (bool status : capStatus) {
    capmsg += ",";
    capmsg += status;
  }
  Serial.println(capmsg);
}

// ------- Setup and loop

void setup() {
  Serial.begin(9600);

  Serial.println("Serial port initialized.");

  FastLED.addLeds<WS2812, LED_PIN_0>(leds[0], NUM_LEDS_0);
  FastLED.addLeds<WS2812, LED_PIN_1>(leds[1], NUM_LEDS_1);
  FastLED.addLeds<WS2812, LED_PIN_2>(leds[2], NUM_LEDS_2);
  FastLED.addLeds<WS2812, LED_PIN_3>(leds[3], NUM_LEDS_3);
  FastLED.addLeds<WS2812, LED_PIN_4>(leds[4], NUM_LEDS_4);
  FastLED.addLeds<WS2812, LED_PIN_5>(leds[5], NUM_LEDS_5);

  // Setup flash
  for (int i = 0; i < 3; i++) {
    light_tube_number(999, i * 85, 100); // Adjust hue to get distinct colors
    delay(300);
    light_tube_number(999, 0, 0);
    delay(300);
  }

  Serial.println("Finish setup!");

  // Clear buffer
  clear_buffer();
}

void loop() {
  currentMillis = millis();

  if (currentMillis - startMillis1 >= period1) {
    startMillis1 = currentMillis;
    readallcaps();
    parseledfromserial(capStatus); // Use the capStatus in parseledfromserial
    buffer_count = 0;
  }

  buffer_count += 1;
  if (buffer_count > buffer_clear_timeout) {
    clear_buffer();
    buffer_count = 0;
  }

  delay(50); // Short delay to avoid flooding the serial communication
}
