import json
import os
from functools import lru_cache
from typing import Any, Dict, Optional

REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "ai_models.json")

ALIASES = {
    "GPT3.5": "GPT35",
    "gpt-3.5-turbo": "GPT35",
    "gpt-4": "GPT4",
    "gpt-4o": "GPT4O",
    "gpt-4o-mini": "GPT4OMini",
    "meta-llama/Llama-2-70b-chat-hf": "LLAMA2",
}


@lru_cache(maxsize=1)
def _load() -> Dict[str, Dict[str, Any]]:
    """
    Load the ai_models.json registry and return two maps:
      - by_internal: { internal_name: entry }
      - by_id: { model_id: { entry fields + 'internal_name': internal_name } }
    """
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    by_internal: Dict[str, Dict[str, Any]] = {}
    by_id: Dict[str, Dict[str, Any]] = {}

    for internal_name, entry in data.items():
        by_internal[internal_name] = entry.copy()
        # Save the internal name on the entry copy for convenience
        if "internal_name" not in by_internal[internal_name]:
            by_internal[internal_name]["internal_name"] = internal_name

        model_id = entry.get("model_id")
        if model_id:
            # store a copy that includes the internal name for reverse lookup
            by_id[model_id] = {**entry, "internal_name": internal_name}

    return {"by_internal": by_internal, "by_id": by_id}


def _canonical(name: str) -> str:
    """Apply aliasing to map a name to a canonical internal registry key."""
    return ALIASES.get(name, name)


def entry_from_internal_name(internal_name: str) -> Optional[Dict[str, Any]]:
    """
    Return the registry entry (dict) for a given internal name (or alias).
    """
    if not internal_name or not isinstance(internal_name, str):
        return None
    name = _canonical(internal_name)
    return _load()["by_internal"].get(name)


def entry_from_id(model_id: str) -> Optional[Dict[str, Any]]:
    """
    Return the registry entry (dict) for a given model_id (mdl_...).
    The returned entry will include an 'internal_name' field.
    """
    if not model_id or not isinstance(model_id, str):
        return None
    return _load()["by_id"].get(model_id)


def id_from_internal_name(internal_name: str) -> Optional[str]:
    """
    Map an internal name (or alias) to its model_id (mdl_...).
    Returns None if not found.
    """
    entry = entry_from_internal_name(internal_name)
    if entry:
        return entry.get("model_id")
    return None


def internal_name_from_id(model_id: str) -> Optional[str]:
    """
    Reverse map a model_id (mdl_...) to the registry internal name.
    Returns None if not found.
    """
    entry = entry_from_id(model_id)
    if entry:
        return entry.get("internal_name")
    return None


def resolve_to_entry(value: str) -> Optional[Dict[str, Any]]:
    """
    Given a string that may be a model_id (mdl_...) or an internal name (or alias),
    return the full registry entry (with internal_name) or None.

    This is a convenience for code that wants to accept either form.
    """
    if not value or not isinstance(value, str):
        return None
    if value.startswith("mdl_"):
        return entry_from_id(value)
    return entry_from_internal_name(value)


def reload_registry() -> None:
    """Clear cache so subsequent calls re-read ai_models.json."""
    _load.cache_clear()