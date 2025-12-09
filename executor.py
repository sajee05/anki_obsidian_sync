# -*- coding: utf-8 -*-

"""
Executes the filesystem actions (Create, Update, Delete) determined by the diff calculator.
Handles the actual writing, deleting, and moving of files and folders (Note-Centric).
Uses custom MOC naming convention and generates hierarchical root MOC linking to deck MOCs (which only list notes).
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Set, Optional
import html
import re
import sys # <-- Added import for maxint fallback

# Anki imports
from aqt import mw

# Local imports
from .html_converter import combine_fields_to_markdown, convert_html_to_markdown, CLOZE_REGEX
from .state_builder import sanitize_filename, YAML_AVAILABLE, yaml, ROOT_MOC_FILENAME

# --- Helper ---

def ensure_dir_exists(dir_path: Path):
    """Creates a directory if it doesn't exist."""
    dir_path.mkdir(parents=True, exist_ok=True)

# --- Phase 3: Deletions & Folder Structure ---
# (No changes needed here)
def execute_deletions_and_folders(actions: Dict[str, Any], obsidian_base_path: Path, assets_rel_path: str):
    print("Executing Phase 3: Deletions and Folder Creation (Note-Centric)...")
    assets_abs_path = obsidian_base_path / assets_rel_path
    # 1. Create Folders
    folders_created = 0; folders_to_create = actions.get("folders_to_create", [])
    if folders_to_create:
        mw.progress.start(label="Creating Folders...", max=len(folders_to_create), immediate=True)
        for rel_path in folders_to_create:
            try: abs_path = obsidian_base_path / rel_path; ensure_dir_exists(abs_path); folders_created += 1
            except Exception as e: print(f"Error creating folder {rel_path}: {e}")
            mw.progress.update(label=f"Creating folder: {rel_path}", value=folders_created)
        mw.progress.finish(); print(f"Created {folders_created} folders.")
    ensure_dir_exists(assets_abs_path)
    # 2. Delete Obsolete Note Files
    notes_deleted = 0; notes_to_delete = actions.get("notes_to_delete", [])
    if notes_to_delete:
        mw.progress.start(label="Deleting Obsolete Notes...", max=len(notes_to_delete), immediate=True)
        for note_action in notes_to_delete:
            rel_path = note_action["target_rel_path"]; abs_path = obsidian_base_path / rel_path
            try:
                if abs_path.is_file(): abs_path.unlink(); notes_deleted += 1
                else: print(f"Warning: Note file to delete not found: {abs_path}")
                mw.progress.update(label=f"Deleting note: {rel_path}", value=notes_deleted)
            except Exception as e: print(f"Error deleting note file {rel_path}: {e}")
        mw.progress.finish(); print(f"Deleted {notes_deleted} obsolete note files.")
    # 3. Delete Obsolete Images
    images_deleted = 0; images_to_delete = actions.get("images_to_delete", set())
    if images_to_delete:
        mw.progress.start(label="Deleting Obsolete Assets...", max=len(images_to_delete), immediate=True)
        for img_filename in images_to_delete:
            abs_path = assets_abs_path / img_filename
            try:
                if abs_path.is_file(): abs_path.unlink(); images_deleted += 1
                else: print(f"Warning: Asset file to delete not found: {abs_path}")
                mw.progress.update(label=f"Deleting asset: {img_filename}", value=images_deleted)
            except Exception as e: print(f"Error deleting asset file {img_filename}: {e}")
        mw.progress.finish(); print(f"Deleted {images_deleted} obsolete asset files.")
    # 4. Delete Obsolete MOC Files
    mocs_deleted = 0; mocs_to_delete = actions.get("mocs_to_delete", set())
    if mocs_to_delete:
        mw.progress.start(label="Deleting Obsolete MOCs...", max=len(mocs_to_delete), immediate=True)
        for moc_rel_path in mocs_to_delete:
            abs_path = obsidian_base_path / moc_rel_path
            try:
                if abs_path.is_file(): abs_path.unlink(); mocs_deleted += 1
                else: print(f"Warning: MOC file to delete not found: {abs_path}")
                mw.progress.update(label=f"Deleting MOC: {moc_rel_path}", value=mocs_deleted)
            except Exception as e: print(f"Error deleting MOC file {moc_rel_path}: {e}")
        mw.progress.finish(); print(f"Deleted {mocs_deleted} obsolete MOC files.")

    # 5. Delete Obsolete Folders (Deferred)
    print("Folder deletion logic is currently deferred.")
    print("Phase 3 execution complete.")

# --- Phase 4: Content Conversion & File Writing (Note-Centric) ---
# (No changes needed here)
def copy_required_media(
    required_media: Set[str], media_to_copy_set: Set[str],
    anki_media_path: str, obsidian_assets_path: Path ):
    """Copies all required media files (images, audio, video, etc.) to Obsidian assets folder."""
    if not required_media: return
    ensure_dir_exists(obsidian_assets_path)
    for media_filename in required_media:
        if media_filename not in media_to_copy_set: continue
        source_path = Path(anki_media_path) / media_filename
        dest_path = obsidian_assets_path / media_filename
        if source_path.is_file():
            if not dest_path.exists():
                try: 
                    shutil.copy2(source_path, dest_path)
                    print(f"Copied media file: {media_filename}")
                except Exception as e: 
                    print(f"Error copying media {media_filename}: {e}")
            media_to_copy_set.discard(media_filename)
        else: 
            print(f"Warning: Source media not found in Anki media: {source_path}")
            media_to_copy_set.discard(media_filename)

# Backwards compatibility alias
copy_required_images = copy_required_media

def calculate_content_hash(content: str) -> str: return hashlib.md5(content.encode('utf-8')).hexdigest()

def execute_note_writes(
    actions: Dict[str, Any], obsidian_base_path: Path, assets_rel_path: str ):
    print("Executing Phase 4: Note File Writing...")
    notes_to_create = actions.get("notes_to_create", []); notes_to_update = actions.get("notes_to_update", [])
    notes_to_process = notes_to_create + notes_to_update
    if not notes_to_process: print("No notes to create or update."); return
    anki_media_path = mw.col.media.dir(); obsidian_assets_abs_path = obsidian_base_path / assets_rel_path
    images_to_copy_set = actions.get("images_to_copy", set()).copy(); notes_written = 0
    total_notes = len(notes_to_process); mw.progress.start(label="Writing Note Files...", max=total_notes, immediate=True)
    for i, note_action in enumerate(notes_to_process):
        anki_note_data = note_action["anki_note_data"]; target_rel_path = note_action["target_rel_path"]
        target_abs_path = obsidian_base_path / target_rel_path; note_id = anki_note_data["note_id"]
        note_type_name = anki_note_data["note_type_name"]; fields = anki_note_data["relevant_fields"]
        required_images = anki_note_data.get("required_images", set()); card_ids = anki_note_data.get("card_ids", [])
        old_abs_path = None
        if "obs_note_data" in note_action and note_action.get("needs_move", False):
            old_rel_path = note_action["obs_note_data"]["obs_rel_path"]; old_abs_path = obsidian_base_path / old_rel_path
            print(f"DEBUG: Note {note_id} needs move from {old_rel_path} to {target_rel_path}")
        copy_required_media(required_images, images_to_copy_set, anki_media_path, obsidian_assets_abs_path)
        markdown_body = combine_fields_to_markdown(fields, note_type_name, note_id)
        content_hash = calculate_content_hash(markdown_body)
        frontmatter_dict = {"anki_note_id": note_id, "anki_note_mod": anki_note_data["note_mod_time"], "content_hash": content_hash}
        try:
            if not YAML_AVAILABLE: frontmatter_yaml = f"# YAML Frontmatter requires PyYAML library (missing)\n# anki_note_id: {note_id}\n"
            else: frontmatter_yaml = yaml.dump(frontmatter_dict, sort_keys=False, allow_unicode=True, default_flow_style=False)
        except Exception as e: print(f"Error dumping YAML for {target_rel_path}: {e}"); frontmatter_yaml = f"# Error generating YAML: {e}\n"
        final_content = f"---\n{frontmatter_yaml}---\n\n{markdown_body}"
        try:
            if old_abs_path and old_abs_path.is_file(): print(f"DEBUG: Deleting old file for move: {old_abs_path}"); old_abs_path.unlink()
            ensure_dir_exists(target_abs_path.parent)
            print(f"DEBUG: Attempting to write note to: {target_abs_path}") # <-- Added log
            with open(target_abs_path, 'w', encoding='utf-8') as f: f.write(final_content)
            print(f"DEBUG: Successfully wrote note to: {target_abs_path}") # <-- Added log
            notes_written += 1; mw.progress.update(label=f"Writing note: {target_rel_path}", value=i + 1)
        except Exception as e:
            print(f"ERROR: Failed to write note file {target_rel_path} to {target_abs_path}. Exception: {e}") # <-- Enhanced error log
            mw.progress.update(label=f"Error writing: {target_rel_path}", value=i + 1)
    mw.progress.finish(); print(f"Phase 4 complete. Wrote/Updated {notes_written} note files.")

# --- Phase 5: Linking & MOC Generation (Hierarchical Root MOC) ---

def extract_note_id_from_filename(filename: str) -> Optional[int]:
    match = re.match(r".*_(\d+)\.md$", filename); return int(match.group(1)) if match else None

def clean_moc_link_text(text: str) -> str:
    if not text: return "Untitled Note"
    text = re.sub('<br\s*/?>', ' ', text); text = re.sub('<[^>]+>', '', text)
    text = text.replace("==", "").replace("**", ""); text = re.sub(r'!\[.*?\]\(.*?\)', '', text)
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text); text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip(); max_len = 80
    if len(text) > max_len: text = text[:max_len] + "..."
    return text or "Untitled Note"

def get_note_display_text(note_id: int, anki_state: Dict[str, Any]) -> str:
    for deck_path, deck_data in anki_state.items():
        if deck_path == "_root_": continue
        if note_id in deck_data.get("notes", {}):
            note_data = deck_data["notes"][note_id]; note_type = note_data.get("note_type_name", "")
            fields = note_data.get("relevant_fields", {}); display_text = ""
            if "Cloze" in note_type: display_text = fields.get("Title", "") or fields.get("Text") or fields.get("Content", "")
            elif "Basic" in note_type: display_text = fields.get("Front", "")
            else: first_field_name = next(iter(fields)) if fields else None; display_text = fields.get(first_field_name, f"Note_{note_id}")
            return clean_moc_link_text(display_text)
    return f"Note_{note_id}"

# Helper function for numerical sorting of MOC links
def get_moc_sort_key(note_tuple):
    display_text = note_tuple[0]
    match = re.match(r'^(\d+)\.', display_text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            # Handle potential conversion errors if needed, though regex should ensure digits
            return sys.maxsize # Sort non-numeric prefixes last
    else:
        # Fallback for notes without a leading number prefix
        return sys.maxsize # Sort non-numeric prefixes last

def _generate_root_moc_recursive(deck_path: str, anki_state: Dict[str, Any], current_level: int) -> List[str]:
    """Recursive helper for the root MOC's hierarchical structure."""
    lines = []
    deck_data = anki_state.get(deck_path)
    if not deck_data: return lines

    deck_name_part = deck_data.get("anki_deck_name", deck_path.split('/')[-1])
    heading_level = min(current_level + 1, 6) # Start at H2 for top-level
    heading_prefix = "#" * heading_level
    lines.append(f"{heading_prefix} {deck_name_part}") # Just the heading text

    # Add link to the deck's specific MOC *if* it has notes
    deck_has_notes = bool(deck_data.get("notes"))
    if deck_has_notes:
        deck_moc_filename = deck_data.get("moc_filename", "_unknown_index.md")
        moc_link = Path(deck_path).joinpath(deck_moc_filename).as_posix()
        # Add the link on the line below the heading
        lines.append(f"- [[{moc_link}|{deck_name_part} MOC]]") # Link to the deck MOC

    # Recursively add subdecks
    subdeck_paths = sorted(list(deck_data.get("subdeck_paths", set())))
    for sub_path in subdeck_paths:
        lines.extend(_generate_root_moc_recursive(sub_path, anki_state, current_level + 1))

    return lines

def generate_moc_content(
    moc_rel_path_str: str,
    anki_state: Dict[str, Any],
    obsidian_base_path: Path # Unused but kept for signature consistency
    ) -> str:
    content = []
    moc_rel_path = Path(moc_rel_path_str)
    is_root_moc = (moc_rel_path.name == ROOT_MOC_FILENAME)

    if is_root_moc:
        # --- Root MOC (Hierarchical Headings + Links to Deck MOCs) ---
        content.append(f"# {anki_state['_root_']['anki_deck_name']}")
        content.append("")
        top_level_deck_paths = sorted(list(anki_state["_root_"].get("subdeck_paths", set())))
        if not top_level_deck_paths: content.append("- (No decks found)")
        else:
            for deck_path in top_level_deck_paths:
                # Start recursion at level 1 (results in H2)
                content.extend(_generate_root_moc_recursive(deck_path, anki_state, 1))
                content.append("") # Add space between top-level deck sections
    else:
        # --- Deck/Subdeck MOC (Only Notes) ---
        deck_rel_path_str = moc_rel_path.parent.as_posix()
        if deck_rel_path_str == ".": deck_rel_path_str = ""

        deck_data = anki_state.get(deck_rel_path_str)
        if deck_data:
            deck_name = deck_data.get("anki_deck_name", deck_rel_path_str.split('/')[-1])
            # No main heading needed if it only lists notes? Or keep it? Let's keep it.
            content.append(f"# Notes in Deck: {deck_name}")
            content.append("\n## Notes\n")
            note_links = []
            notes_in_deck = deck_data.get("notes", {})
            for note_id, note_data in notes_in_deck.items():
                display_text = get_note_display_text(note_id, anki_state)
                note_filename = note_data.get("target_filename", f"UnknownNote_{note_id}.md")
                note_rel_link = Path(deck_rel_path_str).joinpath(note_filename).as_posix()
                note_links.append((display_text, f"- [[{note_rel_link}|{display_text}]]"))
            # Sort using the custom numerical key function
            note_links.sort(key=get_moc_sort_key)
            if not note_links: content.append("- (No notes directly in this deck)")
            else: content.extend([link for _, link in note_links])
        else:
            content.append(f"# Orphaned MOC: {moc_rel_path_str}")
            content.append("\nThis MOC file seems to correspond to a deck that no longer exists in Anki.")

    return "\n".join(content)

def execute_moc_generation(
    actions: Dict[str, Any],
    anki_state: Dict[str, Any],
    obsidian_base_path: Path
    ):
    """Handles creating/updating/deleting MOC files based on new rules."""
    print("Executing Phase 5: MOC Generation (Hierarchical Root)...")
    mocs_to_create = actions.get("mocs_to_create", set())
    mocs_to_update = actions.get("mocs_to_update", set())
    mocs_to_process = mocs_to_create.union(mocs_to_update) # Files to write/overwrite

    if not mocs_to_process: print("No MOC files need updating or creation."); return

    mocs_written = 0; total_mocs = len(mocs_to_process)
    mw.progress.start(label="Generating MOC Files...", max=total_mocs, immediate=True)

    for i, moc_rel_path in enumerate(mocs_to_process):
        target_abs_path = obsidian_base_path / moc_rel_path
        mw.progress.update(label=f"Generating MOC: {moc_rel_path}", value=i)
        try:
            moc_content = generate_moc_content(moc_rel_path, anki_state, obsidian_base_path)
            ensure_dir_exists(target_abs_path.parent)
            with open(target_abs_path, 'w', encoding='utf-8') as f: f.write(moc_content)
            mocs_written += 1
        except Exception as e:
            print(f"Error generating or writing MOC file {moc_rel_path}: {e}")
            mw.progress.update(label=f"Error MOC: {moc_rel_path}", value=i + 1)

    mw.progress.finish()
    print(f"Phase 5 complete. Wrote/Updated {mocs_written} MOC files.")