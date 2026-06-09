"""
Portable local-data layer for Vāṇi.

Deliberately backend-agnostic: this module has **no Streamlit and no Google
dependencies**. It persists plain JSON under a local ``data/`` directory, so the
same API can later be re-pointed at SQLite, a mobile key-value store, or a sync
service without changing any callers.

Public API (Phase 1):
    get_progress()            -> full progress dict
    is_mastered(topic)        -> bool
    set_mastered(topic, score)-> records a topic as mastered
    clear_mastered(topic)     -> removes a mastery record (useful for re-testing)

The on-disk shape of ``data/progress.json`` is::

    {"mastered": {"<topic name>": {"mastered_at": "<iso8601>", "score": "9/10"}}}
"""

import json
import os
from datetime import datetime

# Resolve paths relative to this file so behavior is independent of the current
# working directory (matters when packaged or launched from elsewhere).
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_BASE_DIR, "data")
PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")


# ---------------------------------------------------------------------------
# Generic JSON helpers (reusable by future stores, e.g. SRS / vocabulary)
# ---------------------------------------------------------------------------
def _read_json(path, default):
    """Return parsed JSON at ``path``, or ``default`` if missing/corrupt."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write_json(path, data):
    """Write ``data`` to ``path`` as UTF-8 JSON, creating the dir if needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Mastery progress
# ---------------------------------------------------------------------------
def get_progress():
    """Return the full progress dict, with a guaranteed ``mastered`` key."""
    data = _read_json(PROGRESS_FILE, {})
    if "mastered" not in data or not isinstance(data.get("mastered"), dict):
        data["mastered"] = {}
    return data


def is_mastered(topic):
    """True if ``topic`` has been recorded as mastered."""
    return topic in get_progress()["mastered"]


def set_mastered(topic, score=None):
    """Record ``topic`` as mastered (optionally with a score string)."""
    data = get_progress()
    data["mastered"][topic] = {
        "mastered_at": datetime.now().isoformat(timespec="seconds"),
        "score": score,
    }
    _write_json(PROGRESS_FILE, data)


def clear_mastered(topic):
    """Remove a mastery record so the topic can be re-tested. No-op if absent."""
    data = get_progress()
    if topic in data["mastered"]:
        del data["mastered"][topic]
        _write_json(PROGRESS_FILE, data)
