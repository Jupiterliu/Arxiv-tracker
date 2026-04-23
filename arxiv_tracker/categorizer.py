# -*- coding: utf-8 -*-
from typing import Dict, Any, List
import os

from .llm import call_llm_categorize

FIXED_CATEGORIES = [
    "传统网络安全（密码、系统）",
    "传统人工智能安全（机器学习模型）",
    "大模型安全（LLM、VLM、MLLM、VLA等的安全）",
    "人工智能/大模型应用",
    "其他",
]


def _fallback(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    base = [{"name_zh": c, "summary_zh": "", "paper_ids": []} for c in FIXED_CATEGORIES]
    for it in items:
        rid = it.get("id")
        if rid:
            base[-1]["paper_ids"].append(rid)
    return {
        "overview_zh": "本次抓取论文按固定五类展示（兜底时归入其他）。",
        "groups": base,
    }


def categorize_items(items: List[Dict[str, Any]], llm_cfg: Dict[str, Any]) -> Dict[str, Any]:
    api_key = (llm_cfg.get("api_key") or
               os.getenv(llm_cfg.get("api_key_env") or "OPENAI_API_KEY", ""))
    if not api_key:
        return _fallback(items)

    try:
        data = call_llm_categorize(
            items,
            base_url=llm_cfg.get("base_url", ""),
            model=llm_cfg.get("model", ""),
            api_key=api_key,
            system_prompt=llm_cfg.get("system_prompt_categorize_zh", ""),
        )
    except Exception:
        return _fallback(items)

    idx_to_raw = {}
    for i, it in enumerate(items, 1):
        rid = it.get("id")
        if not rid:
            continue
        idx_to_raw[i] = str(rid)

    groups = [{"name_zh": c, "summary_zh": "", "paper_ids": []} for c in FIXED_CATEGORIES]
    cat_to_group = {g["name_zh"]: g for g in groups}
    seen = set()

    for a in data.get("assignments", []):
        idx = a.get("idx")
        cat = a.get("category") or ""
        raw = idx_to_raw.get(idx)
        if not raw or raw in seen:
            continue
        if cat not in cat_to_group:
            cat = "其他"
        cat_to_group[cat]["paper_ids"].append(raw)
        seen.add(raw)

    # 未覆盖的论文强制进“其他”
    missing = [it["id"] for it in items if it.get("id") and it["id"] not in seen]
    cat_to_group["其他"]["paper_ids"].extend(missing)

    # 为前四类写简单总结
    for g in groups[:-1]:
        g["summary_zh"] = f"{g['name_zh']}：共 {len(g['paper_ids'])} 篇。"
    groups[-1]["summary_zh"] = "其他：难以归入前四类或信息不足的论文。"

    return {
        "overview_zh": data.get("overview_zh") or "本次抓取论文已按固定五类完成归类。",
        "groups": groups,
    }


def categorize_by_keywords(items: List[Dict[str, Any]], keywords: List[str], num_groups: int = 5) -> Dict[str, Any]:
    """
    基于配置关键词做固定分组（默认 5 类），不再使用“其他”分类。
    """
    kwords = [k.strip() for k in (keywords or []) if (k or "").strip()]
    n = max(1, int(num_groups or 5))

    # 若关键词不足，补默认占位，确保稳定输出 n 个分类
    if len(kwords) < n:
        kwords += [f"Topic-{i+1}" for i in range(n - len(kwords))]

    buckets = [[] for _ in range(n)]
    for i, kw in enumerate(kwords):
        buckets[i % n].append(kw)

    groups = []
    for i, b in enumerate(buckets, 1):
        name = f"主题{i}"
        if b:
            name = f"{name}：{b[0]}"
        groups.append({
            "name_zh": name,
            "summary_zh": ("关键词：" + "、".join(b[:6])) if b else "关键词：—",
            "paper_ids": []
        })

    # 分类：按 matched_keywords 命中数最大归类；若都未命中，则轮转分配，避免“其他”
    for idx, it in enumerate(items):
        mk = set(it.get("matched_keywords") or [])
        scores = []
        for b in buckets:
            scores.append(len(mk.intersection(set(b))))
        best = max(scores) if scores else 0
        gid = scores.index(best) if best > 0 else (idx % n)
        if it.get("id"):
            groups[gid]["paper_ids"].append(it["id"])

    return {
        "overview_zh": f"本次论文按给定关键词划分为 {n} 个主题分类展示。",
        "groups": groups
    }
