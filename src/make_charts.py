# -*- coding: utf-8 -*-
"""
生成 4 张图表（浅色版，适合插入 Word / 打印）
做法：复用作品集 HTML 里的绘图函数，把配色换成浅色，再交给 headless 浏览器截图
"""
import re
import os
import subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
SRC_HTML = os.path.join(BASE, "作品集-可视化与业务结论.html")
OUT_DIR = os.path.join(BASE, "charts_png")
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
os.makedirs(OUT_DIR, exist_ok=True)

src = open(SRC_HTML, encoding="utf-8").read()
script = re.search(r"<script>([\s\S]*)</script>", src).group(1)
# 只取绘图函数部分，去掉末尾的 DOM 渲染调用
core = script.split("/* ==================== 渲染 ==================== */")[0]

# —— 深色配色 -> 浅色配色 ——
core = core.replace(
    'const INK="#e2e8f0", MUTED="#94a3b8", LINE="#334155", GRID="#334155";',
    'const INK="#0f172a", MUTED="#64748b", LINE="#cbd5e1", GRID="#e2e8f0";')
core = core.replace(
    'const BLUE="#60a5fa", AMBER="#f59e0b", GREEN="#34d399", RED="#f87171", DIM="#475569";',
    'const BLUE="#3b82f6", AMBER="#d97706", GREEN="#059669", RED="#dc2626", DIM="#94a3b8";')
core = core.replace('stroke="#fff" stroke-width="2.6"', 'stroke="#0f172a" stroke-width="2.6"')  # 中位数线
core = core.replace('fill="#16213a"', 'fill="#f1f5f9"')                                        # 图例/轨道底
core = core.replace('color:#0b1220', 'color:#ffffff')                                          # 漏斗条内文字
core = core.replace('{size:10.5,fill:MUTED,anchor:"middle",weight:700,opacity:.85}',
                    '{size:10.5,fill:MUTED,anchor:"middle",weight:700,opacity:1}')

FIGS = [
    ("fig1", "图 1　各技术方向的月薪分布", "drawFig1()", 880, 472, "fig1_salary_box"),
    ("fig2", "图 2　大数据岗 vs 全体技术岗：技能要求占比差值", "drawFig2()", 880, 548, "fig2_skill_gap"),
    ("fig3", "图 3　城市机会地图：薪资水平 × 学历门槛", "drawFig3()", 880, 500, "fig3_city_bubble"),
    ("fig4", "图 4　应届生机会漏斗", "drawFig4()", 880, 356, "fig4_funnel"),
]

TPL = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  html,body{{margin:0;padding:0;background:#fff}}
  body{{width:{w}px;font-family:"Microsoft YaHei","Noto Sans SC",sans-serif}}
  .cap{{font-size:15px;font-weight:700;color:#0f172a;padding:14px 12px 2px;
        font-family:"Microsoft YaHei",sans-serif}}
  .cap i{{font-style:normal;color:#d97706;margin-right:8px}}
  svg{{display:block;width:100%;height:auto}}
</style></head><body>
<div class="cap"><i>■</i>{title}</div>
<div id="fig"></div>
<script>{core}
document.getElementById("fig").innerHTML={call};
</script></body></html>"""

for _, title, call, w, h, png in FIGS:
    path = os.path.join(OUT_DIR, png + ".html")
    open(path, "w", encoding="utf-8").write(
        TPL.format(w=w - 24, title=title, core=core, call=call))
    out_png = os.path.join(OUT_DIR, png + ".png")
    cmd = [EDGE, "--headless", "--disable-gpu", "--hide-scrollbars",
           "--force-device-scale-factor=2",
           f"--screenshot={out_png}",
           f"--window-size={w},{h + 52}",
           "file:///" + path.replace("\\", "/")]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
    ok = os.path.exists(out_png)
    size = os.path.getsize(out_png) // 1024 if ok else 0
    print(f"{'✅' if ok else '❌'} {png}: {size} KB")

print("\n输出目录:", OUT_DIR)
