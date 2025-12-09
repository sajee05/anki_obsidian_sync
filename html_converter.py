# -*- coding: utf-8 -*-

"""
Handles the conversion of Anki field HTML content to Obsidian-compatible Markdown.
Supports complex tables, cloze deletions with hints, and media preservation.
"""

import re
import html
from typing import Optional, Dict, List, Tuple
from pathlib import Path

# --- Dependency Check ---
try:
    from markdownify import markdownify as md
    MARKDOWNIFY_AVAILABLE = True
except ImportError:
    MARKDOWNIFY_AVAILABLE = False
    def md(html_string, **options): # Dummy function
        processed = re.sub(r'<br\s*/?>', '\n', html_string)
        processed = re.sub('<[^>]+>', '', processed)
        return html.unescape(processed)
# --- End Dependency Check ---

# --- Cloze Handling ---
CLOZE_REGEX = re.compile(r"\{\{c(\d+)::(.*?)(?:::(.*?))?\}\}", re.DOTALL)

# --- Media Handling ---
IMAGE_REGEX = re.compile(r'<img[^>]+src=["\']([^"\'>]+)["\'][^>]*>', re.IGNORECASE)
AUDIO_REGEX = re.compile(r'\[sound:([^\]]+)\]', re.IGNORECASE)
VIDEO_REGEX = re.compile(r'<video[^>]+src=["\']([^"\'>]+)["\'][^>]*>.*?</video>', re.IGNORECASE | re.DOTALL)
WEBP_IMAGE_REGEX = re.compile(r'src=["\']([^"\'>]+\.webp)["\']', re.IGNORECASE)

# --- Tag Handling ---
# Regex to handle span tags with background color (for highlighting)
HIGHLIGHT_SPAN_REGEX = re.compile(r'<span[^>]*style=["\'][^"\'>]*background(?:-color)?:\s*([^;"\'>]+)[^"\'>]*["\'][^>]*>(.*?)</span>', re.IGNORECASE | re.DOTALL)
# Regex to handle other span tags
SPAN_TAG_REGEX = re.compile(r"<span[^>]*>|</span>", re.IGNORECASE | re.DOTALL)
# Regex to remove font tags
FONT_TAG_REGEX = re.compile(r"<font[^>]*>|</font>", re.IGNORECASE | re.DOTALL)
# Regex to remove mark tags
MARK_TAG_REGEX = re.compile(r"<mark[^>]*>|</mark>", re.IGNORECASE | re.DOTALL)

def preserve_highlighted_content(html_content: str) -> str:
    """Preserves highlighted content with markdown highlighting."""
    if not html_content:
        return ""
    
    # Replace highlighted spans with markdown highlighting
    def replace_highlight(match):
        color = match.group(1).strip()
        content = match.group(2)
        # Check if it's a highlight color (yellow, blue, green, etc.)
        if any(c in color.lower() for c in ['yellow', 'rgb(85, 85, 255)', 'rgb(255, 255, 0)', 'rgb(0, 255, 0)', 'rgb(255, 170, 0)']):
            return f"=={content}=="
        return content
    
    content = HIGHLIGHT_SPAN_REGEX.sub(replace_highlight, html_content)
    return content

def strip_style_tags(html_content: str, preserve_highlights: bool = False) -> str:
    """Removes or preserves span and font tags based on settings."""
    if not html_content:
        return ""
    
    if preserve_highlights:
        content = preserve_highlighted_content(html_content)
    else:
        content = html_content
    
    # Remove remaining span tags
    content = SPAN_TAG_REGEX.sub("", content)
    # Remove font tags
    content = FONT_TAG_REGEX.sub("", content)
    # Remove mark tags (unless we want to preserve them)
    if not preserve_highlights:
        content = MARK_TAG_REGEX.sub("", content)
    return content

def convert_table_to_markdown(table_html: str) -> str:
    """Converts HTML tables to proper Markdown tables."""
    if not table_html:
        return ""
    
    # Parse table rows and cells
    rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.IGNORECASE | re.DOTALL)
    if not rows:
        return table_html
    
    markdown_rows = []
    for row_html in rows:
        # Extract cells (both td and th)
        cells = re.findall(r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>', row_html, re.IGNORECASE | re.DOTALL)
        if cells:
            # Process each cell content
            processed_cells = []
            for cell in cells:
                # Convert cell content to markdown
                cell_content = strip_style_tags(cell, preserve_highlights=True)
                cell_content = re.sub(r'<br\s*/?>', ' ', cell_content)
                cell_content = re.sub(r'<[^>]+>', '', cell_content)
                cell_content = html.unescape(cell_content).strip()
                # Replace newlines with spaces for table compatibility
                cell_content = re.sub(r'\n+', ' ', cell_content)
                processed_cells.append(cell_content)
            markdown_rows.append(processed_cells)
    
    if not markdown_rows:
        return table_html
    
    # Build markdown table
    result = []
    
    # Add header row (first row)
    if markdown_rows:
        result.append('| ' + ' | '.join(markdown_rows[0]) + ' |')
        # Add separator
        result.append('| ' + ' | '.join(['---'] * len(markdown_rows[0])) + ' |')
        # Add remaining rows
        for row in markdown_rows[1:]:
            # Ensure all rows have same number of columns
            while len(row) < len(markdown_rows[0]):
                row.append('')
            result.append('| ' + ' | '.join(row) + ' |')
    
    return '\n'.join(result)

def extract_and_preserve_media(html_content: str) -> Tuple[str, List[Dict[str, str]]]:
    """Extracts media references and preserves them in markdown format."""
    media_items = []
    content = html_content
    
    # Handle images
    for match in IMAGE_REGEX.finditer(content):
        src = match.group(1)
        if src.startswith('paste-') or src.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg')):
            # Preserve image reference
            media_items.append({'type': 'image', 'src': src})
            # Replace with markdown image syntax
            content = content.replace(match.group(0), f'![Image]({src})')
    
    # Handle audio
    for match in AUDIO_REGEX.finditer(content):
        audio_file = match.group(1)
        media_items.append({'type': 'audio', 'src': audio_file})
        # Replace with markdown link
        content = content.replace(match.group(0), f'[Audio: {audio_file}]({audio_file})')
    
    # Handle video
    for match in VIDEO_REGEX.finditer(content):
        video_src = match.group(1)
        media_items.append({'type': 'video', 'src': video_src})
        # Replace with markdown link
        content = content.replace(match.group(0), f'[Video: {video_src}]({video_src})')
    
    return content, media_items

# --- Main Conversion Function ---

def convert_html_to_markdown(html_content: str, preserve_tables: bool = True, remove_hints: bool = True) -> str:
    """
    Converts HTML to Markdown with enhanced support for:
    - Complex HTML tables
    - Cloze deletions with optional hint removal
    - Media preservation (images, audio, video)
    - Highlighted content preservation
    """
    if not html_content:
        return ""

    # 0. Extract and preserve media first
    content_with_media, media_items = extract_and_preserve_media(html_content)
    
    # 1. Handle tables if present
    if preserve_tables and '<table' in content_with_media.lower():
        # Find all tables and convert them
        tables = re.findall(r'<table[^>]*>.*?</table>', content_with_media, re.IGNORECASE | re.DOTALL)
        for table_html in tables:
            markdown_table = convert_table_to_markdown(table_html)
            content_with_media = content_with_media.replace(table_html, markdown_table)
    
    # 2. Process style tags (preserve highlights)
    stripped_content = strip_style_tags(content_with_media, preserve_highlights=True)

    # 3. Process content segment by segment based on clozes
    processed_parts = []
    last_index = 0
    has_clozes = bool(CLOZE_REGEX.search(stripped_content))
    
    # Use markdownify if available, otherwise use the fallback regex-based cleaner
    md_converter = md if MARKDOWNIFY_AVAILABLE else lambda html_str, **options: html.unescape(re.sub(r'<br\s*/?>', '\n', re.sub(r'<[^>]+>', '', html_str)))
    
    if has_clozes:
        for match in CLOZE_REGEX.finditer(stripped_content):
            # Process segment BEFORE the cloze
            pre_cloze_html = stripped_content[last_index:match.start()]
            if pre_cloze_html.strip():
                # Convert pre-cloze HTML to Markdown
                pre_cloze_md = md_converter(pre_cloze_html, heading_style="ATX", bullets="-").strip()
                if pre_cloze_md:
                    processed_parts.append(pre_cloze_md)
            
            # Process the cloze itself
            cloze_number = match.group(1)
            cloze_text = match.group(2)
            cloze_hint = match.group(3)
            
            # Convert cloze content
            processed_cloze_text = md_converter(strip_style_tags(cloze_text, preserve_highlights=True), 
                                               heading_style="ATX", bullets="-").strip()
            
            # Format cloze with highlighting
            if remove_hints or not cloze_hint:
                # Just highlight the cloze text without hint
                processed_parts.append(f"=={processed_cloze_text}==")
            else:
                # Include hint if not removing
                processed_cloze_hint = md_converter(strip_style_tags(cloze_hint), 
                                                  heading_style="ATX", bullets="-").strip()
                processed_parts.append(f"=={processed_cloze_text}== (*hint: {processed_cloze_hint}*)")
            
            last_index = match.end()

        # Process segment AFTER the last cloze
        post_cloze_html = stripped_content[last_index:]
        if post_cloze_html.strip():
            post_cloze_md = md_converter(post_cloze_html, heading_style="ATX", bullets="-").strip()
            if post_cloze_md:
                processed_parts.append(post_cloze_md)
    else:
        # No clozes found, just convert the entire content
        converted_md = md_converter(stripped_content, heading_style="ATX", bullets="-").strip()
        if converted_md:
            processed_parts.append(converted_md)

    # 4. Combine and Final Cleanup
    markdown_content = "\n\n".join(part for part in processed_parts if part)
    
    # Clean up excessive newlines
    markdown_content = markdown_content.strip()
    markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)
    
    # Fix any broken markdown links or images
    markdown_content = re.sub(r'!\[([^\]]*)\]\s*\(([^\)]*)\)', r'![\1](\2)', markdown_content)
    markdown_content = re.sub(r'\[([^\]]*)\]\s*\(([^\)]*)\)', r'[\1](\2)', markdown_content)
    
    return markdown_content

# --- Field Combination ---

def combine_fields_to_markdown(
    fields: Dict[str, str], note_type_name: str, note_id: int,
    preserve_extra: bool = True
    ) -> str:
    """Combines relevant fields into a single Markdown string with support for Extra field."""
    body = ""

    # Convert fields with enhanced HTML handling
    if "Basic" in note_type_name:
        front = fields.get("Front", "")
        back = fields.get("Back", "")
        body_parts = []
        
        if front:
            body_parts.append(f"## Front\n\n{convert_html_to_markdown(front)}")
        if back:
            body_parts.append(f"## Back\n\n{convert_html_to_markdown(back)}")
        
        body = "\n\n<hr/>\n\n".join(body_parts)
        
    elif "Cloze" in note_type_name:
        # Get the main content field
        text_field_content = fields.get("Text") or fields.get("Content", "")
        title = fields.get("Title", "")
        
        # Add title if present
        if title:
            body = f"# {convert_html_to_markdown(title, preserve_tables=False)}\n\n"
            body += convert_html_to_markdown(text_field_content)
        else:
            body = convert_html_to_markdown(text_field_content)
    
    else:  # Handle other note types
        field_parts = []
        for name, value in fields.items():
            if value and value.strip() and name not in ['Extra']:  # Process Extra separately
                field_parts.append(f"## {name}\n\n{convert_html_to_markdown(value)}")
        body = "\n\n<hr/>\n\n".join(field_parts)
    
    # Handle Extra field (common across all note types)
    if preserve_extra:
        extra_content = fields.get("Extra", "")
        if extra_content and extra_content.strip():
            # Add Extra field at the end
            if body:
                body += "\n\n<hr/>\n\n"
            body += f"## Extra\n\n{convert_html_to_markdown(extra_content)}"

    if not MARKDOWNIFY_AVAILABLE:
        body += "\n\n---\n*Note: HTML conversion limited due to missing 'markdownify' library.*"

    return body.strip()