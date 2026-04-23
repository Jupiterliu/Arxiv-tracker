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
