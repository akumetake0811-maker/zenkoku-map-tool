# -*- coding: utf-8 -*-
"""
build_iwate_river_road_paths.pyで作った河川・道路のSVGパスを、
iwate_map_tool_old.htmlに一回だけ挿入する。パスデータが巨大なので
Editツールでの文字列置換ではなくPythonで安全に差し込む。
"""
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(BASE, "iwate_map_tool_old.html")
DATA_PATH = os.path.join(BASE, "_gis_source", "river_road_paths.json")

with open(DATA_PATH, encoding="utf-8") as f:
    rr = json.load(f)

with open(HTML_PATH, encoding="utf-8") as f:
    html = f.read()

# 1) SVGレイヤー(旧市町村レイヤーの後、計測レイヤーの前に挿入)
svg_layers = (
    '<g id="riverLayer">'
    f'<path class="riverPath river1" d="{rr["river1"]}"/>'
    f'<path class="riverPath river2" d="{rr["river2"]}"/>'
    '</g>'
    '<g id="roadLayer">'
    f'<path class="roadPath road-pref" d="{rr["road_pref"]}"/>'
    f'<path class="roadPath road-national" d="{rr["road_national"]}"/>'
    '</g>'
)
anchor_svg = '    <g id="measureLayer"></g>'
assert html.count(anchor_svg) == 1, "SVGレイヤーの挿入位置が特定できません"
html = html.replace(anchor_svg, "    " + svg_layers + "\n" + anchor_svg)

# 2) CSS(河川・道路の線スタイル。デフォルト非表示)
css_block = """
  .riverPath, .roadPath{
    fill:none;
    pointer-events:none;
    display:none;
  }
  .river1{ stroke:#1c4a63; stroke-width:1.4; }
  .river2{ stroke:#5fb3c9; stroke-width:1; }
  .road-national{ stroke:#d9432e; stroke-width:1.6; }
  .road-pref{ stroke:#c9a06b; stroke-width:1.1; }
  body.show-river1 .river1{ display:inline; }
  body.show-river2 .river2{ display:inline; }
  body.show-road-national .road-national{ display:inline; }
  body.show-road-pref .road-pref{ display:inline; }
"""
css_anchor = "  .selected{\n    filter:drop-shadow(0 0 4px #1a73e8) drop-shadow(0 0 4px #1a73e8);\n  }"
assert html.count(css_anchor) == 1, "CSSの挿入位置が特定できません"
html = html.replace(css_anchor, css_anchor + css_block)

# 3) サイドバーのチェックボックス(⑦の直前に新設)
checkbox_section = """  <div class="section">
    <h2>⑧ 河川・道路を表示</h2>
    <label class="chk"><input type="checkbox" id="toggleRiver1"> 1級河川を表示</label>
    <label class="chk"><input type="checkbox" id="toggleRiver2"> 2級河川を表示</label>
    <label class="chk"><input type="checkbox" id="toggleRoadNational"> 国道を表示</label>
    <label class="chk"><input type="checkbox" id="toggleRoadPref"> 県道を表示</label>
    <p class="hint" style="margin:8px 0 0;">国土数値情報(国土交通省)の河川・道路データを加工して表示しています。</p>
  </div>

  <div class="section">
    <h2>⑨ 作図ツールについて</h2>
"""
html_anchor = '  <div class="section">\n    <h2>⑦ 作図ツールについて</h2>\n'
assert html.count(html_anchor) == 1, "サイドバーの挿入位置が特定できません"
html = html.replace(html_anchor, checkbox_section)

# 4) JSのトグル処理(旧市町村名チェックボックスのハンドラの直後に追加)
js_block = """
  document.getElementById('toggleRiver1').addEventListener('change', function(e){
    document.body.classList.toggle('show-river1', e.target.checked);
  });
  document.getElementById('toggleRiver2').addEventListener('change', function(e){
    document.body.classList.toggle('show-river2', e.target.checked);
  });
  document.getElementById('toggleRoadNational').addEventListener('change', function(e){
    document.body.classList.toggle('show-road-national', e.target.checked);
  });
  document.getElementById('toggleRoadPref').addEventListener('change', function(e){
    document.body.classList.toggle('show-road-pref', e.target.checked);
  });
"""
js_anchor = "  document.getElementById('toggleOldLabels').addEventListener('change', function(e){\n    document.body.classList.toggle('hide-old-labels', !e.target.checked);\n  });\n"
assert html.count(js_anchor) == 1, "JSトグル処理の挿入位置が特定できません"
html = html.replace(js_anchor, js_anchor + js_block)

# 5) PNG書き出し時に、非表示レイヤーをクローンから取り除く
export_js = """
    if(!document.body.classList.contains('show-river1')){
      clone.querySelectorAll('.river1').forEach(function(p){ p.remove(); });
    }
    if(!document.body.classList.contains('show-river2')){
      clone.querySelectorAll('.river2').forEach(function(p){ p.remove(); });
    }
    if(!document.body.classList.contains('show-road-national')){
      clone.querySelectorAll('.road-national').forEach(function(p){ p.remove(); });
    }
    if(!document.body.classList.contains('show-road-pref')){
      clone.querySelectorAll('.road-pref').forEach(function(p){ p.remove(); });
    }
"""
export_anchor = "    if(document.body.classList.contains('hide-old-labels')){\n      clone.querySelectorAll('.label.old').forEach(function(t){ t.style.display = 'none'; });\n    }\n"
assert html.count(export_anchor) == 1, "書き出し処理の挿入位置が特定できません"
html = html.replace(export_anchor, export_anchor + export_js)

# 6) 書き出し用の埋め込みCSSにも河川・道路のスタイルを追加(exportクローンは独立SVGなので必須)
export_style_anchor = "'.pinLabel{font-family:\"Hiragino Maru Gothic ProN\",\"BIZ UDPGothic\",\"Yu Gothic\",\"Meiryo\",sans-serif;font-size:15px;font-weight:600;fill:#7a2418;text-anchor:middle;paint-order:stroke;stroke:#fdfcf8;stroke-width:3px;stroke-linejoin:round;}';"
export_style_addition = (
    "'.pinLabel{font-family:\"Hiragino Maru Gothic ProN\",\"BIZ UDPGothic\",\"Yu Gothic\",\"Meiryo\",sans-serif;font-size:15px;font-weight:600;fill:#7a2418;text-anchor:middle;paint-order:stroke;stroke:#fdfcf8;stroke-width:3px;stroke-linejoin:round;}' +\n"
    "      '.river1{fill:none;stroke:#1c4a63;stroke-width:1.4;}' +\n"
    "      '.river2{fill:none;stroke:#5fb3c9;stroke-width:1;}' +\n"
    "      '.road-national{fill:none;stroke:#d9432e;stroke-width:1.6;}' +\n"
    "      '.road-pref{fill:none;stroke:#c9a06b;stroke-width:1.1;}';"
)
assert html.count(export_style_anchor) == 1, "書き出し用CSSの挿入位置が特定できません"
html = html.replace(export_style_anchor, export_style_addition)

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print("done. new size:", len(html), "chars")
