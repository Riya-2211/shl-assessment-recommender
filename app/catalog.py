
import json
import re
from pathlib import Path
from typing import Any, Dict, List


ROOT_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT_DIR / "data" / "shl_product_catalog.json"


KEY_CODE_MAP = {
    "Ability & Aptitude": "A",
    "Biodata & Situational Judgment": "B",
    "Competencies": "C",
    "Development & 360": "D",
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Assessment Exercises": "S",
}


def _safe_json_load(path: Path):
    raw = path.read_text(encoding="utf-8")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # SHL catalog contains raw control characters in some text fields.
        # strict=False allows unescaped control chars inside strings.
        return json.loads(raw, strict=False)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    return " ".join(text.split())


def _to_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_clean_text(x) for x in value if x]
    return [_clean_text(value)]


def _test_type(keys: List[str], name: str) -> str:
    codes = []

    for key in keys:
        code = KEY_CODE_MAP.get(key)
        if code and code not in codes:
            codes.append(code)

    name_lower = name.lower()
    if "opq" in name_lower or "personality" in name_lower:
        if "P" not in codes:
            codes.append("P")

    if not codes:
        return "K"

    return ", ".join(codes)


def load_catalog() -> List[Dict[str, Any]]:
    data = _safe_json_load(CATALOG_PATH)

    catalog = []

    for item in data:
        name = _clean_text(item.get("name", ""))
        url = item.get("link") or item.get("url") or item.get("product_url")

        if not name or not url:
            continue

        url = _clean_text(url)
        keys = _to_list(item.get("keys"))
        job_levels = _to_list(item.get("job_levels"))
        languages = _to_list(item.get("languages"))
        description = _clean_text(item.get("description", ""))

        text_parts = [
            name,
            description,
            " ".join(keys),
            " ".join(job_levels),
            " ".join(languages),
            _clean_text(item.get("duration", "")),
            _clean_text(item.get("remote", "")),
            _clean_text(item.get("adaptive", "")),
        ]

        catalog.append({
            "name": name,
            "url": url,
            "test_type": _test_type(keys, name),
            "keys": keys,
            "description": description,
            "text": " ".join(text_parts),
            "raw": item,
        })

    return catalog