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
See [docs/assembly_instructions.pdf](https://github.com/nexx/nxEncoder-Util/blob/main/docs/assembly_instructions.pdf)

### Firmware installation & provisioning
See [docs/provisioning_instructions.pdf](https://github.com/nexx/nxEncoder-Util/blob/main/docs/provisioning_instructions.pdf)

## Software installation
_To be completed._

## Usage
_To be completed._
