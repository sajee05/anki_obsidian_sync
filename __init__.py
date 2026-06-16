# -*- coding: utf-8 -*-

"""
Anki Add-on: Obsidian Sync (Differential)

Differentially syncs Anki decks and notes to a specified Obsidian vault folder.
"""

import os
import sys
import time
import traceback

addon_path = os.path.dirname(__file__)
vendor_path = os.path.join(addon_path, "vendor")
if vendor_path not in sys.path: sys.path.insert(0, vendor_path)

missing_deps = []
try: import yaml
except ImportError: missing_deps.append("PyYAML")
try: from markdownify import markdownify
except ImportError: missing_deps.append("markdownify")

if missing_deps:
    from aqt.utils import showCritical
    showCritical(f"Missing Dependencies: {', '.join(missing_deps)}")

from aqt import mw
from aqt.qt import QAction, QMenu, qconnect
from aqt.utils import showInfo, showWarning

from .config import get_obsidian_path
from .state_builder import build_anki_state, build_obsidian_state
from .diff_calculator import calculate_diff
from .executor import execute_deletions_and_folders, execute_note_writes, execute_moc_generation
from .config_ui import show_config_dialog

def sync_to_obsidian():
    obsidian_path = get_obsidian_path()
    if not obsidian_path:
        showWarning("Obsidian sync path not configured. Please set it via Tools > Obsidian Sync > Configure...")
        return

    start_time = time.time()
    mw.progress.start(label="Starting Obsidian Sync...", immediate=True)

    try:
        anki_state = build_anki_state(mw.col)
        obsidian_state = build_obsidian_state(obsidian_path)
        assets_rel_path = obsidian_state.get("assets_folder_rel", "assets")

        actions = calculate_diff(anki_state, obsidian_state)
        if not any(v for k, v in actions.items() if isinstance(v, (list, set)) and v):
            mw.progress.finish()
            showInfo("Obsidian sync complete. No changes detected.")
            return

        execute_deletions_and_folders(actions, obsidian_state["base_path"], assets_rel_path)
        execute_note_writes(actions, obsidian_state["base_path"], assets_rel_path)
        execute_moc_generation(actions, anki_state, obsidian_state["base_path"])

        mw.progress.finish()
        showInfo(f"Obsidian sync finished successfully in {time.time() - start_time:.2f} seconds.")
    except Exception as e:
        mw.progress.finish()
        print(traceback.format_exc())
        showWarning(f"Obsidian sync failed.\nError: {e}\n\nSee console or debug log for details.")

def add_menu_items():
    if not hasattr(mw, "menuObsidianSync"):
        mw.menuObsidianSync = QMenu("Obsidian Sync by M Saajeel ⭐", mw)
        mw.form.menuTools.addMenu(mw.menuObsidianSync)

    sync_action = QAction("Sync Now", mw)
    qconnect(sync_action.triggered, sync_to_obsidian)
    mw.menuObsidianSync.addAction(sync_action)

    config_action = QAction("Configure...", mw)
    qconnect(config_action.triggered, show_config_dialog)
    mw.menuObsidianSync.addAction(config_action)

add_menu_items()