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
    
    # Override table preservation based on user config
    if False:
        preserve_tables = False

    table_store = {}
    math_store = {}
    embed_store = {}

    # --- 1. Protect & Convert MathJax/LaTeX ---
    content = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', content, flags=re.DOTALL)
    content = re.sub(r'\\\((.*?)\\\)', r'$\1$', content, flags=re.DOTALL)
    content = re.sub(r'\[\$\$\](.*?)\[/\$\$\]', r'$$\1$$', content, flags=re.DOTALL)
    content = re.sub(r'\[\$\](.*?)\[/\$\]', r'$\1$', content, flags=re.DOTALL)
    content = re.sub(r'<anki-mathjax block="true">(.*?)</anki-mathjax>', r'$$\1$$', content, flags=re.DOTALL)
    content = re.sub(r'<anki-mathjax>(.*?)</anki-mathjax>', r'$\1$', content, flags=re.DOTALL)

    def save_math(m):
        ph = f"MATHPLACEHOLDER{len(math_store)}ENDMATH"
        math_store[ph] = m.group(0)
        return ph
    content = re.sub(r'\$\$.*?\$\$', save_math, content, flags=re.DOTALL)
    content = re.sub(r'\$.*?\$', save_math, content, flags=re.DOTALL)

    # --- 2. Extract and Protect HTML Tables (If enabled) ---
    if preserve_tables and BS4_AVAILABLE:
        soup = BeautifulSoup(content, 'html.parser')
        # We do NOT un-nest tables anymore. Obsidian natively supports nested HTML tables.
        for idx, table in enumerate(soup.find_all('table')):
            # Only process top-level tables to avoid double-processing nested ones
            if table.find_parent('table') is None:
                table_str = str(table)
                table_str = CLOZE_REGEX.sub(r'<mark style="background-color: #ffb74d; color: black; border-radius: 3px; padding: 0 3px;">\2</mark>', table_str)
                table_str = AUDIO_REGEX.sub(r'**[Audio: \1]**', table_str)
                ph = f"TABLEPLACEHOLDER{idx}ENDTABLE"
                table_store[ph] = table_str
                table.insert_after(ph)
                table.extract()
        content = str(soup)

    # --- 3. Process Media (Images, Video, Audio) ---
    content, _ = extract_and_preserve_media(content)
    
    # --- 4. Protect Obsidian Embeds from Markdownify ---
    # This guarantees that webp, jpg, pngs inside clozes or normal text do not get escaped
    def save_embed(m):
        ph = f"EMBEDPLACEHOLDER{len(embed_store)}ENDEMBED"
        embed_store[ph] = m.group(0)
        return ph
    content = re.sub(r'!\[\[.*?\]\]', save_embed, content)

    # --- 5. Markdownify the remaining text ---
    if MARKDOWNIFY_AVAILABLE:
        # Keep formatting tags like underline, colors, sub/sup, strikethrough so Obsidian renders them natively
        content = md(content, heading_style="ATX", bullets="-", keep=['u', 'span', 'font', 'sup', 'sub', 's', 'strike', 'del']).strip()
    else:
        content = html.unescape(re.sub(r'<[^>]+>', '', re.sub(r'<br\s*/?>', '\n', content))).strip()

    # --- 6. Restore Obsidian Embeds ---
    for ph, embed in embed_store.items():
        content = content.replace(ph, embed)

    # --- 7. Process Clozes (Turn them into Obsidian Highlights) ---
    def process_cloze(m):
        text = m.group(2)
        hint = m.group(3)
        if remove_hints or not hint:
            return f"=={text}=="
        return f"=={text}== (*hint: {hint}*)"
        
    content = CLOZE_REGEX.sub(process_cloze, content)

    # Clean up excessive newlines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # --- 8. Restore the intact HTML Tables & MathJax ---
    if preserve_tables:
        for ph, table_html in table_store.items():
            content = content.replace(ph, f"\n\n{table_html}\n\n")
            
    for ph, math_str in math_store.items():
        content = content.replace(ph, math_str)
            
    return content

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