"""Short roof-level route for a nominal 200 mm USB-C extension.
Connector lengths and bend radius must be compared with the actual cable.
"""
import math
from grip_r10 import box,cyl
POINTS=[(-68,26),(-60,18),(-60,-20),(-88,-36)]

def channel():
    pieces=[]
    for x,y in POINTS:pieces.append(cyl(4,5,(x,y,-4.8),(0,0,1)))
    for (x,y),(u,v) in zip(POINTS,POINTS[1:]):
        length=math.hypot(u-x,v-y)
        pieces.append(box(0,length,-4,4,-4.8,.2).rotate((0,0,0),(0,0,1),math.degrees(math.atan2(v-y,u-x))).translate((x,y,0)))
    shape=pieces[0]
    for s in pieces[1:]:shape=shape.fuse(s)
    return shape.clean()

def update(parts):
    # Direct upward exit above the existing fixed-plug/extension bay.
    entrance=box(-81,-55,18,38,-8,3.7)
    exit=box(-95,-77,-43,-29,-5,3.7)
    roof=parts['22_battery_roof'].cut(channel()).cut(entrance).cut(exit)
    parts['22_battery_roof']=roof.clean()
    base=parts['01_pi_base'].cut(exit)
    # Join the low cable exit to the existing USB-C / HDMI service opening.
    base=base.cut(box(-96,-76,-49,-29,-.1,10.1))
    parts['01_pi_base']=base.clean()
    # R14 tray already opens directly beneath this roof entrance; retain it.
    return parts
