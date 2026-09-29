# 浙江名人故居亲子游攻略（静态站点）

> 常住杭州市区的一家三口专用：市区内偏向公共交通，市区外偏向自驾，拥堵时改高铁。
> 67 处名人故居 / 纪念馆，覆盖浙江 11 个地市片区的 9 篇分册。

## 在线访问

GitHub Pages：`https://<你的用户名>.github.io/zhejiang-celebrity-homes/`

## 站点结构

| 页面 | 内容 |
|---|---|
| `index.html` | 总览与出行指南：交通决策原则、高铁/自驾门到门耗时、7 条推荐线路、亲子研学设计、预算、避坑清单、电话速查 |
| `01-hangzhou.html` | 杭州篇 12 处 |
| `02-shaoxing.html` | 绍兴篇 11 处 |
| `03-ningbo.html` | 宁波篇 9 处 |
| `04-jiaxing-huzhou.html` | 嘉兴·湖州篇 10 处 |
| `05-jinhua.html` | 金华篇 9 处 |
| `06-taizhou.html` | 台州篇 4 处 |
| `07-wenzhou.html` | 温州篇 9 处 |
| `08-quzhou-lishui.html` | 衢州·丽水篇 3 处 |
| `all.html` | 全省速查表：关键词搜索 + 地市/门票/周一/预约四维筛选 + 手气不错随机推荐 |

每个点位卡片统一字段：地址 / 名人简介 / 门票 / 开放时间 / 建议时长 / 亲子看点 / 交通（自驾+公交双方案）/ 停车 / 周边串联。
徽标自动派生：**免费**、**票价**、**周一闭馆**、**须提前预约**、**凭证/预约入馆**，并附高德地图导航链接。

## 从 Markdown 重新构建

源稿件在 `source/*.md`，改动后执行：

```bash
python tools/build.py
```

脚本只依赖 Python 标准库，重新生成全部 HTML 与 `assets/data.js`（`all.html` 的搜索数据源）。

## 本地预览

```bash
python -m http.server 8765
# 打开 http://127.0.0.1:8765/
```

## 部署说明

静态站点，零外部依赖（无 CDN、无构建工具），适合 GitHub Pages：

1. Pages 来源设为 **Deploy from a branch → main / root**；
2. 仓库根目录保留 `.nojekyll`，避免 Jekyll 额外处理。

## 免责声明

门票、开放时间、预约规则变动频繁。所有内容整理于 **2026 年 9 月 28 日**，出行前请按《出行前确认清单》电话复核，尤其注意标红的高风险点位。
