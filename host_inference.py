"""
NIFLS real-time triage dashboard (v4)

Mouse
  Click a thumbnail in "Recent detections", or the fracture box in the live feed,
  to open the full-image viewer. In the viewer: scroll to zoom, drag to pan.

Keys
  Main view : Q quit   S screenshot   R reset session   F fullscreen
  Viewer    : X standard / X-ray style   O outline on/off   A / D newer / older
              S save image   + / - zoom   0 reset view   Esc close

Typography: looks for Inter (Inter-Regular.ttf, Inter-SemiBold.ttf) in ./fonts or next
to this file, then falls back to Segoe UI / Helvetica / DejaVu.
"""
import os
import sys
import time
import math
import cv2
import torch
import imagezmq
import threading
import numpy as np
import torchvision.transforms.functional as TF
import segmentation_models_pytorch as smp
from collections import deque
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# ---- Sharpness fix #1: stop Windows from bitmap-stretching the window on scaled displays ----
if sys.platform.startswith("win"):
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# ==========================================
# SETUP & MODEL LOADING
# ==========================================
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"Host inference engine running on: {device}")
if device.type == "cuda":
    torch.backends.cudnn.benchmark = True
else:
    # leave a couple of cores free so the UI thread is not starved by the model
    torch.set_num_threads(max(1, (os.cpu_count() or 4) - 2))

model = smp.Unet(
    encoder_name="resnet34",
    encoder_weights=None,
    in_channels=3,
    classes=1,
    activation="sigmoid",
).to(device)
model.load_state_dict(torch.load('nifls_unet_best.vbb', map_location=device))
model.eval()

image_hub = imagezmq.ImageHub(open_port='tcp://*:5555')
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

# Shared asynchronous state
latest_roi = None
latest_frame_id = 0
latest_mask = None
latest_conf = 0.0
latest_peak = 0.0
latest_infer_ms = 0.0
lock = threading.Lock()
is_running = True

# Diagnostic parameters (unchanged)
REQUIRED_STABILITY_FRAMES = 5
MIN_FRACTURE_AREA = 300
MASK_THRESHOLD = 0.85

# Camera mounted upside down? Rotate what the person SEES by 180 degrees.
ROTATE_DISPLAY_180 = True
# True : the model still receives the camera's original orientation (safe if it was trained on this setup)
# False: the model receives the rotated, upright image (only if it was trained on upright images)
MODEL_SEES_ORIGINAL = True
UNROTATE_FOR_MODEL = ROTATE_DISPLAY_180 and MODEL_SEES_ORIGINAL

# ==========================================
# DESIGN TOKENS
# ==========================================
VIEW = 1200
PANEL_W = 640
CANVAS_W, CANVAS_H = VIEW + PANEL_W, VIEW
PAD = 32
HIST_LEN = 160
THUMB = 168
WIN = "NIFLS Real-Time Triage"
LANCZOS = getattr(Image, "Resampling", Image).LANCZOS
BOX = getattr(Image, "Resampling", Image).BOX
SAVE_DIR = "nifls_captures"


def rgb(h):
    h = h.lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


BG = rgb('#0E1217')
CARD = rgb('#151B23')
CARD2 = rgb('#1C242E')
LINE = rgb('#262F3B')
LINE_HI = rgb('#3A4555')
TEXT = rgb('#EDF1F6')
MUTED = rgb('#8995A6')
OK = rgb('#3DD68C')
WARN = rgb('#F5B84B')
ALERT = rgb('#FF5C5C')
ACCENT = rgb('#6CB8FF')

HERE = os.path.dirname(os.path.abspath(__file__))
REG_PATHS = [
    os.path.join(HERE, "fonts", "Inter-Regular.ttf"), os.path.join("fonts", "Inter-Regular.ttf"),
    os.path.join(HERE, "Inter-Regular.ttf"),
    "C:/Windows/Fonts/segoeui.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
BOLD_PATHS = [
    os.path.join(HERE, "fonts", "Inter-SemiBold.ttf"), os.path.join("fonts", "Inter-SemiBold.ttf"),
    os.path.join(HERE, "Inter-SemiBold.ttf"),
    "C:/Windows/Fonts/segoeuib.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def load_font(size, bold=False):
    for p in (BOLD_PATHS if bold else REG_PATHS):
        if os.path.exists(p):
            try:
                idx = 1 if (bold and p.endswith(".ttc")) else 0
                return ImageFont.truetype(p, size, index=idx)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


f_title = load_font(46, True)
f_h = load_font(25, True)
f_status = load_font(38, True)
f_ring = load_font(54, True)
f_value = load_font(36, True)
f_clock = load_font(30, True)
f_chip = load_font(22, True)
f_btn = load_font(23, True)
f_key = load_font(19, True)
f_label = load_font(22)
f_small = load_font(19)
f_unit = load_font(21)
MEASURE = ImageDraw.Draw(Image.new("RGB", (1, 1)))

# ==========================================
# DRAWING HELPERS
# ==========================================
def aa_rrect(img, box, r, fill=None, outline=None, width=1, S=4):
    """Anti-aliased rounded rectangle via supersampling. Colours may carry alpha."""
    x1, y1, x2, y2 = [int(v) for v in box]
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        return
    base = tuple((fill or outline)[:3]) + (0,)
    layer = Image.new("RGBA", (w * S, h * S), base)
    ImageDraw.Draw(layer).rounded_rectangle(
        (0, 0, w * S - 1, h * S - 1), r * S, fill=fill, outline=outline, width=width * S)
    layer = layer.resize((w, h), BOX)
    img.paste(layer, (x1, y1), layer)


def card(img, box, r=22):
    aa_rrect(img, box, r, fill=CARD, outline=LINE, width=1)


def rounded_mask(w, h, r, S=4):
    m = Image.new("L", (w * S, h * S), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, w * S - 1, h * S - 1), r * S, fill=255)
    return m.resize((w, h), LANCZOS)


THUMB_MASK = rounded_mask(THUMB, THUMB, 14)


def draw_ring(img, cx, cy, radius, frac, color, width=14, S=4):
    D = radius * 2 + 6
    layer = Image.new("RGBA", (D * S, D * S), color + (0,))
    ld = ImageDraw.Draw(layer)
    bbox = (3 * S, 3 * S, (D - 3) * S, (D - 3) * S)
    ld.arc(bbox, 0, 360, fill=LINE + (255,), width=width * S)
    frac = max(0.0, min(1.0, frac))
    if frac > 0.004:
        ld.arc(bbox, -90, -90 + 360 * frac, fill=color + (255,), width=width * S)
    layer = layer.resize((D, D), BOX)
    img.paste(layer, (cx - D // 2, cy - D // 2), layer)


def draw_bar(img, x, y, w, h, frac, color):
    aa_rrect(img, (x, y, x + w, y + h), h // 2, fill=LINE)
    fw = int(w * max(0.0, min(1.0, frac)))
    if fw > 0:
        aa_rrect(img, (x, y, x + max(fw, h), y + h), h // 2, fill=color)


SPARK_BOX = (56, 462, 584, 566)


def spark_y(v):
    x1, y1, x2, y2 = SPARK_BOX
    return y1 + 3 + (1 - min(max(v, 0.0), 1.0)) * (y2 - y1 - 6)


def draw_sparkline(img, values, color, S=3):
    x1, y1, x2, y2 = SPARK_BOX
    w, h = x2 - x1, y2 - y1
    n = len(values)
    if n < 2:
        return
    layer = Image.new("RGBA", (w * S, h * S), color + (0,))
    ld = ImageDraw.Draw(layer)
    pts = []
    for i, v in enumerate(values):
        x = (HIST_LEN - n + i) / (HIST_LEN - 1) * (w - 8) * S
        y = (spark_y(v) - y1) * S
        pts.append((x, y))
    ld.polygon(pts + [(pts[-1][0], h * S), (pts[0][0], h * S)], fill=color + (46,))
    ld.line(pts, fill=color + (255,), width=3 * S, joint="curve")
    ex, ey = pts[-1]
    r = 6 * S
    ld.ellipse((ex - r, ey - r, ex + r, ey + r), fill=color + (255,))
    layer = layer.resize((w, h), BOX)
    img.paste(layer, (x1, y1), layer)


def value_unit(d, x, y, val, unit):
    d.text((x, y), val, font=f_value, fill=TEXT)
    w = d.textlength(val, font=f_value)
    d.text((x + w + 6, y + 14), unit, font=f_unit, fill=MUTED)


def wrap_text(d, s, font, max_w):
    lines, cur = [], ""
    for word in s.split():
        trial = (cur + " " + word).strip()
        if d.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def lighten(c, amt=22):
    return tuple(min(255, v + amt) for v in c)


def inside(pt, r):
    return r[0] <= pt[0] <= r[2] and r[1] <= pt[1] <= r[3]


def chip_on(frame, box, r, fill, draw_fn):
    """Draw a rounded chip onto a BGR numpy frame by touching only its small region
    (avoids converting the whole 1200x1200 frame to PIL and back every frame)."""
    x1, y1, x2, y2 = box
    H, W = frame.shape[:2]
    cx1, cy1, cx2, cy2 = max(0, x1), max(0, y1), min(W, x2), min(H, y2)
    if cx2 - cx1 < 4 or cy2 - cy1 < 4:
        return
    reg = Image.fromarray(cv2.cvtColor(frame[cy1:cy2, cx1:cx2], cv2.COLOR_BGR2RGB))
    aa_rrect(reg, (x1 - cx1, y1 - cy1, x2 - cx1, y2 - cy1), r, fill=fill)
    draw_fn(ImageDraw.Draw(reg), x1 - cx1, y1 - cy1, x2 - cx1, y2 - cy1)
    frame[cy1:cy2, cx1:cx2] = cv2.cvtColor(np.asarray(reg), cv2.COLOR_RGB2BGR)


def centered(label, font, fg):
    def fn(d, x1, y1, x2, y2):
        d.text(((x1 + x2) // 2, (y1 + y2) // 2), label, font=font, fill=fg, anchor="mm")
    return fn


def make_thumb(frame_bgr, contours):
    """Square crop centred on the detection."""
    pts = np.vstack(contours).reshape(-1, 2)
    x1, y1 = pts.min(0)
    x2, y2 = pts.max(0)
    cx, cy = int((x1 + x2) // 2), int((y1 + y2) // 2)
    half = min(int(max(x2 - x1, y2 - y1) / 2) + 110, VIEW // 2)
    x0 = int(np.clip(cx - half, 0, VIEW - 2 * half))
    y0 = int(np.clip(cy - half, 0, VIEW - 2 * half))
    crop = frame_bgr[y0:y0 + 2 * half, x0:x0 + 2 * half]
    crop = cv2.resize(crop, (THUMB, THUMB), interpolation=cv2.INTER_AREA)
    return Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))


def highlight_fracture(frame, contours, color_bgr, dim=0.78, glow=0.5):
    """
    Make the fracture itself stand out, without any box:
      1. gently dim the rest of the image (spotlight with a soft falloff around the fracture)
      2. sharpen / boost local contrast around the fracture so the crack line is easier to see
      3. feathered colour tint that follows the exact segmented shape
      4. soft glow plus a thin crisp outline along the fracture edge
    Works on a padded crop around the fracture, so it stays cheap.
    """
    H, W = frame.shape[:2]
    pts = np.vstack(contours).reshape(-1, 2)
    pad = 120
    x1, y1 = max(0, int(pts[:, 0].min()) - pad), max(0, int(pts[:, 1].min()) - pad)
    x2, y2 = min(W, int(pts[:, 0].max()) + pad), min(H, int(pts[:, 1].max()) + pad)
    out = cv2.convertScaleAbs(frame, alpha=dim)
    roi = frame[y1:y2, x1:x2]
    h, w = roi.shape[:2]
    shifted = [c - np.array([x1, y1], dtype=c.dtype) for c in contours]

    mask = np.zeros((h, w), np.uint8)
    cv2.drawContours(mask, shifted, -1, 255, -1)

    # 1. spotlight (computed at 1/4 size, then scaled up)
    sw_, sh_ = max(2, w // 4), max(2, h // 4)
    small = cv2.resize(mask, (sw_, sh_), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
    halo = cv2.GaussianBlur(small, (0, 0), 7)
    halo = np.clip(halo * 5.0, 0, 1)
    halo = cv2.resize(halo, (w, h), interpolation=cv2.INTER_LINEAR)[..., None]

    # 2. local contrast: fine detail + broad contrast, only inside the spotlight
    fine = cv2.GaussianBlur(roi, (0, 0), 1.6)
    broad_small = cv2.resize(roi, (sw_, sh_), interpolation=cv2.INTER_AREA)
    broad = cv2.resize(cv2.GaussianBlur(broad_small, (0, 0), 3), (w, h), interpolation=cv2.INTER_LINEAR)
    enh = cv2.addWeighted(roi, 1.9, fine, -0.9, 0)
    enh = cv2.addWeighted(enh, 1.6, broad, -0.6, 0)

    mixed = out[y1:y2, x1:x2].astype(np.float32) * (1 - halo) + enh.astype(np.float32) * halo

    # 3. feathered tint that follows the exact shape
    mask_f = cv2.GaussianBlur(mask, (0, 0), 2.0).astype(np.float32) / 255.0
    soft = (mask_f * 0.16)[..., None]
    col = np.array(color_bgr, dtype=np.float32)
    mixed = mixed * (1 - soft) + col * soft

    # 4. glow + crisp outline
    g = np.zeros((h, w), np.uint8)
    cv2.drawContours(g, shifted, -1, 255, 9, cv2.LINE_AA)
    g = cv2.GaussianBlur(g, (0, 0), 5).astype(np.float32) / 255.0
    g *= (1.0 - mask_f)               # glow stays outside, so the real crack stays visible inside the outline
    mixed = mixed + g[..., None] * col * glow * 1.6
    out[y1:y2, x1:x2] = np.clip(mixed, 0, 255).astype(np.uint8)
    cv2.drawContours(out, contours, -1, color_bgr, 2, cv2.LINE_AA)
    return out


# ==========================================
# X-RAY STYLE RENDERING
# ==========================================
_yy, _xx = np.ogrid[:VIEW, :VIEW]
_r = np.sqrt(((_xx - VIEW / 2) / (VIEW / 2)) ** 2 + ((_yy - VIEW / 2) / (VIEW / 2)) ** 2)
VIGNETTE = (1.0 - 0.32 * np.clip(_r - 0.4, 0, 1) ** 1.6).astype(np.float32)
XR_CLAHE = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))


def xray_style(bgr):
    """
    Radiograph-like rendering of an optical transillumination image:
    greyscale, inverted (dense/absorbing areas read bright), contrast-windowed,
    edge-enhanced, with a soft film vignette and a cool tint.
    It is a visual re-rendering only, not a real X-ray.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = XR_CLAHE.apply(gray)
    inv = cv2.GaussianBlur(255 - gray, (0, 0), 1.1).astype(np.float32)
    lo, hi = np.percentile(inv, (1.0, 99.7))
    f = np.clip((inv - lo) / max(hi - lo, 1.0), 0, 1) ** 1.25
    f = f + 0.9 * (f - cv2.GaussianBlur(f, (0, 0), 18))      # broad local contrast
    f = f + 0.6 * (f - cv2.GaussianBlur(f, (0, 0), 2.5))     # fine edge detail
    f = np.clip(f, 0, 1) * VIGNETTE
    out = np.clip(f, 0, 1) * 255.0
    return np.stack([out * 1.00, out * 0.97, out * 0.91], axis=2).clip(0, 255).astype(np.uint8)


# ==========================================
# DETECTION ENTRIES + VIEWER STATE
# ==========================================
gallery = deque(maxlen=3)         # newest first
viewer = None                     # dict while the viewer is open
mouse_xy = (-1.0, -1.0)           # canvas coordinates
drag = {"on": False, "last": (0.0, 0.0)}
live_boxes = []                   # detection boxes in canvas coords (for clicking)
view_scale, view_off = 1.0, (0, 0)
toast_text, toast_until = "", 0.0


def new_entry(raw, annotated, contours, conf, area):
    dt = datetime.now()
    return {"raw": raw.copy(), "contours": [c.copy() for c in contours],
            "thumb": make_thumb(annotated, contours), "dt": dt, "time": dt.strftime("%H:%M:%S"),
            "conf": conf, "area": area, "regions": len(contours), "cache": {}, "xray": None}


def refresh_entry(e, raw, annotated, contours, conf, area):
    e.update(raw=raw.copy(), contours=[c.copy() for c in contours],
             thumb=make_thumb(annotated, contours), conf=conf, area=area,
             regions=len(contours), cache={}, xray=None)


def compose(entry, mode, outline):
    """Full-resolution image for a viewer mode (cached per entry)."""
    key = (mode, outline)
    if key in entry["cache"]:
        return entry["cache"][key]
    if mode == "xray":
        if entry["xray"] is None:
            entry["xray"] = xray_style(entry["raw"])
        base, color = entry["xray"].copy(), WARN[::-1]
    else:
        base, color = entry["raw"].copy(), ALERT[::-1]
    if outline:
        base = highlight_fracture(base, entry["contours"], color, dim=0.9, glow=0.5)
    entry["cache"][key] = base
    return base


def show_toast(msg, secs=2.5):
    global toast_text, toast_until
    toast_text, toast_until = msg, time.time() + secs


def stamp(img_bgr, entry, mode):
    pil = Image.fromarray(cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB))
    d = ImageDraw.Draw(pil, "RGBA")
    kind = "X-ray style rendering, not a radiograph" if mode == "xray" else "Optical transillumination image"
    line = f"NIFLS  {kind}  {entry['dt']:%Y-%m-%d %H:%M:%S}  confidence {int(entry['conf'] * 100)}%"
    d.rectangle((0, pil.height - 46, pil.width, pil.height), fill=(10, 14, 19, 210))
    d.text((18, pil.height - 23), line, font=f_label, fill=TEXT, anchor="lm")
    return cv2.cvtColor(np.asarray(pil), cv2.COLOR_RGB2BGR)


def save_view():
    v = viewer
    e = v["entry"]
    img = stamp(compose(e, v["mode"], v["outline"]), e, v["mode"])
    tag = "xray" if v["mode"] == "xray" else "optical"
    name = f"nifls_{e['dt']:%Y%m%d_%H%M%S}_{tag}{'' if v['outline'] else '_clean'}.png"
    cv2.imwrite(os.path.join(SAVE_DIR, name), img)
    show_toast(f"Saved {name}")


def save_original():
    e = viewer["entry"]
    name = f"nifls_{e['dt']:%Y%m%d_%H%M%S}_original.png"
    cv2.imwrite(os.path.join(SAVE_DIR, name), e["raw"])
    show_toast(f"Saved {name}")


# ---- viewer layout (canvas coordinates) ----
R_CARD = (96, 48, 1744, 1128)
R_IMG = (140, 176, 1064, 1100)
IMG_W = R_IMG[2] - R_IMG[0]
R_CLOSE = (1672, 72, 1720, 120)
R_SEG = (1104, 212, 1700, 268)
R_SEG_STD = (1104, 212, 1402, 268)
R_SEG_XR = (1402, 212, 1700, 268)
R_OUTLINE = (1104, 296, 1700, 344)
STAT_TILES = [(1104, 376, 1398, 476), (1406, 376, 1700, 476),
              (1104, 484, 1398, 584), (1406, 484, 1700, 584)]
R_ZOUT = (1104, 644, 1164, 700)
R_ZIN = (1176, 644, 1236, 700)
R_ZRESET = (1248, 644, 1400, 700)
R_NOTE = (1104, 724, 1700, 848)
R_NEWER = (1104, 872, 1396, 928)
R_OLDER = (1408, 872, 1700, 928)
R_SAVE = (1104, 956, 1700, 1022)
R_SAVEO = (1104, 1034, 1700, 1100)
IMG_MASK = rounded_mask(IMG_W, R_IMG[3] - R_IMG[1], 16)


def open_viewer(entry):
    global viewer
    viewer = {"entry": entry, "mode": "standard", "outline": True,
              "zoom": 1.0, "cx": VIEW / 2, "cy": VIEW / 2}


def close_viewer():
    global viewer
    viewer = None
    drag["on"] = False


def view_geometry(v):
    size = VIEW / v["zoom"]
    half = size / 2
    v["cx"] = min(max(v["cx"], half), VIEW - half)
    v["cy"] = min(max(v["cy"], half), VIEW - half)
    return v["cx"] - half, v["cy"] - half, size, IMG_W / size


def zoom_at(v, factor, pt=None):
    x0, y0, size, ps = view_geometry(v)
    if pt is None:
        pt = ((R_IMG[0] + R_IMG[2]) / 2, (R_IMG[1] + R_IMG[3]) / 2)
    ax, ay = pt[0] - R_IMG[0], pt[1] - R_IMG[1]
    sx, sy = x0 + ax / ps, y0 + ay / ps
    v["zoom"] = min(max(v["zoom"] * factor, 1.0), 8.0)
    size2 = VIEW / v["zoom"]
    ps2 = IMG_W / size2
    v["cx"] = sx - ax / ps2 + size2 / 2
    v["cy"] = sy - ay / ps2 + size2 / 2


def reset_zoom(v):
    v.update(zoom=1.0, cx=VIEW / 2, cy=VIEW / 2)


def step_entry(delta):
    lst = list(gallery)
    try:
        i = lst.index(viewer["entry"])
    except ValueError:
        return
    j = i + delta
    if 0 <= j < len(lst):
        viewer["entry"] = lst[j]
        reset_zoom(viewer)


def nav_state():
    lst = list(gallery)
    try:
        i = lst.index(viewer["entry"])
    except ValueError:
        return None, len(lst)
    return i, len(lst)


def viewer_mouse(event, pt, flags):
    v = viewer
    if event == cv2.EVENT_LBUTTONDOWN:
        if inside(pt, R_IMG):
            drag["on"], drag["last"] = True, pt
        elif inside(pt, R_CLOSE) or not inside(pt, R_CARD):
            close_viewer()
        elif inside(pt, R_SEG_STD):
            v["mode"] = "standard"
        elif inside(pt, R_SEG_XR):
            v["mode"] = "xray"
        elif inside(pt, R_OUTLINE):
            v["outline"] = not v["outline"]
        elif inside(pt, R_ZOUT):
            zoom_at(v, 1 / 1.4)
        elif inside(pt, R_ZIN):
            zoom_at(v, 1.4)
        elif inside(pt, R_ZRESET):
            reset_zoom(v)
        elif inside(pt, R_NEWER):
            step_entry(-1)
        elif inside(pt, R_OLDER):
            step_entry(1)
        elif inside(pt, R_SAVE):
            save_view()
        elif inside(pt, R_SAVEO):
            save_original()
    elif event == cv2.EVENT_MOUSEMOVE and drag["on"]:
        _, _, _, ps = view_geometry(v)
        v["cx"] -= (pt[0] - drag["last"][0]) / ps
        v["cy"] -= (pt[1] - drag["last"][1]) / ps
        drag["last"] = pt
    elif event == cv2.EVENT_LBUTTONUP:
        drag["on"] = False
    elif event == cv2.EVENT_MOUSEWHEEL and inside(pt, R_IMG):
        try:
            delta = cv2.getMouseWheelDelta(flags)
        except AttributeError:
            delta = 1 if flags > 0 else -1
        zoom_at(v, 1.18 if delta > 0 else 1 / 1.18, pt)


def main_mouse(event, pt):
    if event != cv2.EVENT_LBUTTONDOWN:
        return
    for i, entry in enumerate(list(gallery)):
        if inside(pt, (VIEW + SLOT_X[i], SLOT_Y, VIEW + SLOT_X[i] + THUMB, SLOT_Y + THUMB)):
            open_viewer(entry)
            return
    if gallery:
        for b in live_boxes:
            if inside(pt, b):
                open_viewer(gallery[0])
                return


def on_mouse(event, x, y, flags, param):
    global mouse_xy
    pt = ((x - view_off[0]) / view_scale, (y - view_off[1]) / view_scale)
    mouse_xy = pt
    if viewer is not None:
        viewer_mouse(event, pt, flags)
    else:
        main_mouse(event, pt)


# ==========================================
# STATIC LAYERS (drawn once)
# ==========================================
HERO = (32, 132, 608, 372)
SPARK = (32, 392, 608, 592)
TILE_Y = (612, 712)
TILE_W, TILE_GAP = 182, 15
GALLERY = (32, 732, 608, 1048)
SLOT_X = [56 + i * (THUMB + 12) for i in range(3)]
SLOT_Y = 798


def build_static_panel():
    img = Image.new("RGB", (PANEL_W, CANVAS_H), BG)
    d = ImageDraw.Draw(img)
    d.text((PAD, 28), "NIFLS", font=f_title, fill=TEXT)
    d.text((PAD, 86), "Optical transillumination triage", font=f_label, fill=MUTED)

    card(img, HERO)
    d.text((272, 160), "Status", font=f_label, fill=MUTED)
    d.text((272, 284), "Stability", font=f_small, fill=MUTED)

    card(img, SPARK)
    d.text((56, 412), "Detection signal", font=f_h, fill=TEXT)
    d.text((584, 418), f"Threshold {int(MASK_THRESHOLD * 100)}%", font=f_small, fill=MUTED, anchor="ra")
    ty = int(spark_y(MASK_THRESHOLD))
    for x in range(SPARK_BOX[0], SPARK_BOX[2], 12):
        d.line((x, ty, x + 6, ty), fill=LINE_HI, width=1)
    d.line((SPARK_BOX[0], SPARK_BOX[3], SPARK_BOX[2], SPARK_BOX[3]), fill=LINE, width=1)

    for i, label in enumerate(("Events", "Inference", "Stream")):
        x = PAD + i * (TILE_W + TILE_GAP)
        card(img, (x, TILE_Y[0], x + TILE_W, TILE_Y[1]), r=18)
        d.text((x + 20, TILE_Y[0] + 18), label, font=f_small, fill=MUTED)

    card(img, GALLERY)
    d.text((56, 752), "Recent detections", font=f_h, fill=TEXT)
    d.text((584, 758), "Click to inspect", font=f_small, fill=MUTED, anchor="ra")
    for sx in SLOT_X:
        aa_rrect(img, (sx, SLOT_Y, sx + THUMB, SLOT_Y + THUMB), 14, fill=CARD2)

    x = PAD
    for key, label in (("Q", "Quit"), ("S", "Save"), ("R", "Reset"), ("F", "Fullscreen")):
        aa_rrect(img, (x, 1082, x + 30, 1112), 8, fill=CARD2, outline=LINE)
        d.text((x + 15, 1097), key, font=f_key, fill=TEXT, anchor="mm")
        d.text((x + 40, 1086), label, font=f_small, fill=MUTED)
        x += 40 + int(d.textlength(label, font=f_small)) + 22
    d.line((PAD, 1132, PANEL_W - PAD, 1132), fill=LINE, width=1)
    return img


def build_modal_static():
    img = Image.new("RGBA", (CANVAS_W, CANVAS_H), (6, 9, 13, 205))
    aa_rrect(img, R_CARD, 28, fill=CARD + (255,), outline=LINE + (255,), width=1, S=2)
    aa_rrect(img, (R_IMG[0] - 1, R_IMG[1] - 1, R_IMG[2] + 1, R_IMG[3] + 1), 17, fill=LINE + (255,), S=2)
    d = ImageDraw.Draw(img)
    d.text((140, 76), "Fracture detection", font=f_status, fill=TEXT)
    d.text((1104, 178), "View", font=f_small, fill=MUTED)
    aa_rrect(img, R_SEG, 16, fill=CARD2 + (255,))
    d.text((1112, 320), "Fracture outline", font=f_label, fill=TEXT, anchor="lm")
    for (x1, y1, x2, y2), label in zip(STAT_TILES, ("Confidence", "Regions", "Area", "Captured")):
        aa_rrect(img, (x1, y1, x2, y2), 16, fill=CARD2 + (255,))
        d.text((x1 + 20, y1 + 16), label, font=f_small, fill=MUTED)
    d.text((1104, 610), "Zoom", font=f_small, fill=MUTED)
    aa_rrect(img, R_NOTE, 16, fill=CARD2 + (255,))
    return img


STATIC_PANEL = build_static_panel()
MODAL_STATIC = build_modal_static()


def draw_button(canvas, d, rect, label, kind="secondary", enabled=True):
    hover = enabled and inside(mouse_xy, rect)
    if kind == "primary":
        fill = lighten(ACCENT) if hover else ACCENT
        aa_rrect(canvas, rect, 16, fill=fill)
        color = BG
    else:
        fill = lighten(CARD2, 10) if hover else CARD2
        aa_rrect(canvas, rect, 16, fill=fill, outline=LINE_HI if enabled else LINE)
        color = TEXT if enabled else LINE_HI
    d.text(((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2), label, font=f_btn, fill=color, anchor="mm")


def draw_modal(canvas, v):
    canvas.paste(MODAL_STATIC, (0, 0), MODAL_STATIC)
    d = ImageDraw.Draw(canvas)
    e = v["entry"]
    mode, outline = v["mode"], v["outline"]

    # Header
    d.text((140, 130), f"{e['dt']:%d %b %Y, %H:%M:%S}", font=f_label, fill=MUTED)
    idx, n = nav_state()
    if idx is not None:
        d.text((1640, 96), f"{idx + 1} of {n}", font=f_label, fill=MUTED, anchor="rm")
    hov = inside(mouse_xy, R_CLOSE)
    aa_rrect(canvas, R_CLOSE, 16, fill=lighten(CARD2, 14) if hov else CARD2)
    cx, cy = (R_CLOSE[0] + R_CLOSE[2]) // 2, (R_CLOSE[1] + R_CLOSE[3]) // 2
    d.line((cx - 9, cy - 9, cx + 9, cy + 9), fill=TEXT, width=3)
    d.line((cx - 9, cy + 9, cx + 9, cy - 9), fill=TEXT, width=3)

    # Image (zoom + pan)
    base = compose(e, mode, outline)
    x0, y0, size, ps = view_geometry(v)
    xi, yi, si = int(round(x0)), int(round(y0)), int(round(size))
    xi, yi = max(0, min(xi, VIEW - si)), max(0, min(yi, VIEW - si))
    crop = base[yi:yi + si, xi:xi + si]
    interp = cv2.INTER_AREA if si > IMG_W else cv2.INTER_CUBIC
    crop = cv2.resize(crop, (IMG_W, IMG_W), interpolation=interp)
    view_img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
    canvas.paste(view_img, (R_IMG[0], R_IMG[1]), IMG_MASK)

    chip = "X-ray style" if mode == "xray" else "Optical image"
    cw = int(d.textlength(chip, font=f_small))
    aa_rrect(canvas, (R_IMG[0] + 16, R_IMG[1] + 16, R_IMG[0] + 16 + cw + 28, R_IMG[1] + 52), 12,
             fill=(14, 18, 23, 200))
    d.text((R_IMG[0] + 30, R_IMG[1] + 34), chip, font=f_small, fill=TEXT, anchor="lm")

    # View segmented control
    active = R_SEG_XR if mode == "xray" else R_SEG_STD
    aa_rrect(canvas, (active[0] + 4, active[1] + 4, active[2] - 4, active[3] - 4), 12, fill=LINE_HI)
    for rect, label, on in ((R_SEG_STD, "Standard", mode == "standard"), (R_SEG_XR, "X-ray style", mode == "xray")):
        d.text(((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2), label, font=f_btn,
               fill=TEXT if on else MUTED, anchor="mm")

    # Outline toggle
    tx1, ty1, tx2, ty2 = 1640, 304, 1700, 336
    aa_rrect(canvas, (tx1, ty1, tx2, ty2), 16, fill=ACCENT if outline else LINE_HI)
    kx = tx2 - 28 if outline else tx1 + 4
    aa_rrect(canvas, (kx, ty1 + 4, kx + 24, ty2 - 4), 12, fill=TEXT)

    # Stats
    dt_vals = [(f"{int(e['conf'] * 100)}", "%"), (str(e["regions"]), ""), (f"{e['area']:,}", "px"), (e["time"], "")]
    for (x1, y1, x2, y2), (val, unit) in zip(STAT_TILES, dt_vals):
        if unit:
            value_unit(d, x1 + 20, y1 + 44, val, unit)
        else:
            d.text((x1 + 20, y1 + 44), val, font=f_value, fill=TEXT)

    # Zoom controls
    for rect, label in ((R_ZOUT, "-"), (R_ZIN, "+")):
        draw_button(canvas, d, rect, label, enabled=True)
    draw_button(canvas, d, R_ZRESET, "Reset view", enabled=v["zoom"] > 1.0)
    d.text((1700, 672), f"{v['zoom']:.1f}x", font=f_value, fill=TEXT, anchor="rm")

    # Note
    if mode == "xray":
        note = ("X-ray style is a visual re-rendering of this optical image: inverted, contrast-windowed and "
                "edge-enhanced. It is not a radiograph and not a diagnosis.")
    else:
        note = "Original optical transillumination image. Scroll to zoom and drag to pan."
    for i, line in enumerate(wrap_text(d, note, f_small, R_NOTE[2] - R_NOTE[0] - 40)):
        d.text((R_NOTE[0] + 20, R_NOTE[1] + 18 + i * 28), line, font=f_small, fill=MUTED)

    # Navigation + save
    draw_button(canvas, d, R_NEWER, "Newer", enabled=idx is not None and idx > 0)
    draw_button(canvas, d, R_OLDER, "Older", enabled=idx is not None and idx < n - 1)
    draw_button(canvas, d, R_SAVE, "Save image" if mode == "standard" else "Save X-ray image", kind="primary")
    draw_button(canvas, d, R_SAVEO, "Save original")


# ==========================================
# ASYNCHRONOUS INFERENCE WORKER
# ==========================================
def inference_worker():
    global latest_mask, latest_conf, latest_peak, latest_infer_ms
    last_id = -1
    while is_running:
        with lock:
            if latest_roi is None or latest_frame_id == last_id:
                frame_to_process = None
            else:
                frame_to_process = latest_roi.copy()
                last_id = latest_frame_id
        if frame_to_process is None:
            time.sleep(0.005)
            continue

        t0 = time.perf_counter()
        if UNROTATE_FOR_MODEL:      # give the model the orientation the camera actually produced
            frame_to_process = cv2.rotate(frame_to_process, cv2.ROTATE_180)
        gray_roi = cv2.cvtColor(frame_to_process, cv2.COLOR_BGR2GRAY)
        gray_roi = clahe.apply(gray_roi)
        tensor_img = cv2.resize(gray_roi, (256, 256), interpolation=cv2.INTER_AREA)

        tensor = TF.to_tensor(tensor_img).repeat(3, 1, 1)
        tensor = TF.normalize(tensor, mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        tensor = tensor.unsqueeze(0).to(device)

        with torch.inference_mode():
            outputs = model(tensor)

        probs = outputs.squeeze().cpu().numpy()
        if UNROTATE_FOR_MODEL:      # map the prediction back onto the rotated display image
            probs = np.ascontiguousarray(probs[::-1, ::-1])
        infer_ms = (time.perf_counter() - t0) * 1000.0
        pred_mask = probs > MASK_THRESHOLD
        conf = float(probs[pred_mask].mean()) if pred_mask.any() else 0.0
        mask_upscaled = cv2.resize(pred_mask.astype(np.uint8), (VIEW, VIEW), interpolation=cv2.INTER_NEAREST)

        with lock:
            latest_mask = mask_upscaled
            latest_conf = conf
            latest_peak = float(probs.max())
            latest_infer_ms = infer_ms


threading.Thread(target=inference_worker, daemon=True).start()

# ==========================================
# WINDOW (Sharpness fix #2: render at the window's real pixel size)
# ==========================================
def screen_size():
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        w, h = root.winfo_screenwidth(), root.winfo_screenheight()
        root.destroy()
        return w, h
    except Exception:
        return 1920, 1080


def fit_to_window(img_bgr):
    """Resize the canvas to the window's exact pixel size so OpenCV never rescales it (that causes blur)."""
    global view_scale, view_off
    try:
        _, _, ww, wh = cv2.getWindowImageRect(WIN)
    except cv2.error:
        ww, wh = 0, 0
    if ww < 64 or wh < 64:
        view_scale, view_off = 1.0, (0, 0)
        return img_bgr
    s = min(ww / CANVAS_W, wh / CANVAS_H)
    nw, nh = max(1, int(CANVAS_W * s)), max(1, int(CANVAS_H * s))
    interp = cv2.INTER_AREA if s < 1.0 else cv2.INTER_CUBIC
    resized = cv2.resize(img_bgr, (nw, nh), interpolation=interp)
    if (nw, nh) == (ww, wh):
        view_scale, view_off = s, (0, 0)
        return resized
    out = np.empty((wh, ww, 3), dtype=np.uint8)
    out[:] = BG[::-1]
    ox, oy = (ww - nw) // 2, (wh - nh) // 2
    out[oy:oy + nh, ox:ox + nw] = resized
    view_scale, view_off = s, (ox, oy)
    return out


os.makedirs(SAVE_DIR, exist_ok=True)
cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
sw, sh = screen_size()
s0 = min((sw - 40) / CANVAS_W, (sh - 140) / CANVAS_H, 1.0)
cv2.resizeWindow(WIN, int(CANVAS_W * s0), int(CANVAS_H * s0))
cv2.setMouseCallback(WIN, on_mouse)
print("Listening for optimized NIFLS hardware stream on port 5555...")

# ==========================================
# SESSION STATE
# ==========================================
fracture_counter = 0
fracture_total = 0
was_certain = False
history = deque(maxlen=HIST_LEN)
disp_conf = 0.0
fps = 0.0
prev_t = time.time()
fullscreen = False

# ==========================================
# STREAM RECEIVER (own thread: the Pi is released at once and never waits for the UI)
# ==========================================
latest_src = "waiting for stream"
stream_fps = 0.0


def receiver_worker():
    global latest_roi, latest_frame_id, latest_src, stream_fps
    last_t = time.time()
    while is_running:
        name, jpg_buffer = image_hub.recv_jpg()
        image_hub.send_reply(b'OK')
        frame = cv2.imdecode(np.frombuffer(jpg_buffer, dtype='uint8'), -1)
        if frame is None:
            continue
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        if frame.shape[:2] != (VIEW, VIEW):
            frame = cv2.resize(frame, (VIEW, VIEW), interpolation=cv2.INTER_CUBIC)
        if ROTATE_DISPLAY_180:
            frame = cv2.rotate(frame, cv2.ROTATE_180)
        t_now = time.time()
        stream_fps = 0.9 * stream_fps + 0.1 * (1.0 / max(t_now - last_t, 1e-6))
        last_t = t_now
        with lock:
            latest_roi = frame
            latest_frame_id += 1
            latest_src = str(name)


threading.Thread(target=receiver_worker, daemon=True).start()

# ==========================================
# REAL-TIME DIAGNOSTIC DISPLAY LOOP
# ==========================================
BLANK = np.zeros((VIEW, VIEW, 3), dtype=np.uint8)
TARGET_UI_FPS = 30.0
last_fid = -1
valid_contours = []
is_fracture_certain = False
ui_fps, render_ms = 0.0, 0.0
last_report = time.time()

while True:
    loop_start = time.perf_counter()
    with lock:
        roi = latest_roi
        fid = latest_frame_id
        pi_name = latest_src
        current_mask = latest_mask
        current_conf = latest_conf
        current_peak = latest_peak
        infer_ms = latest_infer_ms

    have_frame = roi is not None
    if not have_frame:
        roi = BLANK
    new_frame = have_frame and fid != last_fid

    now = time.time()
    ui_fps = 0.9 * ui_fps + 0.1 * (1.0 / max(now - prev_t, 1e-6))
    prev_t = now

    # ---- Filtering (unchanged logic). Runs once per camera frame, not once per redraw ----
    if new_frame:
        last_fid = fid
        history.append(current_peak)
        is_fracture_certain = False
        valid_contours = []
        if current_mask is not None:
            mask_8u = (current_mask * 255).astype(np.uint8)
            contours, _ = cv2.findContours(mask_8u, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            valid_contours = [c for c in contours if cv2.contourArea(c) > MIN_FRACTURE_AREA]

            if valid_contours:
                fracture_counter += 1
                if fracture_counter >= REQUIRED_STABILITY_FRAMES:
                    is_fracture_certain = True
            else:
                fracture_counter = max(0, fracture_counter - 2)

    is_confirming = (not is_fracture_certain) and fracture_counter > 0
    state_color = ALERT if is_fracture_certain else (WARN if is_confirming else OK)
    total_area = int(sum(cv2.contourArea(c) for c in valid_contours)) if is_fracture_certain else 0

    # ---- Live annotations (all OpenCV, directly on the BGR frame) ----
    display_frame = roi.copy()
    boxes = []
    if is_fracture_certain:
        display_frame = highlight_fracture(display_frame, valid_contours, ALERT[::-1], dim=0.78,
                                           glow=0.5 + 0.15 * math.sin(now * 3))
        for c in valid_contours:          # invisible click targets (no box is drawn)
            x, y, w, h = cv2.boundingRect(c)
            boxes.append((x - 40, y - 40, x + w + 40, y + h + 40))

        if new_frame:
            if not was_certain:
                fracture_total += 1
                gallery.appendleft(new_entry(roi, display_frame, valid_contours, current_conf, total_area))
            elif gallery and current_conf > gallery[0]["conf"]:
                if not (viewer is not None and viewer["entry"] is gallery[0]):
                    refresh_entry(gallery[0], roi, display_frame, valid_contours, current_conf, total_area)
    if new_frame:
        was_certain = is_fracture_certain
    live_boxes = boxes

    if is_fracture_certain:
        thick = 4 + int(4 * (0.5 + 0.5 * math.sin(now * 5)))
        cv2.rectangle(display_frame, (0, 0), (VIEW - 1, VIEW - 1), ALERT[::-1], thick)

    if is_fracture_certain and gallery:
        hint = "Click the fracture to inspect"
        hw = int(MEASURE.textlength(hint, font=f_small))
        chip_on(display_frame, (142, 28, 142 + hw + 36, 76), 24, (14, 18, 23, 180),
                centered(hint, f_small, TEXT))

    dot_r = 5 + int(2 * (0.5 + 0.5 * math.sin(now * 4)))

    def live_pill(d, x1, y1, x2, y2, _r=dot_r):
        d.ellipse((x1 + 26 - _r, y1 + 24 - _r, x1 + 26 + _r, y1 + 24 + _r), fill=ALERT)
        d.text((x1 + 44, y1 + 24), "Live", font=f_chip, fill=TEXT, anchor="lm")

    chip_on(display_frame, (28, 28, 130, 76), 24, (14, 18, 23, 180), live_pill)

    # ---- Panel (PIL, small 640x1200 image) ----
    panel = STATIC_PANEL.copy()
    d = ImageDraw.Draw(panel)

    src = pi_name[:18]
    sw_ = int(d.textlength(src, font=f_label))
    d.text((PANEL_W - PAD, 42), src, font=f_label, fill=MUTED, anchor="ra")
    d.ellipse((PANEL_W - PAD - sw_ - 22, 44, PANEL_W - PAD - sw_ - 12, 54), fill=OK if have_frame else WARN)

    target = current_conf if valid_contours else current_peak
    disp_conf += (target - disp_conf) * 0.2
    draw_ring(panel, 145, 252, 80, disp_conf, state_color)
    d.text((145, 244), f"{int(round(disp_conf * 100))}", font=f_ring, fill=TEXT, anchor="mm")
    d.text((145, 284), "confidence", font=f_small, fill=MUTED, anchor="mm")

    if is_fracture_certain:
        status = "Fracture detected"
        detail = f"{len(valid_contours)} region{'s' if len(valid_contours) != 1 else ''}, {total_area:,} px"
    elif is_confirming:
        status, detail = "Confirming", "Checking across frames"
    else:
        status, detail = "Scanning", "No anomalies in view"
    d.text((272, 190), status, font=f_status, fill=state_color)
    d.text((272, 244), detail, font=f_label, fill=MUTED)

    shown = min(fracture_counter, REQUIRED_STABILITY_FRAMES)
    d.text((584, 284), f"{shown}/{REQUIRED_STABILITY_FRAMES}", font=f_small, fill=TEXT, anchor="ra")
    draw_bar(panel, 272, 322, 312, 10, shown / REQUIRED_STABILITY_FRAMES, state_color)

    draw_sparkline(panel, list(history), ACCENT)

    vals = [(str(fracture_total), "total"), (f"{infer_ms:.0f}", "ms"), (f"{stream_fps:.0f}", "fps")]
    for i, (val, unit) in enumerate(vals):
        value_unit(d, PAD + i * (TILE_W + TILE_GAP) + 20, TILE_Y[0] + 46, val, unit)

    if not gallery:
        mid_x = (SLOT_X[0] + SLOT_X[2] + THUMB) // 2
        d.text((mid_x, SLOT_Y + THUMB // 2 - 14), "No detections yet", font=f_label, fill=TEXT, anchor="mm")
        d.text((mid_x, SLOT_Y + THUMB // 2 + 16), "Best frames appear here", font=f_small, fill=MUTED, anchor="mm")
    for i, entry in enumerate(gallery):
        panel.paste(entry["thumb"], (SLOT_X[i], SLOT_Y), THUMB_MASK)
        if viewer is None and inside(mouse_xy, (VIEW + SLOT_X[i], SLOT_Y, VIEW + SLOT_X[i] + THUMB, SLOT_Y + THUMB)):
            aa_rrect(panel, (SLOT_X[i] - 2, SLOT_Y - 2, SLOT_X[i] + THUMB + 2, SLOT_Y + THUMB + 2), 16,
                     outline=ACCENT, width=3)
        d.text((SLOT_X[i] + 4, SLOT_Y + THUMB + 12), entry["time"], font=f_small, fill=TEXT)
        d.text((SLOT_X[i] + 4, SLOT_Y + THUMB + 36), f"{int(entry['conf'] * 100)}% confidence",
               font=f_small, fill=MUTED)

    d.text((PAD, 1146), datetime.now().strftime("%a %d %b %Y"), font=f_small, fill=MUTED)
    d.text((PAD, 1170), f"UI {ui_fps:.0f} fps, render {render_ms:.0f} ms", font=f_small, fill=MUTED)
    d.text((PANEL_W - PAD, 1142), datetime.now().strftime("%H:%M:%S"), font=f_clock, fill=TEXT, anchor="ra")

    # ---- Assemble canvas in numpy (no full-frame PIL round trip) ----
    canvas_bgr = np.empty((CANVAS_H, CANVAS_W, 3), dtype=np.uint8)
    canvas_bgr[:, :VIEW] = display_frame
    canvas_bgr[:, VIEW:] = cv2.cvtColor(np.asarray(panel), cv2.COLOR_RGB2BGR)

    if viewer is not None:      # the viewer is the only place that still needs the full canvas in PIL
        pil_canvas = Image.fromarray(cv2.cvtColor(canvas_bgr, cv2.COLOR_BGR2RGB))
        draw_modal(pil_canvas, viewer)
        canvas_bgr = cv2.cvtColor(np.asarray(pil_canvas), cv2.COLOR_RGB2BGR)

    if now < toast_until:
        tw = int(MEASURE.textlength(toast_text, font=f_label))
        chip_on(canvas_bgr, (28, CANVAS_H - 64, 28 + tw + 44, CANVAS_H - 16), 24, CARD2,
                centered(toast_text, f_label, TEXT))

    cv2.imshow(WIN, fit_to_window(canvas_bgr))

    # ---- Timing: console report + frame pacing ----
    render_ms = 0.9 * render_ms + 0.1 * (time.perf_counter() - loop_start) * 1000.0
    if time.time() - last_report > 2.0:
        last_report = time.time()
        print(f"stream {stream_fps:4.1f} fps | UI {ui_fps:4.1f} fps | "
              f"render {render_ms:5.1f} ms | inference {infer_ms:5.1f} ms")
    spare = 1.0 / TARGET_UI_FPS - (time.perf_counter() - loop_start)
    key = cv2.waitKey(max(1, int(spare * 1000))) & 0xFF
    if key == 255:
        continue
    if key == ord('q'):
        is_running = False
        break
    if viewer is not None:
        if key == 27:
            close_viewer()
        elif key == ord('x'):
            viewer["mode"] = "standard" if viewer["mode"] == "xray" else "xray"
        elif key == ord('o'):
            viewer["outline"] = not viewer["outline"]
        elif key == ord('s'):
            save_view()
        elif key == ord('a'):
            step_entry(-1)
        elif key == ord('d'):
            step_entry(1)
        elif key in (ord('+'), ord('=')):
            zoom_at(viewer, 1.4)
        elif key == ord('-'):
            zoom_at(viewer, 1 / 1.4)
        elif key == ord('0'):
            reset_zoom(viewer)
    else:
        if key == ord('s'):
            name = datetime.now().strftime("nifls_screenshot_%Y%m%d_%H%M%S.png")
            cv2.imwrite(os.path.join(SAVE_DIR, name), canvas_bgr)
            show_toast(f"Saved {name}")
        elif key == ord('r'):
            fracture_total, fracture_counter, was_certain = 0, 0, False
            gallery.clear()
            history.clear()
            show_toast("Session reset", 2.0)
        elif key == ord('f'):
            fullscreen = not fullscreen
            cv2.setWindowProperty(WIN, cv2.WND_PROP_FULLSCREEN,
                                  cv2.WINDOW_FULLSCREEN if fullscreen else cv2.WINDOW_NORMAL)

cv2.destroyAllWindows()