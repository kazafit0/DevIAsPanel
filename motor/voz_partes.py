"""VOZ DEL DEVPANEL (motor ÚNICO para todos los plugins). El guion (guion/1.json = [{key, texto, t?, pausa?}]) se genera PARTE A PARTE con Voice Studio (caché por texto, la palabra «final» como marca de corte);
las partes se unen y se escriben los tiempos. Perfil, velocidad, semilla y pausas salen de voz_config.json del DevIAs Panel (Ajustes → Voz); el plugin solo declara en plugin.json «voz.modo»:
  json_manda (por defecto) = cada parte cae en su segundo `t` del guion (el juego o el usuario marcan los tiempos); si una parte se pasa de su hueco, avisa.
  libre                   = las partes van seguidas con sus pausas; los tiempos reales salen de la voz (el video se arma sobre ellos).
Uso:
  python voz_partes.py CARPETA --borrador   -> tiempos ESTIMADOS (guion/1.json + audiolibro/tiempos.json con "estimado": true). Sin Voice Studio.
  python voz_partes.py CARPETA              -> genera solo las partes nuevas o cambiadas, las une y escribe tiempos REALES + voz/ (voz_completa.wav, 1_NN.wav, textos.json, completa.json, plan.json).
  python voz_partes.py CARPETA --rehacer    -> ignora la caché.        --parte KEY…  -> otra toma de esas partes.        --libre  -> fuerza el modo libre.
Variables: PLUGIN_DIR (para leer voz.modo), DEVPANEL (carpeta del panel), DEVPANEL_TMP (temporales). Caché: audiolibro/partes/."""
import os, sys, json, re, pathlib, urllib.request, urllib.error, wave, subprocess, hashlib, shutil
os.environ["TEMP"] = os.environ["TMP"] = os.environ.get("DEVPANEL_TMP") or os.environ.get("TEMP") or "."
import hashlib as _hl
def _firma_guion(_R):   # claves y textos del guion (no sus tiempos: la voz los reescribe al terminar)
    try: return _hl.md5(json.dumps([(g.get("key"), g.get("texto")) for g in json.loads((pathlib.Path(_R) / "guion" / "1.json").read_text(encoding="utf8"))], ensure_ascii=False).encode()).hexdigest()
    except Exception: return ""
if not os.environ.get("VOZ_HIJO") and "--borrador" not in sys.argv:   # GUARDIA: la voz se genera en un proceso hijo; si el guion cambia mientras tanto, se vuelve a generar con el guion nuevo
    import subprocess as _sp
    for _i in range(3):
        _f0 = _firma_guion(sys.argv[1]); _r = _sp.run([sys.executable, "-X", "utf8", "-u", __file__] + sys.argv[1:], env=dict(os.environ, VOZ_HIJO="1"))
        if _r.returncode != 0: sys.exit(_r.returncode)
        if _firma_guion(sys.argv[1]) == _f0: sys.exit(0)
        print("AVISO: el guion cambió mientras se generaba la voz; la repito con el guion nuevo (solo se generan las frases nuevas o cambiadas).", flush=True)
    sys.exit(0)
import numpy as np, imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe(); R = pathlib.Path(sys.argv[1]).resolve(); A = R / "audiolibro"; PART = A / "partes"; PART.mkdir(parents=True, exist_ok=True); (R / "voz").mkdir(exist_ok=True)
# La voz es del DEVPANEL: la configuración sale de voz_config.json (Ajustes → Voz); el plugin solo declara su modo.
PANEL = pathlib.Path(__file__).resolve().parent.parent; _c = {"perfil": "MI VOZ", "velocidad": 1.1, "semilla": 12345, "pasos": 32, "ritmo_estimado": 0.0775, "pausa_ms": 400, "pausa_min_ms": 200}
try: _c.update(json.loads((PANEL / "voz_config.json").read_text(encoding="utf-8")))
except Exception: pass
SEED = int(_c["semilla"]); NSTEP = int(_c["pasos"]); SR = 48000; RATE = float(_c["ritmo_estimado"]); PAUSA_DEF = int(_c["pausa_ms"]); PAUSA_MIN = int(_c["pausa_min_ms"]); SPEED = float(_c["velocidad"]); PERFIL = str(_c["perfil"])
MOTOR = str(_c.get("motor", "voicestudio")).lower(); HFTOK = str(_c.get("hf_token") or "").strip() or None   # motor: «voicestudio» (local) o «huggingface» (API gratuita VoxCPM; si falla una frase pasa a Voice Studio)
LOCAL = MOTOR in ("piper", "kokoro", "edge", "clon")   # voces locales/por internet SIN Voice Studio (motor/voz_local.py); «voicestudio» sigue con su camino original de abajo
if LOCAL: sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); import voz_local
def _vs_auto():   # dónde está Voice Studio si no se dijo en devpanel.json -> "voice_studio_dir" (sin rutas de nadie): variable VOICESTUDIO_DIR o sitios habituales
    import os
    for b in (os.environ.get("VOICESTUDIO_DIR"), os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "VoiceStudio"), os.path.join(os.environ.get("ProgramFiles", ""), "VoiceStudio"), os.path.join(os.path.expanduser("~"), "VoiceStudio")):
        if b:
            for sub in ("project", ""):
                p = pathlib.Path(b) / sub if sub else pathlib.Path(b)
                if (p / ".venv").exists() or (p / "data").exists(): return p
    return pathlib.Path(os.path.expanduser("~")) / "VoiceStudio" / "project"
try: _cfgp = json.loads((PANEL / "devpanel.json").read_text(encoding="utf-8"))
except Exception: _cfgp = {}
VSDATA = pathlib.Path(str(_c.get("voicestudio_data") or (pathlib.Path(_cfgp["voice_studio_dir"]).parent / "data" if _cfgp.get("voice_studio_dir") else _vs_auto().parent / "data")))
MODO = "json_manda"
try: MODO = (json.loads((pathlib.Path(os.environ["PLUGIN_DIR"]) / "plugin.json").read_text(encoding="utf-8")).get("voz") or {}).get("modo", "json_manda")
except Exception: pass
BORRADOR = "--borrador" in sys.argv; REHACER = "--rehacer" in sys.argv
PARTES = set(sys.argv[sys.argv.index("--parte") + 1:]) if "--parte" in sys.argv else set(); PASOS = [32, 36, 28, 40, 24]   # «Rehacer voz» de UNA parte: otra toma (cambian los pasos), misma voz y semilla
G = json.loads((R / "guion" / "1.json").read_text(encoding="utf8")); n = len(G)
PA = {}; vu = R / "tools" / "voz_unica.py"
if vu.exists():
    m = re.search(r"PAUSAS = (\{.*?\})\n", vu.read_text(encoding="utf8"), re.S)
    if m:
        try: PA = json.loads(m.group(1))
        except Exception: PA = {}
def limpio(t): return re.sub(r"\.\s+", ", ", t.strip()).replace(".", "").rstrip(",;: ").strip()   # NUNCA puntos (frenan el habla)
txs = [limpio(g["texto"]) for g in G]; pau = [max(PAUSA_MIN, int(g.get("pausa") or PA.get(g["key"], PAUSA_DEF))) for g in G]
def escribe(S, E, dur, estimado):
    tags = {g["key"]: [round(S[i], 2), round(E[i], 2)] for i, g in enumerate(G)}
    for nm in ("1.json", "1_original.json"):
        pp = R / "guion" / nm
        if not pp.exists(): continue
        gg = json.loads(pp.read_text(encoding="utf8"))
        for o in gg:
            if o["key"] in tags: o["t"] = tags[o["key"]][0]
        pp.write_text(json.dumps(gg, ensure_ascii=False, indent=1), encoding="utf8")
    (A / "tiempos.json").write_text(json.dumps({"orden": [g["key"] for g in G], "dur": round(dur, 2), "perfil": PERFIL, "seed": SEED, "speed": SPEED, "metodo": "partes_con_final", "estimado": estimado, "pausas_ms": {g["key"]: pau[i] for i, g in enumerate(G)}, "tags": tags}, ensure_ascii=False, indent=1), encoding="utf8")
    (R / "plan.json").write_text(json.dumps([{"k": k + 1, "key": g["key"], "texto": g["texto"], "escena": 1, "t_suceso": tags[g["key"]][0], "at": tags[g["key"]][0], "dur": round(tags[g["key"]][1] - tags[g["key"]][0], 2), "retraso": 0.0, "se_pasa": 0} for k, g in enumerate(G)], ensure_ascii=False, indent=1), encoding="utf8")
    return tags
if BORRADOR:
    rate = RATE
    try:
        t = json.loads((A / "tiempos.json").read_text(encoding="utf8"))
        if not t.get("estimado"):
            tg_ = t.get("colocado") or t["tags"]   # en modo «JSON manda» los tiempos reales de la voz están en «colocado»
            r = [(tg_[g["key"]][1] - tg_[g["key"]][0]) / max(1, len(g["texto"])) for g in G if g["key"] in tg_]
            if len(r) > 5: rate = float(np.median(r))
    except Exception: pass
    t = 0.3; S = []; E = []
    for i in range(n):
        d = rate * len(txs[i]) + .2 * txs[i].count(","); S.append(t); E.append(t + d); t += d + pau[i] / 1000
    tg = escribe(S, E, t + 1.0, True); print("BORRADOR (%.4f s/carácter): %.1f s, %d partes" % (rate, t + 1.0, n)); sys.exit(0)
def vs_abierto():
    try: urllib.request.urlopen("http://127.0.0.1:3900/health", timeout=5); return True
    except Exception: return False
if MOTOR != "huggingface" and not LOCAL and not vs_abierto(): sys.exit("Voice Studio esta CERRADO (puerto 3900). Abrelo y repite.")
print("MOTOR DE VOZ: %s" % ("Hugging Face (VoxCPM2 por API; respaldo Voice Studio)" if MOTOR == "huggingface" else ("%s, voz %s" % (MOTOR.capitalize(), voz_local.voz_valida(MOTOR, PERFIL))) if LOCAL else "Voice Studio (local)"), flush=True)
_SAT = 0   # reintentos cuando Voice Studio responde «saturado» (atiende de a una frase)
def tts(tx, ns=NSTEP, perfil=None, seed=None):   # perfil: opcional por línea del guion («perfil» en guion/1.json); si no, el perfil general
    b = {"model": "omnivoice", "input": tx + ",---------------------------------- final", "voice": (perfil or PERFIL), "response_format": "wav", "language": "es", "seed": (SEED if seed is None else seed), "num_step": ns, "speed": SPEED}
    try: raw = urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:3900/v1/audio/speech", data=json.dumps(b).encode(), headers={"Content-Type": "application/json"}), timeout=600).read()
    except urllib.error.HTTPError as e:   # el motivo real viene en el cuerpo de la respuesta: se muestra claro en vez de «HTTP Error 500»
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); import voz_local as _vl
        try: cuerpo = json.loads(e.read().decode("utf-8", "replace")).get("error", {}).get("message", "")
        except Exception: cuerpo = ""
        global _SAT
        if ("saturated" in cuerpo or "safe to retry" in cuerpo) and _SAT < 30: _SAT += 1; print("  Voice Studio está ocupado con otra generación; espero 8 s y reintento (%d)" % _SAT, flush=True); import time as _tt; _tt.sleep(8); return tts(tx, ns, perfil, seed)
        sys.exit("Voice Studio no pudo generar la frase: " + (_vl.vs_error_amigable(cuerpo, b["voice"]) if cuerpo else "error %s" % e.code))
    tmp = A / "tmp_parte.wav"; tmp.write_bytes(raw); w = wave.open(str(tmp)); sr = w.getframerate(); ch = w.getnchannels(); y = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close(); tmp.unlink()
    return (y.reshape(-1, ch).mean(1) if ch > 1 else y), sr
_WM = None; CUTV = 13
def corridas(y, sr, gap=.08):   # rachas de voz; huecos menores que `gap` s no separan (una palabra puede partirse en dos rachas)
    fr = int(sr * .01); e = np.array([np.abs(y[i:i + fr]).max() for i in range(0, len(y) - fr, fr)]); v = e > .02; runs = []; i = 0; g = int(gap / .01)
    while i < len(v):
        if v[i]:
            j = i
            while j < len(v) and (v[j] or v[j:j + g].any()): j += 1
            runs.append([i * .01, j * .01]); i = j
        else: i += 1
    return runs
def corta_final(y, sr, texto):   # «final» es la MARCA: la última racha de voz detrás de un hueco. Se corta justo antes, anclado al texto real (Whisper); si «final» no se pronunció no se corta nada
    global _WM
    import unicodedata, difflib
    try: from faster_whisper import WhisperModel
    except ImportError:   # sin Whisper instalado: solo el criterio de silencios (la marca es la última racha corta tras un hueco largo)
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent)); import voz_local as _vl; return _vl._corta_marca(y, sr)
    runs = corridas(y, sr)
    if _WM is None: _WM = WhisperModel("small", device="cpu", compute_type="int8")
    tmp = A / "tmp_final.wav"; w = wave.open(str(tmp), "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes()); w.close()
    segs, _ = _WM.transcribe(str(tmp), language="es", word_timestamps=True); tmp.unlink()
    nz = lambda t: re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFD", t.lower()).encode("ascii", "ignore").decode())
    ws = [(nz(x.word), float(x.start), float(x.end)) for s_ in segs for x in s_.words]; ws = [w_ for w_ in ws if w_[0]]
    last_tok = [nz(z) for z in texto.split() if nz(z)][-1]; ls, ld = runs[-1]; gap_prev = (ls - runs[-2][1]) if len(runs) >= 2 else 0.0
    fi = [k for k, (wd, t, _e) in enumerate(ws) if (wd.startswith("fin") or wd == "final") and not last_tok.startswith("fin")]
    if fi:   # (1) lo más fiable: la marca es la ÚLTIMA racha de voz (corta) detrás de un hueco; el corte va en medio de ese hueco (Whisper falla en los tiempos de las cifras)
        rr = corridas(y, sr, .10)
        if len(rr) >= 2 and (rr[-1][1] - rr[-1][0]) <= 1.0 and rr[-1][0] - rr[-2][1] >= .05:
            cut = int(((rr[-2][1] + rr[-1][0]) / 2) * sr)
            if cut > .3 * sr:
                yy = y[:cut].copy(); fd = int(.02 * sr); yy[-fd:] *= np.linspace(1, 0, fd); return yy, True
    if fi:   # Whisper oyó la marca: el corte va en un HUECO de silencio (energía < 3-10 % del pico) justo antes de «final», nunca dentro de una palabra
        k = fi[-1]; t = ws[k][1]; prev_end = ws[k - 1][2] if k > 0 else 0.0; fr = int(sr * .005); peak = float(np.abs(y).max())
        lo = int(max(prev_end - .05, t - .35, 0) * sr); hi = min(len(y) - fr, int((t + .10) * sr)); e = np.array([np.abs(y[i:i + fr]).max() for i in range(lo, hi, fr)]); cut = None
        for th in (.03, .06, .10):
            low = set(np.where(e < th * peak)[0].tolist()); cand = [i for i in sorted(low) if lo + i * fr <= (t + .05) * sr]
            if cand:
                j = cand[-1]; i0 = j
                while (i0 - 1) in low: i0 -= 1
                cut = lo + ((i0 + j) // 2) * fr + fr // 2; break
        if cut is None: cut = int(max(prev_end, t - .02) * sr)   # sin hueco claro: lo más tarde posible antes de «final», con fundido
        if cut > .3 * sr:
            yy = y[:cut].copy(); fd = int(.02 * sr); yy[-fd:] *= np.linspace(1, 0, fd); return yy, True
    rr2 = corridas(y, sr, .10)   # (2) Whisper no transcribió la marca (se funde con una cifra): si la voz dura mucho más que lo esperado por el texto y hay una última racha corta detrás de un hueco, esa racha es «final»
    esperado = len(texto) * .0775 + .2 * texto.count(",")
    if len(rr2) >= 2 and (rr2[-1][1] - rr2[0][0]) > 1.18 * esperado and .3 <= (rr2[-1][1] - rr2[-1][0]) <= 1.0 and rr2[-1][0] - rr2[-2][1] >= .05:
        cut = int(((rr2[-2][1] + rr2[-1][0]) / 2) * sr)
        if cut > .3 * sr:
            yy = y[:cut].copy(); fd = int(.02 * sr); yy[-fd:] *= np.linspace(1, 0, fd); return yy, True
    anchor = next((t for wd, t, _e in reversed(ws) if wd == last_tok or (len(last_tok) > 4 and wd[:4] == last_tok[:4])), None)
    if anchor is not None:   # la racha que contiene la última palabra real termina el texto; lo que viene detrás es «final»
        k = max([j for j, r in enumerate(runs) if r[0] <= anchor + .15] or [0])
        if k >= len(runs) - 1: return y, False
        cut = int((runs[k][1] + .08) * sr); return (y[:cut], True) if cut > .3 * sr else (y, False)
    if ld - ls <= .75 and gap_prev >= .2:   # sin ancla (p. ej. cifras): la última racha corta tras un hueco es «final»
        cut = int((runs[-2][1] + .08) * sr); return y[:cut], True
    return y, False
_HFC = None; _HFREF = {}
def _norm_(t):
    import unicodedata
    t = unicodedata.normalize("NFD", t.lower()); t = "".join(c for c in t if unicodedata.category(c) != "Mn"); return re.sub(r"[^a-z0-9 ]", "", t).split()
def hf_ref(perfil):   # audio y texto de referencia del perfil de Voice Studio (se copian a la carpeta del video una sola vez)
    import sqlite3, tempfile
    k = perfil or PERFIL
    if k in _HFREF: return _HFREF[k]
    t = tempfile.mkdtemp()
    for f in ("omnivoice.db", "omnivoice.db-wal", "omnivoice.db-shm"):
        if (VSDATA / f).exists(): shutil.copy(VSDATA / f, t)
    r = sqlite3.connect(os.path.join(t, "omnivoice.db")).execute("select ref_audio_path, ref_text from voice_profiles where name=?", (k,)).fetchone()
    if not r: raise RuntimeError("el perfil «%s» no existe en Voice Studio" % k)
    dst = A / ("hf_ref_%s%s" % (re.sub(r"\W", "_", k), pathlib.Path(r[0]).suffix)); shutil.copy(VSDATA / "voices" / r[0], dst); _HFREF[k] = (str(dst), r[1]); return _HFREF[k]
def hf_tts(tx, perfil):
    global _HFC
    sys.path.insert(0, str(PANEL / "_tmp" / "hf_libs"))
    from gradio_client import Client, handle_file
    if _HFC is None: _HFC = Client("openbmb/VoxCPM-Demo", token=HFTOK, verbose=False) if HFTOK else Client("openbmb/VoxCPM-Demo", verbose=False)
    ref, reftxt = hf_ref(perfil)
    o = _HFC.predict(text_input=tx, control_instruction="", reference_wav_path_input=handle_file(ref), use_prompt_text=True, prompt_text_input=reftxt, cfg_value_input=2.0, do_normalize=False, denoise=False, api_name="/generate")
    tmp = A / "tmp_hf.wav"; subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(o), "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(tmp)], check=True)
    w = wave.open(str(tmp)); sr = w.getframerate(); y = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768; w.close(); tmp.unlink()
    return y, sr
_HF_VEL = []   # caracteres por segundo de las frases ya aceptadas: la API de Hugging Face no tiene semilla, así que se elige entre varias tomas la que mejor encaja con el ritmo del resto
def hf_parte(tx, perfil):   # genera con Hugging Face y VERIFICA con Whisper que la frase salga entera; si su ritmo se aleja >14% de las anteriores prueba otras tomas (hasta 5 en total) y se queda con la más parecida. Devuelve (audio, sr, exacta)
    import difflib
    global _WM
    from faster_whisper import WhisperModel
    mejor = (-1.0, None, None); cand = []
    for n in range(5):
        try: y, sr = hf_tts(tx, perfil)
        except Exception as e: print("  Hugging Face intento %d falló: %s" % (n + 1, repr(e)[:140]), flush=True); continue
        if _WM is None: _WM = WhisperModel("small", device="cpu", compute_type="int8")
        tmp = A / "tmp_hfv.wav"; w = wave.open(str(tmp), "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((np.clip(y, -1, 1) * 32767).astype("<i2").tobytes()); w.close()
        segs, _ = _WM.transcribe(str(tmp), language="es"); oyo = " ".join(s_.text for s_ in segs); tmp.unlink()
        sim = difflib.SequenceMatcher(None, _norm_(tx), _norm_(oyo)).ratio()
        if sim > mejor[0]: mejor = (sim, y, sr)
        if sim >= .93:
            v = len(tx) / max(.3, len(y) / sr); med = sorted(_HF_VEL)[len(_HF_VEL) // 2] if len(_HF_VEL) >= 3 else None; dev = abs(v - med) / med if med else 0
            cand.append((dev, y, sr, v))
            if dev <= .14 or len(cand) >= 3: break
            print("  Hugging Face: ritmo distinto al resto (%.0f%%), pruebo otra toma" % (dev * 100), flush=True); continue
        print("  Hugging Face: frase incompleta (%.2f, se oyó «%s»), repito" % (sim, oyo.strip()[:60]), flush=True)
    if cand:
        b_ = min(cand, key=lambda x: x[0]); _HF_VEL.append(b_[3]); return b_[1], b_[2], True
    return mejor[1], mejor[2], False
INTF = PART / "intentos.json"; INT = json.loads(INTF.read_text(encoding="utf8")) if INTF.exists() else {}
import time as _t
def guarda_parte(f, **kw):   # guarda una parte de la voz; si la carpeta del video no está un momento (renombrada, disco ocupado…) espera y reintenta en vez de perder 6 minutos de voz
    for intento in range(60):
        try: np.savez(f, **kw); return
        except (FileNotFoundError, PermissionError, OSError) as e:
            if intento == 0: print("AVISO: no puedo guardar %s (%s); espero a que vuelva la carpeta del video…" % (pathlib.Path(f).name, type(e).__name__), flush=True)
            _t.sleep(5)
    np.savez(f, **kw)
# REGLA (usuario 2026-11-23: «he generado varias veces otra voz pero sigo escuchando la misma grabación»): rehacer SIEMPRE da OTRA toma. Misma semilla = mismo audio, así que cada «rehacer» (una parte o todas) sube el contador de intentos, que cambia semilla y pasos.
if REHACER and not PARTES: PARTES = set(g["key"] for g in G)
for _k in PARTES: INT[_k] = INT.get(_k, 0) + 1
if PARTES: INTF.write_text(json.dumps(INT), encoding="utf8")
parts = []; nuevas = 0
for i in range(n):
    ns_ = PASOS[INT.get(G[i]["key"], 0) % len(PASOS)]; sd_ = SEED + 7919 * INT.get(G[i]["key"], 0); h = hashlib.md5(json.dumps([txs[i], sd_, ns_, SPEED, (G[i].get("perfil") or PERFIL), "v6final"] + ([MOTOR, voz_local.voz_valida(MOTOR, G[i].get("perfil") or PERFIL)] if LOCAL else [])).encode()).hexdigest()[:10]; f = PART / ("%02d_%s_%s.npz" % (i + 1, G[i]["key"], h))
    if f.exists() and not REHACER:
        z = np.load(f); sr = int(z["sr"])
        if "cutv" in z.files and int(z["cutv"]) == CUTV: parts.append((z["y"], sr)); continue
        if "raw" in z.files:
            y, cortado = corta_final(z["raw"], sr, txs[i]); idx = np.where(np.abs(y) > .002)[0]
            if len(idx): y = y[max(0, idx[0] - int(.03 * sr)): idx[-1] + int(.12 * sr)]
            guarda_parte(f, y=y, sr=sr, raw=z["raw"], cutv=CUTV); parts.append((y, sr)); print("parte %d/%d %s recortada de nuevo (sin pedir voz)" % (i + 1, n, G[i]["key"]), flush=True); continue
    via = "Voice Studio"; y_raw = None
    if LOCAL:   # Piper / Kokoro / edge / clon: la frase sale entera, sin marca «final» que cortar
        y_raw, sr = voz_local.sintetizar(MOTOR, G[i].get("perfil") or PERFIL, txs[i], SPEED, A / "tmp_local", FF); y = y_raw; cortado = True; via = MOTOR.capitalize()
    elif MOTOR == "huggingface":
        y_hf, sr_hf, ok_hf = hf_parte(txs[i], G[i].get("perfil"))
        if y_hf is not None and (ok_hf or not vs_abierto()): y_raw, sr, y, cortado, via = y_hf, sr_hf, y_hf, True, ("Hugging Face" if ok_hf else "Hugging Face (sin verificar)")
    if y_raw is None:   # motor local (o respaldo cuando Hugging Face no entregó la frase entera)
        if not vs_abierto(): sys.exit("Hugging Face no entregó la frase «%s» y Voice Studio está CERRADO: ábrelo y repite." % txs[i])
        y_raw, sr = tts(txs[i], ns_, G[i].get("perfil"), sd_); y, cortado = corta_final(y_raw, sr, txs[i])
    idx = np.where(np.abs(y) > .002)[0]   # en Voice Studio se corta en la palabra «final»; luego solo el silencio digital de los bordes
    if len(idx): y = y[max(0, idx[0] - int(.03 * sr)): idx[-1] + int(.12 * sr)]
    for old in PART.glob("%02d_%s_*.npz" % (i + 1, G[i]["key"])): old.unlink()
    guarda_parte(f, y=y, sr=sr, raw=y_raw, cutv=CUTV); parts.append((y, sr)); nuevas += 1; print("parte %d/%d %s: %.2f s%s  [%s]" % (i + 1, n, G[i]["key"], len(y) / sr, "" if cortado else "  (sin «final» audible)", via), flush=True)
print("partes nuevas: %d, en caché: %d" % (nuevas, n - nuevas), flush=True)
sr0 = parts[0][1]; FIJAR = MODO != "libre" and "--libre" not in sys.argv   # POR DEFECTO el JSON manda: cada parte se coloca en su segundo del guion (el usuario ajusta los tiempos mirando los subtítulos del panel)
S = []; E = []; PLAN_S = [float(g["t"]) for g in G]; avisos = []
if FIJAR:
    ends = [PLAN_S[i] + (len(parts[i][0]) / parts[i][1] - .15) for i in range(n)]; tot = max(max(ends), PLAN_S[-1]) + 1.0; buf = np.zeros(int((tot + 3) * sr0), np.float32); prev_end = -9.0
    for i, (yy, sr) in enumerate(parts):
        yy = yy.copy(); fd = int(.008 * sr); yy[:fd] *= np.linspace(0, 1, fd); yy[-fd:] *= np.linspace(1, 0, fd)
        want = PLAN_S[i] - .03; start = max(want, prev_end + .10); a0 = int(start * sr0)
        if a0 + len(yy) > len(buf): buf = np.concatenate([buf, np.zeros(a0 + len(yy) - len(buf) + sr0, np.float32)])
        buf[a0:a0 + len(yy)] += yy; S.append(start + .03); E.append(start + len(yy) / sr0 - .12); prev_end = start + len(yy) / sr0 - .12
        if start - want > .08: avisos.append({"key": G[i]["key"], "parte": i + 1, "se_pasa_s": round(start - want, 2), "msg": "la parte anterior se pasa %.1f s de su hueco: sube el tiempo de esta o acorta el texto anterior" % (start - want)})
    y = buf[: int((max(E[-1] + 1.0, PLAN_S[-1] + 1.5)) * sr0)]
else:
    out = [np.zeros(int(.3 * sr0), np.float32)]; pos = int(.3 * sr0)
    for i, (yy, sr) in enumerate(parts):
        yy = yy.copy(); fd = int(.008 * sr); yy[:fd] *= np.linspace(0, 1, fd); yy[-fd:] *= np.linspace(1, 0, fd)
        S.append(pos / sr0 + .03); E.append((pos + len(yy)) / sr0 - .12); out.append(yy); pos += len(yy)
        gg = np.zeros(int(pau[i] / 1000 * sr0), np.float32); out.append(gg); pos += len(gg)
    out.append(np.zeros(int(sr0 * 1.0), np.float32)); y = np.concatenate(out)
DUR = len(y) / sr0
vv = np.abs(y) > .02; rms = float(np.sqrt(np.mean(y[vv] ** 2))) if vv.any() else .1; y = np.clip(y * min(.1 / max(rms, 1e-4), .95 / max(float(np.abs(y).max()), 1e-4)), -1, 1)
tmp = A / "tmp.f32"; tmp.write_bytes(y.astype("<f4").tobytes())
subprocess.run([FF, "-y", "-loglevel", "error", "-f", "f32le", "-ar", str(sr0), "-ac", "1", "-i", str(tmp), "-ar", str(SR), "-c:a", "pcm_f32le", str(R / "voz" / "voz_completa.wav")], check=True); tmp.unlink()
shutil.copy(R / "voz" / "voz_completa.wav", A / "voz_completa_f32.wav")
if FIJAR:
    PE = []
    try:
        old = json.loads((A / "tiempos.json").read_text(encoding="utf8"))["tags"]; PE = [old[g["key"]][1] if g["key"] in old else None for g in G]
    except Exception: PE = [None] * n
    tg = {g["key"]: [round(PLAN_S[i], 2), round(PE[i] if PE[i] else E[i], 2)] for i, g in enumerate(G)}   # lo que lee el motor (planificado: el video no cambia)
    (A / "tiempos.json").write_text(json.dumps({"orden": [g["key"] for g in G], "dur": round(DUR, 2), "perfil": PERFIL, "seed": SEED, "speed": SPEED, "metodo": "partes_fijas_en_el_json", "estimado": False, "pausas_ms": {g["key"]: pau[i] for i, g in enumerate(G)}, "tags": tg, "colocado": {g["key"]: [round(S[i], 2), round(E[i], 2)] for i, g in enumerate(G)}}, ensure_ascii=False, indent=1), encoding="utf8")
    (R / "plan.json").write_text(json.dumps([{"k": k + 1, "key": g["key"], "texto": g["texto"], "escena": 1, "t_suceso": PLAN_S[k], "at": round(S[k], 2), "dur": round(E[k] - S[k], 2), "retraso": round(S[k] - PLAN_S[k], 2), "se_pasa": round(max(0.0, E[k] - (PLAN_S[k + 1] if k + 1 < n else E[k])), 2)} for k, g in enumerate(G)], ensure_ascii=False, indent=1), encoding="utf8")
    (A / "avisos.json").write_text(json.dumps(avisos, ensure_ascii=False, indent=1), encoding="utf8"); tags = tg
    for a in avisos: print("AVISO parte %d (%s): %s" % (a["parte"], a["key"], a["msg"]), flush=True)
    print("JSON manda: %d partes colocadas en sus segundos, %d avisos de hueco corto" % (n, len(avisos)), flush=True)
else: tags = escribe(S, E, DUR, False)
for fz in (R / "voz").glob("1_*.wav"):
    try: fz.unlink()
    except Exception: pass
def wv(path, a):
    ww = wave.open(str(path), "wb"); ww.setnchannels(1); ww.setsampwidth(2); ww.setframerate(sr0); ww.writeframes((np.clip(a, -1, 1) * 32767).astype("<i2").tobytes()); ww.close()
for k in range(n): wv(R / "voz" / ("1_%02d.wav" % (k + 1)), y[int(max(0, S[k] - .03) * sr0):int((E[k] + .12) * sr0)])
(R / "voz" / "textos.json").write_text(json.dumps({"1_%02d.wav" % k: g["texto"] for k, g in enumerate(G, 1)}, ensure_ascii=False), encoding="utf8")
(R / "voz" / "completa.json").write_text(json.dumps({"frases": list(range(1, n + 1)), "dur": round(DUR, 2), "metodo": "partes_con_final"}), encoding="utf8")
print("voz por partes %.1f s" % DUR, {k: v[0] for k, v in tags.items()}, flush=True)
