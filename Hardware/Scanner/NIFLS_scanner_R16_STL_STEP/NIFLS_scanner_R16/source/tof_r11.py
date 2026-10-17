"""Original optical/ToF assembly lowered 28 mm as one rigid assembly."""
import tof_r3 as old
from tof_r3 import box
def world(s):return old.world(s).translate((0,0,-28))
def local(s):return old.local(s.translate((0,0,28)))
def build_tof():return {n:s.translate((0,0,-28)) for n,s in old.build_tof().items()}
def other_clamp(s):return old.other_clamp(s.translate((0,0,28))).translate((0,0,-28))
def orient_for_print(n,s):return old.orient_for_print(n,s.translate((0,0,28)))
def reference_hardware():return {n:s.translate((0,0,-28)) for n,s in old.reference_hardware().items()}
def test_cone():return old.test_cone().translate((0,0,-28))
def update_optics(parts):
    parts=old.update_optics(parts)
    for n in list(parts):
        if n.startswith(('03_','04_','05_','06_')):parts[n]=parts[n].translate((0,0,-28))
    return parts
