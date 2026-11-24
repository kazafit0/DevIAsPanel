"""GRABADOR PARALELO de shorts (mudo, 1080x1920, 30 fps): parte el video en N trozos y los graba a la vez, un navegador por trozo; luego los une.
El juego es determinista, asi que cada navegador salta (sin dibujar) hasta su trozo y el resultado es IDENTICO a grabar de corrido, pero ~N veces mas rapido.
Fotogramas en JPEG de alta calidad (mas rapido que PNG). Uso:
  python grab_paralelo.py CARPETA SEED [--tag _full] [--workers 6] [--desde 0] [--hasta 0] [--fps 30] [--q 94]
  (--hasta 0 = hasta el final de la partida)  ->  CARPETA/salida_mudo/s{SEED}{TAG}.mp4 + .json (cues y log, igual que grab_short.py)"""
import os, sys, json, time, socket, pathlib, argparse, subprocess, shutil
os.environ['TEMP'] = os.environ['TMP'] = os.environ.get("DEVPANEL_TMP") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_tmp")
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe()
ARGS = ["--use-angle=d3d11", "--ignore-gpu-blocklist", "--enable-gpu-rasterization", "--force-device-scale-factor=1", "--disable-dev-shm-usage", "--disable-extensions", "--js-flags=--max-old-space-size=700"]

def trabajador(i, port, seed, f0, f1, fps, q, tmp):
    """Graba los fotogramas [f0, f1) del juego -> tmp/p{i}.mp4. Devuelve (i, ruta, cues, log)."""
    from playwright.sync_api import sync_playwright
    out = pathlib.Path(tmp) / ("p%d.mp4" % i); prog = pathlib.Path(tmp) / ("p%d.n" % i)
    enc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-i", "-", "-vf", "scale=1080:1920:flags=lanczos:out_color_matrix=bt709:out_range=tv,format=yuv420p",
                            "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-tune", "animation", "-threads", "2", str(out)], stdin=subprocess.PIPE)
    with sync_playwright() as p:
        br = p.chromium.launch(args=ARGS); pg = br.new_page(viewport={"width": int(os.environ.get("GRAB_W", 1080)), "height": int(os.environ.get("GRAB_H", 1920))}, device_scale_factor=1)
        pg.on("pageerror", lambda e: print("ERROR pagina:", e, flush=True))
        pg.goto("http://localhost:%d/index.html?seed=%d&cta=99,99" % (port, seed)); pg.wait_for_function("window.__ready===true", timeout=90000); pg.evaluate("document.fonts.ready")
        if f0 > 0: pg.evaluate("__adv(%d)" % f0)   # salta sin dibujar hasta el inicio del trozo (misma partida)
        dt = 1 / fps
        for n in range(f1 - f0):
            pg.evaluate("__frame(%f)" % dt); enc.stdin.write(pg.screenshot(type="jpeg", quality=q))
            if n % 10 == 0: prog.write_text(str(n + 1))
        prog.write_text(str(f1 - f0)); cues = pg.evaluate("window.__cues"); log = pg.evaluate("window.__log"); br.close()
    enc.stdin.close(); enc.wait()
    return i, str(out), cues, log

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("carpeta"); ap.add_argument("seed", type=int); ap.add_argument("--tag", default=""); ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--desde", type=float, default=0); ap.add_argument("--hasta", type=float, default=0); ap.add_argument("--fps", type=int, default=30); ap.add_argument("--q", type=int, default=94)
    a = ap.parse_args(); root = pathlib.Path(a.carpeta).resolve(); outdir = root / "salida_mudo"; outdir.mkdir(exist_ok=True)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--directory", str(root)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1.5)
    tmp = pathlib.Path(os.environ.get("DEVPANEL_TMP") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_tmp")) / ("par_%d_%d" % (a.seed, int(time.time()))); tmp.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:   # duracion total de la partida (simulacion, sin dibujar)
            br = p.chromium.launch(args=ARGS); pg = br.new_page(viewport={"width": int(os.environ.get("GRAB_W", 1080)), "height": int(os.environ.get("GRAB_H", 1920))})
            pg.goto("http://localhost:%d/index.html?seed=%d&cta=99,99" % (port, a.seed)); pg.wait_for_function("window.__ready===true", timeout=90000)
            tv = pg.evaluate("(async()=>{const r=await __sim(%d,400);return r.V??null})()" % a.seed); br.close()
        if tv is None and a.hasta <= 0:   # juego antiguo sin duracion en __sim: se graba de corrido con el grabador clasico
            print("Este juego no informa su duracion: uso el grabador clasico (mas lento).", flush=True)
            cta = "11,17"
            try: cta = (root / "cta.txt").read_text().strip() or cta
            except Exception: pass
            r_ = subprocess.run([sys.executable, "-u", str(root / "tools" / "grab_short.py"), str(a.seed), "--cta", cta, "--port", str(port), "--tag", a.tag], cwd=str(root)); sys.exit(r_.returncode)
        total = float(tv if tv is not None else a.hasta)
        t1 = a.hasta if a.hasta > 0 else total; t1 = min(t1, total); F0 = int(round(a.desde * a.fps)); F1 = int(round(t1 * a.fps)); N = max(1, min(a.workers, F1 - F0)); tot_f = F1 - F0
        cortes = [F0 + round(tot_f * k / N) for k in range(N + 1)]
        print("Partida de %.1f s; grabo %.1f-%.1f s en %d trozos a la vez" % (total, F0 / a.fps, F1 / a.fps, N), flush=True); t0 = time.time()
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=N) as ex:
            futs = [ex.submit(trabajador, i, port, a.seed, cortes[i], cortes[i + 1], a.fps, a.q, str(tmp)) for i in range(N)]; ult = -1
            while not all(f.done() for f in futs):
                hechos = 0
                for i in range(N):
                    try: hechos += int((tmp / ("p%d.n" % i)).read_text() or 0)
                    except Exception: pass
                sec = hechos / a.fps
                if int(sec) != ult: ult = int(sec); print("  %5.1fs (%ds)" % (sec, time.time() - t0), flush=True)
                time.sleep(2)
            res = sorted(f.result() for f in futs)
        lista = tmp / "lista.txt"; lista.write_text("".join("file '%s'\n" % r[1].replace("\\", "/") for r in res), encoding="utf-8")
        out = outdir / ("s%d%s.mp4" % (a.seed, a.tag)); subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(out)], check=True)
        cues, log = res[-1][2], res[-1][3]   # el ultimo trozo simulo la partida entera: trae TODOS los sucesos
        out.with_suffix(".json").write_text(json.dumps({"cues": cues, "log": log, "dur": F1 / a.fps, "seed": a.seed}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("LISTO", out, "%.1fs en %.0f s de trabajo (%.1fx tiempo real)" % (F1 / a.fps, time.time() - t0, (time.time() - t0) / (tot_f / a.fps)), flush=True)
    finally:
        srv.terminate(); shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
