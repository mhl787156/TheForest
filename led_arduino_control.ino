#include <WS2812FX.h>

// For Urban Pillar
//#define LED_COUNT 391
// For Nature Pillar
#define LED_COUNT 404

#define LED_PIN 12
const int num_segments = 4;

WS2812FX ws2812fx = WS2812FX(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void setup() {


  ws2812fx.init();
  ws2812fx.setBrightness(255);
  ws2812fx.setSpeed(200);


//  for (int i = 0; i < num_segments; i++) {
//    int lower = i * LED_COUNT / num_segments;
//    int upper = ((i + 1) * LED_COUNT / num_segments) - 1;
//    ws2812fx.setSegment(i, lower, upper, FX_MODE_COLOR_WIPE_RANDOM);
//  }

//  For Urban Pillar
//  ws2812fx.setSegment(0, 0, 96, FX_MODE_COLOR_WIPE, RED, 200, false);
//  ws2812fx.setSegment(1, 97, 193, FX_MODE_COLOR_WIPE, BLUE, 200, false);
//  ws2812fx.setSegment(2, 194, 292, FX_MODE_COLOR_WIPE, GREEN, 200, true);
//  ws2812fx.setSegment(3, 293, 391, FX_MODE_COLOR_WIPE, PINK, 200, false);

// For Nature Pillar
  ws2812fx.setSegment(0, 0, 101, FX_MODE_COLOR_WIPE, RED, 200, false);
  ws2812fx.setSegment(1, 102, 202, FX_MODE_COLOR_WIPE, BLUE, 200, true);
  ws2812fx.setSegment(2, 203, 305, FX_MODE_COLOR_WIPE, GREEN, 200, false);
  ws2812fx.setSegment(3, 306, 400, FX_MODE_COLOR_WIPE, PINK, 200, true);


  ws2812fx.start();

  Serial.begin(115200);
  Serial.setTimeout(1);
}



const int maxNumbers = 3; // Maximum number of elements in the array
const int maxDigits = 3; // Maximum number of digits for each number

int numberArray[maxNumbers];
int arrayCount = 0;

char inputBuffer[maxDigits + 1];
int bufferIndex = 0;


bool readNumberArray() {

  if (Serial.available()) {
    char receivedChar = Serial.read();
    Serial.println(receivedChar);

    if (isdigit(receivedChar)) {
      if (bufferIndex < maxDigits - 1) {
        inputBuffer[bufferIndex] = receivedChar;
        bufferIndex++;
      }
    } else if (receivedChar == 'r') {
      arrayCount = 0;
      memset(numberArray, 0, sizeof(numberArray));
      bufferIndex = 0;
      inputBuffer[bufferIndex] = '\0';
      return false;
    } else if (receivedChar == ',' || receivedChar == ';') {
      inputBuffer[bufferIndex] = '\0'; // Null-terminate the input buffer

      if (bufferIndex > 0) {
        numberArray[arrayCount] = atoi(inputBuffer);
        arrayCount++;

        if (arrayCount >= maxNumbers) {
          arrayCount = 0;
          return false;
        }
      }

      bufferIndex = 0;

      if (receivedChar == ';') {
        return true;
      }
    }
  }
  return false;
}

void loop() {
  ws2812fx.service();

  if (readNumberArray()) {
    Serial.println("Here");
    Serial.println(numberArray[0]);
    Serial.println(numberArray[1]);
    ws2812fx.setMode(numberArray[0], numberArray[1]);
    arrayCount = 0;
    Serial.println("-------");
  }

  //  delay(1);

}

// Set the mode for the first segment (LEDs 0-50)
//  ws2812fx.setMode(segmentid, patternid); // Adjust the mode as desired