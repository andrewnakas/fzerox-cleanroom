"""Taint report: generated F-Zero X assets vs the retail extraction (dev check, dirty tree needed).

Scanned (clean vs every retail stream, cleanroom.taint windows, runs >= FAIL_RUN fail):
  * every texture/TLUT as stored bytes (MIO0 textures: compressed and decompressed) and, for non-CI formats,
    decoded RGBA,
  * every sample: its VADPCM bytes in audio_table.bin, its decoded PCM, its codebook (audio_bank.c),
  * the 38 1-bit masks and the crash-screen font the decomp keeps in C.
Kept facts (sequences, soundfont structure, course data, ghosts, code, geometry) are listed, not scanned.

    python -m games.fzerox.taint_report <dirty tree> <clean tree>
"""
import json
import os
import re
import sys

import crunch64
import numpy as np

from cleanroom import taint
from cleanroom.audio import vadpcm
from cleanroom.gfx import texfmt

from .audio import BANK_C, parse_bank
from .extract_spec import CSIZE, FMTS, VER, inc_bytes
from .masks import RX as MASK_RX

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "spec")


def c_words(path, name):
    s = open(path).read()
    m = re.search(r"\b%s\[[^\]]*\]\s*=\s*\{(.*?)\n\};" % re.escape(name), s, re.S)
    return b"".join(int(v, 16).to_bytes(4, "big") for v in re.findall(r"0x[0-9A-Fa-f]+", m.group(1)))


def audio_streams(tree, aud):
    table = open(os.path.join(tree, "bin", VER, "audio_table.bin"), "rb").read()
    samples, books = parse_bank(open(os.path.join(tree, BANK_C)).read())
    bases = aud["bases"]
    for name, d in aud["samples"].items():
        st = bases[d["bank"]][0] + d["addr"]
        data = table[st:st + d["size"]]
        yield "adpcm:" + name, data
        _, order, npred, coefs = books[(d["font"], d["book"])]
        yield "book:" + name, np.asarray(coefs, ">i2").tobytes()
        pcm = vadpcm.decode(data, {"order": order, "npred": npred, "book": coefs}, d["n"])
        yield "pcm:" + name, pcm.astype(">i2").tobytes()


def streams(tree, tex, aud):
    for sym, e in tex.items():
        p = os.path.join(tree, e["file"])
        if e.get("mio0"):
            raw = inc_bytes(p, 1)
            # MIO0 = header, layout flag bits, back-reference commands, literal bytes. Only the literals carry
            # pixel bytes; flags/commands are the encoder's (identical for any blank run in any picture), and
            # the decoded texels are scanned below.
            lit = int.from_bytes(raw[12:16], "big")
            yield "mio0lit:" + sym, raw[lit:]
            b = crunch64.mio0.decompress(raw)
        else:
            b = inc_bytes(p, CSIZE[e["ctype"]])
        yield "tex:" + sym, b
        if e["fmt"] != "TLUT" and "w" in e:
            f, s = FMTS[e["fmt"]]
            if f != texfmt.CI:
                img = texfmt.decode(b, e["w"], e["h"], f, s)
                yield "rgba:" + sym, img[img[..., 3] > 0].tobytes()
    if aud:
        yield from audio_streams(tree, aud)
    cac = open(os.path.join(tree, "src", "assets", VER, "common_assets_compressed", "common_assets_compressed.c")).read()
    for m in MASK_RX.finditer(cac):
        vals = [int(v) for v in re.findall(r"\d+", m.group(2))]
        if len(vals) == 512:
            yield "mask:" + m.group(1), bytes(vals)
    yield "code:sys_fault", c_words(os.path.join(tree, "src/sys/sys_fault.c"), "sFaultCharPixelFlags")


def main(argv):
    dirty, clean = argv[1], argv[2]
    tex = json.load(open(os.path.join(SPEC, "textures.json"), encoding="utf-8"))
    aud = json.load(open(os.path.join(SPEC, "audio.json")))
    if "--only" in argv:   # quick re-check of some textures against ALL retail textures (no audio in the clean set)
        rx = re.compile(argv[argv.index("--only") + 1])
        index = taint.build_index(s for _, s in streams(dirty, tex, None))
        sub = {k: v for k, v in tex.items() if rx.search(k) or rx.search(v["yaml"])}
        hits = taint.scan(index, (x for x in streams(clean, sub, None) if not x[0].startswith(("mask:", "code:"))))
        bad = sorted((h for h in hits if h[3] >= taint.FAIL_RUN), key=lambda h: -h[3])
        print(f"subset {len(sub)} textures: {len(bad)} failing")
        for label, off, nw, run in bad[:10]:
            print(f"  FAIL {label} run {run} B")
        return 1 if bad else 0
    # two passes (pictures + code, then audio) keep the index small enough for a busy machine
    index = taint.build_index(s for _, s in streams(dirty, tex, None))
    hits = taint.scan(index, streams(clean, tex, None))
    del index
    index = taint.build_index(s for _, s in audio_streams(dirty, aud))
    hits += taint.scan(index, audio_streams(clean, aud))
    bad = sorted((h for h in hits if h[3] >= taint.FAIL_RUN), key=lambda h: -h[3])
    print(f"scanned {len(tex)} textures/TLUTs (+MIO0 literals, +decoded), {len(aud['samples'])} samples (ADPCM, PCM, books), "
          f"38 masks, fault font; {len(hits)} streams with short coincidental matches; "
          f"{len(bad)} failing (run >= {taint.FAIL_RUN} B)")
    print("kept facts, not scanned: audio_seq (sequences), soundfont structure (books regenerated), course data, "
          "ghost inputs, CPU lines, asm (boot/RSP code, libultra), Torch geometry C")
    for label, off, nw, run in bad[:15]:
        print(f"  FAIL {label} run {run} B ({nw} windows)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
