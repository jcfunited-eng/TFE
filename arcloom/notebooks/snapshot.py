"""
ArcLoom Camera Snapshot — capture and save one Y-channel frame.

Usage in Jupyter (after overlay loaded):
    from pynq import MMIO
    mmio = MMIO(0x40000000, 0x100)
    %run snapshot.py

Saves: /home/xilinx/jupyter_notebooks/ArcLoom/snapshot.png
"""

import time
import numpy as np
from PIL import Image

# Registers
REG_SNAPSHOT_CTRL = 0x5C  # write: [0]=trigger, [16:2]=read addr
REG_SNAPSHOT_STATUS = 0x5C  # read: [0]=done, [1]=busy
REG_SNAPSHOT_DATA = 0x60  # read: 4 Y pixels per word

WIDTH = 80
HEIGHT = 60
N_PIXELS = WIDTH * HEIGHT  # 4,800
N_WORDS = N_PIXELS // 4   # 1,200

# Trigger snapshot
print("Triggering snapshot...")
mmio.write(REG_SNAPSHOT_CTRL, 0x01)

# Wait for done
for _ in range(100):
    status = mmio.read(REG_SNAPSHOT_STATUS)
    if status & 0x01:  # done bit
        break
    time.sleep(0.1)
else:
    print("Snapshot timed out!")
    raise RuntimeError("Snapshot did not complete")

print("Frame captured. Reading BRAM...")

# Read frame data
pixels = np.zeros(N_PIXELS, dtype=np.uint8)
for i in range(N_WORDS):
    # Set read address
    mmio.write(REG_SNAPSHOT_CTRL, (i << 2))
    # Small delay for BRAM read latency
    word = mmio.read(REG_SNAPSHOT_DATA)
    pixels[i*4 + 0] = word & 0xFF
    pixels[i*4 + 1] = (word >> 8) & 0xFF
    pixels[i*4 + 2] = (word >> 16) & 0xFF
    pixels[i*4 + 3] = (word >> 24) & 0xFF

    if i % 300 == 0:
        print(f"  {i}/{N_WORDS} words read...")

# Reshape and save
frame = pixels.reshape((HEIGHT, WIDTH))
img = Image.fromarray(frame, mode='L')
path = '/home/xilinx/jupyter_notebooks/ArcLoom/snapshot.png'
img.save(path)
print(f"Saved: {path}")
print(f"Min={frame.min()}, Max={frame.max()}, Mean={frame.mean():.1f}")
