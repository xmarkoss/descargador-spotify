import os
import requests
import yt_dlp
import re

class UltimateSpotifyDownloader:
    def __init__(self):
        self.download_path = 'descargas'
        if not os.path.exists(self.download_path):
            os.makedirs(self.download_path)

    def clean_filename(self, name):
        """Evita errores al guardar archivos en Windows"""
        return re.sub(r'[\\/*?:"<>|]', "", name).strip()

    def get_metadata_oembed(self, url):
        """Extrae el título y artista 100% real de Spotify."""
        oembed_url = f"https://open.spotify.com/oembed?url={url}"
        try:
            response = requests.get(oembed_url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                title = data.get('title', '')
                author = data.get('author_name', '')
                
                # Devolvemos el nombre limpio para el archivo y el string de búsqueda
                clean_name = self.clean_filename(f"{title} - {author}")
                # El truco: "provided to youtube" filtra covers y directos.
                search_query = f"{title} {author} provided to youtube" 
                
                return clean_name, search_query
            else:
                return None, None
        except Exception as e:
            print(f"[-] Error conectando a oEmbed: {e}")
            return None, None

    def download(self, spotify_url):
        print("[*] 1. Extrayendo metadatos a través de oEmbed...")
        file_name, search_query = self.get_metadata_oembed(spotify_url)
        
        if not search_query:
            print("[-] No se pudo descifrar el nombre.")
            return False

        print(f"[+] Canción detectada: {file_name}")
        print("[*] 2. Ejecutando búsqueda de precisión (Sniper Search)...")

        ydl_opts = {
            'format': 'bestaudio/best',
            # Nombramos el archivo con la info pura de Spotify
            'outtmpl': f'{self.download_path}/{file_name}.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }, {
                'key': 'FFmpegMetadata',
            }],
            'quiet': True,
            'no_warnings': True
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Volvemos a ytsearch1 pero con la consulta blindada
                ydl.download([f"ytsearch1:{search_query}"])
            return True
        except Exception as e:
            print(f"[-] Error en el motor de descarga: {e}")
            return False

if __name__ == "__main__":
    print("=======================================")
    print("   SPOTIFY ULTIMATE DOWNLOADER v3.2")
    print("=======================================")
    url = input("Pega el enlace de Spotify: ").strip().split('?')[0]
    
    bot = UltimateSpotifyDownloader()
    
    if bot.download(url):
        print("\n[OK] ¡Descarga física completada! Revisa la carpeta 'descargas'.")
    else:
        print("\n[X] Error en el proceso.")