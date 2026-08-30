# -*- coding: utf-8 -*-
"""new_prefectures.json をPythonリテラルに変換し、muni_lists.pyの末尾に
残り40道府県分のPREFECTURESエントリとREGIONS定義を追記する使い捨てスクリプト。
"""
import json

with open("new_prefectures.json", encoding="utf-8") as f:
    data = json.load(f)

# 順序を都道府県コード順に整列
order = sorted(data.keys(), key=lambda k: data[k]["pref_code"])

lines = []
for key in order:
    e = data[key]
    lines.append(f'    "{key}": {{')
    lines.append(f'        "name": "{e["name"]}",')
    lines.append(f'        "pref_code": "{e["pref_code"]}",')
    lines.append('        "municipalities": [')
    munis = e["municipalities"]
    for i in range(0, len(munis), 4):
        chunk = munis[i:i + 4]
        row = ", ".join(f'("{n}", "{c}")' for n, c in chunk)
        lines.append(f'            {row},')
    lines.append('        ],')
    if e.get("designated_cities"):
        lines.append('        "designated_cities": [')
        for dc in e["designated_cities"]:
            wards_str = ", ".join(f'"{w}"' for w in dc["wards"])
            lines.append('            {')
            lines.append(f'                "name": "{dc["name"]}", "code": "{dc["code"]}",')
            lines.append(f'                "wards": [{wards_str}],')
            lines.append('            },')
        lines.append('        ],')
    lines.append('    },')

block = "\n".join(lines)

REGIONS_BLOCK = '''
REGIONS = [
    ("hokkaido", "北海道", ["hokkaido"]),
    ("tohoku", "東北", ["aomori", "iwate", "miyagi", "akita", "yamagata", "fukushima"]),
    ("kanto", "関東", ["ibaraki", "tochigi", "gunma", "saitama", "chiba", "tokyo", "kanagawa"]),
    ("chubu", "中部", ["niigata", "toyama", "ishikawa", "fukui", "yamanashi", "nagano", "gifu", "shizuoka", "aichi"]),
    ("kinki", "近畿", ["mie", "shiga", "kyoto", "osaka", "hyogo", "nara", "wakayama"]),
    ("chugoku", "中国", ["tottori", "shimane", "okayama", "hiroshima", "yamaguchi"]),
    ("shikoku", "四国", ["tokushima", "kagawa", "ehime", "kochi"]),
    ("kyushu_okinawa", "九州・沖縄", ["fukuoka", "saga", "nagasaki", "kumamoto", "oita", "miyazaki", "kagoshima", "okinawa"]),
]
'''

with open("muni_lists.py", encoding="utf-8") as f:
    content = f.read()

marker = "\nKANTO_5 = "
idx = content.index(marker)
# 既存の "}\n\nKANTO_5 = ..." の "}" (PREFECTURES辞書の閉じ括弧)の直前に追記
close_brace_idx = content.rindex("}", 0, idx)
new_content = (
    content[:close_brace_idx]
    + block + "\n"
    + content[close_brace_idx:]
)
new_content += REGIONS_BLOCK

with open("muni_lists.py", "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"muni_lists.py 更新完了: {len(order)}道府県分を追記")
