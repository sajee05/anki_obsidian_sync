# -*- coding: utf-8 -*-

"""
Handles configuration storage and retrieval for the Obsidian Sync addon.
Supports per-Anki-profile config isolation via a "profiles" key in config.json.

Config file schema:
    {
        "profiles": {
            "<profile_name>": {
                "obsidianSyncPath": "...",
                "excludedDecks": [...],
                "filenameSuffix": "..."
            }
        },
        "lastProfile": "<profile_name>"
    }

Auto-migrates old flat config.json into the nested format on first read.
"""

import os
import json
from typing import Optional, List
from aqt import mw

# --- config key names (used inside profile dicts) ---
CONFIG_KEY_OBSIDIAN_PATH = "obsidianSyncPath"
CONFIG_KEY_EXCLUDED_DECKS = "excludedDecks"
CONFIG_KEY_FILENAME_SUFFIX = "filenameSuffix"

# --- root-level keys for profile isolation ---
_ROOT_PROFILES = "profiles"
_ROOT_LAST_PROFILE = "lastProfile"

_DEFAULT_PROFILE = "default"


# ═══════════════════ Low-level file I/O ═══════════════════

def _get_addon_dir() -> Optional[str]:
    if not mw or not hasattr(mw, "addonManager"):
        return None
    try:
        addon_dir = os.path.dirname(__file__)
        if os.path.exists(os.path.join(addon_dir, "meta.json")):
            return addon_dir
        package_name = mw.addonManager.addonFromModule(__name__)
        if package_name:
            return mw.addonManager.addonsFolder(package_name)
        return None
    except Exception:
        return None


def _get_config_path() -> Optional[str]:
    addon_dir = _get_addon_dir()
    return os.path.join(addon_dir, "config.json") if addon_dir else None


def _read_raw() -> dict:
    """Read the full config.json as-is."""
    config_path = _get_config_path()
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                return cfg if isinstance(cfg, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _write_raw(config: dict):
    config_path = _get_config_path()
    if not config_path:
        return
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
    except OSError as e:
        from aqt.utils import showWarning
        showWarning(f"Could not write addon configuration.\nError: {e}")


# ═══════════════════ Profile resolution ═══════════════════

ALL_KEYS = {CONFIG_KEY_OBSIDIAN_PATH, CONFIG_KEY_EXCLUDED_DECKS, CONFIG_KEY_FILENAME_SUFFIX}


def _current_profile() -> str:
    """Return the active Anki profile name (or 'default')."""
    if mw and hasattr(mw, 'pm'):
        name = mw.pm.name
        if name:
            return name
    return _DEFAULT_PROFILE


def _ensure_profiles(root: dict) -> dict:
    """Convert an old flat config into nested {profiles: {…}} in-place.

    Returns the root dict (mutated if migration happened).
    """
    if _ROOT_PROFILES in root:
        return root  # already migrated

    migrated = {
        _ROOT_PROFILES: {_DEFAULT_PROFILE: {}},
        _ROOT_LAST_PROFILE: _DEFAULT_PROFILE,
    }
    # Copy any known flat keys into the default profile
    dst = migrated[_ROOT_PROFILES][_DEFAULT_PROFILE]
    for k in ALL_KEYS:
        if k in root:
            dst[k] = root[k]
    # Also preserve any unknown keys at top level (forward compat)
    for k, v in root.items():
        if k not in (ALL_KEYS | {_ROOT_PROFILES, _ROOT_LAST_PROFILE}):
            dst.setdefault(k, v)

    root.clear()
    root.update(migrated)
    return root


def _profile_config() -> dict:
    """Return the config dict for the *current* Anki profile.

    Lazily migrates old-format config.json on first call.
    """
    root = _read_raw()
    root = _ensure_profiles(root)
    profile = _current_profile()
    return root.setdefault(_ROOT_PROFILES, {}).setdefault(profile, {})


def _write_profile(profile_cfg: dict):
    """Persist *profile_cfg* as the current profile's entire config dict."""
    root = _read_raw()
    root = _ensure_profiles(root)
    profile = _current_profile()
    root.setdefault(_ROOT_PROFILES, {})[profile] = profile_cfg
    root[_ROOT_LAST_PROFILE] = profile
    _write_raw(root)


def _read_profile_field(key: str, default=None):
    """Read *key* from the current profile's config."""
    return _profile_config().get(key, default)


# ═══════════════════ Public API ═══════════════════

def get_obsidian_path() -> Optional[str]:
    path = _read_profile_field(CONFIG_KEY_OBSIDIAN_PATH)
    if path and os.path.isdir(path):
        return path
    return None


def set_obsidian_path(path: str):
    if not path or not os.path.isdir(path):
        return
    cfg = _profile_config()
    cfg[CONFIG_KEY_OBSIDIAN_PATH] = path
    _write_profile(cfg)


def get_excluded_decks() -> List[str]:
    return _read_profile_field(CONFIG_KEY_EXCLUDED_DECKS, [])


def set_excluded_decks(decks: List[str]):
    cfg = _profile_config()
    cfg[CONFIG_KEY_EXCLUDED_DECKS] = decks
    _write_profile(cfg)


def get_filename_suffix() -> str:
    return _read_profile_field(CONFIG_KEY_FILENAME_SUFFIX, "nid")


def set_filename_suffix(value: str):
    cfg = _profile_config()
    cfg[CONFIG_KEY_FILENAME_SUFFIX] = value
    _write_profile(cfg)
