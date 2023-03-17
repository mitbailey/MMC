Front-end / GUI
mmc.py

Middleware
middleware.py

Drivers
_thorlabs_kst_advanced.py
mp_789a_4.py
mp_792.py

The drivers implements the Middleware-Driver interface. No threading is allowed in this abstraction layer.

The middleware implements the GUI-Middleware interface. All functions in this layer have blocking and non-blocking options or are getters. When called in non-blocking mode, the functions are wrappers which start threads. Otherwise, they call the function directly. This layer has no knowledge of graphical elements and uses python threads.

The GUI uses exclusively GUI-compatible QThreads when spawning threads.