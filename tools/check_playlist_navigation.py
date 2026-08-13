"""Regression checks for CrowEyes 1.2 playlist selection and folder rows."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "CrowEyes_Image_Viewer_1.2.py"


def load_viewer_module():
    spec = importlib.util.spec_from_file_location("croweyes_v12_playlist_check", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.load_settings = lambda: {
        **module.DEFAULT_SETTINGS,
        "auto_register_associations": False,
        "list_mode": "icons",
    }
    return module


def main() -> None:
    module = load_viewer_module()
    with tempfile.TemporaryDirectory(prefix="croweyes-playlist-check-") as tmp:
        folder = Path(tmp)
        (folder / "A-folder").mkdir()
        (folder / "B-folder").mkdir()
        files = []
        for number in range(5):
            path = folder / f"image-{number + 1:02d}.png"
            Image.new("RGB", (32, 24), (40 + number * 20, 80, 120)).save(path)
            files.append(path)

        viewer = module.CrowEyesImageViewer()
        viewer.withdraw()
        viewer.current_folder = folder
        viewer.folder_files = files
        viewer.index = 0
        viewer.list_mode = "icons"
        viewer._list_mode_var.set("icons")
        viewer._rebuild_file_list_widget()
        viewer._populate_list_names_only()

        kinds = [kind for kind, _path, _idx in viewer._playlist_items]
        assert kinds[:3] == ["parent", "folder", "folder"], kinds
        assert kinds[3:] == ["image"] * 5, kinds

        viewer.goto_index = lambda *_args, **_kwargs: None
        viewer._queue_thumbs_priority = lambda: None
        viewer._playlist_selection = {0}
        viewer._selection_anchor = 0
        viewer._on_icon_click(SimpleNamespace(state=0x0001), 3)
        assert viewer._playlist_selection == {0, 1, 2, 3}
        viewer._on_playlist_button_release()
        viewer.update_idletasks()
        assert viewer._playlist_selection == {0, 1, 2, 3}

        # A plain press on an already selected item must preserve the set so
        # that starting a drag does not reduce it to one file.
        viewer._on_icon_click(SimpleNamespace(state=0), 2)
        assert viewer._playlist_selection == {0, 1, 2, 3}
        drag = viewer._drag_init_playlist(SimpleNamespace(), 2)
        assert drag is not None and len(drag[2]) == 4, drag

        # Rebuild a native list and ensure release restoration reselects every
        # image even if Tk temporarily painted only one row as selected.
        viewer.list_mode = "names"
        viewer._list_mode_var.set("names")
        viewer._rebuild_file_list_widget()
        viewer._populate_list_names_only()
        viewer._playlist_selection = {0, 1, 2, 3}
        viewer._selected_folder_path = None
        viewer._restore_playlist_selection_visuals()
        selected_rows = tuple(int(row) for row in viewer._list_widget.curselection())
        assert selected_rows == (3, 4, 5, 6), selected_rows

        navigated = []
        viewer.open_folders = lambda paths: navigated.extend(paths)
        viewer._search_var.set("temporary query")
        viewer._navigate_playlist_folder(folder / "A-folder")
        assert navigated == [folder / "A-folder"]
        assert viewer._search_var.get() == ""
        viewer.destroy()

    print("PASS: playlist multi-selection and folder navigation")


if __name__ == "__main__":
    main()
