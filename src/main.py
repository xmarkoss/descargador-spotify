import os
import requests
import yt_dlp
import re

class UltimateSpotifyDownloader:
    def __init__(self):
        self.download_path = 'descargas'
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def get_metadata_oembed(self, url):
        """Usa el endpoint público oEmbed de Spotify para obtener metadatos sin bloqueos."""
        # Esta es la 'puerta trasera' legal y gratuita
        oembed_url = f"https://open.spotify.com/oembed?url={url}"
        try:
            response = requests.get(oembed_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                title = data.get('title', '')
                author = data.get('author_name', '')
                
                # Formateamos la búsqueda: "Título Artista"
                search_query = f"{title} {author}".strip()
                return search_query
            else:
                return None
        except Exception as e:
            print(f"[-] Error conectando a oEmbed: {e}")
            return None

    def download(self, spotify_url):
        print("[*] 1. Extrayendo metadatos a través de oEmbed...")
        search_query = self.get_metadata_oembed(spotify_url)
        
        if not search_query:
            print("[-] No se pudo descifrar el nombre. ¿Es un enlace válido y público?")
            return False

        print(f"[+] Canción detectada: {search_query}")
        print("[*] 2. Buscando audio de alta calidad en servidores públicos...")

        # Configuramos yt-dlp para descargar silenciosamente
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f'{self.download_path}/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }, {
                'key': 'FFmpegMetadata',
            }],
            'quiet': True,       # Oculta la basura técnica de la consola
            'no_warnings': True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # ytsearch1: busca el query y baja el PRIMER resultado
                ydl.download([f"ytsearch1:{search_query} official audio"])
            return True
        except Exception as e:
            print(f"[-] Error en el motor de descarga: {e}")
            return False

if __name__ == "__main__":
    print("=======================================")
    print("   SPOTIFY ULTIMATE DOWNLOADER v3.0")
    print("=======================================")
    url = input("Pega el enlace de Spotify: ").strip().split('?')[0]
    
    bot = UltimateSpotifyDownloader()
    
    if bot.download(url):
        print("\n[OK] ¡Descarga física completada! Revisa la carpeta 'descargas'.")
    else:
        print("\n[X] Error en el proceso.")