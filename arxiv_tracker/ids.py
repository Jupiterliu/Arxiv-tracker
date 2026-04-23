# -*- coding: utf-8 -*-
import re


_ARXIV_ID_RE = re.compile(r"(?:arxiv\.org/(?:abs|pdf)/)?(?P<id>\d{4}\.\d{4,5})(?:v\d+)?", re.IGNORECASE)


def canonical_arxiv_id(raw_id: str) -> str:
    """
    将 arXiv id 统一为不含版本号的 canonical 形式（如 2501.01234）。
    兼容输入：
    - https://arxiv.org/abs/2501.01234v2
    - http://arxiv.org/pdf/2501.01234v1
    - 2501.01234v3
    """
    s = (raw_id or "").strip()
    if not s:
        return ""
    m = _ARXIV_ID_RE.search(s)
    if m:
        return m.group("id")
    # 兜底：去掉末尾版本号
    return re.sub(r"v\d+$", "", s, flags=re.IGNORECASE)
