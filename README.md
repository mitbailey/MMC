# McPherson Monochromator Controller

## Usage
Boot in normal mode, attempting connections and failing if devices not found:  
`python mmc.py`   
   
Boot in debug mode, no real connections to hardware will be attempted:  
`python mmc.py 1`

# NiceLib Conversion for Thorlabs Kinesis Stepper Motor Driver
(_From mitbailey/driver_converter/runnable/README.MD_)
1. Required packages: Thorlabs Kinesis (installed in C:\Program Files..), NiceLib, CFFI
2. To build the CFFI symbol table: `python _build_kst.py`
3. Mid level wrapper: `python _thorlabs_kst_wrap_basic.py`