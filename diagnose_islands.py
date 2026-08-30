# -*- coding: utf-8 -*-
"""県内の各市町村の「最大リング」の重心をもとに、本土/主要クラスタから
極端に離れた市町村(=離島)がどれだけ全体のbboxを間延びさせているかを診断する。
Tokyoで実施した「離島除外の要否判断」を他県にも適用するための調査用スクリプト。
"""
import json
import math
import os
import sys

from build_pref_data import get_rings, ring_area_deg

BASE = os.path.dirname(os.path.abspath(__file__))
GEOJSON_DIR = os.path.join(BASE, "geojson")


def main(key):
    pref_dir = os.path.join(GEOJSON_DIR, key)
    entries = []
    for fn in sorted(os.listdir(pref_dir)):
        if not fn.endswith(".geojson"):
            continue
        name = fn.replace(".geojson", "").rsplit("_", 1)[0]
        gj = json.load(open(os.path.join(pref_dir, fn), encoding="utf-8"))
        feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
        for feat in feats:
            rings = get_rings(feat["geometry"])
            if not rings:
                continue
            best = max(rings, key=ring_area_deg)
            lons = [p[0] for p in best]
            lats = [p[1] for p in best]
            cx, cy = sum(lons) / len(lons), sum(lats) / len(lats)
            entries.append((name, cx, cy))

    all_lon_min = min(e[1] for e in entries)
    all_lon_max = max(e[1] for e in entries)
    all_lat_min = min(e[2] for e in entries)
    all_lat_max = max(e[2] for e in entries)
    coslat = math.cos(math.radians((all_lat_min + all_lat_max) / 2))
    full_w = (all_lon_max - all_lon_min) * coslat
    full_h = all_lat_max - all_lat_min
    print(f"[{key}] 全体: 経度{all_lon_min:.2f}-{all_lon_max:.2f} 緯度{all_lat_min:.2f}-{all_lat_max:.2f} "
          f"w={full_w:.2f} h={full_h:.2f} aspect={max(full_w,full_h)/max(full_w,full_h,0.001):.2f}")
    print(f"  全体アスペクト比(長辺/短辺) = {max(full_w, full_h)/min(full_w, full_h):.2f}")

    # 中央値からの距離でソートし、外れ値(離島候補)を表示
    med_x = sorted(e[1] for e in entries)[len(entries) // 2]
    med_y = sorted(e[2] for e in entries)[len(entries) // 2]
    dists = sorted(entries, key=lambda e: -math.hypot((e[1] - med_x) * coslat, e[2] - med_y))
    print("  中央値から遠い順(上位10件, 度単位の概算距離):")
    for name, lon, lat in dists[:10]:
        d = math.hypot((lon - med_x) * coslat, lat - med_y)
        print(f"    {name}: {d:.2f}度")


if __name__ == "__main__":
    for key in sys.argv[1:]:
        main(key)
        print()
