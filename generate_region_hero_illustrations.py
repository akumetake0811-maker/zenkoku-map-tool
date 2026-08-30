# -*- coding: utf-8 -*-
"""region_{key}.html(地方→都道府県選択ページ)用のヒーローイラストを、
地方ごとの名産・お祭り・風景をテーマにGeminiで生成する一回限りのスクリプト。
index.htmlのhero.pngと同じ画風(フラットベクター調・色鉛筆で描いたような温かいタッチ)で統一する。
"""
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE)
ASSETS_DIR = os.path.join(BASE, "assets")

STYLE_PREFIX = (
    "フラットベクター調のやさしいイラスト。輪郭線は手描き風でややラフ、"
    "色鉛筆で塗ったようなやさしい質感。影は最小限のシンプルなセルシェーディング。"
    "写実的・写真的な表現は絶対に避ける。文字やロゴ、ウォーターマークは一切入れない。"
    "配色は温かみのあるベージュ(#f7f5f0)を背景に、オレンジ系(#c98a5e、#a8663f)を基調とした"
    "やさしいアースカラーでまとめる。人物を描く場合は特定の実在人物に似せない。"
)

# 地方ごとに、その地方らしさが一目で伝わる名産品・名所・お祭りを3〜4個程度指定する
REGION_THEMES = {
    "hokkaido": "毛ガニやイクラなどの海鮮、ラベンダー畑、雪だるまや流氷、乳牛と牧草地。雄大で涼しげな雰囲気。",
    "tohoku": "青森のりんご、ねぶた祭りの灯篭、笹かまぼこ、実った稲穂、こけし人形。実りの秋のような温かい雰囲気。",
    "kanto": "富士山、東京のビル群と東京タワー、温泉旅館(箱根)、いちご。都会と自然が両方ある雰囲気。",
    "chubu": "日本アルプスの山並み、金沢の金箔工芸品、新潟の米俵と日本酒の徳利、味噌樽。山と匠の技の雰囲気。",
    "kinki": "京都の五重塔と紅葉、奈良公園の鹿、大阪のたこ焼き、伊勢神宮の鳥居。歴史と伝統の雰囲気。",
    "chugoku": "出雲大社の注連縄、広島のもみじ饅頭とお好み焼き、瀬戸内海の島々とみかん、鳥取砂丘のらくだ。",
    "shikoku": "讃岐うどん、鳴門の渦潮、愛媛のみかん、よさこい祭りの鳴子。海と太陽の明るい雰囲気。",
    "kyushu_okinawa": "博多の明太子とラーメン、桜島、沖縄のシーサーとハイビスカス、パイナップル。南国の陽気な雰囲気。",
}


def _get_client() -> genai.Client:
    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEYが.envに設定されていません")
    return genai.Client(api_key=api_key)


def generate_one(client: genai.Client, key: str, theme: str) -> None:
    prompt = (
        STYLE_PREFIX
        + "\n\n描きたい内容：この地方を代表するモチーフを、"
        + theme
        + " これらのモチーフを、地図や文字を使わずに、横長の1枚の絵の中に"
        "バランスよく並べて描いてください。背景は無地または淡いグラデーションのみ。"
    )
    response = client.models.generate_content(
        model="gemini-2.5-flash-image",
        contents=[prompt],
        config=types.GenerateContentConfig(
            image_config=types.ImageConfig(aspect_ratio="16:9"),
        ),
    )
    for part in response.candidates[0].content.parts:
        if part.inline_data is not None:
            os.makedirs(ASSETS_DIR, exist_ok=True)
            out_path = os.path.join(ASSETS_DIR, f"hero_{key}.png")
            with open(out_path, "wb") as f:
                f.write(part.inline_data.data)
            print(f"[{key}] 保存完了: {out_path} ({len(part.inline_data.data)} bytes)")
            return
    raise RuntimeError(f"[{key}] 画像データを受け取れませんでした")


def main():
    client = _get_client()
    for key, theme in REGION_THEMES.items():
        generate_one(client, key, theme)


if __name__ == "__main__":
    main()
