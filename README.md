# McPherson Monochromator Controller Software

## Usage
### via Executable
The executable is available within the MMCS zip archive included with each release. Download and extract the archive to access and run MMCS.exe. See the [releases page](https://github.com/mitbailey/MMC/releases) for details.  

### via Source Code
Boot in normal mode, attempting connections and failing if devices not found:  
`python mmc.py`   
   
Boot in debug mode, no real connections to hardware will be attempted:  
`python mmc.py 1`

# NiceLib Conversion for Thorlabs Kinesis Stepper Motor Driver
(_From mitbailey/driver_converter/runnable/README.MD_)
1. Required packages: Thorlabs Kinesis (installed in C:\Program Files..), NiceLib, CFFI
2. To build the CFFI symbol table: `python _build_kst.py`
3. Mid level wrapper: `python _thorlabs_kst_wrap_basic.py`

## Compatible Hardware
This version is tested and confirmed to work with the following hardware:  
- ThorLabs KST101 Controller with ZFS25 Stage 
- Keithley 6485 Picoammeter

## Hierarchy
GUI <-> Middleware <-> Drivers <-> Hardware
- The GUI calls Middleware functions and is the layer the user directly interacts with. The GUI simply knows that it exists above some Monochromator with some type of Motion Controller and Sampling device.
- The middleware allows the GUI to be agnostic to specific hardware and hardware implementations, providing the GUI layer with consistent functions to interface with across all forms of Motion Control and Sampling. The Middleware determines which drivers must be used.
- The drivers interact directly with the Motion Controller and Sampler and are specific to their model / type.

# Compilation (One Directory - Fast Startup, 1 GB)

The One Directory compilation method produces a larger set of files but starts up significantly faster than the One File method. For software versions 0.7.1 and newer, this method is used to compile the zip archive and executable available on the [releases page](https://github.com/mitbailey/MMC/releases).

## Prerequisites
PyQtWebEngine, pipenv

`pip install PyQtWebEngine`  
`pip install pipenv`

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