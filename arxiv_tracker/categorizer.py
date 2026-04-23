# -*- coding: utf-8 -*-
from typing import Dict, Any, List
import os

from .llm import call_llm_categorize
from .ids import canonical_arxiv_id


def _fallback(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    groups: Dict[str, Dict[str, Any]] = {}
    for it in items:
        label = (it.get("primary_category") or "其他").strip()
        if not label:
            label = "其他"
        g = groups.setdefault(label, {"name_zh": label, "summary_zh": "", "paper_ids": []})
        if it.get("id"):
            g["paper_ids"].append(it["id"])
    return {
        "overview_zh": "本次抓取论文按 arXiv 学科标签进行分组展示。",
        "groups": list(groups.values())[:10],
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

    by_id = {it.get("id"): it for it in items if it.get("id")}
    id_alias_to_raw = {}
    for it in items:
        rid = it.get("id")
        if not rid:
            continue
        id_alias_to_raw[str(rid)] = str(rid)
        cid = canonical_arxiv_id(str(rid))
        if cid:
            id_alias_to_raw[cid] = str(rid)
    seen = set()
    clean_groups = []
    for g in data.get("groups", []):
        ids = []
        for pid in (g.get("paper_ids") or []):
            raw = id_alias_to_raw.get(str(pid))
            if not raw:
                raw = id_alias_to_raw.get(canonical_arxiv_id(str(pid)))
            if not raw or raw in seen:
                continue
            ids.append(raw)
        if not ids:
            continue
        seen.update(ids)
        clean_groups.append({
            "name_zh": g.get("name_zh") or "未命名类别",
            "summary_zh": g.get("summary_zh") or "",
            "paper_ids": ids,
        })

    # 把漏掉的论文放到“其他”
    missing = [it["id"] for it in items if it.get("id") and it["id"] not in seen]
    if missing:
        clean_groups.append({
            "name_zh": "其他",
            "summary_zh": "未被模型明确归类的论文。",
            "paper_ids": missing,
        })

    return {
        "overview_zh": data.get("overview_zh") or "本次抓取论文已按主题分类展示。",
        "groups": clean_groups[:10],
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
