# -*- coding: utf-8 -*-
"""
岩手県マップ(iwate_map_tool_old.html)に「高速道路」レイヤーを追加するための
一回限りの変換スクリプト。既に取得済みの道路タイル(削除用フォルダ待避中)から
N13_003="4"(高速自動車国道等)だけを抽出する。

入力:
  - 削除用フォルダ/_gis_source/road_tiles/extracted/N13-24_*/*.geojson

出力:
  - _gis_source_extra/expressway_path.json
"""
import glob
import json
import math
import os

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "削除用フォルダ", "_gis_source")
OUT_DIR = os.path.join(BASE, "_gis_source_extra")
os.makedirs(OUT_DIR, exist_ok=True)

with open(os.path.join(BASE, "..", "iwateMAP", "proj_params.json"), encoding="utf-8") as f:
    P = json.load(f)

LON_MIN = P["lon_min"]
LAT_MAX = P["lat_max"]
COSLAT = P["coslat"]
SCALE = P["scale"]
MARGIN = P["margin"]
SVG_W = P["SVG_W"]
SVG_H = P["SVG_H"]
BOUNDS_MARGIN = SVG_W * 0.03

EPSILON = 0.25


def proj(lon, lat):
    x = (lon - LON_MIN) * COSLAT * SCALE + MARGIN
    y = (LAT_MAX - lat) * SCALE + MARGIN
    return (round(x, 2), round(y, 2))


def in_bounds(x, y):
    return (-BOUNDS_MARGIN <= x <= SVG_W + BOUNDS_MARGIN) and (-BOUNDS_MARGIN <= y <= SVG_H + BOUNDS_MARGIN)


def clip_to_bounds(proj_pts):
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


def line_to_path_pieces(lonlat_points):
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


def build_expressway():
    pieces = []
    for path in glob.glob(os.path.join(SRC, "road_tiles", "extracted", "*", "*.geojson")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        for feat in data["features"]:
            if feat["properties"].get("N13_003") != "4":
                continue
            coords = feat["geometry"]["coordinates"]
            pieces.extend(line_to_path_pieces(coords))
    return " ".join(pieces)


def main():
    d = build_expressway()
    print(f"expressway: {len(d)} chars")
    out_path = os.path.join(OUT_DIR, "expressway_path.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"expressway": d}, f)
    print("written to", out_path)


if __name__ == "__main__":
    main()
