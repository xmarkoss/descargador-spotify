"""
gui.py — Interfaz gráfica del Spotify Downloader v7.0
Usa customtkinter para una experiencia premium tipo aplicación de música.
"""

import os
import threading
from tkinter import filedialog
import customtkinter as ctk

# Motor de descarga (toda la lógica vive en engine.py)
from engine import SpotifyMetadata, Downloader, get_base_dir

# ──────────────────────────────────────────────
#  Tema: Spotify Dark Premium
# ──────────────────────────────────────────────
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

C_BG       = "#0D0D0D"
C_SURFACE  = "#161616"
C_SURFACE2 = "#1E1E1E"
C_ACCENT   = "#1DB954"
C_ACCENT2  = "#1ED760"
C_TEXT     = "#FFFFFF"
C_SUBTEXT  = "#B3B3B3"
C_OK       = "#1DB954"
C_ERROR    = "#FF4D4D"
C_BORDER   = "#2A2A2A"


# ══════════════════════════════════════════════════════════════════
#  INTERFAZ GRÁFICA PREMIUM
# ══════════════════════════════════════════════════════════════════
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Spotify Downloader")
        self.geometry("740x600")
        self.minsize(640, 520)
        self.configure(fg_color=C_BG)
        self.resizable(True, True)

        self._is_downloading = False
        self._stop_event: threading.Event | None = None
        self.download_path = os.path.join(get_base_dir(), "descargas")
        self._build_ui()
        self.iconbitmap("assets/icon.ico")

    # ── Construcción UI ────────────────────────────────────────────
    def _build_ui(self):
        # ─ Header ─────────────────────────────────────────────────
        header = ctk.CTkFrame(self, fg_color=C_SURFACE, corner_radius=0, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="  ♫  Spotify Downloader",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=C_ACCENT,
            fg_color="transparent",
        ).pack(side="left", padx=20)

        ctk.CTkLabel(
            header,
            text="v7.0 Sniper · MP3 320kbps · Sin API key",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=C_SUBTEXT,
            fg_color="transparent",
        ).pack(side="right", padx=20)

        # ─ Main content ───────────────────────────────────────────
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=20)

        # ─ URL Card ───────────────────────────────────────────────
        url_card = ctk.CTkFrame(
            content, fg_color=C_SURFACE, corner_radius=14,
            border_width=1, border_color=C_BORDER,
        )
        url_card.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            url_card,
            text="ENLACE DE SPOTIFY  —  track · álbum · playlist",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=C_SUBTEXT,
            fg_color="transparent",
        ).pack(anchor="w", padx=18, pady=(14, 4))

        entry_row = ctk.CTkFrame(url_card, fg_color="transparent")
        entry_row.pack(fill="x", padx=14, pady=(0, 14))

        self.entry = ctk.CTkEntry(
            entry_row,
            placeholder_text="https://open.spotify.com/track/...",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=44,
            corner_radius=10,
            fg_color=C_SURFACE2,
            border_color=C_BORDER,
            border_width=1,
            text_color=C_TEXT,
            placeholder_text_color=C_SUBTEXT,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.entry.bind("<Return>", lambda _: self.start_download_thread())

        self.btn = ctk.CTkButton(
            entry_row,
            text="  Descargar",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=44,
            width=130,
            corner_radius=10,
            fg_color=C_ACCENT,
            hover_color=C_ACCENT2,
            text_color="#000000",
            command=self.start_download_thread,
        )
        self.btn.pack(side="right", padx=(0, 8))

        self.stop_btn = ctk.CTkButton(
            entry_row,
            text="  ⏹ Stop",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=44,
            width=110,
            corner_radius=10,
            fg_color="#B91C1C",
            hover_color="#EF4444",
            text_color="#FFFFFF",
            command=self.stop_download,
        )
        # Se muestra solo durante la descarga
        self.stop_btn.pack_forget()

        # ─ Directory Row ──────────────────────────────────────────
        dir_row = ctk.CTkFrame(url_card, fg_color="transparent")
        dir_row.pack(fill="x", padx=14, pady=(0, 14))

        self.dir_entry = ctk.CTkEntry(
            dir_row,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            height=32,
            corner_radius=8,
            fg_color=C_SURFACE2,
            border_color=C_BORDER,
            border_width=1,
            text_color=C_SUBTEXT,
        )
        self.dir_entry.insert(0, self.download_path)
        self.dir_entry.configure(state="readonly")
        self.dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.dir_btn = ctk.CTkButton(
            dir_row,
            text="Cambiar Carpeta",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=32,
            width=130,
            corner_radius=8,
            fg_color=C_SURFACE2,
            hover_color=C_BORDER,
            text_color=C_TEXT,
            border_width=1,
            border_color=C_BORDER,
            command=self._choose_directory,
        )
        self.dir_btn.pack(side="right", padx=(0, 8))

        # ─ Progress ───────────────────────────────────────────────
        prog_frame = ctk.CTkFrame(content, fg_color="transparent")
        prog_frame.pack(fill="x", pady=(0, 10))

        self.status_label = ctk.CTkLabel(
            prog_frame,
            text="Esperando enlace...",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=C_SUBTEXT,
            fg_color="transparent",
        )
        self.status_label.pack(anchor="w", pady=(0, 4))

        self.progressbar = ctk.CTkProgressBar(
            prog_frame,
            height=6,
            corner_radius=4,
            fg_color=C_SURFACE2,
            progress_color=C_ACCENT,
            mode="determinate",
        )
        self.progressbar.set(0)
        self.progressbar.pack(fill="x")

        # ─ Log console ────────────────────────────────────────────
        log_header = ctk.CTkFrame(content, fg_color="transparent")
        log_header.pack(fill="x", pady=(16, 4))

        ctk.CTkLabel(
            log_header,
            text="REGISTRO DE ACTIVIDAD",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=C_SUBTEXT,
            fg_color="transparent",
        ).pack(side="left")

        ctk.CTkButton(
            log_header,
            text="Limpiar",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            height=24,
            width=60,
            corner_radius=6,
            fg_color=C_SURFACE2,
            hover_color=C_BORDER,
            text_color=C_SUBTEXT,
            command=self._clear_log,
        ).pack(side="right")

        self.textbox = ctk.CTkTextbox(
            content,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color=C_SURFACE,
            text_color=C_TEXT,
            corner_radius=12,
            border_width=1,
            border_color=C_BORDER,
            wrap="word",
            activate_scrollbars=True,
            scrollbar_button_color=C_SURFACE2,
            scrollbar_button_hover_color=C_BORDER,
        )
        self.textbox.pack(fill="both", expand=True)
        self.textbox.configure(state="disabled")

        self._log_intro()

    def _choose_directory(self):
        folder = filedialog.askdirectory(initialdir=self.download_path, title="Seleccionar Carpeta de Descargas")
        if folder:
            self.download_path = folder
            self.dir_entry.configure(state="normal")
            self.dir_entry.delete(0, "end")
            self.dir_entry.insert(0, self.download_path)
            self.dir_entry.configure(state="readonly")

    # ── Log helpers ────────────────────────────────────────────────
    def _log_intro(self):
        self._raw("  ♫  Spotify Downloader v7.0  — Sniper Edition\n", C_ACCENT)
        self._raw("  Soporta tracks, álbumes y playlists completas.\n", C_SUBTEXT)
        self._raw("  Sin API key · Sin cuenta premium · MP3 320kbps\n", C_SUBTEXT)
        self._raw("  ─────────────────────────────────────────────\n", C_BORDER)

    def _raw(self, text: str, _color=None):
        """Inserta texto en el log (customtkinter no soporta coloreo nativo por tags)."""
        self.textbox.configure(state="normal")
        self.textbox.insert("end", text)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def log_message(self, level: str, message: str):
        """Callback de log tipado — llamado desde el hilo de descarga."""
        PREFIX = {
            "info":  "  ›  ",
            "track": "  ♪  ",
            "ok":    "  ✔  ",
            "error": "  ✖  ",
            "warn":  "  ⚠  ",
            "done":  "  ★  ",
        }
        line = f"{PREFIX.get(level, '  ·  ')}{message}\n"
        # always schedule UI updates on the main thread
        self.after(0, lambda l=line: self._raw(l))

    def _clear_log(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("0.0", "end")
        self.textbox.configure(state="disabled")
        self._log_intro()

    # ── Progress ───────────────────────────────────────────────────
    def update_progress(self, current: int, total: int):
        if total == 0:
            return
        value = current / total
        self.after(0, lambda: self._set_progress(value, current, total))

    def _set_progress(self, value: float, current: int, total: int):
        self.progressbar.set(value)
        if value >= 1.0:
            self.status_label.configure(
                text=f"✔  Completado — {total} pista(s)", text_color=C_OK
            )
        elif value > 0:
            self.status_label.configure(
                text=f"Descargando {current}/{total}...", text_color=C_SUBTEXT
            )
        else:
            self.status_label.configure(text="Iniciando...", text_color=C_SUBTEXT)

    # ── Descarga ───────────────────────────────────────────────────
    def start_download_thread(self):
        if self._is_downloading:
            return

        url = self.entry.get().strip()
        if not url:
            self.log_message("warn", "Por favor, pega un enlace de Spotify.")
            return

        self._is_downloading = True
        self._stop_event = threading.Event()   # Event fresco en cada descarga

        self.btn.configure(state="disabled", text="  Descargando...", fg_color=C_BORDER)
        self.dir_btn.configure(state="disabled")
        # Mostrar botón Stop
        self.stop_btn.pack(side="right", padx=(0, 8))
        self.progressbar.set(0)
        self.status_label.configure(text="Conectando con Spotify...", text_color=C_SUBTEXT)

        stop_ev = self._stop_event   # Captura local para el hilo

        def task():
            try:
                meta   = SpotifyMetadata(log=self.log_message)
                tracks = meta.get_tracks(url)

                if not tracks:
                    self.log_message("error", "No se encontraron pistas. Verifica el enlace.")
                    return

                dl = Downloader(
                    download_path=self.download_path,
                    log=self.log_message,
                    progress=self.update_progress,
                    stop_event=stop_ev,
                )
                dl.download_all(tracks)

            finally:
                self.after(0, self._on_download_complete)

        threading.Thread(target=task, daemon=True).start()

    def stop_download(self):
        """Señaliza cancelación al hilo de descarga."""
        if self._stop_event:
            self._stop_event.set()
        self.stop_btn.configure(state="disabled", text="  Deteniendo...")
        self.status_label.configure(text="Deteniendo tras la pista actual...", text_color=C_ERROR)

    def _on_download_complete(self):
        self._is_downloading = False
        self._stop_event = None
        # Restaurar botón Descargar y ocultar Stop
        self.btn.configure(state="normal", text="  Descargar", fg_color=C_ACCENT)
        self.dir_btn.configure(state="normal")
        self.stop_btn.configure(state="normal", text="  ⏹ Stop")
        self.stop_btn.pack_forget()


# ──────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()