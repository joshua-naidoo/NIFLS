# NIFLS: Non-Invasive Fracture Light Scanner (`nifls_interface`)

A low-cost, non-ionising optical transillumination system for bone fracture triage, built as a final-year project (EEE4022S) at the University of Cape Town.

A 940 nm LED baseplate lights a hand from below, a Raspberry Pi camera head images the transmitted light, and a laptop runs a U-Net to segment the fracture and show it on a live dashboard.

> **Research prototype.** All testing used a silicone–TiO₂ hand phantom with a black 3D-printed bone analogue. No patients or human tissue were involved. The results show technical feasibility only, not clinical sensitivity or specificity. This is not a medical device.

**Report:** *Development of a Low-Cost Optical Transillumination System for Bone Fracture Triage (NIFLS)*, Joshua Naidoo, supervised by Dr Simon Winberg, Dept. of Electrical Engineering, University of Cape Town.

---

## How it works

```
[8×AA pack] → [99 × 940 nm LED baseplate] → [hand / phantom] → [NoIR camera + Raspberry Pi 4B]
                                                                         │  JPEG 600×600, imagezmq / TCP :5555
                                                                         ▼
 [Dashboard] ← [Threshold + stability filter] ← [U-Net inference] ← [CLAHE, 256×256] ← [Receiver (laptop)]
```

Three separate units:

| Unit | Contents |
|---|---|
| **Illuminator baseplate** | 99 Kingbright L-53F3C 940 nm LEDs in an 11×9 grid (33 parallel strings of 3 LEDs + 470 Ω), 8×AA pack (12 V), rocker switch, 150×150 mm active area behind a diffuser |
| **Handheld camera head** | Raspberry Pi 4B, Camera Module 3 NoIR (Sony IMX708), 3D-printed pistol-grip housing, about 150 mm working distance, about 51×51 mm field of view |
| **Host laptop** | Receiver thread, CLAHE and resize, U-Net (ResNet-34 encoder, PyTorch), detection threshold and stability filter, dashboard |

Key design choices:

- **Edge/host split.** The Pi only captures and streams. Only the newest frame is ever sent, so a slow host cannot build a queue of stale frames.
- **Fixed exposure, gain and focus** (20 ms, gain 1.0), so brightness changes cannot be mistaken for fracture contrast.
- **Detection logic.** The probability map is thresholded at 0.85, regions of 300 px or fewer are discarded, and a fracture is declared only after 5 stable frames (the counter rises by 1 for a valid frame and falls by 2 otherwise).

## Measured results (phantom only)

| Measurement | Result |
|---|---|
| Effective attenuation of phantom at 940 nm | 1.1 ± 0.2 cm⁻¹ over 27–47 mm |
| Dry 1.5 mm gap, Michelson contrast | 0.09 ± 0.03 against 0.04 ± 0.02 for an intact control (one frame each) |
| End-to-end latency, camera to display (531 frames) | 401.3 ± 71.5 ms mean; 530 of 531 frames below 1.0 s |
| U-Net Dice, 5-fold cross-validation (53 fracture frames) | 0.735 ± 0.201 at threshold 0.5 (0.728 at 0.85); target 0.70 |
| Fractures detected / false detections | 51 of 53 / 7 of 56 fracture-free frames at 0.85 |
| Mass (scanner + baseplate) | 1.47 kg |
| Scanner cost | R3 776.93 |

These come from one phantom, one session and a small dataset; see the Limitations chapter of the report before relying on any figure.

## Repository layout

```
NIFLS/
├── Hardware/
│   ├── Baseplate/                 LED baseplate (99 × 940 nm LEDs, 33 strings of 3 LEDs + 470 Ω)
│   ├── Phantom/                   Tissue-mimicking silicone–TiO₂ hand phantom and 3D-printed bone core
│   └── Scanner/                   Handheld camera head (Raspberry Pi 4B + NoIR Camera Module 3)
├── Software/
│   ├── requirements.txt           Python packages for the host laptop
│   ├── experiment 1/              Attenuation experiment
│   │   ├── results/                   Output: exp1_fit.csv and exp1_attenuation_fit.png
│   │   ├── exp1_attenuation.py        Measures the ROI grey levels, fits mu_eff, draws the fit figure
│   │   ├── frames.csv                 Region, thickness and image file for each frame
│   │   ├── exp1_index.jpg             Index finger (32 mm)
│   │   ├── exp1_middle_finger.jpg     Middle finger (36 mm)
│   │   ├── exp1_middle_fingertip.jpg  Middle fingertip (32 mm)
│   │   ├── exp1_palm.jpg              Palm (47 mm)
│   │   ├── exp1_pinky.jpg             Pinky, first frame (27 mm)
│   │   ├── exp1_pinky_frame1.jpg      Pinky, second frame (27 mm)
│   │   ├── exp1_thumb.jpg             Thumb (32 mm)
│   │   ├── exp1_upper_palm_a.jpg      Upper palm (a) (42 mm)
│   │   └── exp1_upper_palm_b.jpg      Upper palm (b) (40 mm)
│   ├── experiment 2/              Fracture-gap contrast experiment
│   │   ├── results/                   Output: summary .json files, per-position .csv, profile figures
│   │   ├── control.jpg                Frame of intact bone (middle finger)
│   │   ├── exp2_gap_contrast.py       Michelson contrast and maximum gradient across the gap
│   │   └── gap.jpg                    Frame with the dry 1.5 mm gap (index finger)
│   ├── experiment 3/              Latency experiment
│   │   ├── pi_streamer_timed.py       Pi streamer with per-stage timing and clock calibration
│   │   ├── host_dashboard_timed.py    Laptop dashboard with per-stage timing log
│   │   ├── host_latency_log.csv       Raw per-frame timings from the 531-frame run
│   │   ├── analyze_latency.py         Latency table and breakdown figure
│   │   ├── exp3_latency_breakdown.png Figure used in the report
│   │   └── exp3_table_rows.tex        Table rows used in the report
│   └── experiment 4/              Segmentation experiment and live dashboard
│       ├── pi_streamer.py             Raspberry Pi camera streamer (edge node)
│       ├── host_dashboard.py          Laptop receiver, U-Net inference and dashboard
│       ├── train_unet.py              U-Net training and 5-fold cross-validated evaluation
│       ├── annotations_v3_std.json    Fracture polygon labels (COCO format) for the training frames
│       ├── nifls_unet_best.vbb        U-Net weights loaded by the dashboard
│       ├── nifls_unet_v3.pth          U-Net weights, final model trained on all labelled frames
│       ├── nifls_captures/            Captured frames
│       └── training_images/           Images used to train the U-Net
└── README.md
```

## Requirements

**Raspberry Pi 4B** (Raspberry Pi OS, libcamera stack): Python 3.11, `picamera2`, OpenCV, `imagezmq`, NumPy.

**Host laptop** (Windows or Linux): Python 3, PyTorch (CUDA GPU optional, CPU works), `segmentation_models_pytorch`, OpenCV, Pillow, NumPy, `imagezmq`; `pandas` and `matplotlib` for the analysis scripts; `scikit-learn` for training.

```bash
pip install -r Software/requirements.txt
```

On the Pi, install `picamera2` through the system package manager (`sudo apt install python3-picamera2`) rather than pip, and install `imagezmq` with pip.

## Running the live system

1. Put the phantom (or hand) on the LED baseplate and switch the baseplate on. Use dim room lights so only the 940 nm LEDs illuminate the scene.
2. On the laptop, start the dashboard first: `python "Software/experiment 4/host_dashboard.py"`. It listens on port 5555 and loads the U-Net weights (`nifls_unet_best.vbb`).
3. On the Pi, start the streaming script: `python3 "Software/experiment 4/pi_streamer.py"`. It connects to the laptop by network name, so no fixed IP address is needed. Edit `SERVER` at the top of the script to your laptop's network name.
4. Hold the camera head above the baseplate. Frames stream at up to 30 FPS and a confirmed detection is outlined with a confidence value.

Both machines must be on the same local network. The send is a blocking request/reply, so the Pi stalls if the laptop disappears mid-session (a send timeout with reconnection is listed as future work).

## Reproducing the experiments

**Experiment 1 (attenuation).** From `Software/experiment 1/`, run:

```bash
python exp1_attenuation.py frames.csv --images-dir . --out results
```

The script resizes each frame to 2576 px wide, takes the mean grey level over a 150 × 150 px region centred on the brightest point of the Gaussian-smoothed frame (σ = 25 px), averages the two pinky frames, raises the grey levels to the power 2.2, and fits −ln(I/I_pinky) against thickness. It prints the table and μ_eff ± the standard error of the slope (about 1.1 ± 0.2 cm⁻¹, R² about 0.88), and writes `exp1_fit.csv` and `exp1_attenuation_fit.png` to `results/`. The first region in `frames.csv` is the reference (the pinky).

**Experiment 2 (fracture contrast).** From `Software/experiment 2/`, run:

```bash
python exp2_gap_contrast.py gap.jpg --box 1017 1264 527 654 \
    --control control.jpg --control-box 1070 1332 440 1032 --out results/exp2
```

Frames of any size are resized to 2576 px wide first, and the box coordinates refer to that width. The script takes a lightly smoothed intensity profile (σ = 3 px) along the finger axis at every column of the box, aligns them on their peaks, and reports the mean and sample standard deviation of the Michelson contrast over the profiles, the mean maximum gradient, and the peak-aligned profile figure (`exp2_comparison.png`). It should give a gap contrast of about 0.09 ± 0.03 and a control contrast of about 0.04 ± 0.02. The box coordinates must lie inside the region analysed, so use frames without any drawn marker.

**Experiment 3 (latency).** Run the timed dashboard (`Software/experiment 3/host_dashboard_timed.py`) on the laptop and the timed streamer (`Software/experiment 3/pi_streamer_timed.py`) on the Pi, then run `analyze_latency.py` on the merged Pi and host logs. The per-frame laptop log from the reported run is `host_latency_log.csv`.

**Experiment 4 (segmentation).** The trained weights, the captured frames, the training images (`training_images/`), the labels (`annotations_v3_std.json`) and the training script (`train_unet.py`) are in `Software/experiment 4/`. From the repository root, run:

```bash
python "Software/experiment 4/train_unet.py" \
    --images "Software/experiment 4/training_images" \
    --annotations "Software/experiment 4/annotations_v3_std.json" \
    --out results
```

The script runs 5-fold stratified cross-validation (every frame is scored once, out-of-fold), prints the Dice, IoU, precision, recall and false-detection results at thresholds 0.5 and 0.85, and then trains a final model on all usable frames. It writes `exp4_v3_cv_per_frame.csv`, `exp4_v3_qualitative.png` and `nifls_unet_v3.pth` to `results/`. Of the 56 annotated frames, 53 are used, because three have most of the fracture outside the 1200 px centre crop. A CUDA GPU is recommended, and the ImageNet encoder weights are downloaded on first use. On Windows, set `NUM_WORKERS = 0` in the script.

## Data

Captured frames are in `Software/experiment 4/nifls_captures/` and the images used to train the U-Net are in `Software/experiment 4/training_images/`. The fracture annotations (polygon labels in COCO format, standardised) are in `Software/experiment 4/annotations_v3_std.json`. Frames with no annotation are used as empty-mask negatives.

## Limitations

- Phantom only: the TiO₂ silicone phantom is more transparent than tissue and cannot reproduce tissue's forward-directed scattering.
- The fracture gap appeared as a lighter line, not the total-internal-reflection shadow the literature suggests; the fracture contrast result rests on one frame, one gap width and one control region.
- The segmentation score comes from a small dataset (53 fracture frames) from one session, and the cross-validation folds were not grouped by session.
- The 1.0 s latency requirement was met on average, not for every frame (one of 531 frames measured 1000.6 ms).

## Acknowledgements

Supervisor: Dr Simon Winberg, University of Cape Town.

## Contact

Joshua Naidoo, ndxjos012@myuct.ac.za