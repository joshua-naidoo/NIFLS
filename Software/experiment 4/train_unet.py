"""
NIFLS U-Net training and 5-fold cross-validated evaluation (Experiment 4).

What it does
  1. Reads the annotated transillumination frames (COCO-style polygon labels) and every other
     image in the image folder(s). Frames with no annotation are used as empty-mask negatives.
  2. Crops the centre 1200 x 1200 px of each frame, applies CLAHE, and resizes to IMG_SIZE
     (the same order as host_dashboard.py, so training and deployment match).
  3. Runs 5-fold stratified cross-validation. Every frame is scored once, out-of-fold, so no
     checkpoint is chosen on the data it is scored on. Reports DSC, IoU, precision, recall and
     false detections at both thresholds in THRESHOLDS.
  4. Trains a final model on all usable frames and saves it as nifls_unet_v3.pth, which loads
     directly into the dashboard (rename to nifls_unet_best.vbb if you want that file name).

Model and training: U-Net with a ResNet-34 encoder (ImageNet-pretrained), per-image Dice + BCE
loss on logits, AdamW, cosine learning-rate schedule, fixed number of epochs, flips, rotation,
scale, brightness/contrast and noise augmentation. Masks are resized with area averaging and
thresholded so that thin lines survive.

Usage
  python train_unet.py --images training_images --annotations annotations_v3_std.json --out results

Outputs (in --out): exp4_v3_cv_per_frame.csv, exp4_v3_qualitative.png, nifls_unet_v3.pth

Requires: torch, torchvision, segmentation-models-pytorch, scikit-learn, opencv-python, numpy,
pandas, matplotlib. The ImageNet encoder weights are downloaded on first use (needs internet);
a CUDA GPU is strongly recommended.
"""
import argparse
import os
import json
import random

import cv2
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
import torchvision.transforms.functional as TF
from torchvision.transforms import InterpolationMode
from sklearn.model_selection import StratifiedKFold
import segmentation_models_pytorch as smp
import matplotlib
matplotlib.use("Agg")                      # save figures to file; no display needed
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description="Train and cross-validate the NIFLS U-Net.")
parser.add_argument("--images", nargs="+", required=True,
                    help="folder(s) containing the .jpg/.png frames (annotated frames and negatives)")
parser.add_argument("--annotations", required=True,
                    help="COCO-style JSON with the fracture polygons (e.g. annotations_v3_std.json)")
parser.add_argument("--out", default="results", help="folder for the CSV, figure and model weights")
args = parser.parse_args()

IMAGE_DIRS = args.images
COCO_JSON = args.annotations
OUT_DIR = args.out
os.makedirs(OUT_DIR, exist_ok=True)

# Images with no entry in the annotation file are used as empty-mask negatives. List here any image
# that shows a fracture but has no annotation (it must not be used as a negative):
EXCLUDE = []
MIN_INSIDE = 0.5                   # drop a labelled frame if less than this fraction of its mask lies inside the crop

IMG_SIZE, CROP = 256, 1200         # model input size; centre-crop size in sensor pixels
EPOCHS, BATCH, LR = 120, 8, 2e-4
FOLDS, SEED = 5, 42
THRESHOLDS = (0.5, 0.85)           # both are reported; 0.85 is the dashboard threshold
DILATE_K = 5                       # 5x5 dilation of the labelled mask, applied at full resolution
NUM_WORKERS = 2                    # DataLoader workers (set to 0 on Windows)

def seed_all(s):
    random.seed(s); np.random.seed(s); torch.manual_seed(s); torch.cuda.manual_seed_all(s)
seed_all(SEED)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print("device:", device)

# ---------- annotations ----------
with open(COCO_JSON) as f:
    coco = json.load(f)
info = {i['id']: i for i in coco['images']}
anns = {}
for a in coco.get('annotations', []):
    anns.setdefault(a['image_id'], []).append(a)
ann_names = {os.path.basename(info[k]['file_name']) for k in anns if k in info}

PATH = {}
for d_ in IMAGE_DIRS:
    for f_ in os.listdir(d_):
        if f_.endswith(('.jpg', '.jpeg', '.png')) and f_ not in EXCLUDE:
            PATH[f_] = os.path.join(d_, f_)
valid = sorted(PATH)
missing = sorted(ann_names - set(valid))
print("annotated in JSON but image file not found:", missing)
is_pos = {f: (f in ann_names) for f in valid}
print(f"images: {len(valid)} | with fracture annotation: {sum(is_pos.values())} | "
      f"no annotation (used as empty-mask negatives): {len(valid) - sum(is_pos.values())}")

name2id = {os.path.basename(i['file_name']): k for k, i in info.items()}
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

def small_mask(m):
    s = cv2.resize(m, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_AREA)
    return (s > 64).astype(np.uint8)

# ---------- cache every frame once (4K reads are slow) ----------
X, MD, MR, inside = {}, {}, {}, {}
for f in valid:
    g = cv2.imread(PATH[f], cv2.IMREAD_GRAYSCALE)
    h, w = g.shape
    raw = np.zeros((h, w), np.uint8)
    if is_pos[f]:
        for a in anns[name2id[f]]:
            for seg in a['segmentation']:
                cv2.fillPoly(raw, [np.array(seg).reshape(-1, 2).astype(np.int32)], 255)
    dil = cv2.dilate(raw, np.ones((DILATE_K, DILATE_K), np.uint8), iterations=1)
    y0, x0 = (h - CROP) // 2, (w - CROP) // 2
    c = g[y0:y0 + CROP, x0:x0 + CROP]
    c = clahe.apply(c)                                   # CLAHE after the crop (matches dashboard)
    X[f] = cv2.resize(c, (IMG_SIZE, IMG_SIZE), interpolation=cv2.INTER_AREA)
    inside[f] = (raw[y0:y0 + CROP, x0:x0 + CROP] > 0).sum() / max((raw > 0).sum(), 1) if is_pos[f] else 1.0
    MD[f] = small_mask(dil[y0:y0 + CROP, x0:x0 + CROP])
    MR[f] = small_mask(raw[y0:y0 + CROP, x0:x0 + CROP])
# a labelled frame is dropped entirely (not used as a negative either) if most of its fracture lies outside the crop
lost = [f for f in valid if is_pos[f] and (inside[f] < MIN_INSIDE or not MD[f].any())]
valid = [f for f in valid if f not in lost]
for f in lost: is_pos.pop(f)
print("cached", len(X), "frames at", IMG_SIZE)
print(f"labelled frames dropped (fracture mostly outside the {CROP}px centre crop): {len(lost)} {lost}")
print(f"fracture frames used: {sum(is_pos.values())}")

MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]

class DS(torch.utils.data.Dataset):
    def __init__(self, files, train):
        self.files, self.train = files, train
    def __len__(self):
        return len(self.files)
    def __getitem__(self, i):
        f = self.files[i]
        img = torch.from_numpy(X[f]).float()[None] / 255.0
        m = torch.from_numpy(MD[f]).float()[None]
        if self.train:
            if random.random() < 0.5: img, m = TF.hflip(img), TF.hflip(m)
            if random.random() < 0.5: img, m = TF.vflip(img), TF.vflip(m)
            if random.random() < 0.7:
                ang = random.uniform(-20, 20); sc = random.uniform(0.9, 1.1)
                tx = int(random.uniform(-0.06, 0.06) * IMG_SIZE); ty = int(random.uniform(-0.06, 0.06) * IMG_SIZE)
                img = TF.affine(img, ang, [tx, ty], sc, 0.0, interpolation=InterpolationMode.BILINEAR)
                m = TF.affine(m, ang, [tx, ty], sc, 0.0, interpolation=InterpolationMode.NEAREST)
            if random.random() < 0.5: img = TF.adjust_brightness(img, random.uniform(0.7, 1.3))
            if random.random() < 0.5: img = TF.adjust_contrast(img, random.uniform(0.7, 1.3))
            if random.random() < 0.3: img = (img + 0.02 * torch.randn_like(img)).clamp(0, 1)
        img = TF.normalize(img.repeat(3, 1, 1), MEAN, STD)
        return img, m

def make_model():
    # activation=None -> raw logits for training (apply sigmoid for predictions). The state_dict is
    # identical to a sigmoid-activation model, so nifls_unet_v3.pth loads straight into host_dashboard.py.
    return smp.Unet(encoder_name="resnet34", encoder_weights="imagenet", in_channels=3,
                    classes=1, activation=None).to(device)

def loss_fn(logits, tgt):
    bce = F.binary_cross_entropy_with_logits(logits, tgt, pos_weight=torch.tensor(5.0, device=logits.device))
    p = torch.sigmoid(logits).flatten(1); t = tgt.flatten(1)
    dice = 1 - (2 * (p * t).sum(1) + 1) / (p.sum(1) + t.sum(1) + 1)     # per image, then mean
    return 0.5 * bce + dice.mean()

def train_model(files, epochs=EPOCHS, tag=""):
    model = make_model()
    w = [3.0 if is_pos[f] else 1.0 for f in files]          # positives are rarer: show them ~3x as often
    sampler = torch.utils.data.WeightedRandomSampler(w, num_samples=len(files), replacement=True)
    dl = torch.utils.data.DataLoader(DS(files, True), batch_size=BATCH, sampler=sampler, drop_last=True, num_workers=NUM_WORKERS)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    sch = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=epochs, eta_min=1e-6)
    for ep in range(epochs):
        model.train(); tot = 0
        for x, y in dl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad(); l = loss_fn(model(x), y); l.backward(); opt.step(); tot += l.item()
        sch.step()
        if (ep + 1) % 20 == 0 or ep == 0:
            print(f"{tag} epoch {ep+1}/{epochs} train loss {tot/len(dl):.4f}")
    return model

@torch.no_grad()
def predict(model, files):
    model.eval(); out = {}
    for f in files:
        x, _ = DS([f], False)[0]
        out[f] = torch.sigmoid(model(x[None].to(device)))[0, 0].cpu().numpy()
    return out

def scores(pr, gt):
    tp = (pr & gt).sum(); fp = (pr & ~gt).sum(); fn = (~pr & gt).sum()
    d = 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) else np.nan
    i = tp / (tp + fp + fn) if (tp + fp + fn) else np.nan
    p = tp / (tp + fp) if (tp + fp) else np.nan
    r = tp / (tp + fn) if (tp + fn) else np.nan
    return d, i, p, r

# ---------- 5-fold cross-validation (out-of-fold predictions) ----------
oof = {}
strat = [int(is_pos[f]) for f in valid]
for k, (tr, te) in enumerate(StratifiedKFold(FOLDS, shuffle=True, random_state=SEED).split(valid, strat)):
    seed_all(SEED + k)
    m = train_model([valid[i] for i in tr], tag=f"[fold {k+1}/{FOLDS}]")
    oof.update(predict(m, [valid[i] for i in te]))
    del m; torch.cuda.empty_cache()

rows = []
for f in valid:
    for th in THRESHOLDS:
        pr = oof[f] > th
        if is_pos[f]:
            d, i, p, r = scores(pr, MD[f].astype(bool))
            d_raw = scores(pr, MR[f].astype(bool))[0]
            rows.append(dict(frame=f, positive=True, thr=th, dsc=d, iou=i, precision=p, recall=r,
                             dsc_vs_undilated=d_raw, detected=bool(d > 0), false_detect=False))
        else:
            rows.append(dict(frame=f, positive=False, thr=th, dsc=np.nan, iou=np.nan, precision=np.nan,
                             recall=np.nan, dsc_vs_undilated=np.nan, detected=False, false_detect=bool(pr.any())))
df = pd.DataFrame(rows)
df.to_csv(os.path.join(OUT_DIR, 'exp4_v3_cv_per_frame.csv'), index=False)
npos = int(df[df.thr == THRESHOLDS[0]].positive.sum()); nneg = len(valid) - npos
print(f"\n=== 5-fold out-of-fold results: {npos} fracture frames, {nneg} no-annotation frames ===")
for th in THRESHOLDS:
    s = df[(df.thr == th) & df.positive]
    fd = df[(df.thr == th) & ~df.positive].false_detect
    print(f"threshold {th}: DSC {s.dsc.mean():.3f} +/- {s.dsc.std(ddof=1):.3f} | median {s.dsc.median():.3f} | "
          f">=0.90: {(s.dsc>=0.9).mean()*100:.0f}% | DSC vs undilated {s.dsc_vs_undilated.mean():.3f} | "
          f"IoU {s.iou.mean():.3f} | P/R {s.precision.mean():.3f}/{s.recall.mean():.3f} | detected {int(s.detected.sum())}/{len(s)}")
    print(f"  false detections on no-annotation frames: {int(fd.sum())}/{len(fd)}")

# qualitative figure (best / median / worst at THRESHOLDS[0])
s = df[(df.thr == THRESHOLDS[0]) & df.positive].sort_values('dsc')
picks = [s.iloc[-1].frame, s.iloc[len(s)//2].frame, s.iloc[0].frame]
fig, ax = plt.subplots(3, 4, figsize=(10, 7.5))
for r_, (n, lab) in enumerate(zip(picks, ['best', 'median', 'worst'])):
    g = X[n] / 255.0; p_ = oof[n]; pr = p_ > THRESHOLDS[0]; gt = MD[n].astype(bool)
    ov = np.stack([g] * 3, -1); ov[gt & ~pr] = (0, 1, 0); ov[pr & ~gt] = (1, 0, 0); ov[pr & gt] = (1, 1, 0)
    d = s[s.frame == n].dsc.iloc[0]
    for c_, (im, t, cm) in enumerate([(g, 'input (CLAHE)', 'gray'), (p_, 'probability', 'magma'),
                                      (gt, 'ground truth', 'gray'), (ov, f"{lab}, DSC {d:.2f}", None)]):
        ax[r_, c_].imshow(im, cmap=cm); ax[r_, c_].set_title(t, fontsize=8); ax[r_, c_].axis('off')
plt.tight_layout(); plt.savefig(os.path.join(OUT_DIR, 'exp4_v3_qualitative.png'), dpi=200); plt.close()

# ---------- final model on ALL annotated frames, for deployment ----------
seed_all(SEED)
final = train_model(valid, tag="[final]")
torch.save(final.state_dict(), os.path.join(OUT_DIR, 'nifls_unet_v3.pth'))
print(f"saved {os.path.join(OUT_DIR, 'nifls_unet_v3.pth')}")