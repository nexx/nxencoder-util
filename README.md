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
- 1x E3D Hobb Goblin 5mm ID Drive Gear
- 1x M5x30 dowel
- 4x M3x20 countersunk flat head screw (DIN EN ISO 7046)
- 4x M3 nylon-insert lock nut
- 1x compression spring (5mm OD, 0.5mm wire size, ~10mm long, capable of compressing to ~6mm)

#### The following pre-crimped options are available with regards to wiring:
- Pre-crimped 1FT cable (CUI-3131-1FT)
- Pre-crimped 6FT cable (CUI-3131-6FT)

#### Alternately you can purchase the crimps and housings to make your own:
- Molex 5P housing (50-57-9405)
- Molex crimp connectors (16-02-0086)

### Assembly
See [docs/assembly_instructions.pdf](https://github.com/nexx/nxencoder-util/blob/main/docs/assembly_instructions.pdf)

### Firmware installation & provisioning
See [docs/provisioning_instructions.pdf](https://github.com/nexx/nxencoder-util/blob/main/docs/provisioning_instructions.pdf)

## Software installation
### Microsoft Windows
Pre-compiled and self-contained binaries are currently available for 64bit Windows platforms. These can be found under [releases](https://github.com/nexx/nxencoder-util/releases).

### Linux
Use the following commands to clone the source code, install the required Python libraries, and then run the application.
```console
foo@bar:~$ git clone https://github.com/nexx/nxencoder-util.git
foo@bar:~$ cd nxencoder-util/nxencoder
foo@bar:~$ pip install -r requirements.txt
foo@bar:~$ python3 ./__main__.pyw
```
### macOS
Instructions are currently unavailable as the software has not been tested on macOS.

## Usage
_To be completed._

## License
nxencoder-util is free software and is published under the GNU General Public License v3.0. For full details, please see the [included license](https://github.com/nexx/nxencoder-util/blob/main/COPYING)
