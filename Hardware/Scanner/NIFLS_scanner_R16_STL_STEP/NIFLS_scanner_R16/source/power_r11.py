"""R9 flush power module lowered into slim R11 main base."""
import power_r9 as old
from power_r4 import box,ins
def update_head(parts):
    opening=box(-121,-107.7,-29.3,29.3,4.7,33.1)
    base=parts['01_pi_base'].cut(opening)
    lid=parts['02_pi_lid'].cut(opening)
    for y in [-34,34]:
        base=base.fuse(box(-120,-101,29.3 if y>0 else -44,44 if y>0 else -29.3,13.8,24.2))
        base=base.cut(box(-114.3,-107.7,y-5.5,y+5.5,13.9,24.1)).cut(ins((-107.7,y,19)))
    for y in [-40,40]:base=base.cut(ins((-111,y,27),(0,0,-1)))
    parts['01_pi_base']=base.clean();parts['02_pi_lid']=lid.clean()
    return parts
def build_power():return {n:s.translate((0,0,-15)) for n,s in old.build_power().items()}
def reference_hardware():return {n:s.translate((0,0,-15)) for n,s in old.reference_hardware().items()}
def orient_for_print(n,s):return old.orient_for_print(n,s)
