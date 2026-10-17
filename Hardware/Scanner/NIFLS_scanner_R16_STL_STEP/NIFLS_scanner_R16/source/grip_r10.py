"""Uniform wiring-only grip, local U forward, V thickness, W down.
Ultra-Link 77.2 x 35 x 24.7 is in the separate under-head cassette.
"""
import cadquery as cq
from cadquery import Vector as V
import math
DATUM=(-75,0,-61.6)
CLAMPS=[(-14,11),(14,11),(-16,43),(16,43),(-14,120),(14,120)]
TOP=[(u,v) for u in [-15,15] for v in [-9,9]]
def box(a,b,c,d,e,f):return cq.Solid.makeBox(b-a,d-c,f-e,V(a,c,e))
def cyl(r,h,p,d):return cq.Solid.makeCylinder(r,h,V(*p),V(*d))
def ins(p,d):return cyl(2.1,4.5,p,d).fuse(cq.Solid.makeCone(2.4,2.1,.6,V(*p),V(*d)))
def global_shape(s):return s.rotate((0,0,0),(1,0,0),180).rotate((0,0,0),(0,1,0),15).translate(DATUM)
def local_button(s):return s.rotate((0,0,0),(1,0,0),180).translate((22.5,0,-10))
def button_global(s):return global_shape(local_button(s))
def button_original(s):return s.translate(tuple(-v for v in DATUM)).rotate((0,0,0),(0,1,0),-15).rotate((0,0,0),(1,0,0),180).translate((-22.5,0,10)).rotate((0,0,0),(1,0,0),180)

def build_grip():
    outer=cq.Workplane('XY').box(45,35,125).translate((0,0,62.5)).edges('|Z').fillet(5).faces('>Z or <Z').edges().chamfer(2).val()
    pocket=box(-12,12,-10,10,49,115)
    # Empty internal wiring plenum; the battery is above this grip.
    chamber=box(-12,12,-10,10,19,52.3)
    wire=box(2,10,-5,5,-.1,20)
    body=outer.cut(pocket).cut(chamber).cut(wire)
    # Capture pod attaches to the upper front, above the bank itself.
    for y,z in [(0,-22),(0,-30),(-7,-38)]:body=body.cut(ins((22.5,-y,-z-10),(-1,0,0)))
    body=body.cut(cyl(2,13,(22.6,-7.5,26),(-1,0,0)))
    minus=body.intersect(box(-23,23,-18,0,-.1,126))
    plus=body.intersect(box(-23,23,0,18,-.1,126))
    for u,w in CLAMPS:
        plus=plus.cut(cyl(1.8,18,(u,-.1,w),(0,1,0))).cut(cyl(3.1,6,(u,11.7,w),(0,1,0)))
        minus=minus.cut(ins((u,0,w),(0,-1,0)))
    for u,v in TOP:
        h=ins((u,v,0),(0,0,1))
        if v<0:minus=minus.cut(h)
        else:plus=plus.cut(h)
    # Rails lie outside the component pocket and away from fasteners.
    for u in [-18.7,18.7]:
        for a,b in [(59,85),(96,107)]:
            tongue=box(u-.7,u+.7,-.3,1.8,a,b)
            minus=minus.fuse(tongue)
            plus=plus.cut(box(u-1,u+1,-.05,2.1,a-.3,b+.3))
    for v in [-10,10]:
        key=box(-6,-2,v-1.5,v+1.5,-2,.2)
        if v<0:minus=minus.fuse(key)
        else:plus=plus.fuse(key)
    return {'grip_insert_half':minus.clean(),'grip_screw_half':plus.clean()}

def build_saddle():
    c=math.cos(math.radians(15));s=math.sin(math.radians(15))
    rear=(-75-22.5*c,-61.6+22.5*s);front=(-75+22.5*c,-61.6-22.5*s)
    saddle=cq.Workplane('XZ',origin=(0,21,0)).polyline([(-120,-41),(-20,-41),(-20,-46),front,rear,(-120,-46)]).close().extrude(42).val()
    for u,v in TOP:
        saddle=saddle.cut(global_shape(cyl(1.8,80.3,(u,v,-80),(0,0,1))))
        saddle=saddle.cut(global_shape(cyl(3.1,73,(u,v,-80),(0,0,1))))
    saddle=saddle.cut(global_shape(box(2,10,-5,5,-80,.1)))
    for v in [-10,10]:saddle=saddle.cut(global_shape(box(-6.3,-1.7,v-1.8,v+1.8,-2.3,.1)))
    for x in [-108,-38]:
        for y in [-17,17]:saddle=saddle.cut(ins((x,y,-41),(0,0,-1)))
    return saddle.clean()

def reference_hardware():
    result={'battery_ultralink_nominal':box(-106.6,-29.4,-30.5,4.5,-32.64,-7.94),
            'side_output_and_adapter_allowance':box(-82.7,-53.3,4.5,31.7,-32.64,-8),
            'power_wire_throat':global_shape(box(2.3,9.7,-4.7,4.7,-25,19.3)),
            'button_wire_entry':global_shape(cyl(1.5,12.7,(22.5,-7.5,26),(-1,0,0)))}
    for u,w in CLAMPS:result[f'grip_M3x16_{u}_{w}']=global_shape(cyl(1.5,16,(u,11.7,w),(0,-1,0)).fuse(cyl(2.75,3,(u,11.7,w),(0,1,0))))
    for u,v in TOP:result[f'grip_top_M3x10_{u}_{v}']=global_shape(cyl(1.5,10,(u,v,-7),(0,0,1)).fuse(cyl(2.75,3,(u,v,-10),(0,0,1))))
    return result
