from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, Optional


VALID_LEVELS = {"fatal", "error", "warn", "info"}


def normalize_level(level: str) -> str:
    normalized = (level or "").lower()
    if normalized not in VALID_LEVELS:
        raise ValueError(f"invalid level: {level}")
    return normalized


def default_event_key(level: str, raw_content: str) -> str:
    content = "" if raw_content is None else str(raw_content)
    digest = hashlib.sha1(content.encode("utf-8")).hexdigest()
    return f"{level}:{digest[:12]}"


def build_event(
    raw_content: Any,
    type: str = "text",
    level: str = "info",
    event_key: Optional[str] = None,
    source: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    meta: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_level = normalize_level(level)
    content = "" if raw_content is None else str(raw_content)
    content_type = (type or "text").lower()
    key = event_key or default_event_key(normalized_level, content)
    created_at = timestamp or datetime.now(timezone.utc).isoformat()
    if not isinstance(context, dict):
        context = {}
    if not isinstance(meta, dict):
        meta = {}
    return {
        "event_key": key,
        "level": normalized_level,
        "raw_content": content,
        "type": content_type,
        "source": source,
        "context": context,
        "meta": meta,
        "timestamp": created_at,
    }
