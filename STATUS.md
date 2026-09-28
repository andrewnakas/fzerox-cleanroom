# F-Zero X clean room: status

_Last update: 2026-09-27 01:20_

## Works (verified in headless Chrome on the clean build)
- Boots: N64 logo -> title (our logo) -> attract-mode demo race with HUD.
- Plays: Start -> mode select -> difficulty -> cup -> machine select -> machine settings -> race (countdown,
  steering, laps, falling off -> retire back to menus). Keyboard via N64Wasm; gamepads via N64Wasm.
- Audio: our resynthesised SFX + our own procedurally composed music (the retail soundtrack is 18 streamed
  recordings, not sequences) — audio engine unchanged in structure (same soundfont sizes).

## For the morning
- **Play it**: https://andrewnakas.github.io/fzerox-cleanroom/ (once published; see the log below). Keys: arrows = steer,
  D = accelerate (A), S = brake (B), A/E = lean (Z/R), Enter = Start, I = change view; gamepads work.
- **Look at**: pilot portraits (menus, race HUD, character select, endings), title screen (our logo, crowd, comic,
  Blue Falcon), menu signs/cup shields, HUD digits/markers/LED countdown, course billboards, credits machines.
- **Listen**: the music is **our own procedural composition** (the original soundtrack is recorded audio, not note
  data, so it could not be kept as "note sequences"); tell me if you want a different style per course.
- **Record voices** (optional): practice pack at `D:/n64work/fzerox/practice_pack/` (17 lines: announcer 15,
  Mr. Zero 2; personal use only — the reference clips come from your ROM). Play `practice_<WHO>_call_and_response.wav`,
  speak after each beep, record the whole track, then
  `python -m games.fzerox.takes cut <recording> <WHO> D:/n64work/fzerox/practice_pack`,
  `python -m games.fzerox.audio voices D:/n64work/fzerox/clean`, `sh games/fzerox/build_clean.sh`, taint, publish.
  Words were read by Whisper from the retail clips; check SCRIPT.txt (e.g. "That's quite a lap!", "Wicked! Well done!",
  "Fantastic!" are best guesses).

## Decisions (log)
- 2026-09-26 23:15 ROM: `F-Zero X (USA).z64`, md5 753437d0… = decomp's `fzerox.us.rev0.md5`. Unzipped to `D:/n64work/fzerox/rom/`.
- Decomp: `inspectredc/fzerox` @ 4b00f36, cloned LF (`pristine` depth 1; `dirty` with submodules: Torch 432d85c,
  splat 306b23c, asm-processor 52d6454). 4 functions still GLOBAL_ASM (Racer_Draw, Transition_PhasedStripsDraw,
  func_i6_8011D394 + 2 EK-only) — kept as splat asm (code).
- **Web route = 3 (clean N64 ROM + N64Wasm)**, decided 23:20. Why: no F-Zero X PC port with a web target; the decomp
  builds a US ROM; the Star Fox 64 sibling session (same decomp author, same Torch pipeline) proved N64Wasm (MIT,
  ParaLLEl core, keyboard + gamepad + audio) runs at full speed in the browser. `ports/emu` copied from sf64.
- **Compiler**: the decomp uses IDO 7.1 (game) + IDO 5.3 (libultra). The prebuilt ido-static-recomp Windows 7.1
  (Cygwin) dies here ("Page size too small" assert). Built **native IDO 7.1 passes** the PW64 way
  (`tools/idowin/build71.bat`: recomp.exe on the IRIX 7.1 binaries -> clang-cl, `/DIDO71`), output
  `D:/n64work/fzerox/idowin71/bin`. `ido_cc.py` gained `--bin=<dir>` so one make run uses both pass sets.
  **Dirty round trip: md5 == retail (753437d0…)** with these native compilers.
- Build: `games/fzerox/build.sh <tree>` (make -j4, IDO/IDO53 on the command line); Windows patches in
  `games/fzerox/tree_patches.py` (DETECTED_OS, Torch MSVC path, crunch64 for MIO0, asm-processor posix paths).
- Torch built with MSVC 2022 (`cmake --build ... --config Release`), 49 s full extraction.
- ROM layout: the shipped ROM is the **compressed** one (`compress.py` MIO0s 14 whole segments; 419 textures are
  stored pre-compressed as MIO0 `.incbin.c`).
  - **Trap found**: the game reads exactly `_<tex>_COMPRESSED_SIZE` bytes (Torch header defines, plus one literal
    in credits.c) for MIO0 textures -> with our different-size MIO0 data it hung at the N64 logo. generate.py now
    rewrites those defines with our sizes (`patch_comp_sizes`).
  - Whole-segment MIO0 (course/venue textures) must compress about as well as retail: those textures use smooth
    upsampling + an ordered (Bayer) dither instead of noise. `segsize.py` compares; all within retail except
    machine_models (+1.6 %, harmless so far).
  - End padding (F67900.bin, 0xFF) shortened 256 KB so the ROM stays 16 MB.
- Make does not track `#include`d `.inc.c`: generate.py deletes the asset objects so they rebuild.
- Audio: 2 soundfonts, 72 ADPCM samples, no loop predictor states. Sample rate = instrument tuning x 32 kHz.
  Books replaced in audio_bank.c (structure kept as `spec/audio_bank_layout.c` with zeroed books).
  Music is 18 long streamed samples (40-160 s) -> **recomposed** with `music.py` (seeded key/tempo/progression,
  drums/bass/power chords/lead, following the kept per-second loudness curve). ~15 announcer clips (16 kHz,
  2-4 s) -> placeholder TTS to do.
- Text: 6 glyph fonts re-typeset from symbol names (`fonts.py`, OFL fonts Exo 2 / Russo One / Rubik /
  Press Start 2P / M PLUS Rounded / Noto Sans JP); ~140 text textures transcribed (`text_labels.json`: menus,
  headers, 31 ending quotes, 30 name cards) and re-typeset (`labels.py`); HUD widgets (`hudart.py`: position
  digits, place markers, LED countdown, lap/racer digit strips, stat panels); cup shields, mode signs, title logo
  (`signs.py`).
- Intensity (I4/I8) textures: hook drawings are premultiplied into the intensity (else solid boxes).
- Crash-screen font in sys_fault.c replaced (`faultfont.py`); the 38 1-bit ending masks regenerated (`masks.py`).
- Taint: MIO0 streams share encoder back-reference runs for blank areas with retail (e.g. `f000 f012 f024…`,
  "copy 18 zero bytes"); those are not content. The scan covers MIO0 literal bytes + decoded texels.

- 2026-09-27 01:30 **Machine pressure**: C: is at 0 bytes free (other sessions; the pagefile is there too, so the
  commit limit hits ~1.5 GB free), which made IDO passes and numpy fail with odd errors (uopt exit 1, "cannot write
  cur table", OpenBLAS alloc failures). All my temp files now go to D:/n64work/fzerox/tmp (build.sh, build_clean.sh);
  the taint scan hashes in 1 MB chunks and runs pictures and audio as two passes to stay small.

- 2026-09-27 ~01:30 **Paused**: the rebuild + taint job was stopped by Claude Code because the machine was critically
  low on memory (other sessions hold ~20 GB: a mupen64plus console at 9.5 GB, Windows Terminal at 12 GB; C: has 0 bytes
  free). Not restarted automatically. **Not published yet** (publish needs taint 0 failing; last texture-only pass was
  4 trivial near-black runs, fixed in code since, not yet re-verified).
  To resume when memory is free: `sh games/fzerox/build_clean.sh` then
  `python -m games.fzerox.taint_report D:/n64work/fzerox/dirty D:/n64work/fzerox/clean` (expect 0 failing), then
  `sh games/fzerox/publish.sh`.

- 2026-09-27 23:45 Resumed: clean build OK (15 MB ROM), headless check boots to our title, menus and machine settings;
  **taint: 0 failing** (1592 textures/TLUTs + MIO0 literals + decoded, 72 samples ADPCM/PCM/books, 38 masks, fault font).
  **Publish is ready but not done**: `sh games/fzerox/publish.sh` (creates the public repo andrewnakas/fzerox-cleanroom,
  pushes main + gh-pages, enables Pages) was blocked by the auto-mode permission classifier ("Create Public Surface").
  Run it yourself, or allow it, to publish.

## Next
- Taint 0 -> publish (repo + gh-pages).
- Pilot portraits (subagent), title backgrounds (main/comic/Blue Falcon), credits machine pictures.
- Announcer TTS placeholders + practice pack.
