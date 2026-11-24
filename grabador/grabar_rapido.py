"""Grabador del panel (2026-11-15, acelerado 2026-11-19): primero GPU (WebCodecs dentro de la pagina; el codificador del navegador es POR SOFTWARE y usa 1 nucleo por trabajador, por eso varios trabajadores en paralelo escalan);
si falla reintenta con menos trabajadores y solo al final cae al paralelo de respaldo. Uso igual que grab_paralelo: python grabar_rapido.py CARPETA SEED [--tag T]
Medido (RTX 2060, Ryzen 5 5600X, 30 s de video 1080p): 1 trabajador 71 s · 2 trabajadores 48 s · 3 trabajadores 45 s (≈0,55 GB de RAM c/u) · 4 trabajadores FALLA -> tope 3.
Variables: GRAB_WORKERS (fuerza el numero), GRAB_FPS, GRAB_MBPS (borrador rapido: p. ej. 20 fps y 8 Mbps)."""
import os, sys, ctypes, subprocess, pathlib
D = pathlib.Path(__file__).parent; a = sys.argv[1:]
class _MS(ctypes.Structure):
    _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong), ("tpf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ae", ctypes.c_ulonglong)]
def ram_libre_gb():
    try: m = _MS(); m.l = ctypes.sizeof(_MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); return m.ap / 2 ** 30
    except Exception: return 2.0
def elegir_trabajadores():
    if os.environ.get("GRAB_WORKERS"): return max(1, min(3, int(os.environ["GRAB_WORKERS"])))
    libre = ram_libre_gb(); w = 3 if libre >= 3.0 else 2 if libre >= 1.8 else 1
    print("RAM libre %.1f GB -> %d trabajadores de grabacion" % (libre, w), flush=True); return w
extra = ["--fps", os.environ.get("GRAB_FPS", "30"), "--mbps", os.environ.get("GRAB_MBPS", "20")]
w = elegir_trabajadores(); r = None
if os.environ.get("GRAB_MODO") == "pagina":   # páginas con HUD en HTML (no solo canvas): se graba la PÁGINA entera (capturas) en trozos paralelos; el GPU/WebCodecs solo copia canvas
    r = subprocess.run([sys.executable, "-u", str(D / "grab_paralelo.py")] + a + ["--workers", str(w), "--fps", os.environ.get("GRAB_FPS", "30")])
    sys.exit(r.returncode)
while w >= 1:
    r = subprocess.run([sys.executable, "-u", str(D / "grab_gpu.py")] + a + ["--workers", str(w)] + extra)
    if r.returncode == 0: sys.exit(0)
    print("grab_gpu fallo con %d trabajadores (codigo %d)" % (w, r.returncode), flush=True); w -= 1
print("grab_gpu fallo siempre: uso el grabador paralelo de respaldo", flush=True)
r = subprocess.run([sys.executable, "-u", str(D / "grab_paralelo.py")] + a + ["--workers", "3"])
sys.exit(r.returncode)
