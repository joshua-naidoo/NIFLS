#!/usr/bin/env python3
"""
Experiment 2 -- contrast and edge sharpness of the fracture gap.

Method (Section 5.2 of the report):
  * One raw 940 nm frame (20 ms, lights off) is analysed inside a rectangular box
    (the slit for the gap frame, the intact-bone region for the control frame).
  * Profiles run along the finger axis (vertical in the frame), i.e. across the lighter
    line, one per column of the box (all columns for the gap slit, 22 for the control),
    each lightly smoothed (Gaussian, sigma = 3 px).
  * The Michelson contrast of each profile, C_M = (I_max - I_min)/(I_max + I_min), uses
    I_max = the peak of the profile and I_min = the surrounding (flank) level.   [Eq. 3.1]
  * The maximum gradient is the largest absolute value of dI/dx along each profile
    (grey levels per pixel).
  * The values quoted are the mean over the positions; the +/- is the sample standard
    deviation (n - 1) over the positions.                                         [Eq. 3.3]
    All positions come from a single frame, so this is not a repeat measurement.
  * Profiles are aligned on their peaks and normalised to the flank level for the figure.

NOTE: the smoothing width and the flank window are analysis settings (--smooth,
--half-window, --flank-px). The maximum gradient depends strongly on the smoothing, so
state the value used. The box limits must be the INSIDE of the box: use frames
without the orange box drawn on them, or leave out the ~7 px outline.

Usage (the box coordinates refer to a frame 2576 px wide; frames of any size are
resized to that width first, so the full 4608 x 2592 camera frames can be used directly)
  python exp2_gap_contrast.py frame_gap.jpg --box 1017 1264 527 654 --out results/gap
  python exp2_gap_contrast.py frame_control.jpg --box 1070 1332 440 1032 --positions 22 --out results/control
    --box   pixel limits of the analysed region: X0 X1 Y0 Y1 (X1, Y1 exclusive)
    --axis  y (default): vertical profiles, one per column of the box;
            x: horizontal profiles, one per row
"""
import argparse
import json
import os

import numpy as np


def smooth(p, sigma):
    if sigma <= 0:
        return p
    r = int(np.ceil(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()
    return np.convolve(np.pad(p, r, mode="edge"), k, mode="valid")


def fwhm(p, base):
    """Full width at half maximum of the peak above the flank level."""
    k = int(p.argmax())
    half = base + 0.5 * (p[k] - base)
    lo = k
    while lo > 0 and p[lo] > half:
        lo -= 1
    hi = k
    while hi < len(p) - 1 and p[hi] > half:
        hi += 1
    return float(hi - lo)


def analyse(img, box, axis, positions, sigma, half_window, flank_px):
    x0, x1, y0, y1 = box
    reg = img[y0:y1, x0:x1].astype(np.float64)
    if axis == "y":
        reg = reg.T                       # make profiles run along the last axis
    n = reg.shape[0]
    idx = np.arange(n) if positions is None else np.linspace(0, n - 1, positions).round().astype(int)

    rows = []
    aligned = []
    for i in idx:
        # average +/-2 neighbouring lines so one noisy line does not dominate
        lo, hi = max(0, i - 2), min(n, i + 3)
        p = smooth(reg[lo:hi].mean(axis=0), sigma)
        k = int(p.argmax())
        a, b = max(0, k - half_window), min(len(p), k + half_window + 1)
        seg = p[a:b]
        f = min(flank_px, len(seg) // 2)
        flank = np.r_[seg[:f], seg[-f:]].mean()           # I_min: surrounding level
        c = (p[k] - flank) / (p[k] + flank)               # Eq. 3.1
        g = np.abs(np.gradient(p)).max()                  # max |dI/dx|, grey/px
        rows.append((p[k], flank, c, g, fwhm(p, flank)))
        # peak-aligned, flank-normalised profile for the figure
        pad = np.full(2 * half_window + 1, np.nan)
        off = half_window - (k - a)
        pad[off:off + len(seg)] = seg / flank
        aligned.append(pad)
    r = np.array(rows)
    return r, np.array(aligned)


def prepare(img, width):
    """Resize to a common width (area interpolation) so every frame uses the same pixel scale."""
    import cv2
    if width and img.shape[1] != width:
        h = int(round(img.shape[0] * width / img.shape[1]))
        img = cv2.resize(img, (width, h), interpolation=cv2.INTER_AREA)
    return img


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image")
    ap.add_argument("--box", type=int, nargs=4, required=True, metavar=("X0", "X1", "Y0", "Y1"))
    ap.add_argument("--axis", choices=["x", "y"], default="y")
    ap.add_argument("--positions", type=int, default=None, help="number of positions (default: all)")
    ap.add_argument("--smooth", type=float, default=3.0, help="Gaussian sigma (px) applied to each profile")
    ap.add_argument("--half-window", type=int, default=50, help="profile half-width about the peak (px)")
    ap.add_argument("--flank-px", type=int, default=15, help="px at each end used for the flank level")
    ap.add_argument("--resize-width", type=int, default=2576,
                    help="frames are resized to this width (height keeps the aspect ratio) before the "
                         "analysis; the box coordinates refer to this width. Default 2576, the size the "
                         "boxes below were drawn on. Use 0 to analyse the full-resolution frame "
                         "(then give the box in full-resolution pixels and scale --smooth, "
                         "--half-window and --flank-px accordingly).")
    ap.add_argument("--control", help="control frame; with --control-box also draws the comparison figure")
    ap.add_argument("--control-box", type=int, nargs=4, metavar=("X0", "X1", "Y0", "Y1"))
    ap.add_argument("--control-positions", type=int, default=22)
    ap.add_argument("--out", default="results/exp2")
    a = ap.parse_args()

    import cv2
    img = cv2.imread(a.image, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(a.image)

    img = prepare(img, a.resize_width)
    r, aligned = analyse(img, a.box, a.axis, a.positions, a.smooth, a.half_window, a.flank_px)
    out = {
        "image": os.path.basename(a.image),
        "positions": int(len(r)),
        "peak_grey_mean": float(r[:, 0].mean()),
        "flank_grey_mean": float(r[:, 1].mean()),
        "michelson_mean": float(r[:, 2].mean()),
        "michelson_sd": float(r[:, 2].std(ddof=1)),
        "max_gradient_mean_grey_per_px": float(r[:, 3].mean()),
        "max_gradient_sd": float(r[:, 3].std(ddof=1)),
        "fwhm_px_mean": float(r[:, 4].mean()),
    }
    print(json.dumps(out, indent=2))

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out + "_summary.json", "w") as f:
        json.dump(out, f, indent=2)
    np.savetxt(a.out + "_per_position.csv", r, delimiter=",",
               header="peak_grey,flank_grey,michelson,max_abs_gradient,fwhm_px", comments="")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    x = np.arange(-a.half_window, a.half_window + 1)
    fig, ax = plt.subplots(figsize=(6.4, 4))
    with np.errstate(all="ignore"):
        mean_prof = np.nanmean(aligned, axis=0)
    ax.plot(x, mean_prof, color="black")
    ax.axhline(1.0, ls="--", lw=0.8, color="grey")
    ax.set_xlabel("Position along finger axis, relative to profile peak (px)")
    ax.set_ylabel("Relative intensity (profile / flank level)")
    fig.tight_layout()
    fig.savefig(a.out + "_profile.png", dpi=200)
    if a.control:
        ctl = cv2.imread(a.control, cv2.IMREAD_GRAYSCALE)
        if ctl is None or not a.control_box:
            raise SystemExit("--control needs a readable image and --control-box")
        ctl = prepare(ctl, a.resize_width)
        rc, ac = analyse(ctl, a.control_box, a.axis, a.control_positions, a.smooth, a.half_window, a.flank_px)
        cout = {
            "positions": int(len(rc)),
            "peak_grey_mean": float(rc[:, 0].mean()),
            "flank_grey_mean": float(rc[:, 1].mean()),
            "michelson_mean": float(rc[:, 2].mean()),
            "michelson_sd": float(rc[:, 2].std(ddof=1)),
            "max_gradient_mean_grey_per_px": float(rc[:, 3].mean()),
            "max_gradient_sd": float(rc[:, 3].std(ddof=1)),
            "fwhm_px_mean": float(rc[:, 4].mean()),
        }
        print("control:", json.dumps(cout, indent=2))
        with open(a.out + "_control_summary.json", "w") as f:
            json.dump(cout, f, indent=2)
        with np.errstate(all="ignore"):
            gmean, cmean = np.nanmean(aligned, axis=0), np.nanmean(ac, axis=0)
        fig, ax = plt.subplots(figsize=(6.4, 4))
        ax.plot(x, gmean, color="#c0392b", lw=2, label="Fracture gap (index finger)")
        ax.plot(x, cmean, color="#2471a3", lw=2, label="Intact bone (control, middle finger)")
        ax.axhline(1.0, ls="--", lw=0.8, color="grey")
        ax.set_xlabel("Position along finger axis, relative to profile peak (px)")
        ax.set_ylabel("Relative intensity (profile / flank level)")
        ax.legend(frameon=False, fontsize=8)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        fig.tight_layout()
        fig.savefig(a.out + "_comparison.png", dpi=200)
        print("peak of the mean profiles (relative to flank): gap %.2f, control %.2f"
              % (np.nanmax(gmean), np.nanmax(cmean)))


if __name__ == "__main__":
    main()