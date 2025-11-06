#include <FastLED.h>

#define CHIPSET WS2811
#define NUM_STRIPS 5
#define NUM_LEDS_PER_STRIP 30
#define MAX_LEDS 30
#define BRIGHTNESS 60
#define COLOR_ORDER GRB
#define NUM_BUTTONS 4


#define LED_PIN_0 4
#define LED_PIN_1 5
#define LED_PIN_2 6
#define LED_PIN_3 7
#define LED_PIN_4 8
#define LED_PIN_5 13

const uint8_t BUTTON_PINS[NUM_BUTTONS] PROGMEM = {9, 10, 11, 12};

uint8_t counter = 0;
uint16_t active_pulse_period = 3000;
uint8_t default_hue = 0; // Set the base colour for the node
uint8_t contrast_hue = 100; // Set the colour for the pulse

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
    Serial.println(BUTTON_PINS[i]);
  }
  
  // Configure LEDs - each strip gets its own array
  FastLED.addLeds<CHIPSET, LED_PIN_0, COLOR_ORDER>(leds[0], NUM_LEDS_PER_STRIP);
  FastLED.addLeds<CHIPSET, LED_PIN_1, COLOR_ORDER>(leds[1], NUM_LEDS_PER_STRIP);
  FastLED.addLeds<CHIPSET, LED_PIN_2, COLOR_ORDER>(leds[2], NUM_LEDS_PER_STRIP);
  FastLED.addLeds<CHIPSET, LED_PIN_3, COLOR_ORDER>(leds[3], NUM_LEDS_PER_STRIP);
  FastLED.addLeds<CHIPSET, LED_PIN_4, COLOR_ORDER>(leds[4], NUM_LEDS_PER_STRIP);
  // FastLED.addLeds<CHIPSET, LED_PIN_5, COLOR_ORDER>(leds[5], NUM_LEDS_PER_STRIP);

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
  
  Serial.println(F("Ready"));
}

void loop() {
  static uint8_t lastButtonState[NUM_BUTTONS] = {0};
  static unsigned long lastButtonTime = 0;
  static unsigned long lastSendTime = 0;
  static uint8_t buttonPressCounts = 0; // The cumulative count for button presses
  static uint16_t ledState[NUM_STRIPS] = {0};
  static uint8_t activeStrips = 0;

  // Send button states every 100ms
  if (millis() - lastSendTime > 100) {
    sendButtonStateToPi();
    lastSendTime = millis();
  }
  
  // Handle button press events
  if (millis() - lastButtonTime > 50) { // Reduced debounce time
    bool buttonChanged = false;
    
    for (uint8_t i = 0; i < NUM_BUTTONS; i++) {
      uint8_t currentState = !digitalRead(pgm_read_byte(&BUTTON_PINS[i]));
      
      // Only process on button press (rising edge)
      if (currentState && !lastButtonState[i]) {
        handleButtonPress(i);
        buttonChanged = true;
        // Check if led strip inactive
        if (ledState[i] == 0) {
          ledState[i] = active_pulse_period;
        }
        activeStrips++;
        buttonPressCounts++;
      }
      lastButtonState[i] = currentState;
    }
    
    if (buttonChanged) {
      lastButtonTime = millis();
    }

    // If no button is triggered, then go back to default pattern
    // But wait (active_pulse_period) s to allow the trigger pattern to complete
    else if (millis() - lastButtonTime > active_pulse_period) {
      buttonPressCounts = 0;
      activeStrips = 0;
      for (uint8_t strip = 0; strip < NUM_STRIPS; strip++) {
        ledState[strip] = 0;
      }
    }
  }
  
  // Run activated strip pattern
  for(uint8_t strip = 0; strip < NUM_STRIPS; strip++) {
    if (strip == 4) {
      source(strip, buttonPressCounts, default_hue);
      continue;
    }

    if (strip == 2) {
      source2(strip, buttonPressCounts, 100);
      continue;
    }

    if (ledState[strip] == 0) {
      heartbeat(strip); // Default pattern
    }
    else {
      FastLED[strip].clearLeds(NUM_LEDS_PER_STRIP);
      activatePulse(strip);
      ledState[strip] -= 1;
    }
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
    // Serial.print(F(" Pattern: "));
    // Serial.println(pattern);
    lastDebug = millis();
  }
}

void handleButtonPress(uint8_t buttonIndex) {
  // FastLED.clear();
  // pattern = buttonIndex + 1;
  
  Serial.print(F("Button "));
  Serial.print(buttonIndex + 1);
  // Serial.print(F(" -> Pattern "));
  // Serial.println(pattern);
  
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

void heartbeat(uint8_t strip){
  // 40 BPM = 1500ms cycle, with 50ms delay = 20 frames per second
  // 1500ms / 50ms = 30 frames per beat cycle
  uint16_t phase = ((uint16_t)counter * 20) % 3000; // Cast to prevent overflow
  
  uint8_t default_value = 100; // Brightness
  uint8_t value = default_value;      
  uint8_t default_saturation = 180; // Lighter base
  uint8_t saturation = default_saturation; // Light red base
  
  // Double heartbeat pattern (lub-dub)
  if (phase < 150) {
    // First beat (lub)
    float progress = phase / 150.0;
    // float pulse = sin(0.3*(progress * PI));
    float pulse = sin(progress * PI);
    saturation = default_saturation - (50 * pulse);  // 180 to 255 (light to strong red)
    value = default_value - (40 * pulse);        // 80 to 120 (subtle brightness pulse)
  } 
  else if (phase < 200) {
    // Short pause
    saturation = default_saturation;
    value = default_value;
  }
  else if (phase < 340) {
    // Second beat (dub) - slightly weaker
    float progress = (phase - 200) / 120.0;
    float pulse = sin(progress * PI) * 0.8;
    saturation = default_saturation + (20 * pulse);
    value = default_value + (80 * pulse);
  }
  // else: long pause (320-1000ms) stays at default low values
  
  // Set base to clear
  for(int i = 0; i < NUM_LEDS_PER_STRIP; i++) {
    leds[strip][i] = CHSV(default_hue, 100, 0);
  }

  uint8_t chunk_increment = 4;
  for (uint8_t i=1; i<NUM_LEDS_PER_STRIP; i=i+chunk_increment) {
    leds[strip][i] += CHSV(default_hue, saturation, value);
  }
}

void activatePulse(uint8_t strip) {
  // Fade all LEDs first for smooth trailing effect
  // fadeToBlackBy(leds[strip], NUM_LEDS_PER_STRIP, 100);
  uint8_t default_saturation = 180; // Lighter base

  uint8_t chunk_increment = 4;
  for (uint8_t i=1; i<NUM_LEDS_PER_STRIP; i=i+chunk_increment) {
    leds[strip][i] = CHSV(default_hue, default_saturation, 100);
  }
  
  // Slow movement - update position every 4 frames
  static uint8_t lastPos[NUM_STRIPS] = {0};
  if (counter % 2 == 0) {
    lastPos[strip] = (lastPos[strip] + 1) % NUM_LEDS_PER_STRIP;
  }
  
  // Add bright spot at current position - creates smooth comet tail
  leds[strip][lastPos[strip]] += CHSV(contrast_hue, 255, 180); // Boost brightness/saturation
}

// Controls the LED strip for the central lantern
void source(uint8_t strip, uint8_t buttonPressCounts, uint8_t hue) {
  uint8_t default_brightness = 100;
  static uint8_t brightness = default_brightness;
  static uint16_t target = default_brightness;

  // Fade if buttonPressCounts is reset
  if (buttonPressCounts == 0 && brightness > default_brightness) {
    target = default_brightness;
    if (target < brightness) {
      brightness = brightness-2;
    }
  }
  else if (buttonPressCounts > 0) {
    target = min(255, default_brightness + (30*buttonPressCounts));
    if (target > brightness) {
      brightness = brightness + 1;
    }
  }

  fill_solid(leds[strip], NUM_LEDS_PER_STRIP, CHSV(hue, 200, brightness));
}

void source2(uint8_t strip, uint8_t buttonPressCounts, uint8_t hue) {
  uint8_t default_brightness = 100;
  static uint8_t brightness = default_brightness;
  static uint16_t target = default_brightness;

  // Fade if buttonPressCounts is reset
  // if (buttonPressCounts == 0 && brightness > default_brightness) {
  //   target = default_brightness;
  //   if (target < brightness) {
  //     brightness = brightness-2;
  //   }
  // }
  // else if (buttonPressCounts > 0) {
  //   target = min(255, default_brightness + (10*buttonPressCounts));
  //   if (target > brightness) {
  //     brightness = brightness + 2;
  //   }
  // }

  fill_solid(leds[strip], NUM_LEDS_PER_STRIP, CHSV(hue, 200, brightness));
}