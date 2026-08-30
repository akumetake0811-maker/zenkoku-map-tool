# -*- coding: utf-8 -*-
"""data/*.json を元に index.html の都道府県カード一覧を差し込む"""
import json
import os

from muni_lists import PREFECTURES

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")


def main():
    nationwide_card = ""
    nw_path = os.path.join(DATA_DIR, "nationwide.json")
    if os.path.exists(nw_path):
        with open(nw_path, encoding="utf-8") as f:
            nw_data = json.load(f)
        nationwide_card = (
            '<a class="prefcard featured" href="map_nationwide.html">'
            '<span class="pname">全国 都道府県マップ</span>'
            f'<span class="pcount">{len(nw_data["prefectures"])}都道府県 ・ 沖縄本島は縮尺別インセット表示</span></a>'
        )

    cards = []
    for key, pref in PREFECTURES.items():
        data_path = os.path.join(DATA_DIR, f"{key}.json")
        if not os.path.exists(data_path):
            continue
        with open(data_path, encoding="utf-8") as f:
            data = json.load(f)
        count = len(data["municipalities"])
        cards.append(
            f'<a class="prefcard" href="map_{key}.html">'
            f'<span class="pname">{pref["name"]}</span>'
            f'<span class="pcount">{count}市区町村</span></a>'
        )

    template_path = os.path.join(BASE, "index_template.html")
    with open(template_path, encoding="utf-8") as f:
        html = f.read()
    html = html.replace("__NATIONWIDE_CARD__", nationwide_card)
    html = html.replace("__PREF_CARDS__", "\n    ".join(cards))
    out_path = os.path.join(BASE, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"index.html 生成完了 ({len(cards)}県)")


if __name__ == "__main__":
    main()
