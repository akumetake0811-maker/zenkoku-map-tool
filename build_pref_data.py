# -*- coding: utf-8 -*-
"""都道府県ごとに geojson/{pref}/*.geojson を読み込み、
SVG path文字列・ラベル座標・投影パラメータを計算して data/{pref}.json に書き出す。

地図の「枠」は各市町村の一番大きい陸地(本土や主島)を基準に決め、
極端に遠い離島(例: 東京都小笠原村に属する沖ノ鳥島・南鳥島)は
枠の外になっても構造上は保持する(ズームすれば見える)。
"""
import json
import math
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
GEOJSON_DIR = os.path.join(BASE, "geojson")
DATA_DIR = os.path.join(BASE, "data")

MARGIN = 20
TARGET_MAX_DIM = 2800  # 長辺をこのpxに合わせる(岩手版の最終解像度=2780に合わせて底上げ)

MIN_RING_AREA_PX = 9.7  # このpx^2未満の断片(ノイズ)は描画から除外。ただし各市町村の最大リングは必ず残す(解像度アップ分だけ閾値も比例拡大)


def walk_points(coords):
    if isinstance(coords[0], (int, float)):
        yield coords
    else:
        for c in coords:
            yield from walk_points(c)


def ring_area_deg(ring):
    lat0 = sum(p[1] for p in ring) / len(ring)
    coslat = math.cos(math.radians(lat0))
    pts = [(p[0] * coslat, p[1]) for p in ring]
    a = 0.0
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def get_rings(geom):
    """(exterior_ring, is_hole) のリストを返す。holeは除外して外周だけ返す"""
    gtype = geom["type"]
    polys = geom["coordinates"] if gtype == "MultiPolygon" else [geom["coordinates"]]
    return [poly[0] for poly in polys]  # 各ポリゴンの外周(穴は無視)


def compute_core_bbox(pref_dir):
    """各市町村ファイルについて「一番面積が大きい外周リング」だけを使ってbboxを計算する"""
    lon_min, lon_max = 999.0, -999.0
    lat_min, lat_max = 999.0, -999.0
    for fn in sorted(os.listdir(pref_dir)):
        if not fn.endswith(".geojson"):
            continue
        gj = json.load(open(os.path.join(pref_dir, fn), encoding="utf-8"))
        feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
        for feat in feats:
            rings = get_rings(feat["geometry"])
            if not rings:
                continue
            best_ring = max(rings, key=ring_area_deg)
            for lon, lat in best_ring:
                lon_min = min(lon_min, lon)
                lon_max = max(lon_max, lon)
                lat_min = min(lat_min, lat)
                lat_max = max(lat_max, lat)
    return lon_min, lon_max, lat_min, lat_max


def make_proj(lon_min, lon_max, lat_min, lat_max):
    coslat = math.cos(math.radians((lat_min + lat_max) / 2))
    w_deg = (lon_max - lon_min) * coslat
    h_deg = lat_max - lat_min
    if w_deg >= h_deg:
        scale = (TARGET_MAX_DIM - 2 * MARGIN) / w_deg
    else:
        scale = (TARGET_MAX_DIM - 2 * MARGIN) / h_deg
    svg_w = w_deg * scale + 2 * MARGIN
    svg_h = h_deg * scale + 2 * MARGIN

    def proj(lon, lat):
        x = (lon - lon_min) * coslat * scale + MARGIN
        y = (lat_max - lat) * scale + MARGIN
        return (round(x, 2), round(y, 2))

    return proj, svg_w, svg_h


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
    return [points[0], points[-1]]


def ring_area_px(pts):
    a = 0.0
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2


def ring_centroid(pts):
    a = cx = cy = 0.0
    for i in range(len(pts) - 1):
        x1, y1 = pts[i]
        x2, y2 = pts[i + 1]
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    a /= 2
    if a == 0:
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    return (cx / (6 * a), cy / (6 * a))


def ring_to_path(pts, epsilon=1.2):
    dedup = [pts[0]]
    for p in pts[1:]:
        if p != dedup[-1]:
            dedup.append(p)
    simplified = douglas_peucker(dedup, epsilon)
    if len(simplified) < 3:
        simplified = dedup
    return "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in simplified) + " Z"


def geometry_to_path_and_label(geom, proj):
    rings = get_rings(geom)
    if not rings:
        return "", (0.0, 0.0)
    # 投影後の面積で「一番大きいリング」を決める(ラベル位置・ノイズ除外の免除対象)
    projected = [[proj(lon, lat) for lon, lat in ring] for ring in rings]
    areas = [ring_area_px(p) for p in projected]
    biggest_idx = max(range(len(areas)), key=lambda i: areas[i])

    parts = []
    for i, pts in enumerate(projected):
        if i != biggest_idx and areas[i] < MIN_RING_AREA_PX:
            continue  # ノイズ的な小断片は除外(ただし最大リングは必ず残す)
        parts.append(ring_to_path(pts))

    cx, cy = ring_centroid(projected[biggest_idx])
    core_xs = [p[0] for p in projected[biggest_idx]]
    core_ys = [p[1] for p in projected[biggest_idx]]
    core_bbox = (min(core_xs), min(core_ys), max(core_xs), max(core_ys))
    return " ".join(parts), (round(cx, 2), round(cy, 2)), core_bbox


def compute_default_view(municipalities, svg_w, svg_h):
    """本土から極端に離れた離島(例: 東京都小笠原村の沖ノ鳥島・南鳥島)が初期表示を
    間延びさせないよう、主要クラスタだけに絞った初期viewBoxを計算する。
    沖縄のように離島群自体が県の主要な構成要素で、全体の縦横比がそこまで
    極端でない場合は絞り込まず全域を初期表示にする(実在の人口集積地を
    デフォルトで見えなくしないため)。"""
    aspect = max(svg_w, svg_h) / max(1.0, min(svg_w, svg_h))
    if aspect < 4.0:
        return {"x": 0, "y": 0, "w": svg_w, "h": svg_h}

    pts = [m for m in municipalities if m["_core_bbox"] is not None]
    if len(pts) <= 1:
        return {"x": 0, "y": 0, "w": svg_w, "h": svg_h}

    xs_c = sorted(m["cx"] for m in pts)
    ys_c = sorted(m["cy"] for m in pts)
    med_x = xs_c[len(xs_c) // 2]
    med_y = ys_c[len(ys_c) // 2]

    dists = sorted(math.hypot(m["cx"] - med_x, m["cy"] - med_y) for m in pts)
    radius = dists[min(int(len(dists) * 0.85), len(dists) - 1)]
    if radius <= 0:
        radius = max(svg_w, svg_h) / 2

    included = [m for m in pts if math.hypot(m["cx"] - med_x, m["cy"] - med_y) <= radius]
    x0 = min(m["_core_bbox"][0] for m in included)
    y0 = min(m["_core_bbox"][1] for m in included)
    x1 = max(m["_core_bbox"][2] for m in included)
    y1 = max(m["_core_bbox"][3] for m in included)
    pad = max(x1 - x0, y1 - y0) * 0.08 + 20
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(svg_w, x1 + pad)
    y1 = min(svg_h, y1 + pad)
    w, h = x1 - x0, y1 - y0

    # 単一クラスタの県(絞り込んでもほぼ全域)ならそのまま全域を使う
    if w > svg_w * 0.9 and h > svg_h * 0.9:
        return {"x": 0, "y": 0, "w": svg_w, "h": svg_h}
    return {"x": round(x0, 2), "y": round(y0, 2), "w": round(w, 2), "h": round(h, 2)}


def build_pref(key):
    pref_dir = os.path.join(GEOJSON_DIR, key)
    print(f"[{key}] bbox計算中...")
    lon_min, lon_max, lat_min, lat_max = compute_core_bbox(pref_dir)
    proj, svg_w, svg_h = make_proj(lon_min, lon_max, lat_min, lat_max)
    print(f"[{key}] svg_w={svg_w:.0f} svg_h={svg_h:.0f}")

    municipalities = []
    for fn in sorted(os.listdir(pref_dir)):
        if not fn.endswith(".geojson"):
            continue
        name_full = fn.replace(".geojson", "")
        parts = name_full.rsplit("_", 1)
        disp_name, code = parts[0], parts[1] if len(parts) > 1 else ""
        gj = json.load(open(os.path.join(pref_dir, fn), encoding="utf-8"))
        feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
        d_parts = []
        label = (0.0, 0.0)
        core_bbox = None
        for feat in feats:
            d, (cx, cy), bbox = geometry_to_path_and_label(feat["geometry"], proj)
            d_parts.append(d)
            # 複数featureある場合は一番大きい塊のラベル・bboxを採用(通常は1feature)
            label = (cx, cy)
            core_bbox = bbox
        cw = core_bbox[2] - core_bbox[0] if core_bbox else 0
        ch = core_bbox[3] - core_bbox[1] if core_bbox else 0
        municipalities.append({
            "name": disp_name, "code": code, "d": " ".join(d_parts),
            "cx": label[0], "cy": label[1], "cw": round(cw, 2), "ch": round(ch, 2),
            "_core_bbox": core_bbox,
        })

    default_view = compute_default_view(municipalities, svg_w, svg_h)
    for m in municipalities:
        del m["_core_bbox"]

    # ラベルの目標フォントサイズは「画面上でのpx」なので、ズームのたびに
    # updateLabels()側で動的に再計算される(SVG font-sizeはviewBoxに追従するため)。
    # そのため県ごとの初期表示幅で逆算する必要はなく、全県共通の固定値でよい。
    base_font = 15.0

    out = {
        "municipalities": municipalities,
        "svg_w": round(svg_w, 2),
        "svg_h": round(svg_h, 2),
        "default_view": default_view,
        "base_font": base_font,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, f"{key}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    total_chars = sum(len(m["d"]) for m in municipalities)
    print(f"[{key}] 完了: {len(municipalities)}市町村, d文字数合計={total_chars}, 書き込み先={out_path}")


if __name__ == "__main__":
    keys = sys.argv[1:] or ["iwate", "tokyo", "kanagawa", "okinawa"]
    for k in keys:
        build_pref(k)
