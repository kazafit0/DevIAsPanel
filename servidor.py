"""PANEL DE MAPAS (copia del panel de videos para /mapa-interactivo) · servidor local (solo stdlib).  Uso: python servidor.py [puerto]   -> http://localhost:8810
Todo vive en D:. Sirve la interfaz (static/), los videos y juegos de series/, y una API para: catalogo de ideas, pedidos, proyectos, guion por frases,
y TRABAJOS (rehacer voz, grabar, mezclar) que ejecutan las herramientas de cada proyecto con los temporales en la carpeta elegida en Ajustes (por defecto _tmp)."""
import http.server, socketserver, json, os, sys, pathlib, subprocess, threading, time, urllib.parse, urllib.request, mimetypes, wave, shutil, re, socket
ROOT = pathlib.Path(__file__).resolve().parent; SERIES = ROOT / "series"; STATIC = ROOT / "static"; PY = sys.executable
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8820
LOCK = threading.Lock(); JOBS = {}; JID = [0]
def _cfg_json():
    try: return json.loads((ROOT / "devpanel.json").read_text(encoding="utf-8"))
    except Exception: return {}
TMPD = _cfg_json().get("temp_dir") or os.environ.get("DEVPANEL_TMP") or str(ROOT / "_tmp")   # temporales: la carpeta que el usuario eligió (Ajustes / instalación) o, si no, _tmp dentro del panel
ENV = dict(os.environ, TEMP=TMPD, TMP=TMPD, PYTHONIOENCODING="utf-8", DEVPANEL_TMP=TMPD)
os.makedirs(TMPD, exist_ok=True)

def jload(name, default):
    p = ROOT / name
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return default
def jsave(name, data):
    with LOCK: (ROOT / name).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

def proyecto(pid):
    for p in jload("proyectos.json", []):
        if p["id"] == pid: return p
    return None
def carpeta(p): return SERIES / (p.get("carpeta") or "__sin_carpeta__")
ETAPAS = ["Entender el pedido", "Guion y frases", "Mapa y países", "Personajes y escenas", "Gráficos", "Voz y tiempos", "Verificación", "Borrador listo"]
def logact(idea, msg, tipo="info", **kw):
    """Bitácora de lo que hace Claude (pestaña Actividad y campana de avisos)."""
    L = jload("actividad.json", []); L.append(dict({"ts": time.time(), "hora": time.strftime("%H:%M:%S"), "dia": time.strftime("%Y-%m-%d"), "idea": idea, "tipo": tipo, "msg": msg}, **kw)); jsave("actividad.json", L[-400:])
EXT_COD = (".py", ".js", ".json", ".html", ".md")
def archivos_recientes(ref, desde=0, horas=6):
    """Archivos de código que Claude creó o cambió para este video (carpeta del proyecto, o la carpeta de series más reciente si aún no tiene)."""
    c = None
    for pr in jload("proyectos.json", []):
        if ref in (pr.get("id"), pr.get("idea")) and pr.get("carpeta"): c = SERIES / pr["carpeta"]
    lim = max(desde, time.time() - horas * 3600)
    if c is None or not c.exists():
        mejor = (0, None)
        for d in SERIES.iterdir():
            if d.is_dir():
                try: t = max([d.stat().st_mtime] + [f.stat().st_mtime for f in d.glob("*") if f.is_file()])
                except Exception: continue
                if t > mejor[0] and t >= lim: mejor = (t, d)
        c = mejor[1]
    if c is None: return {"carpeta": None, "archivos": []}
    out = []
    for f in c.rglob("*"):
        if f.is_file() and f.suffix in EXT_COD and not any(x in f.parts for x in ("salida", "salida_mudo", "voz", "audiolibro", "sfx", "music", "node_modules", "__pycache__", "miniaturas", "vista_previa")) and f.stat().st_mtime >= lim:
            try: n = sum(1 for _ in open(f, encoding="utf-8", errors="ignore"))
            except Exception: n = 0
            out.append({"f": str(f.relative_to(c)).replace(chr(92), "/"), "kb": round(f.stat().st_size / 1024, 1), "lineas": n, "t": f.stat().st_mtime, "hora": time.strftime("%H:%M", time.localtime(f.stat().st_mtime))})
    out.sort(key=lambda x: -x["t"]); return {"carpeta": c.name, "archivos": out[:30]}
def voice_up():
    try: urllib.request.urlopen("http://127.0.0.1:3900/health", timeout=1.5); return True
    except Exception: return False
def _vs_auto():   # dónde está Voice Studio si no se dijo en devpanel.json -> "voice_studio_dir" (sin rutas de nadie): variable VOICESTUDIO_DIR o sitios habituales
    import os
    for b in (os.environ.get("VOICESTUDIO_DIR"), os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "VoiceStudio"), os.path.join(os.environ.get("ProgramFiles", ""), "VoiceStudio"), os.path.join(os.path.expanduser("~"), "VoiceStudio")):
        if b:
            for sub in ("project", ""):
                p = pathlib.Path(b) / sub if sub else pathlib.Path(b)
                if (p / ".venv").exists() or (p / "data").exists(): return p
    return pathlib.Path(os.path.expanduser("~")) / "VoiceStudio" / "project"
def _vs_dir():   # la carpeta de Voice Studio se puede cambiar en devpanel.json -> "voice_studio_dir" (otra cuenta o equipo)
    try: return pathlib.Path(json.loads((ROOT / "devpanel.json").read_text(encoding="utf-8")).get("voice_studio_dir") or _vs_auto())
    except Exception: return _vs_auto()
VS_DIR = _vs_dir(); VS_PY = VS_DIR / ".venv" / "Scripts" / "python.exe"
def _ram_libre():
    import ctypes
    class MS(ctypes.Structure): _fields_ = [("l", ctypes.c_ulong), ("load", ctypes.c_ulong), ("tp", ctypes.c_ulonglong), ("ap", ctypes.c_ulonglong), ("tpf", ctypes.c_ulonglong), ("apf", ctypes.c_ulonglong), ("tv", ctypes.c_ulonglong), ("av", ctypes.c_ulonglong), ("ae", ctypes.c_ulonglong)]
    m = MS(); m.l = ctypes.sizeof(MS); ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m)); return round(m.ap / 2 ** 30, 2), round(m.tp / 2 ** 30, 1)
_HW = {"t": 0, "d": None}
def _senal_min():   # cada cuántos minutos Claude renueva la señal de «conectado» (se elige en el popup de primer uso y en Ajustes; devpanel.json -> senal_min)
    try: return max(5, min(240, int(jload("devpanel.json", {}).get("senal_min") or 30)))
    except Exception: return 30
def hardware():   # QUÉ PC es: Windows, procesador, RAM, tarjeta(s) de video y cómo va a grabar el panel (se muestra en Ajustes)
    if _HW["d"] and time.time() - _HW["t"] < 120: return _HW["d"]
    import platform
    def ps(cmd):
        try:
            r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=12, encoding="utf-8", errors="replace"); return r.stdout.strip()
        except Exception: return ""
    def js(cmd):
        s = ps(cmd + " | ConvertTo-Json -Compress")
        try: v = json.loads(s)
        except Exception: return []
        return v if isinstance(v, list) else ([v] if v else [])
    so = (js("Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,OSArchitecture") or [{}])[0]
    cpu = (js("Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors") or [{}])[0]
    pc = (js("Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model") or [{}])[0]
    gpus = js("Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM,DriverVersion")
    rl, rt = _ram_libre(); vl, vt = _vram()
    g = []
    for x in gpus:
        nombre = (x.get("Name") or "").strip(); ram = round((x.get("AdapterRAM") or 0) / 1024 ** 3, 1)
        nv = "nvidia" in nombre.lower()
        g.append({"nombre": nombre, "vram_gb": (vt if (nv and vt) else (ram or None)), "nvidia": nv, "driver": x.get("DriverVersion")})
    gpu_ok = any(x["nvidia"] and (x["vram_gb"] or 0) >= 4 for x in g)
    modo = ("Tarjeta de video NVIDIA: grabación rápida por GPU y voz local (Voice Studio)" if gpu_ok else
            ("Tarjeta de video sin NVIDIA suficiente: se graba con el procesador (más lento) y la voz usa Hugging Face" if g else "Sin tarjeta de video: se graba solo con procesador y memoria RAM (más lento) y la voz usa Hugging Face"))
    d = {"windows": ("%s %s" % (so.get("Caption") or platform.system(), so.get("OSArchitecture") or "")).strip(), "windows_version": so.get("Version") or platform.version(),
         "equipo": ("%s %s" % (pc.get("Manufacturer") or "", pc.get("Model") or "")).strip(), "procesador": (cpu.get("Name") or platform.processor() or "").strip(),
         "nucleos": cpu.get("NumberOfCores"), "hilos": cpu.get("NumberOfLogicalProcessors"), "ram_total_gb": rt, "ram_libre_gb": rl, "gpus": g, "usa_gpu": gpu_ok, "modo_render": modo,
         "python": platform.python_version(), "voice_studio": voice_up()}
    _HW["d"] = d; _HW["t"] = time.time(); return d

def _vram():
    try:
        o = subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=6).stdout.strip().split(",")
        return round((float(o[1]) - float(o[0])) / 1024, 2), round(float(o[1]) / 1024, 1)
    except Exception: return None, None
def _pid_3900():
    try:
        for l in subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, timeout=8).stdout.splitlines():
            if ":3900 " in l and "LISTENING" in l: return int(l.split()[-1])
    except Exception: pass
    return None
def voice_iniciar(espera=120):
    """Enciende SOLO la API de Voice Studio (sin la ventana): ~150 MB de RAM; el modelo ocupa la tarjeta recién al generar la primera frase."""
    if voice_up(): return True
    if not VS_PY.exists(): return False
    _env = dict(os.environ); _dd = VS_DIR.parent / "data"   # REGLA: sin OMNIVOICE_DATA_DIR Voice Studio usa %APPDATA%\OmniVoice (carpeta vacia): no ve los perfiles del usuario ni sus activaciones y la API responde 403. Siempre su carpeta «data».
    if _dd.exists(): _env["OMNIVOICE_DATA_DIR"] = str(_dd)
    subprocess.Popen([str(VS_PY), "-m", "uvicorn", "main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "3900"], cwd=str(VS_DIR), env=_env, creationflags=0x08000000 | 0x00000008, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    t0 = time.time()
    while time.time() - t0 < espera:
        if voice_up(): return True
        time.sleep(1.5)
    return False
def voice_detener():
    """Apaga la API de Voice Studio (libera ~5 GB de la tarjeta). Mata el proceso que escucha en 3900 y su lanzador de Python."""
    pid = _pid_3900()
    if not pid: return False
    try:
        pp = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Process -Filter 'ProcessId=%d').ParentProcessId" % pid], capture_output=True, text=True, timeout=10).stdout.strip()
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=15)
        if pp.isdigit():
            nom = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-Process -Id %s -ErrorAction SilentlyContinue).ProcessName" % pp], capture_output=True, text=True, timeout=10).stdout.strip().lower()
            if nom == "python": subprocess.run(["taskkill", "/PID", pp, "/T", "/F"], capture_output=True, timeout=15)
    except Exception: pass
    time.sleep(2); return not voice_up()
def wav_dur(path):
    try:
        with wave.open(str(path)) as w: return round(w.getnframes() / w.getframerate(), 2)
    except Exception:   # WAV de 32 bits float (voz unica): leer la cabecera RIFF a mano
        try:
            import struct
            with open(path, "rb") as f:
                f.read(12); br = None
                while True:
                    h = f.read(8)
                    if len(h) < 8: return None
                    cid, sz = struct.unpack("<4sI", h)
                    if cid == b"fmt ": d = f.read(sz); br = struct.unpack("<I", d[8:12])[0]
                    elif cid == b"data": return round(sz / br, 2) if br else None
                    else: f.seek(sz + (sz & 1), 1)
        except Exception: return None

def guion_de(p):
    c = carpeta(p)
    try: g = json.loads((c / p.get("guion", "guion/1.json")).read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError): return []   # proyecto sin carpeta o sin guion todavía (idea en espera, video archivado o rehaciéndose): no hay frases, no es un error
    plan = {}
    try:
        for q in json.loads((c / "plan.json").read_text(encoding="utf-8")): plan[q["k"]] = q
    except Exception: pass
    try: hist = json.loads((c / "voz" / "textos.json").read_text(encoding="utf-8"))
    except Exception: hist = {}
    out = []
    for k, l in enumerate(g, 1):
        w = c / "voz" / ("1_%02d.wav" % k); vig = w.exists() and (hist.get(w.name) == l.get("texto"))   # la voz solo vale si se genero con ESTE texto
        out.append({"k": k, "t": l.get("t", 0), "texto": l.get("texto", ""), "key": l.get("key", ""), "voz": vig, "dur": wav_dur(w) if vig else None, "at": plan.get(k, {}).get("at") if vig else None, "se_pasa": plan.get(k, {}).get("se_pasa") if vig else None, "vv": int(w.stat().st_mtime) if w.exists() else 0, "retraso": plan.get(k, {}).get("retraso")})
    return out


import random, hashlib, re

def voz_escenas(p):   # UN SOLO audio para todo el video (voz/voz_completa.wav, de 0 a la duracion); valido si todas las frases tienen la voz de su texto actual
    c = carpeta(p); g = guion_de(p); f = c / "voz" / "voz_completa.wav"
    try: meta = json.loads((c / "voz" / "completa.json").read_text(encoding="utf-8"))
    except Exception: meta = {}
    ok = f.exists() and bool(g) and all(l["voz"] for l in g) and sorted(meta.get("frases", [])) == list(range(1, len(g) + 1))
    return {"voz": bool(ok), "dur": wav_dur(f) if f.exists() else None, "vv": int(f.stat().st_mtime) if f.exists() else 0, "url": "/series/%s/voz/voz_completa.wav" % p["carpeta"], "frases": len(g)}

def voz_preview(p):   # mp4 de revision = video mudo + las voces ya puestas en su segundo (audio nativo: suena en cualquier navegador)
    import imageio_ffmpeg
    c = carpeta(p); mu = c / p["video_mudo"] if p.get("video_mudo") else None
    if not mu or not mu.exists(): return None
    ve = voz_escenas(p)
    if ve["voz"]:   # un solo audio de todo el video, desde el segundo 0
        f_ = c / "voz" / "voz_completa.wav"; sig = hashlib.md5((str(mu.stat().st_mtime) + "U|" + str(f_.stat().st_mtime)).encode()).hexdigest()[:10]; out = c / "salida_mudo" / ("voz_preview_%s.mp4" % sig)
        if not out.exists():
            import imageio_ffmpeg
            for old in (c / "salida_mudo").glob("voz_preview_*.mp4"):
                try: old.unlink()
                except Exception: pass   # archivo en uso (se esta reproduciendo): no romper la ruta
            r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(mu), "-i", str(f_), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], env=ENV, capture_output=True, text=True)
            if r.returncode: print("voz_preview error", r.stderr[-500:]); return None
        return "/series/%s/salida_mudo/%s" % (p["carpeta"], out.name)
    g = guion_de(p); it = []; prev = -9.0
    for l in g:
        if not l["voz"] or not l["dur"]: continue
        at = l["at"] if l.get("at") is not None else l["t"]; at = max(at, prev - .10); prev = at + l["dur"]; it.append((at, c / "voz" / ("1_%02d.wav" % l["k"])))
    if not it: return None
    sig = hashlib.md5((str(mu.stat().st_mtime) + "|" + "|".join("%.2f:%d" % (a, f.stat().st_mtime) for a, f in it)).encode()).hexdigest()[:10]
    out = c / "salida_mudo" / ("voz_preview_%s.mp4" % sig)
    if not out.exists():
        for old in (c / "salida_mudo").glob("voz_preview_*.mp4"): old.unlink()
        cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(mu)]
        for a, f in it: cmd += ["-i", str(f)]
        fc = "".join("[%d:a]aresample=44100,adelay=%d|%d[a%d];" % (i + 1, int(a * 1000), int(a * 1000), i) for i, (a, f) in enumerate(it))
        fc += "".join("[a%d]" % i for i in range(len(it))) + "amix=inputs=%d:normalize=0:duration=longest[o]" % len(it)
        cmd += ["-filter_complex", fc, "-map", "0:v", "-map", "[o]", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)]
        r = subprocess.run(cmd, env=ENV, capture_output=True, text=True)
        if r.returncode: print("voz_preview error", r.stderr[-500:]); return None
    return "/series/%s/salida_mudo/%s" % (p["carpeta"], out.name)
import cola, titulos_base as titulos
import inspect
def nombres(pr): return [cola.PAIS.get(k, k) for k in pr.get("paises", [])]
def hechos(pr):
    if pr.get("seo"): return dict(pr["seo"])   # el contenido sale del bloque seo del proyecto
    return {"paises": nombres(pr), "momentos": pr.get("momentos") or []}
def _gen(pr):
    """Generador de títulos: el que declara el plugin del video (plugin.json -> titulos.tipos[seo.tipo]) y SOLO si ese plugin está activo; si no, el genérico del núcleo."""
    d, m = plugin_de(pr); tp = (pr.get("seo") or {}).get("tipo")
    if d:
        mn = ((m.get("titulos") or {}).get("tipos") or {}).get(tp)
        mod = modulo_plugin(d, "%s/%s.py" % ((m.get("titulos") or {}).get("dir", "titulos"), mn)) if mn else None
        if mod and hasattr(mod, "generar"):
            ac = "largo" in inspect.signature(mod.generar).parameters
            return (lambda pid, f, l, usados=(): mod.generar(pid, f, l, usados, largo=pr.get("formato") == "largo")) if ac else (lambda pid, f, l, usados=(): mod.generar(pid, f, l, usados))
    return lambda pid, f, l, usados=(): titulos.generar(pid, f, l, usados, largo=pr.get("formato") == "largo")
def titulos_de(pr):
    d = titulos.cargar(ROOT / "titulos", pr["id"])
    if d and d.get("version") == (5 if pr.get("seo") else 3): return d
    el = (d or {}).get("elegido")   # version nueva del generador (SEO / alto CTR): se regeneran las opciones y se conserva lo elegido
    d = {"version": 5 if pr.get("seo") else 3, "lote": 1, "pos": 0, "elegido": el, "usados": [], "items": _gen(pr)(pr["id"], hechos(pr), 1)}
    d["usados"] = [x["titulo"] for x in d["items"]]; return d
def nuevo_lote(pr, d):   # se gastaron las 100: se genera otro JSON de 100 opciones nuevas
    d["lote"] += 1; d["pos"] = 0; d["items"] = _gen(pr)(pr["id"], hechos(pr), d["lote"], d["usados"]); d["usados"] += [x["titulo"] for x in d["items"]]
MEC = {"carrera": ("Carrera", "Los países corren hacia la meta"), "supervivencia": ("Supervivencia", "Gana el último que queda en pie"), "empujar": ("Empujones", "Se empujan fuera de la plataforma"),
       "punteria": ("Puntería", "Lanzan y apuntan a un blanco"), "duelo": ("Duelo", "Dos equipos se enfrentan cara a cara"), "apilar": ("Construcción", "Apilan y construyen sin que se caiga"),
       "conquista": ("Conquista", "Se reparten un mapa y conquistan territorio"), "escondidas": ("Escondidas", "Unos buscan y otros se esconden"), "defensa": ("Defensa", "Defienden su base de oleadas que llegan"),
       "laberinto": ("Laberinto", "Buscan la salida entre muros y fantasmas"), "cooperacion": ("Cooperativo", "Equipos que se ayudan para vencer a un jefe"), "equilibrio": ("Equilibrio", "Se mantienen sobre algo que se mueve")}
CLAVES = {"angry": "punteria", "birds": "punteria", "catapulta": "punteria", "tiro": "punteria", "canon": "punteria", "cañon": "punteria", "disparo": "punteria", "mario": "carrera", "kart": "carrera", "carrera": "carrera", "correr": "carrera", "fall": "carrera",
          "guys": "carrera", "zombi": "defensa", "zombis": "defensa", "plantas": "defensa", "torre": "defensa", "defensa": "defensa", "pacman": "laberinto", "laberinto": "laberinto", "fantasma": "laberinto", "tetris": "apilar", "apilar": "apilar", "jenga": "apilar",
          "among": "escondidas", "impostor": "escondidas", "escondidas": "escondidas", "royale": "supervivencia", "battle": "supervivencia", "sobrevivir": "supervivencia", "lava": "supervivencia", "sumo": "empujar", "empuje": "empujar", "lucha": "duelo",
          "duelo": "duelo", "pelea": "duelo", "guerra": "conquista", "mapa": "conquista", "conquista": "conquista", "risk": "conquista", "avion": "duelo", "aviones": "duelo", "jefe": "cooperacion", "equipos": "cooperacion", "equilibrio": "equilibrio", "puente": "equilibrio"}
GIROS = ["con una zona que se encoge", "con viento que cambia", "sobre hielo resbaladizo", "con imanes que atraen", "entre niebla", "a doble velocidad", "con controles al revés", "con obstáculos que giran", "con gravedad invertida", "con un molino en medio", "con trampas sorpresa"]
ESCS = ["en una fábrica", "en el espacio", "en el océano", "en la selva", "en una ciudad", "en un volcán", "en la nieve", "en un casino", "en un estadio", "en una juguetería", "en un supermercado", "en un parque de atracciones"]
def ejemplos_de(ref, n=6):
    low = re.sub(r"[^a-z0-9ñ ]", " ", ref.lower()); palabras = low.split(); m = []
    for w in palabras:
        if w in CLAVES and CLAVES[w] not in m: m.append(CLAVES[w])
    rnd = random.Random(int(hashlib.md5(ref.encode("utf-8")).hexdigest()[:8], 16)); resto = [k for k in MEC if k not in m]; rnd.shuffle(resto); orden = (m + resto)[:n]; out = []
    for k, key in enumerate(orden):
        nm, ds = MEC[key]; g = rnd.choice(GIROS); e = rnd.choice(ESCS)
        out.append({"id": "e%d" % int(time.time() * 1000 % 100000000 + k), "titulo": "%s %s %s" % (nm, g, e), "desc": "Inspirado en «%s»: %s %s %s." % (ref.strip()[:60], ds, g, e), "estado": "nuevo", "mecanica": key})
    return out

# ---------------- trabajos ----------------
def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p
def esperado(p, tipo, c):
    t = jload("tiempos.json", {}).get(tipo + ":" + p["id"])
    if t: return t
    d = float(p.get("duracion") or 40)
    if tipo == "grabar": return d * .7 + 20
    if tipo == "mezclar": return d * 1.8 + 40   # el mezclador no informa: se estima segun lo que dura el video
    try: n = len(guion_de(p))
    except Exception: n = 20
    return n * (4 if tipo == "voz_todas" else 2) + 15

PARADOS = {}   # idea -> {"titulo", "min", "auto"}: pedidos que Claude dejo sin avanzar (los ve el panel y los despierta solo)
def _vigila_claude():
    """DETECTOR AUTOMATICO de «Claude se quedo parado» (interno del panel, sin que nadie escriba): un pedido sin terminar (pendiente / en proceso) que lleva varios minutos sin ningun avance
    (ni pedido.py, ni archivos nuevos en su carpeta, ni trabajo del panel, ni pregunta esperando al usuario) = parado. Entonces el panel dispara SOLO el aviso de emergencia (despierta a Claude por el monitor)
    y lo muestra en la barra superior. Si el monitor tambien esta caido, la barra lo dice para que el usuario sepa que hace falta escribirle."""
    ultimo = {}
    while True:
        try:
            time.sleep(30); ahora = time.time(); nuevos = {}
            ocupado = any(j["estado"] == "corriendo" and not j.get("externo") for j in JOBS.values())
            for x in jload("pedidos.json", []):
                est = x.get("estado") or "pendiente"
                if est not in ("pendiente", "en_proceso") or x.get("error") or (x.get("tipo") or "") in ("ideas", "recibido") or (x.get("pregunta") and not x.get("respuesta")): continue
                try: t0 = time.mktime(time.strptime(x.get("act") or x.get("hora") or "", "%Y-%m-%d %H:%M:%S" if x.get("act") else "%Y-%m-%d %H:%M"))
                except Exception: continue
                ref = x.get("idea") or ""; pr = next((q for q in jload("proyectos.json", []) if q.get("idea") == ref or q.get("id") == ref), None); d = ROOT / "series" / (pr or {}).get("id", "_x")
                try: t_arch = max((f.stat().st_mtime for f in d.rglob("*") if f.is_file() and f.suffix in (".js", ".py", ".json", ".md", ".mp4", ".html")), default=0) if d.exists() else 0
                except Exception: t_arch = 0
                quieto = ahora - max(t0, t_arch)
                if quieto > (150 if est == "pendiente" else 240) and not ocupado: nuevos[ref] = {"titulo": (x.get("titulo") or ref)[:70], "min": int(quieto // 60), "estado": est}
            PARADOS.clear(); PARADOS.update(nuevos)
            for ref, v in nuevos.items():
                if ahora - ultimo.get(ref, 0) > 360:   # un aviso cada 6 min por pedido
                    ultimo[ref] = ahora; (ROOT / "emergencia.json").write_text(json.dumps({"ts": ahora, "hora": time.strftime("%H:%M:%S"), "auto": True, "idea": ref}), encoding="utf-8")
                    logact(ref, "Detector automatico: Claude lleva %d min sin avanzar en «%s»; el panel lo despierta solo." % (v["min"], v["titulo"]), "pedido")
        except Exception as e: print("vigila_claude:", e)


def archivar_carpeta(src, dst):
    """Archiva una carpeta de video SIN romperla si un archivo esta en uso (Windows WinError 32): 1) rename directo; 2) si no, COPIA todo a `dst` (se puede leer un archivo en uso),
    comprueba que se copio y recien entonces borra lo que pueda del origen. Devuelve la lista de archivos que no se pudieron borrar. Si la copia falla, no borra nada y lanza el error."""
    import gc; gc.collect()   # cierra manejadores de archivos que el propio panel haya dejado abiertos al servir el video
    try: os.rename(str(src), str(dst)); return []
    except OSError: pass
    shutil.copytree(str(src), str(dst), dirs_exist_ok=True)
    falt = [str(f.relative_to(src)) for f in src.rglob("*") if f.is_file() and not (dst / f.relative_to(src)).exists()]
    if falt: raise RuntimeError("la copia quedo incompleta (%s)" % ", ".join(falt[:3]))
    fallos = []
    for f in sorted(src.rglob("*"), key=lambda x: -len(x.parts)):
        try: f.unlink() if f.is_file() else f.rmdir()
        except Exception: fallos.append(f.name)
    try: src.rmdir()
    except Exception: pass
    return fallos

def vista_job(j):
    if j.get("externo") and j["estado"] == "corriendo":   # barra «atascada»: un trabajo de Claude se cierra SOLO si (1) su ultimo mensaje ya dice «listo», (2) el proyecto ya muestra el borrador/video listo, o (3) lleva 4 min sin avisar
        _ult = str((j.get("log") or [""])[-1]).lower().strip(); _lis = _ult.startswith(("borrador listo", "video listo", "listo")) or " borrador listo" in _ult[:40]
        try: _pg = next((x.get("progreso") or {} for x in jload("proyectos.json", []) if x.get("id") == j.get("proyecto")), {}); _lis = _lis or (str(_pg.get("msg", "")).lower().startswith(("borrador listo", "video listo")) and time.mktime(time.strptime(_pg.get("act", "1970-01-01 00:00:00"), "%Y-%m-%d %H:%M:%S")) >= j["inicio"] - 5)
        except Exception: pass
        if _lis or time.time() - j.get("ultima", j["inicio"]) > 240: j["estado"] = "listo"; j["pct"] = 100; j["fin"] = j.get("ultima", time.time())
    d = {k: v for k, v in j.items() if k != "log"}; d["log"] = j["log"][-60:]; now = time.time(); fin = j["fin"] or now
    d["transcurrido"] = round(fin - j["inicio"], 1); d["silencio"] = round(now - j.get("ultima", j["inicio"]), 1) if j["estado"] == "corriendo" else 0
    if j["estado"] == "corriendo":
        import math; est = int(95 * (1 - math.exp(-2.0 * d["transcurrido"] / max(5, j.get("esperado", 60)))))   # sube sin congelarse en 95
        d["pct"] = max(j.get("pct", 0), est)
    return d
def run_job(job, p, tipo):
    c = carpeta(p); seed = str(p["seed"]); tag = p.get("tag", "")
    def log(x): job["log"].append(x); job["log"] = job["log"][-400:]
    try:
        if tipo in ("voz", "voz_todas"):
            if not voice_up() and not voice_iniciar(): job["estado"] = "error"; log("Voice Studio esta CERRADO y no pude encenderlo solo (carpeta VoiceStudioRunIA en E:). Abrelo y repite."); return
            if (c / "tools" / "voz_unica.py").exists() or (c / "guion" / "1.json").exists():   # METODO de los mapas (2026-11-16): AUDIOLIBRO con colchon « , ----[pause Xms] » sin puntos, UNA toma (corto y largo); nunca recortar palabras
                _vs = ROOT / "motor" / "voz_partes.py"   # LA VOZ ES DEL DEVPANEL (un solo motor para todos los plugins); el plugin solo declara voz.modo
                if not _vs.is_file(): job["estado"] = "error"; log("Falta motor/voz_partes.py del DevIAs Panel."); return
                cmd = [PY, "-u", str(_vs), str(c)] + (["--rehacer"] if tipo == "voz_todas" else [])   # POR CAPITULOS con cache: solo se regenera lo que cambio
            elif p.get("voz_metodo") == "audiolibro" or not (c / "tools" / "generar_voz_api.py").exists():   # metodo AUDIOLIBRO (frase a frase, semilla unica, pausas exactas) -> voz/1_kk.wav + audiolibro/
                cmd = [PY, "-u", str(ROOT.parent / "herramientas" / "voz_audiolibro.py"), str(c), "--panel"]
            else: cmd = [PY, "-u", "tools/generar_voz_api.py", "1"] + (["--rehacer"] if tipo == "voz_todas" else [])
            if tipo == "voz_todas":
                for f in (c / "voz").glob("1_*.wav"): f.unlink()
                for f in (c / "audiolibro" / "escenas").glob("e*.json"): f.unlink()   # fuerza regenerar las escenas de corrido
                try: (c / "voz" / "textos.json").unlink()
                except Exception: pass
        elif tipo == "escena_mezcla": cmd = [PY, "tools/mix_escena.py", seed, tag, str(p["_n"]), p["_suf"]]
        elif tipo == "musica":
            if p.get("musica_manual") and p.get("musica_id"): cmd = [PY, "tools/music_short.py", str(p["musica_id"])]   # solo si el usuario pide otra musica de Freesound para ESTE video
            else: cmd = [PY, str(plugin_de(p)[0] / "pipeline" / "musica_fondo.py"), str(c)]   # MUSICA DE FONDO de los mapas (musica_fondo_mapas/fondo.json): efectos siempre de Freesound
        elif tipo in ("unir", "unir_prev"):
            import imageio_ffmpeg
            vids = [c / e["video"] for e in p.get("escenas", []) if e.get("video") and e.get("estado") in ("lista", "aprobada") and (c / e["video"]).exists()]
            if not vids: job["estado"] = "error"; log("No hay escenas listas para unir."); return
            lst = pathlib.Path(TMPD) / ("unir_%s.txt" % p["id"]); lst.write_text("".join("file '%s'" % str(v).replace(chr(92), "/") + chr(10) for v in vids), encoding="utf-8")
            outv = c / "salida" / (p["id"] + "_completo.mp4"); cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(outv)]
        elif tipo == "mezclar": cmd = [PY, "tools/mix_short.py", seed, tag, "_panel"]
        elif tipo == "capturas":   # capturas SIMPLES (sin texto) para la miniatura
            if (c / "tools" / "capturas.py").exists():
                port = free_port(); srv = subprocess.Popen([PY, "-m", "http.server", str(port), "--directory", str(c)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1.2); cmd = [PY, "tools/capturas.py", seed, str(port)]
            else: srv = None; cmd = [PY, str(ROOT / "capturas_ffmpeg.py"), str(c), p.get("video_mudo", "")]
        elif tipo == "grabar":   # grabador PARALELO: 6 navegadores a la vez (6-7x mas rapido que uno)
            srv = None; cmd = [PY, "-u", str(ROOT / "grabador" / "grabar_rapido.py"), str(c), seed, "--tag", "_panel"]   # /render-rapido: GPU (WebCodecs), 1 navegador; cae al paralelo con 3 si falla (6 navegadores daban Timeout con Voice Studio abierto)
        else: job["estado"] = "error"; log("tipo desconocido"); return
        job["esperado"] = esperado(p, tipo, c)
        log("$ " + " ".join(cmd)); pr = subprocess.Popen(cmd, cwd=str(c), env=env_plugin(p), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for line in pr.stdout:
            line = line.rstrip()
            job["ultima"] = time.time()
            m = re.match(r"\s*([\d.]+)s \(\d+s\)", line)
            if m and tipo == "grabar" and p.get("duracion"): job["pct"] = max(job.get("pct", 0), min(97, int(100 * float(m.group(1)) / float(p["duracion"]))))
            if re.match(r"\s*\d+_\d\d\s", line) and tipo in ("voz", "voz_todas"): job["hechas"] = job.get("hechas", 0) + 1
            if line and "Warning" not in line and "warn" not in line.lower(): log(line[:300])
        pr.wait(); ok = pr.returncode == 0
        if tipo in ("grabar", "capturas") and srv:
            try: srv.terminate()
            except Exception: pass
        if ok and tipo == "grabar":
            ps = jload("proyectos.json", [])
            for q in ps:
                if q["id"] == p["id"]: q["tag"] = "_panel"; q["video_mudo"] = "salida_mudo/s%s_panel.mp4" % seed
            jsave("proyectos.json", ps)
        if ok and tipo in ("voz", "voz_todas") and not job.get("_sub"):
            ps = jload("proyectos.json", [])
            for q in ps:
                if q["id"] == p["id"] and q.get("fase") == "resto": q["fase"] = "voces"
            jsave("proyectos.json", ps)
        if ok and tipo == "unir":
            ps = jload("proyectos.json", [])
            for q in ps:
                if q["id"] == p["id"]: q["video_final"] = "salida/" + p["id"] + "_completo.mp4"; q["estado"] = "hecho"
            jsave("proyectos.json", ps); cat = jload("catalogo.json", [])
            for it in cat:
                if it.get("proyecto") == p["id"]: it["estado"] = "hecho"
            jsave("catalogo.json", cat)
        if ok and tipo == "mezclar":
            ps = jload("proyectos.json", [])
            for q in ps:
                if q["id"] == p["id"]:
                    cand = sorted((c / "salida").glob("*_panel.mp4"), key=lambda f: f.stat().st_mtime, reverse=True)
                    if cand: q["video_final"] = "salida/" + cand[0].name
            jsave("proyectos.json", ps)
        if job.get("_sub"): job["_ok"] = ok; return
        job["estado"] = "listo" if ok else "error"
        if ok: job["pct"] = 100
        t = jload("tiempos.json", {}); t[tipo + ":" + p["id"]] = round(time.time() - job["inicio"], 1); jsave("tiempos.json", t)
    except Exception as e:
        job["estado"] = "error"; log("ERROR: %s" % e)
    finally:
        if not job.get("_sub"): job["fin"] = time.time()
def run_escena(job, p, n):   # rehace la voz de las frases cambiadas y vuelve a mezclar SOLO esta escena (con su audio)
    ps = jload("proyectos.json", []); q = next(x for x in ps if x["id"] == p["id"]); e = next(x for x in q["escenas"] if x["n"] == n); ver = e.get("ver", 1) + 1
    job["_sub"] = True; job["esperado"] = 60; p2 = dict(p); p2["_n"] = n; p2["_suf"] = "_v%d" % ver
    for k, t in enumerate(("voz", "escena_mezcla")):
        job["_ok"] = None; job["pct"] = (5, 60)[k]; job["log"].append("== Paso %d/2: %s ==" % (k + 1, ("generar la voz de las frases nuevas o cambiadas", "mezclar la escena %d con voz, efectos y musica" % n)[k]))
        run_job(job, p2, t)
        if not job.get("_ok"): job["estado"] = "error"; job["fin"] = time.time(); return
    ps = jload("proyectos.json", [])
    for x in ps:
        if x["id"] == p["id"]:
            for z in x["escenas"]:
                if z["n"] == n: z["video"] = "salida/escena_%02d%s.mp4" % (n, p2["_suf"]); z["ver"] = ver; z["estado"] = "lista"
    jsave("proyectos.json", ps); job["estado"] = "listo"; job["pct"] = 100; job["fin"] = time.time()
def run_final(job, p):   # TODAS las escenas aprobadas -> musica, voz, mezcla de cada escena (voz + efectos + musica de Freesound) y union en un solo mp4
    job["_sub"] = True; job["esperado"] = 260; n = len(p.get("escenas", [])); pasos = [("musica", None, 3), ("voz", None, 10)] + [("escena_mezcla", e["n"], 12 + int(75 * (k + 1) / max(1, n))) for k, e in enumerate(p["escenas"])] + [("unir", None, 96)]
    for k, (t, en, pc) in enumerate(pasos):
        job["_ok"] = None; job["pct"] = pc; job["log"].append("== Paso %d/%d: %s ==" % (k + 1, len(pasos), {"musica": "musica de Freesound", "voz": "voz de las frases nuevas o cambiadas", "escena_mezcla": "mezclar la escena %s con voz, efectos y musica" % en, "unir": "unir las escenas en un solo video"}[t]))
        if t == "unir":
            ps = jload("proyectos.json", [])
            for x in ps:
                if x["id"] == p["id"]:
                    for z in x["escenas"]: z["video"] = "salida/escena_%02d.mp4" % z["n"]; z["ver"] = z.get("ver", 1) + 1
            jsave("proyectos.json", ps); p = next(x for x in ps if x["id"] == p["id"]); job["_sub"] = True
        p2 = dict(p); p2["_n"] = en; p2["_suf"] = ""
        run_job(job, p2, t)
        if not job.get("_ok"): job["estado"] = "error"; job["fin"] = time.time(); return
    job["estado"] = "listo"; job["pct"] = 100; job["fin"] = time.time()
def run_audio_final(job, p):   # las escenas son MUDAS; solo cuando todas tienen OK se genera la voz y se mezcla con efectos y musica de Freesound
    job["_sub"] = True; job["_ok"] = None; job["esperado"] = 120
    for k, t in enumerate(("musica", "voz", "mezclar")):
        job["_ok"] = None; job["pct"] = (3, 15, 80)[k]; job["log"].append("== Paso %d/3: %s ==" % (k + 1, ("descargar la musica (Freesound)", "generar la voz del juego", "mezclar voz + efectos + musica")[k]))
        run_job(job, p, t)
        if not job.get("_ok"): job["estado"] = "error"; job["fin"] = time.time(); return
    job["estado"] = "listo"; job["pct"] = 100; job["fin"] = time.time()

def run_conforme(job, p, etapa="conforme", extra=()):   # pipeline «conforme» (voz por partes + union) como job del panel: se ve en «Trabajos» con su avance
    job["_sub"] = True; job["esperado"] = 240; c = carpeta(p)
    d_, m_ = plugin_de(p)
    if not d_: job["log"].append(SIN_PLUGIN["error"]); job["estado"] = "error"; job["fin"] = time.time(); return
    scr = d_ / (m_.get("pipeline") or {}).get("script", "")
    if not scr.is_file(): job["log"].append("El plugin «%s» no declara pipeline.script o no existe." % m_.get("nombre")); job["estado"] = "error"; job["fin"] = time.time(); return
    aj = dict({a_["id"]: a_.get("defecto") for a_ in m_.get("ajustes", [])}, **((estado_plugins().get("ajustes") or {}).get(d_.name) or {}))
    pr = subprocess.Popen([PY, "-u", str(scr), str(c), etapa, *extra], cwd=str(d_), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=dict(os.environ, TEMP=TMPD, TMP=TMPD, DEVPANEL_TMP=TMPD, PYTHONIOENCODING="utf-8", DEVPANEL=str(ROOT), PLUGIN_DIR=str(d_), PLUGIN_AJUSTES=json.dumps(aj, ensure_ascii=False)))
    for line in pr.stdout:
        job["log"].append(line.rstrip()[:300]); job["ultima"] = time.time(); m = re.match(r"\[(\d+)%\]", line)
        if m: job["pct"] = int(m.group(1))
    rc = pr.wait(); job["estado"] = "listo" if rc == 0 else "error"; job["pct"] = 100 if rc == 0 else job.get("pct", 0); job["fin"] = time.time()
def iniciar_conforme(p, etapa="conforme", extra=()):
    if etapa in ("conforme", "voz", "parte") and not voice_up(): voice_iniciar()   # la voz necesita la API: se enciende sola (solo la API, sin la ventana)
    with LOCK:
        if any(j["estado"] == "corriendo" and not j.get("externo") for j in JOBS.values()): return None   # los avisos de progreso de Claude (externo) NO bloquean los botones del panel
        JID[0] += 1; job = {"id": JID[0], "tipo": "conforme", "n": None, "proyecto": p["id"], "estado": "corriendo", "inicio": time.time(), "ultima": time.time(), "pct": 0, "fin": None, "log": ["== %s ==" % ("Estoy conforme: voz por partes + unión" if etapa == "conforme" else ("Voz (sin unir el video)" if etapa == "voz" else "Rehacer la voz de una parte + unión"))]}; JOBS[job["id"]] = job
    threading.Thread(target=run_conforme, args=(job, p, etapa, extra), daemon=True).start(); return job["id"]


# ---------------- PLUGINS = plugins del DevIAs Panel (2026-11-20) ----------------
# ESQUELETO ÚNICO: todo plugin lleva un plugin.json con estos campos. Sin ellos el panel NO lo usa y dice qué falta.
import zipfile, io, importlib.util
PLUGINS_DIR = ROOT / "plugins"
FORMATOS = {   # los formatos y sus duraciones son del PANEL; el plugin solo declara cuáles soporta (formatos: ["short", "largo"])
    "short": {"id": "short", "nombre": "Short vertical", "aspecto": "9:16", "duraciones": [30, 45, 60, 80, 105, 120], "defecto": 80},
    "largo": {"id": "largo", "nombre": "Video largo", "aspecto": "16:9", "duraciones": [210, 240, 300], "defecto": 240}}
def limpia_config_video(m, cfg):
    """Valida lo que el usuario eligió en Ideas contra config_video del plugin. -> (config limpia, error)."""
    out = {}; cfg = cfg if isinstance(cfg, dict) else {}
    for f in (m.get("config_video") or []):
        v = cfg.get(f["id"], f.get("defecto"))
        if f["tipo"] == "paises":
            v = [c for c in (v or []) if c in cola.PAIS]; v = list(dict.fromkeys(v))
            if not f.get("min", 1) <= len(v) <= f.get("max", 200): return None, "«%s»: elige entre %s y %s países" % (f["etiqueta"], f.get("min", 1), f.get("max", 200))
        elif f["tipo"] == "interruptor": v = bool(v)
        elif f["tipo"] == "numero":
            try: v = float(v)
            except Exception: return None, "«%s» debe ser un número" % f["etiqueta"]
            if v < f.get("min", v) or v > f.get("max", v): return None, "«%s» debe estar entre %s y %s" % (f["etiqueta"], f.get("min"), f.get("max"))
        elif f["tipo"] == "opcion" and v not in f.get("opciones", []): return None, "«%s»: opción no válida" % f["etiqueta"]
        elif f["tipo"] == "ganador":
            ps = out.get(f.get("paises", "paises")) or []; v = v if v in ps else ""
        elif f["tipo"] == "comentario":
            v = v if isinstance(v, dict) else {}
            try: sg = max(5.0, min(70.0, float(v.get("seg", 11))))
            except Exception: sg = 11.0
            v = {"activo": bool(v.get("activo")), "usuario": str(v.get("usuario", "")).strip().lstrip("@")[:40], "texto": str(v.get("texto", "")).strip()[:200], "seg": sg, "voz": (str(v.get("voz", "")).strip() or "Mira lo último que dijo este fan.")[:80]}
            if v["activo"] and (not v["usuario"] or not v["texto"]): return None, "«%s»: pon el usuario y el mensaje del comentario (o desactívalo)" % f["etiqueta"]
        elif f["tipo"] == "equipos":
            v = v if isinstance(v, dict) else {}; ps = out.get(f.get("paises", "paises")) or []; v = {"rojo": [c for c in (v.get("rojo") or []) if c in ps], "azul": [c for c in (v.get("azul") or []) if c in ps]}
            resto = [c for c in ps if c not in v["rojo"] and c not in v["azul"]]
            for k_, c in enumerate(resto): v["rojo" if (len(v["rojo"]) <= len(v["azul"])) else "azul"].append(c)
        out[f["id"]] = v
    return out, None
def cierra_trabajos_de(*claves):
    """Al borrar o rehacer un video, sus barras «Claude trabaja en…» se cierran (no se quedan abiertas en el panel)."""
    with LOCK:
        for j in JOBS.values():
            if j.get("externo") and j["estado"] == "corriendo" and (j.get("clave") in claves or j.get("proyecto") in claves): j["estado"] = "listo"; j["fin"] = time.time(); j["pct"] = 100
def correr_agentes(d_, m_, it, cfgv, fm, seg, anterior=None):
    """Los DOS AGENTES del cerebro: «formato» (trae el mejor formato para la idea: tipo de inicio, estructura…) y «diseño» (trae el mejor diseño gráfico del juego).
    Sus reglas son del plugin (plugin.json → agentes.modulo con formato(ctx) y diseno(ctx)); recuerdan lo ya usado (agentes_historial.json) para no repetirse.
    Claude puede refinarlos lanzando subagentes y avisando con pedido.py --agente formato|diseno «texto»."""
    ag = {}; mod = None; ref = (m_.get("agentes") or {}).get("modulo")
    if ref:
        try: mod = modulo_plugin(d_, ref)
        except Exception as e: print("agentes:", e)
    hist = jload("agentes_historial.json", {}); h = hist.setdefault(d_.name, {})
    ctx = {"idea": it, "config_video": cfgv, "formato": fm, "seg": seg, "historial": h, "anterior": anterior, "ajustes": dict({a["id"]: a.get("defecto") for a in m_.get("ajustes", [])}, **((estado_plugins().get("ajustes") or {}).get(d_.name) or {}))}
    for nom in ("formato", "diseno"):
        f = getattr(mod, nom, None) if mod else None
        if not f: continue
        try: r = f(ctx)
        except Exception as e: print("agente", nom, e); r = None
        if r:
            ag[nom] = {"estado": "listo", "resumen": r.get("resumen", ""), "msg": r.get("detalle") or r.get("resumen", ""), "config": r.get("config", {}), "hora": time.strftime("%H:%M:%S")}
            for k, v in (r.get("uso") or {}).items(): h.setdefault(k, []).append(v); h[k] = h[k][-40:]
    jsave("agentes_historial.json", hist); return ag
def texto_agentes(ag):
    return "".join(" AGENTE DE %s (propuesta del panel): %s." % (n.upper(), (ag[k].get("msg") or ag[k].get("resumen", "")).replace("\n", " ")) for k, n in (("formato", "FORMATO"), ("diseno", "DISEÑO")) if k in ag) + (" Puedes refinar estas propuestas lanzando un subagente de formato y otro de diseño, y avisar con pedido.py --agente formato|diseno «texto»." if ag else "")
def texto_config_video(m, cfg):
    t = []
    for f in (m.get("config_video") or []):
        v = cfg.get(f["id"])
        if f["tipo"] == "paises": t.append("%s: %s" % (f["etiqueta"], ", ".join("%s (%s)" % (cola.PAIS.get(c, c), c) for c in v)))
        elif f["tipo"] == "ganador": t.append("%s: %s" % (f["etiqueta"], cola.PAIS.get(v, v) if v else "al azar (lo decide el juego)"))
        elif f["tipo"] == "comentario":
            if v and v.get("activo"): t.append("COMENTARIO DE UN FAN (barra estilo YouTube; motor/fancomment.js lee config.json → comentario; añade al guion la frase de voz con la clave «uc» en el segundo indicado): @%s «%s» en el segundo %s, voz «%s»" % (v["usuario"], v["texto"], int(v["seg"]), v["voz"]))
        elif f["tipo"] == "equipos":
            if cfg.get(f.get("si", "")) is False: continue
            t.append("%s: ROJO = %s · AZUL = %s" % (f["etiqueta"], ", ".join(cola.PAIS.get(c, c) for c in v["rojo"]), ", ".join(cola.PAIS.get(c, c) for c in v["azul"])))
        else: t.append("%s: %s" % (f["etiqueta"], "sí" if v is True else "no" if v is False else v))
    return " | ".join(t)
def formatos_de(m): return [FORMATOS[i] for i in (m.get("formatos") or []) if i in FORMATOS]
OPCIONALES = {"config_video", "agentes"}
API_PANEL = 2   # versión de la API de plugins que ofrece este DevIAs Panel
ESQUELETO = [  # (campo, tipo, para qué sirve)
    ("esquema", "número", "versión del esqueleto (1)"), ("api", "número", "versión de la API del DevIAs Panel que usa el plugin (1)"), ("id", "texto", "identificador (= nombre de la carpeta)"), ("nombre", "texto", "nombre que ve el usuario"), ("version", "texto", "versión del plugin"), ("descripcion", "texto", "qué videos genera"),
    ("instrucciones", "archivo", "INSTRUCCIONES.md: el método y las reglas para Claude"), ("formatos", "lista", "qué formatos soporta: short, largo (el panel define aspecto y duraciones)"), ("pipeline", "objeto", "comandos del plugin: borrador, voz, unir"),
    ("config_video", "lista (opcional)", "configuración que el plugin pide EN IDEAS para cada video (países que juegan, modo equipos, quién contra quién…): campos {id, tipo: paises|interruptor|opcion|numero|equipos|ganador|comentario, etiqueta, ayuda, defecto…}; lo que ya está en los ajustes del plugin no se repite aquí"),
    ("agentes", "objeto (opcional)", "los dos agentes del cerebro: {\"modulo\": \"agentes/agentes_plugin.py\"} con formato(ctx) -> mejor formato para la idea y diseno(ctx) -> mejor diseño del juego; devuelven {resumen, detalle, config, uso}"),
    ("tiempos", "texto", "regla de tiempos: «guion» = la escena se adapta a los tiempos del guion (el flujo de Mapas: borrador estimado → voz real → regrabar) o «juego» = el juego marca sus propios segundos"), ("pagina", "lista", "archivos del plugin donde la página de la escena expone lo que pide el grabador del panel: __ready, __frame(dt), __adv(n), __sim, __cues, __log"), ("voz", "objeto", "cómo usa la voz del DevIAs Panel: {\"modo\": \"json_manda\" | \"libre\"}. La voz, la mezcla y el render los hace el panel: el plugin NO trae scripts de voz, mezcla ni render"), ("titulos", "objeto", "tipos de título/descripción/etiquetas que aporta el plugin"), ("requisitos", "objeto", "python, servicios y archivos que necesita (el panel los detecta)"), ("ajustes", "lista", "campos del subpanel: id, tipo, etiqueta y ayuda (qué hace); opcional grupo, defecto, min, max, opciones")]
PIP = {"PIL": "pillow", "imageio_ffmpeg": "imageio-ffmpeg", "cv2": "opencv-python", "yaml": "pyyaml"}
def _plugin_dirs():
    for _ in range(4):   # la carpeta puede desaparecer un instante (disco ocupado, copia en curso): se reintenta y, si sigue sin estar, no se rompe el panel
        try:
            PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
            return sorted(d for d in PLUGINS_DIR.iterdir() if d.is_dir() and not d.name.startswith((".", "_")))
        except OSError: time.sleep(.4)
    return []
def validar_plugin(d):
    """-> (meta, errores). Un plugin es válido solo si cumple el esqueleto y los archivos que declara existen."""
    f = d / "plugin.json"
    if not f.exists(): return {}, ["falta plugin.json (la ficha del esqueleto)"]
    try: m = json.loads(f.read_text(encoding="utf-8"))
    except Exception as e: return {}, ["plugin.json no es un JSON válido: %s" % e]
    er = []
    for c, tp, _ in ESQUELETO:
        if c in OPCIONALES: continue
        if c not in m or m[c] in (None, "", [], {}): er.append("falta el campo «%s»" % c)
    if m.get("esquema") not in (1, None) and "esquema" in m: er.append("esquema %s no soportado (usa 1)" % m.get("esquema"))
    if "api" in m and m["api"] != API_PANEL: er.append("el plugin usa la API %s del DevIAs Panel y este panel ofrece la %s: actualiza el plugin (desde la API 2 la voz, la mezcla y el render son del panel y el plugin declara «tiempos» y «pagina»)" % (m["api"], API_PANEL))
    if m.get("id") and m["id"] != d.name: er.append("el id «%s» no coincide con la carpeta «%s»" % (m["id"], d.name))
    if isinstance(m.get("instrucciones"), str) and not (d / m["instrucciones"]).exists(): er.append("no existe el archivo de instrucciones «%s»" % m["instrucciones"])
    for x in (m.get("formatos") or []):
        if x not in FORMATOS: er.append("formato desconocido «%s» (el panel soporta: %s)" % (x, ", ".join(FORMATOS)))
    if isinstance(m.get("voz"), dict):
        if m["voz"].get("modo") not in ("json_manda", "libre"): er.append("voz.modo debe ser «json_manda» o «libre»")
        if "script" in m["voz"]: er.append("la voz es del DevIAs Panel: quita voz.script del plugin")
    if isinstance(m.get("pipeline"), dict) and "borrador" not in m["pipeline"]: er.append("pipeline.borrador no está definido")
    if isinstance(m.get("titulos"), dict) and not isinstance(m["titulos"].get("tipos"), dict): er.append("titulos.tipos debe ser un objeto {tipo: módulo}")
    for k, a in enumerate(m.get("ajustes") or []):
        if not isinstance(a, dict) or not all(y in a for y in ("id", "tipo", "etiqueta", "ayuda")): er.append("el ajuste #%d debe tener id, tipo, etiqueta y ayuda" % (k + 1))
        elif a["tipo"] not in ("numero", "interruptor", "opcion", "texto"): er.append("el ajuste «%s» tiene un tipo desconocido (numero, interruptor, opcion o texto)" % a["id"])
    for a in (m.get("requisitos") or {}).get("archivos", []):
        if not (d / a).exists(): er.append("requisito: no existe «%s»" % a)
    if not er: er = [c["grupo"] + ": " + c["texto"] for c in informe_plugin(d)["checks"] if not c["ok"]]
    return m, er

# ---------------- VERIFICACIÓN DE UN PLUGIN (informe punto por punto; si algo obligatorio falla, NO se instala ni se usa) ----------------
MOTOR_PROPIO = r"(unir|mix|mix_escena|mix_short|mezcla|grab|grabar|grab_fast|grab_gpu|grab_paralelo|grabar_rapido|regrabar_tramo|generar_voz_api|rehacer_frase|musica_fondo|voz_[a-z_]+)\.py"   # lo que hace el DevIAs Panel y un plugin no debe traer
def _ast_nombres(f):
    """Nombres definidos al nivel del módulo (def, asignaciones, imports) sin ejecutar el código; (None, error) si no compila."""
    import ast
    try: t = ast.parse(f.read_text(encoding="utf-8"))
    except Exception as e: return None, "no compila: %s" % str(e)[:90]
    n = {}
    for x in t.body:
        if isinstance(x, ast.FunctionDef): n[x.name] = [a.arg for a in x.args.args]
        elif isinstance(x, ast.Assign): [n.setdefault(y.id, None) for y in x.targets if isinstance(y, ast.Name)]
        elif isinstance(x, (ast.ImportFrom, ast.Import)): [n.setdefault((y.asname or y.name).split(".")[0], None) for y in x.names]
    return n, None
def informe_plugin(d):
    """-> {"ok": bool, "checks": [{"grupo","ok","texto"}]}. Revisa la ficha, los campos del esqueleto, los archivos declarados, los scripts (compilan y traen su interfaz) y los ajustes."""
    C = []
    def ck(g, ok, t): C.append({"grupo": g, "ok": bool(ok), "texto": t}); return bool(ok)
    f = d / "plugin.json"
    if not f.is_file(): ck("Ficha", False, "falta plugin.json (la ficha del esqueleto)"); return {"ok": False, "checks": C}
    try: m = json.loads(f.read_text(encoding="utf-8")); ck("Ficha", True, "plugin.json es un JSON válido")
    except Exception as e: ck("Ficha", False, "plugin.json no es un JSON válido: %s" % str(e)[:100]); return {"ok": False, "checks": C}
    for c, tp, _ in ESQUELETO:
        if c not in OPCIONALES: ck("Esqueleto", c in m and m[c] not in (None, "", [], {}), "campo «%s» (%s)" % (c, tp))
    cv_ = m.get("config_video") or []; ids_cv = [x.get("id") for x in cv_ if isinstance(x, dict)]
    if "config_video" in m:
        ck("Ideas", isinstance(m["config_video"], list), "config_video es una lista de campos")
        for x in (cv_ if isinstance(cv_, list) else []): ck("Ideas", isinstance(x, dict) and all(y in x for y in ("id", "tipo", "etiqueta", "ayuda")) and x["tipo"] in ("paises", "interruptor", "opcion", "numero", "equipos", "ganador", "comentario"), "config_video «%s» (%s) con etiqueta, ayuda y tipo válido" % ((x or {}).get("id"), (x or {}).get("tipo")))
        ck("Ideas", len(ids_cv) == len(set(ids_cv)), "config_video: ids sin repetir")
        rep_ = sorted(set(ids_cv) & {a.get("id") for a in (m.get("ajustes") or []) if isinstance(a, dict)}); ck("Ideas", not rep_, "config_video no repite ajustes del plugin" + ((": " + ", ".join(rep_)) if rep_ else ""))
    ck("Esqueleto", m.get("esquema") == 1, "esquema = 1 (versión del esqueleto)")
    ck("Escena", m.get("tiempos") in ("guion", "juego"), "tiempos = «guion» (la escena se adapta al guion) o «juego» (el juego marca sus segundos)")
    pag = [x for x in (m.get("pagina") or []) if isinstance(x, str)]; txt = "".join((d / x).read_text(encoding="utf-8", errors="ignore") for x in pag if (d / x).is_file())
    ck("Escena", bool(pag) and all((d / x).is_file() for x in pag), "archivos de la página de la escena existen (pagina)")
    for tk_ in ("__ready", "__frame", "__adv", "__sim", "__cues", "__log"): ck("Escena", tk_ in txt, "la página expone «%s» (lo que pide el grabador del panel)" % tk_)
    ck("Esqueleto", m.get("api") == API_PANEL, "api = %s (la que ofrece este DevIAs Panel; el plugin dice %s)" % (API_PANEL, m.get("api")))
    ck("Esqueleto", m.get("id") == d.name, "el id «%s» coincide con la carpeta «%s»" % (m.get("id"), d.name))
    ck("Esqueleto", bool(m.get("formatos")) and all(x in FORMATOS for x in (m.get("formatos") or [])), "formatos conocidos por el panel (%s)" % ", ".join(FORMATOS))
    def arch(g, rel, t):
        ok = bool(rel) and (d / str(rel)).exists(); ck(g, ok, "%s: %s" % (t, rel or "(sin declarar)")); return ok
    if m.get("imagen"): arch("Archivos", m.get("imagen"), "imagen de portada")
    arch("Archivos", m.get("instrucciones"), "instrucciones")
    for x in m.get("reglas") or []: arch("Archivos", x, "regla")
    for x in m.get("referencias") or []: arch("Archivos", x, "referencia")
    if m.get("memoria"): arch("Archivos", m.get("memoria"), "memoria")
    for x in (m.get("requisitos") or {}).get("archivos", []): arch("Archivos", x, "requisito")
    for k_, v_ in (m.get("plantillas") or {}).items():
        if isinstance(v_, str): arch("Archivos", v_, "plantillas.%s" % k_)
    pl = (m.get("pipeline") or {}).get("script"); idm = (m.get("ideas") or {}).get("modulo")
    vz_ = m.get("voz") if isinstance(m.get("voz"), dict) else {}; ck("Motor del panel", vz_.get("modo") in ("json_manda", "libre"), "voz.modo declarado (json_manda o libre): la voz la genera el DevIAs Panel")
    pro = sorted(str(f.relative_to(d)).replace(chr(92), "/") for f in d.rglob("*.py") if "__pycache__" not in f.parts and re.fullmatch(MOTOR_PROPIO, f.name)) + (["voz/"] if (d / "voz").exists() else []) + (["voz.script"] if "script" in vz_ else [])
    ck("Motor del panel", not pro, "el plugin NO trae su propio motor de voz, mezcla o render (los hace el DevIAs Panel)" + ((": quita " + ", ".join(pro[:4]) + ("…" if len(pro) > 4 else "")) if pro else ""))
    for g_, rel in (("Pipeline", pl),):
        if arch(g_, rel, "script"):
            n_, err = _ast_nombres(d / rel); ck(g_, n_ is not None, "el script compila" if n_ is not None else "el script " + str(err))
    ck("Pipeline", isinstance(m.get("pipeline"), dict) and "borrador" in (m.get("pipeline") or {}), "pipeline.borrador está definido")
    if idm and arch("Ideas", idm, "módulo de ideas"):
        n_, err = _ast_nombres(d / idm)
        if n_ is None: ck("Ideas", False, "el módulo " + str(err))
        else: ck("Ideas", "mas_ideas" in n_, "define mas_ideas(formato, n, usados)"); ck("Ideas", "ideas_de" in n_, "define ideas_de(texto, formato)")
    tt = m.get("titulos") or {}; mods = sorted(set((tt.get("tipos") or {}).values())) if isinstance(tt.get("tipos"), dict) else []
    ck("Títulos", bool(mods), "titulos.tipos asigna un módulo a cada tipo de video")
    for mn in mods:
        rel = "%s/%s.py" % (tt.get("dir", "titulos"), mn)
        if arch("Títulos", rel, "módulo de títulos"):
            n_, err = _ast_nombres(d / rel)
            if n_ is None: ck("Títulos", False, "el módulo %s %s" % (mn, err))
            else:
                ck("Títulos", "generar" in n_, "%s define generar(pid, f, lote, usados, largo)" % mn)
                if n_.get("generar") is not None: ck("Títulos", len(n_["generar"]) >= 4, "%s: generar recibe pid, f, lote y usados" % mn)
    ag_ = m.get("agentes")
    if ag_ is not None:
        ref_ = (ag_ or {}).get("modulo") if isinstance(ag_, dict) else None
        if ck("Agentes", bool(ref_) and (d / str(ref_)).is_file(), "módulo de agentes: %s" % ref_):
            n_, err = _ast_nombres(d / ref_); ck("Agentes", n_ is not None, "el módulo compila" if n_ is not None else "el módulo " + str(err))
            if n_ is not None: ck("Agentes", "formato" in n_ and "diseno" in n_, "define formato(ctx) y diseno(ctx)")
    ids = []
    for k, a in enumerate(m.get("ajustes") or []):
        if not isinstance(a, dict) or not all(y in a for y in ("id", "tipo", "etiqueta", "ayuda")): ck("Ajustes", False, "el ajuste #%d debe tener id, tipo, etiqueta y ayuda" % (k + 1)); continue
        ids.append(a["id"]); ok = a["tipo"] in ("numero", "interruptor", "opcion", "texto") and str(a["ayuda"]).strip() != ""
        if a["tipo"] == "numero" and "defecto" in a: ok = ok and isinstance(a["defecto"], (int, float)) and a.get("min", a["defecto"]) <= a["defecto"] <= a.get("max", a["defecto"])
        if a["tipo"] == "opcion": ok = ok and bool(a.get("opciones")) and a.get("defecto", a["opciones"][0]) in a["opciones"]
        ck("Ajustes", ok, "ajuste «%s» (%s) con ayuda y valor por defecto válido" % (a["id"], a["tipo"]))
    ck("Ajustes", len(ids) == len(set(ids)), "no hay ajustes con el mismo id")
    for rq in (m.get("requisitos") or {}).get("python", []): ck("Requisitos", True, "usa el paquete de Python «%s» (se detecta al instalar)" % rq)
    return {"ok": all(c["ok"] for c in C), "checks": C}

def requisitos_plugin(d, m):
    out = []; rq = m.get("requisitos") or {}
    for mod in rq.get("python", []): out.append({"tipo": "python", "nombre": mod, "ok": importlib.util.find_spec(mod) is not None, "pip": PIP.get(mod, mod)})
    for sv in rq.get("servicios", []): out.append({"tipo": "servicio", "nombre": sv, "ok": voice_up() if sv == "voice-studio" else True})
    for a in rq.get("archivos", []): out.append({"tipo": "archivo", "nombre": a, "ok": (d / a).exists()})
    return out
def estado_plugins():
    e = jload("plugins_estado.json", {}); return e if isinstance(e, dict) else {}
def imagen_plugin(d, m):
    """Imagen de portada del plugin (opcional): la que declara «imagen» en plugin.json o, si no, imagen/portada/icono (png, jpg, webp, svg) en la raíz. None = el panel dibuja una portada por defecto."""
    cand = [m.get("imagen")] if m.get("imagen") else [n + e for n in ("imagen", "portada", "icono") for e in (".png", ".jpg", ".jpeg", ".webp", ".svg")]
    for c in cand:
        if c and isinstance(c, str):
            f = (d / c).resolve()
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".svg") and f.is_relative_to(d.resolve()): return f
    return None
def plugins_info(detalle=False):
    out = []; est = estado_plugins()
    for d in _plugin_dirs():
        fs = [f for f in d.rglob("*") if f.is_file() and "__pycache__" not in f.parts]; m, er = validar_plugin(d); rq = requisitos_plugin(d, m) if not er else []
        vals = dict({a["id"]: a.get("defecto") for a in m.get("ajustes", []) if isinstance(a, dict) and "id" in a}, **((est.get("ajustes") or {}).get(d.name) or {}))
        o = {"id": d.name, "nombre": m.get("nombre") or d.name, "version": m.get("version", ""), "desc": m.get("descripcion", ""), "valido": not er, "falta": er, "activo": est.get("activo") == d.name, "requisitos": rq, "formatos": formatos_de(m), "ajustes": m.get("ajustes", []), "config_video": m.get("config_video", []), "valores": vals,
             "imagen": imagen_plugin(d, m) is not None, "archivos": len(fs), "mb": round(sum(f.stat().st_size for f in fs) / 1048576, 1), "actualizado": time.strftime("%Y-%m-%d %H:%M", time.localtime(max([f.stat().st_mtime for f in fs] + [0])))}
        if detalle: o["lista"] = sorted(str(f.relative_to(d)).replace(chr(92), "/") for f in fs)[:400]
        out.append(o)
    return out

# ---------------- CICLO DE VIDA DE UN PLUGIN: instalar (.zip), actualizar, desinstalar ----------------

def revisar_plugin_zip(data):
    """PRECARGA: lee el paquete SIN instalar nada y dice qué es. -> {tipo: plugin|skill-claude|instalador-devpanel|zip-otro|no-zip, es_plugin, ok, id, nombre, version, existe, version_instalada, informe, mensaje}.
    El DevIAs Panel solo instala lo que detecta como plugin y que cumple el esqueleto."""
    tmp = pathlib.Path(TMPD) / ("rev_%d" % int(time.time() * 1000)); tmp.mkdir(parents=True, exist_ok=True)
    try:
        try: z = zipfile.ZipFile(io.BytesIO(data)); nombres = z.namelist()
        except Exception: return {"es_plugin": False, "ok": False, "tipo": "no-zip", "mensaje": "El archivo no es un .zip válido: el DevIAs Panel solo instala plugins empaquetados en .zip."}
        for n in nombres:
            if not (tmp / n).resolve().is_relative_to(tmp.resolve()): return {"es_plugin": False, "ok": False, "tipo": "zip-otro", "mensaje": "El .zip trae rutas peligrosas: no se abre."}
        z.extractall(tmp)
        raiz = next((c for c in [tmp] + sorted(x for x in tmp.iterdir() if x.is_dir()) if (c / "plugin.json").exists()), None)
        if not raiz:
            base = [c for c in [tmp] + sorted(x for x in tmp.iterdir() if x.is_dir())]
            if any((c / "SKILL.md").exists() for c in base): return {"es_plugin": False, "ok": False, "tipo": "skill-claude", "mensaje": "Esto NO es un plugin del DevIAs Panel: es un skill de Claude (trae SKILL.md y no plugin.json). Hay que convertirlo a plugin (ficha plugin.json) para poder instalarlo."}
            if any((c / "servidor.py").exists() and (c / "instalar.py").exists() for c in base): return {"es_plugin": False, "ok": False, "tipo": "instalador-devpanel", "mensaje": "Esto NO es un plugin: es el instalador del propio DevIAs Panel (servidor.py + instalar.py). Los plugins se instalan aquí; el panel se instala en otra carpeta."}
            return {"es_plugin": False, "ok": False, "tipo": "zip-otro", "mensaje": "Esto NO es un plugin del DevIAs Panel: el .zip no trae plugin.json (la ficha que identifica a un plugin)."}
        try: m = json.loads((raiz / "plugin.json").read_text(encoding="utf-8"))
        except Exception as e: return {"es_plugin": True, "ok": False, "tipo": "plugin", "mensaje": "Trae plugin.json pero no es un JSON válido: %s" % str(e)[:100], "informe": [{"grupo": "Ficha", "ok": False, "texto": "plugin.json no es un JSON válido"}]}
        pid = str(m.get("id", "")).strip(); idok = re.fullmatch(r"[a-z0-9][a-z0-9\-]{1,60}", pid) is not None
        r_ = {"es_plugin": True, "tipo": "plugin", "id": pid, "nombre": m.get("nombre", pid), "version": m.get("version", ""), "descripcion": m.get("descripcion", ""), "formatos": m.get("formatos", [])}
        if not idok: r_.update(ok=False, informe=[{"grupo": "Ficha", "ok": False, "texto": "el id «%s» no es válido (minúsculas, números y guiones)" % pid}], mensaje="Es un plugin, pero su id no es válido."); return r_
        stage = tmp / "_stage" / pid; shutil.copytree(raiz, stage); inf = informe_plugin(stage); dest = PLUGINS_DIR / pid; r_.update(informe=inf["checks"], ok=inf["ok"], existe=dest.exists())
        if dest.exists():
            try: r_["version_instalada"] = json.loads((dest / "plugin.json").read_text(encoding="utf-8")).get("version", "")
            except Exception: r_["version_instalada"] = "?"
        mal = [c for c in inf["checks"] if not c["ok"]]
        r_["mensaje"] = ("Es un plugin del DevIAs Panel y cumple la estructura." if inf["ok"] else "Es un plugin, pero NO cumple la estructura del DevIAs Panel (%d fallo%s): no se puede instalar." % (len(mal), "" if len(mal) == 1 else "s"))
        return r_
    finally: shutil.rmtree(tmp, ignore_errors=True)

def instalar_plugin_zip(data, actualizar=False):
    tmp = pathlib.Path(TMPD) / ("plug_%d" % int(time.time() * 1000)); tmp.mkdir(parents=True, exist_ok=True)
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
        for n in z.namelist():
            if not (tmp / n).resolve().is_relative_to(tmp.resolve()): return {"ok": False, "error": "El .zip trae rutas peligrosas."}
        z.extractall(tmp)
    except Exception as e: return {"ok": False, "error": "No pude leer el .zip: %s" % e}
    raiz = next((c for c in [tmp] + sorted(x for x in tmp.iterdir() if x.is_dir()) if (c / "plugin.json").exists()), None)
    if not raiz: shutil.rmtree(tmp, ignore_errors=True); return {"ok": False, "error": "El .zip no trae plugin.json: no es un plugin del DevIAs Panel."}
    try: m = json.loads((raiz / "plugin.json").read_text(encoding="utf-8"))
    except Exception as e: shutil.rmtree(tmp, ignore_errors=True); return {"ok": False, "error": "plugin.json no es un JSON válido: %s" % e}
    pid = str(m.get("id", "")).strip()
    if not re.fullmatch(r"[a-z0-9][a-z0-9\-]{1,60}", pid): shutil.rmtree(tmp, ignore_errors=True); return {"ok": False, "error": "El id del plugin («%s») no es válido (usa minúsculas, números y guiones)." % pid}
    stage = tmp / "_stage" / pid; shutil.copytree(raiz, stage); inf = informe_plugin(stage)
    if not inf["ok"]:   # no cumple: NO se instala nada
        mal = [c["texto"] for c in inf["checks"] if not c["ok"]]; shutil.rmtree(tmp, ignore_errors=True)
        return {"ok": False, "id": pid, "informe": inf["checks"], "error": "El paquete NO cumple la estructura del DevIAs Panel y no se instaló (%d fallo%s): %s" % (len(mal), "" if len(mal) == 1 else "s", "; ".join(mal[:3]) + ("…" if len(mal) > 3 else ""))}
    dest = PLUGINS_DIR / pid; viejo = None
    if dest.exists():
        if not actualizar:
            ver = ""
            try: ver = json.loads((dest / "plugin.json").read_text(encoding="utf-8")).get("version", "")
            except Exception: pass
            shutil.rmtree(tmp, ignore_errors=True); return {"ok": False, "existe": True, "id": pid, "informe": inf["checks"], "version_instalada": ver, "version_nueva": m.get("version"), "error": "«%s» ya está instalado (versión %s). Se puede actualizar a la %s." % (m.get("nombre", pid), ver, m.get("version"))}
        pap = ROOT / "_papelera"; pap.mkdir(exist_ok=True); viejo = pap / ("%s_%s" % (pid, time.strftime("%Y%m%d_%H%M%S"))); shutil.move(str(dest), str(viejo))
    shutil.copytree(raiz, dest); shutil.rmtree(tmp, ignore_errors=True)
    m2, er = validar_plugin(dest)
    if er:   # no cumple el esqueleto: se deshace todo
        shutil.rmtree(dest, ignore_errors=True)
        if viejo: shutil.move(str(viejo), str(dest))
        return {"ok": False, "error": "El plugin no cumple el esqueleto del DevIAs Panel y no se instaló: " + "; ".join(er[:4]), "falta": er}
    logact(None, "Plugin %s: «%s» v%s." % ("actualizado" if viejo else "instalado", m2.get("nombre", pid), m2.get("version", "")), "info")
    return {"ok": True, "id": pid, "actualizado": bool(viejo), "version": m2.get("version"), "informe": inf["checks"]}
def desinstalar_plugin(pid):
    d = PLUGINS_DIR / pid
    if not d.is_dir(): return {"ok": False, "error": "El plugin no existe."}
    if estado_plugins().get("activo") == pid: return {"ok": False, "error": "Primero desactívalo: un plugin activo no se puede desinstalar."}
    usan = [p_["titulo"] for p_ in jload("proyectos.json", []) if p_.get("plugin") == pid]
    pap = ROOT / "_papelera"; pap.mkdir(exist_ok=True); dst = pap / ("%s_%s" % (pid, time.strftime("%Y%m%d_%H%M%S")))
    try: shutil.move(str(d), str(dst))
    except Exception as e_: return {"ok": False, "error": "No pude mover el plugin a _papelera (¿hay un archivo o terminal abierto dentro de su carpeta?): %s" % e_}
    est = estado_plugins(); (est.get("ajustes") or {}).pop(pid, None); jsave("plugins_estado.json", est)
    logact(None, "Plugin desinstalado: «%s» (guardado en _papelera, se puede recuperar)." % pid, "info")
    return {"ok": True, "papelera": str(dst), "videos_afectados": usan}

def plugin_zip(pid):
    d = PLUGINS_DIR / pid
    if not d.is_dir(): return None
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(d.rglob("*")):
            if f.is_file() and "__pycache__" not in f.parts and not f.name.endswith((".key", ".env")): z.write(f, "%s/%s" % (pid, str(f.relative_to(d)).replace(chr(92), "/")))
    return bio.getvalue()


def plugin_activo():
    """(carpeta, ficha) del plugin activo y válido, o (None, None)."""
    sid = estado_plugins().get("activo")
    if not sid: return None, None
    d = PLUGINS_DIR / sid; m, er = validar_plugin(d)
    return (d, m) if not er else (None, None)
_MODS = {}
def modulo_plugin(d, rel):
    """Carga un módulo .py del plugin (su carpeta entra al sys.path para que sus imports funcionen)."""
    f = d / rel
    if not f.exists(): return None
    clave = str(f.resolve()); mt = f.stat().st_mtime
    if clave in _MODS and _MODS[clave][0] == mt: return _MODS[clave][1]
    import importlib.util as iu
    for x in (str(f.parent), str(d)):
        if x not in sys.path: sys.path.insert(0, x)
    sp = iu.spec_from_file_location("plugin_%s_%s" % (d.name.replace("-", "_"), f.stem), f); mod = iu.module_from_spec(sp); sp.loader.exec_module(mod); _MODS[clave] = (mt, mod); return mod
def env_plugin(p):
    """Entorno para ejecutar herramientas DE UN PLUGIN: el DevIAs Panel, el plugin y los ajustes del subpanel (perfil/velocidad de voz, estilos…)."""
    d_, m_ = plugin_de(p) if isinstance(p, dict) else plugin_activo(); e = dict(ENV)
    if d_:
        aj = dict({x["id"]: x.get("defecto") for x in m_.get("ajustes", [])}, **((estado_plugins().get("ajustes") or {}).get(d_.name) or {})); e.update(DEVPANEL=str(ROOT), PLUGIN_DIR=str(d_), PLUGIN_AJUSTES=json.dumps(aj, ensure_ascii=False))
    return e
def plugin_de(p):
    """Plugin de un proyecto. ESTRICTO: si el video es de un plugin que NO está activo, no se usa nada de ningún plugin (evita conflictos con otro plugin activo)."""
    sid = p.get("plugin") if isinstance(p, dict) else None
    if sid and sid != estado_plugins().get("activo"): return None, None
    return plugin_activo()
def bloqueo_plugin(pid):
    """Mensaje de error si el video pertenece a un plugin desactivado; None si se puede trabajar."""
    if not pid: return None
    p = proyecto(pid)
    if not p or not p.get("plugin") or p["plugin"] == estado_plugins().get("activo"): return None
    nom = p["plugin"]
    try: nom = validar_plugin(PLUGINS_DIR / p["plugin"])[0].get("nombre") or nom
    except Exception: pass
    return {"error": "Este video es del plugin «%s», que está desactivado. Actívalo en Plugins para generar voz, unir, regrabar o títulos (así no se mezcla con otro plugin)." % nom, "plugin_inactivo": p["plugin"]}
PLUGIN_RUTAS = ("/api/rehacer_todo", "/api/generar_voz", "/api/conforme", "/api/rehacer_parte", "/api/job", "/api/mejora", "/api/escena", "/api/titulos", "/api/capturas", "/api/guion_ia")
SIN_PLUGIN = {"error": "No hay un plugin activo. Ve a Plugins y activa uno para poder generar ideas, videos y títulos.", "sin_plugin": True}


# ---------------- INSTALACIÓN del DevIAs Panel (2026-11-20) ----------------
def info_instalacion():
    cfg = jload("devpanel.json", {}); bat = ROOT / "iniciar_devpanel.bat"
    return {"ruta": str(ROOT), "puerto": cfg.get("puerto", PORT), "python": cfg.get("python", PY), "instalado": cfg.get("instalado"), "bat_existe": bat.exists(), "bat": str(bat), "bat_detener": (ROOT / "detener_devpanel.bat").exists(), "tmp": TMPD}
NUCLEO = ["servidor.py", "pedido.py", "escucha.py", "cola.py", "titulos_base.py", "progreso.py", "chequeo.py", "capturas_ffmpeg.py", "vigila_log.py", "instalar.py", "instalar.bat", "voz_config.json", "requisitos.py", "GUIA_INSTALACION.md", "SKILL.md"]
def devpanel_zip():
    """Instalador del DevIAs Panel: solo el núcleo (código + vista + grabador); SIN plugins, videos ni datos. Al ejecutar instalar.bat genera el .bat de encendido."""
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for n in NUCLEO:
            if (ROOT / n).exists(): z.write(ROOT / n, "devpanel/" + n)
        for f in sorted((ROOT / "grabador").glob("*.py")): z.write(f, "devpanel/grabador/" + f.name)
        for f in sorted((ROOT / "motor").glob("*.py")): z.write(f, "devpanel/motor/" + f.name)
        for f in sorted((ROOT / "static").iterdir()):
            if f.is_file() and not re.search(r"\.(bak|pre_diseno)", f.name): z.write(f, "devpanel/static/" + f.name)
        z.writestr("devpanel/plugins/LEEME.txt", "Aquí van los plugins (cada uno en su carpeta con un plugin.json). El panel los detecta solo y los muestra en la pestaña Plugins.\\nDescarga un plugin desde la pestaña Plugins de otro DevIAs Panel y descomprímelo aquí.")
        z.writestr("devpanel/LEEME_INSTALAR.md", "# DevIAs Panel\\n1. Instala Python 3.10 o superior (python.org).\\n2. Haz doble clic en **instalar.bat**. Crea las carpetas, comprueba los paquetes y genera **iniciar_devpanel.bat** (y detener_devpanel.bat).\\n   Para instalar también los paquetes que falten:  `instalar.bat --instalar-paquetes`   · acceso directo en el escritorio: `instalar.bat --acceso-directo`.\\n3. Enciende el panel con **iniciar_devpanel.bat**: se abre http://localhost:8820/static/admin.html\\n4. Pon un plugin en la carpeta `plugins/` y actívalo desde la pestaña Plugins.\\n\\nSi mueves la carpeta a otro lugar, vuelve a ejecutar instalar.bat para regenerar los .bat con las rutas nuevas.\\nPara las voces hace falta Voice Studio (API en 127.0.0.1:3900); el panel lo enciende solo si está instalado.\\n")
    return bio.getvalue()



def hacer_borrador_voz(p):
    """Pega la voz real al borrador (sin volver a grabar). Solo si el video se grabó DESPUÉS de medir la voz (mismos tiempos) y el «borrador con voz» quedó viejo."""
    c = carpeta(p); mu = c / (p.get("video_mudo") or "x"); wav = c / "voz" / "voz_completa.wav"; tj = c / "audiolibro" / "tiempos.json"
    if not (mu.exists() and wav.exists() and tj.exists()): return False
    try:
        if json.loads(tj.read_text(encoding="utf-8")).get("estimado"): return False
    except Exception: return False
    if mu.stat().st_mtime < tj.stat().st_mtime - 2 or time.time() - mu.stat().st_mtime < 25: return False   # grabado con tiempos estimados, o todavía escribiéndose
    bv = c / "salida_mudo" / "borrador_voz.mp4"
    if bv.exists() and bv.stat().st_mtime >= mu.stat().st_mtime - 2: return False
    import imageio_ffmpeg
    tmp = bv.with_suffix(".tmp.mp4"); r = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(mu), "-i", str(wav), "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", str(tmp)], capture_output=True, text=True)
    if r.returncode != 0 or not tmp.exists(): print("aviso borrador_voz:", r.stderr[-200:]); return False
    os.replace(tmp, bv)
    ps = jload("proyectos.json", [])
    for x in ps:
        if x["id"] == p["id"]: x["borrador_voz"] = "salida_mudo/borrador_voz.mp4"; x["borrador_voz_t"] = int(bv.stat().st_mtime)
    jsave("proyectos.json", ps); return True
def autoreparar_borradores_voz():
    if any(j["estado"] == "corriendo" for j in JOBS.values()): return
    for p in jload("proyectos.json", []):
        if p.get("carpeta") and p.get("estado") != "espera" and (not p.get("plugin") or p["plugin"] == estado_plugins().get("activo")):
            try: hacer_borrador_voz(p)
            except Exception as e: print("aviso borrador_voz:", e)

# ---------------- AVISOS DE CAMBIOS EN EL BORRADOR (2026-11-20) ----------------
# Cada vez que un video se vuelve a grabar (borrador, borrador con voz o final) el panel lo AVISA (campana, aviso en pantalla y bitácora) para que se sepa que los cambios ya pasaron.
# Claude puede añadir qué cambió con:  python pedido.py IDEA PCT "msg" --proyecto ID --cambio "texto"  (se muestra en el aviso).
def _versiones(p):
    c = carpeta(p); out = {}
    for k, rel in (("borrador", p.get("video_mudo")), ("borrador_voz", p.get("borrador_voz")), ("final", p.get("video_final"))):
        f = c / (rel or "x")
        if rel and f.exists(): out[k] = int(f.stat().st_mtime)
    return out
_NOTIF_LOCK = threading.Lock()
def detectar_cambios_video():
    with _NOTIF_LOCK:
        est = jload("notif_versiones.json", {}); pend = jload("cambios_pendientes.json", {}); nuevo = False
        for p in jload("proyectos.json", []):
            if p.get("estado") == "espera" or not p.get("carpeta"): continue
            ver = _versiones(p); ant = est.get(p["id"])
            if ant is None: est[p["id"]] = ver; nuevo = True; continue
            for k, t in ver.items():
                if t > ant.get(k, 0) + 1:
                    ch = [x for x in pend.get(p["id"], [])]; pend.pop(p["id"], None)
                    what = {"borrador": "Borrador actualizado", "borrador_voz": "Borrador CON VOZ actualizado", "final": "Video final actualizado"}[k]
                    msg = "%s: «%s» ya tiene los cambios nuevos.%s Recarga el video para verlos." % (what, p.get("titulo", p["id"])[:70], (" Cambios: " + "; ".join(ch) + ".") if ch else "")
                    logact(p.get("idea"), msg, "borrador", proyecto=p["id"], version=t, cambios=ch); nuevo = True
                    break
            est[p["id"]] = ver
        if nuevo: jsave("notif_versiones.json", est); jsave("cambios_pendientes.json", pend)
def _vigila_versiones():
    while True:
        try: autoreparar_borradores_voz(); detectar_cambios_video()
        except Exception as e: print("aviso versiones:", e)
        time.sleep(8)

# ---------------- HTTP ----------------
class H(http.server.BaseHTTPRequestHandler):
    server_version = "PanelVideos/1.0"
    def log_message(self, *a): pass
    def _json(self, obj, code=200):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8"); self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8"); self.send_header("Content-Length", str(len(b))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)
    def _descargar(self, path, nombre):   # entrega el archivo como descarga
        if not path.is_file(): self.send_error(404); return
        self.send_response(200); self.send_header("Content-Type", "video/mp4"); self.send_header("Content-Length", str(path.stat().st_size)); self.send_header("Content-Disposition", 'attachment; filename="%s"' % nombre); self.end_headers()
        try:
            with open(path, "rb") as f:
                while True:
                    b = f.read(65536)
                    if not b: break
                    self.wfile.write(b)
        except Exception: pass
    def _file(self, path):
        if not path.is_file(): self.send_error(404); return
        size = path.stat().st_size; start, end, code = 0, size - 1, 200; rng = self.headers.get("Range")
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1): start = int(m.group(1))
                if m.group(2): end = min(size - 1, int(m.group(2)))
                if not m.group(1) and m.group(2): start = max(0, size - int(m.group(2))); end = size - 1
                code = 206
        ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        if path.suffix in (".js", ".mjs"): ctype = "text/javascript; charset=utf-8"
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Accept-Ranges", "bytes"); self.send_header("Content-Length", str(end - start + 1)); self.send_header("Cache-Control", "no-store")
        if code == 206: self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
        self.end_headers()
        try:
            with open(path, "rb") as f:
                f.seek(start); left = end - start + 1
                while left > 0:
                    b = f.read(min(65536, left))
                    if not b: break
                    self.wfile.write(b); left -= len(b)
        except (ConnectionResetError, BrokenPipeError): pass
    def _safe(self, base, rel):
        p = (base / urllib.parse.unquote(rel).lstrip("/")).resolve()
        return p if str(p).startswith(str(base.resolve())) else None
    def do_GET(self):
        u = urllib.parse.urlparse(self.path); q = urllib.parse.parse_qs(u.query); pa = u.path
        if pa in PLUGIN_RUTAS:
            e_ = bloqueo_plugin(q.get("id", [""])[0])
            if e_: return self._json(e_, 409)
        if pa == "/" : return self._file(STATIC / "admin.html")   # solo existe la vista v2 (se quitó la vista clásica)
        if pa.startswith("/static/"): p = self._safe(STATIC, pa[8:]); return self._file(p) if p else self.send_error(403)
        if pa.startswith("/series/"):
            p = self._safe(SERIES, pa[8:]); return self._file(p) if p else self.send_error(403)
        if pa == "/api/instalacion": return self._json(info_instalacion())
        if pa == "/api/hardware": return self._json(hardware())
        if pa == "/api/temp": return self._json({"temp_dir": _cfg_json().get("temp_dir") or "", "efectivo": TMPD, "defecto": str(ROOT / "_tmp")})
        if pa == "/api/senal": return self._json({"senal_min": _senal_min(), "primer_uso": bool(jload("devpanel.json", {}).get("primer_uso"))})
        if pa == "/api/devpanel_zip":
            data = devpanel_zip(); self.send_response(200); self.send_header("Content-Type", "application/zip"); self.send_header("Content-Length", str(len(data))); self.send_header("Content-Disposition", 'attachment; filename="devpanel-instalador-%s.zip"' % time.strftime("%Y%m%d")); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(data); return
        if pa == "/api/esqueleto": return self._json([{"campo": c, "tipo": t, "para": p_} for c, t, p_ in ESQUELETO])
        if pa == "/api/plugins": return self._json(plugins_info(q.get("detalle", [""])[0] == "1"))
        if pa == "/api/plugin_imagen":   # portada del plugin (si la trae)
            d_ = PLUGINS_DIR / q.get("id", [""])[0]; f_ = imagen_plugin(d_, validar_plugin(d_)[0] or {}) if d_.is_dir() else None
            if not f_: return self._json({"error": "sin imagen"}, 404)
            b_ = f_.read_bytes(); self.send_response(200); self.send_header("Content-Type", mimetypes.guess_type(str(f_))[0] or "image/png"); self.send_header("Content-Length", str(len(b_))); self.send_header("Cache-Control", "no-cache"); self.end_headers(); self.wfile.write(b_); return
        if pa == "/api/voz_config": c_ = dict(jload("voz_config.json", {})); c_["hf_token_set"] = bool(c_.pop("hf_token", "")); c_.setdefault("motor", "voicestudio"); return self._json(c_)   # el token nunca sale al navegador
        if pa == "/api/paises": cola.cargar_paises(); return self._json(sorted(({"cod": k, "nom": v} for k, v in cola.PAIS.items()), key=lambda x: x["nom"]))
        if pa == "/api/plugin_verificar":   # informe de un plugin YA instalado
            d_ = PLUGINS_DIR / q.get("id", [""])[0]
            return self._json(informe_plugin(d_) if d_.is_dir() else {"ok": False, "checks": [{"grupo": "Ficha", "ok": False, "texto": "el plugin no existe"}]})
        if pa == "/api/plugin_zip":
            data = plugin_zip(q.get("id", [""])[0])
            if data is None: return self._json({"error": "paquete no existe"}, 404)
            self.send_response(200); self.send_header("Content-Type", "application/zip"); self.send_header("Content-Length", str(len(data))); self.send_header("Content-Disposition", 'attachment; filename="plugin-%s-%s.zip"' % (q.get("id", ["x"])[0], time.strftime("%Y%m%d"))); self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(data); return
        if pa == "/api/actividad":
            ref = q.get("id", [""])[0]; ped_ = [x for x in jload("pedidos.json", []) if ref and x.get("idea") == ref and x.get("tipo") == "video"]
            return self._json({"etapas": ETAPAS, "log": [x for x in jload("actividad.json", []) if not ref or x.get("idea") in (ref, None)][-150:], "codigo": archivos_recientes(ref, (ped_[-1].get("ts") or 0) if ped_ else 0) if ref else {"carpeta": None, "archivos": []}})
        if pa == "/api/archivo":   # ver el código que Claude generó (solo lectura, dentro de series/)
            f = self._safe(SERIES, (q.get("c", [""])[0] + "/" + q.get("f", [""])[0]).strip("/"))
            if not f or f.suffix not in EXT_COD or not f.is_file(): return self._json({"error": "no disponible"}, 404)
            tx = f.read_text(encoding="utf-8", errors="replace").splitlines(); return self._json({"archivo": f.name, "lineas": len(tx), "texto": "\n".join(tx[:400]), "cortado": len(tx) > 400})
        if pa == "/api/memoria":
            rl, rt = _ram_libre(); vl, vt = _vram(); return self._json({"ram_libre_gb": rl, "ram_total_gb": rt, "vram_libre_gb": vl, "vram_total_gb": vt, "voice_studio": voice_up(), "voice_pid": _pid_3900()})
        if pa == "/api/estado": 
            try: cv = time.time() - json.loads((ROOT / "claude_vivo.json").read_text(encoding="utf-8"))["ts"] < 15
            except Exception: cv = False
            try: vh = float(json.loads((ROOT / "vivo_hasta.json").read_text(encoding="utf-8"))["hasta"])
            except Exception: vh = 0
            try: mon = time.time() - json.loads((ROOT / "claude_monitor.json").read_text(encoding="utf-8"))["ts"] < 15
            except Exception: mon = False
            return self._json({"senal_min": _senal_min(), "primer_uso": bool(jload("devpanel.json", {}).get("primer_uso")), "voice_studio": voice_up(), "claude": cv, "monitor": mon, "parados": list(PARADOS.values()), "hora": time.strftime("%H:%M:%S"), "vivo_resta": max(0, int(vh - time.time())), "plugin_activo": (lambda dm: {"id": dm[0].name, "nombre": dm[1].get("nombre")} if dm[0] else None)(plugin_activo())})
        if pa == "/api/catalogo":
            act_ = estado_plugins().get("activo")   # las IDEAS son del plugin que las trajo: con otro plugin activo (o ninguno) no se ven; vuelven al reactivar el suyo
            cat = [i for i in jload("catalogo.json", []) if i.get("estado") != "idea" or (act_ and i.get("plugin") == act_)]
            for i in cat:
                if i.get("estado") != "hecho" and (not i.get("config") or "mapa2d" not in i["config"]): i["config"] = cola.cfg_default(i["formato"], i.get("titulo"), i.get("desc")); i["config_def"] = True
            return self._json(cat)
        if pa == "/api/pedidos": return self._json(jload("pedidos.json", []))
        if pa == "/api/referencias": return self._json(jload("referencias.json", []))
        if pa == "/api/proyectos":
            try: detectar_cambios_video()
            except Exception: pass
            ps = jload("proyectos.json", []); ideas_reales = set(x.get("idea") for x in ps if x.get("estado") != "espera" and x.get("idea")); ps = [x for x in ps if not (x.get("estado") == "espera" and x.get("idea") in ideas_reales)]
            act_ = estado_plugins().get("activo")
            for p in ps:
                p["plugin_ok"] = (not p.get("plugin")) or p["plugin"] == act_
                c = carpeta(p); p["existe_final"] = (c / (p.get("video_final") or "x")).exists(); p["final_t"] = int(((c / (p.get("video_final") or "x")).stat().st_mtime) if p["existe_final"] else 0); p["existe_mudo"] = (c / (p.get("video_mudo") or "x")).exists() and (c / (p.get("video_mudo") or "x")).with_suffix(".json").exists()   # solo cuando la grabacion TERMINO
                uj = c / "salida" / (p["id"] + "_completo.mp4"); ev = [c / e["video"] for e in p.get("escenas", []) if e.get("video") and (c / e["video"]).exists()]
                bv_ = c / (p.get("borrador_voz") or "x"); mv_ = c / (p.get("video_mudo") or "x"); tj_ = c / "audiolibro" / "tiempos.json"; p["existe_borrador_voz"] = bool(bv_.exists() and tj_.exists() and mv_.exists() and bv_.stat().st_mtime >= tj_.stat().st_mtime - 5 and bv_.stat().st_mtime >= mv_.stat().st_mtime - 5); p["borrador_voz_t"] = int(bv_.stat().st_mtime) if bv_.exists() else 0
                mu = c / (p.get("video_mudo") or "x"); p["mudo_t"] = int(mu.stat().st_mtime) if mu.exists() else 0
                p["unido_ok"] = bool(uj.exists() and ev and len(ev) == len(p.get("escenas", [])) and uj.stat().st_mtime >= max(f.stat().st_mtime for f in ev)); p["unido_t"] = int(uj.stat().st_mtime) if uj.exists() else 0; p["unido_ruta"] = str(uj); p["unido_mb"] = round(uj.stat().st_size / 1048576, 1) if uj.exists() else 0
            return self._json(ps)
        if pa == "/api/previa":
            p = proyecto(q.get("id", [""])[0])
            if not p: return self._json({"error": "proyecto no existe"}, 404)
            c = carpeta(p); im = sorted((c / "vista_previa").glob("*.jpg")) if (c / "vista_previa").exists() else []
            return self._json({"carpeta": str(c), "imagenes": ["/series/%s/vista_previa/%s" % (p["carpeta"], f.name) for f in im], "rutas": {"Guion": str(c / p.get("guion", "guion/1.json")), "Voces": str(c / "voz"), "Video mudo": str(c / "salida_mudo"), "Video final": str(c / "salida"), "Imagenes de prueba": str(c / "vista_previa"), "Juego": str(c / "game.js"), "Musica": str(c / "music")}})
        if pa == "/api/miniatura":   # imagen (jpg) de una escena: asi el panel no abre 5 videos a la vez
            pr = proyecto(q.get("id", [""])[0]); n = int(q.get("n", ["1"])[0])
            if not pr: self.send_error(404); return
            e = next((x for x in pr.get("escenas", []) if x["n"] == n), None); mu = carpeta(pr) / pr.get("video_mudo", "x")
            if not e or not mu.exists(): self.send_error(404); return
            d = ROOT / "miniaturas"; d.mkdir(exist_ok=True); f = d / ("%s_%d_%d.jpg" % (pr["id"], n, int(mu.stat().st_mtime) + int(e.get("desde", 0))))
            if not f.exists():
                import imageio_ffmpeg
                subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-ss", "%.2f" % (float(e.get("desde", 0)) + 1.0), "-i", str(mu), "-frames:v", "1", "-vf", "scale=270:480", "-q:v", "4", str(f)], env=ENV)
            return self._file(f)
        if pa == "/api/capturas":
            pr = proyecto(q.get("id", [""])[0])
            if not pr: return self._json({"error": "proyecto no existe"}, 404)
            d = carpeta(pr) / "miniaturas"; im = sorted(d.glob("*.jpg")) if d.exists() else []
            return self._json({"ruta": str(d), "imagenes": ["/series/%s/miniaturas/%s?v=%d" % (pr["carpeta"], f.name, int(f.stat().st_mtime)) for f in im]})
        if pa == "/api/descargar":
            pr = proyecto(q.get("id", [""])[0])
            if not pr: self.send_error(404); return
            return self._descargar(carpeta(pr) / "salida" / (pr["id"] + "_completo.mp4"), pr["id"] + ".mp4")
        if pa == "/api/titulos":
            pr = proyecto(q.get("id", [""])[0])
            if not pr: return self._json({"error": "proyecto no existe"}, 404)
            d = titulos_de(pr); titulos.guardar(ROOT / "titulos", pr["id"], d); return self._json(d)
        if pa == "/api/voz_escenas":
            p = proyecto(q.get("id", [""])[0]); return self._json(voz_escenas(p) if p else {"voz": False})
        if pa == "/api/voz_preview":
            p = proyecto(q.get("id", [""])[0]); return self._json({"url": voz_preview(p) if p else None})
        if pa == "/api/voz_progreso":   # cuántas partes de la voz ya están guardadas (se guardan una a una; si se corta, «Seguir» retoma desde ahí)
            p = proyecto(q.get("id", [""])[0])
            if not p: return self._json({"error": "proyecto no existe"}, 404)
            c = carpeta(p); g = guion_de(p); part = c / "audiolibro" / "partes"; hechas = 0
            if part.is_dir():
                for k, l in enumerate(g, 1):
                    if any(part.glob("%02d_%s_*.npz" % (k, l.get("key", "")))): hechas += 1
            return self._json({"hechas": hechas, "total": len(g), "unidas": sum(1 for l in g if l.get("voz"))})
        if pa == "/api/guion":
            p = proyecto(q.get("id", [""])[0]); return self._json(guion_de(p)) if p else self._json({"error": "proyecto no existe"}, 404)
        if pa == "/api/jobs":
            with LOCK: return self._json([vista_job(j) for j in sorted(JOBS.values(), key=lambda j: -j["id"])][:12])
        self.send_error(404)
    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0) or 0); body = json.loads(self.rfile.read(n).decode("utf-8") or "{}") if n else {}; pa = urllib.parse.urlparse(self.path).path
        if pa in PLUGIN_RUTAS:
            e_ = bloqueo_plugin(body.get("id"))
            if e_: return self._json(e_, 409)
        if pa == "/api/voice_detener":   # «Liberar memoria»: apaga la API de voz; se vuelve a encender sola al generar voz
            with LOCK:
                if any(j["estado"] == "corriendo" for j in JOBS.values()): return self._json({"error": "Hay un trabajo corriendo; espera a que termine para no cortarlo."}, 409)
            ok = voice_detener(); rl, rt = _ram_libre(); vl, vt = _vram(); return self._json({"ok": ok, "ram_libre_gb": rl, "vram_libre_gb": vl, "vram_total_gb": vt})
        if pa == "/api/voice_iniciar":
            ok = voice_iniciar(); return self._json({"ok": ok})
        if pa == "/api/emergencia":   # BOTON DE EMERGENCIA: Claude no responde -> deja el aviso y, si el monitor esta vivo, lo despierta sin que el usuario escriba
            try: mon = time.time() - json.loads((ROOT / "claude_monitor.json").read_text(encoding="utf-8"))["ts"] < 15
            except Exception: mon = False
            (ROOT / "emergencia.json").write_text(json.dumps({"ts": time.time(), "hora": time.strftime("%H:%M:%S")}), encoding="utf-8")
            pend = [x.get("titulo") for x in jload("pedidos.json", []) if (x.get("estado") or "pendiente") not in ("hecho", "cancelado") and (x.get("tipo") or "") != "ideas"]
            logact(None, "EMERGENCIA: el usuario pidio que Claude retome lo pendiente (%s)." % ("; ".join(str(t)[:60] for t in pend[-4:]) or "nada pendiente"), "pedido")
            return self._json({"ok": True, "monitor": mon, "pendientes": pend[-6:]})
        if pa == "/api/temp":   # {"temp_dir": "RUTA"}: carpeta de temporales (la usa el panel al reiniciar); vacío = la de por defecto (_tmp del panel)
            cfg = jload("devpanel.json", {}); d_ = str(body.get("temp_dir") or "").strip()
            if d_:
                try: os.makedirs(d_, exist_ok=True)
                except Exception as e_: return self._json({"error": "No pude usar esa carpeta: %s" % e_}, 400)
                cfg["temp_dir"] = d_
            else: cfg.pop("temp_dir", None)
            (ROOT / "devpanel.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8"); return self._json({"ok": True, "temp_dir": cfg.get("temp_dir") or "", "reiniciar": True})
        if pa == "/api/senal":   # {"senal_min": N, "primer_uso": false}: intervalo de la señal de conexión (se guarda en devpanel.json y aparece en Ajustes)
            cfg = jload("devpanel.json", {})
            if body.get("senal_min") is not None: cfg["senal_min"] = max(5, min(240, int(body["senal_min"])))
            if body.get("primer_uso") is not None: cfg["primer_uso"] = bool(body["primer_uso"])
            (ROOT / "devpanel.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=1), encoding="utf-8"); return self._json({"ok": True, "senal_min": _senal_min(), "primer_uso": bool(cfg.get("primer_uso"))})
        if pa == "/api/vivo_tiempo":   # temporizador de la conexion con Claude: {"min": N, "modo": "poner"|"sumar"}
            f = ROOT / "vivo_hasta.json"
            try: h = float(json.loads(f.read_text(encoding="utf-8"))["hasta"])
            except Exception: h = 0
            m = max(0, min(600, float(body.get("min", _senal_min())))) * 60; ahora = time.time()
            h = (max(h, ahora) + m) if body.get("modo") == "sumar" else ahora + m
            f.write_text(json.dumps({"hasta": h}), encoding="utf-8"); return self._json({"ok": True, "resta": int(h - ahora)})
        if pa == "/api/idea":   # cambiar estado / borrar / pedir otra idea
            cat = jload("catalogo.json", []); ped = jload("pedidos.json", []); iid = body.get("id"); it = next((i for i in cat if i["id"] == iid), None)
            if not it: return self._json({"error": "idea no existe"}, 404)
            acc = body.get("accion")
            if acc == "borrar": cat = [i for i in cat if i["id"] != iid]; ped = [x for x in ped if x.get("idea") != iid]
            elif acc == "otra":   # la actual se declina y entra la siguiente del banco (mismo formato)
                it["estado"] = "declinado"; banco = jload("banco.json", []); nx = next((b for b in banco if b["formato"] == it["formato"]), None)
                if nx: banco.remove(nx); nx["estado"] = "idea"; cat.append(nx); jsave("banco.json", banco)
            else:
                est = body.get("estado", it["estado"]); it["estado"] = est
                if est in ("interesa", "validacion") and not it.get("config"): it["config"] = cola.cfg_default(it["formato"], it.get("titulo"), it.get("desc"))
                if "muestra" in body: it["muestra"] = body["muestra"]
                ped = [x for x in ped if not (x.get("idea") == iid and x.get("tipo") in ("muestra", "resto"))]
                if acc == "pedir_muestra": it["estado"] = "validacion"; it["muestra"] = "pedida"; ped.append({"idea": iid, "tipo": "muestra", "titulo": it["titulo"], "formato": it["formato"], "nota": "Construir SOLO la escena 1 (apertura ~12 s con voz, cuenta atras y primeras jugadas) como muestra para validar. " + cola.cfg_resumen(it.get("config")), "hora": time.strftime("%Y-%m-%d %H:%M")})
                if acc == "procesar_escena1": it["estado"] = "validacion"; it["muestra"] = "pedida1"; ped.append({"idea": iid, "tipo": "escena1", "titulo": "Escena 1 de " + it["titulo"], "formato": it["formato"], "nota": "Las capturas gustaron: procesar SOLO la escena 1 (grabar ese tramo mudo + sus voces) para validar. " + cola.cfg_resumen(it.get("config")), "hora": time.strftime("%Y-%m-%d %H:%M"), "estado": "pendiente"})
                if acc == "producir_resto":
                    it["estado"] = "produccion"; it["muestra"] = "aprobada"; cola.encolar(cat, it)
                    if it.get("proyecto"):
                        ps_ = jload("proyectos.json", [])
                        for x_ in ps_:
                            if x_["id"] == it["proyecto"]: x_["fase"] = "resto"
                        jsave("proyectos.json", ps_)
                if acc == "rehacer_todo":   # boton «Rehacer todo» (debajo de «Aprobar todo»): Claude rehace escenas, frases y final
                    nota = "REHACER TODO EL VIDEO. Queja del usuario: " + (body.get("nota") or "(sin detalle)") + " | Revisar y corregir: que cada escena coincida con su frase (la voz manda y cada palabra clave cae en su suceso), frases CORTAS al punto clave como un comentarista (no frases largas), finales limpios (ganador y cierre), y respetar los ajustes: " + cola.cfg_resumen(it.get("config") or {})
                    ped = [x for x in ped if not (x.get("idea") == iid and x.get("tipo") == "mejora" and x.get("estado") == "pendiente" and str(x.get("titulo", "")).startswith("Rehacer TODO"))]
                    ped.append({"idea": iid, "tipo": "mejora", "titulo": "Rehacer TODO " + it["titulo"], "formato": it["formato"], "proyecto": it.get("proyecto"), "nota": nota, "hora": time.strftime("%Y-%m-%d %H:%M"), "estado": "pendiente"})
                if acc == "rehacer_ajustes":   # boton «Rehacer con mis ajustes»: Claude rehace lo construido aplicando de verdad los niveles guardados
                    nota = "REHACER CON LOS AJUSTES GUARDADOS (aplicalos de verdad en el juego, no solo los menciones; luego rehacer la escena 1 y dejar el video listo): " + cola.cfg_resumen(it.get("config") or {})
                    ped = [x for x in ped if not (x.get("idea") == iid and x.get("tipo") == "mejora" and x.get("estado") == "pendiente" and str(x.get("titulo", "")).startswith("Rehacer con ajustes"))]
                    ped.append({"idea": iid, "tipo": "mejora", "titulo": "Rehacer con ajustes de " + it["titulo"], "formato": it["formato"], "proyecto": it.get("proyecto"), "nota": nota, "hora": time.strftime("%Y-%m-%d %H:%M"), "estado": "pendiente"})
                    if it.get("muestra") in ("previa", "lista"): it["muestra"] = "pedida1"
                if acc == "rehacer_muestra": it["estado"] = "validacion"; it["muestra"] = "pedida"; ped.append({"idea": iid, "tipo": "muestra", "titulo": it["titulo"], "formato": it["formato"], "nota": "REHACER la escena 1: " + body.get("nota", "no gusto"), "hora": time.strftime("%Y-%m-%d %H:%M")})
            jsave("catalogo.json", cat); jsave("pedidos.json", ped); cola.avanzar(); return self._json({"ok": True})
        if pa == "/api/borrar_ideas":   # borra SOLO las ideas sin empezar (estado «idea») del formato pedido; lo que está en proceso o hecho NO se toca
            cat = jload("catalogo.json", []); fm = body.get("formato", "short"); act_ = estado_plugins().get("activo"); keep = [i for i in cat if not (i["formato"] == fm and i.get("estado") == "idea" and i.get("plugin") == act_)]
            jsave("catalogo.json", keep); return self._json({"ok": True, "borradas": len(cat) - len(keep)})
        if pa == "/api/mas_ideas":   # «Dame 10 ideas nuevas»: las pone el plugin activo (sin plugin no sale nada)
            d_, m_ = plugin_activo()
            if not d_: return self._json(SIN_PLUGIN, 409)
            mod = modulo_plugin(d_, (m_.get("ideas") or {}).get("modulo", "")) if (m_.get("ideas") or {}).get("modulo") else None
            if not mod or not hasattr(mod, "mas_ideas"): return self._json({"error": "El plugin «%s» no aporta ideas (falta ideas.modulo con mas_ideas)." % m_.get("nombre")}, 400)
            cat = jload("catalogo.json", []); fm = body.get("formato", "short"); n = int(body.get("n", 10)); lote = max([i.get("lote", 1) for i in cat if i.get("formato") == fm] + [1]) + 1
            nuevas = [dict(x, id="m%d%02d" % (int(time.time()), k), formato=fm, estado="idea", lote=lote, plugin=d_.name) for k, x in enumerate(mod.mas_ideas(fm, n, [i["titulo"] for i in cat]))]
            cat += nuevas; jsave("catalogo.json", cat); return self._json({"ok": True, "nuevas": len(nuevas), "lote": lote})
        if pa == "/api/referencia":   # el usuario menciona una referencia -> ejemplos (generador local) y, si quiere, pedido a Claude
            refs = jload("referencias.json", []); txt = body.get("texto", "").strip()
            if not txt: return self._json({"error": "escribe una referencia"}, 400)
            refs.append({"id": "r%d" % int(time.time()), "referencia": txt, "formato": body.get("formato", "short"), "hora": time.strftime("%Y-%m-%d %H:%M"), "ejemplos": ejemplos_de(txt), "claude": False}); jsave("referencias.json", refs); return self._json({"ok": True})
        if pa == "/api/ejemplo":
            refs = jload("referencias.json", []); r = next((x for x in refs if x["id"] == body.get("ref")), None); e = next((x for x in (r or {}).get("ejemplos", []) if x["id"] == body.get("ejemplo")), None)
            if not e: return self._json({"error": "no existe"}, 404)
            if body.get("accion") == "pasar":
                cat = jload("catalogo.json", []); cat.append({"id": "x-" + e["id"], "formato": r["formato"], "titulo": e["titulo"], "desc": e["desc"], "estado": "validacion", "muestra": "sin_pedir", "referencia": r["referencia"], "config": cola.cfg_default(r["formato"], e["titulo"], e["desc"])}); jsave("catalogo.json", cat); e["estado"] = "pasado"
            elif body.get("accion") == "descartar": e["estado"] = "descartado"
            elif body.get("accion") == "claude":
                ped = jload("pedidos.json", []); r["claude"] = True; ped.append({"idea": None, "tipo": "referencia", "titulo": "Ejemplos mejores para: " + r["referencia"][:80], "formato": r["formato"], "nota": "Referencia del usuario: " + r["referencia"] + " (ref " + r["id"] + " en referencias.json). Proponer 6 ejemplos de juego con mecanica, giro y escenario.", "hora": time.strftime("%Y-%m-%d %H:%M")}); jsave("pedidos.json", ped)
            jsave("referencias.json", refs); return self._json({"ok": True})
        if pa == "/api/referencia_borrar":
            refs = [x for x in jload("referencias.json", []) if x["id"] != body.get("ref")]; jsave("referencias.json", refs); return self._json({"ok": True})
        if pa == "/api/pedido_estado":   # lo actualiza Claude (pedido.py) o el panel
            ped = jload("pedidos.json", [])
            for x in ped:
                if (body.get("idea") and x.get("idea") == body["idea"]) or (body.get("titulo") and x.get("titulo") == body["titulo"]):
                    for k in ("estado", "pct", "msg"):
                        if k in body: x[k] = body[k]
                    x["act"] = time.strftime("%Y-%m-%d %H:%M:%S")
            jsave("pedidos.json", ped); return self._json({"ok": True})
        if pa == "/api/escena":   # aprobar / rehacer una escena (cada escena se produce y se revisa aparte; al final se unen)
            ps = jload("proyectos.json", []); pr = next((x for x in ps if x["id"] == body.get("id")), None); e = next((x for x in (pr or {}).get("escenas", []) if x["n"] == body.get("n")), None)
            if body.get("accion") == "aprobar_todo" and pr: e = {}
            if e is None: return self._json({"error": "escena no existe"}, 404)
            acc = body.get("accion")
            if acc == "aprobar": e["estado"] = "aprobada"
            if acc == "aprobar_todo":
                for z in pr.get("escenas", []): z["estado"] = "aprobada"
            if acc == "rehacer":
                e["estado"] = "rehacer"; e.setdefault("notas", []).append({"hora": time.strftime("%Y-%m-%d %H:%M"), "texto": body.get("nota", "")}); ped = jload("pedidos.json", []); cat = jload("catalogo.json", []); it = next((i for i in cat if i.get("proyecto") == pr["id"]), None)
                ped.append({"idea": it["id"] if it else None, "tipo": "escena", "titulo": "Rehacer escena %d de %s" % (e["n"], pr["titulo"]), "formato": pr["formato"], "proyecto": pr["id"], "n": e["n"], "nota": "REHACER escena %d (%s): %s" % (e["n"], e.get("titulo", ""), body.get("nota", "")), "hora": time.strftime("%Y-%m-%d %H:%M"), "estado": "pendiente"}); jsave("pedidos.json", ped)
            jsave("proyectos.json", ps); return self._json({"ok": True})
        if pa == "/api/mejora":   # UNA mejora para todo el video (afecta a todas las escenas)
            ps = jload("proyectos.json", []); pr = next((x for x in ps if x["id"] == body.get("id")), None)
            if not pr or not body.get("nota", "").strip(): return self._json({"error": "falta el proyecto o el texto"}, 400)
            pr.setdefault("mejoras", []).append({"hora": time.strftime("%Y-%m-%d %H:%M"), "texto": body["nota"].strip()})
            ped = jload("pedidos.json", []); cat = jload("catalogo.json", []); it = next((i for i in cat if i.get("proyecto") == pr["id"]), None)
            ped.append({"idea": it["id"] if it else None, "tipo": "mejora", "titulo": "Mejora para %s" % pr["titulo"], "formato": pr["formato"], "proyecto": pr["id"], "nota": "MEJORA (afecta a todo el video): " + body["nota"].strip(), "hora": time.strftime("%Y-%m-%d %H:%M"), "estado": "pendiente"})
            jsave("pedidos.json", ped); jsave("proyectos.json", ps); return self._json({"ok": True})
        if pa == "/api/config":   # paises, estilo, dificultad, modo y ganador de un video
            cat = jload("catalogo.json", []); it = next((i for i in cat if i["id"] == body.get("id")), None)
            if not it: return self._json({"error": "idea no existe"}, 404)
            viejo = it.get("config") or {}; nuevo = body.get("config") or {}; cambio = viejo != nuevo; it["config"] = nuevo; it.pop("config_def", None); enviado = None
            # Si el video ya se pidio/construyo (muestra pedida, capturas, escena 1 o proyecto), CUALQUIER cambio de ajustes le llega a Claude solo (antes solo con «Guardar y aplicar»).
            ya = bool(it.get("proyecto")) or it.get("muestra") in ("pedida", "pedida1", "previa", "lista")
            if (body.get("aplicar") or cambio) and ya:
                ped = jload("pedidos.json", []); nota = "CAMBIO DE AJUSTES (afecta a todo el video, rehacer lo ya construido con estos niveles; aplicalos de verdad, no solo los menciones): " + cola.cfg_resumen(nuevo)
                abiertos = [x for x in ped if x.get("idea") == it["id"] and x.get("tipo") == "mejora" and x.get("estado") == "pendiente" and str(x.get("titulo", "")).startswith("Cambiar ajustes")]
                if abiertos: abiertos[0]["nota"] = nota; abiertos[0]["hora"] = time.strftime("%Y-%m-%d %H:%M")
                else: ped.append({"idea": it["id"], "tipo": "mejora", "titulo": "Cambiar ajustes de " + it["titulo"], "formato": it["formato"], "proyecto": it.get("proyecto"), "nota": nota, "hora": time.strftime("%Y-%m-%d %H:%M"), "estado": "pendiente"})
                jsave("pedidos.json", ped); enviado = True
            jsave("catalogo.json", cat); return self._json({"ok": True, "enviado": bool(enviado), "cambio": cambio})
        if pa == "/api/titulos":   # 100 opciones de titulo/descripcion/etiquetas: se muestran de 10 en 10; al gastar los 100 se genera otro lote
            pr = proyecto(body.get("id"))
            if not pr: return self._json({"error": "proyecto no existe"}, 404)
            d = titulos_de(pr); acc = body.get("accion")
            if acc == "otros":
                d["pos"] += 10
                if d["pos"] >= len(d["items"]): nuevo_lote(pr, d)
            elif acc == "elegir": d["elegido"] = body.get("datos")
            elif acc == "nuevo_lote": nuevo_lote(pr, d)
            titulos.guardar(ROOT / "titulos", pr["id"], d); return self._json(d)
        if pa == "/api/abrir_carpeta":   # abre el Explorador de Windows con el video seleccionado
            pr = proyecto(body.get("id"))
            if pr and body.get("tipo") == "capturas":
                d = carpeta(pr) / "miniaturas"; d.mkdir(exist_ok=True); subprocess.Popen(["explorer", str(d).replace("/", chr(92))]); return self._json({"ok": True})
            f = carpeta(pr) / "salida" / (pr["id"] + "_completo.mp4") if pr else None
            if not f or not f.exists(): return self._json({"error": "Aun no hay video unido."}, 404)
            subprocess.Popen(["explorer", "/select," + str(f).replace("/", chr(92))]); return self._json({"ok": True})
        if pa == "/api/cola":   # subir | bajar | quitar un video de la cola
            cat = jload("catalogo.json", []); q = sorted([i for i in cat if i.get("estado") == "produccion"], key=lambda i: i.get("cola", 999)); ids = [i["id"] for i in q]; iid = body.get("id"); acc = body.get("accion")
            if iid in ids:
                k = ids.index(iid)
                if acc == "subir" and k > 0: ids[k - 1], ids[k] = ids[k], ids[k - 1]
                if acc == "bajar" and k < len(ids) - 1: ids[k + 1], ids[k] = ids[k], ids[k + 1]
                if acc == "quitar": ids.remove(iid)
                for i in cat:
                    if i["id"] in ids: i["cola"] = ids.index(i["id"]) + 1
                    if i["id"] == iid and acc == "quitar": i["estado"] = "validacion"; i["muestra"] = "lista"
                jsave("catalogo.json", cat)
            return self._json({"ok": True})
        if pa == "/api/pedido_borrar":
            ped = jload("pedidos.json", []); k = body.get("i")
            if isinstance(k, int) and 0 <= k < len(ped):
                x = ped.pop(k)
                if x.get("idea") and x.get("tipo") in ("muestra", "resto"):
                    cat = jload("catalogo.json", [])
                    for it in cat:
                        if it["id"] == x["idea"] and it.get("muestra") == "pedida": it["muestra"] = "sin_pedir"
                    jsave("catalogo.json", cat)
                jsave("pedidos.json", ped)
            return self._json({"ok": True})
        if pa == "/api/rehacer_parte":   # «Rehacer voz» de UNA frase (otra toma): voz de esa parte + unión; el video no se vuelve a grabar
            p = proyecto(body.get("id"))
            if not p: return self._json({"error": "proyecto no existe"}, 404)
            if not (carpeta(p) / "proyecto.json").exists(): return self._json({"error": "este proyecto no es del pipeline nuevo"}, 400)
            k = str(body.get("key", "")).strip()
            if not k: return self._json({"error": "falta la clave de la frase"}, 400)
            jid = iniciar_conforme(p, "voz" if p.get("estado") == "borrador" else "parte", (k,))   # en BORRADOR solo se rehace la voz de esa frase (sin unir ni regrabar); ya aprobado: voz + unión
            return self._json({"ok": True, "job": jid} if jid else {"error": "ya hay un trabajo corriendo; espera a que termine"}, 200 if jid else 409)
        if pa == "/api/generar_voz":   # voz de TODAS las frases (solo lo nuevo o cambiado), SIN unir el video: se puede revisar y rehacer frases antes de aprobar
            p = proyecto(body.get("id"))
            if not p: return self._json({"error": "proyecto no existe"}, 404)
            if not (carpeta(p) / "proyecto.json").exists(): return self._json({"error": "este proyecto no es del pipeline nuevo (falta proyecto.json)"}, 400)
            jid = iniciar_conforme(p, "voz")
            return self._json({"ok": True, "job": jid} if jid else {"error": "ya hay un trabajo corriendo; espera a que termine"}, 200 if jid else 409)
        if pa == "/api/conforme":   # el USUARIO aprueba el borrador -> voz + unir (pipeline «conforme»)
            p = proyecto(body.get("id"))
            if not p: return self._json({"error": "proyecto no existe"}, 404)
            if not (carpeta(p) / "proyecto.json").exists(): return self._json({"error": "este proyecto no es del pipeline nuevo (falta proyecto.json)"}, 400)
            jid = iniciar_conforme(p)
            return self._json({"ok": True, "job": jid} if jid else {"error": "ya hay un trabajo corriendo; espera a que termine"}, 200 if jid else 409)
        if pa == "/api/pedido":   # pedido libre -> el panel responde con IDEAS relacionadas (con «cómo sucedería» y referencia); a Claude se le pide recién con «Díselo a Claude»
            texto = body.get("texto", "").strip(); fm = body.get("formato", "short")
            if not texto: return self._json({"error": "escribe el pedido"}, 400)
            ped = jload("pedidos.json", []); cat_ = jload("catalogo.json", []); pid_ = "p%d" % int(time.time()); lote = max([i.get("lote", 1) for i in cat_ if i.get("formato") == fm] + [1]) + 1
            d_, m_ = plugin_activo()
            if not d_: return self._json(SIN_PLUGIN, 409)
            mod = modulo_plugin(d_, (m_.get("ideas") or {}).get("modulo", "")) if (m_.get("ideas") or {}).get("modulo") else None
            ids = mod.ideas_de(texto, fm) if mod and hasattr(mod, "ideas_de") else [{"titulo": texto[:200], "desc": "Pedido del usuario", "modo": "pedido"}]
            for k_, it_ in enumerate(ids): cat_.append(dict(it_, id="%s-%d" % (pid_, k_ + 1), formato=fm, estado="idea", lote=lote, pedido=pid_, pedido_texto=texto, plugin=d_.name))
            jsave("catalogo.json", cat_)
            ped.append({"idea": None, "tipo": "ideas", "titulo": texto[:200], "formato": fm, "nota": texto, "hora": time.strftime("%Y-%m-%d %H:%M"), "estado": "hecho", "pct": 100, "msg": "%d ideas listas en «Ideas»" % len(ids), "act": time.strftime("%Y-%m-%d %H:%M:%S")}); jsave("pedidos.json", ped)
            logact(None, "Pedido recibido: «%s». Se prepararon %d ideas para elegir." % (texto[:80], len(ids)), "ideas"); return self._json({"ok": True, "ideas": len(ids), "lote": lote})
        if pa == "/api/responder":   # el usuario contesta una pregunta de Claude (aparece en el panel y le llega a Claude por el vigilante)
            ped = jload("pedidos.json", []); x = next((z for z in reversed(ped) if z.get("idea") == body.get("idea") and z.get("tipo") == "video"), None); r_ = (body.get("respuesta") or "").strip()
            if not x or not r_: return self._json({"error": "falta la respuesta"}, 400)
            q_ = (x.get("pregunta") or {}).get("texto", ""); x["respuesta"] = r_; x.pop("pregunta", None)
            ped.append({"idea": x["idea"], "tipo": "respuesta", "titulo": "Respuesta del usuario: " + r_[:80], "formato": x.get("formato"), "nota": "RESPUESTA del usuario a tu pregunta («" + q_ + "»): " + r_ + ". Sigue con el video pedido.", "hora": time.strftime("%Y-%m-%d %H:%M"), "estado": "pendiente", "pct": 0}); jsave("pedidos.json", ped)
            logact(x["idea"], "Respondiste: «%s». Claude sigue con el video." % r_[:80], "respuesta"); return self._json({"ok": True})
        if pa == "/api/instalar":   # regenera iniciar_devpanel.bat / detener_devpanel.bat con las rutas de esta carpeta
            args = [PY, "-X", "utf8", str(ROOT / "instalar.py"), "--puerto", str(PORT)] + (["--acceso-directo"] if body.get("acceso_directo") else []) + (["--instalar-paquetes"] if body.get("paquetes") else [])
            r = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900); logact(None, "Instalador ejecutado: se regeneró iniciar_devpanel.bat.", "info")
            return self._json({"ok": r.returncode == 0, "salida": (r.stdout + r.stderr)[-1500:], "info": info_instalacion()})
        if pa == "/api/plugin_activar":   # activa (o desactiva con activar=false) un plugin: solo uno a la vez y solo si cumple el esqueleto
            d = PLUGINS_DIR / str(body.get("id", "")); est = estado_plugins()
            if not d.is_dir(): return self._json({"error": "plugin no existe"}, 404)
            if body.get("activar", True):
                m, er = validar_plugin(d)
                if er: return self._json({"error": "No cumple el esqueleto: " + "; ".join(er[:3])}, 400)
                est["activo"] = d.name; logact(None, "Plugin activado: «%s»." % m.get("nombre", d.name), "info")
            else: est["activo"] = None; logact(None, "Plugin desactivado: «%s»." % d.name, "info")
            jsave("plugins_estado.json", est); return self._json({"ok": True, "activo": est.get("activo")})
        if pa == "/api/plugin_ajustes":   # guarda los ajustes del subpanel (validados contra la ficha del plugin)
            d = PLUGINS_DIR / str(body.get("id", "")); m, er = validar_plugin(d)
            if er: return self._json({"error": "plugin no válido"}, 400)
            aj = {a["id"]: a for a in m.get("ajustes", [])}; vals = {}
            for k, v in (body.get("valores") or {}).items():
                a = aj.get(k)
                if not a: continue
                if a["tipo"] == "numero":
                    try: v = float(v); v = int(v) if v == int(v) else v
                    except Exception: return self._json({"error": "«%s» debe ser un número" % a["etiqueta"]}, 400)
                    if v < a.get("min", v) or v > a.get("max", v): return self._json({"error": "«%s» debe estar entre %s y %s" % (a["etiqueta"], a.get("min"), a.get("max"))}, 400)
                elif a["tipo"] == "texto": v = str(v).strip()[:120]
                elif a["tipo"] == "interruptor": v = bool(v)
                elif a["tipo"] == "opcion" and v not in a.get("opciones", []): return self._json({"error": "«%s»: opción no válida" % a["etiqueta"]}, 400)
                vals[k] = v
            est = estado_plugins(); est.setdefault("ajustes", {})[d.name] = vals; jsave("plugins_estado.json", est); logact(None, "Ajustes guardados del plugin «%s»." % m.get("nombre", d.name), "info"); return self._json({"ok": True, "valores": vals})
        if pa == "/api/plugin_mejora":   # sub-pregunta del plugin: Claude la recibe marcada con el plugin y mejora SOLO ese plugin
            d = PLUGINS_DIR / str(body.get("id", "")); txt = (body.get("texto") or "").strip()
            if not d.is_dir() or not txt: return self._json({"error": "falta el plugin o el texto"}, 400)
            m, er = validar_plugin(d); ped = jload("pedidos.json", [])
            ped.append({"idea": "plugin:" + d.name, "tipo": "plugin_mejora", "plugin": d.name, "titulo": "Mejorar el plugin «%s»: %s" % (m.get("nombre", d.name), txt[:60]), "formato": "plugin", "hora": time.strftime("%Y-%m-%d %H:%M"), "estado": "pendiente", "pct": 0,
                        "nota": "MEJORA DE PLUGIN «%s» (carpeta plugins/%s del DevIAs Panel). Pedido: %s. Reglas: 1) copia de seguridad en _backups antes de tocar nada; 2) cambia SOLO este plugin; 3) plugin.json debe seguir cumpliendo el esqueleto (sube la versión); 4) avisa el avance con pedido.py plugin:%s." % (m.get("nombre", d.name), d.name, txt, d.name)})
            jsave("pedidos.json", ped); logact("plugin:" + d.name, "Mejora enviada para el plugin «%s»: %s" % (m.get("nombre", d.name), txt[:80]), "pedido"); return self._json({"ok": True})
        if pa == "/api/plugin_instalar":   # instala SOLO los paquetes python que le faltan al plugin (acción del usuario)
            d = PLUGINS_DIR / str(body.get("id", "")); m, er = validar_plugin(d)
            if er: return self._json({"error": "plugin no válido"}, 400)
            faltan = [r_["pip"] for r_ in requisitos_plugin(d, m) if r_["tipo"] == "python" and not r_["ok"]]
            if not faltan: return self._json({"ok": True, "instalado": []})
            r = subprocess.run([PY, "-m", "pip", "install", *faltan], capture_output=True, text=True, timeout=600); logact(None, "Instalado para «%s»: %s" % (m.get("nombre", d.name), ", ".join(faltan)), "info")
            return self._json({"ok": r.returncode == 0, "instalado": faltan, "salida": (r.stdout + r.stderr)[-400:]})
        if pa == "/api/borrar_video":   # «Mis videos» -> borrar: la carpeta va a _papelera/videos (recuperable); se quitan el registro, la idea y los pedidos de ese video
            pid = str(body.get("id", "")); ps_ = jload("proyectos.json", []); p_ = next((x for x in ps_ if x.get("id") == pid), None); idea_ = (p_ or {}).get("idea") or (pid[4:] if pid.startswith("esp-") else None)
            if not p_ and not idea_: return self._json({"error": "ese video no existe"}, 404)
            with LOCK: busy = [j for j in JOBS.values() if j["estado"] == "corriendo" and j.get("proyecto") == pid and (not j.get("externo") or time.time() - j.get("ultima", 0) < 600)]
            if busy: return self._json({"error": "Este video tiene un trabajo en curso (voz, grabación, unión o Claude trabajando). Espera a que termine para borrarlo."}, 409)
            dst = None; c_ = carpeta(p_) if p_ else None
            if c_ is not None and c_.is_dir():
                pap_ = ROOT / "_papelera" / "videos"; pap_.mkdir(parents=True, exist_ok=True); dst = pap_ / ("%s_%s" % (c_.name, time.strftime("%Y%m%d_%H%M%S")))
                try: shutil.move(str(c_), str(dst))
                except Exception as e_: return self._json({"error": "No pude mover la carpeta a _papelera (¿hay un archivo o ventana abierta dentro de «%s»?): %s" % (c_.name, e_)}, 409)
            tf_ = ROOT / "titulos" / (pid + ".json")
            if tf_.exists():
                try: (shutil.copy(str(tf_), str(dst / "_titulos.json")) if dst else None); tf_.unlink()
                except Exception: pass
            jsave("proyectos.json", [x for x in ps_ if x.get("id") != pid])
            cat_ = jload("catalogo.json", []); n_c = len(cat_); jsave("catalogo.json", [i for i in cat_ if i.get("proyecto") != pid and not (idea_ and i.get("id") == idea_)])
            ped_ = jload("pedidos.json", []); jsave("pedidos.json", [x for x in ped_ if not (idea_ and x.get("idea") == idea_)])
            cp_ = jload("cambios_pendientes.json", {}); cp_.pop(pid, None); jsave("cambios_pendientes.json", cp_)
            cierra_trabajos_de(pid, "esp-" + str(idea_), idea_)
            logact(None, "Video borrado: «%s»%s." % ((p_ or {}).get("titulo") or idea_, " (carpeta en _papelera/videos)" if dst else ""), "info")
            return self._json({"ok": True, "papelera": str(dst) if dst else None})
        if pa == "/api/voz_config":   # Ajustes → Voz: perfil, velocidad y pausa de TODAS las voces del DevIAs Panel
            c_ = jload("voz_config.json", {}); c_ = c_ if isinstance(c_, dict) else {}
            try: v_ = float(body.get("velocidad", c_.get("velocidad", 1.12))); pz_ = int(float(body.get("pausa_ms", c_.get("pausa_ms", 450))))
            except Exception: return self._json({"error": "velocidad y pausa deben ser números"}, 400)
            pf_ = str(body.get("perfil", c_.get("perfil", "MI VOZ"))).strip()[:80]
            if not pf_ or not .8 <= v_ <= 1.4 or not 150 <= pz_ <= 900: return self._json({"error": "perfil obligatorio, velocidad entre 0.8 y 1.4 y pausa entre 150 y 900 ms"}, 400)
            mo_ = str(body.get("motor", c_.get("motor", "voicestudio"))).strip().lower()
            if mo_ not in ("voicestudio", "huggingface"): return self._json({"error": "el motor debe ser voicestudio o huggingface"}, 400)
            c_.update(perfil=pf_, velocidad=v_, pausa_ms=pz_, motor=mo_)
            tk_ = str(body.get("hf_token") or "").strip()
            if tk_: c_["hf_token"] = tk_[:200]
            if body.get("hf_token_borrar"): c_.pop("hf_token", None)
            jsave("voz_config.json", c_); logact(None, "Ajustes de voz guardados: motor %s, perfil «%s», velocidad %s, pausa %s ms." % ("Hugging Face (respaldo Voice Studio)" if mo_ == "huggingface" else "Voice Studio", pf_, v_, pz_), "info"); out_ = dict(c_); out_["hf_token_set"] = bool(out_.pop("hf_token", "")); return self._json({"ok": True, "config": out_})
        if pa == "/api/trabajo_externo":   # lo que Claude hace FUERA de los botones del panel (borradores, cambios…) también sale en «Trabajos recientes»: pedido.py avisa aquí cada avance
            ps_ = jload("proyectos.json", []); idea_ = body.get("idea"); pr_ = next((x for x in ps_ if x.get("id") == body.get("proyecto") or (idea_ and x.get("idea") == idea_)), None); clave = (pr_ or {}).get("id") or idea_ or "?"
            tit = (pr_ or {}).get("titulo") or next((x.get("titulo") for x in jload("pedidos.json", []) if x.get("idea") == idea_), "") or clave; pct_ = int(body.get("pct") or 0); fin_ = bool(body.get("hecho")) or bool(body.get("cierra")) or pct_ >= 100 or bool(body.get("error")) or int(body.get("etapa") or 0) == 8 or str(body.get("msg") or "").lower().startswith(("borrador listo", "video listo"))
            with LOCK:
                if idea_ and pr_:   # el proyecto ya está registrado: la barra provisional («esp-<idea>», abierta antes de existir el proyecto) se cierra y pasa a la definitiva
                    for x in JOBS.values():
                        if x.get("externo") and x.get("clave") == "esp-" + str(idea_) and x["estado"] == "corriendo": x["estado"] = "listo"; x["fin"] = time.time(); x["pct"] = 100
                j = next((x for x in JOBS.values() if x.get("externo") and x.get("clave") == clave and x["estado"] == "corriendo"), None)
                if not j: JID[0] += 1; j = {"id": JID[0], "tipo": "claude", "externo": True, "clave": clave, "n": None, "proyecto": (pr_ or {}).get("id"), "estado": "corriendo", "inicio": time.time(), "ultima": time.time(), "pct": 0, "fin": None, "log": ["== Claude trabaja en «%s» ==" % tit[:60]], "esperado": 300}; JOBS[j["id"]] = j
                j["ultima"] = time.time(); j["pct"] = max(j.get("pct", 0), pct_) if not fin_ else (100 if not body.get("error") and (body.get("hecho") or pct_ >= 100) else (max(j.get("pct", 0), pct_) if not body.get("error") else j.get("pct", 0))); j["log"].append(str(body.get("msg") or "")[:300]); j["log"] = j["log"][-400:]
                if fin_: j["estado"] = "error" if body.get("error") else "listo"; j["fin"] = time.time(); j["pct"] = j["pct"] if body.get("error") else 100
            return self._json({"ok": True, "job": j["id"]})
        if pa == "/api/plugin_revisar":   # precarga: lee el .zip y dice si es un plugin del DevIAs Panel y si cumple (no instala nada)
            import base64
            try: data = base64.b64decode(body.get("zip_b64") or "")
            except Exception: return self._json({"es_plugin": False, "ok": False, "tipo": "no-zip", "mensaje": "archivo no válido"})
            return self._json(revisar_plugin_zip(data))
        if pa == "/api/plugin_instalar_zip":   # instala (o actualiza) un plugin desde un .zip enviado en base64; solo se instala si cumple el esqueleto
            import base64
            try: data = base64.b64decode(body.get("zip_b64") or "")
            except Exception: return self._json({"ok": False, "error": "archivo no válido"}, 400)
            r_ = instalar_plugin_zip(data, bool(body.get("actualizar"))); return self._json(r_, 200 if r_.get("ok") else (409 if r_.get("existe") else 400))
        if pa == "/api/plugin_desinstalar":   # desinstala (a _papelera, recuperable); nunca un plugin activo
            r_ = desinstalar_plugin(str(body.get("id", ""))); return self._json(r_, 200 if r_.get("ok") else 400)
        if pa == "/api/rehacer_todo":   # «Rehacer todo»: la versión anterior se archiva (recuperable) y el video vuelve a EN ESPERA para que el cerebro lo genere de nuevo, de otra forma y con el motor actualizado
            pid = str(body.get("id", "")); ps_ = jload("proyectos.json", []); p_ = next((x for x in ps_ if x.get("id") == pid), None); idea_ = (p_ or {}).get("idea") or (pid[4:] if pid.startswith("esp-") else None)
            if not idea_: return self._json({"error": "ese video no existe"}, 404)
            with LOCK: busy = [j for j in JOBS.values() if j["estado"] == "corriendo" and j.get("proyecto") == pid and (not j.get("externo") or time.time() - j.get("ultima", 0) < 600)]
            if busy: return self._json({"error": "Este video tiene un trabajo en curso. Espera a que termine para rehacerlo."}, 409)
            cat_ = jload("catalogo.json", []); it_ = next((i for i in cat_ if i["id"] == idea_), None)
            if not it_: return self._json({"error": "la idea de este video ya no existe"}, 404)
            anterior = {"titulo": (p_ or {}).get("titulo") or it_.get("titulo")}; dst = None; c_ = carpeta(p_) if p_ else None
            if c_ is not None and c_.is_dir():
                try: _cj = json.loads((c_ / "config.json").read_text(encoding="utf-8")); anterior["config"] = _cj.get("inicio"); anterior["diseno"] = _cj.get("diseno")
                except Exception: pass
                try: anterior["guion"] = [x.get("texto", "") for x in json.loads((c_ / "guion" / "1.json").read_text(encoding="utf-8"))][:40]   # para que el guion nuevo NO repita sus frases
                except Exception: pass
                pap_ = ROOT / "_papelera" / "videos"; pap_.mkdir(parents=True, exist_ok=True); dst = pap_ / ("%s_rehecho_%s" % (c_.name, time.strftime("%Y%m%d_%H%M%S")))
                try: _fallos = archivar_carpeta(c_, dst)   # copia primero y borra despues: NUNCA deja el video a medio mover (un archivo en uso ya no rompe el «Rehacer todo»)
                except Exception as e_: return self._json({"error": "No pude archivar la versión anterior (no se borró nada): %s" % e_}, 409)
                if _fallos: logact(idea_, "Rehacer todo: la versión anterior se copió a la papelera; no se pudieron borrar (en uso, se reemplazan al regrabar): %s" % ", ".join(_fallos[:4]), "pedido")
            ped_ = jload("pedidos.json", []); prev = next((x for x in reversed(ped_) if x.get("idea") == idea_ and x.get("tipo") == "video"), {})
            jsave("proyectos.json", [x for x in ps_ if x.get("id") not in (pid, "esp-" + idea_)]); jsave("pedidos.json", [x for x in ped_ if x.get("idea") != idea_])
            tf_ = ROOT / "titulos" / (pid + ".json")
            if tf_.exists():
                try: tf_.unlink()
                except Exception: pass
            cierra_trabajos_de(pid, "esp-" + str(idea_), idea_)
            logact(idea_, "Rehacer todo: «%s» vuelve al cerebro (la versión anterior quedó en _papelera/videos)." % anterior["titulo"], "pedido")
            body = {"id": idea_, "formato": (p_ or {}).get("formato") or prev.get("formato") or it_.get("formato"), "seg": (p_ or {}).get("seg") or prev.get("seg") or it_.get("seg"), "config": it_.get("config_video") or prev.get("config_video") or {}, "rehacer": True, "anterior": anterior, "papelera": str(dst) if dst else ""}
            pa = "/api/idea_a_claude"
        if pa == "/api/idea_a_claude":   # «Díselo a Claude»: formato y duración del plugin activo -> pedido real + video EN ESPERA
            d_, m_ = plugin_activo()
            if not d_: return self._json(SIN_PLUGIN, 409)
            cat = jload("catalogo.json", []); it = next((i for i in cat if i["id"] == body.get("id")), None)
            if not it: return self._json({"error": "idea no existe"}, 404)
            fms = {f_["id"]: f_ for f_ in formatos_de(m_)}; fm = body.get("formato", it.get("formato")); fm = fm if fm in fms else next(iter(fms)); F = fms[fm]; asp = F["aspecto"]
            ajs = (estado_plugins().get("ajustes") or {}).get(d_.name) or {}; seg = max(15, min(900, int(body.get("seg") or F["defecto"])))
            cfgv, err_ = limpia_config_video(m_, body.get("config"))
            if err_: return self._json({"error": err_}, 400)
            ag = correr_agentes(d_, m_, it, cfgv, fm, seg, body.get("anterior"))
            it.update({"formato": fm, "aspecto": asp, "seg": seg, "estado": "espera", "plugin": d_.name, "config": dict(cola.cfg_default(fm, it["titulo"], it.get("desc")), duracion=seg), "config_video": cfgv}); jsave("catalogo.json", cat)
            ped = jload("pedidos.json", []); ped = [x for x in ped if not (x.get("idea") == it["id"] and x.get("tipo") == "video")]
            nota = "[%s · %d s · %s] NUEVO VIDEO con el plugin «%s» (carpeta plugins/%s del DevIAs Panel; leer %s y sus reglas). Idea: %s. Enfoque: %s. Cómo sucedería: %s. Referencia: %s. Pedido original: «%s». Ajustes del plugin: %s.%s Avisar el avance con pedido.py --etapa." % (asp, seg, fm, m_["nombre"], d_.name, m_["instrucciones"], it["titulo"], it.get("enfoque", ""), " | ".join(it.get("como", [])), it.get("ref", ""), it.get("pedido_texto", it["titulo"]), json.dumps(dict({a["id"]: a.get("defecto") for a in m_["ajustes"]}, **ajs), ensure_ascii=False), ((" CONFIGURACIÓN DE ESTE VIDEO (elegida por el usuario en Ideas): " + texto_config_video(m_, cfgv) + ".") if cfgv else ""))
            nota += texto_agentes(ag)
            if body.get("rehacer"): nota += " REHACER TODO (versión NUEVA): el usuario pidió volver a generar este video desde cero con el motor actualizado y de OTRA forma. La versión anterior quedó archivada en «%s» y usó: %s. Haz un video distinto (otro inicio, otro diseño, otra jugada estrella): no copies la versión anterior. EL GUION TAMBIÉN DEBE SER NUEVO: otro gancho (no abras con «%s»), frases y estructura distintas (no repitas las frases del guion anterior que van en «guion» de arriba, salvo la llamada a dar like/suscribirse y a comentar), y los títulos, la descripción y las etiquetas se generan de nuevo." % (body.get("papelera") or "—", json.dumps(dict((k, v) for k, v in (body.get("anterior") or {}).items() if k != "guion"), ensure_ascii=False) + " · guion anterior: " + json.dumps(((body.get("anterior") or {}).get("guion") or [])[:40], ensure_ascii=False), (((body.get("anterior") or {}).get("guion") or [""])[0])[:80])
            ped.append({"idea": it["id"], "tipo": "video", "plugin": d_.name, "config_video": cfgv, "agentes": ag, "rehecho": bool(body.get("rehacer")), "titulo": it["titulo"], "formato": fm, "aspecto": asp, "seg": seg, "nota": nota, "hora": time.strftime("%Y-%m-%d %H:%M"), "ts": time.time(), "estado": "pendiente", "pct": 0, "etapa": 1}); jsave("pedidos.json", ped)
            ps_ = [x for x in jload("proyectos.json", []) if x.get("id") != "esp-" + it["id"]]
            ps_.append({"id": "esp-" + it["id"], "titulo": it["titulo"], "formato": fm, "aspecto": asp, "estado": "espera", "idea": it["id"], "plugin": d_.name, "seg": seg, "duracion": seg, "enviado_ts": time.time(), "progreso": {"etapa": "espera", "pct": 0, "msg": "En espera de Claude", "act": time.strftime("%Y-%m-%d %H:%M:%S")}}); jsave("proyectos.json", ps_)
            logact(it["id"], "Enviado a Claude: «%s» (%s, %d s) con el plugin «%s»." % (it["titulo"][:70], asp, seg, m_["nombre"]), "pedido"); return self._json({"ok": True, "proyecto": "esp-" + it["id"]})
        if pa == "/api/guion":
            p = proyecto(body.get("id"));
            if not p: return self._json({"error": "proyecto no existe"}, 404)
            c = carpeta(p); g = [{"t": float(l["t"]), "texto": l["texto"].strip(), "key": l.get("key", "u%02d" % (k + 1))} for k, l in enumerate(body["lineas"])]
            gp = c / p.get("guion", "guion/1.json"); shutil.copy(gp, str(gp) + ".bak"); gp.write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding="utf-8"); return self._json({"ok": True, "lineas": len(g)})
        if pa == "/api/job":
            p = proyecto(body.get("id"))
            if not p: return self._json({"error": "proyecto no existe"}, 404)
            if body.get("tipo") in ("final_audio", "audio_final") and (carpeta(p) / "proyecto.json").exists():   # proyecto del pipeline nuevo: el boton viejo = «Estoy conforme»
                jid = iniciar_conforme(p)
                return self._json({"ok": True, "job": jid} if jid else {"error": "ya hay un trabajo corriendo; espera a que termine"}, 200 if jid else 409)
            if body.get("tipo") in ("audio_final", "final_audio") and not (p.get("escenas") and all(e.get("estado") == "aprobada" for e in p["escenas"])): return self._json({"error": "El audio se genera cuando TODAS las escenas estan hechas y aprobadas."}, 400)
            with LOCK:
                if any(j["estado"] == "corriendo" for j in JOBS.values()): return self._json({"error": "ya hay un trabajo corriendo; espera a que termine"}, 409)
                JID[0] += 1; job = {"id": JID[0], "tipo": body["tipo"], "n": body.get("n"), "proyecto": p["id"], "estado": "corriendo", "inicio": time.time(), "ultima": time.time(), "pct": 0, "fin": None, "log": []}; JOBS[job["id"]] = job
            if body["tipo"] == "escena": threading.Thread(target=run_escena, args=(job, p, int(body["n"])), daemon=True).start()
            elif body["tipo"] == "final_audio": threading.Thread(target=run_final, args=(job, p), daemon=True).start()
            else: threading.Thread(target=(run_audio_final if body["tipo"] == "audio_final" else run_job), args=((job, p) if body["tipo"] == "audio_final" else (job, p, body["tipo"])), daemon=True).start()
            return self._json({"ok": True, "job": job["id"]})
        self.send_error(404)

def _enciende_todo():   # «activar el panel» = activar todo: al arrancar se enciende también la API de voz (si Voice Studio está instalado y devpanel.json no dice "voz_al_iniciar": false)
    try:
        cfg = json.loads((ROOT / "devpanel.json").read_text(encoding="utf-8")) if (ROOT / "devpanel.json").exists() else {}
        if cfg.get("voz_al_iniciar", True) and not voice_up() and (VS_PY.exists() and (VS_DIR / "backend").exists()): print("Encendiendo Voice Studio (API de voz)…", flush=True); voice_iniciar()
    except Exception as e: print("aviso: no se pudo encender Voice Studio al iniciar:", e, flush=True)
class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True; allow_reuse_address = True
    def handle_error(self, request, client_address):   # el navegador cierra la conexión a mitad de una respuesta (recarga, mover el video…): es normal, no es un error del panel
        if issubclass(sys.exc_info()[0] or Exception, (ConnectionError, TimeoutError)): return
        super().handle_error(request, client_address)
if __name__ == "__main__":
    print("DEVPANEL en http://localhost:%d  (Ctrl+C para cerrar)" % PORT, flush=True); threading.Thread(target=_vigila_versiones, daemon=True).start(); threading.Thread(target=_vigila_claude, daemon=True).start(); threading.Thread(target=_enciende_todo, daemon=True).start(); S(("127.0.0.1", PORT), H).serve_forever()

