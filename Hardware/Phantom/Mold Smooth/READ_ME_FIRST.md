# Fully smoothed hand mold — 10 mm silicone — Prusa MINI

Use **01_mold_lower_MINI_DIAGONAL.3mf** and **02_mold_upper_MINI_DIAGONAL.3mf**. Matching STL files are included. This version extends the smooth palm and wrist treatment across all fingers, the thumb and knuckles.

## Shape and size

- Separate rounded envelopes around each digit blend into the rounded palm and wrist. Grooves from the underlying bone joints are filled and softened. The cropped wrist connects continuously to the palm and has a rounded end, without a forearm extension.
- Designed for the latest uploaded `human_bone.3mf`, with saved bone dimensions **117.597 × 180.000 × 33.265 mm**. Bone geometry and scale are preserved.
- Designed for at least **10 mm** of silicone between the bone and outer surface. The smallest measured CAD clearance is **10.134 mm**. Filled hollows around joints, the palm and wrist are thicker to achieve the smooth shape. Narrow finger spaces merge where their surrounding layers overlap.
- Each mold half is already diagonal at **41.22°**, centered on a **180 × 180 mm** plate. Each footprint is **178.167 × 178.190 mm**. Lower height: **40.31 mm**; upper height: **45.41 mm**.
- Minimum peripheral mold wall: **2 mm**. Flat back: **5 mm**. The fit on the MINI is tight, so the final sliced toolpaths must be checked.

## Print

1. Select your Prusa MINI profile and import **one mold half at a time**. Keep **100% scale** and the supplied orientation. Each flat back rests on the plate and its cavity faces upwards.
2. Set **brim = 0** and **skirt loops = 0**. Check that the sliced toolpaths stay inside the build plate. Rescaling would change the bone fit and silicone thickness.
3. Starting settings for a 0.4 mm nozzle: **0.20 mm layers, 5 perimeters, 25% infill and 10 top/bottom solid layers**. Use the appropriate printer preset for your filament. Review cavity and locating-seat layers before printing.
4. The 3MF files contain geometry and placement, without printer or filament presets. Bone and outer-hand reference STL files are for comparison; they are not additional mold pieces.

## Assemble and cast

1. Clean the cavities and seating surfaces. Dry-fit the printed bone on the seven locating seats, then close the upper half. **2 tapered keys** align the halves. The printed bone must match the source dimensions above.
2. Clamp evenly, or use **four M3 × 75 mm bolts, washers and nuts** through the 3.4 mm holes. Tighten gently because the peripheral walls are thin.
3. Use a release treatment compatible with your mold and silicone. Check the mold for leaks and, if necessary, seal its cavities with a compatible thin coating before casting.
4. Cast with the **palm/lower half down** and the upper half's funnel and vents facing upwards. Pour through the **14 mm wrist funnel** (7 mm bore). Keep the **11 vents**, each 1.8 mm diameter, open while filling.
5. Estimated silicone volume, including channels: **538 mL**. Prepare approximately **610 mL** of mixed silicone to allow for pouring losses. Follow the manufacturer's mixing, working-time and curing instructions. Volume is not a mixing ratio or a mass measurement.
6. After full cure, remove clamps or bolts and ease the halves apart. The printed bone remains embedded. Trim the inlet and vent stems.
7. The opposed locating seats leave **14 small contact holes** that reach the bone. Fill these with compatible silicone after demolding to complete coverage. The 10 mm outer-surface clearance excludes these deliberate support openings until patched.

## Checks and previews

- `hand_preview.png`: actual revised outer-hand geometry.
- `MINI_plate_preview.png` and `mold_preview.png`: actual mold geometry on separate MINI plates.
- `clearance_qa.json`: 768,522 nearest-surface measurements, none below 10 mm. All sampled bone vertices and triangle centers are inside the envelope.
- `print_file_qa.json`: independent checks of exported STL and 3MF files, including closed meshes and build-plate bounds.
- `design_checks.json`: dimensions, locating seats, channels and fit checks. Computed bone-to-mold interference and bone outside the cavity are both zero.
- `source_dimensions_and_transform.json`: source-file hash, dimensions and positioning transform.
- `smoothing_details.json`: description of the full-hand smoothing construction.

This is a CAD-checked prototype; physical printing and casting have not been tested. The outer form is an engineering approximation derived from the skeleton.
