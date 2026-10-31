"""final.mp4 を YouTube にアップロードする（既定は限定公開）。

  python src/upload_youtube.py --file out/final_720.mp4 --privacy unlisted

認証は marcos プロファイルの google_token_youtube.json（youtube.upload スコープ）を使う。
トークンは表示しない。
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request

TOKEN = r"C:\Users\unocy\AppData\Local\hermes\profiles\marcos\google_token_youtube.json"

TITLE = "The Dogu Remembers / 遮光器土偶の記憶 (40s, fully offline)"
DESCRIPTION = """A Jōmon dogū narrates its own memory. Script by a local GGUF (Llama-3-ELYZA-JP-8B),
voice by a locally trained GPT-SoVITS v2, image by Blender 5.2 EEVEE. No API calls.

遮光器土偶が自分の記憶を語る40秒。台本はローカルLLM、声はローカル学習のTTS、映像はBlender。
すべてローカル実行です。

#Hacktoberfest #devchallenge #hf26challenge
"""
TAGS = ["hacktoberfest", "devchallenge", "hf26challenge", "blender", "llm", "dogu", "粘土"]


def access_token():
    d = json.load(open(TOKEN, encoding="utf-8"))
    if d.get("token") and d.get("expiry"):
        # 期限切れでも refresh で取り直す（判定はGoogle側に任せる）
        pass
    body = urllib.parse.urlencode({
        "client_id": d["client_id"],
        "client_secret": d["client_secret"],
        "refresh_token": d["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(d["token_uri"], data=body,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        tok = json.loads(r.read().decode())["access_token"]
    return tok


def upload(path, privacy):
    tok = access_token()
    size = os.path.getsize(path)
    meta = {
        "snippet": {
            "title": TITLE,
            "description": DESCRIPTION,
            "tags": TAGS,
            "categoryId": "24",  # Entertainment
            "defaultLanguage": "ja",
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    init = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=json.dumps(meta).encode(),
        headers={
            "Authorization": "Bearer " + tok,
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Length": str(size),
            "X-Upload-Content-Type": "video/mp4",
        },
        method="POST",
    )
    with urllib.request.urlopen(init, timeout=60) as r:
        session = r.headers["Location"]

    with open(path, "rb") as f:
        data = f.read()
    put = urllib.request.Request(session, data=data, method="PUT",
                                 headers={"Content-Type": "video/mp4", "Content-Length": str(size)})
    t0 = time.time()
    with urllib.request.urlopen(put, timeout=1800) as r:
        res = json.loads(r.read().decode())
    print("uploaded in %.1fs" % (time.time() - t0))
    vid = res["id"]
    print("VIDEO_ID", vid)
    print("URL https://youtu.be/" + vid)
    return vid


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default="out/final_720.mp4")
    ap.add_argument("--privacy", default="unlisted", choices=["private", "unlisted", "public"])
    a = ap.parse_args()
    p = a.file if os.path.isabs(a.file) else os.path.abspath(a.file)
    if not os.path.exists(p):
        sys.exit("no file: " + p)
    upload(p, a.privacy)
