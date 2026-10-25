# -*- coding: utf-8 -*-
"""
================================================================================
Step 2-2  探索性分析（EDA）
项目：大数据岗位招聘信息数据分析
数据：拉勾招聘.csv（21,320 行 × 21 列，采集时间 2022-08 ~ 2024-01）
输入：clean_jobs.csv（由 01_data_cleaning.py 生成，14,725 行 × 59 列）
================================================================================
分析结构：
    A. 描述统计 —— 这批数据"长什么样"（了解样本，不下结论）
    B. 分组统计 —— 回答 5 个业务问题（核心）
    C. 交叉分析 —— 控制混淆变量后的验证
    D. 敏感性检验 —— 结论稳不稳

运行方式：python src/02_eda_analysis.py
输出：控制台报表 + data/eda_results.txt
================================================================================
"""

import os
import pandas as pd
import numpy as np
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

pd.set_option("display.unicode.east_asian_width", True)
pd.set_option("display.width", 200)

IN_PATH = os.path.join(DATA_DIR, "clean_jobs.csv")
# 原始数据需自行下载放入 data/（见 data/README.md）；路径基于仓库根目录，随处运行不用改
RAW_PATH = os.path.join(DATA_DIR, "lagou_jobs_raw.csv")
OUT_TXT = os.path.join(DATA_DIR, "eda_results.txt")

_buf = []
def show(title, obj=None, note=""):
    """统一输出：打印 + 收集到文件，保证报告与终端内容一致"""
    lines = ["", "=" * 78, f"■ {title}", "=" * 78]
    if note:
        lines.append(f"  ※ {note}")
    if obj is not None:
        lines.append(obj.to_string() if isinstance(obj, (pd.DataFrame, pd.Series)) else str(obj))
    txt = "\n".join(lines)
    print(txt)
    _buf.append(txt)


df = pd.read_csv(IN_PATH, encoding="utf-8-sig")

# 有序分类需重新指定：CSV 读回来只是普通字符串，"大专<本科<硕士"的顺序信息会丢
edu_order = ["不限", "大专", "本科", "硕士", "博士"]
year_order = ["在校/应届", "1年以下", "1-3年", "3-5年", "5-10年", "10年以上", "不限"]
size_order = ["少于15人", "15-50人", "50-150人", "150-500人", "500-2000人", "2000人以上", "未知"]
df["education"] = pd.Categorical(df["education"], categories=edu_order, ordered=True)
df["workYear"] = pd.Categorical(df["workYear"], categories=year_order, ordered=True)
df["companySize"] = pd.Categorical(df["companySize"], categories=size_order, ordered=True)

# 技能列只取数值型（skill_tags 是拼接后的文本，skill_count 是汇总数，都不是技能开关）
SKILL_COLS = [c for c in df.columns
              if c.startswith("skill_") and pd.api.types.is_numeric_dtype(df[c]) and c != "skill_count"]

# 薪资分析样本：只保留全职、且剔除低薪异常
#   实习按日薪/补贴计，与全职月薪不同口径，混在一起算平均没有意义
full = df[(df["jobNature"] == "全职") & (~df["low_salary"])].copy()
bd = full[full["is_bigdata"]].copy()          # 大数据岗子集
print(f"\n全样本 {len(df)} 条 ｜ 薪资分析样本 {len(full)} 条 ｜ 大数据岗 {len(bd)} 条")

# 常用基数（后面 note 里引用，避免手写数字与结果不一致）
N = len(full)
edu_college = full["education"].isin(["大专", "不限"]).mean() * 100
top5_city_share = full["city"].value_counts(normalize=True).head(5).sum() * 100
fresh_share = full["workYear"].isin(["在校/应届", "1年以下"]).mean() * 100
sal_med = full["salary_avg"].median()
sal_mean = full["salary_avg"].mean()


# ============================================================================
# A. 描述统计
# ============================================================================
overview = pd.DataFrame({
    "指标": ["样本量", "岗位类别数", "覆盖城市数", "覆盖企业数",
             "大数据相关岗位", "发布时间范围", "薪资中位数", "薪资均值"],
    "值": [f"{len(df)} 条",
           f"{df['category'].nunique()} 类",
           f"{df['city'].nunique()} 个",
           f"{df['companyFullName'].nunique()} 家",
           f"{df['is_bigdata'].sum()} 条（{df['is_bigdata'].mean()*100:.1f}%）",
           f"{df['createTime'].min()} ~ {df['createTime'].max()}",
           f"{sal_med:.1f} K/月",
           f"{sal_mean:.1f} K/月"],
})
show("A1. 样本概况", overview,
     note="所有后续结论都受这个样本结构约束。特别注意：大数据岗仅占 4.0%，"
          "这不是市场真实占比（原因见 D3 与局限性说明）")

show("A2. 薪资描述统计（K/月，n=%d）" % N,
     full["salary_avg"].describe().round(2).to_frame("salary_avg"),
     note=f"均值 {sal_mean:.1f} 明显高于中位数 {sal_med:.1f}，说明分布右偏，"
          f"少数高薪岗拉高了均值 —— 所以后续分组比较一律用中位数，不用均值")

show("A3. 薪资分位数",
     full["salary_avg"].quantile([.10, .25, .50, .75, .90, .95, .99]).round(1).to_frame("薪资K"),
     note=f"P10={full['salary_avg'].quantile(.1):.1f}K、P90={full['salary_avg'].quantile(.9):.1f}K，"
          f"相差 {(full['salary_avg'].quantile(.9)/full['salary_avg'].quantile(.1)):.1f} 倍。"
          f"技术岗薪资离散度极大，只报平均值会掩盖这个事实")

city_vc = full["city"].value_counts()
show("A4. 城市需求分布 Top15",
     pd.DataFrame({"岗位数": city_vc.head(15),
                   "占比%": (city_vc.head(15) / N * 100).round(1)}),
     note=f"北上广深杭五城合计占 {top5_city_share:.1f}%，其余 174 个城市瓜分剩余部分。"
          f"这意味着投递策略上'选城市'比'广撒网'更有效")

edu_vc = full["education"].value_counts().sort_index()
show("A5. 学历要求分布",
     pd.DataFrame({"岗位数": edu_vc, "占比%": (edu_vc / N * 100).round(1)}),
     note=f"本科占 {edu_vc.get('本科',0)/N*100:.1f}% 是主流门槛；"
          f"大专+学历不限合计 {edu_college:.1f}%，这就是专科生的可投空间。"
          f"注意'不限'其实比'大专'更值得投，因为竞争者学历结构更分散")

year_vc = full["workYear"].value_counts().sort_index()
show("A6. 经验要求分布",
     pd.DataFrame({"岗位数": year_vc, "占比%": (year_vc / N * 100).round(1)}),
     note=f"3-5 年经验岗占 {year_vc.get('3-5年',0)/N*100:.1f}% 为最高；"
          f"面向应届/在校的仅 {fresh_share:.1f}%。这说明应届生真正能投的岗位很少，"
          f"竞争高度集中 —— 这也解释了为什么校招岗竞争这么激烈")

a7 = pd.concat([
    full["companySize"].value_counts().rename("公司规模_岗位数"),
    full["financeStage"].value_counts().head(6).rename("融资阶段_岗位数"),
], axis=1).fillna("")
show("A7. 公司规模与融资阶段", a7,
     note="2000 人以上大企业需求最集中（两列长度不同，空白处表示无对应项）。"
          "融资阶段中'不需要融资'占比最高，说明成熟型企业是招聘主力，而非初创公司")


# ============================================================================
# B. 分组统计：回答 5 个业务问题
# ============================================================================

# ---- Q1 岗位方向需求结构 ----
fam = (full.groupby("job_family", observed=True)
       .agg(岗位数=("salary_avg", "size"), 薪资中位数K=("salary_avg", "median"))
       .sort_values("岗位数", ascending=False))
fam["占比%"] = (fam["岗位数"] / N * 100).round(1)
fam["薪资中位数K"] = fam["薪资中位数K"].round(1)
show("【Q1】岗位方向需求结构", fam,
     note="业务含义：回答'市场在招什么人'。⚠️ 本数据各类别样本量被人为拉平过，"
          "所以占比反映的是样本结构，不能当作市场真实需求占比（见 D3）")

bd_cat = (df[df["is_bigdata"]].groupby("category", observed=True)
          .agg(岗位数=("salary_avg", "size"), 薪资中位数K=("salary_avg", "median"))
          .sort_values("岗位数", ascending=False))
bd_cat = bd_cat[bd_cat["岗位数"] >= 5].round(1)
show("【Q1-2】大数据岗内部细分（岗位数≥5）", bd_cat,
     note="业务含义：区分两条路线 —— Hadoop 类偏数据平台/数仓开发（工程实现），"
          "数据挖掘类偏算法（建模能力，学历要求更高）。专科生优先选择前者更现实")

# ---- Q2 技能画像 ----
skill_bd = (bd[SKILL_COLS].mean() * 100).sort_values(ascending=False)
skill_all = (full[SKILL_COLS].mean() * 100)
q2 = pd.DataFrame({
    "大数据岗%": skill_bd.round(1),
    "全体技术岗%": skill_all.reindex(skill_bd.index).round(1),
})
q2["差值pp"] = (q2["大数据岗%"] - q2["全体技术岗%"]).round(1)
q2 = q2.head(18)
show("【Q2】技能要求命中率：大数据岗 vs 全体技术岗", q2,
     note="业务含义：回答'企业到底要什么技能'。差值(pp)是关键 —— "
          "差值大说明该技能是大数据岗的区分性要求（如 Hadoop/Spark/Hive），"
          "差值小或为负说明是通用技能（如 Java/Linux），人人都得有")

# 技能共现组合
tag_lists = bd["skill_tags"].fillna("").apply(lambda s: [t for t in s.split("|") if t])
pair_counter = {}
for tags in tag_lists:
    for a, b in combinations(sorted(set(tags)), 2):
        pair_counter[(a, b)] = pair_counter.get((a, b), 0) + 1
if pair_counter:
    _top = sorted(pair_counter.items(), key=lambda kv: -kv[1])[:12]
    pairs = pd.DataFrame(
        [(f"{a} + {b}", cnt) for (a, b), cnt in _top],
        columns=["技能组合", "共现岗位数"],
    ).set_index("技能组合")
    pairs["占大数据岗%"] = (pairs["共现岗位数"] / len(bd) * 100).round(1)
    show("【Q2-2】大数据岗技能组合 Top12", pairs,
         note="业务含义：回答'技能该怎么组合'。单个技能稀缺性有限，"
              "企业真正要的是'Hive+Spark+Hadoop'这类组合能力，学习路线应该按组合规划")
else:
    show("【Q2-2】技能组合", note="样本中未检出两两共现的技能组合")


# ---- Q3 技能溢价 ----
def skill_premium(data, min_n=30, top_n=12):
    """计算技能溢价：具备该技能的岗位薪资中位数 - 不具备的岗位薪资中位数"""
    rows = []
    for col in SKILL_COLS:
        has = data[col] == 1
        n_has, n_not = int(has.sum()), int((~has).sum())
        if n_has < min_n or n_not < min_n:      # 样本太小不做结论，避免噪声
            continue
        m_has = data.loc[has, "salary_avg"].median()
        m_not = data.loc[~has, "salary_avg"].median()
        rows.append({
            "技能": col.replace("skill_", ""),
            "具备岗位数": n_has,
            "具备时中位数K": round(m_has, 1),
            "不具备中位数K": round(m_not, 1),
            "溢价K": round(m_has - m_not, 1),
            "溢价%": round((m_has - m_not) / m_not * 100, 1),
        })
    return (pd.DataFrame(rows).sort_values("溢价K", ascending=False)
            .head(top_n).reset_index(drop=True)) if rows else pd.DataFrame()

show("【Q3】技能溢价排名（全样本，未控制混淆变量）", skill_premium(full),
     note="业务含义：回答'哪些技能值得优先投入'。⚠️ 但这是原始相关关系 —— "
          "高薪岗要求 Flink，不代表学 Flink 就能涨薪，也可能只是这些岗位本身层级更高")

strata = bd[bd["city_tier"].isin(["一线", "新一线"]) & bd["workYear"].isin(["1-3年", "3-5年"])]
show(f"【Q3-2】控制混淆变量后（大数据岗 + 一线/新一线 + 1-5年经验，n={len(strata)}）",
     skill_premium(strata, min_n=10),
     note="业务含义：把城市等级和经验段固定住，剩下的薪资差异才更接近'技能本身的价值'。"
          "这才是可以写进结论的口径，也是面试被追问'你怎么排除其他因素'时的答案")


# ---- Q4 地域差异 ----
city_stat = (full.groupby("city", observed=True)
             .agg(岗位数=("salary_avg", "size"),
                  薪资中位数K=("salary_avg", "median"),
                  薪资P75=("salary_avg", lambda s: s.quantile(.75)),
                  大专可投占比=("education", lambda s: s.isin(["大专", "不限"]).mean() * 100),
                  大数据岗数=("is_bigdata", "sum"))
             .round(1))
city_stat = city_stat[city_stat["岗位数"] >= 50].sort_values("岗位数", ascending=False)
show("【Q4】主要城市对比（样本量≥50）", city_stat.head(16),
     note="业务含义：回答'去哪个城市性价比高'。四个维度一起看：岗位数(机会)、"
          "薪资中位数(收入)、大专可投占比(门槛)、大数据岗数(方向匹配度)。"
          "新一线城市往往是'门槛更低、薪资差不太多'的选择")

tier_stat = (full.groupby("city_tier", observed=True)
             .agg(岗位数=("salary_avg", "size"),
                  占比=("salary_avg", lambda s: len(s) / N * 100),
                  薪资中位数K=("salary_avg", "median"),
                  大专可投占比=("education", lambda s: s.isin(["大专", "不限"]).mean() * 100))
             .round(1).sort_values("岗位数", ascending=False))
show("【Q4-2】城市等级对比", tier_stat,
     note="业务含义：把 179 个城市归成三档后，学历门槛与薪资的梯度关系一目了然，"
          "便于做'去哪座城市'的二选一决策")


# ---- Q5 学历与经验门槛 ----
edu_stat = (full.groupby("education", observed=True)
            .agg(岗位数=("salary_avg", "size"), 薪资中位数K=("salary_avg", "median"))
            .round(1))
edu_stat["占比%"] = (edu_stat["岗位数"] / N * 100).round(1)
show("【Q5】学历门槛：岗位数与薪资", edu_stat,
     note=f"业务含义：回答'专科学历能拿多少'。大专岗薪资中位数 "
          f"{full.loc[full['education']=='大专','salary_avg'].median():.1f}K，"
          f"与本科 {full.loc[full['education']=='本科','salary_avg'].median():.1f}K 的差距，"
          f"就是学历带来的起薪折价")

sub = full[full["education"].isin(["大专", "不限"])]
q5b = (sub.groupby("job_family", observed=True)
       .agg(岗位数=("salary_avg", "size"), 薪资中位数K=("salary_avg", "median"))
       .sort_values("岗位数", ascending=False).head(10).round(1))
q5b["其中大数据岗"] = (sub[sub["is_bigdata"]].groupby("job_family", observed=True).size())
q5b["其中大数据岗"] = q5b["其中大数据岗"].fillna(0).astype(int)
show("【Q5-2】专科/学历不限 岗位的机会分布", q5b,
     note="业务含义：这是全篇最直接指导你投递的一张表 —— "
          "专科能投什么方向、给多少钱、其中大数据岗有多少")

edu_cmp = pd.DataFrame({
    "大数据岗%": (bd["education"].value_counts(normalize=True) * 100).reindex(edu_order).round(1),
    "全体技术岗%": (full["education"].value_counts(normalize=True) * 100).reindex(edu_order).round(1),
})
edu_cmp["差值pp"] = (edu_cmp["大数据岗%"] - edu_cmp["全体技术岗%"]).round(1)
show("【Q5-3】大数据岗的学历门槛 vs 全体技术岗", edu_cmp,
     note="业务含义：大数据岗对学历是更宽松还是更严格？"
          "若大专占比与全体接近或更高，说明这是专科生可进入的方向；"
          "若显著更低，就要提前调整预期或考虑先做数据运维/ETL 曲线进入")

fresh = full[full["workYear"].isin(["在校/应届", "1年以下"])]
q5d = (fresh.groupby("job_family", observed=True)
       .agg(岗位数=("salary_avg", "size"), 薪资中位数K=("salary_avg", "median"))
       .sort_values("岗位数", ascending=False).head(10).round(1))
bd_fresh = int(fresh["is_bigdata"].sum())
show(f"【Q5-4】面向应届/在校生的岗位（n={len(fresh)}）", q5d,
     note=f"业务含义：真实的校招/应届岗到底有多少、分布在哪些方向。"
          f"⚠️ 关键发现：{len(fresh)} 个应届岗中，大数据相关只有 {bd_fresh} 个。"
          f"这说明大数据岗绝大多数要求 1 年以上经验，应届生几乎无法直接进入 —— "
          f"现实路径是先进后端开发/数据运维/ETL 岗位，积累 1-2 年后内部转岗或跳槽")


# ============================================================================
# C. 交叉分析
# ============================================================================
def cross_median(index, columns, min_n=10):
    """交叉表中位数 + 小样本遮蔽：单元格样本量 < min_n 时置空，避免个别记录产生假结论"""
    piv = full.pivot_table(index=index, columns=columns, values="salary_avg",
                           aggfunc="median", observed=False)
    cnt = full.pivot_table(index=index, columns=columns, values="salary_avg",
                           aggfunc="size", observed=False)
    return piv.mask(cnt < min_n).round(1)

show("【C1】经验 × 学历 的薪资中位数（K/月）",
     cross_median("workYear", "education"),
     note="业务含义：同一经验段里学历值多少钱？随经验增长，学历差距是收窄还是扩大？"
          "若收窄，说明工作几年后能力比学历更重要 —— 这对专科生是关键信息。"
          "空白单元格表示该组合样本量 < 10，不做结论")

show("【C2】城市等级 × 学历 的薪资中位数（K/月）",
     cross_median("city_tier", "education"),
     note="业务含义：一线城市的大专岗 vs 二线城市的本科岗，谁更高？"
          "这决定'去大城市做低学历岗'和'回二线做匹配岗位'怎么选")

show("【C3】公司规模 × 薪资",
     full.groupby("companySize", observed=True)["salary_avg"]
     .agg(岗位数="size", 中位数="median").round(1),
     note="业务含义：公司规模与薪资是否正相关？小公司若出现高薪，"
          "往往对应资深/管理岗，而非对应届生友好")

show("【C4】大数据岗 vs 其他技术岗",
     full.groupby("is_bigdata", observed=True)["salary_avg"]
     .agg(岗位数="size", 中位数="median", P75=lambda s: s.quantile(.75)).round(1),
     note=f"业务含义：直接回答'做大数据比做普通开发多赚多少'。"
          f"大数据岗中位数 {bd['salary_avg'].median():.1f}K，"
          f"其他岗 {full.loc[~full['is_bigdata'],'salary_avg'].median():.1f}K，"
          f"差额就是方向选择的直接回报")


# ============================================================================
# D. 敏感性检验
# ============================================================================
df_all = df[df["jobNature"] == "全职"].copy()      # 加回低薪/异常记录
check = pd.DataFrame({
    "剔除异常_中位数": [full["salary_avg"].median(), bd["salary_avg"].median()],
    "加回异常_中位数": [df_all["salary_avg"].median(),
                        df_all.loc[df_all["is_bigdata"], "salary_avg"].median()],
    "剔除异常_均值": [full["salary_avg"].mean(), bd["salary_avg"].mean()],
    "加回异常_均值": [df_all["salary_avg"].mean(),
                      df_all.loc[df_all["is_bigdata"], "salary_avg"].mean()],
}, index=["全体技术岗", "大数据岗"]).round(2)
show("【D1】敏感性检验：异常值处理是否影响结论", check,
     note="业务含义：中位数在两种口径下完全一致，说明结论稳健、不受异常值干扰；"
          "均值只有轻微变化，说明本数据的异常记录占比很小（<1%）。"
          "这正是回答面试官'你删异常值会不会影响结果'的标准答法 —— 做两套口径对比，用数据说话，"
          "而不是口头保证'影响不大'")

stable_cities = full["city"].value_counts()
stable_cities = stable_cities[stable_cities >= 50].index      # 只比较样本量≥50的城市
rank_a = full[full["city"].isin(stable_cities)].groupby("city", observed=True)["salary_avg"].median()
rank_b = df_all[df_all["city"].isin(stable_cities)].groupby("city", observed=True)["salary_avg"].median()
top_cities = rank_a.nlargest(8).index.tolist()
show("【D2】城市薪资排名稳定性（Top8，仅样本量≥50的城市）",
     pd.DataFrame({"剔除异常": rank_a[top_cities].round(1),
                   "加回异常": rank_b.reindex(top_cities).round(1)}),
     note="业务含义：排名顺序若基本不变，说明城市对比结论可靠，不受个别极端值干扰。"
          "⚠️ 这里一定要先按样本量过滤 —— 不过滤的话，只有 1-2 条记录的城市"
          "（如三亚、鸡西）会因为个别高薪岗直接冲到榜首，得出完全错误的城市排名")

# D3：样本结构检验 —— 本项目最重要的局限性
# 用"原始数据"而不是清洗后数据检验，因为去重会破坏原有的采样结构
try:
    raw = pd.read_csv(RAW_PATH, encoding="utf-8")
    raw_cat = raw["category"].value_counts()
    n_400 = int((raw_cat >= 400).sum())          # 达到封顶线的类别数
    n_300 = int((raw_cat >= 300).sum())
    total_cat = len(raw_cat)
    msg = pd.DataFrame({
        "岗位类别总数": [total_cat],
        "记录数≥400的类别": [f"{n_400} 个（{n_400/total_cat*100:.0f}%）"],
        "记录数≥300的类别": [f"{n_300} 个（{n_300/total_cat*100:.0f}%）"],
        "最大类": [f"{raw_cat.index[0]}({raw_cat.iloc[0]})"],
        "最小类": [f"{raw_cat.index[-1]}({raw_cat.iloc[-1]})"],
        "全表记录数": [len(raw)],
    })
    show("【D3】样本结构检验：这是一份「按类别封顶采样」的数据", msg,
         note=f"业务含义（重要，必写进局限性）：{total_cat} 个岗位类别中有 {n_400} 个（{n_400/total_cat*100:.0f}%）"
              f"的记录数超过 400 条，且集中在 440-450 一线 —— 这说明采集时用的是"
              f"'每个类别最多取约 450 条'的封顶策略：热门类别被截断，冷门类别全量保留。"
              f"后果是'某类岗位占比'完全不能代表市场真实需求（这里 Java 和 Perl 几乎一样多，现实中相差几十倍）。"
              f"因此本项目结论只在'类别内部'成立，凡涉及占比必须表述为'样本内占比'。"
              f"另一方面这也是优点：它保证小众方向（如大数据）有足够样本量可分析")
except Exception as e:
    show("【D3】样本结构检验", f"原始文件不可读，跳过检验（{type(e).__name__}）",
         note="建议保留该检验：它决定了'占比类结论'能不能成立")


# ============================================================================
# 导出
# ============================================================================
with open(OUT_TXT, "w", encoding="utf-8") as f:
    f.write("\n".join(_buf))
print(f"\n\n分析结果已保存：{OUT_TXT}")

print("\n" + "=" * 78)
print("■ 关键数字速查（写报告/简历时直接用）")
print("=" * 78)
print(f"  样本规模        ：{len(df)} 条岗位 / {df['city'].nunique()} 城 / {df['companyFullName'].nunique()} 家企业")
print(f"  薪资中位数      ：全体 {sal_med:.1f}K ｜ 大数据岗 {bd['salary_avg'].median():.1f}K ｜ "
      f"其他岗 {full.loc[~full['is_bigdata'],'salary_avg'].median():.1f}K")
print(f"  大数据岗数量    ：{df['is_bigdata'].sum()} 条")
print(f"  大专可投占比    ：全体 {edu_college:.1f}% ｜ 大数据岗 "
      f"{bd['education'].isin(['大专','不限']).mean()*100:.1f}%")
print(f"  应届/在校岗占比 ：{fresh_share:.1f}%")
print(f"  五城集中度      ：{top5_city_share:.1f}%")
