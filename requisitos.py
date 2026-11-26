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
# 5) Voces locales (Piper / Kokoro)
_vd = pathlib.Path(os.environ.get("VOCES_TTS_DIR") or (pathlib.Path.home() / "voces_tts"))
_pv = sorted(x.name[:-5] for x in _vd.glob("*.onnx")) if _vd.is_dir() else []
item("NECESARIO PARA VOZ/VIDEO", "Voz Piper instalada", bool(_pv and tiene("piper")), (", ".join(_pv) + " en " + str(_vd)) if _pv else "no hay voces en: %s" % _vd, "Ejecuta:  python instalar_voces.py  (instala piper-tts y descarga la voz es_MX-claude-high)")
_nx = bool(shutil.which("npx") or shutil.which("npx.cmd"))
item("OPCIONAL", "Voces Kokoro (em_alex, em_santa)", bool(_nx and tiene("kokoro_onnx") and tiene("soundfile")), "listas" if (_nx and tiene("kokoro_onnx") and tiene("soundfile")) else "faltan Node.js 22+ y/o los paquetes kokoro-onnx y soundfile", "Instala Node.js 22+ (nodejs.org) y ejecuta:  python -m pip install kokoro-onnx soundfile  y luego  python instalar_voces.py --solo-kokoro")
# 5b) Voice Studio (opcional)
_vsd = CFG.get("voice_studio_dir")
_vs_ok = bool(_vsd and (pathlib.Path(_vsd) / "backend").is_dir() and (pathlib.Path(_vsd) / ".venv").is_dir())
item("OPCIONAL", "Voice Studio (solo si quieres usar tus perfiles)", _vs_ok, _vsd if _vs_ok else "no configurado", "Actívalo en Ajustes → Voz → Voice Studio y pulsa «Buscar en el PC». No es necesario para generar voz.")
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
