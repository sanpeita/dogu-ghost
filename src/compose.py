"""フレーム列＋ナレーション＋タイトルカードを final.mp4 に合成する。

  python src/compose.py            # out/final_720.mp4
  python src/compose.py --height 1080

前提: out/frames720/f_####.png（24fps, 960枚）/ out/narr_dogu.wav / out/title.png
"""
import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ap = argparse.ArgumentParser()
ap.add_argument("--height", type=int, default=720)
ap.add_argument("--fps", type=int, default=24)
ap.add_argument("--voice-delay", type=float, default=4.0)
ap.add_argument("--title-at", type=float, default=31.4)
a = ap.parse_args()

frames = os.path.join(ROOT, "out", "frames720" if a.height == 720 else "frames", "f_%04d.png")
voice = os.path.join(ROOT, "out", "narr_dogu.wav")
title = os.path.join(ROOT, "out", "title.png")
mix = os.path.join(ROOT, "out", "mix.wav")
out = os.path.join(ROOT, "out", "final_%d.mp4" % a.height)
TOTAL = 40.0

if not os.path.exists(voice):
    sys.exit("ナレーションがありません: " + voice)
if not os.path.isdir(os.path.dirname(frames)):
    sys.exit("フレームがありません: " + os.path.dirname(frames))

delay_ms = int(a.voice_delay * 1000)

# 1) 環境音（低いドローン＋ブラウンノイズ）とナレーションを混ぜる
cmd = [
    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    "-f", "lavfi", "-i", "sine=frequency=55:sample_rate=32000:duration=%g" % TOTAL,
    "-f", "lavfi", "-i", "anoisesrc=color=brown:sample_rate=32000:duration=%g" % TOTAL,
    "-i", voice,
    "-filter_complex",
    ("[0:a]volume=0.16,tremolo=f=0.12:d=0.55[d1];"
     "[1:a]lowpass=f=180,volume=0.05[d2];"
     "[d1][d2]amix=inputs=2:duration=longest:normalize=0[dr];"
     "[2:a]adelay=%d|%d,aecho=0.8:0.9:110|250:0.20|0.10,"
     "loudnorm=I=-16:TP=-1.5:LRA=11[vo];"
     "[dr][vo]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0,"
     "apad=whole_dur=%g,atrim=0:%g,alimiter=limit=0.95[a]" % (delay_ms, delay_ms, TOTAL, TOTAL)),
    "-map", "[a]", "-c:a", "pcm_s16le", mix,
]
print("MIX:", " ".join(cmd[:6]), "...")
subprocess.run(cmd, check=True)

# 2) 映像＋音声＋タイトルカード
cmd = [
    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    "-framerate", str(a.fps), "-start_number", "1", "-i", frames,
    "-loop", "1", "-i", title,
    "-i", mix,
    "-filter_complex",
    ("[0:v]fade=t=in:st=0:d=1.0[base];"
     "[1:v]format=rgba,fade=t=in:st=%g:d=0.9:alpha=1[t];"
     "[base][t]overlay=enable='gte(t,%g)':eof_action=repeat[v]"
     % (a.title_at, a.title_at)),
    "-map", "[v]", "-map", "2:a",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "medium",
    "-c:a", "aac", "-b:a", "192k", "-t", str(TOTAL), "-shortest", out,
]
print("COMPOSE ->", out)
subprocess.run(cmd, check=True)

probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=codec_type,width,height,r_frame_rate",
                        "-of", "default=nw=1", out], capture_output=True, text=True)
print(probe.stdout)
print("DONE", out)
