# -*- coding: utf-8 -*-
"""
岩手県マップ(iwate_map_tool_old.html)に「1級・2級河川」「国道・県道」レイヤーを
追加するための一回限りの変換スクリプト。

入力:
  - _gis_source/river_extracted/W05-07_03-g_Stream.* (国土数値情報 河川データ、岩手県、Shapefile)
  - _gis_source/road_tiles/extracted/N13-24_*/*.geojson (国土数値情報 道路データ、1次メッシュ単位、GeoJSON)

出力:
  - _gis_source/river_road_paths.json (SVG path文字列。iwate_map_tool_old.htmlへの埋め込み用)

岩手県マップ本体と同じ投影式(proj_params.json)でlon/lat→SVG座標に変換し、
Douglas-Peuckerで間引いてからpathデータにする。
"""
import glob
import json
import math
import os

import shapefile

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "_gis_source")

with open(os.path.join(BASE, "..", "iwateMAP", "proj_params.json"), encoding="utf-8") as f:
    P = json.load(f)

LON_MIN = P["lon_min"]
LAT_MAX = P["lat_max"]
COSLAT = P["coslat"]
SCALE = P["scale"]
MARGIN = P["margin"]
SVG_W = P["SVG_W"]
SVG_H = P["SVG_H"]
BOUNDS_MARGIN = SVG_W * 0.03  # 県境ぴったりで切れると不自然なので、ごく少しだけはみ出しを許容


def proj(lon, lat):
    x = (lon - LON_MIN) * COSLAT * SCALE + MARGIN
    y = (LAT_MAX - lat) * SCALE + MARGIN
    return (round(x, 2), round(y, 2))


def in_bounds(x, y):
    return (-BOUNDS_MARGIN <= x <= SVG_W + BOUNDS_MARGIN) and (-BOUNDS_MARGIN <= y <= SVG_H + BOUNDS_MARGIN)


def clip_to_bounds(proj_pts):
    """bbox内にある連続区間だけを取り出す(範囲外に出たり戻ったりする場合は複数区間に分割)。"""
    segments = []
    current = []
    for p in proj_pts:
        if in_bounds(*p):
            current.append(p)
        else:
            if len(current) >= 2:
                segments.append(current)
            current = []
    if len(current) >= 2:
        segments.append(current)
    return segments


def perp_dist(pt, a, b):
    (x, y), (ax, ay), (bx, by) = pt, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(x - ax, y - ay)
    t = ((x - ax) * dx + (y - ay) * dy) / (dx * dx + dy * dy)
    px, py = ax + t * dx, ay + t * dy
    return math.hypot(x - px, y - py)


def douglas_peucker(points, epsilon):
    if len(points) < 3:
        return points
    dmax, idx = 0.0, 0
    for i in range(1, len(points) - 1):
        d = perp_dist(points[i], points[0], points[-1])
        if d > dmax:
            dmax, idx = d, i
    if dmax > epsilon:
        left = douglas_peucker(points[: idx + 1], epsilon)
        right = douglas_peucker(points[idx:], epsilon)
        return left[:-1] + right
    else:
        return [points[0], points[-1]]


EPSILON = 1.8  # 川・道路は輪郭線ほどの精度が要らないので少し粗めに間引く


def line_to_path_pieces(lonlat_points):
    """1本の線を投影し、地図の範囲内にある区間だけを簡略化してSVGパスのパーツ群を返す。"""
    proj_pts = [proj(lon, lat) for lon, lat in lonlat_points]
    dedup = [proj_pts[0]]
    for p in proj_pts[1:]:
        if p != dedup[-1]:
            dedup.append(p)
    pieces = []
    for seg in clip_to_bounds(dedup):
        simplified = douglas_peucker(seg, EPSILON) if len(seg) > 2 else seg
        if len(simplified) >= 2:
            pieces.append("M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in simplified))
    return pieces


def build_rivers():
    sf = shapefile.Reader(os.path.join(SRC, "river_extracted", "W05-07_03-g_Stream"), encoding="cp932")
    # 区間種別: 1=1級直轄, 2=1級指定, 3=2級河川, 5/6/7=それぞれ+湖沼区間
    class1_codes = {"1", "2", "5", "6"}
    class2_codes = {"3", "7"}
    pieces1, pieces2 = [], []
    for sr in sf.iterShapeRecords():
        cls = sr.record["W05_003"]
        if cls not in class1_codes and cls not in class2_codes:
            continue
        pieces = line_to_path_pieces(sr.shape.points)
        if cls in class1_codes:
            pieces1.extend(pieces)
        else:
            pieces2.extend(pieces)
    return {
        "river1": " ".join(pieces1),
        "river2": " ".join(pieces2),
    }


def build_roads():
    pieces_national, pieces_pref = [], []
    for path in glob.glob(os.path.join(SRC, "road_tiles", "extracted", "*", "*.geojson")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for feat in data["features"]:
            cls = feat["properties"].get("N13_003")
            if cls not in ("1", "2"):
                continue
            coords = feat["geometry"]["coordinates"]
            pieces = line_to_path_pieces(coords)
            if cls == "1":
                pieces_national.extend(pieces)
            else:
                pieces_pref.extend(pieces)
    return {
        "road_national": " ".join(pieces_national),
        "road_pref": " ".join(pieces_pref),
    }


def main():
    rivers = build_rivers()
    roads = build_roads()
    out = {**rivers, **roads}
    for k, v in out.items():
        print(f"{k}: {len(v)} chars")
    out_path = os.path.join(SRC, "river_road_paths.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f)
    print("written to", out_path)


if __name__ == "__main__":
    main()
