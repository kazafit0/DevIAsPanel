"""VOCES DEL DEVPANEL. Cinco motores (piper, kokoro y voicestudio corren en tu PC; edge y clon van por internet):
  piper       = voces .onnx descargadas en  <carpeta de usuario>/voces_tts  (o <panel>/voces_tts)  (ej. es_MX-claude-high)   -> python -m piper
  kokoro      = voces em_alex / em_santa vía HyperFrames (Node 22+, `npx hyperframes tts`)
  clon        = voces clonadas ya guardadas en <panel>/voces_tts/clones (audio de referencia + texto), con VoxCPM (Hugging Face, por INTERNET)
  edge        = voces de Microsoft Edge (paquete edge-tts, ej. es-MX-JorgeNeural). OJO: va por INTERNET; no usa tu PC.
  voicestudio = OPCIONAL: tus perfiles de Voice Studio (programa aparte, API local en el puerto 3900). Lo enciende y apaga el panel (servidor.py); aquí solo se listan sus perfiles y se genera la muestra de «Escuchar».
Se instalan con  instalar_voces.py  (en la carpeta del panel). Aquí solo se SINTETIZA una frase y se devuelve (audio float32 mono, sr).
La velocidad se aplica con ffmpeg (atempo) en todos los motores menos Voice Studio, que la recibe en su API. Variable opcional: VOCES_TTS_DIR.
catalogo() lista las voces que ve el panel (Ajustes → Voz) y sintetizar_wav() genera un WAV para «Escuchar»."""
import os, sys, json, shutil, subprocess, pathlib, wave, importlib.util, time
import numpy as np

SR = 24000
PANEL = pathlib.Path(__file__).resolve().parent.parent
def carpetas():   # dónde se buscan las voces Piper (sin repetir)
    out = []
    for c in (os.environ.get("VOCES_TTS_DIR"), pathlib.Path.home() / "voces_tts", PANEL / "voces_tts"):
        if c and pathlib.Path(c) not in out: out.append(pathlib.Path(c))
    return out
KOKORO = {"em_alex": "Alex · neutra y natural", "em_santa": "Santa · cálida"}
EDGE = {"es-MX-JorgeNeural": "Jorge · México"}
POR_DEFECTO = {"piper": "es_MX-claude-high", "kokoro": "em_alex", "edge": "es-MX-JorgeNeural"}
MOTORES = ("piper", "kokoro", "edge", "clon", "voicestudio")
_HFC = None
FRASE = "Hola. Esta es una prueba de voz para tus videos. Si me escuchas bien, ya puedes usarme."
VS_PUERTO = 3900


def _cfg():
    try: return json.loads((PANEL / "voz_config.json").read_text(encoding="utf-8"))
    except Exception: return {}


def _modelo(voz):
    for c in carpetas():
        if (c / (voz + ".onnx")).exists(): return c / (voz + ".onnx")
    return None


def carpeta_propia():   # aquí van TUS voces Piper (cada una: NOMBRE.onnx + NOMBRE.onnx.json)
    c = PANEL / "voces_tts"; c.mkdir(exist_ok=True); return c


def voces_piper():   # solo cuentan las que traen su .onnx.json (Piper lo exige)
    return sorted({p.name[:-5] for c in carpetas() if c.is_dir() for p in c.glob("*.onnx") if (c / (p.name + ".json")).exists()})


def kokoro_listo():
    return importlib.util.find_spec("kokoro_onnx") is not None and importlib.util.find_spec("soundfile") is not None and bool(shutil.which("npx.cmd") or shutil.which("npx"))


def carpeta_clones():   # voces clonadas: NOMBRE.wav (audio de referencia) + NOMBRE.txt (lo que dice el audio, opcional)
    c = carpeta_propia() / "clones"; c.mkdir(exist_ok=True); return c


def clones():
    return sorted(p.stem for p in carpeta_clones().glob("*.wav"))


def clon_listo():
    return importlib.util.find_spec("gradio_client") is not None


def edge_listo():
    return importlib.util.find_spec("edge_tts") is not None


# ---------------- VOICE STUDIO (opcional) ----------------
def _es_project(p):
    return p.is_dir() and (p / "backend").is_dir() and (p / ".venv" / "Scripts" / "python.exe").exists()


def _normaliza_vs(p):
    """Acepta la carpeta «project», la que la contiene (con data/) o la carpeta VoiceStudio de arriba. Devuelve la carpeta «project» o None."""
    p = pathlib.Path(str(p).strip().strip('"'))
    for q in (p, p / "project", p / "VoiceStudio" / "project"):
        if _es_project(q): return q
    return None


def vs_buscar(limite_s=25):
    """Busca Voice Studio en el PC: variable VOICESTUDIO_DIR, sitios habituales y carpetas *VoiceStudio* hasta 3 niveles en cada disco."""
    cand = [os.environ.get("VOICESTUDIO_DIR"), os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "VoiceStudio"), os.path.join(os.environ.get("ProgramFiles", ""), "VoiceStudio"), os.path.join(os.path.expanduser("~"), "VoiceStudio")]
    for c in cand:
        if c and _normaliza_vs(c): return _normaliza_vs(c)
    t0 = time.time(); saltar = {"windows", "$recycle.bin", "system volume information", "programdata", "appdata", "node_modules", ".git", "recovery", "perflogs"}
    for letra in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        raiz = pathlib.Path(letra + ":\\")
        if not raiz.exists(): continue
        cola = [(raiz, 0)]
        while cola and time.time() - t0 < limite_s:
            d, n = cola.pop(0)
            try: hijos = [h for h in os.scandir(d) if h.is_dir(follow_symlinks=False)]
            except Exception: continue
            for h in hijos:
                nm = h.name.lower()
                if nm in saltar: continue
                if "voicestudio" in nm:
                    r = _normaliza_vs(h.path)
                    if r: return r
                if n < 3: cola.append((pathlib.Path(h.path), n + 1))
    return None


def vs_dir():
    """Carpeta «project» de Voice Studio, igual que antes: «voice_studio_dir» de devpanel.json, la variable VOICESTUDIO_DIR o los sitios habituales; None si no hay."""
    try: d = json.loads((PANEL / "devpanel.json").read_text(encoding="utf-8")).get("voice_studio_dir")
    except Exception: d = None
    for c in (d, os.environ.get("VOICESTUDIO_DIR"), os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "VoiceStudio"), os.path.join(os.environ.get("ProgramFiles", ""), "VoiceStudio"), os.path.join(os.path.expanduser("~"), "VoiceStudio")):
        if c and _normaliza_vs(c): return _normaliza_vs(c)
    return None


def vs_arriba():
    import urllib.request
    try: urllib.request.urlopen("http://127.0.0.1:%d/health" % VS_PUERTO, timeout=1.5); return True
    except Exception: return False


def _vs_data(proj):
    d = proj.parent / "data"; return d if d.exists() else None


def vs_perfiles():
    """Nombres de los perfiles de voz de Voice Studio (se lee una copia de su base de datos: no hace falta que esté encendido)."""
    import sqlite3, tempfile
    proj = vs_dir(); dd = _vs_data(proj) if proj else None
    if not dd or not (dd / "omnivoice.db").exists(): return []
    t = tempfile.mkdtemp()
    try:
        for f in ("omnivoice.db", "omnivoice.db-wal", "omnivoice.db-shm"):
            if (dd / f).exists(): shutil.copy(dd / f, t)
        con = sqlite3.connect(os.path.join(t, "omnivoice.db")); r = [x[0] for x in con.execute("select name from voice_profiles order by name").fetchall()]; con.close(); return r
    except Exception: return []
    finally: shutil.rmtree(t, ignore_errors=True)


def vs_error_amigable(msg, perfil=""):
    """Traduce el error de Voice Studio a algo que se entienda."""
    import re
    msg = str(msg or "")
    if "clone_ref_too_long" in msg:
        m = re.search(r"([\d.]+) seconds", msg); seg = (m.group(1) if m else "?")
        return ("El perfil «%s» tiene un audio de referencia de %s s y esta versión de Voice Studio solo acepta hasta 20 s. Solución: en Voice Studio recorta ese audio a 3-10 s, o instala un modelo de voz a texto (Catálogo de modelos) para que lo recorte solo. Mientras tanto usa otro perfil." % (perfil, seg))
    return msg[:260] or "Voice Studio respondió con un error."


def _vs_post(texto, voz, v, seed, pasos):
    import urllib.request, urllib.error
    b = {"model": "omnivoice", "input": texto + ",---------------------------------- final", "voice": voz, "response_format": "wav", "language": "es", "seed": int(seed), "num_step": int(pasos), "speed": v}
    for intento in range(12):   # Voice Studio genera de a una frase: si su cola está llena responde «saturado» y pide reintentar en unos segundos
        try: return urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:%d/v1/audio/speech" % VS_PUERTO, data=json.dumps(b).encode(), headers={"Content-Type": "application/json"}), timeout=600).read()
        except urllib.error.HTTPError as e:
            try: cuerpo = json.loads(e.read().decode("utf-8", "replace")).get("error", {}).get("message", "")
            except Exception: cuerpo = ""
            if ("saturated" in cuerpo or "safe to retry" in cuerpo or e.code in (429, 503)) and intento < 11: time.sleep(8); continue
            raise RuntimeError(("Voice Studio sigue ocupado con otra generación: espera a que termine y vuelve a intentar." if "saturated" in cuerpo else vs_error_amigable(cuerpo, voz)) if cuerpo else "Voice Studio respondió con el error %s." % e.code)


def _corridas(y, sr, gap=.10):   # rachas de voz; huecos menores que `gap` s no separan
    fr = int(sr * .01); e = np.array([np.abs(y[i:i + fr]).max() for i in range(0, len(y) - fr, fr)]); v = e > .02; runs = []; i = 0; g = int(gap / .01)
    while i < len(v):
        if v[i]:
            j = i
            while j < len(v) and (v[j] or v[j:j + g].any()): j += 1
            runs.append([i * .01, j * .01]); i = j
        else: i += 1
    return runs


def _corta_marca(y, sr):
    """Voice Studio recibe el texto + una marca «final» detrás de un silencio largo (así no se come las últimas sílabas). La marca es la ÚLTIMA racha de voz, corta, detrás de un hueco: se corta en medio del hueco. Si no se distingue, la toma queda como está."""
    rr = _corridas(y, sr)
    if len(rr) >= 2 and (rr[-1][1] - rr[-1][0]) <= 1.0 and rr[-1][0] - rr[-2][1] >= .25:
        cut = int(((rr[-2][1] + rr[-1][0]) / 2) * sr)
        if cut > .3 * sr:
            yy = y[:cut].copy(); fd = int(.02 * sr); yy[-fd:] *= np.linspace(1, 0, fd); return yy, True
    return y, False
# ---------------- fin Voice Studio ----------------


def _nombre_piper(vid):
    conocidos = {"es_MX-claude-high": "Claude · México, calidad alta", "es_ES-davefx-medium": "Davefx · España, calidad media", "es_MX-ald-medium": "Ald · México, calidad media"}
    if vid in conocidos: return conocidos[vid]
    p = vid.split("-")
    return "%s · %s" % (p[1].capitalize(), p[0]) if len(p) > 1 and p[0][:3] in ("es_", "en_", "pt_", "fr_") else vid.replace("_", " ").title() + " · tu voz"


def catalogo():
    """Todas las voces que el panel puede ofrecer: [{id, nombre, motor, motor_txt, donde, instalada, borrable}]."""
    out = []
    kl = kokoro_listo()
    for vid, nom in KOKORO.items(): out.append({"id": vid, "nombre": nom, "motor": "kokoro", "motor_txt": "Kokoro", "donde": "en tu PC (HyperFrames)", "instalada": kl, "borrable": False})
    pv = voces_piper(); prop = carpeta_propia()
    for vid in pv: out.append({"id": vid, "nombre": _nombre_piper(vid), "motor": "piper", "motor_txt": "Piper", "donde": "en tu PC" if vid.startswith(("es_", "en_")) else "en tu PC · voz tuya", "instalada": True, "borrable": (prop / (vid + ".onnx")).exists()})
    cl = clon_listo()
    for vid in clones(): out.append({"id": vid, "nombre": vid.replace("_", " ").title() + " · clon", "motor": "clon", "motor_txt": "Clon VoxCPM", "donde": "tu voz · por internet (Hugging Face)", "instalada": cl, "borrable": True})
    el = edge_listo()
    for vid, nom in EDGE.items(): out.append({"id": vid, "nombre": nom, "motor": "edge", "motor_txt": "edge-tts", "donde": "por internet, no usa tu PC", "instalada": el, "borrable": False})
    if _cfg().get("voicestudio_activo") and vs_dir():
        for nm in vs_perfiles(): out.append({"id": nm, "nombre": nm, "motor": "voicestudio", "motor_txt": "Voice Studio", "donde": "tu PC · programa aparte", "instalada": True, "borrable": False})
    if POR_DEFECTO["piper"] not in pv: out.append({"id": POR_DEFECTO["piper"], "nombre": _nombre_piper(POR_DEFECTO["piper"]), "motor": "piper", "motor_txt": "Piper", "donde": "en tu PC", "instalada": False, "borrable": False})
    return out


def borrar(motor, vid):
    """Borra una voz subida por el usuario: la MUEVE a <panel>/_papelera/voces (se puede recuperar). Solo voces clonadas y voces Piper de la carpeta del panel."""
    import re
    if not re.fullmatch(r"[A-Za-z0-9_.\- ]+", str(vid or "")): raise RuntimeError("Nombre de voz no válido.")
    if motor == "clon": arch = [carpeta_clones() / (vid + ".wav"), carpeta_clones() / (vid + ".txt")]
    elif motor == "piper": arch = [carpeta_propia() / (vid + ".onnx"), carpeta_propia() / (vid + ".onnx.json")]
    else: raise RuntimeError("Solo se pueden borrar las voces que subiste (clonadas o Piper de la carpeta del panel).")
    if not arch[0].exists(): raise RuntimeError("Esa voz no está en la carpeta del panel, así que no la borro desde aquí.")
    dst = PANEL / "_papelera" / "voces" / time.strftime("%Y%m%d_%H%M%S"); dst.mkdir(parents=True, exist_ok=True)
    for a in arch:
        if a.exists(): shutil.move(str(a), str(dst / a.name))
    return str(dst)


def voz_valida(motor, voz):
    """Devuelve la voz pedida si existe para ese motor; si no, la voz por defecto del motor."""
    voz = (voz or "").strip()
    if motor == "kokoro": return voz if voz in KOKORO else POR_DEFECTO["kokoro"]
    if motor == "edge": return voz if voz in EDGE else POR_DEFECTO["edge"]
    if motor == "clon": return voz if voz in clones() else (clones() or [voz])[0]
    if motor == "voicestudio":
        pv = vs_perfiles(); return voz if (voz in pv or not pv) else pv[0]
    if _modelo(voz): return voz
    d = POR_DEFECTO["piper"]; pv = voces_piper()
    return d if (_modelo(d) or not pv) else pv[0]


FIN_LIMPIO = .30   # energía de los últimos 60 ms respecto a la voz: por encima, la frase probablemente quedó cortada


def _fin_ratio(ffmpeg, path, tmp):
    """Qué tan 'pegada' a la voz termina una toma (0 = acaba en silencio, 1 = acaba en plena palabra). Las tomas de VoxCPM que se cortan terminan con voz."""
    t = pathlib.Path(tmp) / "local_chk.wav"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(path), "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(t)], check=True)
    w = wave.open(str(t)); y = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close(); t.unlink(missing_ok=True)
    fr = 480; e = np.array([np.sqrt(np.mean(y[i:i + fr] ** 2)) for i in range(0, len(y) - fr, fr)])
    if len(e) < 8: return 1.0
    return float(e[-3:].mean() / max(np.percentile(e, 90), 1e-6))


def _run(cmd, **kw):
    cmd = [str(c) for c in cmd]
    if os.name == "nt" and pathlib.Path(cmd[0]).suffix.lower() in (".cmd", ".bat"):
        return subprocess.run(subprocess.list2cmdline(cmd), shell=True, **kw)
    return subprocess.run(cmd, **kw)


def sintetizar_wav(motor, voz, texto, velocidad, tmp, ffmpeg, seed=12345, pasos=32):
    """Genera la frase y devuelve la ruta de un WAV mono de 24 kHz (con la velocidad aplicada). Quien lo llama lo borra."""
    tmp = pathlib.Path(tmp); tmp.mkdir(parents=True, exist_ok=True)
    voz = voz_valida(motor, voz); raw = tmp / "local_raw.wav"; fin = tmp / "local_fin.wav"; v = max(.5, min(2.0, float(velocidad or 1.0)))
    for f in (raw, fin): f.unlink(missing_ok=True)
    if motor == "piper":
        modelo = _modelo(voz)
        if not modelo: raise RuntimeError("No hay voces Piper en %s: ejecuta  python instalar_voces.py --solo-piper" % carpetas()[0])
        r = subprocess.run([sys.executable, "-X", "utf8", "-m", "piper", "-m", str(modelo), "-f", str(raw)], input=texto, text=True, encoding="utf-8", capture_output=True)
        if r.returncode != 0 or not raw.exists(): raise RuntimeError("Piper falló: " + (r.stderr or "")[-300:])
    elif motor == "kokoro":
        npx = shutil.which("npx.cmd") or shutil.which("npx")
        if not npx: raise RuntimeError("Falta Node.js 22+ para Kokoro (nodejs.org).")
        txt = tmp / "local_txt.txt"; txt.write_text(texto, encoding="utf-8")
        r = _run([npx, "--yes", "hyperframes", "tts", txt, "--voice", voz, "--output", raw], capture_output=True)
        if r.returncode != 0 or not raw.exists() or raw.stat().st_size < 4000: raise RuntimeError("Kokoro falló (internet la primera vez, Node 22+, paquetes kokoro-onnx y soundfile): " + (r.stderr or b"").decode("utf-8", "ignore")[-300:])
    elif motor == "edge":
        if not edge_listo(): raise RuntimeError("Falta el paquete edge-tts:  python -m pip install edge-tts")
        txt = tmp / "local_txt.txt"; txt.write_text(texto, encoding="utf-8"); raw = tmp / "local_raw.mp3"; raw.unlink(missing_ok=True)
        r = subprocess.run([sys.executable, "-X", "utf8", "-m", "edge_tts", "--voice", voz, "--file", str(txt), "--write-media", str(raw)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        if r.returncode != 0 or not raw.exists() or raw.stat().st_size < 1000: raise RuntimeError("edge-tts falló (¿hay internet?): " + (r.stderr or "")[-300:])
    elif motor == "voicestudio":
        if not vs_arriba(): raise RuntimeError("Voice Studio está apagado: enciéndelo con el botón de encendido (Ajustes → Voz → Voice Studio).")
        data = _vs_post(texto, voz, v, seed, pasos)
        bruto = tmp / "vs_bruto.wav"; bruto.write_bytes(data)
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(bruto), "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(raw)], check=True); bruto.unlink(missing_ok=True)
        w = wave.open(str(raw)); y = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close()
        y, _cortada = _corta_marca(y, SR)
        w = wave.open(str(fin), "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes()); w.close(); raw.unlink(missing_ok=True)
        return fin   # la velocidad ya la aplicó Voice Studio
    elif motor == "clon":
        global _HFC
        ref = carpeta_clones() / (voz + ".wav")
        if not ref.exists(): raise RuntimeError("No existe la voz clonada «%s»." % voz)
        if not clon_listo(): raise RuntimeError("Falta el paquete gradio_client:  python -m pip install gradio_client")
        from gradio_client import Client, handle_file
        if _HFC is None: _HFC = Client("openbmb/VoxCPM-Demo", verbose=False)
        rt = (carpeta_clones() / (voz + ".txt")); rt = rt.read_text(encoding="utf-8").strip() if rt.exists() else ""
        mejor = None; ultimo_error = ""   # (ratio de corte, ruta): se queda con la toma que termina más limpia
        for n in range(6):   # la API gratuita no tiene semilla: cada intento es otra toma; también se reintenta si el servicio está ocupado
            try: o = _HFC.predict(text_input=texto + (" ." if n % 2 else ""), control_instruction="", reference_wav_path_input=handle_file(str(ref)), use_prompt_text=bool(rt), prompt_text_input=rt, cfg_value_input=2.0, do_normalize=False, denoise=False, api_name="/generate")
            except Exception as ex:
                ultimo_error = repr(ex)[:240]
                if n < 5: time.sleep(4 + 3 * n)
                continue
            cand = tmp / ("clon_toma_%d.wav" % n); shutil.copy(str(o), str(cand)); rr = _fin_ratio(ffmpeg, cand, tmp)
            if mejor is None or rr < mejor[0]:
                if mejor: pathlib.Path(mejor[1]).unlink(missing_ok=True)
                mejor = (rr, cand)
            else: cand.unlink(missing_ok=True)
            if rr <= FIN_LIMPIO: break   # la toma termina en silencio: la frase salió entera
            print("  clon: la toma %d termina cortada (%.2f); pruebo otra" % (n + 1, rr), flush=True)
        if mejor is None: raise RuntimeError("La clonación por internet falló tras 6 intentos (Hugging Face ocupado, sin internet o sin cupo): " + ultimo_error)
        shutil.copy(str(mejor[1]), str(raw)); pathlib.Path(mejor[1]).unlink(missing_ok=True)
    else:
        raise RuntimeError("motor desconocido: %s" % motor)
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(raw), "-af", "atempo=%.4f" % v, "-ar", str(SR), "-ac", "1", "-c:a", "pcm_s16le", str(fin)], check=True)
    raw.unlink(missing_ok=True)
    return fin


def sintetizar(motor, voz, texto, velocidad, tmp, ffmpeg, seed=12345, pasos=32):
    fin = sintetizar_wav(motor, voz, texto, velocidad, tmp, ffmpeg, seed, pasos)
    w = wave.open(str(fin)); y = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close()
    fin.unlink(missing_ok=True)
    return y, SR
