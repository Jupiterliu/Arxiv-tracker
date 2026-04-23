# -*- coding: utf-8 -*-
from typing import Dict, Any, List
import os

from .llm import call_llm_classify_paper

FIXED_CATEGORIES = [
    "传统网络安全（密码、系统）",
    "传统人工智能安全（机器学习模型）",
    "大模型安全（LLM、VLM、MLLM、VLA等的安全）",
    "人工智能/大模型应用",
    "其他",
]


def categorize_items(items: List[Dict[str, Any]], llm_cfg: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    对每篇论文调用一次大模型，强制归到固定5类之一。
    """
    llm_cfg = llm_cfg or {}
    api_key = (llm_cfg.get("api_key") or
               os.getenv(llm_cfg.get("api_key_env") or "OPENAI_API_KEY", ""))
    groups = [{"name_zh": c, "summary_zh": "", "paper_ids": []} for c in FIXED_CATEGORIES]
    gmap = {g["name_zh"]: g for g in groups}

    for it in items:
        rid = it.get("id")
        if not rid:
            continue
        cat = "其他"
        if api_key:
            try:
                pred = call_llm_classify_paper(
                    it,
                    base_url=llm_cfg.get("base_url", ""),
                    model=llm_cfg.get("model", ""),
                    api_key=api_key,
                    categories=FIXED_CATEGORIES,
                    system_prompt=llm_cfg.get("system_prompt_categorize_zh", ""),
                )
                if pred in gmap:
                    cat = pred
            except Exception:
                cat = "其他"
        gmap[cat]["paper_ids"].append(rid)

    for g in groups:
        g["summary_zh"] = f"{g['name_zh']}：共 {len(g['paper_ids'])} 篇。"
    return {
        "overview_zh": "",
        "groups": groups,
    }
