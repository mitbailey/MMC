Program split in two:
    Front-End
        mmc.py (main)
        iface_netcomms.py
        UI Files
    Back-End
        midw.py (main)
        middleware.py
        midw_netcomms.py
        Driver Files

```
0123456789...

CCCC-????...

--------------------
Iface ==> Middleware
--------------------

DUMM
    Is this a dummy?

HOME
    Go home.

POSN
    Get position request.

HOMG
    Are we homing?

MOVG
    Are we moving?

MOVE IIII
    Move to position command. IIII represents the four bytes of a 32-bit integer.

--------------------
Middleware ==> Iface
--------------------

DUMM SSSS
    Is this a dummy? Where SSSS is either 'TRUE' or 'FALS'.

HOME ?
    Response once self.motor_ctrl.home() returns. Where ? is the return value of .home().

POSN IIII                   
    Current position report. VVVV represents the four bytes of a 32-bit integer.

HOMG SSSS
MOVG SSSS
MOVE ?
```

def is_dummy(self):
    return self.is_dummy

def home(self):
    return self.motor_ctrl.home()

def get_position(self):
    return self.motor_ctrl.get_position()

def is_homing(self):
    return self.motor_ctrl.is_homing()

def is_moving(self):
    return self.motor_ctrl.is_moving()

def move_to(self, position, block):
    return self.motor_ctrl.move_to(position, block)