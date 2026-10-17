"""Holder for measured Zomei metal-ring envelope, diameter 33 x 6 mm."""
import math
from tof_r3 import box,cyl

def update_filter(parts):
    # Shoulder and retainer enclose 6.6 mm: 6 mm filter plus two 0.3 mm pads.
    carrier=cyl(25.5,9.9,(13,0,-4)).cut(cyl(14.25,10.3,(12.8,0,-4)))
    carrier=carrier.cut(cyl(16.8,6.8,(16.3,0,-4)))
    ret=cyl(25.5,5.5,(22.9,0,-4)).cut(cyl(14.25,5.9,(22.7,0,-4)))
    for a in [270,30,150]:
        y=21*math.cos(math.radians(a));z=-4+21*math.sin(math.radians(a))
        carrier=carrier.cut(cyl(1.8,10.3,(12.8,y,z)))
        ret=ret.cut(cyl(1.8,5.9,(22.7,y,z)))
        ret=ret.cut(cyl(3.1,3.5,(25.1,y,z)))
    relief=box(15,29,-26,26,14,34)
    parts.pop('05_filter_carrier_1mm_glass')
    parts.pop('05_filter_carrier_2mm_glass')
    parts['05_filter_carrier_zomei_33x6']=carrier.cut(relief).clean()
    parts['06_filter_retainer']=ret.cut(relief).clean()
    # Keep 35 mm past the forward-most ring face. Glass sits somewhere inside.
    hood=parts['04_contact_hood_35mm'].cut(box(51,60,-60,60,-50,50))
    import cadquery as cq
    from cadquery import Vector as V
    ext=cyl(37,4.6,(51,0,-4)).fuse(cq.Solid.makeCone(37,35,2,V(55.6,0,-4),V(1,0,0)))
    ext=ext.cut(cyl(32,7,(50.8,0,-4)))
    hood=hood.fuse(ext).cut(cyl(34.2,4.1,(27,0,-4)))
    parts['04_contact_hood_35mm']=hood.clean()
    return parts

def reference_hardware():
    refs={'zomei_filter_33x6_envelope':cyl(16.5,6,(16.6,0,-4))}
    for a in [270,30,150]:
        y=21*math.cos(math.radians(a));z=-4+21*math.sin(math.radians(a))
        refs['filter_M3x16_'+str(a)]=cyl(1.5,16,(9.1,y,z)).fuse(cyl(2.75,3,(25.1,y,z)))
    return refs
