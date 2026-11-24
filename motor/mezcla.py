"""MEZCLA DEL DEVPANEL (motor ÚNICO para todos los plugins): corta el video mudo [desde, hasta] de una escena y le pone la voz, los efectos y la música -> salida/escena_NN<sufijo>.mp4
Uso: python mezcla.py CARPETA N [SUFIJO]
Lee del proyecto (los datos los pone el plugin / Claude; el motor no sabe nada de ningún formato):
  proyecto.json            seed (video mudo salida_mudo/s<seed>_completo.mp4 y su .json con «cues» y «dur»)
  escenas.json             [{n, titulo, desde, hasta}]  (una escena cuyo título empieza por «Pausa» lleva los toques de like y suscripción)
  voz/voz_completa.wav     UN solo audio de todo el video (la ventana de la escena se recorta, sin trocear frases)  ·  plan.json (avisos de huecos)
  music/bgm.wav + music/creditos.json (ganancia)   música en bucle con ducking bajo la voz
  sfx/<nombre>.wav         efectos ya descargados (CC0 de Freesound); sfx_plan.json = efectos por MOMENTO del guion [[clave, desfase_s, sonido, volumen], …];
                           sfx_cues.json = efectos por CUE del juego {cue: [sonido, volumen, separación_mínima_s]} o {cue: [[sonido, volumen, desfase], …]}; sfx/ambiente.wav (o viento.wav) = ambiente en bucle.
Mezcla: música ×0,34 con ducking, ambiente ×0,12, efectos ×0,42, voz ×1,0 -> tanh suave -> loudnorm -14 LUFS."""
import os, sys, json, pathlib, subprocess, wave
os.environ["TEMP"] = os.environ["TMP"] = os.environ.get("DEVPANEL_TMP") or os.environ.get("TEMP") or "."
import numpy as np, imageio_ffmpeg

# --- RÁPIDO: np.convolve con núcleo plano (media móvil) era O(N*K): se hace con suma acumulada (misma salida) ---
_np_conv_orig = np.convolve
def _conv_rapida(a, v, mode="full"):
    v = np.asarray(v)
    if mode == "same" and v.ndim == 1 and len(v) > 64 and np.ptp(v) == 0 and np.ndim(a) == 1:
        a = np.asarray(a, dtype=np.float64); k = len(v); n = len(a); C = np.concatenate([[0.0], np.cumsum(a)]); i = np.arange(n)
        hi = np.clip(i + (k - 1) // 2, 0, n - 1); lo = np.clip(i + (k - 1) // 2 - k + 1, 0, n)
        return (C[hi + 1] - C[lo]) * v[0]
    return _np_conv_orig(a, v, mode)
np.convolve = _conv_rapida
R = pathlib.Path(sys.argv[1]).resolve(); NE = int(sys.argv[2]); SUF = sys.argv[3] if len(sys.argv) > 3 else ""
FF = imageio_ffmpeg.get_ffmpeg_exe(); SR = 44100
def jl(p, d=None):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return d
META = jl(R / "proyecto.json", {}); SEED = int(META.get("seed", 1)); TAG = "_completo"
mudo = R / "salida_mudo" / ("s%d%s.mp4" % (SEED, TAG)); meta = jl(R / "salida_mudo" / ("s%d%s.json" % (SEED, TAG)), {"cues": [], "dur": 0})
ESC = jl(R / "escenas.json", []); esc = next((e for e in ESC if e["n"] == NE), None)
if not esc: sys.exit("No existe la escena %d en escenas.json" % NE)
d0, d1 = esc["desde"], min(esc["hasta"], meta.get("dur") or esc["hasta"]); dur = d1 - d0; N = int((dur + .3) * SR)
def load(path):
    raw = subprocess.run([FF, "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()
def put(buf, x, t, g=1.0):
    i = int(t * SR)
    if i < 0 or i >= len(buf): return
    x = x[:max(0, len(buf) - i)]; buf[i:i + len(x)] += x * g
# ---- voz: la ventana de esta escena del audio completo ----
voice = np.zeros(N, dtype=np.float32); sobra = 0.0; VW = R / "voz" / "voz_completa.wav"
if VW.exists():
    x = load(VW)[int(d0 * SR):int(d1 * SR)]; put(voice, x, 0.0)
    for L in jl(R / "plan.json", []):
        if L.get("escena") == NE and L.get("se_pasa", 0) > sobra: sobra = L["se_pasa"]
else: print("AVISO: no hay voz/voz_completa.wav; la escena sale sin voz", flush=True)
# ---- efectos ----
sfx = np.zeros(N, dtype=np.float32); S = {}; last = {}
def snd(name):
    if name not in S: f = R / "sfx" / (name + ".wav"); S[name] = load(f) if f.exists() else np.zeros(1, dtype=np.float32)
    return S[name]
def gate(k, t, gap):
    if t - last.get(k, -9) < gap: return False
    last[k] = t; return True
if str(esc.get("titulo", "")).lower().startswith("pausa"):   # toques del cursor: like a +1,75 s y suscribirse a +3,95 s desde que empieza la pausa
    for tp in (esc["desde"] + 1.75, esc["desde"] + 3.95):
        if d0 <= tp < d1: put(sfx, snd("tap"), tp - d0, .6)
GU = jl(R / "guion" / "1.json", []); gt = {o.get("key"): o.get("t") for o in GU}
for k_, off_, nm_, vol_ in jl(R / "sfx_plan.json", []):
    if gt.get(k_) is None: continue
    tt_ = gt[k_] + off_
    if d0 <= tt_ < d1: put(sfx, snd(nm_), tt_ - d0, vol_)
CUES = jl(R / "sfx_cues.json", {})
for c in meta.get("cues", []):
    k, t = c["k"], c["v"]
    if k not in CUES: continue
    spec = CUES[k]; spec = spec if isinstance(spec[0], list) else [[spec[0], spec[1], 0.0]]; gap = float(CUES[k][2]) if not isinstance(CUES[k][0], list) and len(CUES[k]) > 2 else 0.0
    if gap and not gate(k, t, gap): continue
    for nm, vol, off in spec:
        tt = t + float(off)
        if d0 <= tt < d1: put(sfx, snd(nm), tt - d0, vol)
# ---- música (bucle con fundido de 0,6 s) y ambiente ----
def gbgm():
    c = jl(R / "music" / "creditos.json", {}); return float(c.get("ganancia", 1) or 1)
def bgm_loop(n):
    f = R / "music" / "bgm.wav"
    if not f.exists(): return np.zeros(n, dtype=np.float32)
    x = load(f); x = x / (np.max(np.abs(x)) + 1e-9) * .9 * gbgm(); cf = int(.6 * SR); out = x.copy()
    while len(out) < n: out = np.concatenate([out[:-cf], out[-cf:] * np.linspace(1, 0, cf) + x[:cf] * np.linspace(0, 1, cf), x[cf:]])
    return out[:n]
wf = next((R / "sfx" / (nm + ".wav") for nm in ("ambiente", "viento") if (R / "sfx" / (nm + ".wav")).exists()), None); wnd = load(wf) if wf else np.zeros(SR, dtype=np.float32)
wnd = np.tile(wnd, int((N + int(d0 * SR)) / max(1, len(wnd))) + 2)[int(d0 * SR):int(d0 * SR) + N]; wnd = wnd / (np.max(np.abs(wnd)) + 1e-9) * (1.0 if wf else 0.0)
mus = bgm_loop(N + int(d0 * SR))[int(d0 * SR):int(d0 * SR) + N]   # la música sigue donde iba: las escenas encajan sin salto
tot = meta.get("dur") or esc["hasta"]; _tg = np.arange(N) / SR + d0; mus = mus * np.clip(_tg / 1.0, 0, 1) * np.clip((tot - _tg) / 1.6, 0, 1)   # entrada y salida suaves: el video hace loop sin golpe
env = np.convolve(np.abs(voice), np.ones(int(.12 * SR)) / int(.12 * SR), "same"); env = np.clip(env / (env.max() + 1e-9) * 2.2, 0, 1); duck = 1 - .6 * np.convolve(env, np.ones(int(.25 * SR)) / int(.25 * SR), "same")
fade = np.ones(N, dtype=np.float32); fo = int(.05 * SR); i1 = int(dur * SR); fade[:fo] = np.linspace(0, 1, fo); fade[i1 - fo:i1] = np.linspace(1, 0, fo); fade[i1:] = 0
mix = (mus * .34 * duck + wnd * .12 * duck + sfx * .42 * (.55 + .45 * duck) + voice * 1.0) * fade; mix = np.tanh(mix * 1.1) / np.tanh(1.1); mix = mix / (np.max(np.abs(mix)) + 1e-9) * .93
db = lambda x: 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-9)
print("escena %d [%.1f-%.1f s] niveles dB: voz %.1f · efectos %.1f · música %.1f%s" % (NE, d0, d1, db(voice * fade), db(sfx * .42 * (.55 + .45 * duck) * fade), db(mus * .34 * duck * fade), ("  ¡AVISO: la voz se pasa %.2f s del final de la escena!" % sobra) if sobra > .05 else ""), flush=True)
wav = R / "salida" / ("_e%d.wav" % NE); wav.parent.mkdir(exist_ok=True)
with wave.open(str(wav), "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
out = R / "salida" / ("escena_%02d%s.mp4" % (NE, SUF))
subprocess.run([FF, "-y", "-loglevel", "error", "-ss", "%.3f" % d0, "-t", "%.3f" % dur, "-i", str(mudo), "-i", str(wav), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-tune", "animation", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-t", "%.3f" % dur, str(out)], check=True)
print("LISTO", out)
