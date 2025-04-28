# -*- coding: utf-8 -*-

"""
Handles configuration storage and retrieval for the Obsidian Sync addon
by directly reading/writing config.json. (Simplified write logic)
"""

import os
import json
from typing import Optional
from aqt import mw

# Configuration key within the JSON file
CONFIG_KEY_OBSIDIAN_PATH = "obsidianSyncPath"

def _get_addon_dir() -> Optional[str]:
    """Gets the absolute path to the addon's directory."""
    # print("DEBUG: _get_addon_dir called") # DEBUG
    if not mw or not hasattr(mw, "addonManager"):
        print("Warning: Anki environment (mw.addonManager) not fully loaded.")
        return None
    try:
        addon_dir = os.path.dirname(__file__)
        if os.path.exists(os.path.join(addon_dir, "meta.json")):
             # print(f"DEBUG: Addon directory identified as: {addon_dir}") # DEBUG
             return addon_dir
        else:
             package_name = mw.addonManager.addonFromModule(__name__)
             if package_name:
                 addon_dir = mw.addonManager.addonsFolder(package_name)
                 # print(f"DEBUG: Addon directory identified via package name '{package_name}': {addon_dir}") # DEBUG
                 return addon_dir
             else:
                 print(f"Warning: Could not determine addon directory from module '{__name__}'.")
                 return None
    except Exception as e:
        print(f"DEBUG: Error getting addon directory: {e}")
        return None

def _get_config_path() -> Optional[str]:
    """Gets the absolute path to the config.json file."""
    addon_dir = _get_addon_dir()
    return os.path.join(addon_dir, "config.json") if addon_dir else None

def _read_config() -> dict:
    """Reads the config.json file."""
    config_path = _get_config_path()
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # print(f"DEBUG: Read config from {config_path}: {json.dumps(config)}") # DEBUG
                return config if isinstance(config, dict) else {}
        except (json.JSONDecodeError, OSError) as e:
            print(f"Error reading config file {config_path}: {e}")
            return {}
    else:
        # print(f"DEBUG: Config file not found at {config_path}") # DEBUG
        return {}

def _write_config(config: dict):
    """Writes the config dictionary to config.json."""
    config_path = _get_config_path()
    if not config_path:
        print("Error: Cannot write config, addon directory not found.")
        return
    try:
        print(f"DEBUG: Writing config to {config_path}: {json.dumps(config)}") # DEBUG
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        print("DEBUG: Config file written successfully.") # DEBUG
    except OSError as e:
        print(f"Error writing config file {config_path}: {e}")
        from aqt.utils import showWarning
        showWarning(f"Could not write addon configuration.\nError: {e}")

def get_obsidian_path() -> Optional[str]:
    """Retrieves the configured Obsidian sync path from config.json."""
    # print("DEBUG: get_obsidian_path (using config.json) called") # DEBUG
    config = _read_config()
    path = config.get(CONFIG_KEY_OBSIDIAN_PATH)
    # print(f"DEBUG: Path retrieved from config.json: {path!r}") # DEBUG
    if path and os.path.isdir(path):
        # print("DEBUG: Path is valid directory.") # DEBUG
        return path
    elif path:
        print(f"Warning: Stored Obsidian path is invalid or inaccessible: {path}")
        return None
    return None

def set_obsidian_path(path: str):
    """Saves the Obsidian sync path to config.json by overwriting."""
    print(f"DEBUG: set_obsidian_path (using config.json - overwrite) called with path: {path!r}") # DEBUG
    # Basic validation before saving
    if not path or not os.path.isdir(path):
        print(f"Error: Attempted to save invalid path: {path}")
        return

    # Create a dictionary containing only the key to save
    config_to_write = {CONFIG_KEY_OBSIDIAN_PATH: path}
    # Write this dictionary, overwriting the file
    _write_config(config_to_write)