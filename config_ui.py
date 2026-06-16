# -*- coding: utf-8 -*-

"""
Configuration Dialog for the Obsidian Sync Add-on.
"""

import os
from aqt.qt import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QFileDialog, QDialogButtonBox, QWidget,
    QListWidget, QListWidgetItem, QAbstractItemView, Qt
)
from aqt import mw
from aqt.utils import showWarning

from .config import get_obsidian_path, set_obsidian_path, get_excluded_decks, set_excluded_decks

class ConfigDialog(QDialog):
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle("Obsidian Sync Configuration")
        self.setMinimumWidth(550)

        self.current_path = get_obsidian_path() or ""

        # --- Path Selection Widgets ---
        self.path_label = QLabel("Obsidian Sync Target Folder:")
        self.path_edit = QLineEdit(self.current_path)
        self.path_edit.setPlaceholderText("Enter the absolute path to your Obsidian sync folder")
        self.browse_button = QPushButton("Browse...")

        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_label)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_button)

        # --- Exclude Decks List ---
        self.exclude_label = QLabel("Exclude Decks from Sync (Multi-select):")
        self.deck_list = QListWidget()
        self.deck_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        
        if mw and mw.col:
            excluded = get_excluded_decks()
            for deck_name in sorted(mw.col.decks.all_names()):
                item = QListWidgetItem(deck_name)
                # Cross-compatible Qt Flags for PyQt5 & PyQt6
                try:
                    user_checkable = Qt.ItemFlag.ItemIsUserCheckable
                    checked_state = Qt.CheckState.Checked
                    unchecked_state = Qt.CheckState.Unchecked
                except AttributeError:
                    user_checkable = Qt.ItemIsUserCheckable
                    checked_state = Qt.Checked
                    unchecked_state = Qt.Unchecked
                
                item.setFlags(item.flags() | user_checkable)
                item.setCheckState(checked_state if deck_name in excluded else unchecked_state)
                self.deck_list.addItem(item)

        # --- Main Layout ---
        main_layout = QVBoxLayout(self)
        main_layout.addLayout(path_layout)
        main_layout.addSpacing(10)
        main_layout.addWidget(self.exclude_label)
        main_layout.addWidget(self.deck_list)
        main_layout.addSpacing(10)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        main_layout.addWidget(self.button_box)

        # --- Connections ---
        self.browse_button.clicked.connect(self.on_browse)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def on_browse(self):
        start_dir = self.path_edit.text() or os.path.expanduser("~")
        new_path = QFileDialog.getExistingDirectory(self, "Select Obsidian Sync Folder", start_dir)
        if new_path:
            self.path_edit.setText(new_path)

    def accept(self):
        new_path = self.path_edit.text().strip()
        if new_path and os.path.isdir(new_path):
            set_obsidian_path(new_path)
            
            # Save excluded decks
            excluded = []
            try:
                checked_state = Qt.CheckState.Checked
            except AttributeError:
                checked_state = Qt.Checked

            for i in range(self.deck_list.count()):
                item = self.deck_list.item(i)
                if item.checkState() == checked_state:
                    excluded.append(item.text())
            
            set_excluded_decks(excluded)
            super().accept()
        else:
            showWarning("Invalid path specified. Please select a valid directory.")

def show_config_dialog():
    dialog = ConfigDialog(mw)
    dialog.exec()