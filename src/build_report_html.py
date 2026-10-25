# -*- coding: utf-8 -*-
"""
把 REPORT.md 渲染成 report.html（GitHub Pages 可读的网页版报告）。
零依赖：只用标准库。支持 标题/段落/表格/图片/代码块/引用/列表/行内格式 + 自动生成侧边目录。
"""
import re, os, html, io

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(ROOT, "REPORT.md")
OUT = os.path.join(ROOT, "report.html")

md = open(MD, encoding="utf-8").read()


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


def slug(t):
    t = re.sub(r"<[^>]+>", "", t)
    t = t.strip().lower()
    t = re.sub(r"[^\w\u4e00-\u9fa5\s-]", "", t)
    return re.sub(r"\s+", "-", t)


lines = md.split("\n")
out, toc = [], []
i = 0
title = "大数据招聘岗位数据分析"
in_code, code_buf = False, []
para = []


def flush():
    global para
    if para:
        out.append("<p>%s</p>" % inline(" ".join(para)))
        para = []


while i < len(lines):
    s = lines[i].strip()

    if s.startswith("```"):
        flush()
        if not in_code:
            in_code, code_buf = True, []
        else:
            out.append("<pre><code>%s</code></pre>" % html.escape("\n".join(code_buf), quote=False))
            in_code = False
        i += 1
        continue
    if in_code:
        code_buf.append(lines[i])
        i += 1
        continue

    if s == "":
        flush()
        i += 1
        continue

    if re.match(r"^-{3,}$", s) or re.match(r"^\*{3,}$", s):
        flush()
        out.append("<hr>")
        i += 1
        continue

    if s.startswith("### "):
        flush()
        t = s[4:]
        out.append('<h3 id="%s">%s</h3>' % (slug(t), inline(t)))
        i += 1
        continue
    if s.startswith("## "):
        flush()
        t = s[3:]
        hid = slug(t)
        toc.append((2, hid, re.sub(r"<[^>]+>", "", inline(t))))
        out.append('<h2 id="%s">%s</h2>' % (hid, inline(t)))
        i += 1
        continue
    if s.startswith("# "):
        flush()
        t = s[2:]
        title = t
        i += 1
        continue

    m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", s)
    if m:
        flush()
        out.append('<figure><img src="%s" alt="%s"><figcaption>%s</figcaption></figure>'
                   % (m.group(2), html.escape(m.group(1), quote=True), inline(m.group(1))))
        i += 1
        continue

    # HTML 图片块（README 里用的是 <p align=center><img ...></p>）
    if s.startswith("<p align") or s.startswith("<img") or s.startswith("<table") or s.startswith("<div"):
        flush()
        buf = []
        while i < len(lines) and lines[i].strip() != "":
            buf.append(lines[i])
            i += 1
        raw = "\n".join(buf)
        # 只保留图片与表格，其余 HTML 直出
        raw = re.sub(r'width="\d+"', 'width="100%"', raw)
        out.append(raw)
        continue

    if s.startswith("|"):
        flush()
        rows = []
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows.append(lines[i].strip())
            i += 1

        def cells(r):
            r = r.strip().strip("|")
            return [c.strip() for c in r.split("|")]

        head = cells(rows[0])
        body = [cells(r) for r in rows[1:] if not re.match(r"^[\s|:\-]+$", r)]
        ncol = len(head)
        mx = []
        for c in range(ncol):
            vals = [len(re.sub(r"[`*\[\]]", "", head[c]))] + [
                len(re.sub(r"[`*\[\]]", "", r[c])) for r in body if c < len(r)]
            mx.append(max(vals) if vals else 4)
        tot = sum(mx) or 1
        w = [max((x / tot) ** 0.85, 0.13) for x in mx]
        ssum = sum(w)
        w = [x / ssum for x in w]
        out.append("<table><colgroup>%s</colgroup><thead><tr>%s</tr></thead><tbody>"
                   % ("".join("<col style=\"width:%.1f%%\">" % (x * 100) for x in w),
                      "".join("<th>%s</th>" % inline(c) for c in head)))
        for r in body:
            out.append("<tr>%s</tr>" % "".join("<td>%s</td>" % inline(c) for c in r))
        out.append("</tbody></table>")
        continue

    if s.startswith("> "):
        flush()
        buf = []
        while i < len(lines) and lines[i].strip().startswith("> "):
            buf.append(lines[i].strip()[2:])
            i += 1
        out.append("<blockquote>%s</blockquote>" % inline(" ".join(buf)))
        continue

    if re.match(r"^\d+\.\s", s) or re.match(r"^[-*]\s", s):
        flush()
        tag = "ol" if re.match(r"^\d+\.\s", s) else "ul"
        items = []
        while i < len(lines) and (re.match(r"^\d+\.\s", lines[i].strip())
                                  or re.match(r"^[-*]\s", lines[i].strip())):
            items.append(re.sub(r"^(\d+\.|[-*])\s+", "", lines[i].strip()))
            i += 1
        out.append("<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % inline(x) for x in items), tag))
        continue

    para.append(s)
    i += 1

flush()

toc_html = "".join('<a href="#%s">%s</a>' % (h, t) for _, h, t in toc)

HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · 完整报告</title>
<style>
:root{--bg:#0f172a;--panel:#1e293b;--ink:#e2e8f0;--muted:#94a3b8;--blue:#60a5fa;--line:#334155;--amber:#f59e0b}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);line-height:1.85;
  font-family:"Noto Sans SC","PingFang SC","Microsoft YaHei",system-ui,sans-serif;
  -webkit-font-smoothing:antialiased;font-size:16px}
.topbar{position:sticky;top:0;z-index:20;background:rgba(15,23,42,.9);backdrop-filter:blur(10px);
  border-bottom:1px solid var(--line)}
.topbar .in{max-width:1180px;margin:0 auto;padding:0 24px;height:58px;display:flex;align-items:center;
  justify-content:space-between;gap:16px}
.topbar b{font-size:14.5px}
.topbar a{color:var(--muted);text-decoration:none;font-size:13.5px;padding:6px 11px;border-radius:8px}
.topbar a:hover{color:var(--ink);background:var(--panel)}
.layout{max-width:1180px;margin:0 auto;padding:32px 24px 80px;display:flex;gap:40px;align-items:flex-start}
aside{position:sticky;top:82px;width:216px;flex:0 0 216px;border-left:2px solid var(--line);padding-left:16px}
aside p{font-size:12px;letter-spacing:.14em;color:var(--muted);text-transform:uppercase;margin-bottom:10px}
aside a{display:block;color:var(--muted);text-decoration:none;font-size:13.5px;padding:4px 0}
aside a:hover{color:var(--blue)}
article{flex:1;min-width:0;max-width:820px}
h2{font-size:25px;line-height:1.4;margin:56px 0 18px;padding-bottom:12px;border-bottom:1px solid var(--line);
  scroll-margin-top:80px;letter-spacing:-.01em}
h2:first-child{margin-top:0}
h3{font-size:18.5px;margin:34px 0 12px;color:var(--blue);scroll-margin-top:80px}
p{margin:0 0 16px;color:#cbd5e1}
strong{color:#fff;font-weight:600}
a{color:var(--blue)}
ul,ol{margin:0 0 18px;padding-left:24px;color:#cbd5e1}
li{margin-bottom:7px}
blockquote{margin:0 0 20px;padding:14px 18px;border-left:3px solid var(--amber);
  background:rgba(245,158,11,.07);border-radius:0 10px 10px 0;color:#e8d9bd;font-size:15px}
blockquote p{margin:0;color:inherit}
code{background:#0b1220;border:1px solid var(--line);border-radius:5px;padding:1px 6px;
  font-family:"JetBrains Mono",Consolas,monospace;font-size:13.5px;color:#93c5fd}
pre{background:#0b1220;border:1px solid var(--line);border-radius:12px;padding:18px;overflow-x:auto;margin:0 0 22px}
pre code{background:none;border:none;padding:0;color:#cbd5e1;font-size:13px;line-height:1.7}
table{width:100%;border-collapse:collapse;margin:0 0 24px;font-size:14px;table-layout:fixed}
th{background:#16213a;color:#fff;font-weight:600;text-align:left;padding:10px 12px;border:1px solid var(--line)}
td{padding:9px 12px;border:1px solid var(--line);color:#cbd5e1;vertical-align:top;word-break:break-word}
tbody tr:nth-child(even){background:rgba(30,41,59,.45)}
figure{margin:24px 0 26px;text-align:center}
figure img{width:100%;border-radius:12px;border:1px solid var(--line);background:#fff}
figcaption{font-size:13px;color:var(--muted);margin-top:9px}
img{max-width:100%}
hr{border:none;border-top:1px solid var(--line);margin:44px 0}
.foot{max-width:1180px;margin:0 auto;padding:0 24px 60px;color:var(--muted);font-size:13px}
@media(max-width:900px){.layout{flex-direction:column;padding:22px 18px 60px}aside{display:none}table{font-size:13px}}
</style>
</head>
<body>
<div class="topbar"><div class="in">
  <b>大数据招聘岗位数据分析</b>
  <span><a href="index.html">← 可视化作品集</a><a href="README.md">仓库首页</a></span>
</div></div>

<div class="layout">
  <aside>
    <p>本页导航</p>
    __TOC__
  </aside>
  <article>
    __BODY__
    <hr>
    <p style="color:#94a3b8;font-size:14px">本页由 <code>src/build_report_html.py</code> 从 <code>REPORT.md</code> 自动生成。</p>
  </article>
</div>
<div class="foot">
  数据来源：和鲸社区公开数据集，仅用于学习与研究。
</div>
</body>
</html>
"""
HTML = (HTML.replace("__TITLE__", title)
            .replace("__TOC__", toc_html)
            .replace("__BODY__", "\n".join(out)))

open(OUT, "w", encoding="utf-8").write(HTML)
print("report.html 已生成：", OUT)
print("字符数:", len(HTML), "｜章数:", len(toc), "｜表格:", HTML.count("<table>") - 0,
      "｜图片:", HTML.count("<img"))
