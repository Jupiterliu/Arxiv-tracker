# -*- coding: utf-8 -*-
from typing import Dict, Any

from deep_translator import GoogleTranslator


def _safe_translate(text: str, target: str = "zh-CN") -> str:
    t = (text or "").strip()
    if not t:
        return ""
    try:
        return GoogleTranslator(source="auto", target=target).translate(t) or ""
    except Exception:
        return ""


def translate_item(item: Dict[str, Any], target_lang: str = "zh") -> Dict[str, str]:
    """
    使用翻译工具（非 LLM）翻译标题/摘要/备注。
    """
    target = "zh-CN" if target_lang == "zh" else target_lang
    out: Dict[str, str] = {
        "title_zh": _safe_translate(item.get("title", ""), target=target),
        "summary_zh": _safe_translate(item.get("summary", ""), target=target),
    }
    comments = (item.get("comments") or "").strip()
    if comments:
        out["comments_zh"] = _safe_translate(comments, target=target)
    return out
