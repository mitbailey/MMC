# McPherson Monochromator Controller

## Usage
### via Executable
See the appropriate [releases page](https://github.com/mitbailey/MMC/releases) for details.  

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
- KST101 (Motor Controller)  
- KM6485 (Picoammeter)  

## Hierarchy
GUI <-> Middleware <-> Drivers <-> Hardware
- The GUI calls Middleware functions and is the layer the user directly interacts with. The GUI simply knows that it exists above some Monochromator with some type of Motion Controller and Sampling device.
- The middleware allows the GUI to be agnostic to specific hardware and hardware implementations, providing the GUI layer with consistent functions to interface with across all forms of Motion Control and Sampling. The Middleware determines which drivers must be used.
- The drivers interact directly with the Motion Controller and Sampler and are specific to their model / type.