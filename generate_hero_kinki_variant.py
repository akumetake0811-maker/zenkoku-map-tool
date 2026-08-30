# -*- coding: utf-8 -*-
"""
トップページのヒーロースライドショー用に「近畿地方の地図を色鉛筆で塗るver」の
フレームを作る一回限りのスクリプト。generate_hero_kanto_variant.pyと同じ方式で、
近畿2府5県だけを切り出し、隣接府県が同色にならないよう手動で配色を指定する。
"""
import json
import os
import subprocess

from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE)
DATA_PATH = os.path.join(BASE, "data", "nationwide.json")
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ASSETS_DIR = os.path.join(BASE, "assets")

KINKI_CODES = ["24", "25", "26", "27", "28", "29", "30"]

# 隣接関係(三重-滋賀-京都-大阪-兵庫-奈良-和歌山)を踏まえ、隣り合う府県は必ず別の色にする
KINKI_COLORS = {
    "24": "#e57373",  # 三重 赤
    "25": "#f2a65a",  # 滋賀 オレンジ
    "26": "#f7d060",  # 京都 黄
    "27": "#e57373",  # 大阪 赤(三重と隣接しないため再利用可)
    "28": "#a3d977",  # 兵庫 緑
    "29": "#9e86d6",  # 奈良 紫
    "30": "#5fb3c9",  # 和歌山 青
}

STYLE_PREFIX = (
    "フラットベクター調のやさしいイラスト。輪郭線ははっきりくっきり、"
    "影は最小限のシンプルなセルシェーディング。写実的・写真的な表現は絶対に避け、"
    "あくまで手描き風のフラットイラストにする。文字やロゴ、ウォーターマークは一切入れない。"
    "配色は温かみのあるベージュ(#f7f5f0)を背景にする。"
)

PROMPT = (
    "添付した画像は、近畿地方の府県境界を正確に示した塗り分け地図です。"
    "この府県ごとの境界線の位置・形と、各府県の塗り分けの色(どの府県がどの色か)は"
    "絶対に変えないでください。\n\n"
    + STYLE_PREFIX
    + "\n\n変えてよいのは質感・タッチだけです。地図の輪郭線を今より少し手描き風のラフな線にし、"
    "各府県の塗りに色鉛筆で塗ったようなやさしい質感を足してください。"
    "そのうえで、地図の右下から色鉛筆を1本だけ持った手を自然に伸ばして添えてください"
    "(色鉛筆は朱色を1本のみ、2本以上は描かない)。背景は無地のベージュのみ。"
)


def build_svg(data, out_w, out_h, bbox):
    x0, y0, x1, y1 = bbox
    parts = [f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" fill="#f7f5f0"/>']
    for p in data["prefectures"]:
        if p["code"] not in KINKI_COLORS:
            continue
        fill = KINKI_COLORS[p["code"]]
        parts.append(
            f'<path d="{p["d"]}" fill="{fill}" stroke="#4a4238" stroke-width="4" stroke-linejoin="round"/>'
        )
    svg_body = "\n".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1-x0} {y1-y0}" '
        f'width="{out_w}" height="{out_h}">{svg_body}</svg>'
    )


def compute_bbox(data, margin_frac=0.12):
    xs0, ys0, xs1, ys1 = [], [], [], []
    for p in data["prefectures"]:
        if p["code"] not in KINKI_COLORS:
            continue
        xs0.append(p["cx"] - p["cw"] / 2)
        xs1.append(p["cx"] + p["cw"] / 2)
        ys0.append(p["cy"] - p["ch"] / 2)
        ys1.append(p["cy"] + p["ch"] / 2)
    x0, x1 = min(xs0), max(xs1)
    y0, y1 = min(ys0), max(ys1)
    mx = (x1 - x0) * margin_frac
    my = (y1 - y0) * margin_frac
    return (x0 - mx, y0 - my, x1 + mx, y1 + my)


def build_reference_png():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    bbox = compute_bbox(data)
    bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
    out_w = 1400
    out_h = round(out_w * bh / bw)
    svg = build_svg(data, out_w, out_h, bbox)

    html_path = os.path.join(BASE, "_kinki_color_reference.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(f"<!DOCTYPE html><html><body style='margin:0;'>{svg}</body></html>")

    png_path = os.path.join(BASE, "_kinki_color_reference.png")
    subprocess.run(
        [
            EDGE_PATH,
            "--headless",
            "--disable-gpu",
            "--virtual-time-budget=4000",
            f"--screenshot={png_path}",
            f"--window-size={out_w},{out_h}",
            f"file:///{html_path.replace(os.sep, '/')}",
        ],
        check=True,
    )
    return png_path


def main():
    reference_png = build_reference_png()
    print(f"ベース参考画像を作成: {reference_png}")

    load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEYが.envに設定されていません")

    with open(reference_png, "rb") as f:
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
            out_path = os.path.join(ASSETS_DIR, "hero4.png")
            with open(out_path, "wb") as f:
                f.write(part.inline_data.data)
            print(f"保存完了: {out_path} ({len(part.inline_data.data)} bytes)")
            return
    raise RuntimeError("画像データを受け取れませんでした")


if __name__ == "__main__":
    main()
