"""The 38 u8[512] arrays in common_assets_compressed: 64x64 1-bit masks (ending fireworks shapes).

    masks.spec(<dirty tree>)     DIRTY: -> spec/masks.json, a 16x16 occupancy grid per mask (coarse outline)
    masks.mask_bytes(symbol)     CLEAN: our 64x64 mask: the grid upsampled smoothly, thresholded, packed MSB-first
"""
import json
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "spec", "masks.json")
RX = re.compile(r"u8 (D_F2[0-9A-F]{5})\[\] = \{([^}]*)\};")


def unpack(vals):
    b = np.array(vals, np.uint8)
    return np.unpackbits(b).reshape(64, 64)


def spec(tree):
    p = os.path.join(tree, "src", "assets", "us", "rev0", "common_assets_compressed", "common_assets_compressed.c")
    out = {}
    for m in RX.finditer(open(p).read()):
        vals = [int(v) for v in re.findall(r"\d+", m.group(2))]
        if len(vals) != 512:
            continue
        bits = unpack(vals).astype(np.float32)
        g = bits.reshape(16, 4, 16, 4).mean((1, 3))
        out[m.group(1)] = [int(round(v * 3)) for v in g.reshape(-1)]   # 2-bit coverage per 4x4 cell
    json.dump(out, open(SPEC, "w"), indent=0)
    print(f"masks: {len(out)} (16x16 2-bit coverage)")


_SPEC = None


def mask_bytes(sym):
    global _SPEC
    if _SPEC is None:
        _SPEC = json.load(open(SPEC))
    g = np.array(_SPEC[sym], np.float32).reshape(16, 16) / 3.0
    # bilinear upsample to 64x64, threshold at half coverage: soft blob shapes, not the retail bits
    c = (np.arange(64) + 0.5) / 4.0 - 0.5
    i0 = np.clip(np.floor(c).astype(int), 0, 15)
    i1 = np.clip(i0 + 1, 0, 15)
    f = np.clip(c - np.floor(c), 0, 1)
    rows = g[i0] * (1 - f)[:, None] + g[i1] * f[:, None]
    img = rows[:, i0] * (1 - f)[None, :] + rows[:, i1] * f[None, :]
    bits = (img >= 0.5).astype(np.uint8)
    return [int(v) for v in np.packbits(bits.reshape(-1))]
