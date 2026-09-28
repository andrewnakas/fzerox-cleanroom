# F-Zero X — clean room web build

Play: **https://andrewnakas.github.io/fzerox-cleanroom/**

F-Zero X (US 1.0) built from the [fzerox decompilation](https://github.com/inspectredc/fzerox) and played in
the browser with [N64Wasm](https://github.com/nbarkhina/N64Wasm) (MIT), with **every asset the decomp normally
extracts from a ROM regenerated**: textures, fonts, HUD, menus, palettes, portraits, sound effects and music.
No ROM is needed to play it.

Controls: arrow keys = stick · `D` = A (accelerate) · `S` = B (brake) · `A` / `E` = Z / R (lean; tap twice
for a side attack) · `Enter` = Start · `I` = C-up (view) · gamepads work too (remap under the `` ` `` menu).
Phones/tablets get a touch pad.

## What is kept, what is generated

The decomp is source code: game logic, and — through its Torch asset extractor — display lists, vertices,
course data, ghost inputs and CPU racing lines as C. Everything else comes from the ROM. This project reads
the ROM **once, in a "dirty room" step** (`extract_spec.py`, `audio.py spec`), keeps only coarse facts in
`spec/`, and builds every asset from those facts plus our own drawings:

| Asset | Kept fact | Generated |
|---|---|---|
| Textures (1529) + palettes (63) | format, size, a 4×4 colour grid (16×16 for ≥128 px), a 2-bit alpha outline | colour from the grid, our own dither; palettes rebuilt by k-means over the pictures that share them |
| MIO0-stored textures (419) and compressed segments | — | compressed by us; the decomp's `_COMPRESSED_SIZE` defines are rewritten with our sizes |
| Glyph fonts (6 fonts, 334 glyphs) | which character each texture holds (symbol names) | re-typeset with OFL fonts (Exo 2, Russo One, Rubik, Press Start 2P, M PLUS Rounded, Noto Sans JP) — `fonts.py` |
| Text in textures (menus, headers, 31 ending quotes) | the words (transcribed) | re-typeset — `text_labels.json`, `labels.py` |
| Portraits, full-body pictures, ending panels | the alpha silhouette | drawn from our own character briefs — `pilots.py` |
| Ending firework masks (38 × 64×64 1-bit, in C) | 16×16 coverage | our smooth shapes — `masks.py` |
| Crash-screen font (in the decomp's C) | layout | our 5×7 font — `faultfont.py` |
| Sound effects (52 samples) | length, rate, a coarse spectral outline, median pitch, loudness | resynthesised; our own VADPCM codebooks (same predictor count, so the soundfont keeps its size) |
| Music (the retail soundtrack is ~20 streamed recordings, not note data) | slot length and rate, a per-second loudness curve | **recomposed**: our own procedural rock/techno tracks (`music.py`) |
| Announcer | slot length and rate | placeholder (TTS when present) |

`taint_report.py` scans every generated texture (stored bytes, MIO0 bytes and decoded RGBA), every sample
(ADPCM bytes, decoded PCM, codebooks), the masks and the fault font against the retail extraction for shared
runs of 32 bytes or more.

Kept as code, as in any decomp build: IPL3 boot code, RSP microcode, libultra, the game code.

## Build (Windows, Git Bash)

Needs Python 3 (numpy, scipy, Pillow, crunch64), GNU make, libdragon's mips64-elf binutils, native IDO 7.1 and
5.3 passes (recompiled with ido-static-recomp's `recomp` and clang-cl: `tools/idowin/build71.bat`, driven by
`tools/idowin/ido_cc.py`), Torch (built with MSVC) and the decomp's Python requirements.

```sh
# dirty room, once: needs your own ROM, never published
git clone https://github.com/inspectredc/fzerox dirty       # + submodules; clone with core.autocrlf=false
python -m games.fzerox.tree_patches dirty                   # Windows build patches
cp baserom.us.rev0.z64 dirty/ && TARGET_RULE=extract sh games/fzerox/build.sh dirty
python -m games.fzerox.tree_patches dirty --splat && TARGET_RULE=assets sh games/fzerox/build.sh dirty
python -m games.fzerox.extract_spec dirty                   # -> spec/textures.json, spec/masks.json
python -m games.fzerox.audio spec dirty                     # -> spec/audio.json, spec/audio_bank_layout.c

# clean room: from the spec only
games/fzerox/build_clean.sh --audio                         # generate, build ROM, web site
python -m games.fzerox.taint_report dirty clean             # dev check
```
