# -*- coding: utf-8 -*-
import os, json, re, requests
from typing import Dict, Any, List

# ========== 通用小工具 ==========

def _json_loose(s: str) -> Dict[str, Any]:
    """
    宽松 JSON 解析：尽力从文本中抽出首个 {...} 为 JSON。
    """
    m = re.search(r"\{[\s\S]*\}", s)
    if not m:
        return {}
    raw = m.group(0)
    try:
        return json.loads(raw)
    except Exception:
        # 去掉尾随逗号等常见小问题再试一次
        t = re.sub(r",\s*([}\]])", r"\1", raw)
        try:
            return json.loads(t)
        except Exception:
            return {}

def _loose_json_load(s: str) -> Dict[str, Any]:
    """兼容旧名，等价 _json_loose。"""
    return _json_loose(s)

def _normalize_chat_endpoint(base_url: str) -> str:
    """
    允许三种写法：
      1) https://api.xxx.com
      2) https://api.xxx.com/v1
      3) https://api.xxx.com/v1/chat/completions
    统一规范到完整终点：.../v1/chat/completions
    """
    if not base_url:
        raise ValueError("llm.base_url is empty")
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if base.endswith("/v1"):
        return base + "/chat/completions"
    return base + "/v1/chat/completions"

def _chat_completions_request(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 1024,
    timeout: int = 30,
) -> str:
    """
    统一的 OpenAI 兼容 Chat Completions 请求（requests 直连）。
    适配 DeepSeek / SiliconFlow / 其他 OAI 兼容服务。
    """
    url = _normalize_chat_endpoint(base_url)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    # 标准 OAI 兼容返回
    try:
        return data["choices"][0]["message"]["content"]
    except Exception:
        # 兜底：部分实现把文本放在 text
        return data.get("choices", [{}])[0].get("text", "")

# ========== 双语“一段话总结” ==========

def call_llm_bilingual_summary(
    item: Dict[str, Any],
    *,
    base_url: str,
    model: str,
    api_key: str,
    system_prompt_zh: str = "",
    system_prompt_en: str = ""
) -> Dict[str, str]:
    """
    让 LLM 直接输出两段“总结”：digest_en / digest_zh
    内容要求：动机、方法、实验结果（各 1-2 句，合成两段：英文一段 + 中文一段）
    —— 统一 OpenAI 兼容通道，无需区分供应商。
    """
    title   = item.get("title") or ""
    summary = item.get("summary") or ""
    comments= item.get("comments") or ""
    venue   = item.get("venue_inferred") or (item.get("journal_ref") or "")

    sys_prompt = system_prompt_en or "You are a precise academic assistant. Summarize papers concisely."

    user_payload = {
        "title": title,
        "abstract": summary,
        "venue_or_comments": (venue or comments or "")
    }

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content":
            "Given the paper metadata below, write TWO concise one-paragraph digests:\n"
            "1) English paragraph first.\n"
            "2) Then a Simplified Chinese paragraph.\n"
            "- Each paragraph must briefly cover: motivation, method, and main experimental results.\n"
            "- Do not include links, bullet lists, markdown, or headings. Plain sentences only.\n"
            '- Return STRICT JSON: {\"digest_en\": \"...\", \"digest_zh\": \"...\"}\n\n'
            f"DATA:\n{json.dumps(user_payload, ensure_ascii=False)}"
        }
    ]

    text = _chat_completions_request(
        base_url=base_url, api_key=api_key, model=model, messages=messages,
        temperature=0.2, max_tokens=600
    )
    data = _json_loose(text)
    return {
        "digest_en": (data.get("digest_en") or "").strip(),
        "digest_zh": (data.get("digest_zh") or "").strip(),
    }


def call_llm_keyword_summary(
    *,
    keyword: str,
    papers: List[Dict[str, Any]],
    base_url: str,
    model: str,
    api_key: str,
    system_prompt_zh: str = "",
) -> str:
    """对某个关键词下的论文做聚合总结（中文）。"""
    sys_prompt = system_prompt_zh or "你是资深论文分析助手，请对同一主题论文做聚合总结。"
    payload = []
    max_papers = 12
    max_abs_chars = 700
    max_title_chars = 220
    for p in papers[:max_papers]:
        absu = (p.get("summary") or "").strip()
        if len(absu) > max_abs_chars:
            absu = absu[:max_abs_chars] + " ..."
        title = (p.get("title") or "").strip()
        if len(title) > max_title_chars:
            title = title[:max_title_chars] + " ..."
        payload.append({
            "title": title,
            "summary": absu,
            "authors": p.get("authors") or [],
            "published": p.get("published") or "",
            "updated": p.get("updated") or "",
        })

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content":
            "请基于以下同一关键词下的论文列表，输出中文总结，包含：\n"
            "1) 该关键词下研究主线与热点；\n"
            "2) 代表性方法范式；\n"
            "3) 常见评测方式/结论趋势；\n"
            "4) 潜在空白与后续研究方向。\n"
            "要求：客观简洁，控制在 180-260 字，返回纯文本，不要 Markdown 标题或列表。\n\n"
            f"关键词: {keyword}\n"
            f"输入论文数: {len(papers)}，已抽样: {len(payload)}\n"
            f"论文数据(JSON): {json.dumps(payload, ensure_ascii=False)}"
         }
    ]
    text = _chat_completions_request(
        base_url=base_url,
        api_key=api_key,
        model=model,
        messages=messages,
        temperature=0.2,
        max_tokens=520,
    )
    return (text or "").strip()

# ========== 两阶段摘要（保留你原有接口与行为） ==========

def build_llm_prompt(item: Dict[str, Any], lang: str = "zh", scope: str = "both"):
    title   = item.get("title") or ""
    authors = ", ".join(item.get("authors") or [])
    venue   = item.get("venue_inferred") or (item.get("journal_ref") or "")
    comments = item.get("comments") or ""
    summary  = item.get("summary") or ""
    links = {
        "html": item.get("html_url"),
        "pdf": item.get("pdf_url"),
        "code": item.get("code_urls") or [],
        "project": item.get("project_urls") or [],
        "other": item.get("other_urls") or [],
    }
    meta = {
        "title": title, "authors": authors, "venue": venue,
        "comments": comments, "summary": summary, "links": links
    }
    ask_lang = "中文" if lang == "zh" else "English"
    user_prompt = f"""
请阅读以下论文元信息(JSON)，用{ask_lang}输出“两阶段摘要”：
1) TL;DR（1~2 句，先总后分，避免口号）
2) **Method Card**：任务/动机、核心方法、关键设计、数据与指标、主要结果与结论、局限与未来工作、保留链接（PDF/代码/项目页）
3) **Discussion Questions**：3~5 个高质量问题（可用于组会讨论）
请保留所有给定链接，不要臆造。scope="{scope}" 表示输出范围（tldr/full/both）。

JSON:
{json.dumps(meta, ensure_ascii=False, indent=2)}
""".strip()
    return user_prompt

def call_llm_two_stage(item: Dict[str, Any], lang: str, scope: str,
                       base_url: str, model: str, api_key: str,
                       system_prompt: str = "") -> Dict[str, str]:
    """
    兼容你原先的“两阶段摘要”接口，内部改为统一 OpenAI 兼容通道。
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": build_llm_prompt(item, lang=lang, scope=scope)})

    text = _chat_completions_request(
        base_url=base_url, api_key=api_key, model=model, messages=messages,
        temperature=0.2, max_tokens=900
    ).strip()

    tldr, full_md = "", ""
    if "TL;DR" in text or "TLDR" in text or "Tl;dr" in text:
        parts = text.splitlines()
        tldr_lines, rest_lines, in_tldr = [], [], False
        for ln in parts:
            if "TL;DR" in ln or "TLDR" in ln or "Tl;dr" in ln:
                in_tldr = True
                t = ln.replace("TL;DR","").replace("TLDR","").replace("Tl;dr","")
                tldr_lines.append(t.strip(" :："))
            elif in_tldr and (ln.strip().startswith("**Method") or ln.strip().lower().startswith("**discussion")):
                in_tldr = False
                rest_lines.append(ln)
            elif in_tldr:
                tldr_lines.append(ln)
            else:
                rest_lines.append(ln)
        tldr = " ".join([s.strip() for s in tldr_lines if s.strip()])
        full_md = "\n".join(rest_lines).strip()
    else:
        full_md = text
    return {"tldr": tldr, "full_md": full_md}

# ========== 标题/摘要中文翻译 ==========

def call_llm_translate(item: Dict[str, Any], target_lang: str,
                       base_url: str, model: str, api_key: str,
                       system_prompt: str = "") -> Dict[str, str]:
    """
    返回：{ title_zh?, summary_zh?, comments_zh? }
    —— 同一 OpenAI 兼容通道，按任意 base_url + api_key 工作。
    """
    title   = item.get("title") or ""
    summary = item.get("summary") or ""
    comments= item.get("comments") or ""
    want_comments = bool(comments.strip())
    schema_keys = ["title_zh", "summary_zh"] + (["comments_zh"] if want_comments else [])

    sys_prompt = system_prompt or (
        "You are a precise academic translator. Translate to Simplified Chinese concisely and faithfully; keep technical terms."
    )
    inst = f"""
Translate the following fields into Simplified Chinese.
Return ONLY compact JSON with keys {schema_keys} (omit keys you can't translate).
Do not add commentary.

DATA:
{json.dumps({"title": title, "summary": summary, "comments": comments}, ensure_ascii=False, indent=2)}
""".strip()

    messages = [{"role":"system","content":sys_prompt},
                {"role":"user","content":inst}]
    text = _chat_completions_request(
        base_url=base_url, api_key=api_key, model=model, messages=messages,
        temperature=0.0, max_tokens=600
    ).strip()

    data = _loose_json_load(text)
    out: Dict[str, str] = {}
    if isinstance(data, dict):
        if "title_zh" in data and isinstance(data["title_zh"], str):
            out["title_zh"] = data["title_zh"].strip()
        if "summary_zh" in data and isinstance(data["summary_zh"], str):
            out["summary_zh"] = data["summary_zh"].strip()
        if "comments_zh" in data and isinstance(data["comments_zh"], str):
            out["comments_zh"] = data["comments_zh"].strip()
    return out


def call_llm_categorize(
    items: List[Dict[str, Any]],
    *,
    base_url: str,
    model: str,
    api_key: str,
    system_prompt: str = "",
) -> Dict[str, Any]:
    """
    对论文做固定类别分类，并输出总览与逐篇归类结果。
    返回：
    {
      "overview_zh": "...",
      "assignments": [
        {"idx": 1, "category": "..."},
      ]
    }
    """
    compact = []
    for idx, it in enumerate(items, 1):
        compact.append({
            "idx": idx,
            "id": it.get("id"),
            "title": it.get("title", ""),
        })

    sys_prompt = system_prompt or (
        "你是论文安全方向分析助手。你的任务是根据论文标题与摘要做严格分类。"
    )
    fixed_categories = [
        "传统网络安全（密码、系统）",
        "传统人工智能安全（机器学习模型）",
        "大模型安全（LLM、VLM、MLLM、VLA等的安全）",
        "人工智能/大模型应用",
    ]

    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content":
            "请仅基于论文英文标题，把下面论文逐篇分类到指定类别。\n"
            "要求：\n"
            "1) 每篇论文只能归到一个类别。\n"
            "2) 不要遗漏论文，必须覆盖全部 idx。\n"
            "3) 仅使用以下类别（不能新造类别）：\n"
            f"{json.dumps(fixed_categories, ensure_ascii=False)}\n"
            "4) 只返回严格 JSON，格式：\n"
            '{"overview_zh":"...", "assignments":[{"idx":1,"category":"..."}]}\n\n'
            f"DATA:\n{json.dumps(compact, ensure_ascii=False)}"
        }
    ]
    text = _chat_completions_request(
        base_url=base_url, api_key=api_key, model=model, messages=messages,
        temperature=0.1, max_tokens=4000
    )
    data = _json_loose(text)
    out = {"overview_zh": "", "assignments": []}
    out["overview_zh"] = (data.get("overview_zh") or "").strip()
    assignments = data.get("assignments") or []
    if isinstance(assignments, list):
        clean = []
        for a in assignments:
            if not isinstance(a, dict):
                continue
            idx = a.get("idx")
            cat = (a.get("category") or "").strip()
            clean.append({
                "idx": int(idx) if isinstance(idx, (int, float, str)) and str(idx).isdigit() else -1,
                "category": cat,
            })
        out["assignments"] = clean
    return out


def call_llm_category_summary(
    category_name: str,
    items: List[Dict[str, Any]],
    *,
    base_url: str,
    model: str,
    api_key: str,
    system_prompt: str = "",
) -> str:
    """
    对某个类别下的论文做中文长总结。
    """
    compact = []
    for it in items:
        compact.append({
            "title": it.get("title", ""),
            "summary": (it.get("summary", "") or "")[:1200],
        })

    sys_prompt = system_prompt or "你是资深论文分析助手，擅长从多篇论文中提炼主题脉络与共性趋势。"
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content":
            f"请对类别“{category_name}”下的论文做一段较详细的中文总结。\n"
            "要求：\n"
            "1) 说明该类别的主要研究主题与问题。\n"
            "2) 概括常见方法路线与技术趋势。\n"
            "3) 总结代表性结果/应用方向与潜在局限。\n"
            "4) 直接输出纯文本，不要 JSON，不要 markdown 标题。\n\n"
            f"DATA:\n{json.dumps(compact, ensure_ascii=False)}"
        }
    ]
    text = _chat_completions_request(
        base_url=base_url, api_key=api_key, model=model, messages=messages,
        temperature=0.2, max_tokens=1200
    )
    return (text or "").strip()


def call_llm_classify_paper(
    item: Dict[str, Any],
    *,
    base_url: str,
    model: str,
    api_key: str,
    categories: List[str],
    system_prompt: str = "",
) -> str:
    """
    对单篇论文做固定类别判定，返回类别名。
    """
    payload = {
        "title": item.get("title", ""),
        "summary": (item.get("summary", "") or "")[:1800],
    }
    sys_prompt = system_prompt or "你是安全方向论文分类助手。"
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content":
            "请把下面这篇论文分类到给定类别中的一个。\n"
            "要求：\n"
            "1) 只能输出一个类别，必须从给定列表中选择；\n"
            "2) 无法判断时输出“其他”；\n"
            "3) 返回严格 JSON：{\"category\": \"...\"}\n\n"
            f"CATEGORIES: {json.dumps(categories, ensure_ascii=False)}\n"
            f"DATA: {json.dumps(payload, ensure_ascii=False)}"
        }
    ]
    text = _chat_completions_request(
        base_url=base_url, api_key=api_key, model=model, messages=messages,
        temperature=0.0, max_tokens=120
    )
    data = _json_loose(text)
    return (data.get("category") or "").strip()
