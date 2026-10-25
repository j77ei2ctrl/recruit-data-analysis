# -*- coding: utf-8 -*-
"""
Step 3-1  图表数据计算
从 clean_jobs.csv 算出 4 张图所需的精确坐标数据，导出 JSON
供 03_visualization.py(matplotlib) 与作品集 HTML(原生JS/SVG) 共用
"""
import json
import os
import pandas as pd
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

df = pd.read_csv(os.path.join(DATA_DIR, "clean_jobs.csv"), encoding="utf-8-sig")
edu_order = ["不限", "大专", "本科", "硕士", "博士"]
year_order = ["在校/应届", "1年以下", "1-3年", "3-5年", "5-10年", "10年以上", "不限"]
df["education"] = pd.Categorical(df["education"], categories=edu_order, ordered=True)
df["workYear"] = pd.Categorical(df["workYear"], categories=year_order, ordered=True)

full = df[(df["jobNature"] == "全职") & (~df["low_salary"])].copy()
bd = full[full["is_bigdata"]].copy()
SKILL_COLS = [c for c in df.columns
              if c.startswith("skill_") and pd.api.types.is_numeric_dtype(df[c]) and c != "skill_count"]
out = {}

# ========== 图1：各岗位方向薪资箱线图 ==========
# 用 salary_avg（薪资区间中值）代表岗位薪资水平；须按 matplotlib 默认 1.5*IQR 计算
fams = ["后端开发", "运维", "前端开发", "测试", "人工智能", "移动开发", "大数据开发/数仓"]
box = []
for f in fams:
    s = full.loc[full["job_family"] == f, "salary_avg"].dropna()
    q1, med, q3 = s.quantile(.25), s.median(), s.quantile(.75)
    iqr = q3 - q1
    lo = s[s >= q1 - 1.5 * iqr].min()
    hi = s[s <= q3 + 1.5 * iqr].max()
    box.append({
        "name": f, "n": int(len(s)),
        "low": round(float(lo), 1), "q1": round(float(q1), 1),
        "median": round(float(med), 1), "q3": round(float(q3), 1),
        "high": round(float(hi), 1),
        "mean": round(float(s.mean()), 1),
        "outliers": [round(float(v), 1) for v in
                     s[(s < lo) | (s > hi)].sample(min(28, int(((s < lo) | (s > hi)).sum())),
                                                   random_state=42).tolist()],
        "n_outliers": int(((s < lo) | (s > hi)).sum()),
    })
out["chart1_salary_box"] = box

# ========== 图2：技能命中率差值（大数据岗 vs 全体技术岗）==========
rate_bd = (bd[SKILL_COLS].mean() * 100)
rate_all = (full[SKILL_COLS].mean() * 100)
diff = (rate_bd - rate_all).sort_values(ascending=False)
top = diff.head(12).index
out["chart2_skill"] = [{
    "skill": c.replace("skill_", ""),
    "bd": round(float(rate_bd[c]), 1),
    "all": round(float(rate_all[c]), 1),
    "diff": round(float(rate_bd[c] - rate_all[c]), 1),
    "n_bd": int(bd[c].sum()),
} for c in top]

# ========== 图3：城市 薪资 × 大专可投占比 气泡图 ==========
city_stat = (full.groupby("city", observed=True)
             .agg(n=("salary_avg", "size"),
                  median=("salary_avg", "median"),
                  college=("education", lambda s: s.isin(["大专", "不限"]).mean() * 100),
                  bd_n=("is_bigdata", "sum")))
city_stat = city_stat[city_stat["n"] >= 50].sort_values("n", ascending=False).head(14)
out["chart3_city"] = [{
    "city": idx,
    "n": int(r["n"]),
    "median": round(float(r["median"]), 1),
    "college": round(float(r["college"]), 1),
    "bd_n": int(r["bd_n"]),
} for idx, r in city_stat.iterrows()]
out["chart3_avg_line"] = {
    "median": round(float(full["salary_avg"].median()), 1),
    "college": round(float(full["education"].isin(["大专", "不限"]).mean() * 100), 1),
}

# ========== 图4：应届生机会漏斗 ==========
# 口径说明：「经验不限」的岗位应届生同样可以投递，不能漏掉，否则会严重低估机会
FRESH = ["在校/应届", "1年以下", "不限"]
college_ok = full["education"].isin(["大专", "不限"])
fresh_ok = full["workYear"].isin(FRESH)
steps = [
    ("全部技术岗", int(len(full))),
    ("学历门槛可通过（大专/不限）", int(college_ok.sum())),
    ("其中属于大数据方向", int((college_ok & full["is_bigdata"]).sum())),
    ("且应届可投（经验不限/应届）", int((college_ok & full["is_bigdata"] & fresh_ok).sum())),
]
out["chart4_funnel"] = [{"stage": s, "count": c, "pct": round(c / len(full) * 100, 2)} for s, c in steps]

# 对照口径：若只看"明确写在校/应届/1年以下"，结果会更严苛，用于结论中做区间说明
strict_fresh = full["workYear"].isin(["在校/应届", "1年以下"])
out["chart4_note"] = {
    "bd_total": int(bd.shape[0]),
    "college_bd": int((college_ok & full["is_bigdata"]).sum()),
    "college_bd_fresh_loose": int((college_ok & full["is_bigdata"] & fresh_ok).sum()),
    "college_bd_fresh_strict": int((college_ok & full["is_bigdata"] & strict_fresh).sum()),
    "bd_fresh_any_edu": int((full["is_bigdata"] & fresh_ok).sum()),
    "college_jobs_all": int(college_ok.sum()),
    "fresh_ok_ratio": round(float(fresh_ok.mean() * 100), 1),
}

# ========== 附加：技能溢价双口径对比（体现"相关≠因果"）==========
def premium(data, min_n):
    rows = {}
    for c in SKILL_COLS:
        has = data[c] == 1
        if has.sum() < min_n or (~has).sum() < min_n:
            continue
        m1 = data.loc[has, "salary_avg"].median()
        m0 = data.loc[~has, "salary_avg"].median()
        rows[c.replace("skill_", "")] = round(float(m1 - m0), 1)
    return rows

p_all = premium(full, 30)
strata = bd[bd["city_tier"].isin(["一线", "新一线"]) & bd["workYear"].isin(["1-3年", "3-5年"])]
p_ctl = premium(strata, 10)
keys = ["Spark", "Hive", "Hadoop", "Flink", "Kafka", "Java", "Python", "SQL"]
out["chart5_premium"] = [{"skill": k, "raw": p_all.get(k), "controlled": p_ctl.get(k)}
                         for k in keys if k in p_all]
out["meta"] = {
    "total": int(len(df)), "salary_sample": int(len(full)),
    "bd_n": int(bd.shape[0]),
    "median_all": round(float(full["salary_avg"].median()), 1),
    "median_bd": round(float(bd["salary_avg"].median()), 1),
    "median_other": round(float(full.loc[~full["is_bigdata"], "salary_avg"].median()), 1),
}

with open(os.path.join(DATA_DIR, "charts_data.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)

print("=== 图1 箱线 ===")
for b in box:
    print(f"  {b['name']:<14} n={b['n']:<5} 中位={b['median']:<6} Q1={b['q1']:<6} Q3={b['q3']:<6} 须={b['low']}-{b['high']}")
print("\n=== 图2 技能差值 Top12 ===")
for s in out["chart2_skill"]:
    print(f"  {s['skill']:<16} 大数据{s['bd']:>5}%  全体{s['all']:>5}%  差{s['diff']:>+6}pp")
print("\n=== 图3 城市 ===")
for c in out["chart3_city"]:
    print(f"  {c['city']:<5} n={c['n']:<5} 中位{c['median']:<6}K 大专可投{c['college']:<6}% 大数据{c['bd_n']}")
print("\n=== 图4 漏斗 ===")
for s in out["chart4_funnel"]:
    print(f"  {s['stage'].replace(chr(10),' '):<26} {s['count']:>6} ({s['pct']}%)")
print("  对照:", out["chart4_note"])
print("\n=== 图5 溢价双口径 ===")
for p in out["chart5_premium"]:
    print(f"  {p['skill']:<10} 全样本{p['raw']:>+6}K  控变量{p['controlled']}K")
print("\n已导出 charts_data.json")
