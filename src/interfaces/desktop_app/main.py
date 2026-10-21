"""A tiny desktop GUI: drag a file onto the window (or click to browse) and
it gets ingested into Qdrant via rag_core.Ingester -- the drag-and-drop
counterpart to `python -m rag_core.ingest`, for someone who'd rather not use
a terminal. Same module-boundary rule as every other interface (see
agents.md): this file owns the window and the file dialog; everything
about turning a file into indexed chunks lives in rag_core.

Run directly:
    pip install -e ".[desktop]"
    python -m interfaces.desktop_app.main

Package as a single executable (see README's "Desktop app" section for the
full command and per-OS notes):
    pyinstaller --onefile --windowed --name rag-system-ingest \
        src/interfaces/desktop_app/main.py

Drag-and-drop needs the optional `tkinterdnd2` package. If it isn't
installed, the window still opens and still works -- clicking the drop
zone falls back to a normal file-picker dialog instead of silently
breaking the whole app over one optional dependency.
"""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from rag_core.errors import RagCoreError
from rag_core.ingest import Ingester
from rag_core.logging_config import configure_logging

logger = logging.getLogger(__name__)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    _DND_AVAILABLE = True
except ImportError:
    _DND_AVAILABLE = False


IDLE_TEXT = "Drag a file here\n(or click to browse)"


class IngestApp:
    def __init__(self, root: tk.Misc) -> None:
        self._root = root
        self._root.title("rag_system: ingest a file")
        self._root.geometry("420x260")
        self._root.resizable(False, False)

        # Events flow: a background thread does the (slow) ingest and puts
        # a result on this queue; the Tk mainloop polls it, so the window
        # never freezes and nothing touches Tk widgets off the main thread.
        self._results: queue.Queue[tuple[str, str]] = queue.Queue()
        self._busy = False

        self._drop_zone = tk.Label(
            root,
            text=IDLE_TEXT,
            width=40,
            height=8,
            relief="groove",
            borderwidth=2,
            bg="#f4f4f6",
            fg="#333333",
            font=("Helvetica", 13),
            cursor="hand2",
        )
        self._drop_zone.pack(padx=16, pady=16, fill="both", expand=True)
        self._drop_zone.bind("<Button-1>", lambda _event: self._browse())

        self._status = tk.Label(root, text="", fg="#555555", wraplength=380, justify="left")
        self._status.pack(padx=16, pady=(0, 16), fill="x")

        if _DND_AVAILABLE:
            self._drop_zone.drop_target_register(DND_FILES)
            self._drop_zone.dnd_bind("<<Drop>>", self._on_drop)
        else:
            self._set_status("Drag-and-drop isn't available (tkinterdnd2 not installed). Click to browse instead.")

        self._poll_results()

    def _browse(self) -> None:
        if self._busy:
            return
        path = filedialog.askopenfilename(title="Choose a file to ingest")
        if path:
            self._start_ingest(Path(path))

    def _on_drop(self, event) -> None:
        if self._busy:
            return
        # event.data can contain multiple paths, brace-quoted if they have
        # spaces (e.g. "{/a/b.txt} {/c/d.txt}"); only the first file is
        # ingested -- one drop, one file, matching ingest_file's contract.
        raw = event.data.strip()
        first = raw.split("} {")[0].strip("{}") if raw.startswith("{") else raw.split()[0]
        self._start_ingest(Path(first))

    def _start_ingest(self, path: Path) -> None:
        self._busy = True
        self._drop_zone.config(text=f"Ingesting…\n{path.name}", bg="#eef6ff")
        self._set_status("")
        threading.Thread(target=self._ingest_worker, args=(path,), daemon=True).start()

    def _ingest_worker(self, path: Path) -> None:
        try:
            count = Ingester().ingest_file(path)
            self._results.put(("ok", f"Indexed {count} chunk(s) from '{path.name}'."))
        except ValueError as exc:
            self._results.put(("error", str(exc)))
        except RagCoreError as exc:
            logger.exception("Ingestion failed for %s", path)
            self._results.put(("error", f"Ingestion failed: {exc}"))
        except OSError as exc:
            self._results.put(("error", f"Couldn't read '{path.name}': {exc}"))

    def _poll_results(self) -> None:
        try:
            level, message = self._results.get_nowait()
        except queue.Empty:
            pass
        else:
            self._busy = False
            self._drop_zone.config(text=IDLE_TEXT, bg="#f4f4f6")
            self._set_status(message)
            if level == "error":
                messagebox.showerror("Ingestion failed", message)
        self._root.after(150, self._poll_results)

    def _set_status(self, message: str) -> None:
        self._status.config(text=message)


def main() -> None:
    configure_logging()
    root = TkinterDnD.Tk() if _DND_AVAILABLE else tk.Tk()
    IngestApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
