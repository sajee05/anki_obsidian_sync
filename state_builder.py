# -*- coding: utf-8 -*-

"""
Builds representations of the Anki collection state and Obsidian filesystem state.
Excludes user-selected decks and intelligently names files based on complex Note Types.
"""

import os
import re
import hashlib
import html
from typing import Dict, List, Any, Set, Optional
from pathlib import Path

from anki.collection import Collection
from anki.notes import Note
from aqt import mw

# Dependency Check
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    yaml = None
    YAML_AVAILABLE = False

from .config import get_excluded_decks

# Constants
INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1f]|(?<!^)\.$|\s$'
REPLACEMENT_CHAR = "_"
MAX_FILENAME_LENGTH = 100
ROOT_MOC_FILENAME = "_Anki_Collection_Index.md"

def sanitize_filename(name: str) -> str:
    if not name:
        name = "Untitled Anki Note"
    sanitized = re.sub(INVALID_FILENAME_CHARS, REPLACEMENT_CHAR, name)
    sanitized = re.sub(f'{REPLACEMENT_CHAR}+', REPLACEMENT_CHAR, sanitized)
    sanitized = sanitized.strip(REPLACEMENT_CHAR)
    if len(sanitized) > MAX_FILENAME_LENGTH:
        sanitized = sanitized[:MAX_FILENAME_LENGTH].strip().rstrip(REPLACEMENT_CHAR)
    return sanitized or "anki_note"

def get_note_media(note: Note) -> Set[str]:
<<<<<<< HEAD
    media = set()
    img_regex = re.compile(r'<img.*?src=["\'](.*?)["\']', re.IGNORECASE)
    audio_regex = re.compile(r'\[sound:([^\]]+)\]', re.IGNORECASE)
    video_regex = re.compile(r'<video.*?src=["\'](.*?)["\']', re.IGNORECASE | re.DOTALL)
    paste_img_regex = re.compile(r'(paste-[a-f0-9]+\.(?:jpg|jpeg|png|gif|webp|svg))', re.IGNORECASE)
    general_media_regex = re.compile(r'src=["\'](.*?\.(?:jpg|jpeg|png|gif|webp|svg|mp3|mp4|wav|ogg|webm))["\']', re.IGNORECASE)
    
    for field_value in note.values():
=======
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
>>>>>>> 8413eca9f1e93d7cf1c5475af7081e74e9f08b3c
        if field_value:
            # Extract images
            for match in img_regex.finditer(field_value):
                src = match.group(1)
<<<<<<< HEAD
                if src and not src.startswith(('http:', 'https:', 'data:')): media.add(src)
            for match in audio_regex.finditer(field_value):
                media.add(match.group(1))
            for match in video_regex.finditer(field_value):
                src = match.group(1)
                if src and not src.startswith(('http:', 'https:', 'data:')): media.add(src)
            for match in paste_img_regex.finditer(field_value):
                media.add(match.group(1))
            for match in general_media_regex.finditer(field_value):
                src = match.group(1)
                if src and not src.startswith(('http:', 'https:', 'data:')): media.add(src)
    return media
=======
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
>>>>>>> 8413eca9f1e93d7cf1c5475af7081e74e9f08b3c

def determine_note_filename(note: Note, note_type: Dict) -> str:
    filename_base = ""
    note_type_name = note_type.get('name', '').lower()

    if "cloze" in note_type_name:
        title_field = next((f['name'] for f in note_type['flds'] if f['name'].lower() == 'title'), None)
        if title_field and note[title_field].strip():
            filename_base = note[title_field]
        else:
            text_field = next((f['name'] for f in note_type['flds'] if f['name'].lower() in ('text', 'content')), None)
            if text_field:
                filename_base = re.sub(r"\{\{c\d+::(.*?)(?:::.*?)?\}\}", r"\1", note[text_field])
                
    elif "image occlusion" in note_type_name:
        header_field = next((f['name'] for f in note_type['flds'] if f['name'].lower() == 'header'), None)
        if header_field and note[header_field].strip():
            filename_base = note[header_field]
            
    elif "forum toolkit" in note_type_name or "mcq" in note_type_name:
        q_field = next((f['name'] for f in note_type['flds'] if f['name'].lower() == 'question'), None)
        if q_field and note[q_field].strip():
            filename_base = note[q_field]
            
    elif "current affairs" in note_type_name:
        front_field = next((f['name'] for f in note_type['flds'] if f['name'].lower() == 'front'), None)
        if front_field and note[front_field].strip():
            filename_base = note[front_field]
            
    elif "basic" in note_type_name:
        front_field = next((f['name'] for f in note_type['flds'] if f['name'].lower() == 'front'), None)
        if front_field:
            filename_base = note[front_field]

    # Fallback to the first non-empty field
    if not filename_base:
        for f in note_type['flds']:
            if note[f['name']].strip():
                filename_base = note[f['name']]
                break

    cleaned_text = re.sub('<[^>]+>', ' ', filename_base).strip()
    cleaned_text = html.unescape(cleaned_text)
    
    # Cap to avoid massively long generated names from question blocks
    if len(cleaned_text) > 70:
        cleaned_text = cleaned_text[:70] + "..."
        
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    sanitized_base = sanitize_filename(cleaned_text)
    return f"{sanitized_base}_{note.id}.md"

def build_anki_state(col: Collection) -> Dict[str, Any]:
    anki_state = {"_root_": {"anki_deck_id": None, "anki_deck_name": "Anki Collection", "notes": {}, "subdeck_paths": set(), "moc_filename": ROOT_MOC_FILENAME}}
    deck_map = {}
    deck_parents = {}
    
    excluded_decks = get_excluded_decks()
    all_decks = col.decks.all_names_and_ids()

    def is_excluded(deck_name: str) -> bool:
        for ex in excluded_decks:
            if deck_name == ex or deck_name.startswith(ex + "::"):
                return True
        return False

    for deck in all_decks:
        if is_excluded(deck.name):
            continue
            
        parts = deck.name.split("::")
        current_path_parts = []
        parent_id = None
        
        for i, part_name in enumerate(parts):
            sanitized_part_name = sanitize_filename(part_name)
            current_path_parts.append(sanitized_part_name)
            sanitized_path = "/".join(current_path_parts)
            
            partial_name = "::".join(parts[:i+1])
            current_deck_id = next((d.id for d in all_decks if d.name == partial_name), None)
            
            if current_deck_id is not None:
                deck_map[current_deck_id] = sanitized_path
                if parent_id is not None: 
                    deck_parents[current_deck_id] = parent_id
                if sanitized_path not in anki_state:
                     anki_state[sanitized_path] = {
                        "anki_deck_id": current_deck_id, "anki_deck_name": part_name,
                        "sanitized_deck_name": sanitized_part_name, "notes": {},
                        "subdeck_paths": set(), "moc_filename": f"_{sanitized_part_name}_index.md"}
                if parent_id is None: 
                    anki_state["_root_"]["subdeck_paths"].add(sanitized_path)
                else:
                    parent_path = deck_map.get(parent_id)
                    if parent_path and parent_path in anki_state: 
                        anki_state[parent_path]["subdeck_paths"].add(sanitized_path)
                parent_id = current_deck_id

    note_ids = col.find_notes("")
    processed_note_ids = set()
    total_notes = len(note_ids)
    
    mw.progress.start(label="Building Anki State...", max=total_notes, immediate=True)

    for i, nid in enumerate(note_ids):
        if nid in processed_note_ids: continue
        try:
            note = col.get_note(nid)
            note_type = note.note_type()
            if not note_type: continue
            card_ids = note.card_ids()
            if not card_ids: continue
            
            deck_id = col.get_card(card_ids[0]).did
            deck_path = deck_map.get(deck_id)

            # Only process if deck hasn't been excluded
            if deck_path and deck_path in anki_state:
                target_filename = determine_note_filename(note, note_type)
<<<<<<< HEAD
=======
                if not target_filename or target_filename == ".md":
                    print(f"Warning: Skipping note {nid} due to invalid generated filename: '{target_filename}'") # DEBUG
                    notes_skipped += 1; processed_note_ids.add(nid); continue

                media_files = get_note_media(note)
>>>>>>> 8413eca9f1e93d7cf1c5475af7081e74e9f08b3c
                relevant_fields = {f['name']: note[f['name']] for f in note_type['flds']}
                
                anki_state[deck_path]["notes"][nid] = {
                    "note_id": nid, "card_id": card_ids[0], "note_mod_time": note.mod,
                    "note_type_name": note_type['name'], "relevant_fields": relevant_fields,
<<<<<<< HEAD
                    "target_filename": target_filename, "required_images": get_note_media(note),
                    "card_ids": card_ids
                }
                processed_note_ids.add(nid)
        except Exception:
            pass
            
        if i % 100 == 0: mw.progress.update(value=i)
=======
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
>>>>>>> 8413eca9f1e93d7cf1c5475af7081e74e9f08b3c

    mw.progress.finish()
    return anki_state

def parse_yaml_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    if not content.startswith('---') or not YAML_AVAILABLE: return None
    end_marker = content.find('---', 3)
    if end_marker == -1: return None
    try: 
        return yaml.safe_load(content[3:end_marker].strip())
    except yaml.YAMLError: 
        return None

def build_obsidian_state(target_dir_str: str) -> Dict[str, Any]:
    state = {"base_path": Path(target_dir_str).resolve(), "folders": set(), "note_files": {}, "moc_files": set(), "asset_files": set(), "assets_folder_rel": "assets"}
    if not YAML_AVAILABLE or not state["base_path"].is_dir(): return state
    
    assets_folder_abs = state["base_path"] / state["assets_folder_rel"]
    for root, dirs, files in os.walk(state["base_path"]):
        root_path = Path(root)
        rel_root_path_str = str(root_path.relative_to(state["base_path"])).replace('\\', '/')
        if rel_root_path_str == ".": rel_root_path_str = ""
        
        dirs[:] = [d for d in dirs if d not in ('.obsidian', '.git')]
        for dir_name in dirs:
            if root_path == state["base_path"] and dir_name == state["assets_folder_rel"]: continue
            state["folders"].add(os.path.join(rel_root_path_str, dir_name).replace('\\', '/'))
            
        for filename in files:
            abs_file_path = root_path / filename
            rel_file_path_str = os.path.join(rel_root_path_str, filename).replace('\\', '/')
            
            if root_path == assets_folder_abs: 
                state["asset_files"].add(filename); continue
            if filename == ROOT_MOC_FILENAME or (filename.startswith("_") and filename.endswith("_index.md")): 
                state["moc_files"].add(rel_file_path_str); continue
                
            if filename.endswith(".md"):
                try:
                    with open(abs_file_path, 'r', encoding='utf-8') as f: frontmatter = parse_yaml_frontmatter(f.read())
                    if frontmatter and "anki_note_id" in frontmatter:
                        nid = frontmatter.get("anki_note_id")
                        if isinstance(nid, int):
                            state["note_files"][rel_file_path_str] = {
                                "abs_path": abs_file_path, "anki_note_id": nid,
                                "anki_note_mod": frontmatter.get("anki_note_mod"), "content_hash": frontmatter.get("content_hash")
                            }
                except Exception:
                    pass
    return state