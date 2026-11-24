"""REQUISITOS del DevPanel: revisa que el equipo tenga todo lo que el panel necesita ANTES de abrirlo y dice, en palabras sencillas, qué falta y cómo arreglarlo.
Uso:  python requisitos.py            (informe legible; código de salida 0 = todo lo OBLIGATORIO está listo, 1 = falta algo)
      python requisitos.py --json     (lo mismo como JSON, para que lo lea el panel o Claude)
Niveles: OBLIGATORIO (sin esto el panel no sirve) · NECESARIO PARA VOZ/VIDEO (sin esto se abre, pero no se puede hacer voz o grabar) · OPCIONAL (aviso)."""
import sys, os, json, glob, shutil, pathlib, subprocess, importlib.util, urllib.request, socket
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
AQUI = pathlib.Path(__file__).resolve().parent
CFG = {}
try: CFG = json.loads((AQUI / "devpanel.json").read_text(encoding="utf-8"))
except Exception: pass
def _vs_auto():   # dónde está Voice Studio si no se dijo en devpanel.json -> "voice_studio_dir" (sin rutas de nadie): variable VOICESTUDIO_DIR o sitios habituales
    import os
    for b in (os.environ.get("VOICESTUDIO_DIR"), os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "VoiceStudio"), os.path.join(os.environ.get("ProgramFiles", ""), "VoiceStudio"), os.path.join(os.path.expanduser("~"), "VoiceStudio")):
        if b:
            for sub in ("project", ""):
                p = pathlib.Path(b) / sub if sub else pathlib.Path(b)
                if (p / ".venv").exists() or (p / "data").exists(): return p
    return pathlib.Path(os.path.expanduser("~")) / "VoiceStudio" / "project"
VS_DEF = str(_vs_auto())
R = []   # {nivel, nombre, ok, detalle, arreglo}
def item(nivel, nombre, ok, detalle="", arreglo=""): R.append({"nivel": nivel, "nombre": nombre, "ok": bool(ok), "detalle": detalle, "arreglo": arreglo})
def tiene(mod): return importlib.util.find_spec(mod) is not None

# 1) Python
v = sys.version_info
item("OBLIGATORIO", "Python 3.10 o superior", v >= (3, 10), "tienes %d.%d.%d" % v[:3], "Instala Python 3.10+ desde python.org (marca «Add Python to PATH») y vuelve a ejecutar instalar.bat")
# 2) paquetes
for mod, pip in (("playwright", "playwright"), ("PIL", "pillow"), ("numpy", "numpy"), ("imageio_ffmpeg", "imageio-ffmpeg")):
    item("OBLIGATORIO", "Paquete de Python «%s»" % pip, tiene(mod), "instalado" if tiene(mod) else "falta", "Ejecuta:  python instalar.py --instalar-paquetes")
# 3) Chromium del grabador
chromium = glob.glob(os.path.join(os.environ.get("LOCALAPPDATA", ""), "ms-playwright", "chromium-*")) + glob.glob(os.path.join(os.path.expanduser("~"), ".cache", "ms-playwright", "chromium-*"))
item("NECESARIO PARA VOZ/VIDEO", "Navegador Chromium del grabador", bool(chromium), "encontrado" if chromium else "falta", "Ejecuta:  python -m playwright install chromium   (o  python instalar.py --instalar-paquetes)")
# 4) tarjeta de video
gpu = ""
try: gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=8).stdout.strip().splitlines()[0]
except Exception: pass
mb = 0
try: mb = int(gpu.split(",")[-1].strip().split()[0]) if gpu else 0
except Exception: pass
item("NECESARIO PARA VOZ/VIDEO", "Tarjeta de video NVIDIA (para la voz y el grabador rápido)", bool(gpu), gpu or "no se detecta nvidia-smi", "Instala los drivers de NVIDIA. Sin tarjeta NVIDIA la voz no funciona y la grabación va por procesador (mucho más lenta).")
if gpu and mb < 5000: item("OPCIONAL", "Memoria de la tarjeta de video", False, "%d MB: la voz usa unos 5 GB; puede quedarse corta" % mb, "Cierra otros programas que usen la tarjeta antes de generar la voz.")
# 5) Voice Studio
vs = pathlib.Path(CFG.get("voice_studio_dir") or VS_DEF)
vs_ok = (vs / ".venv" / "Scripts" / "python.exe").exists() and (vs / "backend").exists()
item("NECESARIO PARA VOZ/VIDEO", "Voice Studio instalado", vs_ok, str(vs) if vs_ok else "no está en: %s" % vs,
     "Instala Voice Studio y escribe su carpeta («project», la que tiene backend y .venv) en devpanel.json:  \"voice_studio_dir\": \"C:\\\\...\\\\VoiceStudio\\\\project\"")
up = False
try: urllib.request.urlopen("http://127.0.0.1:3900/health", timeout=2); up = True
except Exception: pass
item("OPCIONAL", "Voice Studio encendido (puerto 3900)", up, "responde" if up else "apagado: el panel lo enciende solo al generar voz si está instalado", "Si no enciende solo, ábrelo a mano y repite.")
# 6) puerto del panel
puerto = int(CFG.get("puerto") or 8820)
s = socket.socket(); s.settimeout(1)
ocupado = s.connect_ex(("127.0.0.1", puerto)) == 0; s.close()
item("OPCIONAL", "Puerto %d del panel" % puerto, True, "ya hay un panel encendido ahí" if ocupado else "libre")
# 7) datos del usuario
mus = [pathlib.Path(p) for p in glob.glob(str(AQUI.parent / "musica_fondo" / "*.mp3"))]
item("OPCIONAL", "Música de fondo", bool(mus), "%d archivo(s) en musica_fondo" % len(mus) if mus else "ninguna", "Se elige en Plugins → Ajustes del plugin (música de fondo). Sin música el video sale solo con voz y efectos.")

falta_ob = [x for x in R if x["nivel"] == "OBLIGATORIO" and not x["ok"]]
falta_vz = [x for x in R if x["nivel"].startswith("NECESARIO") and not x["ok"]]
listo = not falta_ob
if "--json" in sys.argv:
    print(json.dumps({"listo": listo, "completo": listo and not falta_vz, "items": R}, ensure_ascii=False, indent=1)); sys.exit(0 if listo else 1)
print("== REQUISITOS DEL DEVPANEL ==")
for nivel in ("OBLIGATORIO", "NECESARIO PARA VOZ/VIDEO", "OPCIONAL"):
    print("\n%s" % nivel)
    for x in (y for y in R if y["nivel"] == nivel):
        print("  %s %s — %s" % ("✔" if x["ok"] else ("✘" if nivel != "OPCIONAL" else "⚠"), x["nombre"], x["detalle"]))
        if not x["ok"] and x["arreglo"]: print("      → %s" % x["arreglo"])
print()
if falta_ob: print("FALTA ALGO OBLIGATORIO: arréglalo y vuelve a ejecutar  python requisitos.py  antes de abrir el panel.")
elif falta_vz: print("LISTO PARA ABRIR EL PANEL, pero NO para hacer voz/video: falta %s." % ", ".join(x["nombre"] for x in falta_vz))
else: print("TODO EN ORDEN: puedes abrir el panel (iniciar_devpanel.bat).")
sys.exit(0 if listo else 1)
