# -*- coding: utf-8 -*-
"""
================================================================================
Step 2-1  数据清洗（Data Cleaning）
项目：大数据岗位招聘信息数据分析
数据：拉勾招聘.csv（21,320 行 × 21 列，采集时间 2022-08 ~ 2024-01）
================================================================================
清洗目标：把"能看但不好算"的原始数据，变成"可以直接 groupby"的分析表。

运行方式：
    python src/01_data_cleaning.py

输出：
    data/clean_jobs.csv        清洗后的分析表
    data/cleaning_log.txt      清洗日志（每步行数变化，可放进项目报告）
================================================================================
"""

import os
import re
import pandas as pd
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")

# ============================ 0. 路径与全局配置 ============================
# 原始数据需自行下载放入 data/（见 data/README.md）；路径基于仓库根目录，随处运行不用改
RAW_PATH = os.path.join(DATA_DIR, "lagou_jobs_raw.csv")
OUT_PATH = os.path.join(DATA_DIR, "clean_jobs.csv")
LOG_PATH = os.path.join(DATA_DIR, "cleaning_log.txt")

# 大数据岗位识别关键词（口径可调，见文档第三节）
BIGDATA_KEYWORDS = [
    "hadoop", "hive", "spark", "flink", "hbase", "kafka",
    "大数据", "数据开发", "数据仓库", "数仓", "etl",
    "数据平台", "数据工程", "数据架构", "数据挖掘",
]

# 技能词典：用于从 JD 正文抽取技能标签
SKILL_DICT = {
    "Hadoop": ["Hadoop"], "Spark": ["Spark"], "Hive": ["Hive"], "Flink": ["Flink"],
    "HBase": ["HBase"], "Kafka": ["Kafka"], "Zookeeper": ["Zookeeper"],
    "MapReduce": ["MapReduce"], "Yarn": ["Yarn"],
    "ClickHouse": ["ClickHouse"], "Doris": ["Doris"], "DataX": ["DataX"],
    "Airflow": ["Airflow"], "DolphinScheduler": ["DolphinScheduler"],
    "Elasticsearch": ["Elasticsearch", "ES"],
    "SQL": ["SQL"], "MySQL": ["MySQL"], "Oracle": ["Oracle"],
    "Python": ["Python"], "Java": ["Java"], "Scala": ["Scala"],
    "Shell": ["Shell"], "Linux": ["Linux"], "Redis": ["Redis"],
    "MongoDB": ["MongoDB"], "数据仓库": ["数据仓库", "数仓"], "ETL": ["ETL"],
}

# 城市等级划分（用于地域对比，按 2023-2024 主流划分口径）
CITY_TIER = {
    "一线": ["北京", "上海", "广州", "深圳"],
    "新一线": ["成都", "杭州", "重庆", "西安", "苏州", "武汉", "南京", "天津",
               "郑州", "长沙", "东莞", "佛山", "宁波", "青岛", "沈阳", "合肥"],
    "二线": ["昆明", "福州", "无锡", "厦门", "哈尔滨", "长春", "南昌", "济南",
             "大连", "贵阳", "温州", "石家庄", "泉州", "南宁", "金华", "常州",
             "珠海", "惠州", "嘉兴", "南通", "中山", "保定", "兰州", "台州",
             "徐州", "太原", "绍兴", "烟台", "廊坊", "海口"],
}

log_lines = []          # 清洗日志
def log(step, before, after, note=""):
    """记录每一步的行数变化，便于回溯清洗效果"""
    delta = after - before if before is not None else 0
    line = f"[{step}] {before} -> {after} (变动 {delta:+d}) {note}"
    log_lines.append(line)
    print(line)


# ============================ 1. 读取原始数据 ============================
df = pd.read_csv(RAW_PATH, encoding="utf-8")
n0 = len(df)
print(f"\n原始数据：{df.shape[0]} 行 × {df.shape[1]} 列")
log("1.读取", None, n0, f"{df.shape[1]} 列")

# 丢弃对分析无用的列
#   id       : 行号，无业务含义
#   create_at: 采集时间戳，与 createTime（发布时间）重复
df = df.drop(columns=["id", "create_at"], errors="ignore")
log("2.无用列", n0, len(df), f"保留 {df.shape[1]} 列")


# ============================ 2. 文本字段清洗 ============================
# 原始 JD 正文含 <br />、<p>、&nbsp; 等 HTML 标签，直接分词会把标签当词
# 检查结果：21,233 / 21,320 条（99.6%）含 HTML 标签，必须清洗

def strip_html(text):
    """去除 HTML 标签、转义字符、多余空白"""
    if pd.isna(text):
        return ""
    s = str(text)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)      # 换行标签 -> 换行符（保留段落结构）
    s = re.sub(r"<[^>]+>", " ", s)                      # 其余标签 -> 空格
    s = s.replace("&nbsp;", " ").replace("&amp;", "&")
    s = s.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    s = re.sub(r"[ \t\u3000]+", " ", s)                 # 合并空格/全角空格
    s = re.sub(r"\n{3,}", "\n\n", s)                    # 合并多余空行
    return s.strip()

for col in ["positionDetail", "positionAdvantage"]:
    df[col] = df[col].map(strip_html)

# 公司名、行业等短文本只去首尾空白
for col in ["companyFullName", "industryField", "city", "district", "positionName"]:
    df[col] = df[col].astype("string").str.strip()

log("3.HTML清洗", n0, len(df), "JD 与福利文本已去标签")


# ============================ 3. 薪资字段结构化 ============================
# 原始格式：字符串 "25k-40k"
#   问题1：k 大小写不统一（4 条为 "6K-12K"）
#   问题2：是区间，不能直接参与计算 -> 需拆成 min / max / 均值
#   问题3：单位是"千元/月"，需明确并派生年薪

s = df["salary"].astype("string").str.strip().str.lower()
# 统一小写 k，并处理可能出现的 "万/月" 等写法（本数据集未出现，做兜底）
s = s.str.replace("万/月", "0000k", regex=False)

sal = s.str.extract(r"^(?P<salary_min>\d+(?:\.\d+)?)k?-(?P<salary_max>\d+(?:\.\d+)?)k?$")
df["salary_min"] = pd.to_numeric(sal["salary_min"], errors="coerce")
df["salary_max"] = pd.to_numeric(sal["salary_max"], errors="coerce")

n_before = len(df)
# 无法解析的记录（如"面议"）先看有多少，再决定删或留
unparsed = df["salary_min"].isna() | df["salary_max"].isna()
print(f"\n薪资无法解析的记录：{unparsed.sum()} 条")
if unparsed.sum() > 0:
    print("  样例：", df.loc[unparsed, "salary"].unique()[:10])

df["salary_avg"] = (df["salary_min"] + df["salary_max"]) / 2      # 区间中值，单位：千元/月
df["salary_annual"] = df["salary_avg"] * 12 / 10                   # 年薪，单位：万元/年（简化，未计 13 薪）

# ---- 薪资异常识别：先按"业务语义"分类，再决定删/留 ----
# 关键：不要一上来就用 IQR 砍掉两端。高薪岗是真实信息，砍掉会低估薪资水平。
#      要先判断这个异常是"数据错误"还是"真实极值"。
ratio = df["salary_max"] / df["salary_min"].replace(0, np.nan)
df["salary_flag"] = "正常"
df.loc[unparsed, "salary_flag"] = "无法解析"
df.loc[df["salary_max"] < df["salary_min"], "salary_flag"] = "上限小于下限"
# 规则A｜疑似年薪误填：月薪不可能出现 150k、250k 的下限（=15万/月）
#   实证：这类记录如"视觉算法Leader 250k-500k""NLP实习生 200k-300k"，
#        实际应为年薪 25-50 万，被填成了月薪。共 15 条，属单位错误。
df.loc[df["salary_min"] >= 100, "salary_flag"] = "疑似年薪误填"
# 规则B｜区间跨度过大：如 3k-60k，跨度 20 倍，疑似录入错误（保留待查）
df.loc[ratio > 8, "salary_flag"] = "区间跨度过大"

# 规则C｜低薪标记：月薪 < 3k 的全职技术岗，多为虚假招聘或录入错误
#   实证：31 条全职岗如"全栈工程师 1k-2k""IT应用程序开发总监 1k-2k"。
#   这类不直接删（其中混有真实实习岗），只打标，分析全职薪资时排除。
df["low_salary"] = df["salary_avg"] < 3

print("\n薪资异常标记分布：")
print(df["salary_flag"].value_counts().to_string())
print(f"低薪标记（<3K）: {df['low_salary'].sum()} 条")

# 决策：只删除"数据确定错误"的三类（无法解析 / 上限小于下限 / 年薪误填），
#      "跨度过大"与"低薪"保留并标记，在分析阶段做敏感性对比（见文档说明）
drop_mask = df["salary_flag"].isin(["无法解析", "上限小于下限", "疑似年薪误填"])
df = df.loc[~drop_mask].copy()
log("4.薪资解析", n_before, len(df), "拆分min/max/avg；剔除无法解析、逻辑错误、年薪误填")


# ============================ 4. 去重 ============================
# 检查发现：positionId 只有 14,736 个唯一值，却有 21,320 行 -> 6,584 行重复
# 原因推断：同一岗位被重复发布 / 多次采集（全字段完全重复为 0，说明不是简单复制）
# 决策：按 positionId 保留 createTime 最新的一条（最新发布的版本信息更完整）

n_before = len(df)
df["createTime"] = pd.to_datetime(df["createTime"], errors="coerce")
df = (df.sort_values("createTime", ascending=False)
        .drop_duplicates(subset=["positionId"], keep="first")
        .reset_index(drop=True))
log("5.按positionId去重", n_before, len(df), "保留最新一条")

n_before = len(df)
df = df.drop_duplicates()
log("6.全字段去重", n_before, len(df))


# ============================ 5. 缺失值处理 ============================
# 原始缺失：companySize 193 / financeStage 193 / industryField 2495 / district 39 / positionType 1
# 策略原则：关键分析字段（薪资/城市/学历/经验/岗位）不能缺；描述性字段可填"未知"

print("\n处理前缺失情况：")
print(df.isna().sum()[df.isna().sum() > 0].to_string())

n_before = len(df)
# 5.1 关键字段缺失 -> 直接剔除（缺失则无法参与任何分组分析）
key_cols = ["salary_avg", "city", "education", "workYear", "positionName"]
df = df.dropna(subset=key_cols)
log("7.剔除关键字段缺失", n_before, len(df), f"依据 {key_cols}")

# 5.2 描述性字段缺失 -> 填充"未知"，保留样本
#     理由：这些字段缺失不代表岗位无效，填"未知"可避免损失 12% 的样本
for col in ["companySize", "financeStage", "industryField", "positionType"]:
    df[col] = df[col].fillna("未知")
df["district"] = df["district"].fillna(df["city"])   # 区域缺失用城市兜底

log(f"8.描述字段填充({len(df)}行)", len(df), len(df), "companySize/financeStage/industryField -> 未知")


# ============================ 6. 字段类型转换 ============================
# 有序分类的意义：让 pandas 知道"大专 < 本科 < 硕士"，排序和图表才不会乱

# 6.1 学历：转为有序分类（"不限"放最前，表示门槛最低）
edu_order = ["不限", "大专", "本科", "硕士", "博士"]
df["education"] = pd.Categorical(df["education"], categories=edu_order, ordered=True)

# 6.2 经验：转为有序分类
year_order = ["在校/应届", "1年以下", "1-3年", "3-5年", "5-10年", "10年以上", "不限"]
df["workYear"] = pd.Categorical(df["workYear"], categories=year_order, ordered=True)

# 6.3 公司规模：转为有序分类（按人数）
size_order = ["少于15人", "15-50人", "50-150人", "150-500人", "500-2000人", "2000人以上", "未知"]
df["companySize"] = pd.Categorical(df["companySize"], categories=size_order, ordered=True)

# 6.4 其余类别字段
for col in ["bigcategory", "category", "jobNature", "city", "financeStage"]:
    df[col] = df[col].astype("category")

# 6.5 时间字段拆分（为"发布时间分布"分析准备）
df["createTime"] = pd.to_datetime(df["createTime"], errors="coerce")
df["post_year"] = df["createTime"].dt.year
df["post_month"] = df["createTime"].dt.to_period("M").astype(str)

log("9.类型转换", len(df), len(df), "学历/经验/规模 -> 有序分类；时间 -> datetime")


# ============================ 7. 衍生字段构造 ============================
# 7.1 大数据岗位标识
#     口径：category 或 positionName 命中大数据关键词
#     结果：命中约 900+ 条（含 Hadoop 447 + 数据挖掘 449 及少量其他类）
def match_bigdata(row):
    text = f"{row['category']} {row['positionName']}".lower()
    return any(k in text for k in BIGDATA_KEYWORDS)

df["is_bigdata"] = df.apply(match_bigdata, axis=1)

# 7.2 岗位方向归类（用于需求结构分析）
#     思路：大数据单独成类，其余沿用平台自身的 bigcategory
def to_family(row):
    if row["is_bigdata"]:
        # 细分：开发/数仓 vs 算法挖掘
        text = f"{row['category']} {row['positionName']}".lower()
        if any(k in text for k in ["数据挖掘", "算法", "机器学习", "nlp", "自然语言", "视觉", "图像", "推荐", "搜索"]):
            return "数据挖掘/算法"
        return "大数据开发/数仓"
    return str(row["bigcategory"])

df["job_family"] = df.apply(to_family, axis=1).astype("category")

# 7.3 城市等级（用于地域对比）
city2tier = {c: t for t, cities in CITY_TIER.items() for c in cities}
df["city_tier"] = df["city"].astype(str).map(city2tier).fillna("其他").astype("category")

# 7.4 技能标签抽取
#     注意：SQL 不能简单用 in 判断，否则会误匹配 MySQL / PostgreSQL 中的 "SQL"
#     解决：英文技能用"前后非字母"边界判断
def has_skill(text, skill):
    if skill.isascii():
        return re.search(r"(?<![A-Za-z])" + re.escape(skill) + r"(?![A-Za-z])", text, re.I) is not None
    return skill in text

jd_text = (df["positionDetail"].fillna("") + " " + df["positionAdvantage"].fillna(""))
for skill, aliases in SKILL_DICT.items():
    pattern_text = jd_text
    hit = pd.Series(False, index=df.index)
    for alias in aliases:
        if alias.isascii():
            hit |= pattern_text.str.contains(r"(?<![A-Za-z])" + re.escape(alias) + r"(?![A-Za-z])",
                                             case=False, regex=True, na=False)
        else:
            hit |= pattern_text.str.contains(alias, regex=False, na=False)
    # 存成 0/1 整数而非 True/False：CSV 回读时布尔列容易被推断成字符串，
    # 导致后续 sum() / groupby() 报类型错误，用 int8 更稳，也省内存
    df[f"skill_{skill}"] = hit.astype("int8")

skill_cols = [f"skill_{k}" for k in SKILL_DICT]
df["skill_count"] = df[skill_cols].sum(axis=1)          # 该岗位要求的技能项数
df["skill_tags"] = df[skill_cols].apply(
    lambda r: "|".join(k.replace("skill_", "") for k, v in r.items() if v), axis=1)

log("10.衍生字段", len(df), len(df), "is_bigdata / job_family / city_tier / skill_tags")


# ============================ 8. 输出 ============================
# 列顺序整理：基础信息 -> 薪资 -> 门槛 -> 公司 -> 衍生字段
base_cols = ["positionId", "positionName", "category", "bigcategory", "job_family",
             "is_bigdata", "city", "city_tier", "district", "createTime", "post_year", "post_month",
             "salary", "salary_min", "salary_max", "salary_avg", "salary_annual",
             "salary_flag", "low_salary",
             "workYear", "education", "jobNature",
             "companyFullName", "companySize", "industryField", "financeStage"]
other_cols = [c for c in df.columns if c not in base_cols]
df = df[base_cols + other_cols]

df.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

print("\n" + "=" * 60)
print(f"清洗完成：{n0} 行 -> {len(df)} 行（保留 {len(df)/n0*100:.1f}%），{df.shape[1]} 列")
print(f"其中大数据相关岗位：{df['is_bigdata'].sum()} 条（{df['is_bigdata'].mean()*100:.1f}%）")
print(f"输出文件：{OUT_PATH}")

with open(LOG_PATH, "w", encoding="utf-8") as f:
    f.write("数据清洗日志\n" + "=" * 50 + "\n")
    f.write(f"原始数据：{n0} 行\n最终数据：{len(df)} 行\n\n")
    f.write("\n".join(log_lines))
print(f"清洗日志：{LOG_PATH}")
