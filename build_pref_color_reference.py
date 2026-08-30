# -*- coding: utf-8 -*-
"""
data/nationwide.json の正確な都道府県境界を使い、隣接県が同じ色にならないよう
グラフ彩色した「正しい塗り分け」のベース画像を作る。
このベース画像をGeminiに参考画像として渡すことで、AIが県境を無視して
色を塗ってしまう問題(隣接県が同色になる・県境からはみ出す)を防ぐ。
"""
import json
import os
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE, "data", "nationwide.json")

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

PALETTE = ["#e57373", "#f2a65a", "#f7d060", "#a3d977", "#6bbf8e", "#5fb3c9", "#9e86d6"]

# 実際の都道府県の隣接関係(JIS都道府県コード)。厳密な地理データではなく手動リストだが、
# このベース画像は色の塗り分け参考用なので十分な精度。
ADJACENCY = {
    "01": [],
    "02": ["03", "05"],
    "03": ["02", "05", "04"],
    "04": ["03", "05", "06", "07"],
    "05": ["02", "03", "04", "06"],
    "06": ["05", "04", "07", "15"],
    "07": ["04", "06", "15", "10", "09", "08"],
    "08": ["07", "09", "11", "12"],
    "09": ["07", "08", "10", "11"],
    "10": ["07", "09", "11", "20", "15"],
    "11": ["08", "09", "10", "12", "13", "19", "20"],
    "12": ["08", "11", "13"],
    "13": ["11", "12", "14", "19"],
    "14": ["13", "19", "22"],
    "15": ["06", "07", "10", "20", "16"],
    "16": ["15", "20", "21", "17"],
    "17": ["16", "21", "18"],
    "18": ["17", "21", "25", "26"],
    "19": ["11", "13", "14", "22", "20"],
    "20": ["15", "10", "11", "19", "22", "23", "21", "16"],
    "21": ["16", "17", "18", "25", "23", "20", "24"],
    "22": ["14", "19", "20", "23"],
    "23": ["20", "21", "24", "22"],
    "24": ["23", "21", "25", "26", "29", "30"],
    "25": ["18", "21", "24", "26"],
    "26": ["18", "25", "24", "29", "27", "28"],
    "27": ["26", "29", "30", "28"],
    "28": ["26", "27", "33", "31"],
    "29": ["26", "24", "30", "27"],
    "30": ["27", "29", "24"],
    "31": ["28", "33", "32"],
    "32": ["31", "33", "34"],
    "33": ["28", "31", "32", "34"],
    "34": ["32", "33", "35"],
    "35": ["34"],
    "36": ["37", "38", "39"],
    "37": ["36", "38"],
    "38": ["36", "37", "39"],
    "39": ["36", "38"],
    "40": ["41", "44", "43"],
    "41": ["40", "42"],
    "42": ["41"],
    "43": ["40", "44", "45", "46"],
    "44": ["40", "43", "45"],
    "45": ["43", "44", "46"],
    "46": ["43", "45"],
    "47": [],
}


def assign_colors():
    colors = {}
    for code in sorted(ADJACENCY.keys()):
        used = {colors[n] for n in ADJACENCY[code] if n in colors}
        for c in PALETTE:
            if c not in used:
                colors[code] = c
                break
    # 隣接県のない北海道・沖縄は見た目のバリエーションのため個別の色に上書き
    colors["01"] = "#6d9de8"
    colors["47"] = "#5fb3c9"
    return colors


def build_svg(data, colors, out_w, out_h):
    svg_w, svg_h = data["svg_w"], data["svg_h"]
    parts = [f'<rect x="0" y="0" width="{svg_w}" height="{svg_h}" fill="#f7f5f0"/>']
    for p in data["prefectures"]:
        fill = colors.get(p["code"], "#c9a06b")
        parts.append(
            f'<path d="{p["d"]}" fill="{fill}" stroke="#4a4238" stroke-width="4" stroke-linejoin="round"/>'
        )
    svg_body = "\n".join(parts)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" width="{out_w}" height="{out_h}">{svg_body}</svg>'


def main():
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    colors = assign_colors()
    out_w = 1600
    out_h = round(out_w * data["svg_h"] / data["svg_w"])
    svg = build_svg(data, colors, out_w, out_h)

    html_path = os.path.join(BASE, "_pref_color_reference.html")
    html = f"<!DOCTYPE html><html><body style='margin:0;'>{svg}</body></html>"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    png_path = os.path.join(BASE, "_pref_color_reference.png")

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
    print(f"ベース参考画像を書き出しました: {png_path}")
    return png_path


if __name__ == "__main__":
    main()
