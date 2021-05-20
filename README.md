# nxencoder-util

nxEncoder utility is a GUI application for use with the nxEncoder filament tool. Together they are designed to allow for easy, accurate, and consistent, calibrations of an FDM 3D printer extrusion system.

## Features
- Extruder steps/mm calibration for RepRapFirmware and Marlin
- Rotation distance calibration for Klipper
- Extruder system consistency testing
- Maximum volumetric flow calculation

## Firmware support
- RepRapFirmware v3 in standalone mode
- RepRapFirmware v3 via a connected SBC
- Klipper via Moonraker
- Marlin via direct serial connection
- **_Marlin via OctoPrint is not supported at this time._**

## Building the encoder
### Printed Parts
_It is recommended to print these parts in either PETG or ABS, on a well calibrated machine._
- 1x nxencoder_body_base.stl
- 1x nxencoder_body_top.stl
- 1x nxencoder_idler_housing.stl
- 1x nxencoder_idler_pin.stl

### Bill of Materials
- 1x AMT102V rotary encoder (AMT102-D2048-I5000-S)
- 1x Arduino Nano (or compatible clone)
- 3x 695 bearing (695-2RS or 695-ZZ)
- 1x MK8 hobbed extruder gear with a 5mm bore
- 1x M5x30 dowel
- 4x M3x16 countersunk machine screw (DIN EN ISO 10462)
- 4x M3 nylon-insert lock nut

### Assembly
1. Place one 695 bearing on a flat surface and insert the M5x30 dowel through the center until it stops
2. Install the MK8 extruder gear onto the M5x30 dowel so that the hobbed end is furthest from the bearing
3. Make sure the MK8 extruder gear is sat atop the bearing and then secure it in place with the grub screws
4. Insert the bearing, dowel, and extruder gear assembly into the encoder body base
5. Install a second 695 bearing onto the M5x30 dowel pin. Slide it right down so that it rests atop the MK8 extruder gear
6. Install the final 695 bearing into the idler housing and insert the idler pin to secure it in place
7. Insert the idler assembly into the encoder body
8. Install the spring between the rear of the idler assembly and the rear of the housing
9. Install the encoder body top
10. Follow the instructions provided with the the AMT102V encoder to install it atop the completed encoder housing

### Firmware installation
_To be completed._

## Software installation
_To be completed._

## Usage
_To be completed._
