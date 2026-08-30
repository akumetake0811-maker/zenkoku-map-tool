# -*- coding: utf-8 -*-
"""index.html用のヒーローイラストをGemini画像生成で作る一回限りのスクリプト。
投資ブログ側のimage_gen.py(scripts/app/image_gen.py)と同じGemini API・.envキーを流用する。
"""
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE)
ASSETS_DIR = os.path.join(BASE, "assets")

STYLE_PREFIX = (
    "フラットベクター調のやさしいイラスト。輪郭線ははっきりくっきり、"
    "影は最小限のシンプルなセルシェーディング。写実的・写真的な表現は絶対に避け、"
    "あくまで手描き風のフラットイラストにする。文字やロゴ、ウォーターマークは一切入れない。"
    "配色は温かみのあるベージュ(#f7f5f0)を背景に、オレンジ系(#c98a5e、#a8663f)と"
    "やさしいアースカラーでまとめる。"
)

PROMPT = (
    STYLE_PREFIX
    + "\n\n描きたい内容：日本地図の白地図に、色鉛筆で優しい色(オレンジ・黄色・黄緑・水色など)を"
    "塗っているところ。手や色鉛筆が画面の下側から伸びていて、地図の一部がすでに数色に塗られている。"
    "全体的にほっこり温かい雰囲気。背景は無地または淡いグラデーションのみ。"
)


def main():
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEYが.envに設定されていません")

    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[PROMPT],
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
