"""Flush rear service panel at Pi-housing rear plane X=-120 mm."""
import cadquery as cq
import power_r4 as legacy
from power_r4 import box,cyl,cham,ins

def update_head(parts):
    lid=parts['02_pi_lid']
    lid=lid.cut(box(-121,-107.7,-29.3,29.3,19.7,48.1))
    for y in [-34,34]:
        block=box(-120,-101,29.3 if y>0 else -44,44 if y>0 else -29.3,28.8,39.2)
        lid=lid.fuse(block)
        lid=lid.cut(box(-114.3,-107.7,y-5.5,y+5.5,28.9,39.1))
        lid=lid.cut(ins((-107.7,y,34)))
    parts['02_pi_lid']=lid.clean()
    return parts

def build_power():
    frame=box(-114,-108,-29,29,20,48).cut(box(-114.1,-107.9,-20,20,22.9,45.1))
    for y in [-34,34]:
        frame=frame.fuse(cyl(4.8,6,(-114,y,34)))
        # Bridge mounting ears onto frame sides.
        frame=frame.fuse(box(-114,-108,min(y,0),max(y,0),30,38).cut(box(-114.1,-107.9,-20,20,22.9,45.1)))
        frame=frame.cut(cyl(1.8,6.2,(-114.1,y,34))).cut(cyl(3.1,3.1,(-114.1,y,34)))
    for y in [-24,24]:
        for z in [27,41]:frame=frame.cut(ins((-114,y,z)))
    for y in [-14,14]:frame=frame.cut(box(-114.1,-111.7,y-2.3,y+2.3,44.8,46.4))
    plate=cham(box(-120,-114,-29,29,20,48))
    for y in [-24,24]:
        for z in [27,41]:
            plate=plate.cut(cyl(1.8,6.4,(-120.2,y,z))).cut(cyl(3.1,3.4,(-120.1,y,z)))
    for y in [-14,14]:plate=plate.fuse(box(-114.2,-112,y-2,y+2,45.1,46.1))
    # Raise switch 2 mm so its solder terminals clear the Pi envelope.
    plate=plate.cut(cyl(3.475,6.4,(-120.2,-8,36))).cut(cyl(7,3.1,(-120.1,-8,36)))
    key=box(-114.2,-111,-13.73,-2.27,27.35,44.5)
    key=key.cut(box(-114.3,-110.9,-11.73,-4.27,29.35,42.65))
    plate=plate.fuse(key)
    plate=plate.cut(cyl(2.8,6.4,(-120.2,10,34))).cut(cyl(3.25,3.1,(-117,10,34)))
    for z in [27,41]:plate=plate.cut(ins((-114,10,z),(-1,0,0)))
    for label,z in [('ON',44.1),('OFF',23.9)]:
        plane=cq.Plane(origin=(-119.5,-8,z),xDir=(0,-1,0),normal=(-1,0,0))
        for s in cq.Workplane(plane).text(label,2.5,.5,font='Arial',kind='bold',combine=False).vals():plate=plate.cut(s)
    ret=legacy.build_power()['21_led_retainer'].translate((24,0,0))
    return {'19_power_pod':frame.clean(),'20_power_panel':plate.clean(),'21_led_retainer':ret}

def orient_for_print(name,s):return legacy.orient_for_print(name,s)

def reference_hardware():
    result={}
    for name,s in legacy.reference_hardware().items():
        if name.startswith('power_base_screw'):continue
        dz=2 if name.startswith(('power_switch','power_lockwasher','power_nut','power_toggle')) else 0
        result[name]=s.translate((24,0,dz))
    for y in [-34,34]:result[f'power_base_screw_{y}']=cyl(1.5,6,(-111,y,34)).fuse(cyl(2.75,3,(-114,y,34)))
    return result
