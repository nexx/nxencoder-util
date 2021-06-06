/* Filament Reader Firmware
 * 
 * Copyright (c) 2021 Simon Davie <nexx@nexxdesign.co.uk>
 * 
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.

 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.

 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

#include <EEPROM.h>
#include <Encoder.h>
Encoder filamentEncoder(2, 3);

// Constant vars
const char compile_date[] = __DATE__ " " __TIME__;
const float compile_version = 1.0;

// Diameter of the gear or wheel attached to the encoder, this can be
// tweaked as necessary to achieve accurate results.
// E3D Hobb Goblin 5mm ID gear = ~7.30
float gearDiameter = 7.30;

// Number of pulses produces by the encoder for one full rotation.
// This is normally mentioed in the spec sheet.
// LPD3806-600BM-G5-24C = 2400
// AMT102-V (2048 PPR)  = 8192
const unsigned int encoderRotationCount = 8192;

// Used to store the calculated encoder per MM value.
float encoderCountPerMM = 0.00;

// State tracking
String serialData = "";
bool serialDataComplete = false;

// Used to track extruded amount
unsigned long currentMeasurement = 0;
unsigned long previousMeasurement = 0;

void setup() {
  // Open the serial port at 9600 baud.
  Serial.begin(9600);
  serialData.reserve(32);

  // Check the EEPROM for the calibrated value, use that if
  // it exists and is valid.
  float calEEPROM = 0.00;
  EEPROM.get(0, calEEPROM);
  if (!isnan(calEEPROM) && calEEPROM != 0) {
    gearDiameter = calEEPROM;
  }

  // Output a welcome message
  Serial.print("NXE|");
  Serial.print(String(compile_version));
  Serial.print("|");
  Serial.print(String(compile_date));
  Serial.print("|");
  Serial.println(gearDiameter, 6);

  // Calculate the encoder pulses required for 1mm of movement.
  encoderCountPerMM = encoderRotationCount / (gearDiameter * PI);
}

void loop() {
  // Capture the encoder reading prior to anything else
  currentMeasurement = filamentEncoder.read();

  // Handle incoming serial data
  if (serialDataComplete) {
    if (serialData.startsWith("CAL")) {
      serialData = serialData.substring(3);
      if (serialData.toFloat()) {
        float calDistance = serialData.toFloat();
        float calDiameter = ((calDistance / currentMeasurement) * encoderRotationCount) / PI;
        Serial.print("CALIBRATED DIAMETER: ");
        Serial.println(calDiameter, 6);

        // Save calibration to EEPROM
        EEPROM.put(0, calDiameter);
        float calEEPROM = 0.00f;
        EEPROM.get(0, calEEPROM);
        if (calEEPROM != calDiameter) {
          Serial.print("ERROR SAVING TO EEPROM. EXPECTED: ");
          Serial.print(calDiameter);
          Serial.print(" RETRIEVED: ");
          Serial.print(calEEPROM);
        } else {
          Serial.println("CALIBRATION SAVED TO EEPROM");
        }
        encoderCountPerMM = encoderRotationCount / (calDiameter * PI);
      }
    } else if (serialData.startsWith("MEASURE")) {
      if (currentMeasurement > 4290000000) {
        // We have underflowed the 32bit long (or somehow extruded 18km of filament... I think
        // assuming the former of those two scenarios is the wiser choice :P )
        unsigned long underflow = 4294967295 - currentMeasurement;
        underflow += previousMeasurement;

        // Reset the encoder and tracking variables
        filamentEncoder.write(0);
        currentMeasurement = 0;
        Serial.println(0 - (underflow / encoderCountPerMM), 4);
      } else if (currentMeasurement > previousMeasurement) {
        // The filament has moved forwards
        Serial.println((currentMeasurement - previousMeasurement) / encoderCountPerMM, 4);
      } else if (currentMeasurement < previousMeasurement) {
        // The filament has moved backwards
        Serial.println(0 - ((previousMeasurement - currentMeasurement) / encoderCountPerMM), 4);
      } else {
        // The filament has not moved
        Serial.println(0, 4);
      }
      previousMeasurement = currentMeasurement;
    } else if (serialData.startsWith("RESET")) {
        // Reset the encoder to 0
        filamentEncoder.write(0);
      
        // Reset our tracking variables
        currentMeasurement = 0;
        previousMeasurement = 0;
    }

    // Clear serial data and flag
    serialData = "";
    serialDataComplete = false;
  }
}

// Handle incoming serial data
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    serialData += inChar;
    if (inChar == '\n') {
      serialDataComplete = true;
    }
  }
}
