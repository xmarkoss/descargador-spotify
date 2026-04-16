"""
engine.py — Motor central del Spotify Downloader v7.0 "Sniper Edition"
========================================================================
Sin API key, sin cuenta premium, sin tokens duros.

Estrategia de metadatos (en cascada):
  1. oEmbed API  → Tracks individuales (rápido, sin auth)
  2. Embed Widget → __NEXT_DATA__  → Playlists / Álbumes / Tracks
  3. Spotify Partner API (anónima) → Fallback con paginación real

Estrategia de búsqueda en YouTube (precisión máxima):
  1. ytsearch10 con múltiples queries en cascada
  2. Score combinado: similitud de título+artista (difflib) + duración (±5s)
  3. Descarga la URL con mejor score, no el primer resultado ciego
"""
from __future__ import annotations

import os
import sys
import re
import json
import time
import difflib
import threading
from typing import Optional
import requests
import yt_dlp
from bs4 import BeautifulSoup


# ──────────────────────────────────────────────────────────────────
#  Resolución de rutas: funciona en desarrollo Y dentro del .exe
# ──────────────────────────────────────────────────────────────────

def get_base_dir() -> str:
    """
    Directorio base de la aplicación:
    - PyInstaller (.exe): carpeta donde está el ejecutable.
    - Desarrollo:        carpeta raíz del proyecto (un nivel arriba de src/).
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_ffmpeg_dir() -> str:
    """
    Carpeta que contiene ffmpeg.exe y ffprobe.exe:
    - PyInstaller/Portable: carpeta 'ffmpeg/bin' o 'ffmpeg' junto al ejecutable.
    - Fallback PyInstaller: sys._MEIPASS (carpeta temporal de extracción).
    - Desarrollo:  <proyecto>/ffmpeg/
    """
    base = get_base_dir()
    
    # Comprobar si ffmpeg.exe está en <base>/ffmpeg/bin
    ffmpeg_bin = os.path.join(base, 'ffmpeg', 'bin')
    if os.path.exists(os.path.join(ffmpeg_bin, 'ffmpeg.exe')):
        return ffmpeg_bin
        
    # Comprobar si ffmpeg.exe está directamente en <base>/ffmpeg
    ffmpeg_root = os.path.join(base, 'ffmpeg')
    if os.path.exists(os.path.join(ffmpeg_root, 'ffmpeg.exe')):
        return ffmpeg_root

    if getattr(sys, 'frozen', False):
        return sys._MEIPASS          # type: ignore[attr-defined]
    return os.path.join(base, 'ffmpeg')

# User-Agent de Chrome moderno para evitar bloqueos de Spotify
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


# ══════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════

def clean_filename(name: str) -> str:
    """Elimina caracteres inválidos en Windows/Linux."""
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.strip()[:180]  # Límite seguro de longitud


def _title_score(target: str, candidate: str) -> float:
    """Ratio de similitud entre dos strings (0-1)."""
    t = target.lower().strip()
    c = candidate.lower().strip()
    return difflib.SequenceMatcher(None, t, c).ratio()


def _duration_score(target_sec: Optional[float], candidate_sec: Optional[float],
                    tolerance: int = 8) -> float:
    """1.0 si la duración está dentro de ±tolerance segundos, 0.0 si no hay datos."""
    if target_sec is None or candidate_sec is None:
        return 0.5   # Neutro cuando no tenemos datos
    diff = abs(target_sec - candidate_sec)
    if diff <= tolerance:
        return 1.0 - (diff / (tolerance * 2))
    return 0.0


# ══════════════════════════════════════════════════════════════════
#  EXTRACTOR DE METADATOS DE SPOTIFY
# ══════════════════════════════════════════════════════════════════

class SpotifyMetadata:
    """Extrae tracks de cualquier URL de Spotify sin API key ni cuenta."""

    def __init__(self, log=print):
        self.log = log
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # ── Motor 1: oEmbed (tracks individuales, muy rápido) ──────────
    def _oembed(self, url: str) -> Optional[list[dict]]:
        try:
            r = self.session.get(
                f"https://open.spotify.com/oembed?url={url}", timeout=10
            )
            if r.status_code == 200:
                d = r.json()
                title  = d.get("title", "").strip()
                artist = d.get("author_name", "").strip()
                if title and artist:
                    return [{
                        "title":    title,
                        "artist":   artist,
                        "duration": None,
                        "filename": clean_filename(f"{title} - {artist}"),
                    }]
        except Exception:
            pass
        return None

    # ── Motor 2: Embed Widget + __NEXT_DATA__ ──────────────────────
    def _spider_json(self, data, found: list, seen: set):
        """Rastreador recursivo del JSON de Spotify."""
        if isinstance(data, dict):
            title  = data.get("title") or data.get("name")
            artist = data.get("subtitle") or data.get("artist")

            # Intenta extraer artista de la lista artists[]
            if not artist and isinstance(data.get("artists"), list):
                names = [a.get("name", "") for a in data["artists"] if a.get("name")]
                if names:
                    artist = ", ".join(names)

            uri = data.get("uri") or data.get("id", "")
            dur = data.get("duration") or data.get("duration_ms")
            if dur and dur > 1000:           # Viene en ms
                dur = dur / 1000.0
            elif dur and dur <= 1000:        # Ya en segundos
                dur = float(dur)
            else:
                dur = None

            if title and artist and uri and "track" in str(uri) and uri not in seen:
                seen.add(uri)
                found.append((str(title), str(artist), dur))

            for v in data.values():
                self._spider_json(v, found, seen)

        elif isinstance(data, list):
            for item in data:
                self._spider_json(item, found, seen)

    def _embed_widget(self, url: str) -> list[dict]:
        """Scrape del widget embed de Spotify (soporta playlists y álbumes completos)."""
        # Normaliza la URL al formato embed
        embed_url = re.sub(
            r"https://open\.spotify\.com/(intl-[a-z]{2,3}/)?",
            "https://open.spotify.com/embed/",
            url,
        )
        if "/embed/" not in embed_url:
            embed_url = url.replace("open.spotify.com/", "open.spotify.com/embed/")

        tracks: list[dict] = []
        try:
            r = self.session.get(embed_url, timeout=20)
            soup = BeautifulSoup(r.text, "html.parser")
            tag = soup.find("script", id="__NEXT_DATA__")
            if not tag:
                self.log("warn", "No se encontró __NEXT_DATA__ en el widget.")
                return tracks

            json_data = json.loads(tag.string)
            raw: list[tuple] = []
            self._spider_json(json_data, raw, set())

            for title, artist, dur in raw:
                tracks.append({
                    "title":    title,
                    "artist":   artist,
                    "duration": dur,
                    "filename": clean_filename(f"{title} - {artist}"),
                })
        except Exception as e:
            self.log("error", f"Error en embed widget: {e}")
        return tracks

    # ── Motor 3: Spotify Partner API (anónima, con paginación) ─────
    def _get_anon_token(self) -> Optional[str]:
        """Obtiene el token anónimo que usa el propio web player de Spotify."""
        try:
            r = self.session.get("https://open.spotify.com/", timeout=10)
            match = re.search(r'"accessToken":"([^"]+)"', r.text)
            if match:
                return match.group(1)
        except Exception:
            pass
        return None

    def _partner_api(self, url: str) -> list[dict]:
        """
        Usa la API interna de Spotify (partner/Pathfinder) para obtener
        la lista completa sin límite de canciones.
        """
        # Extrae el ID y tipo del link
        m = re.search(r"spotify\.com/(?:intl-[a-z]+/)?(?:embed/)?(playlist|album|track)/([A-Za-z0-9]+)", url)
        if not m:
            return []
        stype, sid = m.group(1), m.group(2)

        token = self._get_anon_token()
        if not token:
            self.log("warn", "No se pudo obtener token anónimo de Spotify.")
            return []

        api_headers = {**HEADERS, "Authorization": f"Bearer {token}"}
        tracks: list[dict] = []

        if stype == "track":
            try:
                r = requests.get(
                    f"https://api.spotify.com/v1/tracks/{sid}",
                    headers=api_headers, timeout=10
                )
                if r.status_code == 200:
                    d = r.json()
                    title  = d.get("name", "")
                    artist = ", ".join(a["name"] for a in d.get("artists", []))
                    dur    = d.get("duration_ms", 0) / 1000
                    tracks.append({
                        "title": title, "artist": artist,
                        "duration": dur,
                        "filename": clean_filename(f"{title} - {artist}"),
                    })
            except Exception as e:
                self.log("error", f"Partner API (track): {e}")

        elif stype in ("playlist", "album"):
            # Paginación para playlists/álbumes grandes
            endpoint = (
                f"https://api.spotify.com/v1/playlists/{sid}/tracks?limit=100&offset=0"
                if stype == "playlist"
                else f"https://api.spotify.com/v1/albums/{sid}/tracks?limit=50&offset=0"
            )
            while endpoint:
                try:
                    r = requests.get(endpoint, headers=api_headers, timeout=15)
                    if r.status_code != 200:
                        break
                    data = r.json()
                    items = data.get("items", [])
                    for item in items:
                        t = item.get("track") or item  # álbum vs playlist structure
                        if not t or t.get("is_local"):
                            continue
                        title  = t.get("name", "")
                        artist = ", ".join(a["name"] for a in t.get("artists", []))
                        dur    = t.get("duration_ms", 0) / 1000
                        if title and artist:
                            tracks.append({
                                "title": title, "artist": artist,
                                "duration": dur,
                                "filename": clean_filename(f"{title} - {artist}"),
                            })
                    endpoint = data.get("next")  # None cuando no hay más páginas
                    if endpoint:
                        time.sleep(0.3)  # Respeta rate limits
                except Exception as e:
                    self.log("error", f"Partner API (paginación): {e}")
                    break

        return tracks

    # ── Enrutador principal ─────────────────────────────────────────
    def get_tracks(self, url: str) -> list[dict]:
        """
        Intenta extraer metadata en cascada:
        oEmbed → embed widget → Partner API anónima
        """
        url = url.strip().split("?")[0]

        # -- Tracks individuales: oEmbed es suficiente y muy rápido --
        if "/track/" in url:
            result = self._oembed(url)
            if result:
                self.log("info", f"Track identificado: {result[0]['title']} — {result[0]['artist']}")
                return result

        # -- Playlists / Álbumes (o track si oEmbed falló) --
        self.log("info", "Extrayendo metadata desde el motor de Widgets...")
        tracks = self._embed_widget(url)

        if not tracks:
            self.log("warn", "Widget vacío, probando Partner API anónima...")
            tracks = self._partner_api(url)

        if tracks:
            self.log("info", f"Se encontraron {len(tracks)} pistas.")
        return tracks


# ══════════════════════════════════════════════════════════════════
#  BÚSQUEDA EN YOUTUBE CON EXACTITUD MÁXIMA
# ══════════════════════════════════════════════════════════════════

class YouTubeSniper:
    """
    Encuentra la URL de YouTube más exacta para un par título+artista,
    usando puntuación combinada de similitud textual y duración.
    """

    # Queries en orden de precisión (se prueba de arriba a abajo)
    _QUERY_TEMPLATES = [
        "{artist} - {title} (Official Audio)",
        "{artist} {title} provided to youtube",
        "{artist} {title} official audio",
        "{artist} {title} audio",
        "{title} {artist}",
    ]

    def __init__(self, log=print):
        self.log = log
        self._ydl_search_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
        }

    def find(self, title: str, artist: str, duration_sec: Optional[float] = None) -> str:
        """
        Devuelve la URL de YouTube con mayor score para el track dado.
        Fallback: `ytsearch1:{title} {artist}` si todo falla.
        """
        target_text = f"{title} {artist}"
        best_url: str | None = None
        best_score: float = -1.0
        MIN_SCORE = 0.40   # Umbral mínimo para aceptar un resultado

        for template in self._QUERY_TEMPLATES:
            query = template.format(title=title, artist=artist)
            candidates = self._search(query, n=10)

            for entry in candidates:
                yt_title = entry.get("title", "")
                yt_dur   = entry.get("duration")  # segundos (puede ser None)
                url      = entry.get("webpage_url") or entry.get("url", "")

                if not url:
                    continue

                t_score = _title_score(target_text, yt_title)
                d_score = _duration_score(duration_sec, yt_dur)

                # Peso: 70% texto, 30% duración
                score = t_score * 0.70 + d_score * 0.30

                if score > best_score:
                    best_score = score
                    best_url = url

            # Si ya tenemos algo bueno, no seguimos probando queries
            if best_score >= MIN_SCORE and best_url:
                break

        if best_url and best_score >= MIN_SCORE:
            return best_url

        # Fallback ciego
        return f"ytsearch1:{title} {artist}"

    def _search(self, query: str, n: int = 10) -> list[dict]:
        try:
            with yt_dlp.YoutubeDL(self._ydl_search_opts) as ydl:
                info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
            return info.get("entries", []) if info else []
        except Exception:
            return []


# ══════════════════════════════════════════════════════════════════
#  MOTOR DE DESCARGA
# ══════════════════════════════════════════════════════════════════

class Downloader:
    """Descarga una lista de tracks a MP3 320kbps con portada y metadatos."""

    def __init__(self, download_path: str = "",
                 log=print, progress=None,
                 stop_event: Optional[threading.Event] = None):
        # Si no se especifica ruta, usa <base>/descargas
        self.download_path = download_path or os.path.join(get_base_dir(), 'descargas')
        self.log = log
        self.progress = progress or (lambda current, total: None)
        self.stop_event = stop_event
        self.sniper = YouTubeSniper(log=log)
        os.makedirs(self.download_path, exist_ok=True)

    def download_all(self, tracks: list[dict]):
        total = len(tracks)
        if total == 0:
            self.log("error", "No hay pistas para descargar.")
            return

        self.log("info", f"Iniciando descarga de {total} pista(s)...")

        for i, track in enumerate(tracks, 1):

            # ── Verificar señal de cancelación ANTES de cada pista ──
            if self.stop_event and self.stop_event.is_set():
                self.log("warn", f"Descarga detenida por el usuario ({i-1}/{total} completadas).")
                self.progress(i - 1, total)
                return

            title    = track["title"]
            artist   = track["artist"]
            duration = track.get("duration")
            filename = track["filename"]

            self.log("track", f"[{i}/{total}]  {filename}")
            self.progress(i - 1, total)

            # ── Buscar URL exacta en YouTube ──
            self.log("info", f"Buscando en YouTube: {title} — {artist}...")
            yt_url = self.sniper.find(title, artist, duration)

            # ── Verificar de nuevo después de la búsqueda (puede tardar) ──
            if self.stop_event and self.stop_event.is_set():
                self.log("warn", f"Descarga detenida por el usuario ({i-1}/{total} completadas).")
                self.progress(i - 1, total)
                return

            # ── Descargar y convertir ──
            out_path = os.path.join(self.download_path, f"{filename}.%(ext)s")
            ydl_opts = {
                "format":           "bestaudio/best",
                "outtmpl":          out_path,
                "writethumbnail":   True,
                "quiet":            True,
                "no_warnings":      True,
                # FFmpeg resuelto para dev y para .exe empaquetado
                "ffmpeg_location":  get_ffmpeg_dir(),
                "postprocessors":   [
                    {
                        "key":              "FFmpegExtractAudio",
                        "preferredcodec":   "mp3",
                        "preferredquality": "320",
                    },
                    {"key": "EmbedThumbnail"},
                    {"key": "FFmpegMetadata"},
                ],
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([yt_url])
                self.log("ok", f"Guardado → {filename}.mp3")
            except Exception as e:
                self.log("error", f"Error descargando '{filename}': {e}")

            self.progress(i, total)

        self.log("done", f"¡PROCESO FINALIZADO! {total} pista(s) en /{self.download_path}")
        self.progress(total, total)
