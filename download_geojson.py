# -*- coding: utf-8 -*-
"""geoshape.ex.nii.ac.jp から各都道府県の現行市区町村GeoJSONをダウンロードする。
政令指定都市は区ごとのデータをunionして1つの市として保存する。
"""
import json
import os
import time
import urllib.request
import urllib.error

from muni_lists import PREFECTURES

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(BASE, "geojson")

URL_TMPL = "https://geoshape.ex.nii.ac.jp/city/geojson/latest/{code}.geojson"


def fetch(code, retries=3):
    url = URL_TMPL.format(code=code)
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
                return json.loads(data.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1)
        except Exception:
            time.sleep(1)
    return None


def union_wards(ward_codes):
    from shapely.geometry import shape, mapping
    from shapely.ops import unary_union

    geoms = []
    for code in ward_codes:
        gj = fetch(code)
        if gj is None:
            print(f"    警告: 区コード{code}が取得できませんでした")
            continue
        feats = gj["features"] if gj.get("type") == "FeatureCollection" else [gj]
        for feat in feats:
            geoms.append(shape(feat["geometry"]))
    merged = unary_union(geoms)
    return mapping(merged)


def save_geojson(pref_key, name, code, geometry_or_gj):
    out_dir = os.path.join(OUT_DIR, pref_key)
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{name}_{code}.geojson")
    if isinstance(geometry_or_gj, dict) and geometry_or_gj.get("type") == "FeatureCollection":
        out = geometry_or_gj
    else:
        out = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "properties": {"N03_004": name, "N03_007": code}, "geometry": geometry_or_gj}],
        }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return path


def main(keys=None):
    targets = {k: PREFECTURES[k] for k in keys} if keys else PREFECTURES
    for key, pref in targets.items():
        if pref.get("reuse_existing"):
            print(f"[{key}] 既存データを再利用するのでスキップ")
            continue
        print(f"[{key}] {pref['name']} のダウンロード開始")
        out_dir = os.path.join(OUT_DIR, key)
        os.makedirs(out_dir, exist_ok=True)

        ok, ng = 0, []
        for name, code in pref.get("municipalities", []):
            gj = fetch(code)
            if gj is None:
                ng.append((name, code))
                continue
            save_geojson(key, name, code, gj)
            ok += 1

        for dc in pref.get("designated_cities", []):
            print(f"  政令指定都市: {dc['name']} の区データをunion中...")
            geom = union_wards(dc["wards"])
            save_geojson(key, dc["name"], dc["code"], geom)
            ok += 1

        print(f"[{key}] 完了: 成功{ok}件, 失敗{len(ng)}件")
        if ng:
            print(f"  失敗リスト: {ng}")


if __name__ == "__main__":
    import sys
    main(sys.argv[1:] or None)
