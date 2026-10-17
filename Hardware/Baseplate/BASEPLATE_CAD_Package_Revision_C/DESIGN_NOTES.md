# NIFLS — revision C: two purchased 4-AA holders

This revision replaces the integrated individual-cell holder with two locating bays for the user's **C0984 / VCZ0984 four-AA holders**, measured at **63 × 31 × 31 mm each**. It retains the 6 mm glass and revision B switch opening. Dimensions are millimetres. This is a mechanical prototype, not a physically tested assembly.

## What to print

- `03_base_for_two_4AA_holders.step/.stl`: the revised, taller base.
- `04_sliding_battery_door.step/.stl`: revised door with a smooth support pad for the purchased holders.
- `01_diffuser_frame.step/.stl` and `02_LED_substrate.step/.stl`: same physical shapes as revisions A/B; their assembly elevations have increased by 16 mm. Existing prints of these two parts can be reused.
- `holder_footprint_fit_coupon.step/.stl`: optional small open ring, with a 32 × 64 mm clear opening, to test the measured holder footprint before printing the whole base. This checks footprint only, not connector fit, height or battery removal.
- `switch_fit_coupon_23p4x12p4.step/.stl`: retained from revision B for checking the provisional switch cutout and 3 mm panel retention.

`NIFLS_assembly.step` contains the four printable parts and the glass reference. `NIFLS_assembly_with_reference_envelopes.step` also includes 99 simplified LED envelopes and two rectangular holder envelopes. These are bounding boxes, not manufacturer CAD models. STL parts are individually lowered to Z=0; choose the appropriate print orientation in your slicer. STEP parts retain their assembled coordinates.

## Size and optical stack

The body is **174 × 174 × 75 mm**, or **174 × 177 × 75 mm** including the door's 3 mm front projection. The height increased from 59 to 75 mm to accommodate the 31 mm holders. Bottom Z=0; partition Z=39–42; board Z=49–51; glass Z=69–75. The gap from board top to glass underside remains **18 mm**. The simplified 8.6 mm tall LED bodies leave a 9.4 mm tip-to-glass gap.

The glass is 150 × 150 × 6, in a 152 × 152 × 6 recess. It sits flush without material underneath it. The supporting ledge leaves a **146 × 146 mm clear optical aperture**. Apply a glass-compatible retaining bead in the lateral gap rather than under the glass. Optical uniformity, glass strength and infrared leakage have not been physically tested.

## Holder installation and removal

The two holder axes are arranged with **63 mm along Y, 31 mm along X and 31 mm vertically**. They sit side by side at X=−18 and +18, Y=0. Each locating bay is **32 × 64 mm**, providing 0.5 mm clearance per side around the supplied measurements. Holder bottoms sit at Z=7 on the closed door's support pad; tops reach Z=38, leaving 1 mm to the ceiling.

The rectangular bays have narrower **26 mm wide connector recesses**, extending a further 10 mm at both short ends. This retains end stops for the holder body while making space for connectors. A provisional **24 × 8 × 26 mm** connector envelope at one end of each holder has been checked for interference. The seller does not supply a connector drawing: confirm the actual snap connector, its position, and wire bends before the full print. The recess is not a guaranteed fit for every PP3 lead.

With the device upside down and unpowered, remove the single door-retention screw and slide the door toward negative Y. Lift out each purchased holder through the bottom opening to change its cells. The holders are captured vertically by the door and partition, and laterally by the bays; no glue is required. Their specific cell loading arrangement is not modeled, so remove the holder for battery service. If desired, use thin removable foam to take up measured rattle, without crushing the holder or obstructing the door. Such foam is not modeled.

The locating walls end at Z=9. The door support pad ends at Z=7 and clears both these walls and the front door slot during withdrawal. Provide approximately 170 mm of clear space in front of the enclosure for full door removal. Invert the enclosure before opening so the holders cannot fall out.

There is open wiring space around the bays, wire exits in their end walls, underside raceways, and a Ø5 feedthrough at X=78,Y=0 to the LED chamber. Route and secure insulated leads away from the sliding door. Connector lead slack must allow holders to be lifted out and unplugged for service.

## Electrical arrangement

Use **two four-AA holders in series**, each fitted with four 1.5 V cells, for 12 V nominal. Connect one holder's positive output to the other's negative; the two remaining outputs supply the circuit. Verify actual polarity with a meter rather than relying solely on lead colour. Eight NiMH cells instead provide 9.6 V nominal. The holders replace all 16 separate contacts and the inter-cell wiring used in revisions A/B.

The listing identifies the included PP3 snap connector but does not establish its current rating: https://nde3d.co.za/battery-holders/984-aa-x-4-square-battery-holder-case-with-snap-on-pp3-connector.html

The LED board still has 99 positions, arranged 11 columns × 9 rows at 13.5 × 16.5 pitch. Two Ø1.1 holes per LED are 2.54 apart. Thirty-three resistor positions have exactly 10.00 mm hole spacing, one for each vertical group of three LEDs. The coordinate CSV identifies every string. Four Ø3.4 mounting holes are at (±70,±59). The substrate is a placement part with no copper tracks or electrical connections; use an appropriate FR-4 board or securely supported, insulated hand wiring. Avoid soldering directly against printed plastic.

The required resistor values and ratings remain unresolved pending the LED part number/current target. A 1/4 W footprint does not permit arbitrary LED current: at 12 V and an illustrative 1.35 V per LED, 100 mA would dissipate about 0.795 W in each resistor. Do not connect the full array without suitable current limiting. Use a fuse selected for the final circuit and verify polarity, shorts and operating current. Thermal performance and optical exposure at 940 nm have not been validated.

## Switch and fasteners

The right wall retains the **23.4 × 12.4 mm** opening, centred at Y=45,Z=13, through a 3 mm wall. This is based on the user's reported 23 × 12 mm switch base, with 0.2 mm clearance per side. It remains provisional: the body immediately behind the front rim, clip retention, full terminal/connector envelope and DC rating have not been confirmed. The photo shows three terminals; no wiring assignment is established by these CAD files.

- Frame: four M3 × 16 socket-head screws at (±80,±80), with counterbores.
- LED board: four M3 × 8 low-head/pan-head screws.
- Door: one M3 × 8 button-head screw at (−65,−80).

The base has Ø2.5 pilots for tapping M3 × 0.5. Verify actual fastener dimensions. The 3 mm deep frame locating skirt and optical ledge are unchanged.

## Printing and verification

Print the holder and switch coupons first. Start with the previously discussed 0.4 mm nozzle, 0.2 mm layers, four perimeters and five solid top/bottom layers; 25% gyroid for the enclosure parts and solid infill for the thin placement substrate. These are prototype settings, not validated strength guarantees. Check the chosen filament's dimensional accuracy, temperature performance and 940 nm opacity.

The base needs removable support under its partition and overhangs; access is through the underside. The door's main plate is raised above the bottom of its front flange and also needs appropriate support/orientation. Print the placement board flat; consider printing the frame top face down. Clear support from small holes, tracks and locating bays before assembly.

The generator checks single-solid validity and STEP reimport, mating-part intersections, door travel including a conservative continuous sweep, two holder bounding boxes, provisional connector bounding boxes, straight holder insertion/removal, and LED envelopes. The assembly STEP is reimported separately during packaging. Results are in `validation_report.json`. The images are rendered from the exported geometry. None of these checks replaces a physical fit test, battery-contact/current validation, or thermal and optical testing.

Confirmed: 150 × 150 × 6 glass; user-measured 63 × 31 × 31 holder dimensions. Unconfirmed: whether that measurement fully includes the fitted connector, connector exit direction, precise switch geometry, circuit operating point, and printer/material tolerances. Earlier revisions remain in their original folders; use this revision's base and door together.
