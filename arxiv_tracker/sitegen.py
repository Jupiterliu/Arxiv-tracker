# -*- coding: utf-8 -*-
import os
import re
import html
import datetime
from typing import Dict, List, Any, Optional

try:
    from markdown import markdown as _md
except Exception:
    _md = None


def _esc(x: Optional[str]) -> str:
    return html.escape(x or "", quote=True)


def _md2html(md: str) -> str:
    if not md:
        return ""
    if _md:
        return _md(md, extensions=["extra", "sane_lists", "tables"])
    return "<pre class='mono'>" + _esc(md) + "</pre>"


def _slug(s: str) -> str:
    t = re.sub(r"\s+", "-", (s or "").strip().lower())
    t = re.sub(r"[^a-z0-9\-\u4e00-\u9fff]", "", t)
    return t or "group"


def _css(accent: str = "#2563eb") -> str:
    return f"""
:root {{
  --bg:#f8fafc; --card:#ffffff; --text:#0f172a; --muted:#667085; --border:#e5e7eb; --acc:{accent};
}}
:root[data-theme="dark"] {{
  --bg:#0b0f17; --card:#111827; --text:#e5e7eb; --muted:#9ca3af; --border:#1f2937; --acc:{accent};
}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--text);
  font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;line-height:1.6;}}
.container{{max-width:1100px;margin:0 auto;padding:18px;}}
.header{{display:flex;gap:10px;justify-content:space-between;align-items:center;margin:8px 0 16px;flex-wrap:wrap}}
h1{{font-size:22px;margin:0}}
.badge{{font-size:12px;color:#111827;background:var(--acc);padding:2px 8px;border-radius:999px}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:16px 18px;margin:14px 0;box-shadow:0 1px 2px rgba(0,0,0,.04)}}
.title{{font-weight:700;margin:0 0 6px 0;font-size:18px}}
.meta-line{{color:var(--muted);font-size:13px;margin:2px 0}}
.links a{{color:var(--acc);text-decoration:none;margin-right:12px}}
.detail{{margin-top:10px;background:rgba(2,6,23,.03);border:1px solid var(--border);border-radius:10px;padding:8px 10px}}
summary{{cursor:pointer;color:var(--acc)}}
.mono{{white-space:pre-wrap;background:rgba(2,6,23,.03);border:1px solid var(--border);padding:10px;border-radius:10px}}
.row{{display:grid;grid-template-columns:1fr;gap:12px}}
.footer{{color:var(--muted);font-size:13px;margin:20px 0 10px}}
.hr{{height:1px;background:var(--border);margin:14px 0}}
.history-list a{{display:block;color:var(--acc);text-decoration:none;margin:4px 0}}
.controls{{display:flex;gap:8px;align-items:center}}
.btn{{border:1px solid var(--border);background:var(--card);padding:6px 10px;border-radius:10px;cursor:pointer;color:var(--text)}}
.btn:hover{{border-color:var(--acc)}}
.layout{{display:grid;grid-template-columns:1fr;gap:14px;margin-top:12px}}
.sidebar{{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px;align-self:start}}
.sidebar-title{{font-weight:700;margin:0 0 8px 0}}
.toc a{{display:block;color:var(--acc);text-decoration:none;padding:3px 0;font-size:14px}}
.maincol{{min-width:0}}
.chips{{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}}
.chip{{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;line-height:1.6;border:1px solid transparent}}
@media (min-width: 980px) {{
  .layout{{grid-template-columns:260px minmax(0,1fr)}}
  .sidebar{{position:sticky;top:12px;max-height:calc(100vh - 24px);overflow:auto}}
}}
"""


def _join_links(it: Dict[str, Any]) -> str:
    parts = []
    if it.get("html_url"):
        parts.append(f'<a href="{_esc(it["html_url"])}">Abs</a>')
    if it.get("pdf_url"):
        parts.append(f'<a href="{_esc(it["pdf_url"])}">PDF</a>')
    if it.get("code_urls"):
        for i, u in enumerate(it["code_urls"][:3]):
            parts.append(f'<a href="{_esc(u)}">Code{i+1}</a>')
    if it.get("project_urls"):
        for i, u in enumerate(it["project_urls"][:2]):
            parts.append(f'<a href="{_esc(u)}">Project{i+1}</a>')
    return " · ".join(parts)


def _chip_color(i: int) -> str:
    palette = [
        "#fee2e2", "#ffedd5", "#fef9c3", "#dcfce7", "#dbeafe",
        "#ede9fe", "#fce7f3", "#cffafe", "#e2e8f0", "#fae8ff",
    ]
    return palette[i % len(palette)]


def _render_chips(values: List[str], color_map: Dict[str, str]) -> str:
    if not values:
        return ""
    chips = []
    for v in values:
        bg = color_map.get(v, "#e2e8f0")
        chips.append(f'<span class="chip" style="background:{bg}">{_esc(v)}</span>')
    return '<div class="chips">' + "".join(chips) + "</div>"


def _card(
    it: Dict[str, Any],
    trans_zh: Optional[Dict[str, str]],
    sum_zh: Optional[Dict[str, str]],
    sum_en: Optional[Dict[str, str]],
) -> str:
    t = it.get("title") or ""
    au = ", ".join(it.get("authors") or [])
    venue = it.get("venue_inferred") or (it.get("journal_ref") or "")
    pub = it.get("published") or "—"
    upd = it.get("updated") or "—"
    comm = it.get("comments") or ""
    absu = it.get("summary") or ""

    zh_title = (trans_zh or {}).get("title_zh")
    zh_abs = (trans_zh or {}).get("summary_zh")

    parts = [f'<div class="card">', f'<div class="title">{_esc(t)}</div>']
    kw_tags = it.get("matched_keywords") or []
    if kw_tags:
        parts.append(_render_chips(kw_tags, it.get("_keyword_color_map") or {}))

    parts.append(f'<div class="meta-line">Authors: {_esc(au)}</div>')
    if venue:
        parts.append(f'<div class="meta-line">Venue: {_esc(venue)}</div>')
    parts.append(f'<div class="meta-line">First: {_esc(pub)} · Latest: {_esc(upd)}</div>')
    if comm:
        parts.append(f'<div class="meta-line">Comments: {_esc(comm)}</div>')

    links = _join_links(it)
    if links:
        parts.append(f'<div class="links" style="margin-top:8px">{links}</div>')

    if absu:
        parts.append('<details class="detail"><summary>Abstract</summary>')
        parts.append(f'<div class="mono">{_esc(absu)}</div></details>')

    if zh_abs or zh_title:
        parts.append('<details class="detail"><summary>中文标题/摘要</summary>')
        if zh_title:
            parts.append(f'<div class="mono"><b>标题：</b>{_esc(zh_title)}</div>')
        if zh_abs:
            parts.append(f'<div class="mono" style="margin-top:8px">{_esc(zh_abs)}</div>')
        parts.append('</details>')

    parts.append('</div>')
    return "\n".join(parts)


def _write(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _build_page(title: str, sub: str, toc_html: str, cards_html: str, history_html: str,
                theme_mode: str, accent: str) -> str:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    js = f"""
<script>
(function() {{
  const root = document.documentElement;
  function apply(t) {{
    if (t==='dark') root.setAttribute('data-theme','dark');
    else if (t==='light') root.removeAttribute('data-theme');
    else {{
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)
        root.setAttribute('data-theme','dark');
      else root.removeAttribute('data-theme');
    }}
  }}
  let t = localStorage.getItem('theme') || '{theme_mode}';
  if (!['light','dark','auto'].includes(t)) t='light';
  apply(t);
  window.__toggleTheme = function() {{
    let cur = localStorage.getItem('theme') || '{theme_mode}';
    if (cur==='light') cur='dark';
    else if (cur==='dark') cur='auto';
    else cur='light';
    localStorage.setItem('theme', cur);
    apply(cur);
    const el=document.getElementById('theme-label');
    if(el) el.textContent = cur.toUpperCase();
  }}
  window.__expandAll = function(open) {{
    document.querySelectorAll('details').forEach(d => d.open = !!open);
  }}
  window.__filterByKeyword = function(keyword) {{
    const cards = document.querySelectorAll('.paper-card');
    const summaryCards = document.querySelectorAll('.kw-summary-card');
    const all = keyword === 'ALL';
    cards.forEach(card => {{
      const kws = (card.getAttribute('data-keywords') || '').split('|').filter(Boolean);
      card.style.display = (all || kws.includes(keyword)) ? '' : 'none';
    }});
    summaryCards.forEach(card => {{
      const k = card.getAttribute('data-keyword') || '';
      card.style.display = (!all && k === keyword) ? '' : 'none';
    }});
    document.getElementById('kw-current').textContent = keyword;
  }}
}})();
</script>
"""
    controls = """
<div class="controls">
  <button class="btn" onclick="__toggleTheme()">Theme: <span id="theme-label" style="margin-left:6px">AUTO</span></button>
  <button class="btn" onclick="__expandAll(true)">Expand All</button>
  <button class="btn" onclick="__expandAll(false)">Collapse All</button>
</div>
"""
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)}</title><style>{_css(accent)}</style>{js}</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{_esc(title)}</h1>
      <div style="display:flex;gap:10px;align-items:center">
        {controls}
        <span class="badge">{_esc(now)}</span>
      </div>
    </div>
    <div class="hr"></div>
    <div>{_esc(sub)} · 当前关键词：<b id="kw-current">ALL</b></div>
    <div class="layout">
      <aside class="sidebar">
        <div class="sidebar-title">分类目录</div>
        <div class="toc">{toc_html}</div>
      </aside>
      <div class="maincol row">{cards_html}</div>
    </div>
    <details style="margin-top:16px" class="detail"><summary>History</summary>
      <div class="history-list">{history_html}</div>
    </details>
    <div class="footer">Generated by arxiv-tracker</div>
  </div>
</body></html>
"""


def _history_list(archive_dir: str, keep: int) -> List[str]:
    if not os.path.isdir(archive_dir):
        return []
    files = [f for f in os.listdir(archive_dir) if f.endswith(".html")]
    files.sort(reverse=True)
    files = files[:keep]
    links = []
    for f in files:
        date = f.replace(".html", "")
        links.append(f'<a href="archive/{_esc(f)}">{_esc(date)}</a>')
    return links


def generate_site(items: List[Dict[str, Any]],
                  summaries_zh: Dict[str, Dict[str, str]],
                  summaries_en: Dict[str, Dict[str, str]],
                  translations: Dict[str, Dict[str, str]],
                  categorization: Dict[str, Any],
                  configured_keywords: Optional[List[str]],
                  keyword_summaries: Optional[Dict[str, str]],
                  site_dir: str, site_title: str = "arXiv Results",
                  keep_runs: int = 60,
                  theme: str = "light",
                  accent: Optional[str] = None) -> Dict[str, str]:
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    archive_dir = os.path.join(site_dir, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    open(os.path.join(site_dir, ".nojekyll"), "w").close()

    by_id = {it.get("id"): it for it in items if it.get("id")}
    groups = (categorization or {}).get("groups") or []
    overview = (categorization or {}).get("overview_zh") or ""
    all_keywords = list(configured_keywords or [])
    kw_color_map = {kw: _chip_color(i) for i, kw in enumerate(all_keywords)}
    for it in items:
        it["_keyword_color_map"] = kw_color_map

    cards = []
    toc_links = []
    if overview:
        cards.append(f'<div class="card"><div class="title">分类概览</div><div class="mono">{_esc(overview)}</div></div>')

    if groups:
        for i, g in enumerate(groups, 1):
            gname = g.get("name_zh") or "未命名类别"
            gsum = g.get("summary_zh") or ""
            paper_ids = g.get("paper_ids", []) or []
            anchor = f"group-{i}-{_slug(gname)}"
            toc_links.append(f'<a href="#{_esc(anchor)}">{i}. {_esc(gname)} ({len(paper_ids)})</a>')
            cards.append(f'<div id="{_esc(anchor)}" class="card"><div class="title">类别：{_esc(gname)}</div>'
                         + (f'<div class="mono">{_esc(gsum)}</div>' if gsum else '')
                         + '</div>')
            for pid in paper_ids:
                it = by_id.get(pid)
                if not it:
                    continue
                sid = it.get("id") or ""
                cards.append(_card(it, translations.get(sid), summaries_zh.get(sid), summaries_en.get(sid)).replace(
                    '<div class="card">', f'<div class="card paper-card" data-keywords="{_esc("|".join(it.get("matched_keywords") or []))}">', 1))
    else:
        for it in items:
            sid = it.get("id") or ""
            cards.append(_card(it, translations.get(sid), summaries_zh.get(sid), summaries_en.get(sid)).replace(
                '<div class="card">', f'<div class="card paper-card" data-keywords="{_esc("|".join(it.get("matched_keywords") or []))}">', 1))

    for kw, summary in (keyword_summaries or {}).items():
        cards.insert(0, f'<div class="card kw-summary-card" data-keyword="{_esc(kw)}" style="display:none">'
                        f'<div class="title">关键词总结：{_esc(kw)}</div><div class="mono">{_esc(summary)}</div></div>')

    cards_html = "\n".join(cards)
    if toc_links:
        group_toc = "\n".join(toc_links)
    else:
        group_toc = '<span class="meta-line">暂无分类目录</span>'

    keyword_box = ""
    if all_keywords:
        links = ['<a href="javascript:void(0)" onclick="__filterByKeyword(\'ALL\')">ALL</a>']
        for kw in all_keywords:
            links.append(f'<a href="javascript:void(0)" onclick="__filterByKeyword(\'{_esc(kw)}\')">{_esc(kw)}</a>')
        keyword_box = '<div class="detail" style="margin-top:12px"><div class="sidebar-title">关键词筛选</div><div class="toc">' + "".join(links) + '</div></div>'
    toc_html = group_toc + keyword_box
    hist_html = "\n".join(_history_list(archive_dir, keep_runs))

    acc = (accent or "#2563eb").strip()

    arch_html = _build_page(site_title, f"Snapshot: {stamp}", toc_html, cards_html, history_html=hist_html,
                            theme_mode=theme, accent=acc)
    arch_path = os.path.join(archive_dir, f"{stamp}.html")
    _write(arch_path, arch_html)

    index_html = _build_page(site_title, "Latest digest", toc_html, cards_html, history_html=hist_html,
                             theme_mode=theme, accent=acc)
    index_path = os.path.join(site_dir, "index.html")
    _write(index_path, index_html)

    return {"index_path": index_path, "archive_path": arch_path, "stamp": stamp}
