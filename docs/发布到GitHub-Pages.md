# 发布到 GitHub Pages

> 从零到线上可访问，约 10 分钟。**以下命令在仓库根目录执行。**

---

## 第 0 步：先改 3 个占位符

发布前必须替换，否则页面上会露出 `your-username`、`your-email@example.com`。

| 文件 | 位置 | 改成 |
| :--- | :--- | :--- |
| `README.md` | 顶部 `在线作品集` 链接 | `https://<你的用户名>.github.io/bigdata-job-analysis/` |
| `README.md` | 顶部 `git clone` 命令 | `https://github.com/<你的用户名>/bigdata-job-analysis.git` |
| `README.md` | 文末「关于我」 | 你的邮箱 |
| `LICENSE` | `Copyright (c) 2026 <YOUR NAME>` | 你的名字 |

> 快速替换（把 `your-username` 换成你的 GitHub 用户名）：
> ```bash
> # macOS / Linux / Git Bash
> grep -rl "your-username" . | xargs sed -i 's/your-username/你的用户名/g'
> ```

---

## 第 1 步：初始化仓库并推送

```bash
# 初始化
git init -b main
git add .
git commit -m "feat: 大数据招聘岗位数据分析项目（报告 + 图表 + 面试材料）"

# 在 GitHub 上先建一个空仓库，名字建议就叫 bigdata-job-analysis
git remote add origin https://github.com/<你的用户名>/bigdata-job-analysis.git
git push -u origin main
```

> ⚠️ **不要提交原始 CSV**。`.gitignore` 已经排除了 `data/*.csv`，如果之前手动 `git add` 过，先执行
> `git rm --cached data/*.csv`。

---

## 第 2 步：开启 GitHub Pages

1. 打开仓库 → **Settings** → 左侧 **Pages**
2. **Source** 选 `Deploy from a branch`
3. **Branch** 选 `main`，目录选 `/ (root)` → **Save**
4. 等 1–2 分钟，页面顶部会出现访问地址：

```
https://<你的用户名>.github.io/bigdata-job-analysis/
```

5. 把这个地址填回 `README.md` 顶部的「在线作品集」链接，再提交一次：

```bash
git add README.md && git commit -m "docs: 补充 Pages 地址" && git push
```

---

## 第 3 步：验证三个页面

| 访问路径 | 应该看到 |
| :--- | :--- |
| `/` | 深色看板：四张图 + 四条结论（`index.html`） |
| `/report.html` | 完整报告，左侧有章节导航（由 `REPORT.md` 生成） |
| 仓库首页 | `README.md` 渲染结果，四张图并排显示 |

---

## 可选：加一条一键部署命令

如果之后改了报告内容，重新生成网页版再推送：

```bash
python src/build_report_html.py   # REPORT.md → report.html
git add report.html && git commit -m "docs: 更新报告" && git push
```

---

## 常见问题

### Q1：README 里的图片不显示

GitHub 渲染 README 时按**相对路径**找图，路径必须是从仓库根目录算起的 `images/xxx.png`。
如果你把 README 放进了子目录，路径要改成 `../images/xxx.png`。

### Q2：Pages 打开是 404

三种常见原因：

1. **仓库是私有的** —— GitHub Pages 免费版只支持公开仓库（私有仓库需要 Pro）；
2. **分支选错了** —— 确认是 `main` 而不是 `master`，且刚提交过；
3. **刚开启还没构建完** —— 等 1–2 分钟，或在 Settings → Pages 里看构建状态。

### Q3：`report.html` 更新后内容没变

浏览器缓存。强制刷新（`Ctrl/Cmd + Shift + R`），或者等 Pages 重新构建（通常 30–60 秒）。

### Q4：想换成自己的域名

Settings → Pages → Custom domain 填入域名，然后在域名服务商处加一条 CNAME 记录指向
`<你的用户名>.github.io`。同时在仓库根目录放一个 `CNAME` 文件，内容是你的域名。

---

## 附：哪些文件不该进仓库

| 文件 | 原因 |
| :--- | :--- |
| `data/*.csv` | 25 MB，且版权归原发布方（见 `data/README.md`） |
| `data/clean_jobs.csv` | 清洗产物，可复现，不必入库 |
| `__pycache__/`、`.venv/` | 环境产物 |
| `output/`、`working/` | 文档生成的中间产物 |

`.gitignore` 已覆盖以上全部。
