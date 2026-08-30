# -*- coding: utf-8 -*-
"""data/nationwide.json を読み込み、47都道府県verの自己完結HTMLツールを生成する"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")


def main():
    data_path = os.path.join(DATA_DIR, "nationwide.json")
    with open(data_path, encoding="utf-8") as f:
        data = json.load(f)

    paths, labels, listbtns = [], [], []
    for p in data["prefectures"]:
        el_id = f"p_{p['code']}"
        paths.append(
            f'<path id="{el_id}" class="muni" data-name="{p["name"]}" '
            f'data-code="{p["code"]}" d="{p["d"]}"><title>{p["name"]}</title></path>'
        )
        labels.append(
            f'<text class="label" x="{p["cx"]}" y="{p["cy"]}" '
            f'data-w="{p["cw"]}" data-h="{p["ch"]}">{p["name"]}</text>'
        )
        listbtns.append(f'<button class="listbtn" data-target="{el_id}">{p["name"]}</button>')

    pts = " ".join(f'{x},{y}' for x, y in data["inset_cut_line"])
    inset_svg = f'<polyline class="insetCutLine" points="{pts}"/>'

    template_path = os.path.join(BASE, "template_nationwide.html")
    with open(template_path, encoding="utf-8") as f:
        tpl = f.read()

    out = (
        tpl.replace("__SVG_W__", str(data["svg_w"]))
        .replace("__SVG_H__", str(data["svg_h"]))
        .replace("__BASE_FONT__", str(data["base_font"]))
        .replace("__CUR_PATHS__", "\n".join(paths))
        .replace("__CUR_LABELS__", "\n".join(labels))
        .replace("__INSET_BOX__", inset_svg)
        .replace("__CUR_LIST__", "".join(listbtns))
    )

    out_path = os.path.join(BASE, "map_nationwide.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    print(f"書き出し完了: {out_path} ({len(out)} chars)")


if __name__ == "__main__":
    main()
