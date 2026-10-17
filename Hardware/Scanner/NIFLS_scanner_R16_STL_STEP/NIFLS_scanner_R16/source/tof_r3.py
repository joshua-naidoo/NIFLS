"""Open-edge 17 x 7 x 1 mm ToF carrier; chip identity is unconfirmed.
Local X is PCB normal, Y is its 17mm length, Z is its 7mm width.
The bracket aims inward 45 degrees, bypassing the camera filter.
"""
import math
import cadquery as cq
from cadquery import Vector as V

ANGLE=45
ORIGIN=(25,0,47)
MOUNTS=[(-22,44),(22,44)]
def box(x0,x1,y0,y1,z0,z1):
    return cq.Solid.makeBox(x1-x0,y1-y0,z1-z0,V(x0,y0,z0))
def cyl(r,h,p,d=(1,0,0)):
    return cq.Solid.makeCylinder(r,h,V(*p),V(*d))
def fuse(*s):
    a=s[0]
    for b in s[1:]:a=a.fuse(b)
    return a.clean()
def world(s):return s.rotate((0,0,0),(0,1,0),ANGLE).translate(ORIGIN)
def local(s):return s.translate(tuple(-v for v in ORIGIN)).rotate((0,0,0),(0,1,0),-ANGLE)
def insert(p):
    return cyl(2.1,4.5,p,(-1,0,0)).fuse(cq.Solid.makeCone(2.4,2.1,.6,V(*p),V(-1,0,0)))
def other_clamp(s):return world(local(s).rotate((0,0,0),(1,0,0),180))

def build_tof():
    base=box(-8,-6.3,-13.5,13.5,-2.5,2.5)
    for side in [-1,1]:
        lo,hi=sorted([side*9.8,side*13.5])
        base=base.fuse(box(-8,-.3,lo,hi,-2.5,2.5))
        lo,hi=sorted([side*7.7,side*13.5])
        base=base.fuse(box(-1.8,-.3,lo,hi,-3.8,3.8))
        base=base.fuse(cyl(3.8,4.5,(-4.8,side*11.6,0)))
        base=base.cut(insert((-.3,side*11.6,0)))
        # Hard edge fence: 17.6mm span, 0.3mm clearance at each PCB end.
        lo,hi=sorted([side*8.8,side*10.2])
        base=base.fuse(box(-.5,1.3,lo,hi,-3.8,3.8))
    base=world(base.clean())
    for y,z in MOUNTS:
        ear=cyl(3.5,3.5,(20,y,z))
        lo,hi=sorted([y,math.copysign(11,y)])
        bridge=box(20,23.5,lo,hi,42,50)
        side=1 if y>0 else -1
        clearance=world(cyl(4.1,5.4,(1.0,side*11.6,0)))
        bridge=bridge.cut(clearance)
        base=base.fuse(ear).fuse(bridge)
        base=base.cut(cyl(1.8,4,(19.8,y,z)))
    for y in [-11.6,11.6]:
        base=base.cut(world(insert((-.3,y,0))))
        base=base.cut(world(cyl(1.8,6.8,(-.5,y,0))))
        base=base.cut(world(cyl(3.1,3.8,(2.7,y,0))))
    # One clamp printed twice; opposite end uses a 180 degree local-X turn.
    clamp=fuse(cyl(3.8,4.7,(1.3,11.6,0)),box(1.3,3.0,7.7,11.6,-3.8,3.8))
    clamp=clamp.cut(cyl(1.8,5.1,(1.1,11.6,0)))
    clamp=clamp.cut(cyl(3.1,3.5,(2.7,11.6,0)))
    return {'17_tof_cradle':base.clean(),'18_tof_edge_clamp_print_2':world(clamp.clean())}

def update_optics(parts):
    # The three filter screw positions are rotated in the master optical builder.
    # Relief is above the glass and retaining shoulder, not in the clear aperture.
    relief=box(15,24.5,-26,26,42,62)
    for name in ['05_filter_carrier_1mm_glass','05_filter_carrier_2mm_glass','06_filter_retainer']:
        parts[name]=parts[name].cut(relief).clean()
    hood=parts['04_contact_hood_35mm']
    # Local expanded bore retains >=2.8mm of the 37mm-radius opaque tube.
    hood=hood.cut(cyl(34.2,11.5,(15.5,0,24)))
    for y,z in MOUNTS:
        hood=hood.fuse(cyl(3.9,8,(12,y,z)))
        hood=hood.cut(cyl(3.8,8.1,(20,y,z)))
        hood=hood.cut(insert((20,y,z)))
    parts['04_contact_hood_35mm']=hood.clean()
    parts['03_camera_bulkhead']=parts['03_camera_bulkhead'].cut(cyl(2,6.4,(-.2,0,42))).clean()
    parts['02_pi_lid']=parts['02_pi_lid'].cut(cyl(2,7.2,(-7,0,42))).clean()
    return parts

def orient_for_print(name,s):
    s=local(s)
    return s.rotate((0,0,0),(0,1,0),-90 if name=='17_tof_cradle' else 90)

def reference_hardware():
    ref={'tof_pcb_17x7x1':world(box(0,1,-8.5,8.5,-3.5,3.5)),
         'tof_front_component_allowance':world(box(1,4,-7.4,7.4,-3.2,3.2)),
         'tof_rear_connector_allowance':world(box(-6,0,-7.4,7.4,-6.5,6.5))}
    for y,z in MOUNTS:
        ref['tof_mount_screw_'+str(y)]=fuse(cyl(1.5,6,(23.5,y,z),(-1,0,0)),cyl(2.75,3,(23.5,y,z)))
    for y in [-11.6,11.6]:
        ref['tof_clamp_screw_'+str(y)]=world(fuse(cyl(1.5,6,(2.7,y,0),(-1,0,0)),cyl(2.75,3,(2.7,y,0))))
    return ref

def test_cone():
    # Assumed 25-degree full cone, 4mm aperture centred on PCB. Not a chip specification.
    h=45.0
    cone=cq.Solid.makeCone(2,2+h*math.tan(math.radians(12.5)),h,V(4,0,0),V(1,0,0))
    return world(cone).intersect(box(-10,53,-70,70,-30,90))
