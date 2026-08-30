# -*- coding: utf-8 -*-
"""
トップページのヒーロースライドショー用に「東京都の市区町村塗り分けver」の
フレームを作る一回限りのスクリプト。build_pref_color_reference.pyと同じ
img2img方式だが、東京都は53市区町村もあるため隣接関係を手作業でリスト化する
代わりに、実際のSVGパス(data/tokyo.json)からshapelyで隣接判定して彩色する。
"""
import json
import os
import re
import subprocess

from dotenv import load_dotenv
from google import genai
from google.genai import types
from shapely.geometry import Polygon
from shapely.ops import unary_union

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE)
DATA_PATH = os.path.join(BASE, "data", "tokyo.json")
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ASSETS_DIR = os.path.join(BASE, "assets")

PALETTE = [
    "#e57373", "#f2a65a", "#f7d060", "#a3d977", "#6bbf8e",
    "#5fb3c9", "#6d9de8", "#9e86d6", "#d18ac4", "#c9a06b",
]

STYLE_PREFIX = (
    "フラットベクター調のやさしいイラスト。輪郭線ははっきりくっきり、"
    "影は最小限のシンプルなセルシェーディング。写実的・写真的な表現は絶対に避け、"
    "あくまで手描き風のフラットイラストにする。文字やロゴ、ウォーターマークは一切入れない。"
    "配色は温かみのあるベージュ(#f7f5f0)を背景にする。"
)

PROMPT = (
    "添付した画像は、東京都の市区町村境界を正確に示した塗り分け地図です。"
    "この市区町村ごとの境界線の位置・形と、各市区町村の塗り分けの色(どこがどの色か)は"
    "絶対に変えないでください。\n\n"
    + STYLE_PREFIX
    + "\n\n変えてよいのは質感・タッチだけです。地図の輪郭線を今より少し手描き風のラフな線にし、"
    "各市区町村の塗りに色鉛筆で塗ったようなやさしい質感を足してください。"
    "そのうえで、地図の右下から色鉛筆を1本だけ持った手を自然に伸ばして添えてください"
    "(色鉛筆は青色を1本のみ、2本以上は描かない)。背景は無地のベージュのみ。"
)


def parse_rings(d):
    rings = []
    current = []
    for cmd, coords in re.findall(r"([MLZ])([^MLZ]*)", d):
        if cmd == "Z":
            if len(current) >= 3:
                rings.append(current)
            current = []
        else:
            for x, y in re.findall(r"(-?\d+\.?\d*),(-?\d+\.?\d*)", coords):
                current.append((float(x), float(y)))
    if len(current) >= 3:
        rings.append(current)
    return rings


def muni_geometry(d):
    polys = []
    for ring in parse_rings(d):
        try:
            p = Polygon(ring)
            if not p.is_valid:
                p = p.buffer(0)
            if not p.is_empty:
                polys.append(p)
        except Exception:
            continue
    if not polys:
        return None
    return unary_union(polys)


def build_adjacency(municipalities):
    geoms = {}
    for m in municipalities:
        g = muni_geometry(m["d"])
        if g is not None:
            geoms[m["code"]] = g.buffer(3)  # 微小な隙間を隣接とみなすため少し膨らませる

    codes = list(geoms.keys())
    adjacency = {c: [] for c in codes}
    for i in range(len(codes)):
        for j in range(i + 1, len(codes)):
            a, b = codes[i], codes[j]
            if geoms[a].intersects(geoms[b]):
                adjacency[a].append(b)
                adjacency[b].append(a)
    return adjacency


def assign_colors(municipalities, adjacency):
    colors = {}
    # 中心のx+y座標が近い順に処理すると、隣接同士が連続して塗られ彩り豊かになりやすい
    ordered = sorted(municipalities, key=lambda m: (m["cy"], m["cx"]))
    for m in ordered:
        code = m["code"]
        used = {colors[n] for n in adjacency.get(code, []) if n in colors}
        for c in PALETTE:
            if c not in used:
                colors[code] = c
                break
        else:
            colors[code] = PALETTE[0]
    return colors


def build_svg(data, colors, out_w, out_h):
    dv = data["default_view"]
    margin_x = dv["w"] * 0.03
    margin_y = dv["h"] * 0.03
    x0, y0 = dv["x"] - margin_x, dv["y"] - margin_y
    w, h = dv["w"] + margin_x * 2, dv["h"] + margin_y * 2

    parts = [f'<rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="#f7f5f0"/>']
    for m in data["municipalities"]:
        fill = colors.get(m["code"], "#c9a06b")
        parts.append(
            f'<path d="{m["d"]}" fill="{fill}" stroke="#4a4238" stroke-width="2.5" stroke-linejoin="round"/>'
        )
    svg_body = "\n".join(parts)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {w} {h}" width="{out_w}" height="{out_h}">{svg_body}</svg>'


def build_reference_png(data, colors):
    dv = data["default_view"]
    out_w = 1400
    out_h = round(out_w * (dv["h"] * 1.06) / (dv["w"] * 1.06))
    svg = build_svg(data, colors, out_w, out_h)

    html_path = os.path.join(BASE, "_tokyo_color_reference.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(f"<!DOCTYPE html><html><body style='margin:0;'>{svg}</body></html>")

    png_path = os.path.join(BASE, "_tokyo_color_reference.png")
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
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)

    adjacency = build_adjacency(data["municipalities"])
    colors = assign_colors(data["municipalities"], adjacency)

    # 彩色の妥当性を軽く検証しておく(隣接同色が無いか)
    bad = 0
    for code, neighbors in adjacency.items():
        for n in neighbors:
            if colors.get(code) == colors.get(n):
                bad += 1
    print(f"隣接チェック: 同色の隣接ペア = {bad // 2}件")

    reference_png = build_reference_png(data, colors)
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
            out_path = os.path.join(ASSETS_DIR, "hero3.png")
            with open(out_path, "wb") as f:
                f.write(part.inline_data.data)
            print(f"保存完了: {out_path} ({len(part.inline_data.data)} bytes)")
            return
    raise RuntimeError("画像データを受け取れませんでした")


if __name__ == "__main__":
    main()
