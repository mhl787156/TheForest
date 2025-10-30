#include <FastLED.h>

#define CHIPSET WS2811
#define NUM_STRIPS 6
#define NUM_LEDS_PER_STRIP 25
#define MAX_LEDS 25
#define BRIGHTNESS 60
#define COLOR_ORDER GRB
#define NUM_BUTTONS 4


#define LED_PIN_0 2
#define LED_PIN_1 3
#define LED_PIN_2 4
#define LED_PIN_3 5
#define LED_PIN_4 6
#define LED_PIN_5 7

const uint8_t BUTTON_PINS[NUM_BUTTONS] PROGMEM = {9, 10, 11, 12};


uint8_t pattern = 0;
uint8_t counter = 0;

// Declare LED array
CRGB leds[NUM_STRIPS][NUM_LEDS_PER_STRIP];
uint8_t buttonState[NUM_BUTTONS] = {0};

// Star pattern definitions
// Star effects
#define star_brightness 50
#define MAX_STARS 10       // Max number of active stars per strip
#define STAR_ON_TIME 500  // Time a star stays ON (milliseconds)
int star_id[6] = { 0 };

void setup() {
  Serial.begin(115200);
  
  // Configure buttons
  for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
    pinMode(pgm_read_byte(&BUTTON_PINS[i]), INPUT_PULLUP);
  }
  
  // Configure LEDs - each strip gets its own array
  FastLED.addLeds<CHIPSET, 2, COLOR_ORDER>(leds[0], NUM_LEDS_PER_STRIP);
  FastLED.addLeds<CHIPSET, 3, COLOR_ORDER>(leds[1], NUM_LEDS_PER_STRIP);
  FastLED.addLeds<CHIPSET, 4, COLOR_ORDER>(leds[2], NUM_LEDS_PER_STRIP);
  FastLED.addLeds<CHIPSET, 5, COLOR_ORDER>(leds[3], NUM_LEDS_PER_STRIP);
  FastLED.addLeds<CHIPSET, 6, COLOR_ORDER>(leds[4], NUM_LEDS_PER_STRIP);
  FastLED.addLeds<CHIPSET, 7, COLOR_ORDER>(leds[5], NUM_LEDS_PER_STRIP);

  FastLED.setBrightness(BRIGHTNESS);
  FastLED.setMaxPowerInVoltsAndMilliamps(5, 450);
  FastLED.clear();
  FastLED.show();

  // Quick initialization test - single flash instead of 3
  for (int strip = 0; strip < NUM_STRIPS; strip++) {
    fill_solid(leds[strip], NUM_LEDS_PER_STRIP, CRGB::Green);
  }
  FastLED.show();
  delay(500);
  FastLED.clear();
  FastLED.show();
  
  Serial.println(F("Ready"));
}

void loop() {
  static uint8_t lastButtonState[NUM_BUTTONS] = {0};
  static unsigned long lastButtonTime = 0;
  static unsigned long lastSendTime = 0;
  
  // Send button states every 100ms
  if (millis() - lastSendTime > 100) {
    sendButtonStateToPi();
    lastSendTime = millis();
  }
  
  if (millis() - lastButtonTime > 50) { // Reduced debounce time
    bool buttonChanged = false;
    
    for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
      uint8_t currentState = !digitalRead(pgm_read_byte(&BUTTON_PINS[i]));
      
      // Only process on button press (rising edge)
      if (currentState && !lastButtonState[i]) {
        handleButtonPress(i);
        buttonChanged = true;
      }
      lastButtonState[i] = currentState;
    }
    
    if (buttonChanged) {
      lastButtonTime = millis();
    }
  }

  // Run pattern
  switch(pattern) {
    case 0: rainbow(); break;  // Default pattern
    case 1: chasePattern(); break;    // Button 1
    case 2: blink(); break;    // Button 2
    case 3: fadePattern(); break;     // Button 3
    case 4: flickerStars(); break;  // Button 4 
  }
  
  FastLED.show();
  delay(50);
  counter++;


  // Less frequent memory management
  static unsigned long lastMemoryCheck = 0;
  if (millis() - lastMemoryCheck > 60000) { // Check every minute
    if (getFreeRAM() < 200) { // If RAM is low
      Serial.println(F("Low RAM - clearing"));
      FastLED.clear();
      FastLED.show();
    }
    lastMemoryCheck = millis();
  }

  // Debug info less frequently
  static unsigned long lastDebug = 0;
  if (millis() - lastDebug > 10000) { // Every 10 seconds
    Serial.print(F("RAM: "));
    Serial.print(getFreeRAM());
    Serial.print(F(" Pattern: "));
    Serial.println(pattern);
    lastDebug = millis();
  }
}

void handleButtonPress(uint8_t buttonIndex) {
  FastLED.clear();
  pattern = buttonIndex + 1;
  
  Serial.print(F("Button "));
  Serial.print(buttonIndex + 1);
  Serial.print(F(" -> Pattern "));
  Serial.println(pattern);
  
  // Send button state to Raspberry Pi
  sendButtonStateToPi();
}

void sendButtonStateToPi() {
  // Read current button states
  uint8_t buttonStates[NUM_BUTTONS];
  for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
    buttonStates[i] = !digitalRead(pgm_read_byte(&BUTTON_PINS[i]));
  }
  
  // Send button state array to Pi
  Serial.print(F("BUTTONS:"));
  for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
    Serial.print(buttonStates[i]);
    if (i < NUM_BUTTONS - 1) {
      Serial.print(F(","));
    }
  }
  Serial.println();
}

// Function to check available RAM
int getFreeRAM() {
  extern int __heap_start, *__brkval;
  int v;
  return (int) &v - (__brkval == 0 ? (int) &__heap_start : (int) __brkval);
}

void rainbow() {
  for(int strip = 0; strip < NUM_STRIPS; strip++) {
    for(int i = 0; i < NUM_LEDS_PER_STRIP; i++) {
      leds[strip][i] = CHSV((counter + i) % 255, 255, 255);
    }
  }
}

void chasePattern() {
  FastLED.clear();
  static int color_cnt = 0;  // Make static so it persists between calls
  
  for(int strip = 0; strip < NUM_STRIPS; strip++) {
    // Each strip gets a different color offset - increased spacing
    int stripOffset = strip * 23;  // 42 hue units between strips (255/6 ≈ 42)
    
    // Use higher saturation and more distinct color differences
    leds[strip][counter % NUM_LEDS_PER_STRIP] = CHSV(stripOffset + counter, 255, 255);
    leds[strip][(counter + 1) % NUM_LEDS_PER_STRIP] = CHSV(stripOffset + counter + 5, 255, 255);
    leds[strip][(counter + 2) % NUM_LEDS_PER_STRIP] = CHSV(stripOffset + counter + 11, 255, 255);
  }
  
  // Increment color counter every few frames for slower color cycling
  if (counter % 5 == 0) {
    color_cnt += 5;
  }
}

void blink() {
  if (counter % 20 < 10) {
    for(int strip = 0; strip < NUM_STRIPS; strip++) {
      fill_solid(leds[strip], NUM_LEDS_PER_STRIP, CRGB::White);
    }
  } else {
    FastLED.clear();
  }
}

void fadePattern() {
  // Slow down the fade by using a smaller multiplier
  uint8_t brightness = sin8(counter * 0.02); 
  for(int strip = 0; strip < NUM_STRIPS; strip++) {
    fill_solid(leds[strip], NUM_LEDS_PER_STRIP, CHSV(counter, 255, brightness));
  }
}

void flickerStars() {
  static int starPositions[NUM_STRIPS][MAX_STARS] = { 0 };         // Store star positions
  static unsigned long starTimers[NUM_STRIPS][MAX_STARS] = { 0 };  // Store when they turned on
  static bool starStates[NUM_STRIPS][MAX_STARS] = { false };       // Track ON/OFF state for stars
  static uint8_t starBrightness[NUM_STRIPS][MAX_STARS] = { 0 };    // Track brightness for fade effect

  unsigned long now = millis();

  // Process each strip independently
  for (int strip = 0; strip < NUM_STRIPS; strip++) {
    for (int i = 0; i < MAX_STARS; i++) {
      if (starStates[strip][i]) {
        // Star is ON - check if it should turn off
        if (now - starTimers[strip][i] > STAR_ON_TIME) {
          // Fade out
          if (starBrightness[strip][i] > 0) {
            starBrightness[strip][i] -= 20; // Fade out gradually
            leds[strip][starPositions[strip][i]] = CHSV(0, 100, starBrightness[strip][i]);
          } else {
            starStates[strip][i] = false; 
            leds[strip][starPositions[strip][i]] = CRGB::Black;  
          }
        } else {
          // Star is still ON - fade in if needed
          if (starBrightness[strip][i] < star_brightness) {
            starBrightness[strip][i] +=255; // Fade in gradually
          }
          leds[strip][starPositions[strip][i]] = CHSV(100, 100, starBrightness[strip][i]);
        }
      } else {
        // Star is OFF - randomly turn on
        if (random(0, 100) < 3) {  // Small chance per frame to create a new star
          starPositions[strip][i] = random(0, NUM_LEDS_PER_STRIP); 
          starStates[strip][i] = true; 
          starTimers[strip][i] = now; 
          starBrightness[strip][i] = 0; // Start at 0 brightness for fade in
        }
      }
    }
  }
}