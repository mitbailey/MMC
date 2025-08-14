# McPherson Monochromator Controller Software

PyQt-based GUI program to control monochromators, detectors, and related hardware. 

# Pre-Requisites

- ThorLabs' Kinesis drivers package
    - Kinesis 64-bit Software for 64-bit Windows: https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=Motion_Control&viewtab=0 
    - Installed in C:/Program Files/Thorlabs/Kinesis (as is default).
    - The Kinesis software MUST be run at least once prior to starting MMCS.
- Windows 10 (may work on other Windows versions, but untested).


If running directly via source code you will also need Python 3.9.7.


# Compatible Hardware
## Motion Controllers
- ThorLabs KST101 K-Cube with the ZFS25B (USB; Requires ThorLabs drivers)
- McPherson 789A-4 (RS-232)
- McPherson 792 (RS-232)

## Detectors
- Stanford Research Systems SR810 Lock-In Amplifier
- Stanford Research Systems SR860 Lock-In Amplifier
- Keithley Instruments KI6485 Picoammeter (RS-232)

## In Progress
- McPherson 747
- ThorLabs KST201 K-Cube

### **_NOTICE FOR KCUBE USERS_**: 
**The following one-time steps should be taken to enable proper KST201 homing and solve KST101/KST201 maximum range movement issues:**  
1). Connect the KST201 to your PC.  
2). Run the ThorLabs Kinesis GUI software.  
3). Move and Home the KST201.  
The MMC Software can now be used as usual.  

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

# Usage
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

# NiceLib Conversion for Thorlabs Kinesis Stepper Motor Driver
(_From mitbailey/driver_converter/runnable/README.MD_)
1. Required packages: Thorlabs Kinesis (installed in C:\Program Files..), NiceLib, CFFI
2. To build the CFFI symbol table: `python _build_kst.py`
3. Mid level wrapper: `python _thorlabs_kst_wrap_basic.py`

## Hierarchy
GUI <-> Middleware <-> Drivers <-> Hardware
- The GUI calls Middleware functions and is the layer the user directly interacts with. The GUI simply knows that it exists above some Monochromator with some type of Motion Controller(s) and detector(s).
- The middleware allows the GUI to be agnostic to specific hardware and hardware implementations, providing the GUI layer with consistent functions to interface with across all forms of motion control and detection. The Middleware determines which drivers must be used.
- The drivers interact directly with the motion controller and detector and are specific to their model / type.