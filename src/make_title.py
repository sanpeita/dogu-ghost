"""エンドカード（タイトル）PNG を作る。

  python src/make_title.py
出力: out/title.png
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
W, H = 1280, 720

img = Image.new("RGB", (W, H), (5, 7, 11))
d = ImageDraw.Draw(img)

# うっすらしたビネット（中心をわずかに明るく）
for r in range(min(W, H) // 2, 0, -8):
    a = int(10 * (1 - r / (min(W, H) / 2)))
    d.ellipse([W / 2 - r * 1.6, H / 2 - r, W / 2 + r * 1.6, H / 2 + r],
              outline=(5 + a, 7 + a, 11 + a))

jp = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 62)
en = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 30)
cr = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 17)
cr_small = ImageFont.truetype("C:/Windows/Fonts/meiryo.ttc", 15)


def center(text, font, y, fill):
    box = d.textbbox((0, 0), text, font=font)
    d.text(((W - (box[2] - box[0])) / 2, y), text, font=font, fill=fill)


center("遮光器土偶の記憶", jp, 268, (238, 233, 224))
center("The Dogu Remembers", en, 352, (196, 178, 150))

d.line([(W / 2 - 150, 418), (W / 2 + 150, 418)], fill=(120, 96, 70), width=1)

center("Llama-3-ELYZA-JP-8B ・ GPT-SoVITS ・ Blender 5.2 EEVEE", cr, 452, (140, 138, 132))
center("すべてローカル実行 / fully offline", cr, 482, (120, 118, 112))
center("Hacktoberfest 2026 ・ devchallenge ・ hf26challenge", cr_small, 528, (96, 94, 90))

img.save(os.path.join(OUT, "title.png"))
print("SAVED", os.path.join(OUT, "title.png"))
