"""
NIFLS edge node: Raspberry Pi 4B camera streamer.

Captures 600x600 frames from the Camera Module 3 NoIR (fixed exposure, gain and focus),
JPEG-encodes them in a capture thread and streams the newest frame to the host laptop
over imagezmq (TCP). Only the newest frame is ever sent, so a slow host cannot build a
queue of stale frames. Start the host dashboard (host_dashboard.py) first.

Requires: picamera2 (install with `sudo apt install python3-picamera2`), OpenCV, imagezmq, NumPy.
Stop with Ctrl+C.
"""
import time
import socket
import threading

import cv2
import imagezmq
from picamera2 import Picamera2

# ---------------- Settings ----------------
SERVER = 'tcp://JOSH-LAPTOP.local:5555'   # host dashboard, found by network name (no fixed IP needed)
SIZE = 600                 # 1200 native-pixel crop on a 2x2-binned mode = 600 real pixels
TARGET_FPS = 30
JPEG_QUALITY = 85          # 70 -> 85 costs little at 600x600 and gives the model cleaner edges
# ------------------------------------------

sender = imagezmq.ImageSender(connect_to=SERVER)
pi_name = socket.gethostname()
print(f"[{pi_name}] Initialising Camera Module 3 (libcamera stack)...")

frame_us = int(1_000_000 / TARGET_FPS)

picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"size": (SIZE, SIZE), "format": "BGR888"},
    # Pin the 2304x1296 mode so the 1200x1200 crop below maps to exactly 600x600 sensor pixels
    sensor={"output_size": (2304, 1296), "bit_depth": 10},
    queue=False,           # always hand back the newest frame, never a stale queued one
    controls={
        "ScalerCrop": (1704, 696, 1200, 1200),     # centre 1200x1200 of the 4608x2592 array
        "FrameDurationLimits": (frame_us, frame_us),
        "ExposureTime": 20000,
        "AeEnable": False,
        "AnalogueGain": 1.0,
        "LensPosition": 5.0,
    },
)
picam2.configure(config)
picam2.start()
print(f"[{pi_name}] Sensor mode in use: {picam2.camera_configuration()['sensor']}")

# ---- Capture + encode thread: runs while the network round trip is in flight ----
cond = threading.Condition()
latest = {"jpg": None, "id": 0}
stats = {"captured": 0, "sent": 0, "encode_ms": 0.0}
running = True


def capture_loop():
    while running:
        frame = picam2.capture_array()
        t0 = time.perf_counter()
        ok, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY])
        if not ok:
            continue
        enc = (time.perf_counter() - t0) * 1000.0
        with cond:
            latest["jpg"] = buf
            latest["id"] += 1
            stats["captured"] += 1
            stats["encode_ms"] = 0.9 * stats["encode_ms"] + 0.1 * enc
            cond.notify()


worker = threading.Thread(target=capture_loop, daemon=True)
worker.start()

print(f"[{pi_name}] Transmitting low-latency stream...")
last_sent_id = 0
last_report = time.time()
last_counts = (0, 0)

try:
    while True:
        with cond:
            cond.wait_for(lambda: latest["id"] != last_sent_id, timeout=1.0)
            if latest["id"] == last_sent_id:
                continue
            buf, last_sent_id = latest["jpg"], latest["id"]
        sender.send_jpg(pi_name, buf)       # blocks until the laptop replies
        stats["sent"] += 1

        now = time.time()
        if now - last_report >= 2.0:
            dt = now - last_report
            cap, snt = stats["captured"], stats["sent"]
            print(f"[{pi_name}] capture {(cap - last_counts[0]) / dt:4.1f} fps | "
                  f"sent {(snt - last_counts[1]) / dt:4.1f} fps | encode {stats['encode_ms']:4.1f} ms")
            last_counts, last_report = (cap, snt), now

except KeyboardInterrupt:
    print("\nStream terminated by user.")
finally:
    running = False
    worker.join(timeout=2.0)
    picam2.stop()