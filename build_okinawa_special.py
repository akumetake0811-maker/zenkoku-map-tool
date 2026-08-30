# -*- coding: utf-8 -*-
"""沖縄県の市区町村マップだけ特別レイアウトで作る。
本島クラスタを中央に大きく描き、慶良間・久米島・宮古・八重山・大東などの
離島群は「本来の位置・縮尺」を無視して、紙の県別マップでよくあるような
枠線付きの囲み(インセット)として周囲に配置する。
"""
import json
import math
import os

from build_pref_data import get_rings, ring_area_deg, ring_area_px, ring_centroid, ring_to_path

BASE = os.path.dirname(os.path.abspath(__file__))
GEOJSON_DIR = os.path.join(BASE, "geojson", "okinawa")
DATA_DIR = os.path.join(BASE, "data")

CANVAS_W = 2200
CANVAS_H = 1700

MAIN_TARGET_MAX_DIM = 1500  # 本島クラスタの描画サイズ(このpxに長辺を合わせる)
MAIN_BOX = (0.30, 0.03, 0.78, 0.97)  # x0,y0,x1,y1 (canvas比率)

# 各インセットの配置(x0,y0,x1,y1は canvas比率, open=本島側に向く辺=枠線を引かない辺)
INSETS = [
    {"key": "kerama", "names": ["渡名喜村", "粟国村", "座間味村", "渡嘉敷村"], "box": (0.02, 0.03, 0.21, 0.23), "open": "right"},
    {"key": "iheya", "names": ["伊是名村", "伊平屋村"], "box": (0.02, 0.27, 0.21, 0.43), "open": "right"},
    {"key": "kumejima", "names": ["久米島町"], "box": (0.02, 0.47, 0.21, 0.63), "open": "right"},
    {"key": "yonaguni", "names": ["与那国町"], "box": (0.02, 0.80, 0.17, 0.97), "open": "top"},
    {"key": "taketomi", "names": ["竹富町"], "box": (0.28, 0.80, 0.46, 0.97), "open": "top"},
    {"key": "ishigaki", "names": ["石垣市"], "box": (0.62, 0.66, 0.87, 0.97), "open": "left"},
    {"key": "miyako", "names": ["多良間村", "宮古島市"], "box": (0.80, 0.36, 0.98, 0.60), "open": "left"},
    {"key": "daito", "names": ["北大東村", "南大東村"], "box": (0.78, 0.03, 0.98, 0.22), "open": "left"},
]

MAIN_EXCLUDE = set()
for ins in INSETS:
    MAIN_EXCLUDE.update(ins["names"])


def load_all():
    entries = {}
    for fn in sorted(os.listdir(GEOJSON_DIR)):
        if not fn.endswith(".geojson"):
            continue
        name = fn.replace(".geojson", "").rsplit("_", 1)[0]
        code = fn.replace(".geojson", "").rsplit("_", 1)[1]
        gj = json.load(open(os.path.join(GEOJSON_DIR, fn), encoding="utf-8"))
        feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
        rings_all = []
        for feat in feats:
            rings_all.extend(get_rings(feat["geometry"]))
        entries[name] = {"name": name, "code": code, "rings": rings_all}
    return entries


def bbox_of(rings_list):
    """各市町村について「一番大きい陸地(最大リング)」だけを使ってbboxを計算する。
    例: 久米島町は本島から250km以上離れた硫黄鳥島も行政区域に含むため、
    全リングを使うと極端に間延びしてしまう。"""
    lon_min, lon_max = 999.0, -999.0
    lat_min, lat_max = 999.0, -999.0
    for rings in rings_list:
        if not rings:
            continue
        best = max(rings, key=ring_area_deg)
        for lon, lat in best:
            lon_min = min(lon_min, lon)
            lon_max = max(lon_max, lon)
            lat_min = min(lat_min, lat)
            lat_max = max(lat_max, lat)
    return lon_min, lon_max, lat_min, lat_max


def make_local_proj(lon_min, lon_max, lat_min, lat_max, scale):
    coslat = math.cos(math.radians((lat_min + lat_max) / 2))

    def proj(lon, lat):
        x = (lon - lon_min) * coslat * scale
        y = (lat_max - lat) * scale
        return x, y

    w = (lon_max - lon_min) * coslat * scale
    h = (lat_max - lat_min) * scale
    return proj, w, h


def draw_group(muni_entries, names, proj, offset_x, offset_y, min_ring_area_px=6.0):
    """指定した市町村名リストを proj + オフセットで描画し、municipalities配列の要素を返す。
    硫黄鳥島(久米島町の飛び地)のような極端に離れた陸地を誤って描画しないよう、
    各市町村について「一番大きい陸地(最大リング)」だけを描画対象にする。
    (本図はもともと本来の縮尺・位置を無視した模式図のため、詳細な離島の
    取りこぼしよりも位置の破綻を避けることを優先する)"""
    out = []
    for name in names:
        ent = muni_entries.get(name)
        if ent is None:
            print(f"  警告: {name} のデータが見つかりません")
            continue
        rings = ent["rings"]
        if not rings:
            continue
        best_ring = max(rings, key=ring_area_deg)
        pts = [proj(lon, lat) for lon, lat in best_ring]
        shifted = [(x + offset_x, y + offset_y) for x, y in pts]
        d = ring_to_path(shifted, epsilon=0.6)
        cx, cy = ring_centroid(shifted)
        xs = [p[0] for p in shifted]
        ys = [p[1] for p in shifted]
        cw, ch = max(xs) - min(xs), max(ys) - min(ys)
        out.append({
            "name": ent["name"], "code": ent["code"], "d": d,
            "cx": round(cx, 2), "cy": round(cy, 2), "cw": round(cw, 2), "ch": round(ch, 2),
        })
    return out


def bracket_path(box_px, open_side, pad=6):
    x0, y0, x1, y1 = box_px
    x0 -= pad; y0 -= pad; x1 += pad; y1 += pad
    corners = {
        "TL": (x0, y0), "TR": (x1, y0), "BR": (x1, y1), "BL": (x0, y1),
    }
    order = ["TL", "TR", "BR", "BL", "TL"]
    # open_sideに応じて、その辺だけ結線しない(4隅を通る折れ線を2本に分割)
    side_between = {
        ("TL", "TR"): "top", ("TR", "BR"): "right", ("BR", "BL"): "bottom", ("BL", "TL"): "left",
    }
    segments = []
    cur = [corners[order[0]]]
    for i in range(len(order) - 1):
        a, b = order[i], order[i + 1]
        side = side_between[(a, b)]
        if side == open_side:
            # 開いている辺は線を引かない: 現在のセグメントをここで打ち切り、bから新規開始
            if len(cur) > 1:
                segments.append(cur)
            cur = [corners[b]]
        else:
            cur.append(corners[b])
    if len(cur) > 1:
        segments.append(cur)
    parts = []
    for seg in segments:
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in seg)
        parts.append(f'<path class="insetBracket" d="{d}"/>')
    return "".join(parts)


def main():
    muni_entries = load_all()

    # ---- 本島クラスタ ----
    main_names = [n for n in muni_entries if n not in MAIN_EXCLUDE]
    main_rings = [muni_entries[n]["rings"] for n in main_names]
    lon_min, lon_max, lat_min, lat_max = bbox_of(main_rings)
    coslat = math.cos(math.radians((lat_min + lat_max) / 2))
    w_deg = (lon_max - lon_min) * coslat
    h_deg = lat_max - lat_min
    main_box_px = (
        MAIN_BOX[0] * CANVAS_W, MAIN_BOX[1] * CANVAS_H,
        MAIN_BOX[2] * CANVAS_W, MAIN_BOX[3] * CANVAS_H,
    )
    box_w = main_box_px[2] - main_box_px[0]
    box_h = main_box_px[3] - main_box_px[1]
    scale = min(box_w / w_deg, box_h / h_deg) * 0.92
    proj_main, shape_w, shape_h = make_local_proj(lon_min, lon_max, lat_min, lat_max, scale)
    off_x = main_box_px[0] + (box_w - shape_w) / 2
    off_y = main_box_px[1] + (box_h - shape_h) / 2

    municipalities = draw_group(muni_entries, main_names, proj_main, off_x, off_y, min_ring_area_px=8.0)

    decor_parts = []

    # ---- インセット群 ----
    for ins in INSETS:
        names = ins["names"]
        rings_list = [muni_entries[n]["rings"] for n in names if n in muni_entries]
        i_lon_min, i_lon_max, i_lat_min, i_lat_max = bbox_of(rings_list)
        box_px = (
            ins["box"][0] * CANVAS_W, ins["box"][1] * CANVAS_H,
            ins["box"][2] * CANVAS_W, ins["box"][3] * CANVAS_H,
        )
        ibw = box_px[2] - box_px[0]
        ibh = box_px[3] - box_px[1]
        i_coslat = math.cos(math.radians((i_lat_min + i_lat_max) / 2))
        iw_deg = max((i_lon_max - i_lon_min) * i_coslat, 0.001)
        ih_deg = max(i_lat_max - i_lat_min, 0.001)
        i_scale = min(ibw / iw_deg, ibh / ih_deg) * 0.72
        proj_i, ishape_w, ishape_h = make_local_proj(i_lon_min, i_lon_max, i_lat_min, i_lat_max, i_scale)
        ioff_x = box_px[0] + (ibw - ishape_w) / 2
        ioff_y = box_px[1] + (ibh - ishape_h) / 2
        municipalities.extend(draw_group(muni_entries, names, proj_i, ioff_x, ioff_y, min_ring_area_px=1.0))
        decor_parts.append(bracket_path(box_px, ins["open"]))

    extra_decor = "".join(decor_parts)

    out = {
        "municipalities": municipalities,
        "svg_w": CANVAS_W,
        "svg_h": CANVAS_H,
        "default_view": {"x": 0, "y": 0, "w": CANVAS_W, "h": CANVAS_H},
        "base_font": 13.0,
        "extra_decor": extra_decor,
    }
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "okinawa.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    print(f"完了: {len(municipalities)}市町村, data/okinawa.json")


if __name__ == "__main__":
    main()
