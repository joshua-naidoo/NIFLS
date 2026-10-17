"""Rear service pod: C&K 7101MYZQE toggle and Kingbright WP7113SGC LED.
Global assembly coordinates, mm; independent of battery and optics.
"""
import cadquery as cq
from cadquery import Vector as V

def box(a,b,c,d,e,f): return cq.Solid.makeBox(b-a,d-c,f-e,V(a,c,e))
def cyl(r,h,p,d=(1,0,0)): return cq.Solid.makeCylinder(r,h,V(*p),V(*d))
def cham(s,n=2): return cq.Workplane(obj=s).edges().chamfer(n).val()
def ins(p,d=(1,0,0)):
    return cyl(2.1,4.5,p,d).fuse(cq.Solid.makeCone(2.4,2.1,.6,V(*p),V(*d)))

def update_head(parts):
    lid=parts['02_pi_lid']
    for y in [-24,24]:
        lid=lid.fuse(cyl(4.8,3,(-116.5,y,34)))
        lid=lid.cut(ins((-120,y,34)))
    lid=lid.cut(box(-121,-113,-4,4,31.5,36.5))
    parts['02_pi_lid']=lid.clean()
    return parts

def build_power():
    pod=cham(box(-138,-120,-29,29,20,48))
    pod=pod.cut(box(-138.1,-123,-20,20,22.9,45.1))
    pod=pod.cut(box(-124,-119,-4,4,31.5,36.5))
    for y in [-24,24]:
        # Deep service access from open rear. M3x6 seat -123, tip -117.
        pod=pod.cut(cyl(1.8,19,(-138.5,y,34)))
        pod=pod.cut(cyl(3.1,15.1,(-138.1,y,34)))
        for z in [27,41]: pod=pod.cut(ins((-138,y,z)))
    # Two short locators, .3 clearance at each flank and end.
    for y in [-14,14]:
        pod=pod.cut(box(-138.1,-135.7,y-2.3,y+2.3,44.8,46.4))
    plate=cham(box(-144,-138,-29,29,20,48))
    for y in [-24,24]:
        for z in [27,41]:
            plate=plate.cut(cyl(1.8,6.4,(-144.2,y,z)))
            plate=plate.cut(cyl(3.1,3.4,(-144.1,y,z)))
    for y in [-14,14]: plate=plate.fuse(box(-138.2,-136,y-2,y+2,45.1,46.1))
    # Toggle bushing, 3 mm panel at bottom of nut recess.
    plate=plate.cut(cyl(3.475,6.4,(-144.2,-8,34)))
    plate=plate.cut(cyl(7,3.1,(-144.1,-8,34)))
    # Square key cradle prevents the body rotating while the nut is fitted.
    key=box(-138.2,-135,-13.73,-2.27,25.35,42.65)
    key=key.cut(box(-138.3,-134.9,-11.73,-4.27,27.35,40.65))
    plate=plate.fuse(key)
    # 5 mm LED, 5.9 mm flange: .3 mm radial pocket clearance.
    plate=plate.cut(cyl(2.8,6.4,(-144.2,10,34)))
    plate=plate.cut(cyl(3.25,3.1,(-141,10,34)))
    for z in [27,41]: plate=plate.cut(ins((-138,10,z),(-1,0,0)))
    # Captive padded LED flange; M3x6 fasteners, recessed heads.
    ret=box(-138,-132,6.2,13.8,27,41)
    for z in [27,41]: ret=ret.fuse(cyl(3.8,6,(-138,10,z)))
    ret=ret.fuse(cyl(2.95,1.7,(-139.7,10,34)))
    ret=ret.cut(cyl(2.1,8,(-139.8,10,34)))
    for z in [27,41]:
        ret=ret.cut(cyl(1.8,6.3,(-138.1,10,z)))
        ret=ret.cut(cyl(3.1,3.4,(-135.3,10,z)))
    # Small power legend, exactly .5 mm deep, does not overlap seats.
    plane=cq.Plane(origin=(-143.5,-8,44.1),xDir=(0,-1,0),normal=(-1,0,0))
    for s in cq.Workplane(plane).text('ON',2.5,.5,font='Arial',kind='bold',combine=False).vals(): plate=plate.cut(s)
    plane=cq.Plane(origin=(-143.5,-8,23.9),xDir=(0,-1,0),normal=(-1,0,0))
    for s in cq.Workplane(plane).text('OFF',2.5,.5,font='Arial',kind='bold',combine=False).vals(): plate=plate.cut(s)
    return {'19_power_pod':pod.clean(),'20_power_panel':plate.clean(),'21_led_retainer':ret.clean()}

def orient_for_print(name,s):
    # Pod head-side face on bed; panel outside face down; retainer rear face down.
    return s.rotate((0,0,0),(0,1,0),90 if name in ['19_power_pod','21_led_retainer'] else -90)

def reference_hardware():
    body=box(-138,-129.11,-11.43,-4.57,27.65,40.35)
    body=body.fuse(cyl(3.175,8.89,(-138,-8,34),(-1,0,0)))
    # Conservative terminal/solder envelope, with separate insulated leads.
    terms=box(-129.11,-125.17,-9.5,-6.5,28,40)
    led=cyl(2.5,7.6,(-141,10,34),(-1,0,0)).fuse(cyl(2.95,1,(-141,10,34)))
    leads=box(-140,-124,9.4,10.6,32.23,35.77)
    result={'power_switch_body':body,'power_switch_solder_space':terms,'power_led':led,'power_led_leads_space':leads}
    result['power_lockwasher']=cyl(6.35,.5,(-141.5,-8,34)).cut(cyl(3.2,.7,(-141.6,-8,34)))
    result['power_nut_envelope']=cyl(5,2,(-143.5,-8,34)).cut(cyl(3.2,2.2,(-143.6,-8,34)))
    for a in [-25,25]:
        result[f'power_toggle_position_{a}']=cyl(1.46,5.08,(-146.89,-8,34),(-1,0,0)).rotate((-146.89,-8,34),(-146.89,-7,34),a)
    for y in [-24,24]:
        result[f'power_base_screw_{y}']=cyl(1.5,6,(-123,y,34)).fuse(cyl(2.75,3,(-126,y,34)))
        for z in [27,41]:
            result[f'power_panel_screw_{y}_{z}']=cyl(1.5,6,(-140.7,y,z)).fuse(cyl(2.75,3,(-143.7,y,z)))
    for z in [27,41]:
        result[f'power_led_screw_{z}']=cyl(1.5,6,(-135.3,10,z),(-1,0,0)).fuse(cyl(2.75,3,(-135.3,10,z)))
    return result
