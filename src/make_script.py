"""ローカルLLM(llama.cpp)で土偶の一人称ナレーションを生成する。

  python src/make_script.py

出力: out/script_candidates.json / out/script_log.txt
ネットワークは使わない（127.0.0.1 の llama-server のみ）。
"""
import json
import os
import re
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)

SYSTEM = (
    "あなたは縄文時代の遮光器土偶です。一人称で、静かに、短い文で語ります。"
    "説明や見出し、括弧書きの指示は書きません。"
)

USER = """つぎの条件で、40秒の映像に載せる語り（ナレーション）を日本語で書いてください。

- 120〜180字（句読点を含む）。それより短くても長くてもいけません。
- 一人称。「わたし」。
- 内容の順序:
  1) わたしは「見るための器」だった（遮光器＝仮面の記憶）
  2) 長いあいだ土の中で眠っていた
  3) いま、光を受けて、また見ている／喋っている
  4) 花（マリーゴールド）は、帰ってくる者のための目印
- 最後は問いかけで終える。
- 比喩は控えめ、文は短く。全体で4〜6文。
- 出力は語りの本文だけ。前置き・見出し・箇条書き・注釈は禁止。

本文:"""


def chat(prompt, temperature=0.8, seed=None):
    body = {
        "model": "local",
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": 260,
        "top_p": 0.9,
        "repeat_penalty": 1.1,
    }
    if seed is not None:
        body["seed"] = seed
    req = urllib.request.Request(
        "http://127.0.0.1:1235/v1/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=300) as r:
        data = json.loads(r.read().decode("utf-8"))
    dt = time.time() - t0
    text = data["choices"][0]["message"]["content"].strip()
    usage = data.get("usage", {})
    return text, dt, usage


def clean(text):
    text = re.sub(r"^[「『\"]|[」』\"]$", "", text.strip())
    text = re.sub(r"\s*\n\s*", "", text)
    return text.strip()


cands = []
for i, seed in enumerate([11, 22, 33]):
    text, dt, usage = chat(USER, temperature=0.8, seed=seed)
    body = clean(text)
    n = len(body)
    ok = 120 <= n <= 180
    cands.append({"seed": seed, "chars": n, "in_range": ok, "text": body,
                  "seconds": round(dt, 1), "usage": usage})
    print("CAND %d seed=%d chars=%d ok=%s %.1fs" % (i + 1, seed, n, ok, dt))
    print(body)
    print("-" * 40)

with open(os.path.join(OUT, "script_candidates.json"), "w", encoding="utf-8") as f:
    json.dump(cands, f, ensure_ascii=False, indent=2)

with open(os.path.join(OUT, "script_log.txt"), "w", encoding="utf-8") as f:
    f.write("model: Llama-3-ELYZA-JP-8B.Q4_K_M.gguf (local GGUF)\n")
    f.write("endpoint: http://127.0.0.1:1235/v1/chat/completions (loopback only)\n")
    f.write("generated_at: %s\n" % time.strftime("%Y-%m-%d %H:%M:%S"))
    for c in cands:
        f.write("seed=%s chars=%s in_range=%s seconds=%s\n" % (c["seed"], c["chars"], c["in_range"], c["seconds"]))

print("SAVED", os.path.join(OUT, "script_candidates.json"))
