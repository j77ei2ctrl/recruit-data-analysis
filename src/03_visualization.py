# -*- coding: utf-8 -*-
"""
================================================================================
Step 3-2  可视化（matplotlib）
项目：大数据岗位招聘信息数据分析
输入：charts_data.json（由 03_charts_data.py 生成）
输出：fig1_salary_box.png / fig2_skill_gap.png / fig3_city_bubble.png / fig4_funnel.png
================================================================================
运行前先装库：
    pip install matplotlib

路径约定：charts_data.json 位于 data/，输出 PNG 落在 images/（均基于仓库根目录）
================================================================================
"""

import json
import os
import matplotlib
matplotlib.use("Agg")                       # 无界面后端，避免弹窗
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
IMG_DIR = os.path.join(ROOT, "images")
from matplotlib import font_manager
from matplotlib.patches import Rectangle

# ============================ 中文显示设置 ============================
# 这是 matplotlib 画中文最容易踩的坑：默认字体不含中文字形，会显示成方框口口口
def setup_chinese_font():
    """按优先级挑一个可用的中文字体；都找不到时直接加载系统字体文件"""
    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC",
                  "Source Han Sans SC", "PingFang SC", "WenQuanYi Micro Hei"]
    installed = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in installed:
            return name
    # 兜底：直接注册字体文件（Windows 常见路径）
    for path in [r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf",
                 r"C:\Windows\Fonts\msyhbd.ttc"]:
        if os.path.exists(path):
            font_manager.fontManager.addfont(path)
            return font_manager.FontProperties(fname=path).get_name()
    print("⚠️ 未找到中文字体，中文可能显示为方框。请安装 SimHei 或 Microsoft YaHei")
    return "DejaVu Sans"

FONT = setup_chinese_font()
plt.rcParams["font.sans-serif"] = [FONT, "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False   # 修复负号显示成方块的问题
print(f"使用字体：{FONT}")

# ============================ 配色与主题 ============================
DARK = True        # True = 深色（配合作品集页面）；改成 False 得到白底图（适合放 Word/PPT）

if DARK:
    BG, PANEL, INK, MUTED = "#0f172a", "#1e293b", "#e2e8f0", "#94a3b8"
    GRID, LINE = "#334155", "#475569"
else:
    BG, PANEL, INK, MUTED = "#ffffff", "#f8fafc", "#0f172a", "#64748b"
    GRID, LINE = "#e2e8f0", "#cbd5e1"

C_BLUE = "#60a5fa"        # 常规系列
C_AMBER = "#f59e0b"       # 高亮系列（大数据相关）
C_GREEN = "#34d399"
C_RED = "#f87171"
C_DIM = "#475569"

def style_ax(ax, title="", xlabel="", ylabel=""):
    """统一的坐标轴样式"""
    ax.set_facecolor(PANEL)
    ax.figure.patch.set_facecolor(BG)
    for spine in ax.spines.values():
        spine.set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=10)
    ax.grid(True, color=GRID, alpha=0.45, linewidth=0.8)
    ax.set_axisbelow(True)
    if title:
        ax.set_title(title, color=INK, fontsize=15, fontweight="bold", pad=14)
    if xlabel:
        ax.set_xlabel(xlabel, color=MUTED, fontsize=11)
    if ylabel:
        ax.set_ylabel(ylabel, color=MUTED, fontsize=11)

D = json.load(open(os.path.join(DATA_DIR, "charts_data.json"), encoding="utf-8"))


# ============================================================================
# 图 1｜各岗位方向薪资分布（箱线图）
# 讲什么：方向选择直接决定薪资中枢；同时展示"离散度"——同样的方向内部差距有多大
# ============================================================================
fig, ax = plt.subplots(figsize=(11, 6), dpi=150)
box = D["chart1_salary_box"]
labels = [f"{b['name']}\n(n={b['n']})" for b in box]

# ⚠️ 关键写法：用 ax.bxp() 传入「已算好的统计量」
#    如果直接 ax.boxplot([[low,q1,med,q3,high], ...])，matplotlib 会把这 5 个数
#    当成 5 条原始数据重新算分位数，画出来的图是错的。这是新手常见陷阱。
stats = [{
    "med": b["median"], "q1": b["q1"], "q3": b["q3"],
    "whislo": b["low"], "whishi": b["high"],
    "fliers": b["outliers"], "mean": b["mean"],
} for b in box]

bp = ax.bxp(
    stats, positions=range(1, len(box) + 1), widths=0.55,
    patch_artist=True, showmeans=True,
    meanprops=dict(marker="D", markerfacecolor=C_RED, markeredgecolor=C_RED, markersize=6),
    medianprops=dict(color=INK, linewidth=2),
    whiskerprops=dict(color=LINE, linewidth=1.4),
    capprops=dict(color=LINE, linewidth=1.4),
    flierprops=dict(marker="o", markerfacecolor=C_DIM, markeredgecolor="none", markersize=3, alpha=.5),
)
for i, patch in enumerate(bp["boxes"]):
    is_bd = "大数据" in box[i]["name"]
    patch.set_facecolor(C_AMBER if is_bd else C_BLUE)
    patch.set_alpha(0.85 if is_bd else 0.55)
    patch.set_edgecolor(C_AMBER if is_bd else C_BLUE)

ax.set_xticks(range(1, len(labels) + 1))
ax.set_xticklabels(labels, color=INK, fontsize=9.5)

# 标注中位数
for i, b in enumerate(box, start=1):
    ax.annotate(f"{b['median']:.1f}K", (i, b["median"]), textcoords="offset points",
                xytext=(0, 10), ha="center", color=INK, fontsize=10, fontweight="bold")

style_ax(ax, "图1 · 各技术方向月薪分布（箱线图）",
         ylabel="月薪（K/月）")
ax.text(0.99, 0.02, "箱体 = 中间 50% 的岗位；白线 = 中位数；红色菱形 = 均值",
        transform=ax.transAxes, ha="right", color=MUTED, fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, "fig1_salary_box.png"), facecolor=BG, bbox_inches="tight")
plt.close()
print("✅ 图1 已保存")


# ============================================================================
# 图 2｜技能要求差值：大数据岗 vs 全体技术岗（横向分组条形图）
# 讲什么：差值才是区分度。差值大的必须学，差值小的属于"人人都要"的通用项
# ============================================================================
fig, ax = plt.subplots(figsize=(11, 7), dpi=150)
sk = D["chart2_skill"]
y = range(len(sk))
h = 0.38

ax.barh([i + h / 2 for i in y], [s["bd"] for s in sk], height=h,
        color=C_AMBER, label="大数据岗要求占比", zorder=3)
ax.barh([i - h / 2 for i in y], [s["all"] for s in sk], height=h,
        color=C_BLUE, alpha=.6, label="全体技术岗要求占比", zorder=3)

for i, s in enumerate(sk):
    ax.text(s["bd"] + 0.8, i + h / 2, f"{s['bd']:.1f}%", va="center", color=C_AMBER, fontsize=9.5)
    ax.text(s["all"] + 0.8, i - h / 2, f"{s['all']:.1f}%", va="center", color=MUTED, fontsize=9)
    # 右侧标出差值，这是本图的核心信息
    ax.text(46, i, f"+{s['diff']:.0f}pp", va="center", ha="left",
            color=INK, fontsize=10, fontweight="bold")

ax.set_yticks(list(y))
ax.set_yticklabels([s["skill"] for s in sk], color=INK, fontsize=11)
ax.invert_yaxis()                                  # 差值最大的排最上
style_ax(ax, "图2 · 技能要求命中率：大数据岗 vs 全体技术岗", xlabel="岗位要求该技能的占比（%）")
ax.set_xlim(0, 54)
ax.legend(facecolor=PANEL, edgecolor=GRID, labelcolor=INK, loc="lower right", fontsize=10)
ax.text(46, -0.95, "差值", color=MUTED, fontsize=10, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, "fig2_skill_gap.png"), facecolor=BG, bbox_inches="tight")
plt.close()
print("✅ 图2 已保存")


# ============================================================================
# 图 3｜城市二维气泡图：薪资 × 大专可投占比
# 讲什么：一图定位"门槛低 + 薪资不低"的性价比城市。气泡大小 = 岗位机会数量
# ============================================================================
fig, ax = plt.subplots(figsize=(11, 7), dpi=150)
ct = D["chart3_city"]
avg_m, avg_c = D["chart3_avg_line"]["median"], D["chart3_avg_line"]["college"]

# 画四象限分割线（用全体均值作为参照）
ax.axvline(avg_c, color=LINE, linestyle="--", linewidth=1.2, zorder=1)
ax.axhline(avg_m, color=LINE, linestyle="--", linewidth=1.2, zorder=1)

for c in ct:
    size = 120 + (c["n"] / 100) ** 0.85 * 42        # 气泡面积按岗位数缩放
    ax.scatter(c["college"], c["median"], s=size, color=C_BLUE, alpha=.45,
               edgecolors=C_BLUE, linewidths=1.6, zorder=3)
    # 大城市标注名字，避免拥挤
    ax.annotate(c["city"], (c["college"], c["median"]), textcoords="offset points",
                xytext=(0, 13), ha="center", color=INK, fontsize=10.5, fontweight="bold")

# 四象限说明
quad = [(avg_c - 3.2, avg_m + 4.2, "薪资高 / 门槛也高", C_RED),
        (avg_c + 3.2, avg_m + 4.2, "薪资高 / 门槛低 ★", C_GREEN),
        (avg_c - 3.2, avg_m - 5.0, "薪资低 / 门槛高", C_DIM),
        (avg_c + 3.2, avg_m - 5.0, "薪资低 / 门槛低", C_AMBER)]
for x, y_, txt, col in quad:
    ax.text(x, y_, txt, color=col, fontsize=10.5, fontweight="bold",
            ha="center", alpha=.9, zorder=2)

style_ax(ax, "图3 · 城市机会地图：薪资水平 × 专科学历友好度",
         xlabel="大专/学历不限岗位占比（%）→ 越右越好投",
         ylabel="薪资中位数（K/月）→ 越上越高薪")
ax.text(0.99, 0.01, "气泡大小 = 该城市岗位数量；虚线为全样本均值",
        transform=ax.transAxes, ha="right", color=MUTED, fontsize=9)
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, "fig3_city_bubble.png"), facecolor=BG, bbox_inches="tight")
plt.close()
print("✅ 图3 已保存")


# ============================================================================
# 图 4｜应届生机会漏斗
# 讲什么：把"专科学历 + 应届 + 大数据"三重条件叠加后，可选岗位收缩到几个
# ============================================================================
fig, ax = plt.subplots(figsize=(11, 6), dpi=150)
fn = D["chart4_funnel"]
max_n = fn[0]["count"]
colors = [C_DIM, C_BLUE, C_AMBER, C_RED]

for i, s in enumerate(fn):
    width = s["count"] / max_n                     # 宽度按数量等比例
    left = (1 - width) / 2                          # 居中
    ax.add_patch(Rectangle((left, len(fn) - i - 0.72), width, 0.56,
                           facecolor=colors[i], alpha=.85, edgecolor="none"))
    pct = s["pct"]
    label = f"{s['count']:,} 个（{pct:.2f}%）" if pct < 1 else f"{s['count']:,} 个（{pct:.1f}%）"
    ax.text(0.5, len(fn) - i - 0.44, f"{s['stage']}：{label}",
            ha="center", va="center", color="#0b1220" if i > 0 else INK,
            fontsize=11.5, fontweight="bold")

ax.set_xlim(0, 1)
ax.set_ylim(-0.1, len(fn) + 0.1)
ax.axis("off")
ax.figure.patch.set_facecolor(BG)
ax.set_title("图4 · 从 14,422 个技术岗，到你能投的 5 个",
             color=INK, fontsize=15, fontweight="bold", pad=16)
ax.text(0.5, -0.06, "三重条件：学历不限/大专 → 大数据方向 → 应届可投（经验不限或明确招应届）",
        ha="center", color=MUTED, fontsize=10)
plt.tight_layout()
plt.savefig(os.path.join(IMG_DIR, "fig4_funnel.png"), facecolor=BG, bbox_inches="tight")
plt.close()
print("✅ 图4 已保存")

print("\n全部图表生成完毕。如需白底版本用于 Word/PPT，把 DARK 改为 False 后重跑。")
