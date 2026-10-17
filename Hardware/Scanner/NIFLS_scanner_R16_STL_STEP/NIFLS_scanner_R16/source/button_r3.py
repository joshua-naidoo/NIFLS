"""NIFLS R3 recessed capture button. Global assembly coordinates in mm."""
import cadquery as cq
from cadquery import Vector as V

CENTRE=(0,0,-30)
TRAVEL=.7
SHIM=.4
MOUNTS=[(0,-22),(0,-30),(-7,-38)]
CLOSURES=[(y,z) for y in [-12,12] for z in [-20,-40]]
CRADLE_SCREWS=[(-8,-30),(8,-30)]

def box(x0,x1,y0,y1,z0,z1):
    return cq.Solid.makeBox(x1-x0,y1-y0,z1-z0,V(x0,y0,z0))
def cyl(r,h,p,d=(1,0,0)):
    return cq.Solid.makeCylinder(r,h,V(*p),V(*d))
def fuse(*shapes):
    s=shapes[0]
    for t in shapes[1:]:s=s.fuse(t)
    return s.clean()
def insert(p):
    return cyl(2.1,4.5,p,(-1,0,0)).fuse(cq.Solid.makeCone(2.4,2.1,.6,V(*p),V(-1,0,0)))
def outer():
    return cq.Workplane(obj=box(0,23,-16.5,16.5,-45,-15)).edges().chamfer(2).val()

def build_button():
    shape=outer()
    rear=shape.intersect(box(-1,6,-18,18,-46,-14))
    front=shape.intersect(box(6,24,-18,18,-46,-14))
    front=front.cut(box(5.9,20,-12.9,12.9,-41.4,-18.6))
    for y,z in CLOSURES:
        rear=rear.cut(insert((6,y,z)))
        front=front.fuse(cyl(4,14,(6,y,z)))
        front=front.cut(cyl(1.8,18,(5.8,y,z)))
        front=front.cut(cyl(3.1,4.2,(19,y,z)))
    # Both guidance and travel stops are part of the front shell.
    front=front.fuse(cyl(10.3,6,(14,0,-30)))
    front=front.cut(cyl(7.3,10,(13.8,0,-30)))
    front=front.cut(cyl(9.3,2.2,(17.8,0,-30)))
    # Flat cap flange rests against x20 released and x17.8 pressed.
    cap=fuse(cyl(7,2,(20,0,-30)),cyl(9,1.5,(18.5,0,-30)),cyl(7,3,(15.5,0,-30)))
    cap=cap.cut(cyl(5.5,4.2,(15.3,0,-30)))
    cap=cap.fuse(cyl(1.5,.6,(19,0,-30)))
    # Small cap edge bevel preserves flat front and exact 0.7 mm stop stroke.
    cap=cap.cut(cyl(7,0.5,(21.5,0,-30)).cut(cq.Solid.makeCone(7,6.5,.5,V(21.5,0,-30),V(1,0,0))))
    for y,z in MOUNTS:
        rear=rear.cut(cyl(1.8,6.4,(-.2,y,z)))
        rear=rear.cut(cyl(3.1,3.3,(2.7,y,z)))
    rear=rear.cut(cyl(2,6.4,(-.2,7.5,-36)))
    for y,z in CRADLE_SCREWS:
        rear=rear.fuse(cyl(4,1,(6,y,z)))
        rear=rear.cut(insert((7,y,z)))
    # Axial flange registers use 0.3 mm receiving clearance on each flank.
    for y in [-14.8,14.8]:
        rear=rear.fuse(box(5.8,7.5,y-.6,y+.6,-32,-28))
        front=front.cut(box(5.9,7.8,y-.9,y+.9,-32.3,-27.7))
    # Cradle reference has zero shim; shift +0.4 for supplied nominal assembly.
    cradle=fuse(box(7,9.5,-12,12,-34,-26),box(9.3,13.55,-4.9,4.9,-34.9,-25.1))
    cradle=cradle.cut(box(11.05,14,-3.4,3.4,-33.4,-26.6))
    for y in [-2.54,2.54]:
        cradle=cradle.cut(cyl(.85,5,(6.9,y,-30)))
        cradle=cradle.cut(cyl(1.5,3.1,(6.9,y,-30)))
    for y,z in CRADLE_SCREWS:
        cradle=cradle.cut(cyl(1.8,4,(6.9,y,z)))
    cradle=cradle.translate((SHIM,0,0))
    shim=cyl(4,SHIM,(7,-8,-30)).cut(cyl(1.8,SHIM+.2,(6.9,-8,-30)))
    return {'12_button_backplate':rear.clean(),'13_button_pod':front.clean(),
            '14_button_cap':cap.clean(),'15_switch_cradle':cradle.clean(),
            '16_switch_shim_0p4_print_2':shim.clean()}

def pressed(shape,travel):return shape.translate((-travel,0,0))
def orient_for_print(name,s):
    return s.rotate((0,0,0),(0,1,0),90 if name in ['13_button_pod','14_button_cap'] else -90)

def reference_hardware():
    base=11.05+SHIM
    ref={'switch_fixed_envelope':box(base,base+6.7,-3.1,3.1,-33.1,-26.9)}
    for i,y in enumerate([-2.54,2.54]):
        ref['switch_pin_'+str(i)]=box(base-3.5,base,y-.45,y+.45,-30.2,-29.8)
    for i,(y,z) in enumerate(MOUNTS):
        ref['backplate_screw_'+str(i)]=fuse(cyl(1.5,6,(2.7,y,z),(-1,0,0)),cyl(2.75,3,(2.7,y,z)))
    for i,(y,z) in enumerate(CLOSURES):
        ref['pod_screw_'+str(i)]=fuse(cyl(1.5,16,(19,y,z),(-1,0,0)),cyl(2.75,3,(19,y,z)))
    for i,(y,z) in enumerate(CRADLE_SCREWS):
        seat=9.5+SHIM
        ref['cradle_screw_'+str(i)]=fuse(cyl(1.5,6,(seat,y,z),(-1,0,0)),cyl(2.75,3,(seat,y,z)))
    return ref
