# -*- coding: utf-8 -*-
"""サイトのファビコン(ブラウザタブのアイコン)をGeminiで作る一回限りのスクリプト。"""
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE)

PROMPT = (
    "アプリのファビコン(ブラウザのタブに出る、とても小さい正方形アイコン)用のデザイン。"
    "1つのオレンジ色の色鉛筆の先端が、シンプルにデフォルメされた日本列島のシルエットに"
    "軽く触れているイラスト。フラットベクター調、輪郭線は太くはっきり、細部は極力減らし、"
    "16x16ピクセルの小さいサイズでも形がはっきりわかるデザインにする。"
    "背景は温かみのあるベージュ(#f7f5f0)の単色の正方形。文字は入れない。"
    "構図は正方形いっぱいに収まるよう中央に配置する。"
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
            image_config=types.ImageConfig(aspect_ratio="1:1"),
        ),
    )
    raw_path = os.path.join(BASE, "_favicon_raw.png")
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            with open(raw_path, "wb") as f:
                f.write(part.inline_data.data)
            break
    else:
        raise RuntimeError("画像データを受け取れませんでした")

    img = Image.open(raw_path).convert("RGBA")
    w, h = img.size
    side = min(w, h)
    img = img.crop(((w - side) // 2, (h - side) // 2, (w - side) // 2 + side, (h - side) // 2 + side))

    img.resize((180, 180), Image.LANCZOS).save(os.path.join(BASE, "apple-touch-icon.png"))
    icon_sizes = [16, 32, 48]
    icon_imgs = [img.resize((s, s), Image.LANCZOS) for s in icon_sizes]
    icon_imgs[0].save(
        os.path.join(BASE, "favicon.ico"),
        format="ICO",
        sizes=[(s, s) for s in icon_sizes],
        append_images=icon_imgs[1:],
    )
    img.resize((32, 32), Image.LANCZOS).save(os.path.join(BASE, "favicon-32x32.png"))
    print("favicon.ico / apple-touch-icon.png / favicon-32x32.png を書き出しました")


if __name__ == "__main__":
    main()
