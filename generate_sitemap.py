# -*- coding: utf-8 -*-
"""公開済みページ一覧からsitemap.xmlを生成する"""
import os

from muni_lists import PREFECTURES, REGIONS

BASE = os.path.dirname(os.path.abspath(__file__))
SITE_URL = "https://akumetake0811-maker.github.io/zenkoku-map-tool"


def main():
    urls = ["/", "/index.html", "/faq.html", "/feedback.html"]
    if os.path.exists(os.path.join(BASE, "map_nationwide.html")):
        urls.append("/map_nationwide.html")
    for key, region_name, pref_keys in REGIONS:
        page = f"region_{key}.html"
        if os.path.exists(os.path.join(BASE, page)):
            urls.append(f"/{page}")
    for key, pref in PREFECTURES.items():
        page = f"map_{key}.html"
        if os.path.exists(os.path.join(BASE, page)):
            urls.append(f"/{page}")

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        lines.append(f"  <url><loc>{SITE_URL}{u}</loc></url>")
    lines.append("</urlset>")

    out_path = os.path.join(BASE, "sitemap.xml")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"sitemap.xml 書き出し完了: {len(urls)}件")


if __name__ == "__main__":
    main()
