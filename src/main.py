import os
import requests
import yt_dlp
import re
import json
from bs4 import BeautifulSoup

class SpotifyMasterSuite:
    def __init__(self):
        self.download_path = 'descargas'
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def clean_filename(self, name):
        """Limpia caracteres inválidos en Windows/Linux"""
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    def get_track_oembed(self, url):
        """Extrae metadata de una sola canción vía oEmbed."""
        oembed_url = f"https://open.spotify.com/oembed?url={url}"
        try:
            response = requests.get(oembed_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                title = data.get('title', '')
                author = data.get('author_name', '')
                
                clean_name = self.clean_filename(f"{title} - {author}")
                search_query = f"{title} {author} provided to youtube"
                return [{'filename': clean_name, 'search': search_query}]
        except:
            pass
        return []

    def _spider_json(self, data, tracks_list, seen_uris):
        """Araña recursiva: Navega por cualquier JSON buscando canciones"""
        if isinstance(data, dict):
            # Una canción en el JSON de Spotify siempre tiene title, subtitle y uri
            if 'title' in data and 'subtitle' in data and 'uri' in data:
                uri = data['uri']
                if uri not in seen_uris and 'track' in uri:
                    tracks_list.append((data['title'], data['subtitle']))
                    seen_uris.add(uri)
            for val in data.values():
                self._spider_json(val, tracks_list, seen_uris)
        elif isinstance(data, list):
            for item in data:
                self._spider_json(item, tracks_list, seen_uris)

    def get_playlist_embed(self, url):
        """Extrae la playlist engañando a Spotify con la vista de Widget"""
        print("[*] Desactivando DRM: Extrayendo metadata desde el motor de Widgets...")
        tracks = []
        
        # Convertimos el link normal en un link de widget
        embed_url = url.replace("open.spotify.com/", "open.spotify.com/embed/")
        
        try:
            res = requests.get(embed_url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Spotify esconde toda la data de la playlist en este script
            script_tag = soup.find('script', id='__NEXT_DATA__')
            if script_tag:
                json_data = json.loads(script_tag.string)
                
                raw_tracks = []
                # Lanzamos la araña para buscar las canciones donde sea que estén escondidas
                self._spider_json(json_data, raw_tracks, set())
                
                for title, artist in raw_tracks:
                    raw_name = f"{title} - {artist}"
                    clean_name = self.clean_filename(raw_name)
                    search_query = f"{title} {artist} provided to youtube"
                    tracks.append({'filename': clean_name, 'search': search_query})
            else:
                print("[-] Bloqueo de seguridad: No se encontró la estructura de datos.")
        except Exception as e:
            print(f"[-] Error en el extractor de Playlists: {e}")
            
        return tracks

    def analyze_url(self, url):
        """Enrutador Inteligente"""
        print("[*] Analizando arquitectura del enlace...")
        if "/track/" in url:
            return self.get_track_oembed(url)
        elif "/playlist/" in url or "/album/" in url:
            return self.get_playlist_embed(url)
        else:
            print("[-] Formato de enlace no soportado.")
            return []

    def download_batch(self, tracks):
        """Motor de descarga iterativo."""
        if not tracks:
            print("\n[X] No se encontraron pistas.")
            return False

        print(f"\n[+] ÉXITO: Se desencriptaron {len(tracks)} pistas. Iniciando descarga masiva...")
        print("    (Usa Ctrl+C para cancelar)\n")

        for i, track in enumerate(tracks, 1):
            print(f"[{i}/{len(tracks)}] Descargando: {track['filename']}")
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': f'{self.download_path}/{track["filename"]}.%(ext)s',
                'writethumbnail': True,
                'postprocessors': [
                    {'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'},
                    {'key': 'EmbedThumbnail'},
                    {'key': 'FFmpegMetadata'}
                ],
                'quiet': True,
                'no_warnings': True
            }

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([f"ytsearch1:{track['search']}"])
                print(f"    [OK] Guardado con portada.")
            except Exception as e:
                print(f"    [X] Error en esta pista (Saltando a la siguiente)...")

        return True

if __name__ == "__main__":
    print("=======================================")
    print("   SPOTIFY MASTER SUITE v6.0")
    print("   (Bypass DRM / Extractor de Playlists)")
    print("=======================================")
    
    # Resolvemos posibles links cortos
    url = input("Pega tu enlace de Spotify: ").strip().split('?')[0]
    
    app = SpotifyMasterSuite()
    lista_tareas = app.analyze_url(url)
    
    if app.download_batch(lista_tareas):
        print("\n[✔] ¡PROCESO FINALIZADO! Revisa tu carpeta de descargas.")