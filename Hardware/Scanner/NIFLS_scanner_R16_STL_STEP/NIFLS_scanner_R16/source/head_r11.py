"""33 mm passive-vent Pi enclosure, PCB shifted 5 mm forward for rear controls."""
import cadquery as cq
from grip_r10 import box,cyl,ins
import math
CLOSURE=[(x,y) for y in [-40,40] for x in ([-111,-43,-9] if y<0 else [-111,-66,-9])]
def build_head():
    outer=cq.Workplane(obj=box(-120,0,-47,47,0,33)).edges().chamfer(2).val()
    shell=outer.cut(box(-116.5,-6,-43.5,43.5,3.5,29.5))
    shell=shell.cut(box(-96,-51,-49,-27.7,10,22))
    shell=shell.cut(box(-7,1,-8.3,8.3,6.8,10.4))
    shell=shell.cut(cyl(2,7.2,(-7,0,14),(1,0,0)))
    for x in [-109,-103,-97,-91,-85,-79]:shell=shell.cut(box(x,x+2.4,43,49,7,16))
    lower=shell.intersect(box(-125,5,-50,50,-1,29.5))
    upper=shell.intersect(box(-125,5,-50,50,29.5,35))
    for x,y in CLOSURE:
        lower=lower.cut(cyl(5.3,3,(x,y,27),(0,0,1)))
        lower=lower.fuse(cyl(5,23.5,(x,y,3.5),(0,0,1))).cut(ins((x,y,27),(0,0,-1)))
        upper=upper.fuse(cyl(5,6,(x,y,27),(0,0,1)))
        upper=upper.cut(cyl(1.8,3.1,(x,y,26.9),(0,0,1))).cut(cyl(3.1,3.4,(x,y,29.8),(0,0,1)))
    for x in [-95.5,-37.5]:
        for y in [-24.5,24.5]:
            lower=lower.fuse(cyl(4,8.5,(x,y,3.5),(0,0,1))).cut(cyl(1.55,13,(x,y,-.1),(0,0,1)))
            nut=cq.Workplane('XY').workplane(offset=-.1).center(x,y).polygon(6,5.6/math.cos(math.pi/6)).extrude(3.6).val()
            lower=lower.cut(nut)
    for x in [-92,-32]:
        for y in [-17,17]:
            lower=lower.fuse(cyl(4.8,3.5,(x,y,3.5),(0,0,1))).cut(cyl(1.8,8,(x,y,-.1),(0,0,1)))
            lower=lower.cut(cyl(3.1,3.4,(x,y,3.7),(0,0,1)))
    for x in [-78,-48]:lower=lower.cut(box(x-.3,x+10.3,-5.3,5.3,-.1,2.3))
    lower=lower.cut(box(-35,-5,-10,10,-.1,3.6))
    for y in [-40,40]:
        lower=lower.fuse(box(-7,0,y-5,y+5,8,18)).cut(ins((0,y,13),(-1,0,0)))
    for x in [-88,-35]:
        for y in [-44.8,44.8]:
            lower=lower.fuse(box(x,x+10,y-.6,y+.6,29.3,31))
            upper=upper.cut(box(x-.3,x+10.3,y-.9,y+.9,29.4,31.3))
    # Passive roof exhaust only: no 3010 fan mount or assumed heatsink clearance.
    for x in [-87,-81,-75,-69,-63,-57,-51]:upper=upper.cut(box(x,x+2.4,-10,19,29.4,33.2))
    plane=cq.Plane(origin=(-63,46.5,23.5),xDir=(-1,0,0),normal=(0,1,0))
    for s in cq.Workplane(plane).text('NIFLS - Joshua Naidoo',5.5,.5,font='Arial',kind='bold',halign='center',valign='center',combine=False).vals():lower=lower.cut(s)
    return {'01_pi_base':lower.clean(),'02_pi_lid':upper.clean()}
def reference_hardware():
    return {f'head_closure_M3x6_{x}_{y}':cyl(1.5,6,(x,y,29.8),(0,0,-1)).fuse(cyl(2.75,3,(x,y,29.8),(0,0,1))) for x,y in CLOSURE}
