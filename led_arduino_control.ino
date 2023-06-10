#include <WS2812FX.h>

#define LED_COUNT 300
#define LED_PIN 12
const int num_segments = 4;


WS2812FX ws2812fx = WS2812FX(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

void setup() {

  
  ws2812fx.init();
  ws2812fx.setBrightness(100);
  ws2812fx.setSpeed(200);
  

  for(int i = 0; i < num_segments; i++) {
    int lower = i * LED_COUNT/num_segments;
    int upper = ((i+1) * LED_COUNT/num_segments) - 1;  
    ws2812fx.setSegment(i, lower, upper, FX_MODE_COLOR_WIPE_RANDOM); 
  }
  
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
  //ws2812fx.setMode(val1, val2);
  for(int i = 0;i++;i < num_segments) {
    int lower = i * LED_COUNT/num_segments;
    int upper = ((i+1) * LED_COUNT/num_segments) - 1;  
    Serial.println(lower);
    Serial.println(upper);
    Serial.println("-------");
  }
  
  if(readNumberArray()){
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
