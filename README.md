# Obsidian Sync (Differential) By M Saajeel ⭐ : Anki ⇌ Obsidian Sync: Bridge Your Flashcards and Notes!

<a href="https://ankiweb.net/shared/info/1162061440?cb=1745843664504" target="_blank" style="display: inline-block; padding: 10px 20px; font-size: 16px; font-weight: bold; color: white; background-color: #007bff; text-align: center; border-radius: 5px; text-decoration: none;">Get it on AnkiWeb</a>

## Demonstration

![Demonstration GIF](demo.gif)

[Link to Demo GIF](demo.gif)

[Link to YouTube Demo](https://youtu.be/LcsV0cqd-6Y)

## The Problem: Flashcards Adrift, Notes Disconnected

You love Anki for drilling facts with spaced repetition. You love Obsidian for building a connected web of knowledge, linking ideas, and seeing the bigger picture. But your Anki flashcards often feel isolated from the rich context stored in your Obsidian notes.

Maybe you make flashcards while reading books or articles. Later, when reviewing a card in Anki, you wish you could instantly jump back to the surrounding paragraph or your broader notes on the topic in Obsidian to refresh your memory. It's frustrating having these two powerful tools working in silos!

## The Solution: An Automatic Bridge!

This Anki addon acts as a bridge, automatically exporting your Anki notes into clean, organized Markdown files within your Obsidian vault. It keeps your knowledge synchronized, allowing you to leverage the strengths of both platforms.

## Key Features: Your Anki Notes, Supercharged in Obsidian

- **🧠 Smart Sync:** Only updates what's actually changed in Anki since the last sync, making it fast and efficient.
- **🗂️ Mirrors Your Decks:** Automatically creates folders in your Obsidian vault that perfectly match your Anki deck and sub-deck structure.
- **✨ Clean Markdown:** Converts your Anki notes (even those with HTML formatting) into Obsidian-friendly Markdown.
- **📝 Automatic Outlines (for Cloze Notes!):** Magically turns the text *before* each `{{c...}}` deletion in your Cloze notes into a numbered heading (`## 1. ...`, `## 2. ...`). This creates a handy outline within the Obsidian note, perfect for seeing the structure of your card!
- **📄 Handles Basic Notes:** Neatly separates your "Front" and "Back" fields with `## Front` and `## Back` headings.
- **⚙️ Supports Custom Notes:** Creates `## Field Name` headings for each field in your other note types.
- **🖼️ Image Sync:** Finds images used in your Anki notes and copies them into a central `assets` folder in your Obsidian sync directory, fixing the links automatically.
- **🗺️ Index Files (Maps of Content):** Generates helpful index files (`_Deck_Name_index.md`) inside each deck folder, listing and linking to all the notes within that deck. It also creates a master index (`_Anki_Collection_Index.md`) at the root!
- **🖱️ Easy Setup:** Configure your target Obsidian folder easily via the Anki "Tools" menu.

## How it Works (The Non-Technical Version)

Think of it like a diligent librarian comparing two sets of books (your Anki collection and your Obsidian sync folder). When you click "Sync Now":

1. **Scan Anki:** The addon looks at all your notes and decks in Anki.
2. **Scan Obsidian:** It checks the designated folder in your Obsidian vault, looking at the files and special tracking info stored within them.
3. **Compare:** It figures out what's new, what's changed, and what's been deleted in Anki since the last sync.
4. **Update Obsidian:** It then carefully:
  - Creates any missing folders (for new decks).
  - Creates new `.md` files for new notes.
  - Updates existing `.md` files if the Anki note changed.
  - Deletes `.md` files if the Anki note was deleted.
  - Copies over any new images needed.
  - Updates the index files (MOCs) to reflect the current state.

## Getting Started: Quick Setup

1. **Install:** Install this addon into Anki like any other (in the addons21 folder).
2. **Configure:**
  - Open Anki.
  - Go to the **Tools** menu -> **Obsidian Sync** -> **Configure...**.
  - Click "Browse" and select the **main folder** inside your Obsidian vault where you want your Anki notes to be saved (e.g., `YourVault/Anki Sync`).
  - Click "Save".
3. **First Sync:** Go to **Tools** -> **Obsidian Sync** -> **Sync Now!** The first sync might take a little longer as it exports everything. Subsequent syncs will be much faster.

## Rules & Tips for Smooth Syncing

- ✅ **Use a "Title" Field for Cloze Notes:** This is highly recommended! Add a field named exactly `Title` to your Cloze note type in Anki. The addon will use the content of this field to create a clean, predictable filename for the corresponding Markdown file in Obsidian. (If missing, it tries to use the start of the main text field, which might be less ideal).
- **Basic Note Filenames:** For standard "Basic" notes, the filename is generated from the content of the "Front" field.
- **Filename Cleanup:** Characters in your deck names or filename source fields that aren't allowed in filenames (like `?`, `/`, `\`, `:`, `*`, `"`, `<`, `>`, `|`) will be automatically replaced with an underscore (`_`).
- **Styling Stripped:** Heads up! Formatting like text color or background highlights applied in Anki **will be removed** during the conversion to Markdown. The focus is on content structure.
- ⚠️ **One-Way Street (Important!):** This addon currently syncs **FROM Anki TO Obsidian ONLY**. If you edit the Markdown files directly in Obsidian, those changes **WILL NOT** be synced back to Anki. Furthermore, your Obsidian edits might be **overwritten** the next time you sync from Anki. Think of the Obsidian files as a searchable, linkable *mirror* or *reference* for your Anki notes.
- **Dependencies:** Just a reminder, it needs `PyYAML` and `markdownify` to work fully.(already present in "anki_obsidian_sync/vendor" folder)

## Use Case Example: Notes from Books / Research

This addon shines when you're creating flashcards from source material like books, articles, or lectures.

1. **Capture in Anki:** As you read, create detailed Anki cards (especially Cloze) for key concepts, definitions, or questions. Use a "Title" field to name the card logically (e.g., "Chapter 5 - Definition of Poverty Line").
2. **Sync to Obsidian:** Run the sync. Your Anki notes appear in Obsidian, organized by deck (e.g., `YourVault/Anki Sync/Book Notes/Chapter 5 - Definition of Poverty Line_1234567890.md`).
3. **Connect in Obsidian:** Inside Obsidian, you can now:
  - Open the generated note. You'll see the content structured with headings based on your clozes (`## 1. The poverty line is defined by...`).
  - Link this note to your main summary note for Chapter 5.
  - Link it to other related concepts across your vault.
  - Add your own commentary or further thoughts *around* the synced content (just remember edits *to* the synced content might be overwritten).
4. **Contextual Review:** Later, when a card pops up in Anki and you feel unsure, glance at the filename (which includes the title and Note ID). Quickly search for this filename or ID in Obsidian to instantly pull up the note and its surrounding context, links, and your additional thoughts. No more context switching or losing the thread!

---

Let me know if you need an even more elaborate and step-by-step demonstration of how to get this working. If things are still not clear after reading these README instructions, I will create a proper video tutorial for ya'll.

Made with Passion by Mohd Sajeel Memon.
Enjoy bridging the gap between spaced repetition and networked thought!