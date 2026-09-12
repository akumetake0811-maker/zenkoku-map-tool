# -*- coding: utf-8 -*-
"""
岩手県マップ(iwate_map_tool_old.html)に「市街地(建物用地)」の色分けレイヤーを
追加するための一回限りの変換スクリプト。

入力:
  - _gis_source_extra/landuse/extracted_*/L03-b-14_*.shp
    (国土数値情報 土地利用細分メッシュ、平成26年度、100mメッシュ、Shapefile)

出力:
  - _gis_source_extra/landuse_path.json (SVG rect要素のリスト)

注記:
  森林(0500)は岩手県内だけで170万メッシュ超あり、100mメッシュ単位で個別に
  描画するのは非現実的(ファイルサイズ・描画性能の両面で破綻する)ため、
  今回は建物用地(0700=市街地)のみを抽出する。同じ行で隣接するメッシュを
  横方向に結合(ラン・レングス結合)してrect数を大幅に削減する。
"""
import glob
import json
import os

import shapefile

BASE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE, "_gis_source_extra", "landuse")
OUT_DIR = os.path.join(BASE, "_gis_source_extra")

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

TARGET_CODE = "0700"  # 建物用地(市街地)


def proj(lon, lat):
    x = (lon - LON_MIN) * COSLAT * SCALE + MARGIN
    y = (LAT_MAX - lat) * SCALE + MARGIN
    return (x, y)


def in_bounds(x, y):
    return (-BOUNDS_MARGIN <= x <= SVG_W + BOUNDS_MARGIN) and (-BOUNDS_MARGIN <= y <= SVG_H + BOUNDS_MARGIN)


DLON = 0.00125
DLAT = 1.0 / 1200.0


def load_cells():
    """建物用地のメッシュセルを、浮動小数点誤差のない整数グリッド座標(row,col)の集合として返す。"""
    cells = set()
    for shp_path in glob.glob(os.path.join(SRC_DIR, "extracted_*", "*.shp")):
        sf = shapefile.Reader(shp_path[:-4], encoding="cp932")
        for sr in sf.iterShapeRecords():
            if sr.record[1] != TARGET_CODE:
                continue
            pts = sr.shape.points[:4]
            lons = [p[0] for p in pts]
            lats = [p[1] for p in pts]
            lon_min, lat_min = min(lons), min(lats)
            cx, cy = proj(lon_min + DLON / 2, lat_min + DLAT / 2)
            if not in_bounds(cx, cy):
                continue
            col = round(lon_min / DLON)
            row = round(lat_min / DLAT)
            cells.add((row, col))
    return cells


def merge_horizontal(cells):
    """同じ行(row)で隣接する(col連番の)セルを横方向に結合する。整数比較なので誤差なし。"""
    rows = {}
    for row, col in cells:
        rows.setdefault(row, []).append(col)
    rects = []  # (row, col_start, col_end_exclusive)
    for row, cols in rows.items():
        cols.sort()
        cur_start = cur_end = cols[0]
        for c in cols[1:]:
            if c == cur_end + 1:
                cur_end = c
            else:
                rects.append((row, cur_start, cur_end + 1))
                cur_start = cur_end = c
        rects.append((row, cur_start, cur_end + 1))
    return rects


def merge_vertical(rects):
    """横結合済みの矩形のうち、col範囲が完全一致し縦(row)に隣接するものをさらに結合する。"""
    by_cols = {}
    for row, col_start, col_end in rects:
        by_cols.setdefault((col_start, col_end), []).append(row)
    merged = []  # (row_start, row_end_exclusive, col_start, col_end)
    for (col_start, col_end), rows_list in by_cols.items():
        rows_list.sort()
        cur_start = cur_end = rows_list[0]
        for r in rows_list[1:]:
            if r == cur_end + 1:
                cur_end = r
            else:
                merged.append((cur_start, cur_end + 1, col_start, col_end))
                cur_start = cur_end = r
        merged.append((cur_start, cur_end + 1, col_start, col_end))
    return merged


def main():
    cells = load_cells()
    print(f"raw cells (in-bounds): {len(cells)}")
    h_merged = merge_horizontal(cells)
    print(f"after horizontal merge: {len(h_merged)}")
    v_merged = merge_vertical(h_merged)
    print(f"after vertical merge: {len(v_merged)}")

    pieces = []
    for row_start, row_end, col_start, col_end in v_merged:
        lon_min, lon_max = col_start * DLON, col_end * DLON
        lat_min, lat_max = row_start * DLAT, row_end * DLAT
        x0, y1 = proj(lon_min, lat_min)
        x1, y0 = proj(lon_max, lat_max)
        w, h = x1 - x0, y1 - y0
        pieces.append(f"M{x0:.0f},{y0:.0f}h{w:.0f}v{h:.0f}h{-w:.0f}Z")
    out = "".join(pieces)
    print(f"output size: {len(out)} chars")

    out_path = os.path.join(OUT_DIR, "landuse_path.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"urban_path": out, "count": len(v_merged)}, f)
    print("written to", out_path)


if __name__ == "__main__":
    main()
