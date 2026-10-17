#!/usr/bin/env python3
"""Experiment 3 analysis: reads host_latency_log.csv written by host_dashboard_timed.py.

Usage:  python analyze_latency.py host_latency_log.csv [warmup_rows=10]
Outputs: console summary, exp3_table_rows.tex, exp3_latency_breakdown.png
"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1] if len(sys.argv) > 1 else "host_latency_log.csv"
warm = int(sys.argv[2]) if len(sys.argv) > 2 else 10

df = pd.read_csv(path).iloc[warm:].reset_index(drop=True)
n = len(df)
if n < 20:
    sys.exit(f"Only {n} rows after warm-up; run longer (>=100 frames).")

STAGES = [
    ("enc_ms",       "JPEG encode (Pi)"),
    ("send_wait_ms", "Wait for send slot (Pi)"),
    ("transfer_ms",  "Network transfer (Wi-Fi/ZeroMQ)"),
    ("decode_ms",    "JPEG decode + resize + rotate"),
    ("infer_wait_ms","Wait for inference thread"),
    ("pre_ms",       "Pre-processing (CLAHE, resize, normalise)"),
    ("model_ms",     "U-Net inference"),
    ("post_ms",      "Post-processing"),
    ("display_ms",   "Render and display"),
]
LIMIT = 1000.0

def stats(x):
    return x.mean(), x.std(ddof=1), x.min(), x.max(), np.percentile(x, 95)

print(f"frames analysed: {n} (first {warm} dropped)")
print(f"clock-offset RTT (uncertainty ~RTT/2): {df.cal_rtt_ms.iloc[0]:.1f} ms -> +/-{df.cal_rtt_ms.iloc[0]/2:.1f} ms")
print(f"{'stage':44s}{'mean':>8s}{'SD':>8s}{'min':>8s}{'max':>8s}{'p95':>8s}")
rows = []
for col, name in STAGES + [("e2e_ms", "End-to-end (frame delivered -> displayed)")]:
    m, s, lo, hi, p95 = stats(df[col])
    print(f"{name:44s}{m:8.1f}{s:8.1f}{lo:8.1f}{hi:8.1f}{p95:8.1f}")
    rows.append(f"{name} & {m:.1f} & {s:.1f} & {lo:.1f} & {hi:.1f} & {p95:.1f} \\\\")
under = (df.e2e_ms < LIMIT).mean() * 100
print(f"frames under {LIMIT:.0f} ms: {under:.1f}%")
print(f"sum of stage means = {sum(df[c].mean() for c,_ in STAGES):.1f} ms (should equal e2e mean)")

with open("exp3_table_rows.tex", "w") as f:
    f.write("\n".join(rows) + "\n")

fig, ax = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1, 1.2]})
left = 0
cmap = plt.get_cmap("tab10")
for i, (col, name) in enumerate(STAGES):
    v = df[col].mean()
    ax[0].barh([0], [v], left=left, color=cmap(i), label=f"{name} ({v:.0f} ms)")
    left += v
ax[0].axvline(LIMIT, color="red", ls="--", lw=1)
ax[0].set_yticks([]); ax[0].set_xlabel("Mean latency (ms)")
ax[0].set_title("Mean stage breakdown"); ax[0].legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=1)
ax[1].hist(df.e2e_ms, bins=30, color="steelblue", edgecolor="white")
ax[1].axvline(LIMIT, color="red", ls="--", label="1.0 s requirement")
ax[1].axvline(df.e2e_ms.mean(), color="k", label=f"mean {df.e2e_ms.mean():.0f} ms")
ax[1].set_xlabel("End-to-end latency (ms)"); ax[1].set_ylabel("Frames")
ax[1].set_title(f"End-to-end distribution (n={n})"); ax[1].legend()
fig.tight_layout()
fig.savefig("exp3_latency_breakdown.png", dpi=200, bbox_inches="tight")
print("wrote exp3_table_rows.tex, exp3_latency_breakdown.png")