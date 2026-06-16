# -*- coding: utf-8 -*-

"""
Handles configuration storage and retrieval for the Obsidian Sync addon
by directly reading/writing config.json.
"""

import os
import json
from typing import Optional, List
from aqt import mw

CONFIG_KEY_OBSIDIAN_PATH = "obsidianSyncPath"
CONFIG_KEY_EXCLUDED_DECKS = "excludedDecks"

def _get_addon_dir() -> Optional[str]:
    """Gets the absolute path to the addon's directory."""
    if not mw or not hasattr(mw, "addonManager"):
        return None
    try:
        addon_dir = os.path.dirname(__file__)
        if os.path.exists(os.path.join(addon_dir, "meta.json")):
             return addon_dir
        else:
             package_name = mw.addonManager.addonFromModule(__name__)
             if package_name:
                 return mw.addonManager.addonsFolder(package_name)
             return None
    except Exception:
        return None

def _get_config_path() -> Optional[str]:
    addon_dir = _get_addon_dir()
    return os.path.join(addon_dir, "config.json") if addon_dir else None

def _read_config() -> dict:
    config_path = _get_config_path()
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config if isinstance(config, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}
    return {}

def _write_config(config: dict):
    config_path = _get_config_path()
    if not config_path:
        return
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except OSError as e:
        from aqt.utils import showWarning
        showWarning(f"Could not write addon configuration.\nError: {e}")

def get_obsidian_path() -> Optional[str]:
    config = _read_config()
    path = config.get(CONFIG_KEY_OBSIDIAN_PATH)
    if path and os.path.isdir(path):
        return path
    return None

def set_obsidian_path(path: str):
    if not path or not os.path.isdir(path):
        return
    config = _read_config()
    config[CONFIG_KEY_OBSIDIAN_PATH] = path
    _write_config(config)

def get_excluded_decks() -> List[str]:
    config = _read_config()
    return config.get(CONFIG_KEY_EXCLUDED_DECKS, [])

def set_excluded_decks(decks: List[str]):
    config = _read_config()
    config[CONFIG_KEY_EXCLUDED_DECKS] = decks
    _write_config(config)