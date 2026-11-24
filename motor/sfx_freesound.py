"""EFECTOS DE SONIDO para la unión (motor del DevIAs Panel). Baja de Freesound SOLO efectos con licencia CC0 (sin atribución) y los deja en CARPETA/sfx/<nombre>.wav (24 kHz mono), que es lo que lee motor/mezcla.py.
Lo llama el pipeline (motor/video.py → Proyecto.sfx) justo antes de mezclar. NUNCA frena la unión: si falta la clave, un sonido o hay un error de red, avisa y la unión sigue (con lo que haya).
Uso:  python sfx_freesound.py CARPETA [catalogo.json]
  · Sonidos que hacen falta = los nombres de sfx_cues.json ({cue: [sonido, vol, sep]} o {cue: [[sonido, vol, desfase], …]}) y de sfx_plan.json ([clave, desfase, sonido, vol]).
  · Catálogo del plugin (base/sfx/catalogo.json): {sonido: {"q": "búsqueda en inglés", "dur": [min, max]}}. Un sonido que no está en el catálogo se omite.
  · Clave API: variable FREESOUND_KEY (el panel la toma del ajuste «Clave API de Freesound» del plugin) o, si no, el archivo freesound.key de la carpeta del video o de la carpeta del DevIAs Panel.
  · Caché compartida: devpanel/sfx_cache/<sonido>.wav (cada efecto se baja UNA vez para todos los videos). Créditos: CARPETA/sfx/creditos.json."""
import os, sys, json, pathlib, shutil, subprocess, urllib.parse, urllib.request, urllib.error
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe(); R = pathlib.Path(sys.argv[1]).resolve(); PANEL = pathlib.Path(__file__).resolve().parent.parent; CACHE = PANEL / "sfx_cache"
CAT = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")) if len(sys.argv) > 2 and pathlib.Path(sys.argv[2]).is_file() else {}
def jl(p, d):
    try: return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception: return d
def necesarios():
    n = []
    for v in (jl(R / "sfx_cues.json", {}) or {}).values():
        if v and isinstance(v[0], list): n += [x[0] for x in v if x]
        elif v: n.append(v[0])
    n += [x[2] for x in (jl(R / "sfx_plan.json", []) or []) if len(x) > 2]
    return list(dict.fromkeys(n))
def clave():
    k = os.environ.get("FREESOUND_KEY", "").strip()
    for f in (R / "freesound.key", PANEL / "freesound.key"):
        if not k and f.is_file(): k = f.read_text(encoding="utf-8").strip()
    return k
def api(url): return json.loads(urllib.request.urlopen(url, timeout=30).read())
def baja(nombre, K):
    c = CAT.get(nombre)
    if not c: print("  · «%s»: no está en el catálogo de efectos del plugin (se omite)" % nombre, flush=True); return None
    d0, d1 = (c.get("dur") or [.1, 3])[:2]; f = urllib.parse.quote('license:"Creative Commons 0" duration:[%s TO %s]' % (d0, d1))
    r = {"results": []}
    for q in (c["q"] if isinstance(c["q"], list) else [c["q"]]):   # varias búsquedas alternativas: se prueba cada una hasta que haya resultado CC0
        r = api("https://freesound.org/apiv2/search/text/?query=%s&filter=%s&sort=rating_desc&fields=id,name,duration,license,previews,username&page_size=5&token=%s" % (urllib.parse.quote(q), f, K))
        if r.get("results"): break
    for s in r.get("results", []):
        if "publicdomain/zero" not in s.get("license", ""): continue
        CACHE.mkdir(exist_ok=True); mp3 = CACHE / (nombre + ".mp3"); urllib.request.urlretrieve(s["previews"]["preview-hq-mp3"], mp3)
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(mp3), "-ac", "1", "-ar", "24000", "-t", str(d1), "-af", "afade=t=out:st=%.2f:d=0.1" % max(0, min(s["duration"], d1) - .1), str(CACHE / (nombre + ".wav"))], check=True); mp3.unlink()
        return {"sonido": nombre, "id": s["id"], "nombre": s["name"], "autor": s["username"], "dur": round(s["duration"], 2), "licencia": s["license"]}
    print("  · «%s»: sin resultados CC0 para %s" % (nombre, c["q"]), flush=True); return None
def main():
    N = necesarios()
    if not N: print("efectos: este video no pide ninguno (sin sfx_cues.json / sfx_plan.json).", flush=True); return
    (R / "sfx").mkdir(exist_ok=True); cred = jl(R / "sfx" / "creditos.json", []); K = clave(); listos = []; faltan = []; sin_clave = False; invalida = False
    for nombre in N:
        out = R / "sfx" / (nombre + ".wav")
        if out.exists(): listos.append(nombre); continue
        if (CACHE / (nombre + ".wav")).exists(): shutil.copy(CACHE / (nombre + ".wav"), out); listos.append(nombre); continue
        if invalida: faltan.append(nombre); continue
        if not K: sin_clave = True; faltan.append(nombre); continue
        try:
            c = baja(nombre, K)
            if c: shutil.copy(CACHE / (nombre + ".wav"), out); cred = [x for x in cred if x.get("sonido") != nombre] + [c]; listos.append(nombre); print("  ✓ %s → «%s» (%s s) de %s" % (nombre, c["nombre"].encode("ascii", "ignore").decode(), c["dur"], c["autor"]), flush=True)
            else: faltan.append(nombre)
        except urllib.error.HTTPError as e:
            faltan.append(nombre); print("  ✗ %s: Freesound respondió %s%s" % (nombre, e.code, " (clave inválida: revisa «Clave API de Freesound» en la configuración del plugin)" if e.code in (401, 403) else ""), flush=True)
            if e.code in (401, 403): invalida = True
        except Exception as e: faltan.append(nombre); print("  ✗ %s: %s" % (nombre, str(e)[:120]), flush=True)
    (R / "sfx" / "creditos.json").write_text(json.dumps(cred, ensure_ascii=False, indent=1), encoding="utf-8")
    if sin_clave: print("AVISO: falta la «Clave API de Freesound» (Plugins → Juegos de gelatinas → Configurar → Efectos de sonido): el video se une SIN estos efectos: %s" % ", ".join(faltan), flush=True)
    print("efectos: %d listos, %d sin descargar%s." % (len(listos), len(faltan), (" (" + ", ".join(faltan) + ")") if faltan else ""), flush=True)
try: main()
except Exception as e: print("AVISO: no se pudieron preparar los efectos (%s); la unión sigue sin ellos." % str(e)[:160], flush=True)
