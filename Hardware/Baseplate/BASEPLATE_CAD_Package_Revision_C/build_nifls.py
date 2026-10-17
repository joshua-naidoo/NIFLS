"""NIFLS parametric mechanical prototype. Millimetres. Requires cadquery 2.8.
Run with Python; exports beside this script. Read DESIGN_NOTES.md before manufacture.
"""
from pathlib import Path
import json, math, csv
import cadquery as cq

OUT=Path(__file__).resolve().parent
GLASS_T=6.0
CONTACT_SLOT=0.8
SWITCH_LENGTH=23.4
SWITCH_HEIGHT=12.4
PITCH_X,PITCH_Y=13.5,16.5
BOARD_TOP=51.0
GLASS_BOTTOM=BOARD_TOP+18
TOP=GLASS_BOTTOM+GLASS_T

def box(dx,dy,dz,x=0,y=0,z=0):
    return cq.Solid.makeBox(dx,dy,dz,cq.Vector(x-dx/2,y-dy/2,z))
def cyl(r,h,x=0,y=0,z=0):
    return cq.Solid.makeCylinder(r,h,cq.Vector(x,y,z))
def cuts(shape, cutters):
    return shape.cut(*cutters).clean() if cutters else shape
def fuse(shape, additions):
    return shape.fuse(*additions).clean() if additions else shape

mounts=[(x,y) for x in [-70,70] for y in [-59,59]]
frame_mounts=[(x,y) for x in [-80,80] for y in [-80,80]]
leds=[(c*PITCH_X-67.5,r*PITCH_Y-66) for c in range(11) for r in range(9)]
resistors=[(c*PITCH_X-67.5,g*49.5-72.5) for c in range(11) for g in range(3)]
cells=[(x,y) for x in [-24.75,-8.25,8.25,24.75] for y in [-31.25,31.25]]
print('Creating board',flush=True)
board=box(148,148,2,z=49)
holes=[cyl(.55,4,x+s*1.27,y,48) for x,y in leds for s in [-1,1]]
holes += [cyl(.55,4,x+s*5,y,48) for x,y in resistors for s in [-1,1]]
holes += [cyl(1.7,4,x,y,48) for x,y in mounts]
board=cuts(board,holes)

print('Creating taller base and two purchased-holder bays',flush=True)
base=cuts(box(174,174,64),[box(168,168,66,z=5)])
base=cuts(base,[box(146,162,5.2,y=-6,z=-.1),box(152,166,2.6,y=-6,z=.9),
                box(146,5,9.1,y=-86,z=0)])
base=fuse(base,[box(168,168,3,z=39),box(72,88,30,z=9)])
holder_centres=[-18,18]
bay_cuts=[]
for x in holder_centres:
    bay_cuts.append(box(32,64,30.2,x,0,8.9))
    for sign in [-1,1]:
        bay_cuts.append(box(26,10.1,30.2,x,sign*37,8.9))
        bay_cuts.append(box(5,4,7,x,sign*43,32))
base=cuts(base,bay_cuts)
base=fuse(base,[cyl(3.5,7,x,y,42) for x,y in mounts])
base=cuts(base,[cyl(1.25,8,x,y,41.5) for x,y in mounts])
base=fuse(base,[cyl(5,13,x,y,51) for x,y in frame_mounts])
base=cuts(base,[cyl(1.25,12,x,y,52) for x,y in frame_mounts])
# Provisional measured switch: 23 x 12 body, 0.2 clearance per side.
base=cuts(base,[box(6,SWITCH_LENGTH,SWITCH_HEIGHT,85.5,45,13-SWITCH_HEIGHT/2)])
# Open-bottom wire raceways, sheltered by partition, with 5 mm clear width.
rails=[box(43,1.5,4,55.5,s*3.25,35) for s in [-1,1]]
rails += [box(1.5,47,4,78+s*3.25,23.5,35) for s in [-1,1]]
base=fuse(base,rails)
base=cuts(base,[box(44,5,1.5,56,0,39),box(5,47,1.5,78,23.5,39),cyl(2.5,7,78,0,36)])
# Door retaining M3 screw, operated only from underneath.
base=fuse(base,[box(8,10,3,-65,-82,9),cyl(4,7.5,-65,-80,4.5)])
base=cuts(base,[cyl(1.25,7,-65,-80,4.5)])

# A 3 mm wall coupon, exported flat for economical fit checking.
switch_coupon=cuts(box(43.4,32.4,3),[box(SWITCH_LENGTH,SWITCH_HEIGHT,3.2,z=-.1)])
assert switch_coupon.isValid() and len(switch_coupon.Solids())==1
cq.exporters.export(switch_coupon,str(OUT/'switch_fit_coupon_23p4x12p4.step'))
cq.exporters.export(switch_coupon,str(OUT/'switch_fit_coupon_23p4x12p4.stl'))
print('Creating glass frame and sliding door',flush=True)
frame=cuts(box(174,174,TOP-64,z=64),[box(146,146,TOP-63,z=63.9),
                                                    box(152,152,GLASS_T+.1,z=GLASS_BOTTOM)])
register=cuts(box(167.4,167.4,3,z=61),[box(161.4,161.4,3.2,z=60.9)])
register=cuts(register,[cyl(5.4,3.2,x,y,60.9) for x,y in frame_mounts])
frame=fuse(frame,[register])
frame=cuts(frame,[cyl(1.7,TOP-60,x,y,60.5) for x,y in frame_mounts]+
                  [cyl(3.2,3.1,x,y,TOP-3) for x,y in frame_mounts])
door=box(151.4,163.6,2,y=-5.3,z=1.2)
door=fuse(door,[box(145.4,161.8,1,y=-6.2,z=3.2),box(156,3,9,y=-88.5)])
# Smooth support pad below the fixed bays; clears the 9.1 mm front slot.
door=fuse(door,[box(72,88,2.8,z=4.2)])
door=cuts(door,[cyl(1.7,5,-65,-80,0),box(28,1.3,2,0,-89.4,1.5)])
glass=box(150,150,GLASS_T,z=GLASS_BOTTOM)

parts={'01_diffuser_frame':frame,'02_LED_substrate':board,'03_base_for_two_4AA_holders':base,'04_sliding_battery_door':door}
print('Exporting and validating',flush=True)
report={'units':'mm','glass_thickness':GLASS_T,'board_to_glass':GLASS_BOTTOM-BOARD_TOP,
        'led_count':len(leds),'resistor_count':len(resistors),'purchased_holder_count':2,'holder_envelope_mm':[63,31,31],'overall_body_height_mm':75,
        'led_pitch':[PITCH_X,PITCH_Y],'resistor_pitch':10.0,'parts':{},'interferences_mm3':{}}
for name,shape in parts.items():
    assert shape.isValid() and len(shape.Solids())==1, name
    cq.exporters.export(shape,str(OUT/(name+'.step')))
    cq.exporters.export(shape.translate((0,0,-shape.BoundingBox().zmin)),str(OUT/(name+'.stl')),tolerance=.05,angularTolerance=.1)
    reimport=cq.importers.importStep(str(OUT/(name+'.step'))).val()
    assert reimport.isValid() and len(reimport.Solids())==1,name+' STEP roundtrip'
    assert abs(reimport.Volume()-shape.Volume())<.01
    bb=shape.BoundingBox()
    report['parts'][name]={'valid':True,'solid_count':1,'volume_mm3':shape.Volume(),'bounding_box_mm':[bb.xlen,bb.ylen,bb.zlen],'step_roundtrip_valid':True}
checks={**parts,'glass_reference':glass}
for i,(a,sa) in enumerate(checks.items()):
    for b,sb in list(checks.items())[i+1:]:
        vol=sa.intersect(sb).Volume()
        report['interferences_mm3'][a+' / '+b]=vol
        assert vol<.001,(a,b,vol)
report['switch_revision']={'opening_mm':[SWITCH_LENGTH,SWITCH_HEIGHT],'wall_mm':3,'clearance_per_side_mm':0.2,'status':'PROVISIONAL: 23 x 12 was measured at the switch base; confirm body at mounting rim and clip engagement using coupon. Exact switch envelope and wiring not verified.'}
report['door_sweep_mm3']={} 
for travel in [0,10,30,60,100,170]:
    v=base.intersect(door.translate((0,-travel,0))).Volume()
    report['door_sweep_mm3'][str(travel)]=v
    assert v<.001,('door travel',travel,v)
# Conservative continuous translational sweep, includes filled screw hole/notch.
swept=[box(151.4,333.6,2,y=-90.3,z=1.2),box(145.4,331.8,1,y=-91.2,z=3.2),
       box(156,173,9,y=-173.5)]
swept += [box(72,258,2.8,0,-85,4.2)]
report['continuous_door_sweep_0_to_170_mm_max_interference']=max(base.intersect(s).Volume() for s in swept)
assert report['continuous_door_sweep_0_to_170_mm_max_interference']<.001

assembly=cq.Assembly(name='NIFLS_mechanical_assembly')
colors=[(.72,.77,.81),(0.15,.45,.35),(.23,.3,.39),(.45,.5,.57)]
for (name,shape),color in zip(parts.items(),colors):
    assembly.add(shape,name=name,color=cq.Color(*color))
assembly.add(glass,name='REFERENCE_only_150x150x6_glass',color=cq.Color(.65,.85,.9,.35))
assembly.save(str(OUT/'NIFLS_assembly.step'))

# Envelope references are separate from the four printable components.
led_envelopes=[fuse(cyl(2.9,1,x,y,51),[cyl(2.5,7.6,x,y,52)]) for x,y in leds]
holder_envelopes=[box(31,63,31,x,0,7) for x in holder_centres]
connector_envelopes=[box(24,8,26,x,36,9) for x in holder_centres]
for env in holder_envelopes+connector_envelopes:
    assert base.intersect(env).Volume()<.001
    assert door.intersect(env).Volume()<.001
report['holder_checks']='Two 31 X x 63 Y x 31 Z envelopes; 0.5 mm lateral clearance, bottom Z7, top Z38, ceiling Z39.'
report['connector_checks']='Two provisional 24 x 8 x 26 envelopes in end recesses, collision-free; actual PP3 connector and wire bend dimensions unconfirmed.'
report['holder_insertion_checks']={}
for x in holder_centres:
    # Full downward insertion/removal sweep while door is removed.
    travel_envelope=box(31,63,71,x,0,-33)
    v=base.intersect(travel_envelope).Volume()
    report['holder_insertion_checks'][str(x)]=v
    assert v<.001
for led in led_envelopes:
    assert base.intersect(led).Volume()<.001
    assert frame.intersect(led).Volume()<.001
report['led_envelope_checks']='99 nominal 5.8 mm flange / 5 mm body / 8.6 mm height; no enclosure interference'
refs=cq.Assembly(name='NIFLS_with_REFERENCE_envelopes')
refs.add(assembly,name='mechanical')
refs.add(cq.Compound.makeCompound(led_envelopes),name='REFERENCE_99_LED_envelopes',color=cq.Color(.35,.45,.8))
refs.add(cq.Compound.makeCompound(holder_envelopes),name='REFERENCE_two_4AA_holders',color=cq.Color(.65,.65,.65))
refs.save(str(OUT/'NIFLS_assembly_with_reference_envelopes.step'))

# Shallow footprint coupon checks the measured holder's body width and length.
fit=cuts(box(36,68,5),[box(32,64,5.2,z=-.1)])
assert fit.isValid() and len(fit.Solids())==1
cq.exporters.export(fit,str(OUT/'holder_footprint_fit_coupon.step'))
cq.exporters.export(fit,str(OUT/'holder_footprint_fit_coupon.stl'))

with (OUT/'LED_and_resistor_coordinates.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['type','ID','string_ID','x_mm','y_mm','hole_spacing_mm','hole_diameter_mm'])
    for c in range(11):
        for r in range(9):
            w.writerow(['LED',f'D{c*9+r+1}',f'S{c*3+r//3+1}',c*13.5-67.5,r*16.5-66,2.54,1.1])
        for g in range(3):
            w.writerow(['resistor',f'R{c*3+g+1}',f'S{c*3+g+1}',c*13.5-67.5,g*49.5-72.5,10,1.1])
(OUT/'validation_report.json').write_text(json.dumps(report,indent=2))
print('PASS: four solids, STEP round trips, mating checks, door motion and reference envelopes',flush=True)

# Render directly from the CAD tessellation, not an illustrative/generated image.
def render(items,path,camera,focus,parallel_scale):
    import vtk
    renderer=vtk.vtkRenderer();renderer.SetBackground(.95,.96,.97)
    for shape,color in items:
        vertices,triangles=shape.tessellate(.15,.18)
        points=vtk.vtkPoints()
        for v in vertices: points.InsertNextPoint(v.x,v.y,v.z)
        faces=vtk.vtkCellArray()
        for tri in triangles:
            faces.InsertNextCell(3)
            for n in tri: faces.InsertCellPoint(n)
        mesh=vtk.vtkPolyData();mesh.SetPoints(points);mesh.SetPolys(faces)
        normals=vtk.vtkPolyDataNormals();normals.SetInputData(mesh);normals.SetFeatureAngle(35)
        mapper=vtk.vtkPolyDataMapper();mapper.SetInputConnection(normals.GetOutputPort())
        actor=vtk.vtkActor();actor.SetMapper(mapper);actor.GetProperty().SetColor(*color[:3])
        actor.GetProperty().SetAmbient(.3);actor.GetProperty().SetDiffuse(.7)
        if len(color)>3: actor.GetProperty().SetOpacity(color[3])
        renderer.AddActor(actor)
    win=vtk.vtkRenderWindow();win.SetOffScreenRendering(1);win.AddRenderer(renderer);win.SetSize(1400,1200)
    cam=renderer.GetActiveCamera();cam.SetPosition(*camera);cam.SetFocalPoint(*focus);cam.SetViewUp(0,0,1);cam.ParallelProjectionOn();cam.SetParallelScale(parallel_scale)
    renderer.ResetCameraClippingRange();win.Render()
    shot=vtk.vtkWindowToImageFilter();shot.SetInput(win);shot.Update()
    writer=vtk.vtkPNGWriter();writer.SetFileName(str(path));writer.SetInputConnection(shot.GetOutputPort());writer.Write();win.Finalize()

render([(base,colors[2]),(board.translate((0,0,45)),colors[1]),
        (frame.translate((0,0,85)),colors[0]),(glass.translate((0,0,110)),(.65,.83,.88,.65)),
        (door.translate((0,-65,-25)),colors[3])],OUT/'NIFLS_exploded.png',(260,-330,245),(0,-5,65),175)
render([(base,colors[2])],OUT/'NIFLS_battery_access.png',(190,-270,-340),(0,0,20),120)
print('Renders complete',flush=True)

render([(base,colors[2]),(cq.Compound.makeCompound(holder_envelopes),(.7,.58,.3))],OUT/'NIFLS_holders_installed.png',(190,-270,-340),(0,0,25),120)
