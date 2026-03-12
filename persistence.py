"""
persistence.py — Save/load multiple company profiles and their document checklists.

Storage layout in ./data/profiles.json:
{
  "profiles": {
    "<company_id>": {
      "company_name": "...",
      "company_industry": "...",
      "company_profile": { ... },
      "doc_checked": { ... }
    }
  },
  "last_used": "<company_id>"
}
"""
from __future__ import annotations

import json
import os
import uuid
from typing import Any, Dict, List, Optional

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
PROFILES_FILE = os.path.join(DATA_DIR, "profiles.json")


def _ensure_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _read() -> Dict[str, Any]:
    _ensure_dir()
    # Also migrate old session.json if it exists
    old_file = os.path.join(DATA_DIR, "session.json")
    if not os.path.exists(PROFILES_FILE) and os.path.exists(old_file):
        try:
            with open(old_file, "r", encoding="utf-8") as f:
                old = json.load(f)
            if old.get("company_profile"):
                pid = str(uuid.uuid4())[:8]
                migrated = {
                    "profiles": {pid: {
                        "company_name": old.get("company_name", ""),
                        "company_industry": old.get("company_industry", ""),
                        "company_profile": old.get("company_profile", {}),
                        "doc_checked": old.get("doc_checked", {}),
                    }},
                    "last_used": pid,
                }
                _write_raw(migrated)
                return migrated
        except (json.JSONDecodeError, OSError):
            pass
    if not os.path.exists(PROFILES_FILE):
        return {"profiles": {}, "last_used": None}
    try:
        with open(PROFILES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "profiles" not in data:
                data["profiles"] = {}
            return data
    except (json.JSONDecodeError, OSError):
        return {"profiles": {}, "last_used": None}


def _write_raw(data: Dict[str, Any]) -> None:
    _ensure_dir()
    try:
        with open(PROFILES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def _write(data: Dict[str, Any]) -> None:
    _write_raw(data)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def list_profiles() -> List[Dict[str, Any]]:
    """Return list of saved profiles as [{"id", "company_name", ...}]."""
    data = _read()
    result = []
    for pid, profile in data["profiles"].items():
        result.append({
            "id": pid,
            "company_name": profile.get("company_name", "Unknown"),
            "company_industry": profile.get("company_industry", ""),
            "company_profile": profile.get("company_profile", {}),
            "doc_checked": profile.get("doc_checked", {}),
        })
    return result


def get_last_used_id() -> Optional[str]:
    return _read().get("last_used")


def save_profile(
    company_name: str,
    company_industry: str,
    company_profile: Dict,
    doc_checked: Dict,
    profile_id: Optional[str] = None,
) -> str:
    """Save or update a company profile. Returns the profile_id."""
    data = _read()
    pid = profile_id or str(uuid.uuid4())[:8]
    data["profiles"][pid] = {
        "company_name": company_name,
        "company_industry": company_industry,
        "company_profile": company_profile,
        "doc_checked": doc_checked,
    }
    data["last_used"] = pid
    _write(data)
    return pid


def update_doc_checked(profile_id: str, doc_checked: Dict) -> None:
    """Update only the checklist state for an existing profile."""
    data = _read()
    if profile_id in data["profiles"]:
        data["profiles"][profile_id]["doc_checked"] = doc_checked
        _write(data)


def delete_profile(profile_id: str) -> None:
    data = _read()
    data["profiles"].pop(profile_id, None)
    if data.get("last_used") == profile_id:
        remaining = list(data["profiles"].keys())
        data["last_used"] = remaining[-1] if remaining else None
    _write(data)


def set_last_used(profile_id: str) -> None:
    data = _read()
    data["last_used"] = profile_id
    _write(data)


# ---------------------------------------------------------------------------
# Legacy shim
# ---------------------------------------------------------------------------

def load_session() -> Dict[str, Any]:
    profiles = list_profiles()
    last_id = get_last_used_id()
    for p in profiles:
        if p["id"] == last_id:
            return p
    return profiles[0] if profiles else {}


def save_session(data: Dict[str, Any]) -> None:
    pid = data.get("profile_id") or get_last_used_id()
    save_profile(
        company_name=data.get("company_name", ""),
        company_industry=data.get("company_industry", ""),
        company_profile=data.get("company_profile", {}),
        doc_checked=data.get("doc_checked", {}),
        profile_id=pid,
    )