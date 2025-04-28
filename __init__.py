# -*- coding: utf-8 -*-

"""
Anki Add-on: Obsidian Sync (Differential)

Differentially syncs Anki decks and notes to a specified Obsidian vault folder.
"""

import os
import sys
from typing import Optional
import time # For timing the sync process
import traceback # For error logging

# Add vendor directory to sys.path to bundle dependencies
addon_path = os.path.dirname(__file__)
vendor_path = os.path.join(addon_path, "vendor")
if vendor_path not in sys.path:
    sys.path.insert(0, vendor_path)

# --- Dependency Checks ---
missing_deps = []
try:
    import yaml
except ImportError:
    missing_deps.append("PyYAML")

try:
    from markdownify import markdownify
except ImportError:
    missing_deps.append("markdownify")

if missing_deps:
    from aqt.utils import showCritical
    showCritical(
        "Obsidian Sync Error: Missing Dependencies\n\n"
        f"The following libraries are required but were not found:\n - {', '.join(missing_deps)}\n\n"
        "Please install them or place them in the addon's 'vendor' folder.\n"
        "The addon may not function correctly without them.",
        title="Addon Load Error"
    )
# --- End Dependency Checks ---

# Anki imports
from aqt import mw, gui_hooks
from aqt.qt import QAction, QMenu, qconnect
from aqt.utils import showInfo, showWarning, tooltip, askUser

# Local imports for sync logic
from .config import get_obsidian_path
from .state_builder import build_anki_state, build_obsidian_state
from .diff_calculator import calculate_diff
# Import renamed function execute_note_writes
from .executor import execute_deletions_and_folders, execute_note_writes, execute_moc_generation
from .config_ui import show_config_dialog

# --- Main Sync Logic ---

def sync_to_obsidian():
    """Main function to trigger the sync process."""
    obsidian_path = get_obsidian_path()
    if not obsidian_path:
        showWarning("Obsidian sync path not configured. Please set it via Tools > Obsidian Sync > Configure...")
        return

    start_time = time.time()
    showInfo(f"Starting sync to Obsidian folder: {obsidian_path}")
    mw.progress.start(label="Starting Obsidian Sync...", immediate=True)

    try:
        # --- Phase 1: State Representation (Note-Centric) ---
        if not mw.col:
            showWarning("Anki collection not available.")
            mw.progress.finish()
            return
        anki_state = build_anki_state(mw.col)
        obsidian_state = build_obsidian_state(obsidian_path)
        assets_rel_path = obsidian_state.get("assets_folder_rel", "assets")

        # --- Phase 2: Comparison & Action Planning (Note-Centric) ---
        actions = calculate_diff(anki_state, obsidian_state)

        # Check if there's anything to do
        if not any(v for k, v in actions.items() if isinstance(v, (list, set)) and v):
            mw.progress.finish()
            showInfo("Obsidian sync complete. No changes detected.")
            return

        # --- Confirmation (Optional) ---
        # ... (confirmation code remains the same) ...

        # --- Phase 3: Execution - Deletions & Folder Structure ---
        execute_deletions_and_folders(actions, obsidian_state["base_path"], assets_rel_path)

        # --- Phase 4: Execution - Note File Writing ---
        # Call the renamed function
        execute_note_writes(actions, obsidian_state["base_path"], assets_rel_path)

        # --- Phase 5: Execution - Linking & MOC Generation ---
        execute_moc_generation(actions, anki_state, obsidian_state["base_path"])

        # --- Phase 6: Refinement ---
        # ...

        end_time = time.time()
        duration = end_time - start_time
        mw.progress.finish()
        showInfo(f"Obsidian sync finished successfully in {duration:.2f} seconds.")

    except Exception as e:
        mw.progress.finish()
        error_details = traceback.format_exc()
        print("--- Obsidian Sync Error ---")
        print(error_details)
        print("---------------------------")
        try:
            duration = time.time() - start_time
            showWarning(f"Obsidian sync failed after {duration:.2f} seconds.\nError: {e}\n\nSee console or debug log for details.")
        except NameError:
             showWarning(f"Obsidian sync failed.\nError: {e}\n\nSee console or debug log for details.")

# --- Menu Setup ---

def add_menu_items():
    """Adds menu items to Anki's Tools menu."""
    if not hasattr(mw, "menuObsidianSync"):
        mw.menuObsidianSync = QMenu("Obsidian Sync by M Saajeel ⭐", mw)
        mw.form.menuTools.addMenu(mw.menuObsidianSync)

    sync_action = QAction("Sync Now", mw)
    qconnect(sync_action.triggered, sync_to_obsidian)
    mw.menuObsidianSync.addAction(sync_action)

    config_action = QAction("Configure...", mw)
    qconnect(config_action.triggered, show_config_dialog)
    mw.menuObsidianSync.addAction(config_action)

# Initialize menu when Anki starts
add_menu_items()

print("Obsidian Sync (Differential) Addon Loaded.")