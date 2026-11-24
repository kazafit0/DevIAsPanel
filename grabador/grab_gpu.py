"""GRABADOR GPU: el navegador codifica H.264 con la tarjeta (WebCodecs VideoEncoder / NVENC) dentro de la pagina; sin screenshot ni x264 por CPU.
Uso: python grab_gpu.py CARPETA SEED [--tag _gpu] [--workers 3] [--desde 0] [--hasta 0] [--fps 30] [--mbps 25] [--sw]
Salida: CARPETA/salida_mudo/s{SEED}{TAG}.mp4"""
import os, sys, json, time, socket, pathlib, argparse, subprocess, shutil, base64
os.environ['TEMP'] = os.environ['TMP'] = os.environ.get("DEVPANEL_TMP") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_tmp")
import imageio_ffmpeg
FF = imageio_ffmpeg.get_ffmpeg_exe(); VW = int(os.environ.get("GRAB_W", 1080)); VH = int(os.environ.get("GRAB_H", 1920))
ARGS = ["--use-angle=d3d11", "--ignore-gpu-blocklist", "--enable-gpu-rasterization", "--enable-zero-copy", "--force-device-scale-factor=1",
        "--enable-features=PlatformHEVCEncoderSupport,MediaFoundationD3D11VideoCapture", "--disable-extensions", "--js-flags=--max-old-space-size=900"]
JS = """
async (cfg) => {
  const W=cfg.W,H=cfg.H, c=document.createElement('canvas'); c.width=W; c.height=H; const x=c.getContext('2d',{alpha:false});
  const gl=document.getElementById('gl'), cv=document.getElementById('cv'); window.__chunks=[]; window.__enc_err=null; window.__flush=async()=>{const l=window.__chunks.splice(0);if(!l.length)return;const t=new Uint8Array(l.reduce((q,u)=>q+u.length,0));let o=0;for(const u of l){t.set(u,o);o+=u.length}const bl=new Blob([t]);const b=await new Promise(r=>{const f=new FileReader();f.onload=()=>r(f.result.split(',')[1]);f.readAsDataURL(bl)});await window.__sink(b)};
  const enc=new VideoEncoder({output:(ch)=>{const b=new Uint8Array(ch.byteLength); ch.copyTo(b); window.__chunks.push(b);}, error:e=>{window.__enc_err=String(e);}});
  const conf={codec:'avc1.640034', width:W, height:H, bitrate:cfg.bps, framerate:cfg.fps, avc:{format:'annexb'}, latencyMode:'realtime', bitrateMode:'constant', hardwareAcceleration:(cfg.hw?'prefer-hardware':'prefer-software')};
  const sup=await VideoEncoder.isConfigSupported(conf); if(!sup.supported) return {err:'config no soportada'}; enc.configure(conf);
  if(cfg.f0>0) __adv(cfg.f0*30/cfg.fps); const dt=1/cfg.fps; const T={draw:0,copy:0,enc:0}; const t00=performance.now();
  for(let n=0;n<cfg.f1-cfg.f0;n++){
    let a=performance.now(); __frame(dt); let b=performance.now(); if(gl) x.drawImage(gl,0,0); if(cv) x.drawImage(cv,0,0);
    const vf=new VideoFrame(c,{timestamp:Math.round((cfg.f0+n)*1e6/cfg.fps)}); let d=performance.now();
    enc.encode(vf,{keyFrame:n%60===0}); vf.close(); let e=performance.now();
    T.draw+=b-a; T.copy+=d-b; T.enc+=e-d;
    while(enc.encodeQueueSize>6) await new Promise(r=>setTimeout(r,1));
    if(n%30===29) await window.__flush();
    if(n%10===0) window.__n=n+1;
  }
  await enc.flush(); await window.__flush(); return {T, total:performance.now()-t00, err:window.__enc_err, n:window.__chunks.length};
}
"""
def trabajador(i, port, seed, f0, f1, fps, bps, sw, tmp):
    from playwright.sync_api import sync_playwright
    out = pathlib.Path(tmp) / ("p%d.h264" % i)
    with sync_playwright() as p:
        br = p.chromium.launch(args=ARGS); pg = br.new_page(viewport={"width": VW, "height": VH}, device_scale_factor=1)
        fh = open(out, "wb"); pg.expose_function("__sink", lambda b: fh.write(base64.b64decode(b)) and None)
        pg.on("pageerror", lambda e: print("ERROR pagina:", e, flush=True))
        pg.goto("http://localhost:%d/index.html?seed=%d&cta=99,99" % (port, seed)); pg.wait_for_function("window.__ready===true", timeout=90000); pg.evaluate("document.fonts.ready")
        r = pg.evaluate(JS, {"W": VW, "H": VH, "fps": fps, "bps": int(bps), "f0": f0, "f1": f1, "sw": sw, "hw": os.environ.get("GRAB_HW") == "1"})
        if r.get("err"): raise RuntimeError("WebCodecs: %s" % r["err"])
        fh.close(); cues = pg.evaluate("window.__cues"); log = pg.evaluate("window.__log"); br.close()
    return i, str(out), cues, log, r

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("carpeta"); ap.add_argument("seed", type=int); ap.add_argument("--tag", default="_gpu"); ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--desde", type=float, default=0); ap.add_argument("--hasta", type=float, default=0); ap.add_argument("--fps", type=int, default=30); ap.add_argument("--mbps", type=float, default=25); ap.add_argument("--sw", action="store_true")
    a = ap.parse_args(); root = pathlib.Path(a.carpeta).resolve(); outdir = root / "salida_mudo"; outdir.mkdir(exist_ok=True)
    s = socket.socket(); s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]; s.close()
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--directory", str(root)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL); time.sleep(1.5)
    tmp = pathlib.Path(os.environ.get("DEVPANEL_TMP") or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "_tmp")) / ("gpu_%d_%d" % (a.seed, int(time.time()))); tmp.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            br = p.chromium.launch(args=ARGS); pg = br.new_page(viewport={"width": VW, "height": VH})
            pg.goto("http://localhost:%d/index.html?seed=%d&cta=99,99" % (port, a.seed)); pg.wait_for_function("window.__ready===true", timeout=90000)
            tv = pg.evaluate("(async()=>{const r=await __sim(%d,400);return r.V??null})()" % a.seed); br.close()
        total = float(tv if tv is not None else a.hasta); t1 = a.hasta if a.hasta > 0 else total; t1 = min(t1, total)
        F0 = int(round(a.desde * a.fps)); F1 = int(round(t1 * a.fps)); N = max(1, min(a.workers, F1 - F0)); tot_f = F1 - F0
        cortes = [F0 + round(tot_f * k / N) for k in range(N + 1)]
        print("Partida %.1f s; grabo %.1f-%.1f s con %d trabajadores (GPU)" % (total, F0 / a.fps, F1 / a.fps, N), flush=True); t0 = time.time()
        from concurrent.futures import ProcessPoolExecutor
        with ProcessPoolExecutor(max_workers=N) as ex:
            futs = [ex.submit(trabajador, i, port, a.seed, cortes[i], cortes[i + 1], a.fps, a.mbps * 1e6, a.sw, str(tmp)) for i in range(N)]
            res = sorted((f.result() for f in futs), key=lambda r: r[0])
        for r in res: print("  trozo %d: %s" % (r[0], json.dumps(r[4])), flush=True)
        out = outdir / ("s%d%s.mp4" % (a.seed, a.tag)); raw = tmp / "todo.h264"
        with open(raw, "wb") as fo:
            for r in res: fo.write(open(r[1], "rb").read())
        tmp_mp4 = outdir / ("_tmp_s%d%s.mp4" % (a.seed, a.tag))
        subprocess.run([FF, "-y", "-loglevel", "error", "-f", "h264", "-i", str(raw), "-c", "copy", "-bsf:v", "setts=ts=N:time_base=1/%d" % a.fps, "-movflags", "+faststart", str(tmp_mp4)], check=True)
        subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(tmp_mp4), "-c", "copy", "-movflags", "+faststart", str(out)], check=True); tmp_mp4.unlink()   # 2.º paso (sin recodificar): el mp4 desde H.264 crudo trae la DURACIÓN de la cabecera mal (el reproductor marcaba 40:02 en un video de 4:01); al copiarlo de nuevo queda exacta
        out.with_suffix(".json").write_text(json.dumps({"cues": res[-1][2], "log": res[-1][3], "dur": F1 / a.fps, "seed": a.seed}, ensure_ascii=False, indent=1), encoding="utf-8")
        print("LISTO", out, "%.1fs en %.0f s (%.2fx tiempo real)" % (F1 / a.fps, time.time() - t0, (time.time() - t0) / (tot_f / a.fps)), flush=True)
    finally:
        srv.terminate(); shutil.rmtree(tmp, ignore_errors=True)
if __name__ == "__main__":
    main()
