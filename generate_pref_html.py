# -*- coding: utf-8 -*-
"""data/{pref}.json を読み込み、都道府県ごとの自己完結HTMLツールを生成する"""
import json
import os

from muni_lists import PREFECTURES

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")


def build_svg_and_list(muni_data):
    paths = []
    listbtns = []
    labels = []
    for m in sorted(muni_data, key=lambda x: x["code"]):
        el_id = f"m_{m['code']}"
        paths.append(
            f'<path id="{el_id}" class="muni" data-name="{m["name"]}" '
            f'data-code="{m["code"]}" d="{m["d"]}"><title>{m["name"]}</title></path>'
        )
        labels.append(
            f'<text class="label" x="{m["cx"]}" y="{m["cy"]}" '
            f'data-w="{m["cw"]}" data-h="{m["ch"]}">{m["name"]}</text>'
        )
        listbtns.append(f'<button class="listbtn" data-target="{el_id}">{m["name"]}</button>')
    return "\n".join(paths), "\n".join(labels), "".join(listbtns)


def main():
    template_path = os.path.join(BASE, "template_pref.html")
    with open(template_path, encoding="utf-8") as f:
        tpl = f.read()

    for key, pref in PREFECTURES.items():
        data_path = os.path.join(DATA_DIR, f"{key}.json")
        if not os.path.exists(data_path):
            print(f"[{key}] データが無いのでスキップ: {data_path}")
            continue
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)

        paths_svg, labels_svg, listbtns = build_svg_and_list(data["municipalities"])
        default_view = json.dumps(data["default_view"], ensure_ascii=False)

        out = (
            tpl.replace("__PREF_NAME__", pref["name"])
            .replace("__SVG_W__", str(data["svg_w"]))
            .replace("__SVG_H__", str(data["svg_h"]))
            .replace("__DEFAULT_VIEW__", default_view)
            .replace("__BASE_FONT__", str(data["base_font"]))
            .replace("__CUR_PATHS__", paths_svg)
            .replace("__CUR_LABELS__", labels_svg)
            .replace("__CUR_LIST__", listbtns)
            .replace("__MUNI_COUNT__", str(len(data["municipalities"])))
            .replace("__EXTRA_DECOR__", data.get("extra_decor", ""))
        )

        out_path = os.path.join(BASE, f"map_{key}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"[{key}] 書き出し完了: {out_path} ({len(out)} chars)")


if __name__ == "__main__":
    main()
