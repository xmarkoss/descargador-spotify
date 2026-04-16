"""
make_icon.py — Convierte cualquier imagen a icon.ico listo para el .exe
=======================================================================
Uso:
    venv\Scripts\python.exe make_icon.py                    <- usa assets/logo.png por defecto
    venv\Scripts\python.exe make_icon.py assets/mi_imagen.png
    venv\Scripts\python.exe make_icon.py assets/foto.jpg
"""

import sys
import os
from PIL import Image

# ── Imagen fuente ─────────────────────────────────────────────────
if len(sys.argv) > 1:
    src_path = sys.argv[1]
else:
    # Busca automáticamente la primera imagen en assets/ (que no sea icon.ico)
    assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
    candidates = [
        f for f in os.listdir(assets_dir)
        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp'))
    ]
    if not candidates:
        print("[!] No se encontró ninguna imagen en assets/")
        print("    Pon tu imagen (.png, .jpg, .webp) en la carpeta assets/ e inténtalo de nuevo.")
        sys.exit(1)
    src_path = os.path.join(assets_dir, candidates[0])

out_path = os.path.join(os.path.dirname(__file__), 'assets', 'icon.ico')

# ── Conversión ────────────────────────────────────────────────────
print(f"  Imagen fuente : {src_path}")
print(f"  Destino       : {out_path}")

try:
    img = Image.open(src_path).convert("RGBA")

    # Recorta al cuadrado centrado si la imagen no es cuadrada
    w, h = img.size
    if w != h:
        side = min(w, h)
        left = (w - side) // 2
        top  = (h - side) // 2
        img  = img.crop((left, top, left + side, top + side))
        print(f"  Recortada a   : {side}x{side}px (centrado automático)")

    img.save(
        out_path,
        format='ICO',
        sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    )
    size_kb = os.path.getsize(out_path) // 1024
    print(f"\n  [OK] icon.ico generado ({size_kb} KB) con 6 resoluciones.")
    print(f"       Listo para usar en el .exe y en Inno Setup.\n")

except FileNotFoundError:
    print(f"[!] No se encontró el archivo: {src_path}")
    sys.exit(1)
except Exception as e:
    print(f"[!] Error al convertir la imagen: {e}")
    sys.exit(1)
