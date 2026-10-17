"""Commemorative inscription, 0.5 mm recessed on the USB-port side."""
import cadquery as cq

def update(parts):
    shape=parts['01_pi_base']
    for text,z in [('FINAL YEAR PROJECT • UCT • 2026',27.1),('THE FIRST OF MANY',23.9)]:
        plane=cq.Plane(origin=(-63,-46.5,z),xDir=(1,0,0),normal=(0,-1,0))
        for letter in cq.Workplane(plane).text(text,3.2,.5,font='Arial',kind='bold',halign='center',valign='center',combine=False).vals():
            bb=letter.BoundingBox()
            assert bb.zmin>22.3 and bb.zmax<29.2,(text,bb.zmin,bb.zmax)
            shape=shape.cut(letter)
    parts['01_pi_base']=shape.clean()
    return parts
