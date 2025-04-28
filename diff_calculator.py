# -*- coding: utf-8 -*-

"""
Compares the Anki state (note-centric) and Obsidian state representations
to determine the necessary filesystem actions (Create, Update, Delete).
Uses custom MOC naming convention and links MOCs hierarchically.
"""

from typing import Dict, Any, Set, List, Tuple
from pathlib import Path
import os

# Local import for root MOC filename constant
from .state_builder import ROOT_MOC_FILENAME

def calculate_diff(anki_state: Dict[str, Any], obsidian_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares the note-centric Anki and Obsidian states and returns actions.
    Uses custom MOC naming convention and links MOCs hierarchically.
    """
    print("Calculating differences between Anki and Obsidian states (Note-Centric)...")

    actions = {
        "folders_to_create": [], "folders_to_delete": [],
        "notes_to_create": [], "notes_to_update": [], "notes_to_delete": [],
        "images_to_copy": set(), "images_to_delete": set(),
        "mocs_to_create": set(), # MOCs that need to be created
        "mocs_to_update": set(), # Existing MOCs that need content update
        "mocs_to_delete": set()  # MOCs that should no longer exist
    }

    # --- Folder Diff ---
    anki_folders = set(anki_state.keys()) - {"_root_"}
    obs_folders = obsidian_state.get("folders", set())
    actions["folders_to_create"] = list(anki_folders - obs_folders)
    print(f"Folders to create: {len(actions['folders_to_create'])}")

    # --- Note Diff ---
    obs_notes_by_anki_id: Dict[int, Dict] = {}
    obs_rel_paths_processed = set()
    for rel_path, obs_note_data in obsidian_state.get("note_files", {}).items():
        anki_note_id = obs_note_data.get("anki_note_id")
        if anki_note_id is not None:
            if anki_note_id not in obs_notes_by_anki_id:
                 obs_notes_by_anki_id[anki_note_id] = {"obs_rel_path": rel_path, **obs_note_data}
            # else: print(f"Warning: Duplicate Obsidian file found for Anki Note ID {anki_note_id}. Ignoring {rel_path}")

    all_required_anki_images = set()
    anki_note_id_to_deck_path = {}
    decks_with_notes = set() # Track decks that directly contain notes

    # --- Iterate Anki State ---
    for deck_path, deck_data in anki_state.items():
        if deck_path == "_root_": continue
        deck_has_notes = bool(deck_data.get("notes"))
        if deck_has_notes:
            decks_with_notes.add(deck_path)

        for note_id, anki_note_data in deck_data.get("notes", {}).items():
            anki_note_id_to_deck_path[note_id] = deck_path
            all_required_anki_images.update(anki_note_data.get("required_images", set()))
            target_rel_path = os.path.join(deck_path, anki_note_data['target_filename']).replace('\\', '/')
            obs_note_match = obs_notes_by_anki_id.get(note_id)

            if obs_note_match: # Note exists in Obsidian
                obs_rel_path = obs_note_match["obs_rel_path"]
                obs_rel_paths_processed.add(obs_rel_path)
                needs_move = (obs_rel_path != target_rel_path)
                anki_mod_time = anki_note_data.get("note_mod_time")
                obs_mod_time = obs_note_match.get("anki_note_mod")
                needs_update = (anki_mod_time is None or obs_mod_time is None or anki_mod_time > obs_mod_time)

                if needs_update or needs_move:
                    actions["notes_to_update"].append({
                        "anki_note_data": anki_note_data, "deck_path": deck_path,
                        "target_rel_path": target_rel_path, "obs_note_data": obs_note_match,
                        "needs_move": needs_move
                    })
            else: # Note needs to be created
                actions["notes_to_create"].append({
                    "anki_note_data": anki_note_data, "deck_path": deck_path,
                    "target_rel_path": target_rel_path
                })

    # --- Find Obsidian notes to delete ---
    obs_note_files_all_paths = set(obsidian_state.get("note_files", {}).keys())
    notes_to_delete_paths = obs_note_files_all_paths - obs_rel_paths_processed
    for rel_path in notes_to_delete_paths:
        obs_note_data = obsidian_state["note_files"][rel_path]
        if obs_note_data.get("anki_note_id") is not None:
            actions["notes_to_delete"].append({
                "obs_note_data": obs_note_data, "target_rel_path": rel_path
            })

    print(f"Notes to create: {len(actions['notes_to_create'])}")
    print(f"Notes to update/move: {len(actions['notes_to_update'])}")
    print(f"Notes to delete: {len(actions['notes_to_delete'])}")

    # --- Image Diff (Same) ---
    obs_assets = obsidian_state.get("asset_files", set())
    actions["images_to_copy"] = all_required_anki_images - obs_assets
    actions["images_to_delete"] = obs_assets - all_required_anki_images
    print(f"Images to copy: {len(actions['images_to_copy'])}")
    print(f"Images to delete: {len(actions['images_to_delete'])}")

    # --- MOC Diff ---
    # Identify which MOCs *should* exist based on Anki state
    expected_mocs = {ROOT_MOC_FILENAME} # Root MOC always expected (will be updated if changes)
    for deck_path, deck_data in anki_state.items():
        if deck_path == "_root_": continue
        # Only expect a deck MOC if the deck directly contains notes
        if deck_path in decks_with_notes:
            moc_filename = deck_data.get("moc_filename")
            if moc_filename:
                expected_mocs.add(os.path.join(deck_path, moc_filename).replace('\\', '/'))

    # Compare with MOCs found in Obsidian
    obs_mocs = obsidian_state.get("moc_files", set())
    actions["mocs_to_create"] = expected_mocs - obs_mocs
    actions["mocs_to_delete"] = obs_mocs - expected_mocs
    # All expected MOCs that also exist in Obsidian might need an update
    actions["mocs_to_update"] = expected_mocs.intersection(obs_mocs)

    # Always update root MOC if there were *any* changes to notes/folders/images
    # This is simpler than tracking exact hierarchy changes.
    if any(act for k, act_list in actions.items() if k != "mocs_to_update" for act in act_list):
         actions["mocs_to_update"].add(ROOT_MOC_FILENAME)
         # Ensure root isn't also marked for creation if it exists
         if ROOT_MOC_FILENAME in actions["mocs_to_create"]:
             actions["mocs_to_create"].discard(ROOT_MOC_FILENAME)


    print(f"MOCs to create: {len(actions['mocs_to_create'])}")
    print(f"MOCs to update: {len(actions['mocs_to_update'])}")
    print(f"MOCs to delete: {len(actions['mocs_to_delete'])}")

    print("Difference calculation complete.")
    return actions