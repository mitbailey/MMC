# McPherson Monochromator Controller Software

IMPORTANT! You MUST read through the entire Getting Started section.

PyQt-based GUI program to control monochromators, detectors, and related hardware. 

# Getting Started
Simple usage. For advanced cases, see Advanced Usage.

## Requirements
- Windows 10/11

## Dependencies
- ThorLabs' Kinesis drivers package
    - Kinesis 64-bit Software for 64-bit Windows: https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=Motion_Control&viewtab=0 
    - Installed in C:/Program Files/Thorlabs/Kinesis (as is default).
    - The Kinesis software MUST be run at least once prior to starting MMCS.

## Usage

The executable is available within the MMCS zip archive included with each release. Download and extract the archive to access and run MMCS.exe. See the [releases page](https://github.com/mitbailey/MMC/releases) for details. 

Before first run (one-time only):
- Unblock `Python.runtime.dll`:
    - 1). Enter the software's folder.
    - 2). Locate the file `Python.runtime.dll`.
    - 3). Right click the file; click "Properties".
    - 4). Check the "Unblock" checkbox near the bottom.
    - 5). Click "Apply"; click "OK".

# Compatible Hardware
## Motion Controllers
- ThorLabs KST101 K-Cube with the ZFS25B (USB; Requires ThorLabs drivers)
- McPherson 789A-4 (RS-232)
- McPherson 792 (RS-232)

## Detectors
- Stanford Research Systems SR810 Lock-In Amplifier
- Stanford Research Systems SR860 Lock-In Amplifier
- Keithley Instruments KI6485 Picoammeter (RS-232)

# Troubleshooting
### Issue 1:   
The program crashes on startup. 

Solution 1A:  
Some systems may require that `Python.Runtime.dll` is 'unblocked' manually.   
To do this:  
    1). Navigate to MMCS\pythonnet\runtime  
    2). Right-click the file `Python.Runtime.dll` and select Properties.    
    3). Check Unblock in the bottom right-hand corner.  

Solution 1B:  
Some systems may require administrative privileges to run the program. Right click `MMCS.exe` and press "Run as Administrator."

Solution 1C:
Ensure that the ThorLabs Kinesis Software is installed as discussed in Pre-Requisites.

# Advanced Usage
## via Executable
The executable is available within the MMCS zip archive included with each release. Download and extract the archive to access and run MMCS.exe. See the [releases page](https://github.com/mitbailey/MMC/releases) for details.  

## via Source Code
Run: `python mmc.py`   


# Compilation (One Directory - Fast Startup, 1 GB)

The One Directory compilation method produces a larger set of files but starts up significantly faster than the One File method. For software versions 0.7.1 and newer, this method is used to compile the zip archive and executable available on the [releases page](https://github.com/mitbailey/MMC/releases).

## Prerequisites
See requirements.txt for requirements.

`pip install -r requirements.txt`

Additionally, you may need to manually install PyQtWebEngine:

`pip install PyQtWebEngine`  

## Pipenv Setup
`cd MMC`  
`pipenv install requests`  

## Compilation
`pipenv run pyinstaller mmc.spec`

Outputs MMC/dist/MMCS/MMCS.exe

# Compilation (One File - Slow Startup, 400 MB)

The One File compilation method produces a smaller file but starts up significantly slower than the One Directory method. For software versions 0.7 and older, this method is used to compile the executable available on the [releases page](https://github.com/mitbailey/MMC/releases).

`pyinstaller mmc_onefile.spec`  

Outputs MMC/dist/mmc.exe

# Licensing

    Copyright (C) 2023  Mit Bailey

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.