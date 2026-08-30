# -*- coding: utf-8 -*-
"""REGIONS定義とdata/*.jsonを元に、地方ごとの都道府県選択ページ(region_{key}.html)を生成する"""
import json
import os

from muni_lists import PREFECTURES, REGIONS, region_label

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")


def main():
    template_path = os.path.join(BASE, "template_region.html")
    with open(template_path, encoding="utf-8") as f:
        tpl = f.read()

    built = 0
    for key, region_name, pref_keys in REGIONS:
        cards = []
        for pk in pref_keys:
            data_path = os.path.join(DATA_DIR, f"{pk}.json")
            if not os.path.exists(data_path):
                continue
            with open(data_path, encoding="utf-8") as f:
                data = json.load(f)
            count = len(data["municipalities"])
            pref = PREFECTURES[pk]
            cards.append(
                f'<a class="prefcard" href="map_{pk}.html">'
                f'<span class="pname">{pref["name"]}</span>'
                f'<span class="pcount">{count}市区町村</span></a>'
            )
        if not cards:
            continue
        out = (
            tpl.replace("__REGION_LABEL__", region_label(key, region_name))
            .replace("__PREF_CARDS__", "\n    ".join(cards))
        )
        out_path = os.path.join(BASE, f"region_{key}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(out)
        built += 1
        print(f"[{key}] {region_name}: {len(cards)}都道府県 -> region_{key}.html")

    print(f"完了: {built}地方ページ生成")


if __name__ == "__main__":
    main()
