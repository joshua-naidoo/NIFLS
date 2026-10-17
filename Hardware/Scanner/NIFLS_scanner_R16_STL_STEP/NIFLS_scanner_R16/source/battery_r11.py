"""Ultra-Link UL-PB560A horizontal cassette; output points +Y from long edge."""
import cadquery as cq
from grip_r10 import box,cyl,ins
FASTENERS=[(x,y) for x in [-106,-8] for y in [-42,42]]
CAP=[(y,z) for y in [-41.5,41.5] for z in [-15,-34]]
SIDE=[(x,z) for x in [-89,-47] for z in [-12,-34]]
def build_battery():
    roof=cq.Workplane(obj=box(-120,0,-47,47,-7.64,0)).edges().chamfer(2).val()
    tray=cq.Workplane(obj=box(-114,0,-47,47,-41,-7.64)).edges().chamfer(2).val()
    tray=tray.cut(box(-114.1,-29.1,-30.8,4.8,-32.94,-7.54))
    tray=tray.cut(box(-83,-53,4.5,47.1,-32.94,-7.54))
    tray=tray.cut(box(-114.1,-12,26.5,32,-32.94,-7.54))
    tray=tray.cut(box(-70,-54,-5,32,-38,-35.8))
    tray=tray.cut(box(-70,-54,-5,5,-41.1,-35.7))
    tray=tray.cut(box(-70,-54,26.5,32,-38,-7.54))
    roof=roof.cut(box(-27,-13,0,32,-7.74,-3.5))
    roof=roof.cut(box(-27,-13,-5,5,-7.74,.1))
    for x,y in FASTENERS:
        roof=roof.cut(cyl(1.8,8,(x,y,.1),(0,0,-1))).cut(cyl(3.1,3.3,(x,y,.1),(0,0,-1)))
        tray=tray.cut(ins((x,y,-7.64),(0,0,-1)))
    for x in [-92,-32]:
        for y in [-17,17]:roof=roof.cut(ins((x,y,0),(0,0,-1)))
    for x in [-78,-48]:roof=roof.cut(box(x-.3,x+10.3,-5.3,5.3,-2.3,.1))
    for x in [-108,-38]:
        for y in [-17,17]:
            tray=tray.cut(cyl(1.8,10.2,(x,y,-30.9),(0,0,-1)))
            tray=tray.cut(cyl(3.1,7.3,(x,y,-30.9),(0,0,-1)))
    for y in [-35,9]:
        for a,b in [(-103,-95),(-40,-32)]:
            tray=tray.fuse(box(a,b,y-.6,y+.6,-7.84,-5.84))
            roof=roof.cut(box(a-.3,b+.3,y-.9,y+.9,-7.74,-5.54))
    # Flush side service panel: connector can be unplugged before bank removal.
    tray=tray.cut(box(-95,-41,40,47.1,-38,-7.94))
    side=box(-94.7,-41.3,40.3,47,-37.7,-8.24)
    for x,z in SIDE:
        tray=tray.cut(ins((x,40,z),(0,-1,0)))
        side=side.cut(cyl(1.8,7,(x,47.1,z),(0,-1,0))).cut(cyl(3.1,3.3,(x,47.1,z),(0,-1,0)))
    cap=cq.Workplane(obj=box(-120,-114,-47,47,-41,-7.94)).edges().chamfer(2).val()
    cap=cap.cut(box(-117,-113.9,-35,38.5,-32.94,-10.94))
    for ya,yb in [(-30.3,-24.3),(-1.7,4.3)]:cap=cap.fuse(box(-117.2,-106.9,ya,yb,-32.64,-28.64))
    for y,z in CAP:
        cap=cap.cut(cyl(1.8,6.2,(-120.1,y,z),(1,0,0))).cut(cyl(3.1,3.1,(-120.1,y,z),(1,0,0)))
        tray=tray.cut(ins((-114,y,z),(1,0,0)))
    for y in [-41,41]:
        cap=cap.fuse(box(-114.2,-112,y-1,y+1,-26,-23))
        tray=tray.cut(box(-114.1,-111.7,y-1.3,y+1.3,-26.3,-22.7))
    for y in [-40,40]:tray=tray.fuse(box(-7,0,y-5,y+5,-26,-16)).cut(ins((0,y,-21),(-1,0,0)))
    return {'22_battery_roof':roof.clean(),'23_battery_tray':tray.clean(),'24_battery_rear_cover':cap.clean(),'25_connector_access_cover':side.clean()}
def reference_hardware():
    result={}
    for x,y in FASTENERS:result[f'cassette_M3x8_{x}_{y}']=cyl(1.5,8,(x,y,-3.2),(0,0,-1)).fuse(cyl(2.75,3,(x,y,-3.2),(0,0,1)))
    for x in [-108,-38]:
        for y in [-17,17]:result[f'tray_saddle_M3x6_{x}_{y}']=cyl(1.5,6,(x,y,-38.2),(0,0,-1)).fuse(cyl(2.75,3,(x,y,-38.2),(0,0,1)))
    for y,z in CAP:result[f'cover_M3x6_{y}_{z}']=cyl(1.5,6,(-117,y,z),(1,0,0)).fuse(cyl(2.75,3,(-120,y,z),(1,0,0)))
    for x,z in SIDE:result[f'side_M3x8_{x}_{z}']=cyl(1.5,8,(x,43.8,z),(0,-1,0)).fuse(cyl(2.75,3,(x,43.8,z),(0,1,0)))
    result['battery_side_power_wire_lane']=box(-113.7,-14,26.8,31.7,-32.64,-8)
    result['roof_power_wire_crossing']=box(-26.7,-13.3,.3,31.7,-7.34,-3.8)
    result['grip_signal_under_battery']=box(-69.7,-54.3,-4.7,31.7,-37.7,-36.1)
    return result
