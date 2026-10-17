"""NIFLS scanner enclosure R8. Units mm. Run with CadQuery 2.8.
Assembly axes: +X optical axis, +Z head up. Mechanical prototype.
"""
import sys, os, json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'work'/'cadlib'))
import cadquery as cq
from cadquery import Vector as V

TRIGGER_WIRE_PATH_POINTS=[(0,7.5,-36),(-6,7.5,-36),(-14,0,-36),(-14,0,0)]
TRIGGER_WIRE_RADIUS=2.0
TRIGGER_MOUNT_CENTRES=[(0,-22),(0,-30),(-7,-38)]
OUT=ROOT/'generated_models'
OUT.mkdir(parents=True,exist_ok=True)

def box(x0,x1,y0,y1,z0,z1):
    return cq.Solid.makeBox(x1-x0,y1-y0,z1-z0,V(x0,y0,z0))
def cyl(r,h,p,d=(0,0,1)):
    return cq.Solid.makeCylinder(r,h,V(*p),V(*d))
def cone(r1,r2,h,p,d=(0,0,1)):
    return cq.Solid.makeCone(r1,r2,h,V(*p),V(*d))
def fuse(*args):
    s=args[0]
    for t in args[1:]: s=s.fuse(t)
    return s.clean()
def chamfer(s,d=2):
    return cq.Workplane(obj=s).edges().chamfer(d).val()
def insert(p,d=(0,0,-1),diam=4.2):
    return cyl(diam/2,4.5,p,d).fuse(cone(2.4,diam/2,.6,p,d))
def hexhole(x,y,z,h,af=5.6):
    return cq.Workplane('XY').workplane(offset=z).center(x,y).polygon(6,af/math.cos(math.pi/6)).extrude(h).val()
def main_parts():
    from head_r11 import build_head
    return build_head()

def optical_parts():
    # Camera rear support plate; optical axis global y0,z24.
    bulk=chamfer(box(0,6,-47,47,-13,61))
    # Camera rear pocket: room for component side/FFC; posts isolated from SMD.
    bulk=bulk.cut(box(2.5,6.2,-12.8,12.8,9.3,33.762))
    for y in [-10.5,10.5]:
        for z in [11.6,24.1]:
            bulk=bulk.fuse(cyl(2.4,4,(2.5,y,z),(1,0,0)))
            bulk=bulk.cut(cyl(.85,4.2,(6.6,y,z),(-1,0,0)))
    # FFC leaves upper PCB edge and passes back to Pi through matched slot.
    bulk=bulk.cut(box(-.2,6.2,-8.3,8.3,34.8,38.4))
    bulk=bulk.cut(box(2.5,6.2,-8.3,8.3,31.5,38.4))
    for y in [-40,40]:
        for z in [7,41]:
            bulk=bulk.cut(cyl(1.8,6.4,(-.2,y,z),(1,0,0)))
            bulk=bulk.cut(cyl(3.1,3.3,(6,y,z),(-1,0,0)))
    # Hood mounting inserts. Nose flange has matching removable screw access.
    for y in [-35,35]:
        for z in [-5,53]:
            bulk=bulk.cut(insert((6,y,z),(-1,0,0)))
    # Cartridge mounting towers: screw insertion through front retainer.
    filter_pts=[]
    for a in [270,30,150]:
        y=21*math.cos(math.radians(a)); z=24+21*math.sin(math.radians(a))
        filter_pts.append((y,z))
        bulk=bulk.fuse(cyl(4.5,7,(6,y,z),(1,0,0)))
        bulk=bulk.cut(insert((13,y,z),(-1,0,0)))
    # Hood: broad rear flange; cylindrical opaque shroud from filter x18 to x53.
    flange=chamfer(box(6,12,-47,47,-13,61))
    tube=cyl(37,39,(12,0,24),(1,0,0)).fuse(cone(37,35,2,(51,0,24),(1,0,0)))
    hood=flange.fuse(tube).cut(cyl(32,48,(5.5,0,24),(1,0,0)))
    for y in [-35,35]:
        for z in [-5,53]:
            hood=hood.cut(cyl(1.8,6.4,(5.8,y,z),(1,0,0)))
            hood=hood.cut(cyl(3.1,3.3,(12,y,z),(-1,0,0)))
    # Keyed flange register (one on either side), 0.3mm per-side clearance.
    for y in [-43,43]:
        bulk=bulk.fuse(box(5.8,7.8,y-1,y+1,19,29))
        hood=hood.cut(box(5.9,8.1,y-1.3,y+1.3,18.7,29.3))
    parts={'03_camera_bulkhead':bulk.clean(),'04_contact_hood_35mm':hood.clean()}
    # Two glass thickness choices. Disc Ã˜30.5 receives Ã˜31.1 pocket.
    for th in [1,2]:
        carrier=cyl(25.5,5.3,(13,0,24),(1,0,0))
        carrier=carrier.cut(cyl(14.25,6,(12.8,0,24),(1,0,0)))
        carrier=carrier.cut(cyl(15.55,th+.5,(18-th,0,24),(1,0,0)))
        for y,z in filter_pts:
            carrier=carrier.cut(cyl(1.8,6,(12.8,y,z),(1,0,0)))
        parts[f'05_filter_carrier_{th}mm_glass']=carrier.clean()
    ret=cyl(25.5,5,(18.3,0,24),(1,0,0)).cut(cyl(14.25,5.4,(18.1,0,24),(1,0,0)))
    for y,z in filter_pts:
        ret=ret.cut(cyl(1.8,5.4,(18.1,y,z),(1,0,0)))
        ret=ret.cut(cyl(3.1,3.3,(23.3,y,z),(-1,0,0)))
    parts['06_filter_retainer']=ret.clean()
    return parts

def small_parts():
    key=box(0,10,0,10,0,4)
    # Insert calibration coupon (nominal press-fit seats intentionally NOT +0.3).
    coupon=chamfer(box(0,54,0,16,0,8),1)
    for i,d in enumerate([4.0,4.2,4.4,4.6]):
        x=8+i*12
        coupon=coupon.cut(insert((x,8,8),diam=d))
        labels=cq.Workplane('XY').workplane(offset=7.5).center(x,2.8).text(str(d),2.4,.5,font='Arial',kind='bold',combine=False).vals()
        for s in labels: coupon=coupon.cut(s)
    return {'10_alignment_key_print_2':key,'11_insert_fit_coupon':coupon.clean()}

def onbed(s):
    b=s.BoundingBox()
    return s.translate((-b.xmin,-b.ymin,-b.zmin))
def print_transform(name,s):
    if name=='02_pi_lid': s=s.rotate((0,0,0),(1,0,0),180)
    elif name.startswith(('03_','04_','05_','06_')): s=s.rotate((0,0,0),(0,1,0),-90)
    elif name=='07_grip_insert_half': s=s.rotate((0,0,0),(1,0,0),90)
    elif name=='08_grip_screw_half': s=s.rotate((0,0,0),(1,0,0),-90)
    elif name=='25_connector_access_cover': s=s.rotate((0,0,0),(1,0,0),-90)
    elif name=='22_battery_roof': s=s.rotate((0,0,0),(1,0,0),180)
    elif name=='24_battery_rear_cover': s=s.rotate((0,0,0),(0,1,0),-90)
    elif name=='09_angled_saddle': s=s.rotate((0,0,0),(1,0,0),180)
    elif name.startswith(('17_','18_')):
        from tof_r13 import orient_for_print
        s=orient_for_print(name,s)
    elif name.startswith(('12_','13_','14_','15_','16_')):
        from button_r3 import orient_for_print
        from grip_r10 import button_original
        s=orient_for_print(name,button_original(s))
    if name.startswith(('19_','20_','21_')):
        from power_r11 import orient_for_print
        s=orient_for_print(name,s)
    return onbed(s)

def build_all():
    from grip_r10 import build_grip
    from grip_r10 import build_saddle
    parts={}
    print('Building main head',flush=True);parts.update(main_parts())
    print('Building optics',flush=True);parts.update(optical_parts())
    print('Building grip',flush=True)
    gr=build_grip()
    parts['07_grip_insert_half']=gr['grip_insert_half']
    parts['08_grip_screw_half']=gr['grip_screw_half']
    saddle=build_saddle()
    parts['09_angled_saddle']=saddle
    from battery_r14 import build_battery
    parts.update(build_battery())
    from button_r3 import build_button
    print('Building recessed button',flush=True)
    from grip_r10 import button_global
    parts.update({k:button_global(v) for k,v in build_button().items()})
    parts.update(small_parts())
    from tof_r13 import build_tof,update_optics
    parts=update_optics(parts)
    from filter_r13 import update_filter
    parts=update_filter(parts)
    parts.update(build_tof())
    from power_r11 import update_head,build_power
    parts=update_head(parts)
    parts.update(build_power())
    from cable_r15 import update
    parts=update(parts)
    from engraving_r16 import update as engrave
    parts=engrave(parts)
    return parts

def main():
    parts=build_all();manifest=[];assembly=cq.Assembly(name='NIFLS_R16_mechanical_prototype')
    for name,shape in parts.items():
        print('Export',name,flush=True)
        assert shape.isValid(),name+' invalid'
        assert len(shape.Solids())==1,(name,len(shape.Solids()))
        p=print_transform(name,shape);bb=p.BoundingBox()
        dims=[bb.xlen,bb.ylen,bb.zlen]
        assert max(dims)<=180.001,(name,dims)
        (OUT/'STL').mkdir(exist_ok=True);(OUT/'STEP_parts').mkdir(exist_ok=True)
        cq.exporters.export(p,str(OUT/'STL'/f'{name}.stl'),tolerance=.035,angularTolerance=.1)
        cq.exporters.export(p,str(OUT/'STEP_parts'/f'{name}.step'))
        if name.startswith(('07_','08_')):
            from grip_r10 import global_shape
            shape=global_shape(shape)
        if name=='10_alignment_key_print_2':
            assembly.add(shape.translate((-78,-5,-2)),name=name+'_A')
            assembly.add(shape.translate((-48,-5,-2)),name=name+'_B')
        elif name=='18_tof_edge_clamp_print_2':
            from tof_r13 import other_clamp
            assembly.add(shape,name=name+'_A')
            assembly.add(other_clamp(shape),name=name+'_B')
        elif name=='16_switch_shim_0p4_print_2':
            assembly.add(shape,name=name+'_A')
            assembly.add(shape.translate((0,16,0)),name=name+'_B')
        elif name not in ['05_filter_carrier_1mm_glass','11_insert_fit_coupon']:
            assembly.add(shape,name=name)
        # Exact assembly position STL for technical rendering and interference.
        (ROOT/'work'/'assembly_meshes_r16').mkdir(parents=True,exist_ok=True)
        cq.exporters.export(shape,str(ROOT/'work'/'assembly_meshes_r16'/f'{name}.stl'),tolerance=.05,angularTolerance=.12)
        manifest.append({'part':name,'print_dimensions_mm':[round(x,3) for x in dims],
                         'volume_mm3':round(p.Volume(),2),'cad_valid':p.isValid(),'solids':len(p.Solids())})
    assembly.save(str(OUT/'NIFLS_R16_assembled.step'))
    (OUT/'part_manifest.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2),flush=True)
    # Avoid VTK/Python cleanup delays on Windows after all writes complete.
    sys.stdout.flush(); os._exit(0)

if __name__=='__main__':
    try: main()
    except BaseException:
        import traceback
        traceback.print_exc();sys.stdout.flush();sys.stderr.flush();os._exit(1)
