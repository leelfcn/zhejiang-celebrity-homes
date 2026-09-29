# -*- coding: utf-8 -*-
"""
把 source/*.md（名人名居攻略分册）构建成纯静态站点，输出到站点根目录。

用法：
    python tools/build.py

依赖：仅 Python 标准库。输出为静态 HTML/CSS/JS，无任何外部 CDN 依赖，
可直接托管到 GitHub Pages。
"""
import json
import os
import re
from collections import OrderedDict
from urllib.parse import quote_plus

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "source")
OUT = ROOT

CHAPTERS = [
    ("00", "index", "总览与出行指南", "index.html", "🏠"),
    ("01", "hangzhou", "杭州篇", "01-hangzhou.html", "🏙️"),
    ("02", "shaoxing", "绍兴篇", "02-shaoxing.html", "🎋"),
    ("03", "ningbo", "宁波篇", "03-ningbo.html", "⚓"),
    ("04", "jiaxing-huzhou", "嘉兴·湖州篇", "04-jiaxing-huzhou.html", "🌾"),
    ("05", "jinhua", "金华篇", "05-jinhua.html", "🔥"),
    ("06", "taizhou", "台州篇", "06-taizhou.html", "⛰️"),
    ("07", "wenzhou", "温州篇", "07-wenzhou.html", "🌊"),
    ("08", "quzhou-lishui", "衢州·丽水篇", "08-quzhou-lishui.html", "🏔️"),
]
CHAPTER_FILES = {c[0]: c[3] for c in CHAPTERS}

FIELD_KEY = {
    "名人简介": "简介",
    "人物简介": "简介",
    "交通 / 停车": "交通",
    "周边美食": "周边",
    "顺路加一站": "周边",
    "周边串联": "周边",
    "咨询": "电话",
    "推荐半日线": "推荐玩法",
}
FIELD_ORDER = ["地址", "简介", "门票", "开放时间", "建议时长", "亲子看点",
               "交通", "停车", "电话", "周边", "推荐玩法"]
FIELD_ICON = {
    "地址": "📍", "简介": "👤", "门票": "🎟️", "开放时间": "🕘",
        "建议时长": "⏱️", "亲子看点": "👀", "交通": "🚗", "停车": "🅿️",
        "电话": "☎️", "周边": "🍜", "推荐玩法": "🧭",
}
CITY_ALIAS = {
    "01": "杭州", "02": "绍兴", "03": "宁波", "04": "嘉兴·湖州",
    "05": "金华", "06": "台州", "07": "温州", "08": "衢州·丽水",
}


# ---------------------------------------------------------------- 行内渲染
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(text):
    """极简行内 markdown：**粗体**、*斜体*、`代码`、[链接](url)。"""
    text = esc(text)
    text = re.sub(r"`([^`]+)`", r'<code>\1</code>', text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    return text


# ---------------------------------------------------------------- 块级解析
def split_blocks(text):
    """把 markdown 切成 (kind, payload) 列表。"""
    lines = text.split("\n")
    blocks = []
    i = 0
    para = []

    def flush():
        if para:
            blocks.append(("p", " ".join(x.strip() for x in para if x.strip())))
            del para[:]

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()
        s = line.strip()

        if not s:
            flush()
            i += 1
            continue

        if s.startswith("|") and s.count("|") >= 2:
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(set(c) <= set("-: ") for c in row):
                    rows.append(row)
                i += 1
            blocks.append(("table", rows))
            continue

        if s.startswith("### "):
            flush()
            blocks.append(("h3", s[4:]))
            i += 1
            continue

        if s.startswith("## "):
            flush()
            blocks.append(("h2", s[3:]))
            i += 1
            continue

        if s.startswith("# "):
            flush()
            blocks.append(("h1", s[2:]))
            i += 1
            continue

        if s.startswith(">"):
            flush()
            quoted = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quoted.append(lines[i].strip().lstrip(">").strip())
                i += 1
            blocks.append(("quote", quoted))
            continue

        if s in ("---", "***", "___"):
            flush()
            i += 1
            continue

        m = re.match(r"^(\d+)\.\s+(.*)$", s)
        if m:
            flush()
            items = []
            while i < len(lines):
                cur = lines[i].strip()
                mm = re.match(r"^(\d+)\.\s+(.*)$", cur)
                if mm:
                    items.append(mm.group(2))
                elif cur and items and not cur.startswith(("#", ">", "|", "---")):
                    items[-1] += " " + cur
                elif not cur:
                    break
                else:
                    break
                i += 1
            blocks.append(("ol", items))
            continue

        if s.startswith("- ") or s.startswith("* "):
            flush()
            items = []
            while i < len(lines):
                cur = lines[i].strip()
                if cur.startswith("- ") or cur.startswith("* "):
                    items.append(cur[2:])
                elif cur and items and not cur.startswith(("#", ">", "|", "---")):
                    items[-1] += " " + cur
                elif not cur:
                    break
                else:
                    break
                i += 1
            blocks.append(("ul", items))
            continue

        para.append(s)
        i += 1

    flush()
    return blocks


def render_blocks(blocks, start_h=2):
    """通用块渲染（用于总览页等非卡片章节）。"""
    out = []
    for kind, payload in blocks:
        if kind == "h1":
            continue
        elif kind == "h2":
            out.append('<h2 id="%s">%s</h2>' % (anchor(payload), inline(payload)))
        elif kind == "h3":
            out.append('<h3 id="%s">%s</h3>' % (anchor(payload), inline(payload)))
        elif kind == "p":
            out.append("<p>%s</p>" % inline(payload))
        elif kind == "quote":
            inner = "".join("<p>%s</p>" % inline(x) for x in payload)
            out.append("<blockquote>%s</blockquote>" % inner)
        elif kind == "ul":
            out.append("<ul>%s</ul>" % "".join("<li>%s</li>" % inline(x) for x in payload))
        elif kind == "ol":
            out.append("<ol>%s</ol>" % "".join("<li>%s</li>" % inline(x) for x in payload))
        elif kind == "table":
            out.append(render_table(payload))
    return "\n".join(out)


def render_table(rows):
    if not rows:
        return ""
    head, body = rows[0], rows[1:]
    th = "".join("<th>%s</th>" % inline(c) for c in head)
    trs = []
    for r in body:
        cells = []
        for idx, c in enumerate(r):
            key = head[idx] if idx < len(head) else ""
            cells.append('<td data-label="%s">%s</td>' % (esc(key), inline(c)))
        trs.append("<tr>%s</tr>" % "".join(cells))
    return ('<div class="table-wrap"><table class="grid-table">'
            "<thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>" % (th, "".join(trs)))


def anchor(text):
    t = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text).strip("-").lower()
    return t or "sec"


# ---------------------------------------------------------------- 分册解析
def parse_chapter(num, text):
    blocks = split_blocks(text)
    # 剥离标题
    title = ""
    if blocks and blocks[0][0] == "h1":
        title = blocks[0][1]
        blocks = blocks[1:]

    intro_units = []   # 速查表之前的引子
    quick_rows = []
    spots = []
    tail = OrderedDict()   # 线路建议 / 避坑提示等：h2 -> blocks
    cur_target = intro_units
    cur_tail_key = None

    for kind, payload in blocks:
        if kind == "h2":
            name = payload
            if name.startswith("速查表"):
                cur_tail_key = None
                cur_target = intro_units
                cur_target.append(("h2", name))
                continue
            m = re.match(r"^(\d+)\.\s*(.+)$", name)
            if m:
                cur_tail_key = None
                idx = int(m.group(1))
                rest = m.group(2).strip()
                stars = rest.count("⭐")
                clean = re.sub(r"[⭐\s]+$", "", rest)
                note = ""
                mm = re.search(r"（全省亲子第一站）", clean)
                if mm:
                    note = mm.group(0)
                    clean = clean.replace(mm.group(0), "").strip()
                    clean = re.sub(r"[⭐\s]+$", "", clean)
                spots.append({"idx": idx, "name": clean, "stars": stars,
                              "note": note, "blocks": []})
                cur_target = spots[-1]["blocks"]
                continue
            cur_tail_key = name
            tail[name] = []
            cur_target = tail[name]
            continue
        cur_target.append((kind, payload))
        if kind == "table" and quick_rows == []:
            quick_rows = payload

    return {"num": num, "title": title, "intro": intro_units,
            "quick": quick_rows, "spots": spots, "tail": tail}


LABEL_RE = re.compile(r"^\*\*(.+?)\*\*[：:]\s*(.*)$")


def spot_fields(spot):
    """把卡片的 `- **标签**：内容` 转成有序字段列表；其余块原样保留。"""
    fields = OrderedDict()
    extras = []
    for kind, payload in spot["blocks"]:
        if kind == "ul":
            for item in payload:
                m = LABEL_RE.match(item)
                if m:
                    key = FIELD_KEY.get(m.group(1).strip(), m.group(1).strip())
                    fields.setdefault(key, []).append(m.group(2).strip())
                else:
                    extras.append(("ul", [item]))
        elif kind == "p" and not payload.strip():
            continue
        else:
            extras.append((kind, payload))
    ordered = []
    for key in FIELD_ORDER:
        for val in fields.pop(key, []):
            ordered.append((key, val))
    for key, vals in fields.items():
        for val in vals:
            ordered.append((key, val))
    return ordered, extras


def is_free(ticket):
    if not ticket:
        return False
    t = ticket.strip()
    if re.search(r"需买|买.{0,6}联票|度假区票", t):
        return False
    if re.search(r"\d+\s*元", t):
        return False
    return "免费" in t


def plain(s):
    """去掉行内 markdown 记号，用于 JSON 数据。"""
    s = re.sub(r"\s+", " ", (s or "").strip())
    return s.replace("**", "").replace("`", "")


def booking_level(*texts):
    """返回 0=无需预约 / 1=凭证件或现场预约入馆 / 2=需明确预约（建议出发前搞定）。"""
    joined = " ".join(t or "" for t in texts)
    joined = re.sub(r"团体预约电话\s*[\d\-—]+", "", joined)
    joined = re.sub(r"（?是否需预约待核实）?", "", joined)
    for neg in ["无需预约", "不用预约", "不需预约", "一般无需", "免预约"]:
        joined = joined.replace(neg, "")
    if "必须预约" in joined:
        return 2
    if "待核实" in joined and "预约" not in joined.split("待核实")[0]:
        return 0
    patterns = [r"预约[：:]", r"需预约", r"须预约", r"扫码预约", r"免费预约",
                r"凭身份证\s*[/、,，]?\s*预约", r"预约入馆", r"预约后进馆",
                r"分时.{0,4}预约", r"提前.{0,4}预约"]
    if not any(re.search(p, joined) for p in patterns):
        return 0
    if re.search(r"（需预约）|公众号|先约", joined):
        return 2
    return 1


def weekday_status(val):
    """返回 open / closed / unknown"""
    v = (val or "").strip()
    if not v or "待核实" in v or "口径不一" in v:
        return "unknown"
    if "闭馆" in v or "不开放" in v:
        return "closed"
    return "open"


# ---------------------------------------------------------------- 页面组装
CSS_LINK = '<link rel="stylesheet" href="assets/style.css">'


def nav_html(active):
    items = []
    for num, _slug, name, fname, emoji in CHAPTERS:
        cls = " active" if num == active else ""
        items.append('<a class="nav-item%s" href="%s"><span>%s</span>%s</a>'
                     % (cls, fname, emoji, name))
    items.append('<a class="nav-item%s" href="all.html"><span>🧭</span>全省速查</a>'
                 % (" active" if active == "all" else ""))
    return "".join(items)


def page_shell(active, title, desc, main_html, extra_js=""):
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%s · 浙江名人故居亲子游攻略</title>
<meta name="description" content="%s">
<meta property="og:title" content="%s">
<meta property="og:description" content="%s">
%s
</head>
<body>
<header class="site-head">
  <div class="wrap head-inner">
    <a class="brand" href="index.html"><span class="brand-mark">浙</span><span class="brand-txt">名人故居<em>亲子游攻略</em></span></a>
    <button class="nav-toggle" id="navToggle" aria-label="目录">☰ 目录</button>
    <nav class="topnav" id="topNav">%s</nav>
  </div>
</header>
<div class="wrap layout">
%s
</div>
<footer class="site-foot">
  <div class="wrap">
    <p>资料整理日期：2026 年 9 月 28 日 · 门票、开放时间、预约规则变动频繁，出行前请务必按《出行前确认清单》电话复核。</p>
    <p class="muted">静态站点 · 由 <code>tools/build.py</code> 从 <code>source/*.md</code> 自动生成 · 无外部依赖</p>
  </div>
</footer>
<script src="assets/app.js"></script>
%s
</body>
</html>
""" % (esc(title), esc(desc), esc(title), esc(desc), CSS_LINK,
       nav_html(active), main_html, extra_js)


def build_home(doc, spot_index):
    at_glance = doc["intro"]
    body = []
    body.append('<section class="hero">')
    body.append('<div class="hero-txt">')
    body.append('<p class="kicker">常住杭州市区 · 一家三口 · 孩子小学阶段</p>')
    body.append("<h1>浙江名人故居<br>亲子游完全攻略</h1>")
    body.append('<p class="hero-sub">%d 处名人故居与纪念馆，覆盖浙江 11 个地市。'
                '市区坐地铁、出城自驾或高铁，带娃把语文课本里的名字走成真人。</p>' % len(spot_index))
    body.append('<div class="stat-row">')
    for val, lab in [(len(spot_index), "处故居/纪念馆"),
                     (len({s["city"] for s in spot_index}), "个地市片区"),
                     (sum(1 for s in spot_index if s["free"]), "处免费开放"),
                     (sum(1 for s in spot_index if s["monday_closed"]), "处周一闭馆")]:
        body.append('<div class="stat"><b>%s</b><span>%s</span></div>' % (val, lab))
    body.append("</div>")
    body.append('<div class="hero-cta">')
    body.append('<a class="btn primary" href="all.html">🧭 全省速查 / 筛选</a>')
    body.append('<a class="btn" href="#xianlu">🚗 直接看线路</a>')
    body.append('<a class="btn" href="#checklist">☎️ 出行前确认清单</a>')
    body.append("</div></div>")
    body.append('<aside class="hero-card"><h3>三句话决策</h3><ol>'
                "<li><strong>杭州市内</strong>一律公共交通：老巷弄没处停车，西湖景区周末单双号限行。</li>"
                "<li><strong>出市区</strong>优先自驾；单程超 2.5 小时或目的地是古城核心区，改高铁。</li>"
                "<li><strong>高铁＋落地打车</strong>是带娃最优解，绝大多数点位出站 10–30 分钟即到。</li>"
                "</ol></aside>")
    body.append("</section>")

    body.append('<section class="chapter-grid" id="fence">')
    body.append('<h2 class="sec-title">按地市翻阅</h2>')
    for num, _slug, name, fname, emoji in CHAPTERS[1:]:
        spots = [s for s in spot_index if s["num"] == num]
        free_cnt = sum(1 for s in spots if s["free"])
        body.append('<a class="chap-card" href="%s"><span class="chap-emoji">%s</span>'
                    '<b>%s</b><span class="chap-meta">%d 处 · %d 处免费</span>'
                    '<span class="chap-more">查看 →</span></a>'
                    % (fname, emoji, name, len(spots), free_cnt))
    body.append("</section>")

    body.append('<article class="prose">')
    body.append(render_blocks([b for b in doc["intro"] if b[0] != "h2"]))
    # 逐节渲染正文（去掉已单独呈现的速查区）
    for sec_name, sec_blocks in doc["tail"].items():
        aid = anchor(sec_name)
        if re.search(r"确认清单", sec_name):
            aid = "checklist"
        if re.search(r"推荐线路", sec_name):
            aid = "xianlu"
        body.append('<h2 id="%s">%s</h2>' % (aid, inline(sec_name)))
        body.append(render_blocks(sec_blocks))
    body.append("</article>")
    return "\n".join(body)


def build_chapter(doc, spot_index):
    num = doc["num"]
    ch = next(c for c in CHAPTERS if c[0] == num)
    spots = doc["spots"]
    meta = {(s["num"], s["idx"]): s for s in spot_index}

    main = []
    main.append('<nav class="crumb"><a href="index.html">总览</a> / <span>%s</span></nav>' % ch[2])
    main.append('<header class="chap-head">')
    main.append('<h1>%s</h1>' % inline(doc["title"]))
    intro_html = render_blocks([b for b in doc["intro"] if b[0] == "quote"])
    main.append(intro_html)
    main.append("</header>")

    # 侧栏目录
    toc = ['<nav class="toc"><b>本篇点位</b><ol>']
    for s in spots:
        toc.append('<li><a href="#p-%s-%d">%s</a></li>' % (num, s["idx"], esc(s["name"])))
    for sec in doc["tail"].keys():
        toc.append('<li class="toc-sec"><a href="#%s">%s</a></li>' % (anchor(sec), esc(sec)))
    toc.append("</ol></nav>")

    content = ['<div class="chap-body">']
    if doc["quick"]:
        content.append('<h2 id="quick">速查表</h2>')
        content.append(render_table(doc["quick"]))
    for s in spots:
        m = meta.get((num, s["idx"]), {})
        fields, extras = spot_fields(s)
        badges = []
        ticket = first_val(fields, "门票")
        if m.get("free"):
            badges.append('<span class="badge free">免费</span>')
        elif ticket:
            tk = plain(ticket)
            m2 = re.search(r"[\d]+(?:\s*[–—~～]\s*[\d]+)?\s*元", tk)
            if m2:
                badges.append('<span class="badge paid">%s%s</span>'
                              % (m2.group(0), "起" if "起" in tk else ""))
        if m.get("monday_closed"):
            badges.append('<span class="badge warn">周一闭馆</span>')
        if m.get("booking_level", 0) == 2:
            badges.append('<span class="badge info">须提前预约</span>')
        elif m.get("booking_level", 0) == 1:
            badges.append('<span class="badge soft">凭证 / 预约入馆</span>')
        content.append('<section class="spot" id="p-%s-%d">' % (num, s["idx"]))
        stars = "⭐" * s["stars"] if s["stars"] else ""
        content.append('<h2 class="spot-title"><span class="spot-idx">%02d</span>%s%s</h2>'
                       % (s["idx"], esc(s["name"]), '<span class="stars">%s</span>' % stars))
        if badges:
            content.append('<div class="badges">%s</div>' % "".join(badges))
        rows = []
        for key, val in fields:
            icon = FIELD_ICON.get(key, "🔹")
            cls = "f-%s" % {"地址": "addr", "简介": "intro"}.get(key, "")
            rows.append('<div class="frow %s"><dt>%s %s</dt><dd>%s</dd></div>'
                        % (cls, icon, esc(key), inline(val)))
        content.append('<dl class="fields">%s</dl>' % "".join(rows))
        addr = first_val(fields, "地址")
        if addr:
            dest = quote_plus((addr + " " + s["name"]).strip())
            content.append('<div class="spot-actions">'
                           '<a class="nav-btn" target="_blank" rel="noopener" '
                           'href="https://uri.amap.com/search?keyword=%s">📍 高德地图导航</a>'
                           '<a class="nav-btn" target="_blank" rel="noopener" '
                           'href="https://www.amap.com/search?query=%s">🗺️ 查看周边</a>'
                           "</div>" % (dest, dest))
        if extras:
            content.append('<div class="spot-extra">%s</div>' % render_blocks(extras))
        content.append("</section>")
    for sec, blocks in doc["tail"].items():
        content.append('<h2 id="%s">%s</h2>' % (anchor(sec), inline(sec)))
        content.append(render_blocks(blocks))
    content.append("</div>")

    prev_next = chapter_pager(num)
    main.append('<div class="two-col">%s%s</div>' % ("".join(content), toc))
    main.append(prev_next)
    return "\n".join(main)


def first_val(fields, key):
    for k, v in fields:
        if k == key:
            return v
    return ""


def chapter_pager(num):
    order = [c for c in CHAPTERS]
    pos = [i for i, c in enumerate(order) if c[0] == num][0]
    prev_c = order[pos - 1] if pos > 0 else None
    next_c = order[pos + 1] if pos < len(order) - 1 else None
    html = ['<nav class="pager">']
    if prev_c:
        html.append('<a href="%s">← %s</a>' % (prev_c[3], prev_c[2]))
    else:
        html.append("<span></span>")
    html.append('<a class="to-all" href="all.html">全省速查</a>')
    if next_c:
        html.append('<a href="%s">%s →</a>' % (next_c[3], next_c[2]))
    else:
        html.append("<span></span>")
    html.append("</nav>")
    return "".join(html)


def build_all(spot_index):
    main = []
    main.append('<nav class="crumb"><a href="index.html">总览</a> / <span>全省速查</span></nav>')
    main.append('<header class="chap-head"><h1>全省 %d 处速查表</h1>'
                '<blockquote><p>支持关键词搜索、按地市 / 是否免费 / 周一是否闭馆筛选，'
                '点名称跳转完整介绍。</p></blockquote></header>' % len(spot_index))
    main.append('<div class="filters">')
    main.append('<input type="search" id="q" class="f-input" placeholder="搜名称、城市或名人，例如：鲁迅 / 免费 / 周一">')
    main.append('<select id="f-city" class="f-select"><option value="">全部地市</option>%s</select>'
                % "".join('<option value="%s">%s</option>' % (CITY_ALIAS[n], CITY_ALIAS[n])
                          for n in sorted(set(s["num"] for s in spot_index), key=lambda x: x)))
    main.append('<select id="f-ticket" class="f-select"><option value="">门票不限</option>'
                '<option value="free">仅免费</option><option value="paid">仅收费</option></select>')
    main.append('<select id="f-mon" class="f-select"><option value="">周一不限</option>'
                '<option value="open">周一开放</option><option value="closed">周一闭馆</option>'
                '<option value="unknown">周一待核实</option></select>')
    main.append('<select id="f-book" class="f-select"><option value="">预约不限</option>'
                '<option value="yes">仅需预约</option><option value="no">仅免预约</option></select>')
    main.append('<button class="btn ghost" id="lucky" type="button">🎲 手气不错</button>')
    main.append('<span class="f-count" id="count"></span>')
    main.append("</div>")
    main.append('<div class="table-wrap"><table class="grid-table" id="spotTable">'
                "<thead><tr><th>地市</th><th>名称</th><th>门票</th><th>开放时间</th>"
                "<th>周一</th><th>时长</th><th>交通要点</th></tr></thead>"
                '<tbody></tbody></table></div>')
    main.append('<p class="empty-tip" id="emptyTip" hidden>没有符合条件的点位，换个关键词试试。</p>')
    return "\n".join(main)


# ---------------------------------------------------------------- 主流程
def load_spot_index(docs):
    idx = []
    for num in ["01", "02", "03", "04", "05", "06", "07", "08"]:
        doc = docs[num]
        head = doc["quick"][0] if doc["quick"] else []
        rows = doc["quick"][1:] if doc["quick"] else []
        # 速查表行序与卡片序号完全对应；先按下标对齐，再用名称兜底
        for order, s in enumerate(doc["spots"]):
            fields, _ = spot_fields(s)
            fmap = {}
            for k, v in fields:
                fmap.setdefault(k, v)
            qrow = {}
            if rows and len(rows) == len(doc["spots"]):
                for i, cell in enumerate(rows[order]):
                    if i < len(head):
                        qrow[head[i]] = cell
            if not qrow:
                for r in rows:
                    if r and (r[0].strip() == s["name"] or r[0].strip().startswith(s["name"][:5])):
                        for i, cell in enumerate(r):
                            if i < len(head):
                                qrow[head[i]] = cell
                        break
            ticket = plain(qrow.get("门票", fmap.get("门票", "")))
            monday = plain(qrow.get("周一", ""))
            idx.append({
                "num": num,
                "city": CITY_ALIAS[num],
                "idx": s["idx"],
                "name": s["name"],
                "stars": s["stars"],
                "ticket": ticket,
                "hours": plain(qrow.get("开放时间", fmap.get("开放时间", ""))),
                "monday": monday,
                "duration": plain(qrow.get("建议时长", fmap.get("建议时长", ""))),
                "traffic": plain(qrow.get("交通要点", "")),
                "addr": plain(qrow.get("地址", fmap.get("地址", ""))),
                "figure": plain((fmap.get("简介", ""))[:110]),
                "url": "%s#p-%s-%d" % (CHAPTER_FILES[num], num, s["idx"]),
                "free": is_free(ticket) or (not ticket and "免费" in fmap.get("门票", "")),
                "booking": booking_level(fmap.get("门票", "")) > 0,
                "booking_level": booking_level(fmap.get("门票", "")),
            })
            idx[-1]["monday_status"] = weekday_status(idx[-1]["monday"])
            idx[-1]["monday_closed"] = (idx[-1]["monday_status"] == "closed")
    return idx


def main():
    docs = {}
    for num, _slug, name, fname, emoji in CHAPTERS:
        path = os.path.join(SRC, "%s.md" % num)
        docs[num] = parse_chapter(num, open(path, encoding="utf-8").read())

    spot_index = load_spot_index(docs)

    # 1. 首页（总览）
    html = page_shell("00", "总览与出行指南",
                      "浙江名人故居亲子游完全攻略：66 处故居、11 个地市、9 篇分册，含门票、开放时间、交通双方案与线路组合。",
                      build_home(docs["00"], spot_index))
    write(os.path.join(OUT, "index.html"), html)

    # 2. 各分册
    for num, _slug, name, fname, emoji in CHAPTERS[1:]:
        doc = docs[num]
        cnt = len(doc["spots"])
        desc = "%s：%d 处名人故居，含门票、开放时间、地址、亲子看点、自驾与公共交通双方案。" % (doc["title"] or name, cnt)
        html = page_shell(num, doc["title"] or name, desc, build_chapter(doc, spot_index))
        write(os.path.join(OUT, fname), html)

    # 3. 全省速查
    html = page_shell("all", "全省速查", "浙江名人故居全省速查表，支持搜索与多维筛选。",
                      build_all(spot_index),
                      extra_js='<script src="assets/data.js"></script><script src="assets/table.js"></script>')
    write(os.path.join(OUT, "all.html"), html)

    # 4. 数据文件
    js = "window.SPOTS = %s;\n" % json.dumps(spot_index, ensure_ascii=False, indent=1)
    write(os.path.join(OUT, "assets", "data.js"), js)

    print("已生成：index.html + %d 篇分册 + all.html，共 %d 处点位"
          % (len(CHAPTERS) - 1, len(spot_index)))
    free_cnt = sum(1 for s in spot_index if s["free"])
    print("免费 %d 处 / 收费 %d 处 / 周一闭馆 %d 处 / 需预约 %d 处"
          % (free_cnt, len(spot_index) - free_cnt,
             sum(1 for s in spot_index if s["monday_closed"]),
             sum(1 for s in spot_index if s["booking"])))


def write(path, content):
    # 兜底清理：不应再出现未渲染的行内记号
    content = content.replace("**", "")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


if __name__ == "__main__":
    main()
