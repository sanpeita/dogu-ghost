# The Dogu Remembers / 遮光器土偶の記憶

A 40-second short film: a Jōmon **dogū** (a clay figure with snow-goggle eyes) remembers what it was
made to do. The narration is written by a **local LLM**, spoken by a **locally trained TTS voice**, and
rendered in **Blender** — the whole pipeline runs with the network off.

- LLM: `Llama-3-ELYZA-JP-8B` (GGUF, Q4_K_M) served by llama.cpp on `127.0.0.1`
- TTS: GPT-SoVITS v2 (weights trained locally, **not** redistributed)
- Render: Blender 5.2 LTS, EEVEE, 1920×1080 / 24 fps
- Length: 40 s (3 s silence → 27 s narration → title card)

## Why

The prompt for this challenge asked for something that works **with the lights and the internet off**.
A dogū is a good fit: it is a face made to be looked at, buried for millennia, and read back by
archaeologists. Here the "ghost in the machine" is not a chatbot in a terminal — it is an object that
was already a mask before it was a model.

## Pipeline

```
dogu_assembly.blend ──► build_scene.py ──► scenes/scene.blend
        (print model)      (assembly, light, camera, bloom keys)

make_script.py ──► narration (126 chars, first person)
        (llama.cpp, loopback)

GPT-SoVITS ──► out/narr_dogu.wav (pitch-shifted −2 semitones)
render.py  ──► out/frames720/f_####.png (960 frames)
compose.py ──► out/final_720.mp4
```

### Reproduce

```bash
# 1) local model server (any llama.cpp build; this run used the Hermes runtime)
llama-server -m models/Llama-3-ELYZA-JP-8B.Q4_K_M.gguf --host 127.0.0.1 --port 1235 -ngl 99 -c 2048

# 2) script
python src/make_script.py

# 3) voice — see docs/voice-setup.md (weights and reference audio are not in this repo)
python src/../infer_gptsovits.py ...     # from the private voice lab

# 4) scene + render
blender --background --factory-startup out/dogu_assembly.blend --python src/build_scene.py
blender --background --factory-startup scenes/scene.blend --python src/render.py -- \
        --w 1280 --h 720 --samples 24 --out out/frames720/f_#### --start 1 --end 960

# 5) compose
python src/compose.py
```

`build_scene.py` is the source of truth for the look: re-running it rebuilds pedestal, flowers,
lighting, eye glow keys and camera from the print-oriented source file. Two things it solves that are
worth knowing if you reuse it:

- The print model is in **millimetres**, so the 250-unit figure sits ~660 units from the camera and
  ordinary wattages render black. `LIGHT_SCALE = 1000` is the measured sweet spot (×100 black,
  ×20000 blown out).
- The arms arrive **detached**, lying on the print bed. The build fits each arm's ball joint to the
  shoulder socket by fitting a sphere to the arm's end vertices and finding the torso's inward-facing
  polys, then translating by +133 mm in Z.

## What is not in this repository

- Model weights (`*.gguf`, GPT-SoVITS checkpoints) — too large, and the voice weights are personal.
- Reference audio and the training set.
- The dogū mesh itself (a separate print project).

`docs/voice-setup.md` describes how the voice was produced instead.

## Licence

Code and text: MIT (`LICENSE`). The rendered stills in `docs/` are released under CC BY 4.0.
