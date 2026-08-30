# -*- coding: utf-8 -*-
"""index.html用のヒーローイラストをGemini画像生成で作る一回限りのスクリプト。
投資ブログ側のimage_gen.py(scripts/app/image_gen.py)と同じGemini API・.envキーを流用する。

県境を無視した塗り分け(隣接県が同色になる・色が県境からはみ出す)を防ぐため、
build_pref_color_reference.pyで作った「正確な都道府県境界で塗り分けたベース画像」を
参考画像として渡し、塗り分けと境界線を変えずに画風だけを描き直してもらう(img2img)。
"""
import os
import subprocess
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE)
ASSETS_DIR = os.path.join(BASE, "assets")
REFERENCE_PNG = os.path.join(BASE, "_pref_color_reference.png")

STYLE_PREFIX = (
    "フラットベクター調のやさしいイラスト。輪郭線ははっきりくっきり、"
    "影は最小限のシンプルなセルシェーディング。写実的・写真的な表現は絶対に避け、"
    "あくまで手描き風のフラットイラストにする。文字やロゴ、ウォーターマークは一切入れない。"
    "配色は温かみのあるベージュ(#f7f5f0)を背景に、オレンジ系(#c98a5e、#a8663f)と"
    "やさしいアースカラーでまとめる。"
)

PROMPT = (
    "添付した画像は、日本の都道府県の境界線を正確に示した塗り分け地図です。"
    "この都道府県ごとの境界線の位置・形と、各都道府県の塗り分けの色(どの県がどの色か)は"
    "絶対に変えないでください。隣り合う都道府県が同じ色になっていたり、色が境界線から"
    "はみ出しているのは添付画像の時点で既に正しいので、そのまま維持してください。\n\n"
    + STYLE_PREFIX
    + "\n\n変えてよいのは質感・タッチだけです。地図の輪郭線を今より少し手描き風のラフな線にし、"
    "各都道府県の塗りに色鉛筆で塗ったようなやさしい質感を足してください。"
    "そのうえで、地図の右下から色鉛筆を1本だけ持った手を自然に伸ばして添えてください"
    "(色鉛筆は1本のみ、2本以上は描かない)。背景は無地のベージュのみ。"
)


def main():
    if not os.path.exists(REFERENCE_PNG):
        print("ベース参考画像が無いので先に作成します...")
        subprocess.run([sys.executable, os.path.join(BASE, "build_pref_color_reference.py")], check=True)

    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEYが.envに設定されていません")

    with open(REFERENCE_PNG, "rb") as f:
        reference_bytes = f.read()

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[
            types.Part.from_bytes(data=reference_bytes, mime_type="image/png"),
            PROMPT,
        ],
        config=types.GenerateContentConfig(
            image_config=types.ImageConfig(aspect_ratio="16:9"),
        ),
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            os.makedirs(ASSETS_DIR, exist_ok=True)
            out_path = os.path.join(ASSETS_DIR, "hero.png")
            with open(out_path, "wb") as f:
                f.write(part.inline_data.data)
            print(f"保存完了: {out_path} ({len(part.inline_data.data)} bytes)")
            return
    raise RuntimeError("画像データを受け取れませんでした")


if __name__ == "__main__":
    main()
