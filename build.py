#!/usr/bin/env python3
"""Build & publish the Obsidian Sync Anki addon.

Usage:
    python build.py                      # Build to dist/ (versioned .ankiaddon)
    python build.py --output foo.ankiaddon   # Build to custom path
    python build.py --publish DIR        # Build + extract directly into DIR/anki_obsidian_sync/
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))

INCLUDE = {
    "__init__.py",
    "config.py",
    "config_ui.py",
    "config.json",
    "diff_calculator.py",
    "executor.py",
    "html_converter.py",
    "state_builder.py",
    "meta.json",
    "LICENSE",
}

VENDOR_DIR = "vendor"


def load_version():
    meta_path = os.path.join(ROOT, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            return json.load(f).get("version", "0.0.0")
    return "0.0.0"


def load_package_name():
    meta_path = os.path.join(ROOT, "meta.json")
    if os.path.isfile(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            return json.load(f).get("package", "anki_obsidian_sync")
    return "anki_obsidian_sync"


def collect_files(root):
    """Yield (arcname, abspath) for all files that should ship."""
    for name in INCLUDE:
        path = os.path.join(root, name)
        if os.path.isfile(path):
            yield name, path

    vendor_src = os.path.join(root, VENDOR_DIR)
    if os.path.isdir(vendor_src):
        for dirpath, dirnames, filenames in os.walk(vendor_src):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for fn in filenames:
                abspath = os.path.join(dirpath, fn)
                yield os.path.relpath(abspath, root), abspath


def build_zip(output: str):
    """Create the .ankiaddon zip at *output*."""
    dst_dir = os.path.dirname(output)
    if dst_dir:
        os.makedirs(dst_dir, exist_ok=True)

    files = list(collect_files(ROOT))
    if not files:
        print("ERROR: no files to package")
        return False

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for arcname, abspath in files:
            zf.write(abspath, arcname)

    size_kb = os.path.getsize(output) >> 10
    print(f"Built  {output}  ({len(files)} files, {size_kb} KB)")
    return True


def publish(publish_dir: str):
    """Build zip in a temp location, then extract into publish_dir/<package>/."""
    package = load_package_name()
    target = os.path.join(publish_dir, package)

    # ── Build to temp ──
    with tempfile.NamedTemporaryFile(suffix=".ankiaddon", delete=False) as tmp:
        tmp_path = tmp.name
    if not build_zip(tmp_path):
        os.unlink(tmp_path)
        return

    # ── Check existing target ──
    if os.path.isdir(target):
        existing_files = sum(len(f) for _, _, f in os.walk(target))
        print(f"\n⚠  Target already exists: {target}  ({existing_files} files)")
        answer = input(f"Overwrite and publish to this directory? [y/N] ").strip().lower()
        if answer != "y":
            print("Publish cancelled.")
            os.unlink(tmp_path)
            return
        # Second confirmation
        answer2 = input("Are you sure? Type 'yes' to confirm: ").strip().lower()
        if answer2 != "yes":
            print("Publish cancelled.")
            os.unlink(tmp_path)
            return
    else:
        print(f"\nPublishing to {target}")
        os.makedirs(target, exist_ok=True)

    # ── Extract ──
    with zipfile.ZipFile(tmp_path) as zf:
        zf.extractall(target)

    file_count = sum(len(f) for _, _, f in os.walk(target))
    print(f"Published  {target}  ({file_count} files)")
    os.unlink(tmp_path)


# ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    version = load_version()
    default_output = os.path.join(ROOT, "dist", f"anki_obsidian_sync-{version}.ankiaddon")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", "-o",
        default=default_output,
        help=f"Output .ankiaddon path (default: {default_output})",
    )
    parser.add_argument(
        "--publish", "-p",
        default=None,
        metavar="DIR",
        help="Publish (extract) the addon into DIR/<package>/  (e.g. path to Anki addons21 folder)",
    )
    args = parser.parse_args()

    if args.publish:
        publish(args.publish)
    else:
        build_zip(args.output)
