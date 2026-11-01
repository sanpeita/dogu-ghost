## What I built

A 40-second short film. A Jōmon **dogū** — the clay figure with snow-goggle eyes — says four
sentences about what it was made for, its eyes light up, marigolds bloom at its feet, and the title
card lands.

Every stage is local:

| Stage | Tool | Runs on |
|---|---|---|
| Script (126 Japanese characters, first person) | `Llama-3-ELYZA-JP-8B` Q4_K_M via llama.cpp | 127.0.0.1 |
| Voice | GPT-SoVITS v2, fine-tuned on ~15 min of my own speech | local GPU |
| Image | Blender 5.2 LTS / EEVEE, 960 frames at 24 fps | local GPU |
| Edit | ffmpeg | local |

No hosted inference, no API keys, no cloud render. The narration was generated against a loopback
llama.cpp server; the model file sits on the same disk as the render.

[Watch the 40-second film](https://youtu.be/Lt9WfaQIQEM)

## Why a dogū

The challenge asks for a ghost *in the machine*. Most entries will be a chatbot in a terminal. I
wanted the Japanese answer instead: a dogū is a **face made to be looked at** — the goggles are a
mask, the body is a vessel — and it spent a few thousand years underground before anyone read it
back. The "ghost" is not new software. It is an object that was already a mask before it was a model.

So the film gives it exactly one thing it never had: a voice, and forty seconds to use it.

## How it works

Three scripts, each re-runnable from scratch.

**1. The script.** A single prompt fixes the beats (I was a vessel for seeing → I slept → I am
looking again → marigolds mark the ones who come back → a question at the end) and the length
(120–180 characters). The model overshot or undershot on most seeds — 114, 128, 92, 80, 85, 78, 126
characters across seven runs — which is a useful reminder that "please write 150 characters" is a
suggestion, not a constraint. I kept the one that landed in range and removed a parenthetical so it
reads aloud.

**2. The voice.** GPT-SoVITS v2, trained earlier on a small personal dataset. For the dogū I shifted
the output down two semitones and slowed it back to the original duration:

```bash
ffmpeg -i narr.wav -af "asetrate=32000*0.891,aresample=32000,atempo=0.858" narr_dogu.wav
```

The weights and reference audio stay offline — they are personal. `docs/voice-setup.md` records the procedure instead.

**3. The image.** This is where the actual work was.

## Two things that cost me the evening

### Millimetres are not metres

The dogū mesh comes from a 3D-print project, so it is modelled in **millimetres**: a 250-unit figure,
a camera 660 units away, lights 400 units away. Blender renders as if one unit is one metre, so
inverse-square falloff treats the key light as 400 m away. Ordinary wattages render **pure black**.

The fix is not "add more light until something appears". I measured a ladder:

| Light multiplier | Total energy | Result |
|---|---|---|
| ×1 | 11 kW | black |
| ×100 | 1.1 MW | nearly black |
| **×1000** | **11.1 MW** | **correct** |
| ×20000 | 222 MW | blown white |

One `LIGHT_SCALE = 1000` constant, documented with that table next to it, ends the guessing.

### The arms were lying on the print bed

A print model arrives in *print orientation*: every part separate, each one placed so it needs no
supports. The arms were 133 mm below their sockets, sitting on the base like dropped tools.

Rather than eyeballing it, I measured:

- fit a sphere to the arm's end vertices → ball centre `x = ±29.1`, radius ≈ 7.9
- find the torso polygons whose normal points *away* from the torso centroid → the socket cavity,
  centred at `x = ±20.9, z = 81.4`
- the arm's existing X was already "socket centre + ball radius", so the fix was a pure translation:
  **+133 mm in Z**

And then a trap worth writing down: after `ob.location += delta`, `matrix_world` and `bound_box` are
**stale** until `bpy.context.view_layer.update()`. Without it, the pedestal, the flowers and the
camera all get placed against the pre-assembly pose — the figure floats 100 mm above its base and
nothing in the log complains.

## Framing, numerically

Four renders went into guessing whether the marigolds were "in shot". They were in the scene, at the
right height, correctly lit — and below the bottom edge of the frame. The thing that settled it was
one projection dump:

```python
from bpy_extras.object_utils import world_to_camera_view
pts = [world_to_camera_view(scn, cam, ob.matrix_world @ Vector(c)) for c in ob.bound_box]
# NDC y < 0 means below the bottom edge
```

If a prop "looks invisible", compute its NDC box before touching the material.

## Why open weights matter here

The submission rule was "works with the lights and the internet off". A hosted model cannot satisfy
that sentence, no matter how open its weights are. Keeping the whole chain local also made the piece
*cheaper to iterate*: seven script generations and about twenty still renders cost nothing but time,
so I could throw away the wrong ones — which is most of them.

The trade was quality on the writing: an 8B Japanese model wrote a usable 126 characters, but it
would not obey a length limit, and it wanted parentheses. The interesting part of local-first work is
not that it beats the cloud on quality. It is that it stays available, and it lets you redo things.

## What I'd do next

- Eyes: the glow spheres had to be moved 2.5 mm forward, out of the socket cavity, or they render as
  dull holes at any energy.
- The window between "correct exposure" and "blown white" is about 1.5 stops at this scale; the final
  cut sits at exposure +0.2.
- The narration is 27 s in a 40 s cut, so the last 8 seconds are the title card — that is a design
  choice, but a longer script (150+ characters) would be better served by a 50 s cut.

## Agent session

Built with Hermes Agent (Marcos profile) driving Blender headless, llama.cpp and ffmpeg from
one session; the still frames, the light ladder and the joint fit were all measured, not guessed.

## Licence

Code and text MIT. Stills CC BY 4.0. Voice model and reference audio are not distributed.