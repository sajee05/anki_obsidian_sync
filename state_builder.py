# -*- coding: utf-8 -*-

"""
Builds representations of the Anki collection state (note-centric) and
Obsidian filesystem state for the differential sync process.
Uses custom MOC naming convention. Includes enhanced logging for filename generation.
Re-adds Note ID to filenames for uniqueness.
"""

import os
import re
import hashlib
import html # Import html for unescaping entities
from typing import Dict, List, Any, Set, Optional
from pathlib import Path

# Anki imports
from anki.collection import Collection
from anki.notes import Note
from anki.cards import Card
from aqt import mw # For media path and utils
from aqt.utils import showCritical # For error messages

# --- Dependency Check ---
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    yaml = None
    YAML_AVAILABLE = False
# --- End Dependency Check ---

# --- Constants ---
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]|(?<!^)\.$|\s$'
REPLACEMENT_CHAR = "_"
MAX_FILENAME_LENGTH = 100 # Limit filename length for sanity
ROOT_MOC_FILENAME = "_Anki_Collection_Index.md" # Define root MOC name

# --- Helper Functions ---

def sanitize_filename(name: str) -> str:
    """Removes or replaces characters invalid in filenames/paths and truncates."""
    if not name:
        name = "Untitled Anki Note"
    sanitized = re.sub(INVALID_FILENAME_CHARS, REPLACEMENT_CHAR, name)
    sanitized = re.sub(f'{REPLACEMENT_CHAR}+', REPLACEMENT_CHAR, sanitized)
    sanitized = sanitized.strip(REPLACEMENT_CHAR)
    if len(sanitized) > MAX_FILENAME_LENGTH:
        sanitized = sanitized[:MAX_FILENAME_LENGTH].strip().rstrip(REPLACEMENT_CHAR)
    final_name = sanitized or "anki_note"
    return final_name

def get_note_media(note: Note) -> Set[str]:
    """Extracts all media filenames (images, audio, video, GIFs) referenced in a note's fields."""
    media = set()
    
    # Regular expressions for different media types
    img_regex = re.compile(r'<img.*?src=["\'](.*?)["\']', re.IGNORECASE)
    audio_regex = re.compile(r'\[sound:([^\]]+)\]', re.IGNORECASE)
    video_regex = re.compile(r'<video.*?src=["\'](.*?)["\']', re.IGNORECASE | re.DOTALL)
    # Also check for webp and other image formats in various contexts
    paste_img_regex = re.compile(r'(paste-[a-f0-9]+\.(?:jpg|jpeg|png|gif|webp|svg))', re.IGNORECASE)
    general_media_regex = re.compile(r'src=["\'](.*?\.(?:jpg|jpeg|png|gif|webp|svg|mp3|mp4|wav|ogg|webm))["\']', re.IGNORECASE)
    
    for field_name, field_value in note.items():
        if field_value:
            # Extract images
            for match in img_regex.finditer(field_value):
                src = match.group(1)
                if src and not src.startswith(('http:', 'https:', 'data:')):
                    media.add(src)
            
            # Extract audio files
            for match in audio_regex.finditer(field_value):
                media.add(match.group(1))
            
            # Extract video files
            for match in video_regex.finditer(field_value):
                src = match.group(1)
                if src and not src.startswith(('http:', 'https:', 'data:')):
                    media.add(src)
            
            # Extract paste images
            for match in paste_img_regex.finditer(field_value):
                media.add(match.group(1))
            
            # Extract general media files
            for match in general_media_regex.finditer(field_value):
                src = match.group(1)
                if src and not src.startswith(('http:', 'https:', 'data:')):
                    media.add(src)
    
    return media

# Backwards compatibility alias
get_note_images = get_note_media

# --- Anki State Building (Note-Centric) ---

def determine_note_filename(note: Note, note_type: Dict) -> str:
    """Determines the base filename from note content, cleans it, adds NoteID and .md."""
    filename_base = ""
    note_type_name = note_type.get('name', '')
    source_field_name = "Unknown"

    # --- Extract base text based on note type ---
    if "Cloze" in note_type_name:
        title_field = next((f['name'] for f in note_type['flds'] if f['name'].lower() == 'title'), None)
        if title_field and note[title_field].strip():
            filename_base = note[title_field]; source_field_name = title_field
        else:
            text_field = next((f['name'] for f in note_type['flds'] if f['name'].lower() in ('text', 'content')), None)
            if text_field:
                filename_base = re.sub(r"\{\{c\d+::(.*?)(?:::.*?)?\}\}", r"\1", note[text_field]); source_field_name = text_field
    elif "Basic" in note_type_name:
        front_field = next((f['name'] for f in note_type['flds'] if f['name'].lower() == 'front'), None)
        if front_field:
            filename_base = note[front_field]; source_field_name = front_field
    else: # Fallback
        for f in note_type['flds']:
            field_name = f['name']
            if note[field_name].strip(): filename_base = note[field_name]; source_field_name = field_name; break

    # print(f"  DEBUG (Filename): Note {note.id}, Source Field ('{source_field_name}'): '{filename_base[:100]}...'") # DEBUG

    # --- Clean the extracted text ---
    cleaned_text = re.sub('<[^>]+>', ' ', filename_base).strip() # Strip HTML tags
    cleaned_text = html.unescape(cleaned_text) # Decode HTML entities
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip() # Consolidate whitespace
    # print(f"  DEBUG (Filename): Note {note.id}, Cleaned Text: '{cleaned_text[:100]}...'") # DEBUG

    # --- Sanitize for filename ---
    sanitized_base = sanitize_filename(cleaned_text)

    # --- Add Note ID for uniqueness and extension ---
    final_filename = f"{sanitized_base}_{note.id}.md"
    print(f"  DEBUG (Filename): Note {note.id}, Final Filename: '{final_filename}'") # DEBUG

    return final_filename


def build_anki_state(col: Collection) -> Dict[str, Any]:
    """Builds a note-centric dictionary representing the desired state."""
    print("Building Anki state representation (Note-Centric)...")
    anki_state = {"_root_": {"anki_deck_id": None, "anki_deck_name": "Anki Collection", "notes": {}, "subdeck_paths": set(), "moc_filename": ROOT_MOC_FILENAME}}
    deck_map = {}
    all_decks = col.decks.all_names_and_ids()
    deck_parents = {}

    # Pre-process decks
    print("DEBUG: Mapping decks...") # DEBUG
    for deck in all_decks:
        parts = deck.name.split("::"); current_path_parts = []; parent_id = None
        for i, part_name in enumerate(parts):
            sanitized_part_name = sanitize_filename(part_name); current_path_parts.append(sanitized_part_name)
            sanitized_path = "/".join(current_path_parts); current_deck_id = None
            partial_name = "::".join(parts[:i+1])
            for d in all_decks:
                if d.name == partial_name: current_deck_id = d.id; break
            if current_deck_id is not None:
                deck_map[current_deck_id] = sanitized_path
                if parent_id is not None: deck_parents[current_deck_id] = parent_id
                if sanitized_path not in anki_state:
                     deck_moc_filename = f"_{sanitized_part_name}_index.md"
                     anki_state[sanitized_path] = {
                        "anki_deck_id": current_deck_id, "anki_deck_name": part_name,
                        "sanitized_deck_name": sanitized_part_name, "notes": {},
                        "subdeck_paths": set(), "moc_filename": deck_moc_filename}
                if parent_id is None: anki_state["_root_"]["subdeck_paths"].add(sanitized_path)
                else:
                    parent_path = deck_map.get(parent_id)
                    if parent_path and parent_path in anki_state: anki_state[parent_path]["subdeck_paths"].add(sanitized_path)
                parent_id = current_deck_id
            else: print(f"Warning: Could not find Deck ID for partial name: '{partial_name}'") # DEBUG
    print(f"DEBUG: Deck mapping complete. {len(deck_map)} decks mapped.") # DEBUG

    # Process notes
    note_ids = col.find_notes("")
    notes_processed = 0; notes_added = 0; notes_skipped = 0 # Combined skipped count
    total_notes = len(note_ids); mw.progress.start(label="Building Anki State (Notes)...", max=total_notes, immediate=True)
    processed_note_ids = set()

    print("DEBUG: Processing notes for state building...") # DEBUG
    for nid in note_ids:
        if nid in processed_note_ids: continue
        try:
            note = col.get_note(nid); note_type = note.note_type()
            if not note_type: print(f"DEBUG: Skipping note {nid} - No note type found."); notes_skipped += 1; processed_note_ids.add(nid); continue
            card_ids = note.card_ids()
            if not card_ids: print(f"DEBUG: Skipping note {nid} - No cards found."); notes_skipped += 1; processed_note_ids.add(nid); continue
            first_card = col.get_card(card_ids[0]); deck_id = first_card.did
            deck_path = deck_map.get(deck_id)

            if deck_path and deck_path in anki_state:
                target_filename = determine_note_filename(note, note_type)
                if not target_filename or target_filename == ".md":
                    print(f"Warning: Skipping note {nid} due to invalid generated filename: '{target_filename}'") # DEBUG
                    notes_skipped += 1; processed_note_ids.add(nid); continue

                media_files = get_note_media(note)
                relevant_fields = {f['name']: note[f['name']] for f in note_type['flds']}
                anki_state[deck_path]["notes"][nid] = {
                    "note_id": nid, "card_id": card_ids[0], "note_mod_time": note.mod,
                    "note_type_name": note_type['name'], "relevant_fields": relevant_fields,
                    "target_filename": target_filename, "required_images": media_files,  # Now includes all media
                    "card_ids": card_ids}
                processed_note_ids.add(nid); notes_added += 1
            else:
                original_deck_name = col.decks.name(deck_id)
                print(f"DEBUG: Skipping note {nid} - Deck path not found or invalid. Deck ID: {deck_id}, Name: '{original_deck_name}', Mapped Path Attempt: '{deck_path}'") # DEBUG
                notes_skipped += 1; processed_note_ids.add(nid)
        except Exception as e: print(f"Error processing note {nid}: {e}"); notes_skipped += 1; processed_note_ids.add(nid) # Count errors as skipped too
        notes_processed += 1
        if notes_processed % 50 == 0: mw.progress.update(label=f"Building Anki State: {notes_processed}/{total_notes} notes", value=notes_processed)

    mw.progress.finish()
    print(f"Anki state built. Found {len(anki_state) - 1} decks/subdecks. Processed {notes_processed} notes. Added {notes_added} notes to state. Skipped {notes_skipped} notes due to errors, deck mapping or filename issues.") # Updated summary log
    return anki_state

# --- Obsidian State Building ---
# (No changes needed here)
def parse_yaml_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    if not content.startswith('---') or not YAML_AVAILABLE: return None
    end_marker = content.find('---', 3);
    if end_marker == -1: return None
    yaml_content = content[3:end_marker].strip()
    try: return yaml.safe_load(yaml_content)
    except yaml.YAMLError as e: print(f"Warning: Could not parse YAML frontmatter: {e}"); return None

def build_obsidian_state(target_dir_str: str) -> Dict[str, Any]:
    if not YAML_AVAILABLE: return {"base_path": Path(target_dir_str).resolve(), "folders": set(), "note_files": {}, "moc_files": set(), "asset_files": set(), "assets_folder_rel": "assets"}
    print(f"Scanning Obsidian directory: {target_dir_str}")
    target_dir = Path(target_dir_str).resolve()
    obsidian_state = {"base_path": target_dir, "folders": set(), "note_files": {}, "moc_files": set(), "asset_files": set(), "assets_folder_rel": "assets"}
    assets_folder_abs = target_dir / obsidian_state["assets_folder_rel"]
    if not target_dir.is_dir(): print(f"Warning: Obsidian target directory does not exist: {target_dir}"); return obsidian_state
    mw.progress.start(label="Scanning Obsidian Folder...", immediate=True); items_scanned = 0
    for root, dirs, files in os.walk(target_dir):
        root_path = Path(root); rel_root_path_str = str(root_path.relative_to(target_dir)).replace('\\', '/');
        if rel_root_path_str == ".": rel_root_path_str = ""
        dirs[:] = [d for d in dirs if d not in ('.obsidian', '.git')]
        for dir_name in dirs:
            if root_path == target_dir and dir_name == obsidian_state["assets_folder_rel"]: continue
            rel_dir_path = os.path.join(rel_root_path_str, dir_name).replace('\\', '/'); obsidian_state["folders"].add(rel_dir_path); items_scanned += 1
        for filename in files:
            items_scanned += 1; abs_file_path = root_path / filename; rel_file_path_str = os.path.join(rel_root_path_str, filename).replace('\\', '/')
            if root_path == assets_folder_abs: obsidian_state["asset_files"].add(filename); continue
            if filename == ROOT_MOC_FILENAME or (filename.startswith("_") and filename.endswith("_index.md")): obsidian_state["moc_files"].add(rel_file_path_str); continue
            if filename.endswith(".md"):
                note_data = {"abs_path": abs_file_path, "anki_note_id": None, "anki_note_mod": None, "content_hash": None}
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: content = f.read()
                    frontmatter = parse_yaml_frontmatter(content)
                    if frontmatter and "anki_note_id" in frontmatter:
                        note_data["anki_note_id"] = frontmatter.get("anki_note_id"); note_data["anki_note_mod"] = frontmatter.get("anki_note_mod"); note_data["content_hash"] = frontmatter.get("content_hash")
                        if not isinstance(note_data["anki_note_id"], (int, type(None))): note_data["anki_note_id"] = None
                        if not isinstance(note_data["anki_note_mod"], (int, type(None))): note_data["anki_note_mod"] = None
                        if not isinstance(note_data["content_hash"], (str, type(None))): note_data["content_hash"] = None
                        if note_data["anki_note_id"] is not None: obsidian_state["note_files"][rel_file_path_str] = note_data
                except Exception as e: print(f"Warning: Could not read or parse frontmatter for {rel_file_path_str}: {e}")
        if items_scanned % 100 == 0: mw.progress.update(label=f"Scanning Obsidian Folder: {items_scanned} items")
    mw.progress.finish()
    print(f"Obsidian scan complete. Found {len(obsidian_state['folders'])} folders, {len(obsidian_state['note_files'])} potential note files, {len(obsidian_state['moc_files'])} MOC files, {len(obsidian_state['asset_files'])} assets.")
    return obsidian_state