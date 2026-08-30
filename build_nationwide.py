# -*- coding: utf-8 -*-
"""47都道府県ver(全国1枚のマップ)を作る。
geojson/nationwide/japan_prefectures_raw.geojson (dataofjapan/land) を元に、
- 本土(沖縄以外46都道府県)は通常の等長方形図法で1枚に投影
- 沖縄県は縦に伸びすぎるのを避けるため、別スケールで右下の別枠(インセット)に配置
- 東京都は離島(伊豆諸島・小笠原諸島)がバウンディングボックスを歪めるため、
  本土(最大リング)のみを描画対象にする(市町村ver東京マップと同じ方針)
"""
import json
import math
import os

from build_pref_data import (
    get_rings,
    ring_area_px,
    ring_centroid,
    ring_to_path,
)

BASE = os.path.dirname(os.path.abspath(__file__))
RAW_PATH = os.path.join(BASE, "geojson", "nationwide", "japan_prefectures_raw.geojson")
DATA_DIR = os.path.join(BASE, "data")

MARGIN = 20
MAINLAND_TARGET_MAX_DIM = 5200  # 海岸線のカクカク感を減らすためさらに高解像度化
MIN_RING_AREA_PX = 30.0  # 解像度アップ分だけノイズ除外の面積閾値も比例拡大

PREF_NAMES = {
    1: "北海道", 2: "青森県", 3: "岩手県", 4: "宮城県", 5: "秋田県", 6: "山形県", 7: "福島県",
    8: "茨城県", 9: "栃木県", 10: "群馬県", 11: "埼玉県", 12: "千葉県", 13: "東京都", 14: "神奈川県",
    15: "新潟県", 16: "富山県", 17: "石川県", 18: "福井県", 19: "山梨県", 20: "長野県", 21: "岐阜県",
    22: "静岡県", 23: "愛知県", 24: "三重県", 25: "滋賀県", 26: "京都府", 27: "大阪府", 28: "兵庫県",
    29: "奈良県", 30: "和歌山県", 31: "鳥取県", 32: "島根県", 33: "岡山県", 34: "広島県", 35: "山口県",
    36: "徳島県", 37: "香川県", 38: "愛媛県", 39: "高知県", 40: "福岡県", 41: "佐賀県", 42: "長崎県",
    43: "熊本県", 44: "大分県", 45: "宮崎県", 46: "鹿児島県", 47: "沖縄県",
}


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


def make_proj(lon_min, lon_max, lat_min, lat_max, target_max_dim, margin=MARGIN):
    coslat = math.cos(math.radians((lat_min + lat_max) / 2))
    w_deg = (lon_max - lon_min) * coslat
    h_deg = lat_max - lat_min
    scale = (target_max_dim - 2 * margin) / (w_deg if w_deg >= h_deg else h_deg)
    svg_w = w_deg * scale + 2 * margin
    svg_h = h_deg * scale + 2 * margin

    def proj(lon, lat):
        x = (lon - lon_min) * coslat * scale + margin
        y = (lat_max - lat) * scale + margin
        return (x, y)

    return proj, svg_w, svg_h, scale


def build_feature_paths(rings, proj, keep_only_largest=False):
    """ringsを投影・簡略化してSVGパス片のリストと、最大リングの重心・core_bboxを返す"""
    projected = [[proj(lon, lat) for lon, lat in ring] for ring in rings]
    areas = [ring_area_px(p) for p in projected]
    biggest_idx = max(range(len(areas)), key=lambda i: areas[i])

    parts = []
    for i, pts in enumerate(projected):
        if keep_only_largest and i != biggest_idx:
            continue
        if i != biggest_idx and areas[i] < MIN_RING_AREA_PX:
            continue
        parts.append(ring_to_path(pts))

    cx, cy = ring_centroid(projected[biggest_idx])
    xs = [p[0] for p in projected[biggest_idx]]
    ys = [p[1] for p in projected[biggest_idx]]
    core_bbox = (min(xs), min(ys), max(xs), max(ys))
    return " ".join(parts), (round(cx, 2), round(cy, 2)), core_bbox


def main():
    with open(RAW_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    mainland_feats = []
    okinawa_feat = None
    for feat in raw["features"]:
        pid = feat["properties"]["id"]
        if pid == 47:
            okinawa_feat = feat
        else:
            mainland_feats.append((pid, feat))

    # --- 本土(沖縄以外)のbbox計算。東京都だけは最大リング(本土)のみ採用 ---
    lon_min, lon_max, lat_min, lat_max = 999.0, -999.0, 999.0, -999.0
    mainland_rings_by_id = {}
    for pid, feat in mainland_feats:
        rings = get_rings(feat["geometry"])
        if pid == 13:
            best = max(rings, key=ring_area_deg)
            rings = [best]
        mainland_rings_by_id[pid] = rings
        for ring in rings:
            for lon, lat in ring:
                lon_min = min(lon_min, lon)
                lon_max = max(lon_max, lon)
                lat_min = min(lat_min, lat)
                lat_max = max(lat_max, lat)

    proj, svg_w, svg_h, scale = make_proj(lon_min, lon_max, lat_min, lat_max, MAINLAND_TARGET_MAX_DIM)
    print(f"[本土] svg_w={svg_w:.0f} svg_h={svg_h:.0f} scale={scale:.2f}px/deg")

    prefectures = []
    for pid, rings in mainland_rings_by_id.items():
        d, (cx, cy), core_bbox = build_feature_paths(rings, proj, keep_only_largest=(pid == 13))
        cw = round(core_bbox[2] - core_bbox[0], 2)
        ch = round(core_bbox[3] - core_bbox[1], 2)
        prefectures.append({
            "name": PREF_NAMES[pid], "code": f"{pid:02d}", "d": d,
            "cx": cx, "cy": cy, "cw": cw, "ch": ch,
        })

    # --- 沖縄県: 本島(最大リング)のみを、本土と同じ縮尺(scale)のまま右下へ平行移動して配置 ---
    # 宮古島・八重山諸島まで含めると本島側が相対的に小さくなりすぎるため、
    # 東京都の離島除外と同じ方針で本島だけを描画する。縮尺は他の都道府県と揃えるため、
    # 独自のフィッティングはせず本土と同じscale/coslatをそのまま使う。
    coslat_main = math.cos(math.radians((lat_min + lat_max) / 2))
    oki_rings_all = get_rings(okinawa_feat["geometry"])
    oki_main_ring = max(oki_rings_all, key=ring_area_deg)
    oki_lons = [lon for lon, lat in oki_main_ring]
    oki_lats = [lat for lon, lat in oki_main_ring]
    oki_lon_min, oki_lon_max = min(oki_lons), max(oki_lons)
    oki_lat_min, oki_lat_max = min(oki_lats), max(oki_lats)
    oki_w = (oki_lon_max - oki_lon_min) * coslat_main * scale
    oki_h = (oki_lat_max - oki_lat_min) * scale

    # 右下の角ぎりぎりではなく、本土(九州)にもう少し近い位置へ寄せて配置する
    inset_x0 = svg_w * 0.63
    inset_y0 = svg_h * 0.80

    def oki_proj(lon, lat):
        x = (lon - oki_lon_min) * coslat_main * scale + inset_x0
        y = (oki_lat_max - lat) * scale + inset_y0
        return (x, y)

    d, (cx, cy), core_bbox = build_feature_paths([oki_main_ring], oki_proj, keep_only_largest=False)
    cw = round(core_bbox[2] - core_bbox[0], 2)
    ch = round(core_bbox[3] - core_bbox[1], 2)
    prefectures.append({
        "name": "沖縄県", "code": "47", "d": d,
        "cx": cx, "cy": cy, "cw": cw, "ch": ch,
    })
    prefectures.sort(key=lambda p: p["code"])

    # 枠は「箱」ではなく、切り取り線のようなくの字(角度付き)の折れ線にする。
    # 頂点(elbow)から上に横線、左下に斜め線を伸ばす。
    elbow = (round(inset_x0 - 14, 2), round(inset_y0 - 14, 2))
    top_right = (round(inset_x0 + oki_w + 50, 2), round(inset_y0 - 14, 2))
    diag_end = (round(inset_x0 - 70, 2), round(inset_y0 + oki_h * 0.6, 2))
    inset_cut_line = [diag_end, elbow, top_right]

    out = {
        "prefectures": prefectures,
        "svg_w": round(svg_w, 2),
        "svg_h": round(svg_h, 2),
        "inset_cut_line": inset_cut_line,
        "inset_label_pos": {"x": elbow[0] + 4, "y": elbow[1] - 6},
        "base_font": 15.0,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = os.path.join(DATA_DIR, "nationwide.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    total_chars = sum(len(p["d"]) for p in prefectures)
    print(f"完了: {len(prefectures)}都道府県, d文字数合計={total_chars}, 書き込み先={out_path}")


if __name__ == "__main__":
    main()
