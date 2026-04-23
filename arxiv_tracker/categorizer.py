# -*- coding: utf-8 -*-
from typing import Dict, Any, List

FIXED_CATEGORIES = [
    "传统网络安全（密码、系统）",
    "传统人工智能安全（机器学习模型）",
    "大模型安全（LLM、VLM、MLLM、VLA等的安全）",
    "人工智能/大模型应用",
]

SECURITY_TERMS = {
    "security", "secure", "attack", "adversarial", "jailbreak", "backdoor",
    "poison", "poisoning", "privacy", "robustness", "defense", "defence",
    "intrusion", "malicious", "watermark", "extraction", "stealing", "hijack",
    "membership inference", "model extraction", "model stealing", "prompt injection",
}
TRAD_NETSEC_TERMS = {
    "crypt", "cipher", "encryption", "decryption", "password", "auth", "authentication",
    "system", "kernel", "os", "network", "protocol", "distributed systems", "binary",
}
TRAD_AI_TERMS = {
    "cnn", "rnn", "svm", "xgboost", "federated", "federated learning",
    "classifier", "传统", "machine learning", "graph neural", "gnn",
}
LLM_TERMS = {
    "llm", "vlm", "mllm", "vla", "gpt", "large language model", "vision-language",
    "multimodal", "agent", "instruction tuning", "reasoning model",
}


def _contains_any(text: str, terms: set) -> bool:
    t = text.lower()
    return any(x in t for x in terms)


def categorize_items(items: List[Dict[str, Any]], llm_cfg: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    固定匹配机制分类（不依赖 LLM）：
    1) 大模型安全（需同时命中 LLM 相关 + 安全相关）
    2) 传统人工智能安全（需同时命中 传统AI相关 + 安全相关）
    3) 传统网络安全（需同时命中 系统/密码相关 + 安全相关）
    4) 其余归入 人工智能/大模型应用
    """
    groups = [{"name_zh": c, "summary_zh": "", "paper_ids": []} for c in FIXED_CATEGORIES]
    gmap = {g["name_zh"]: g for g in groups}

    for it in items:
        rid = it.get("id")
        if not rid:
            continue
        text = " ".join([it.get("title") or "", it.get("summary") or ""])
        has_sec = _contains_any(text, SECURITY_TERMS)
        has_llm = _contains_any(text, LLM_TERMS)
        has_trad_ai = _contains_any(text, TRAD_AI_TERMS)
        has_netsec = _contains_any(text, TRAD_NETSEC_TERMS)

        if has_sec and has_llm:
            gmap["大模型安全（LLM、VLM、MLLM、VLA等的安全）"]["paper_ids"].append(rid)
        elif has_sec and has_trad_ai:
            gmap["传统人工智能安全（机器学习模型）"]["paper_ids"].append(rid)
        elif has_sec and has_netsec:
            gmap["传统网络安全（密码、系统）"]["paper_ids"].append(rid)
        else:
            gmap["人工智能/大模型应用"]["paper_ids"].append(rid)

    for g in groups:
        g["summary_zh"] = f"{g['name_zh']}：共 {len(g['paper_ids'])} 篇。"
    return {
        "overview_zh": "本次抓取论文按固定规则完成分类，后续每类可由大模型生成总结。",
        "groups": groups,
    }
