"""R14: expose both buried saddle fasteners from the open tray top."""
from battery_r11 import reference_hardware
from battery_r11 import build_battery as previous
from grip_r10 import cyl

def build_battery():
    parts=previous()
    tray=parts['23_battery_tray']
    for x in [-108,-38]:
        # Join the existing 6.2 mm counterbore without changing its seat.
        tray=tray.cut(cyl(3.1,23.56,(x,17,-7.54),(0,0,-1)))
    parts['23_battery_tray']=tray.clean()
    return parts
