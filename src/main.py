"""
main.py — CLI del Spotify Downloader v7.0 "Sniper Edition"
Usa: python src/main.py
"""
import sys
from engine import SpotifyMetadata, Downloader


def cli_log(level: str, message: str):
    prefix = {
        "info":  "[*]",
        "track": "[♪]",
        "ok":    "[✔]",
        "error": "[✖]",
        "warn":  "[!]",
        "done":  "[★]",
    }.get(level, "[-]")
    print(f"{prefix} {message}")


def cli_progress(current: int, total: int):
    if total == 0:
        return
    pct = int((current / total) * 100)
    bar = ("█" * (pct // 5)).ljust(20)
    print(f"\r    [{bar}] {pct}%  ({current}/{total})", end="", flush=True)
    if current == total:
        print()


if __name__ == "__main__":
    print("=" * 47)
    print("   SPOTIFY DOWNLOADER v7.0  — Sniper Edition")
    print("   (Sin API key · MP3 320kbps · Playlists completas)")
    print("=" * 47)
    print()

    if len(sys.argv) > 1:
        url = sys.argv[1].strip()
    else:
        url = input("Pega tu enlace de Spotify: ").strip().split("?")[0]

    if not url:
        print("[✖] No se proporcionó un enlace.")
        sys.exit(1)

    meta      = SpotifyMetadata(log=cli_log)
    tracks    = meta.get_tracks(url)

    if not tracks:
        print("[✖] No se encontraron pistas. Verifica el enlace.")
        sys.exit(1)

    downloader = Downloader(log=cli_log, progress=cli_progress)
    downloader.download_all(tracks)