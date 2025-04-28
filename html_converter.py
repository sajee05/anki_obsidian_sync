# -*- coding: utf-8 -*-

"""
Handles the conversion of Anki field HTML content to Obsidian-compatible Markdown.
Strips span tags to remove color/highlight formatting.
"""

import re
import html
from typing import Optional, Dict

# --- Dependency Check ---
try:
    from markdownify import markdownify as md
    MARKDOWNIFY_AVAILABLE = True
except ImportError:
    MARKDOWNIFY_AVAILABLE = False
    def md(html_string, **options): # Dummy function
        processed = re.sub('<br\s*/?>', '\n', html_string)
        processed = re.sub('<[^>]+>', '', processed)
        return html.unescape(processed)
# --- End Dependency Check ---

# --- Cloze Handling ---
CLOZE_REGEX = re.compile(r"\{\{c(\d+)::(.*?)(?:::(.*?))?\}\}", re.DOTALL)

# --- Tag Stripping ---
# Regex to remove span tags (often used for color/highlight) and their content
SPAN_TAG_REGEX = re.compile(r"<span.*?>|</span>", re.IGNORECASE | re.DOTALL)
# Regex to remove font tags (less common but possible)
FONT_TAG_REGEX = re.compile(r"<font.*?>|</font>", re.IGNORECASE | re.DOTALL)
# Regex to remove mark tags (standard HTML highlight)
MARK_TAG_REGEX = re.compile(r"<mark.*?>|</mark>", re.IGNORECASE | re.DOTALL)

def strip_style_tags(html_content: str) -> str:
    """Removes span and font tags to ignore color/highlight formatting."""
    if not html_content: return ""
    # Remove span tags first
    content = SPAN_TAG_REGEX.sub("", html_content)
    # Remove font tags
    content = FONT_TAG_REGEX.sub("", content)
    # Remove mark tags
    content = MARK_TAG_REGEX.sub("", content)
    return content

# Removed old convert_cloze_to_markdown function as logic is integrated below

# --- Main Conversion Function ---

def convert_html_to_markdown(html_content: str) -> str:
    """
    Converts HTML to Markdown, handling cloze deletions and stripping style tags.
    For Cloze notes, adds an H2 heading (##) before the content preceding each cloze.
    """
    if not html_content: return ""

    # 0. Strip style tags (span, font, mark) from the entire field first
    stripped_content = strip_style_tags(html_content)

    # 1. Process content segment by segment based on clozes
    processed_parts = []
    last_index = 0
    heading_counter = 1 # Initialize counter for numbered headings

    # Use markdownify if available, otherwise use the fallback regex-based cleaner
    md_converter = md if MARKDOWNIFY_AVAILABLE else lambda html_str, **options: html.unescape(re.sub('<br\s*/?>', '\n', re.sub('<[^>]+>', '', html_str)))

    for match in CLOZE_REGEX.finditer(stripped_content):
        # --- Process segment BEFORE the cloze ---
        pre_cloze_html = stripped_content[last_index:match.start()]
        if pre_cloze_html.strip():
            # Convert pre-cloze HTML to Markdown using the selected converter
            pre_cloze_md = md_converter(pre_cloze_html, heading_style="ATX", bullets="-").strip()
            if pre_cloze_md: # Only add heading if there's actual content
                # Add numbered H2 heading marker
                processed_parts.append(f"## {heading_counter}. {pre_cloze_md}")
                heading_counter += 1 # Increment counter for the next heading

        # --- Process the cloze itself ---
        # cloze_number = match.group(1) # Not currently used
        cloze_text = match.group(2)
        cloze_hint = match.group(3)

        # Convert inner cloze text/hint (strip tags first, then convert)
        # Avoid recursive calls to convert_html_to_markdown here
        processed_cloze_text = md_converter(strip_style_tags(cloze_text), heading_style="ATX", bullets="-").strip()

        if cloze_hint:
            processed_cloze_hint = md_converter(strip_style_tags(cloze_hint), heading_style="ATX", bullets="-").strip()
            # Format cloze with hint (using == for highlight, as before, will be removed later)
            processed_parts.append(f"=={processed_cloze_text}== (*{processed_cloze_hint}*)")
        else:
            # Format cloze without hint
            processed_parts.append(f"=={processed_cloze_text}==")

        last_index = match.end()

    # --- Process segment AFTER the last cloze ---
    post_cloze_html = stripped_content[last_index:]
    if post_cloze_html.strip():
        # Convert the remaining HTML after the last cloze
        post_cloze_md = md_converter(post_cloze_html, heading_style="ATX", bullets="-").strip()
        if post_cloze_md:
            processed_parts.append(post_cloze_md) # Append remaining text without heading

    # --- Combine and Final Cleanup ---
    # Join parts with double newline for separation
    markdown_content = "\n\n".join(part for part in processed_parts if part)

    # Remove all highlight markers globally (as per original logic)
    # Consider making this optional in the future if highlights are desired
    markdown_content = markdown_content.replace('==', '')

    # Final post-processing (remove excessive newlines)
    markdown_content = markdown_content.strip()
    markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content)

    # Remove the old '?'-based heading logic entirely.
    # The new logic handles headings specifically for clozes.

    return markdown_content

# --- Field Combination ---

def combine_fields_to_markdown(
    fields: Dict[str, str], note_type_name: str, note_id: int
    ) -> str:
    """Combines relevant fields into a single Markdown string."""
    body = ""

    # Use the updated convert_html_to_markdown which now handles cloze headings internally
    if "Basic" in note_type_name:
        front = fields.get("Front", ""); back = fields.get("Back", "")
        # Still call convert_html_to_markdown for basic fields, it won't apply cloze logic
        body = f"## Front\n\n{convert_html_to_markdown(front)}\n\n<hr/>\n\n## Back\n\n{convert_html_to_markdown(back)}"
    elif "Cloze" in note_type_name:
        text_field_content = fields.get("Text") or fields.get("Content", "")
        # Directly convert the Cloze field; the function now handles the H2 logic internally
        body = convert_html_to_markdown(text_field_content)
    else: # Handle other note types (non-Basic, non-Cloze)
        field_parts = []
        for name, value in fields.items():
            if value and value.strip():
                # Convert each field; no special heading logic applied here unless it contains clozes by chance
                field_parts.append(f"## {name}\n\n{convert_html_to_markdown(value)}")
        body = "\n\n<hr/>\n\n".join(field_parts)

    if not MARKDOWNIFY_AVAILABLE:
        body += "\n\n---\n*Note: HTML conversion limited due to missing 'markdownify' library.*"

    return body.strip()