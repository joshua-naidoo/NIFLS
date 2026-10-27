#!/usr/bin/env python3
"""
Experiment 1 -- effective attenuation of 940 nm light through the phantom.

Method (Section 3 / Section 5.1 of the report):
  * Frames are resized to 2576 px wide. The mean grey level I is taken over a 150 x 150 px
    region centred on the brightest transmitted area of each frame (the maximum of the
    Gaussian-smoothed frame, sigma = 25 px).
  * Grey levels are gamma-encoded, so they are linearised: I_lin = (I / 255) ** 2.2.
  * Intensities are expressed relative to the thinnest region (the pinky), because no
    empty-beam reference could be obtained.
  * mu_eff is the slope of  -ln(I / I_pinky)  against thickness d (cm), fitted by
    ordinary least squares; the quoted uncertainty is the standard error of the slope.

The script does the whole analysis: it reads the frames, measures the ROI mean grey
level of every frame, averages frames of the same region, linearises, fits, and writes
the table, the fit and the figure.

Usage
  python exp1_attenuation.py frames.csv --images-dir path/to/frames --out results
      frames.csv columns:  region,d_mm,image
        * one row per frame; frames of the same region (e.g. the two pinky frames)
          are given the same region name and their ROI means are averaged
        * the FIRST region in the file is the reference (the pinky, 27 mm)
        * regions that contain the embedded bone must not be listed
      --roi N          ROI side in px (default 150, on a frame 2576 px wide)
      --width W        resize every frame to W px wide first (default 2576; 0 = no resize)
      --centre-sigma S smoothing (px) used to find the brightest area (default 25)
  python exp1_attenuation.py --from-table
      re-runs the fit from the ROI mean grey levels printed in Table 5.2 of the report
      (no images needed).
"""
import argparse
import csv
import os

import numpy as np

GAMMA = 2.2
ROI = 150            # px, square region (on a frame WIDTH px wide)
WIDTH = 2576         # frames are resized to this width before measuring
CENTRE_SIGMA = 25    # px, smoothing used to locate the brightest area

# Table 5.2 of the report: region, thickness d (mm), ROI mean grey level
TABLE_5_2 = [
    ("Pinky",            27, 203),
    ("Index finger",     32, 180),
    ("Thumb",            32, 178),
    ("Middle fingertip", 32, 201),
    ("Middle finger",    36, 123),
    ("Upper palm (b)",   40, 137),
    ("Upper palm (a)",   42, 115),
    ("Palm",             47,  71),
]


def roi_mean_grey(path, roi=ROI, width=WIDTH, sigma=CENTRE_SIGMA):
    """Mean grey level over a roi x roi window centred on the brightest transmitted area.

    The frame is first resized to `width` px wide (2576 by default) so that the ROI
    always covers the same area. The centre is the brightest point of the frame after
    Gaussian smoothing (sigma px), so that single bright pixels do not move the window.
    """
    import cv2
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(path)
    if width and img.shape[1] != width:
        h = int(round(img.shape[0] * width / img.shape[1]))
        img = cv2.resize(img, (width, h), interpolation=cv2.INTER_AREA)
    img = img.astype(np.float32)
    _, _, _, (cx, cy) = cv2.minMaxLoc(cv2.GaussianBlur(img, (0, 0), sigma))
    h, w = img.shape
    x0 = int(np.clip(cx - roi // 2, 0, w - roi))
    y0 = int(np.clip(cy - roi // 2, 0, h - roi))
    return float(img[y0:y0 + roi, x0:x0 + roi].mean())


def fit_mu_eff(d_mm, grey, ref_index=0):
    """OLS fit of -ln(I/I_ref) against d (cm). Returns slope, standard error, R^2."""
    d_cm = np.asarray(d_mm, float) / 10.0
    lin = (np.asarray(grey, float) / 255.0) ** GAMMA          # linearise
    y = -np.log(lin / lin[ref_index])                         # relative attenuation
    n = len(d_cm)
    slope, intercept = np.polyfit(d_cm, y, 1)
    resid = y - (slope * d_cm + intercept)
    ss_res = float(np.sum(resid ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot
    se = np.sqrt(ss_res / (n - 2) / np.sum((d_cm - d_cm.mean()) ** 2))
    return slope, se, r2, d_cm, y, intercept


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", nargs="?", help="CSV with columns region,d_mm,image")
    ap.add_argument("--images-dir", default=".")
    ap.add_argument("--roi", type=int, default=ROI)
    ap.add_argument("--width", type=int, default=WIDTH, help="resize frames to this width first (0 = no resize)")
    ap.add_argument("--centre-sigma", type=float, default=CENTRE_SIGMA)
    ap.add_argument("--from-table", action="store_true", help="use the grey levels of Table 5.2")
    ap.add_argument("--out", default="results")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    ref_frames = []
    if a.from_table or not a.csv:
        rows = TABLE_5_2
    else:
        per_region = {}                     # region -> [d_mm, [frame means]]
        with open(a.csv, newline="") as f:
            for r in csv.DictReader(f):
                g = roi_mean_grey(os.path.join(a.images_dir, r["image"]), a.roi, a.width, a.centre_sigma)
                print(f"  {r['region']:20s} {r['image']:28s} ROI mean grey = {g:6.1f}")
                per_region.setdefault(r["region"], [float(r["d_mm"]), []])[1].append(g)
        rows = [(k, v[0], float(np.mean(v[1]))) for k, v in per_region.items()]
        ref_frames = next(iter(per_region.values()))[1]      # frames of the reference (pinky)
        print()

    names, d, grey = zip(*rows)
    slope, se, r2, d_cm, y, icpt = fit_mu_eff(d, grey)

    rel = (np.array(grey, float) / 255) ** GAMMA
    rel = rel / rel[0]
    print(f"{'Region':20s} {'d (mm)':>7s} {'ROI grey':>9s} {'I/I_ref (linear)':>17s}")
    for n_, dd, gg, rr in zip(names, d, grey, rel):
        print(f"{n_:20s} {dd:7.0f} {gg:9.1f} {rr:17.2f}")
    print(f"\nmu_eff = {slope:.2f} +/- {se:.2f} cm^-1   R^2 = {r2:.2f}   (n = {len(d)} regions)")

    with open(os.path.join(a.out, "exp1_fit.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["region", "d_mm", "roi_grey", "rel_intensity_linear", "minus_ln_rel"])
        for row in zip(names, d, grey, rel, y):
            w.writerow(row)

    make_figure(os.path.join(a.out, "exp1_attenuation_fit.png"),
                d_cm, y, slope, icpt, r2, ref_frames)


def make_figure(path, d_cm, y, slope, icpt, r2, ref_frames):
    """Fit figure: -ln(I/I_pinky) against thickness, single frames in blue, the pinky
    (the reference, so y = 0) in red with a bar showing the spread of its frames."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    BLUE, RED, GREY = "#2471a3", "#c0392b", "#555555"
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.set_axisbelow(True)
    ax.grid(True, color="#e3e3e3", lw=0.8)
    xs = np.array([2.5, 4.9])
    ax.plot(xs, slope * xs + icpt, "-", color=GREY, lw=1.6)
    ax.scatter(d_cm[1:], y[1:], s=22, color=BLUE, zorder=3)

    err = None
    if len(ref_frames) >= 2:
        lin = (np.asarray(ref_frames, float) / 255.0) ** GAMMA
        dev = -np.log(lin / lin.mean())                     # each pinky frame against their mean
        err = (dev.max() - dev.min()) / 2.0                 # half the spread of the frames
    ax.errorbar([d_cm[0]], [y[0]], yerr=err, fmt="o", color=RED, ecolor=RED,
                capsize=3, ms=5, lw=1.2, zorder=4)

    handles = [Line2D([0], [0], color=GREY, lw=1.6,
                      label=f"Fit: $\\mu_{{\\mathrm{{eff}}}}$ = {slope:.2f} cm$^{{-1}}$, $R^2$ = {r2:.2f}"),
               Line2D([0], [0], marker="o", color="w", markerfacecolor=BLUE, ms=5, label="Single frame")]
    if err is not None:
        handles.append(Line2D([0], [0], marker="o", color=RED, ms=5, lw=1.2, label="Pinky (mean of 2 frames)"))
    ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=7.5)
    ax.set_xlabel("Phantom thickness $d$ (cm)", fontsize=8.5)
    ax.set_ylabel(r"$-\ln(I/I_{\mathrm{pinky}})$", fontsize=8.5)
    ax.tick_params(labelsize=8)
    ax.set_xlim(2.4, 5.0)
    ax.set_yticks([-0.5, 0.0, 0.5, 1.0, 1.5, 2.0])
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=200)


if __name__ == "__main__":
    main()