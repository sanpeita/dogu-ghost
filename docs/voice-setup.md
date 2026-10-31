# Voice setup (procedure only — no weights, no reference audio)

The narration in this film is produced with **GPT-SoVITS v2** fine-tuned on a small personal speech
dataset. Neither the trained weights nor the reference recordings are distributed with this
repository. This file records the procedure so the pipeline is reproducible with your own voice.

## 1. Dataset

- 216 short clips (~15 min), 3–8 s each, single speaker, quiet room, one microphone.
- Each clip paired with an exact transcript (`dataset.list`: `path|speaker|language|text`).
- Keep a **short reference clip** (2–5 s) plus its transcript for inference. Choose it by ear: it
  should have the same energy and length as the lines you intend to generate.

## 2. Training (v2)

- GPT: 40 epochs, SoVITS: 10 epochs, ~4.9 GB VRAM on a 6 GB card.
- Save both `GPT_weights_v2/*.ckpt` and `SoVITS_weights_v2/*.pth`.

## 3. Inference

```bash
NLTK_DATA=<lab>/nltk_data <lab>/engines/GPT-SoVITS/.venv/Scripts/python.exe infer_gptsovits.py \
  --ref dataset/wavs/0050.wav \
  --prompt-text "<transcript of 0050.wav>" \
  --texts texts.json \
  --out out/tts \
  --s1 engines/GPT-SoVITS/GPT_weights_v2/<gpt>.ckpt \
  --s2 engines/GPT-SoVITS/SoVITS_weights_v2/<sovits>.pth
```

`texts.json` is `[{"id": "narr", "text": "..."}]`.

Check with a short ASR pass: CER under ~5 % and speaker similarity above ~0.9 was the acceptance bar
on the reference voice.

## 4. Pitch and pacing for this film

The dogū speaks lower and slower than the source voice. Nothing is re-trained; the output is shifted:

```bash
ffmpeg -i narr.wav -af "asetrate=32000*0.891,aresample=32000,atempo=0.858" narr_dogu.wav
```

`0.891` ≈ −2 semitones; `atempo` brings the duration back to ~27 s for a 40 s cut.

## 5. Cautions

- Reference clips and transcripts must be your own voice, or one you have written permission to model.
- Generated audio of a real person should say so wherever it is published.
- Do not ship the weights in a public repository; they are biometric-adjacent.
