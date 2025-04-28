# -*- coding: utf-8 -*-

"""
Configuration Dialog for the Obsidian Sync Add-on.
"""

import os
from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QDialogButtonBox,
    QWidget,
    QSizePolicy
)
from aqt import mw
# Import showInfo for debugging popup
from aqt.utils import showInfo, showWarning

# Import from the new config module
from .config import get_obsidian_path, set_obsidian_path


class ConfigDialog(QDialog):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Obsidian Sync Configuration")
        self.setMinimumWidth(500) # Set a reasonable minimum width

        self.current_path = get_obsidian_path() or ""
        print(f"DEBUG: ConfigDialog init - current_path loaded as: {self.current_path!r}") # DEBUG

        # --- Widgets ---
        self.path_label = QLabel("Obsidian Sync Target Folder:")
        self.path_edit = QLineEdit(self.current_path)
        self.path_edit.setPlaceholderText("Enter the absolute path to your Obsidian sync folder")
        self.browse_button = QPushButton("Browse...")

        # --- Layouts ---
        # Path selection layout
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_label)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_button)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(path_layout)
        main_layout.addStretch() # Add space before buttons

        # Dialog buttons (OK/Cancel)
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        main_layout.addWidget(self.button_box)

        # --- Connections ---
        self.browse_button.clicked.connect(self.on_browse)
        self.button_box.accepted.connect(self.accept) # Default accept action
        self.button_box.rejected.connect(self.reject) # Default reject action

    def on_browse(self):
        """Opens a directory selection dialog."""
        print("DEBUG: ConfigDialog on_browse() called.") # DEBUG
        start_dir = self.path_edit.text() or os.path.expanduser("~")
        new_path = QFileDialog.getExistingDirectory(
            self,
            "Select Obsidian Sync Folder",
            start_dir
        )
        if new_path:
            print(f"DEBUG: Directory selected: {new_path!r}") # DEBUG
            self.path_edit.setText(new_path) # Update the line edit

    def accept(self):
        """Saves the configuration when OK is clicked."""
        # Show popup first to confirm method is called
        showInfo("Accept method triggered!") # Show popup for debugging
        print("DEBUG: ConfigDialog accept() method called.") # DEBUG
        new_path = self.path_edit.text().strip()
        print(f"DEBUG: Path from text edit: {new_path!r}") # DEBUG
        if new_path and os.path.isdir(new_path):
            print(f"DEBUG: Path is valid, calling set_obsidian_path...") # DEBUG
            set_obsidian_path(new_path)
            print(f"DEBUG: set_obsidian_path called for {new_path!r}. Closing dialog.") # DEBUG
            super().accept() # Close the dialog
        else:
            print(f"DEBUG: Path is invalid: {new_path!r}. Showing warning.") # DEBUG
            # from aqt.utils import showWarning # Already imported at top level now
            showWarning("Invalid path specified. Please select a valid directory.")
            # Keep the dialog open

# --- Function to show the dialog ---
def show_config_dialog():
    print("DEBUG: show_config_dialog() called.") # DEBUG
    dialog = ConfigDialog(mw) # Pass Anki's main window as parent
    dialog.exec() # Use exec() for modal dialog
    print("DEBUG: show_config_dialog() finished.") # DEBUG