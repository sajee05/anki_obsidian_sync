# -*- coding: utf-8 -*-

"""
Handles the conversion of Anki field HTML content to Obsidian-compatible Markdown.
Uses BeautifulSoup to perfectly preserve tables, un-nest nested tables, and retain inline media.
"""

import re
import html
from typing import Optional, Dict, List, Tuple
from aqt import mw

# --- Dependency Check ---
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    from markdownify import markdownify as md
    MARKDOWNIFY_AVAILABLE = True
except ImportError:
    MARKDOWNIFY_AVAILABLE = False
    def md(html_string, **options):
        processed = re.sub(r'<br\s*/?>', '\n', html_string)
        processed = re.sub('<[^>]+>', '', processed)
        return html.unescape(processed)

# --- Regex Matchers ---
CLOZE_REGEX = re.compile(r"\{\{c(\d+)::(.*?)(?:::(.*?))?\}\}", re.DOTALL)
IMAGE_REGEX = re.compile(r'<img[^>]+src=["\']([^"\'>]+)["\'][^>]*>', re.IGNORECASE)
AUDIO_REGEX = re.compile(r'\[sound:([^\]]+)\]', re.IGNORECASE)
VIDEO_REGEX = re.compile(r'<video[^>]+src=["\']([^"\'>]+)["\'][^>]*>.*?</video>', re.IGNORECASE | re.DOTALL)

def extract_and_preserve_media(html_content: str) -> Tuple[str, List[Dict[str, str]]]:
    """Extracts media references and converts them to Obsidian native wiki-embeds."""
    media_items = []
    content = html_content
    
    # Handle audio
    for match in AUDIO_REGEX.finditer(content):
        audio_file = match.group(1)
        media_items.append({'type': 'audio', 'src': audio_file})
        content = content.replace(match.group(0), f'![[{audio_file}]]')
    
    # Handle video
    for match in VIDEO_REGEX.finditer(content):
        video_src = match.group(1)
        media_items.append({'type': 'video', 'src': video_src})
        content = content.replace(match.group(0), f'![[{video_src}]]')
    
    # Handle standard images
    def replace_img(match):
        src = match.group(1)
        if src.startswith('paste-') or src.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')):
            media_items.append({'type': 'image', 'src': src})
        return f'![[{src}]]'
        
    content = IMAGE_REGEX.sub(replace_img, content)
    return content, media_items

def convert_html_to_markdown(html_content: str, preserve_tables: bool = True, remove_hints: bool = True) -> str:
    if not html_content:
        return ""

    content = html_content
    table_store = {}

    # --- 1. Safely Extract and Protect Tables ---
    if preserve_tables and BS4_AVAILABLE:
        soup = BeautifulSoup(content, 'html.parser')
        
        # Un-nest tables (If a table is inside a table, pull it out to make them separate)
        nested_tables = soup.find_all('table')
        for table in nested_tables:
            parent_table = table.find_parent('table')
            if parent_table:
                # Move the nested table to be immediately after its parent
                parent_table.insert_after(table.extract())
                parent_table.insert_after(soup.new_tag("br"))

        # Process all tables (now guaranteed to be top-level)
        for idx, table in enumerate(soup.find_all('table')):
            table_str = str(table)
            
            # Convert Clozes INSIDE tables to HTML highlights so Obsidian renders them
            table_str = CLOZE_REGEX.sub(r'<mark style="background-color: #ffb74d; color: black; border-radius: 3px; padding: 0 3px;">\2</mark>', table_str)
            # Convert audio INSIDE tables to simple text (Obsidian struggles with ![[audio]] inside <td>)
            table_str = AUDIO_REGEX.sub(r'**[Audio: \1]**', table_str)
            
            # Use an alphanumeric placeholder that markdownify will NEVER escape
            placeholder = f"TABLEPLACEHOLDER{idx}ENDTABLE"
            table_store[placeholder] = table_str
            
            table.insert_after(placeholder)
            table.extract()
            
        content = str(soup)

    elif preserve_tables and not BS4_AVAILABLE:
        # Fallback if BeautifulSoup is missing
        def save_table(m):
            idx = len(table_store)
            table_str = m.group(0)
            table_str = CLOZE_REGEX.sub(r'<mark style="background-color: #ffb74d; color: black; border-radius: 3px; padding: 0 3px;">\2</mark>', table_str)
            placeholder = f"TABLEPLACEHOLDER{idx}ENDTABLE"
            table_store[placeholder] = table_str
            return placeholder
        content = re.sub(r'(?si)<table.*?>.*?</table>', save_table, content)

    # --- 2. Process Media outside tables ---
    content, _ = extract_and_preserve_media(content)
    
    # --- 3. Markdownify the remaining text ---
    if MARKDOWNIFY_AVAILABLE:
        content = md(content, heading_style="ATX", bullets="-").strip()
    else:
        content = html.unescape(re.sub(r'<[^>]+>', '', re.sub(r'<br\s*/?>', '\n', content))).strip()

    # --- 4. Process Clozes outside tables ---
    def process_cloze(m):
        text = m.group(2)
        hint = m.group(3)
        if remove_hints or not hint:
            return f"=={text}=="
        return f"=={text}== (*hint: {hint}*)"
        
    content = CLOZE_REGEX.sub(process_cloze, content)

    # Clean up excessive newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # --- 5. Restore the intact HTML Tables ---
    if preserve_tables:
        for placeholder, table_html in table_store.items():
            content = content.replace(placeholder, f"\n\n{table_html}\n\n")
            
    return content

# --- Field Combination ---

def combine_fields_to_markdown(fields: Dict[str, str], note_type_name: str, note_id: int, preserve_extra: bool = True) -> str:
    """Combines relevant fields into a single Markdown string."""
    note_type_lower = note_type_name.lower()
    body_parts = []

    # Format specific note types
    if "cloze" in note_type_lower:
        title = fields.get("Title", "")
        if title: body_parts.append(f"# {convert_html_to_markdown(title, preserve_tables=False)}")
        text = fields.get("Text", fields.get("Content", ""))
        if text: body_parts.append(convert_html_to_markdown(text))
        extra = fields.get("Extra", "")
        if extra and preserve_extra:
            quote = "\n".join(f"> {line}" for line in convert_html_to_markdown(extra).split("\n"))
            body_parts.append(f"### Extra\n{quote}")

    elif "image occlusion" in note_type_lower:
        header = fields.get("Header", "")
        if header: body_parts.append(f"# {convert_html_to_markdown(header)}")
        image = fields.get("Image", "")
        if image: body_parts.append(f"### Base Image\n{convert_html_to_markdown(image)}")
        masks = []
        for mask_f in ["Question Mask", "Answer Mask"]:
            if fields.get(mask_f): masks.append(f"**{mask_f}:**\n{convert_html_to_markdown(fields[mask_f])}")
        if masks: body_parts.append("### Masks\n" + "\n\n".join(masks))
        for ext_f in ["Remarks", "Sources", "Extra 1", "Extra 2"]:
            if fields.get(ext_f): body_parts.append(f"### {ext_f}\n{convert_html_to_markdown(fields[ext_f])}")

    elif "forum toolkit" in note_type_lower or "mcq" in note_type_lower:
        question = fields.get("Question", "")
        if question: body_parts.append(f"## Question\n{convert_html_to_markdown(question)}")
        options = []
        for opt in ["A", "B", "C", "D", "E"]:
            if fields.get(opt): options.append(f"- **{opt}**: {convert_html_to_markdown(fields[opt])}")
        if options: body_parts.append("### Options\n" + "\n".join(options))
        expl = fields.get("Explanation", "")
        if expl: body_parts.append(f"### Explanation\n{convert_html_to_markdown(expl)}")

    elif "current affairs" in note_type_lower:
        date = fields.get("Date", "")
        if date: body_parts.append(f"**Date:** {convert_html_to_markdown(date)}")
        front = fields.get("Front", "")
        back = fields.get("Back", "")
        if front: body_parts.append(f"## Front\n{convert_html_to_markdown(front)}")
        if back: body_parts.append(f"## Back\n{convert_html_to_markdown(back)}")
        if fields.get("Extra") and preserve_extra: body_parts.append(f"### Extra\n{convert_html_to_markdown(fields['Extra'])}")

    else:
        for name, value in fields.items():
            if value and value.strip() and name.lower() != 'extra':
                body_parts.append(f"## {name}\n{convert_html_to_markdown(value)}")
        if fields.get("Extra") and preserve_extra:
            body_parts.append(f"## Extra\n{convert_html_to_markdown(fields['Extra'])}")

    # Fetch Card ID (CID) dynamically from Anki Database
    card_id = note_id
    if mw and mw.col:
        try:
            # Get the first CID associated with this NID
            fetched_cid = mw.col.db.scalar("SELECT id FROM cards WHERE nid = ? LIMIT 1", note_id)
            if fetched_cid:
                card_id = fetched_cid
        except Exception:
            pass

    anki_link = f"anki://x-callback-url/search?query=cid:{card_id}"
    footer = f"\n\n---\n*Anki Reference: [Card {card_id}]({anki_link})*"
    
    if not MARKDOWNIFY_AVAILABLE:
        footer += "\n*Note: HTML conversion limited due to missing 'markdownify' library.*"

    return "\n\n".join(body_parts).strip() + footer