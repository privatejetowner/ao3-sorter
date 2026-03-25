
"""
AO3 Kudos/Hits Ratio Sorter
============================
抓取AO3指定tag下的所有作品，按 kudos/hits 比排序，生成交互式HTML页面。

使用方法:
  1. 在下方 COOKIES 中粘贴你的AO3 cookie
  2. 运行: python3 ao3_sorter.py
  3. 输入tag名称（如：桂瑞）或完整tag URL
  4. 等待抓取完成，自动生成并打开HTML文件
"""

from bs4 import BeautifulSoup
import subprocess
import time
import json
import sys
import re
import os
import webbrowser
from urllib.parse import quote, urljoin, urlparse, parse_qs

# ============================================================
# 配置区 - 请修改这里
# ============================================================

# 把你浏览器里的完整 cookie 字符串粘贴在这里（一整行）
# 获取方法：浏览器打开AO3 → F12开发者工具 → Network → 刷新页面
# → 点击任意请求 → Headers → 找到 Cookie: 后面的整串复制过来
COOKIE_STRING = "view_adult=true; _cfuvid=Iro0yk1mzIdi.LYtbe2IUd42lyxis4Vkjk9VSGyDoPo-1773116632.2244139-1.0.1.1-0JkqdTmIs2QmKDnGOW0scuKf_vnul3AtL7Rk.SJmZug; cf_clearance=NF0FY1yt8_N13BEoiCTrMAPHRMNJJaTIeY3hjz0BVvs-1773116655-1.2.1.1-hxcCOSDDY9CT7w5P0uz7O.hBZJtqXkCZ_2QIavT0dgSj4Q1kKXopBMt40ujC9LbpAf6v866ye5clgC_IlP.huShMtFMkS709_Nube67IuSm4eaiD3mGt5wG0Rj96bnUOtp_95PtmYDSZkt4YMRJJfPFyPE3m9X03fS4rC4rHMbWz0sx77GSK7hcHouBYMENVKPn8kGmq03435TB.JlaZ3l3ng4LWvQdVhhp7z7qayyQ; __cf_bm=guigmOfx8.WHAtkPWwzUzj5ei5UPqfrUh0Qiziwdy58-1773116655.781981-1.0.1.1-kOLFppyrH7f91aFIOm.EZofG0neUlmiV3boQEOUS_hmSZoNDNbetgHzZzSItp1LQSKwM0osIV09driG2Us9SMQDGwnoNEOKpu06HlEkWHHx34b4kzsx2VarlKEzHeLtz; _otwarchive_session=eyJfcmFpbHMiOnsibWVzc2FnZSI6ImV5SnpaWE56YVc5dVgybGtJam9pTm1Ga1pHRXhNems0TVdJek16QXhPV1ZqWkRFd01EQTNOV1E1T1Rjek16TWlMQ0pmWTNOeVpsOTBiMnRsYmlJNklrZG5WRVIxYW1ZMVFtOUZaV28wV1V0NFF6ZGhlRmhPTmswNWVFdFJYMk5VTnpKQk1rMHRjSEZvTkdNaWZRPT0iLCJleHAiOiIyMDI2LTAzLTI0VDA0OjI0OjIzLjM0MloiLCJwdXIiOiJjb29raWUuX290d2FyY2hpdmVfc2Vzc2lvbiJ9fQ%3D%3D--005e161c5d5e7c2f1244f3f815eae0a4f6a0ee20"
# 例如：
# COOKIE_STRING = "view_adult=true; remember_user_token=xxx; user_credentials=1; _otwarchive_session=xxx; cf_clearance=xxx; __cf_bm=xxx"

# 每次请求之间的等待时间（秒），对AO3友好一点
REQUEST_DELAY = 1.5

# 最大重试次数
MAX_RETRIES = 5

# ============================================================


def build_tag_url(tag_input):
    """从用户输入构建tag URL"""
    tag_input = tag_input.strip()
    if tag_input.startswith("http"):
        # 用户给了完整URL，去掉已有的page参数
        base = tag_input.split("?")[0].rstrip("/")
        return base
    else:
        encoded = quote(tag_input, safe="")
        # 用 /tags/X 而非 /tags/X/works，和浏览器翻页行为一致
        return f"https://archiveofourown.org/tags/{encoded}"


def fetch_page(url, page=1):
    """用 curl 抓取单页，绕过 Cloudflare"""
    sep = "&" if "?" in url else "?"
    full_url = f"{url}{sep}page={page}"

    curl_cmd = [
        "curl", "-s", "-L",
        "--max-time", "30",
        "-H", "accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "-H", "accept-language: en,zh-CN;q=0.9,zh;q=0.8",
        "-H", f"cookie: {COOKIE_STRING}",
        "-H", "user-agent: Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
        "-H", "sec-fetch-dest: document",
        "-H", "sec-fetch-mode: navigate",
        "-H", "sec-fetch-site: same-origin",
        full_url,
    ]

    for attempt in range(MAX_RETRIES):
        try:
            result = subprocess.run(
                curl_cmd, capture_output=True, text=True, timeout=45,
                encoding="utf-8", errors="replace"
            )
            html = result.stdout
            if not html or len(html) < 500:
                print(f"  ⚠️  第{attempt+1}次: 返回内容太短，重试中...")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2)
                continue
            # 检测 Cloudflare 错误页（525 SSL, 502, 503, 504等）
            if "cf-error-details" in html or "SSL handshake failed" in html or "cf-error-code" in html:
                print(f"  ⚠️  第{attempt+1}次: AO3服务器临时错误（Cloudflare 5xx），重试中...")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(3)
                continue
            if "429" in html[:200] or "Retry-After" in html[:500]:
                print(f"  ⏳ 被限流了，等待 60 秒...")
                time.sleep(60)
                continue
            return html
        except subprocess.TimeoutExpired:
            print(f"  ⚠️  第{attempt+1}次请求超时")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
        except Exception as e:
            print(f"  ⚠️  第{attempt+1}次请求失败: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(2)
    return None


def get_total_pages(html):
    """从第一页获取总页数"""
    soup = BeautifulSoup(html, "html.parser")
    pagination = soup.select("ol.pagination li")
    if not pagination:
        return 1
    # 找到最后一个数字页码
    max_page = 1
    for li in pagination:
        a = li.find("a")
        text = a.get_text(strip=True) if a else li.get_text(strip=True)
        if text.isdigit():
            max_page = max(max_page, int(text))
    return max_page


def parse_works(html):
    """解析单页中的所有作品"""
    soup = BeautifulSoup(html, "html.parser")
    works = []

    for item in soup.select("li.work.blurb"):
        try:
            work = {}

            # 提取 work ID（用于去重）
            li_id = item.get("id", "")  # e.g. "work_74451806"
            work_id = li_id.replace("work_", "") if li_id.startswith("work_") else ""
            work["work_id"] = work_id

            # 标题和链接
            title_tag = item.select_one("h4.heading a:first-child")
            if not title_tag:
                continue
            work["title"] = title_tag.get_text(strip=True)
            href = title_tag.get("href", "")
            work["url"] = "https://archiveofourown.org" + href

            # 如果从li没拿到id，从URL提取
            if not work_id:
                m = re.search(r'/works/(\d+)', href)
                if m:
                    work["work_id"] = m.group(1)

            # 作者
            author_tag = item.select_one('a[rel="author"]')
            if author_tag:
                work["author"] = author_tag.get_text(strip=True)
                work["author_url"] = "https://archiveofourown.org" + author_tag.get("href", "")
            else:
                work["author"] = "Anonymous"
                work["author_url"] = ""

            # Fandom
            fandom_tags = item.select("h5.fandoms a.tag")
            work["fandoms"] = [t.get_text(strip=True) for t in fandom_tags]

            # 日期
            date_tag = item.select_one("p.datetime")
            work["date"] = date_tag.get_text(strip=True) if date_tag else ""

            # Rating
            rating_span = item.select_one("span[class*='rating']")
            work["rating"] = rating_span.get("title", "") if rating_span else ""

            # Category
            cat_span = item.select_one("span[class*='category']")
            work["category"] = cat_span.get("title", "") if cat_span else ""

            # Completion
            wip_span = item.select_one("span[class*='iswip']")
            work["complete"] = wip_span.get("title", "") if wip_span else ""

            # Relationships
            rel_tags = item.select("li.relationships a.tag")
            work["relationships"] = [t.get_text(strip=True) for t in rel_tags]

            # Characters
            char_tags = item.select("li.characters a.tag")
            work["characters"] = [t.get_text(strip=True) for t in char_tags]

            # Freeform tags
            ff_tags = item.select("li.freeforms a.tag")
            work["freeforms"] = [t.get_text(strip=True) for t in ff_tags]

            # Summary
            summary_tag = item.select_one("blockquote.userstuff.summary")
            work["summary"] = summary_tag.get_text(strip=True) if summary_tag else ""

            # Stats
            words_tag = item.select_one("dd.words")
            work["words"] = int(words_tag.get_text(strip=True).replace(",", "")) if words_tag else 0

            chapters_tag = item.select_one("dd.chapters")
            work["chapters"] = chapters_tag.get_text(strip=True) if chapters_tag else ""

            kudos_tag = item.select_one("dd.kudos")
            if kudos_tag:
                kudos_text = kudos_tag.get_text(strip=True).replace(",", "")
                work["kudos"] = int(kudos_text) if kudos_text.isdigit() else 0
            else:
                work["kudos"] = 0

            hits_tag = item.select_one("dd.hits")
            if hits_tag:
                hits_text = hits_tag.get_text(strip=True).replace(",", "")
                work["hits"] = int(hits_text) if hits_text.isdigit() else 0
            else:
                work["hits"] = 0

            bookmarks_tag = item.select_one("dd.bookmarks")
            if bookmarks_tag:
                bm_text = bookmarks_tag.get_text(strip=True).replace(",", "")
                work["bookmarks"] = int(bm_text) if bm_text.isdigit() else 0
            else:
                work["bookmarks"] = 0

            comments_tag = item.select_one("dd.comments")
            if comments_tag:
                cm_text = comments_tag.get_text(strip=True).replace(",", "")
                work["comments"] = int(cm_text) if cm_text.isdigit() else 0
            else:
                work["comments"] = 0

            # 计算比率
            if work["hits"] > 0 and work["kudos"] > 0:
                work["ratio"] = round(work["kudos"] / work["hits"] * 100, 2)
            else:
                work["ratio"] = 0

            works.append(work)

        except Exception as e:
            print(f"  ⚠️  解析某篇作品时出错: {e}")
            continue

    return works


def generate_html(works, tag_name, output_path):
    """生成交互式HTML页面"""
    works_json = json.dumps(works, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AO3 Sorter · {tag_name}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --bg: #faf8f5;
    --bg-card: #ffffff;
    --text: #2c2c2c;
    --text-dim: #7a7672;
    --text-light: #a8a4a0;
    --accent: #c45d3e;
    --accent-soft: #e8a690;
    --accent-bg: #fdf0ec;
    --border: #e8e4df;
    --border-light: #f0ece8;
    --green: #4a8c6f;
    --green-bg: #edf5f0;
    --blue: #4a7a9b;
    --blue-bg: #edf3f7;
    --shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.03);
    --shadow-hover: 0 2px 8px rgba(0,0,0,0.06), 0 8px 24px rgba(0,0,0,0.05);
    --radius: 10px;
    --font-serif: 'Noto Serif SC', 'Songti SC', serif;
    --font-mono: 'JetBrains Mono', 'Menlo', monospace;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    font-family: var(--font-serif);
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    min-height: 100vh;
  }}

  .container {{
    max-width: 900px;
    margin: 0 auto;
    padding: 40px 24px 80px;
  }}

  /* Header */
  .page-header {{
    text-align: center;
    margin-bottom: 48px;
    padding-bottom: 32px;
    border-bottom: 1px solid var(--border);
  }}

  .page-header h1 {{
    font-size: 28px;
    font-weight: 700;
    letter-spacing: 0.02em;
    margin-bottom: 8px;
  }}

  .page-header h1 span {{
    color: var(--accent);
  }}

  .page-header .subtitle {{
    color: var(--text-dim);
    font-size: 15px;
  }}

  .page-header .stats-bar {{
    display: flex;
    justify-content: center;
    gap: 32px;
    margin-top: 20px;
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--text-dim);
  }}

  .page-header .stats-bar strong {{
    color: var(--text);
    font-weight: 500;
  }}

  /* Controls */
  .controls {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 32px;
    align-items: center;
  }}

  .search-box {{
    flex: 1;
    min-width: 200px;
    padding: 10px 16px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    font-family: var(--font-serif);
    font-size: 14px;
    background: var(--bg-card);
    outline: none;
    transition: border-color 0.2s;
  }}

  .search-box:focus {{
    border-color: var(--accent-soft);
  }}

  .sort-btns {{
    display: flex;
    gap: 4px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 3px;
  }}

  .sort-btn {{
    padding: 7px 14px;
    border: none;
    background: transparent;
    border-radius: 7px;
    font-family: var(--font-serif);
    font-size: 13px;
    color: var(--text-dim);
    cursor: pointer;
    transition: all 0.2s;
    white-space: nowrap;
  }}

  .sort-btn:hover {{
    color: var(--text);
  }}

  .sort-btn.active {{
    background: var(--accent);
    color: white;
  }}

  .filter-row {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    width: 100%;
  }}

  .filter-chip {{
    padding: 5px 12px;
    border: 1px solid var(--border);
    border-radius: 20px;
    font-family: var(--font-serif);
    font-size: 12px;
    color: var(--text-dim);
    cursor: pointer;
    background: var(--bg-card);
    transition: all 0.2s;
  }}

  .filter-chip:hover {{
    border-color: var(--accent-soft);
    color: var(--accent);
  }}

  .filter-chip.active {{
    background: var(--accent-bg);
    border-color: var(--accent-soft);
    color: var(--accent);
  }}

  /* Work cards */
  .work-list {{
    display: flex;
    flex-direction: column;
    gap: 16px;
  }}

  .work-card {{
    background: var(--bg-card);
    border: 1px solid var(--border-light);
    border-radius: var(--radius);
    padding: 24px;
    box-shadow: var(--shadow);
    transition: box-shadow 0.25s, transform 0.25s;
    position: relative;
  }}

  .work-card:hover {{
    box-shadow: var(--shadow-hover);
    transform: translateY(-1px);
  }}

  .work-card .rank {{
    position: absolute;
    top: -10px;
    left: 20px;
    background: var(--accent);
    color: white;
    font-family: var(--font-mono);
    font-size: 12px;
    font-weight: 500;
    padding: 2px 10px;
    border-radius: 12px;
  }}

  .work-card .rank.top3 {{
    background: linear-gradient(135deg, #c45d3e, #d4845a);
    font-size: 13px;
    padding: 3px 12px;
  }}

  .work-title {{
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 4px;
  }}

  .work-title a {{
    color: var(--text);
    text-decoration: none;
    transition: color 0.2s;
  }}

  .work-title a:hover {{
    color: var(--accent);
  }}

  .work-author {{
    font-size: 13px;
    color: var(--text-dim);
    margin-bottom: 12px;
  }}

  .work-author a {{
    color: var(--text-dim);
    text-decoration: none;
  }}

  .work-author a:hover {{
    color: var(--accent);
  }}

  .work-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 12px;
  }}

  .work-tags .tag {{
    font-size: 11px;
    padding: 2px 8px;
    border-radius: 4px;
    background: var(--border-light);
    color: var(--text-dim);
  }}

  .work-tags .tag.rel {{
    background: var(--accent-bg);
    color: var(--accent);
  }}

  .work-summary {{
    font-size: 13px;
    color: var(--text-dim);
    line-height: 1.8;
    margin-bottom: 14px;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }}

  .work-meta {{
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--text-light);
    align-items: center;
  }}

  .work-meta .ratio-badge {{
    background: var(--green-bg);
    color: var(--green);
    padding: 3px 10px;
    border-radius: 6px;
    font-weight: 500;
    font-size: 13px;
  }}

  .work-meta .ratio-badge.high {{
    background: var(--accent-bg);
    color: var(--accent);
  }}

  .work-meta .meta-item {{
    display: flex;
    align-items: center;
    gap: 4px;
  }}

  .work-meta .meta-item .label {{
    color: var(--text-light);
  }}

  .work-meta .meta-item .value {{
    color: var(--text-dim);
    font-weight: 500;
  }}

  .work-date {{
    font-size: 12px;
    color: var(--text-light);
    margin-top: 10px;
  }}

  /* No results */
  .no-results {{
    text-align: center;
    padding: 60px 20px;
    color: var(--text-dim);
    font-size: 15px;
  }}

  .count-display {{
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--text-light);
    margin-bottom: 16px;
  }}

  /* Responsive */
  @media (max-width: 600px) {{
    .container {{ padding: 24px 16px 60px; }}
    .page-header h1 {{ font-size: 22px; }}
    .work-card {{ padding: 18px; }}
    .work-title {{ font-size: 16px; }}
    .controls {{ flex-direction: column; }}
    .page-header .stats-bar {{ flex-wrap: wrap; gap: 16px; }}
  }}
</style>
</head>
<body>

<div class="container">
  <div class="page-header">
    <h1>📖 <span>{tag_name}</span></h1>
    <div class="subtitle">按 Kudos/Hits 比排序 · 数据来自 AO3</div>
    <div class="stats-bar" id="statsBar"></div>
  </div>

  <div class="controls">
    <input type="text" class="search-box" id="searchBox"
           placeholder="搜索标题、作者、标签、简介…">
    <div class="sort-btns" id="sortBtns">
      <button class="sort-btn active" data-sort="ratio">比率 ↓</button>
      <button class="sort-btn" data-sort="kudos">Kudos ↓</button>
      <button class="sort-btn" data-sort="hits">Hits ↓</button>
      <button class="sort-btn" data-sort="words">字数 ↓</button>
      <button class="sort-btn" data-sort="date">最新</button>
    </div>
    <div class="filter-row" id="filterRow">
      <button class="filter-chip" data-filter="complete">仅完结</button>
      <button class="filter-chip" data-filter="long">长篇(>10k)</button>
      <button class="filter-chip" data-filter="short">短篇(<5k)</button>
    </div>
  </div>

  <div class="count-display" id="countDisplay"></div>
  <div class="work-list" id="workList"></div>
</div>

<script>
const ALL_WORKS = {works_json};

let currentSort = "ratio";
let currentSearch = "";
let activeFilters = new Set();

function formatNumber(n) {{
  return n.toLocaleString();
}}

function getSearchText(w) {{
  return [
    w.title, w.author, w.summary,
    ...w.fandoms, ...w.relationships,
    ...w.characters, ...w.freeforms
  ].join(" ").toLowerCase();
}}

// Parse date for sorting
function parseDate(dateStr) {{
  const months = {{
    'Jan':0,'Feb':1,'Mar':2,'Apr':3,'May':4,'Jun':5,
    'Jul':6,'Aug':7,'Sep':8,'Oct':9,'Nov':10,'Dec':11
  }};
  const parts = dateStr.split(" ");
  if (parts.length === 3) {{
    return new Date(parseInt(parts[2]), months[parts[1]] || 0, parseInt(parts[0]));
  }}
  return new Date(dateStr);
}}

function filterAndSort() {{
  let works = ALL_WORKS.filter(w => w.kudos > 0);

  // Search
  if (currentSearch) {{
    const q = currentSearch.toLowerCase();
    works = works.filter(w => getSearchText(w).includes(q));
  }}

  // Filters
  if (activeFilters.has("complete")) {{
    works = works.filter(w => w.complete === "Complete Work");
  }}
  if (activeFilters.has("long")) {{
    works = works.filter(w => w.words >= 10000);
  }}
  if (activeFilters.has("short")) {{
    works = works.filter(w => w.words < 5000);
  }}

  // Sort
  works.sort((a, b) => {{
    switch (currentSort) {{
      case "ratio": return b.ratio - a.ratio;
      case "kudos": return b.kudos - a.kudos;
      case "hits": return b.hits - a.hits;
      case "words": return b.words - a.words;
      case "date": return parseDate(b.date) - parseDate(a.date);
      default: return 0;
    }}
  }});

  return works;
}}

function renderWorks() {{
  const works = filterAndSort();
  const list = document.getElementById("workList");
  const countEl = document.getElementById("countDisplay");

  countEl.textContent = `显示 ${{works.length}} 篇作品（共 ${{ALL_WORKS.length}} 篇，过滤掉 ${{ALL_WORKS.length - works.length}} 篇无kudos/不符合条件的作品）`;

  if (works.length === 0) {{
    list.innerHTML = '<div class="no-results">没有找到符合条件的作品</div>';
    return;
  }}

  list.innerHTML = works.map((w, i) => {{
    const rank = i + 1;
    const rankClass = rank <= 3 ? "top3" : "";
    const ratioClass = w.ratio >= 5 ? "high" : "";

    const relTags = w.relationships.map(t =>
      `<span class="tag rel">${{escapeHtml(t)}}</span>`
    ).join("");
    const ffTags = w.freeforms.slice(0, 5).map(t =>
      `<span class="tag">${{escapeHtml(t)}}</span>`
    ).join("");

    return `
      <div class="work-card">
        <div class="rank ${{rankClass}}">#${{rank}}</div>
        <div class="work-title">
          <a href="${{w.url}}" target="_blank" rel="noopener">${{escapeHtml(w.title)}}</a>
        </div>
        <div class="work-author">
          by <a href="${{w.author_url}}" target="_blank" rel="noopener">${{escapeHtml(w.author)}}</a>
        </div>
        ${{(relTags || ffTags) ? `<div class="work-tags">${{relTags}}${{ffTags}}</div>` : ""}}
        ${{w.summary ? `<div class="work-summary">${{escapeHtml(w.summary)}}</div>` : ""}}
        <div class="work-meta">
          <span class="ratio-badge ${{ratioClass}}">${{w.ratio}}%</span>
          <span class="meta-item"><span class="label">❤️</span><span class="value">${{formatNumber(w.kudos)}}</span></span>
          <span class="meta-item"><span class="label">👁</span><span class="value">${{formatNumber(w.hits)}}</span></span>
          <span class="meta-item"><span class="label">字</span><span class="value">${{formatNumber(w.words)}}</span></span>
          <span class="meta-item"><span class="label">章</span><span class="value">${{w.chapters}}</span></span>
          ${{w.bookmarks ? `<span class="meta-item"><span class="label">🔖</span><span class="value">${{formatNumber(w.bookmarks)}}</span></span>` : ""}}
          ${{w.complete === "Complete Work" ? '<span class="meta-item" style="color:var(--green)">✓ 完结</span>' : '<span class="meta-item" style="color:var(--accent)">◌ 连载中</span>'}}
        </div>
        <div class="work-date">${{w.date}}</div>
      </div>
    `;
  }}).join("");
}}

function escapeHtml(str) {{
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}}

function updateStats() {{
  const valid = ALL_WORKS.filter(w => w.kudos > 0);
  const avgRatio = valid.length > 0
    ? (valid.reduce((s, w) => s + w.ratio, 0) / valid.length).toFixed(2)
    : 0;
  const totalKudos = ALL_WORKS.reduce((s, w) => s + w.kudos, 0);
  const totalWords = ALL_WORKS.reduce((s, w) => s + w.words, 0);

  document.getElementById("statsBar").innerHTML = `
    <span>总计 <strong>${{ALL_WORKS.length}}</strong> 篇</span>
    <span>平均比率 <strong>${{avgRatio}}%</strong></span>
    <span>总Kudos <strong>${{formatNumber(totalKudos)}}</strong></span>
    <span>总字数 <strong>${{formatNumber(totalWords)}}</strong></span>
  `;
}}

// Events
document.getElementById("searchBox").addEventListener("input", (e) => {{
  currentSearch = e.target.value;
  renderWorks();
}});

document.getElementById("sortBtns").addEventListener("click", (e) => {{
  const btn = e.target.closest(".sort-btn");
  if (!btn) return;
  document.querySelectorAll(".sort-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  currentSort = btn.dataset.sort;
  renderWorks();
}});

document.getElementById("filterRow").addEventListener("click", (e) => {{
  const chip = e.target.closest(".filter-chip");
  if (!chip) return;
  const f = chip.dataset.filter;
  if (activeFilters.has(f)) {{
    activeFilters.delete(f);
    chip.classList.remove("active");
  }} else {{
    // "long" and "short" are mutually exclusive
    if (f === "long" && activeFilters.has("short")) {{
      activeFilters.delete("short");
      document.querySelector('[data-filter="short"]').classList.remove("active");
    }}
    if (f === "short" && activeFilters.has("long")) {{
      activeFilters.delete("long");
      document.querySelector('[data-filter="long"]').classList.remove("active");
    }}
    activeFilters.add(f);
    chip.classList.add("active");
  }}
  renderWorks();
}});

// Init
updateStats();
renderWorks();
</script>
</body>
</html>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    print("=" * 52)
    print("  AO3 Kudos/Hits Ratio Sorter")
    print("=" * 52)
    print()

    # 检查 cookie 是否配置
    if COOKIE_STRING == "view_adult=true":
        print("⚠️  建议在脚本顶部 COOKIE_STRING 中填入你的完整AO3 cookie")
        print("   包括 cf_clearance 等 Cloudflare cookie 才能正常访问")
        print("   获取方法：浏览器F12 → Network → 复制请求的Cookie头")
        print()

    # 获取 tag
    tag_input = input("请输入 AO3 tag名称或完整URL: ").strip()
    if not tag_input:
        print("❌ 未输入任何内容")
        return

    tag_url = build_tag_url(tag_input)

    # 清理tag名用于显示
    tag_name = tag_input
    if tag_input.startswith("http"):
        # 从URL提取tag名
        path = urlparse(tag_input).path
        parts = path.split("/tags/")
        if len(parts) > 1:
            tag_name = parts[1].split("/")[0]
            from urllib.parse import unquote
            tag_name = unquote(tag_name)

    print(f"\n📍 Tag: {tag_name}")
    print(f"🔗 URL: {tag_url}")
    print()

    # 第一页
    print("📥 正在抓取第1页...")
    html = fetch_page(tag_url, page=1)
    if not html:
        print("❌ 无法访问AO3，请检查网络和cookie设置")
        return

    total_pages = get_total_pages(html)
    print(f"📄 共 {total_pages} 页\n")

    all_works = parse_works(html)
    print(f"  ✅ 第1页: 解析到 {len(all_works)} 篇作品")

    failed_pages = []

    # 其余页
    for page in range(2, total_pages + 1):
        time.sleep(REQUEST_DELAY)
        print(f"📥 正在抓取第{page}/{total_pages}页...")
        html = fetch_page(tag_url, page=page)
        if html:
            works = parse_works(html)
            if len(works) == 0 and len(html) > 500:
                # 保存调试文件
                debug_file = f"debug_page_{page}.html"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(html)
                print(f"  ⚠️  第{page}页: 有内容但解析到0篇，已保存 {debug_file}")
                failed_pages.append(page)
            else:
                all_works.extend(works)
                print(f"  ✅ 第{page}页: 解析到 {len(works)} 篇作品")
        else:
            print(f"  ❌ 第{page}页抓取失败，跳过")
            failed_pages.append(page)

    # 重试失败的页
    if failed_pages:
        print(f"\n🔄 重试 {len(failed_pages)} 个失败页...")
        for page in failed_pages:
            time.sleep(REQUEST_DELAY + 1)
            print(f"📥 重试第{page}页...")
            html = fetch_page(tag_url, page=page)
            if html:
                works = parse_works(html)
                if len(works) > 0:
                    all_works.extend(works)
                    print(f"  ✅ 重试成功: 第{page}页解析到 {len(works)} 篇")
                else:
                    debug_file = f"debug_page_{page}.html"
                    with open(debug_file, "w", encoding="utf-8") as f:
                        f.write(html)
                    print(f"  ❌ 重试仍然0篇，已保存 {debug_file}，请发给我看看")
            else:
                print(f"  ❌ 重试仍然失败")

    print(f"\n📊 抓取总计: {len(all_works)} 条记录")

    # 去重（按 work_id）
    seen_ids = set()
    unique_works = []
    for w in all_works:
        wid = w.get("work_id", "")
        if wid and wid in seen_ids:
            continue
        if wid:
            seen_ids.add(wid)
        unique_works.append(w)

    dupes = len(all_works) - len(unique_works)
    if dupes > 0:
        print(f"   🔄 去重移除: {dupes} 篇重复")
    all_works = unique_works

    print(f"   📖 去重后: {len(all_works)} 篇作品")
    with_kudos = len([w for w in all_works if w["kudos"] > 0])
    print(f"   ❤️  有kudos的: {with_kudos} 篇")

    # 生成 HTML
    safe_name = re.sub(r'[^\w\-]', '_', tag_name)
    output_file = f"ao3_sorted_{safe_name}.html"
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_file)

    generate_html(all_works, tag_name, output_path)
    print(f"\n✨ 已生成: {output_path}")

    # 尝试自动打开浏览器
    try:
        webbrowser.open(f"file://{output_path}")
        print("🌐 已在浏览器中打开")
    except:
        print("🌐 请手动在浏览器中打开上述文件")


if __name__ == "__main__":
    main()