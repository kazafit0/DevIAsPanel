/* PANEL ADMINISTRATIVO · módulo nuevo (2026-11-20)
   Pedido → Ideas con «cómo sucedería» → «Díselo a Claude» (modal formato/segundos) → video EN ESPERA con CEREBRO 3D de avance
   + campana de avisos + pestaña Actividad (lo que hace Claude y el código que genera) + borrador con voz sincronizada. */
(function () {
  const ETAPAS = ['Entender el pedido', 'Guion y frases', 'Mapa y países', 'Personajes y escenas', 'Gráficos', 'Voz y tiempos', 'Verificación', 'Borrador listo'];
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v) } catch (e) { return d } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)) } catch (e) { } }
  };
  S.act = { log: [], codigo: { carpeta: null, archivos: [] } }; S.glog = []; S.bellOpen = false; S.visto = store.get('act_visto', Date.now() / 1000 - 3600); S.modal = null; S.codeView = null; S.brain = { etapa: 1, hecho: false, error: false, pct: 0, msg: '' };

  /* ---------- helpers de estado ---------- */
  const pedVideo = idea => [...S.ped].reverse().find(x => x.tipo === 'video' && x.idea === idea);
  const esEspera = p => p && (p.estado === 'espera' || (p.estado === 'en_proceso' && !p.existe_mudo && pedVideo(p.idea) && pedVideo(p.idea).estado !== 'hecho'));
  
  /* ---------- navegación: pestaña Actividad ---------- */
  TIT.actividad = ['Actividad', 'Lo que Claude va haciendo y el código que genera'];
  (function () {
    const nav = document.querySelector('.nav[data-p="pedidos"]'); if (!nav || document.querySelector('.nav[data-p="actividad"]')) return;
    const b = document.createElement('button'); b.className = 'nav'; b.dataset.act = 'nav'; b.dataset.p = 'actividad'; b.innerHTML = '<i class="ti ti-terminal-2"></i><span>Actividad</span>'; nav.before(b);
  })();

  /* ---------- IDEAS: con «cómo sucedería» y referencia ---------- */
  function ideaCard(i) {
    const como = (i.como || []).map(c => '<li>' + esc(c) + '</li>').join('');
    return `<div class="idea"><div class="x"><b>${esc(i.titulo)}</b><small>${esc(i.desc || '')}</small>${como ? `<details style="margin-top:6px"><summary style="cursor:pointer;color:var(--acc);font-size:13px">Cómo sucedería</summary><ol style="margin:6px 0 0;padding-left:20px;font-size:13px;color:var(--tx2)">${como}</ol>${i.ref ? `<div class="note"><b>Referencia:</b> ${esc(i.ref)}</div>` : ''}</details>` : ''}</div>${chip(i.enfoque || i.modo || 'idea', '')}<button class="pri mini" data-act="diselo" data-id="${esc(i.id)}"><i class="ti ti-send"></i> Díselo a Claude</button></div>`;
  }
  function rIdeas2() {
    const l = S.cat.filter(i => i.estado === 'idea' && i.formato === S.fmt);
    const grupos = {}; l.forEach(i => { const k = i.pedido || 'otras'; (grupos[k] = grupos[k] || []).push(i) });
    const orden = Object.keys(grupos).sort((a, b) => Math.max(...grupos[b].map(i => i.lote || 0)) - Math.max(...grupos[a].map(i => i.lote || 0)));
    const cuerpo = orden.map(k => {
      const g = grupos[k], tx = g[0].pedido_texto;
      return `<div class="panel" style="margin:0 0 14px;border-radius:0;border-left:0;border-right:0"><div style="padding:10px 16px;background:var(--side);font-size:13px">${tx ? '<b>Basado en tu pedido:</b> «' + esc(tx) + '»' : '<b>Ideas sueltas</b>'} <span class="muted">· ${g.length} ideas</span></div>${g.map(ideaCard).join('')}</div>`;
    }).join('');
    return `<div class="panel"><header><h2>Ideas</h2><div class="r"><div class="seg"><button class="${S.fmt === 'short' ? 'on' : ''}" data-act="fmt" data-v="short">Corto</button><button class="${S.fmt === 'largo' ? 'on' : ''}" data-act="fmt" data-v="largo">Largo</button></div><button class="mini" data-act="irPedidos"><i class="ti ti-message-plus"></i> Nuevo pedido</button><button class="pri mini" data-act="dame10">Dame 100 ideas más</button><button class="mini" data-act="borrar">Borrar y empezar de nuevo</button></div></header>${cuerpo || '<div class="empty">No hay ideas sin empezar en este formato. Escribe un pedido (te devuelvo ideas) o pulsa «Dame 100 ideas más».</div>'}</div>`;
  }
  VIEWS.ideas = rIdeas2;

  /* ---------- PEDIDOS: el pedido devuelve ideas ---------- */
  const rPedOrig = VIEWS.pedidos;
  VIEWS.pedidos = function () {
    const html = rPedOrig();
    return html.replace('Enviar pedido', 'Buscar ideas para mi pedido').replace('Pedirle algo a Claude', 'Tu pedido').replace('Describe el video que quieres', 'Cuéntame qué video quieres. Primero te doy ideas de cómo podría ser; tú eliges y se las pasas a Claude.');
  };

  /* ---------- MODAL «Díselo a Claude» ---------- */
  const SEGS = { short: [30, 45, 60, 80, 105, 120], largo: [210, 240, 300] };
  function modalHtml() {
    const m = S.modal; if (!m) return ''; const it = S.cat.find(x => x.id === m.id); if (!it) return '';
    const fs = m.formato, ss = SEGS[fs], lab = s => fs === 'short' ? s + ' s' : mmss(s);
    return `<div id="mdl" style="position:fixed;inset:0;background:rgba(10,12,16,.55);display:flex;align-items:center;justify-content:center;z-index:20" data-act="mdlFuera"><div style="background:var(--card);border:1px solid var(--line);border-radius:14px;width:min(520px,94vw);max-height:90vh;overflow-y:auto;padding:22px;box-shadow:0 20px 60px rgba(0,0,0,.35)" data-stop="1">
      <h2 style="margin:0 0 4px;font-size:18px">Díselo a Claude</h2><div class="muted" style="margin-bottom:14px">${esc(it.titulo)}</div>
      <label>Formato del video</label><div class="seg" style="display:flex"><button style="flex:1" class="${fs === 'short' ? 'on' : ''}" data-act="mdlFmt" data-v="short">9:16 · Short</button><button style="flex:1" class="${fs === 'largo' ? 'on' : ''}" data-act="mdlFmt" data-v="largo">16:9 · Largo</button></div>
      <label>${fs === 'short' ? 'Cuántos segundos debe durar' : 'Duración del video largo'}</label>
      <div class="row" style="gap:8px">${ss.map(s => `<button class="mini${m.seg === s ? ' pri' : ''}" data-act="mdlSeg" data-v="${s}">${lab(s)}</button>`).join('')}${fs === 'short' ? `<input id="mdlN" type="number" min="15" max="180" value="${m.seg}" style="width:90px" data-act="mdlNum"> <span class="muted">seg</span>` : ''}</div>
      <div class="note" style="margin-top:10px">${fs === 'short' ? 'Short vertical 9:16. Se graba en borrador mudo para que lo revises antes de generar la voz.' : 'Largo horizontal 16:9 (normalmente 3:30–4:00 y 8 capítulos). Tarda más en grabarse.'}</div>
      <div class="row" style="margin-top:18px;justify-content:flex-end"><button data-act="mdlCerrar">Cancelar</button><button class="pri" data-act="mdlEnviar"><i class="ti ti-send"></i> Enviar a Claude (${fs === 'short' ? '9:16' : '16:9'} · ${lab(m.seg)})</button></div></div></div>`;
  }
  document.addEventListener('click', e => { const b = e.target.closest('[data-act]'); if (!b || !S.modal || !S.modal.cfg) return; const a = b.dataset.act, f = b.dataset.f, c = S.modal.cfg, def = cfgDefs().find(x => x.id === f);
    if (a === 'cfgQuitar') { c[f] = c[f].filter(x => x !== b.dataset.v); pintaModal() } else if (a === 'cfgPreset') { c[f] = LATAM.slice(0, (def && def.max) || 12); pintaModal() } else if (a === 'cfgLimpiar') { c[f] = []; pintaModal() }
    else if (a === 'cfgEq') { cfgDefs().filter(x => x.tipo === 'equipos').forEach(q => { const eq = c[q.id]; if (eq.rojo.includes(b.dataset.v)) { eq.rojo = eq.rojo.filter(x => x !== b.dataset.v); eq.azul.push(b.dataset.v) } else { eq.azul = eq.azul.filter(x => x !== b.dataset.v); eq.rojo.push(b.dataset.v) } }); pintaModal() } }, true);
  document.addEventListener('change', e => { const el = e.target; if (!S.modal || !S.modal.cfg || !el) return;
    if (el.dataset && el.dataset.cfgcm) { const def = cfgDefs().find(x => x.tipo === 'comentario'); if (def) { const cm = S.modal.cfg[def.id] = S.modal.cfg[def.id] || {}; cm[el.dataset.cfgcm] = el.type === 'checkbox' ? el.checked : (el.type === 'number' ? +el.value : el.value); pintaModal() } }
    else if (el.dataset && el.dataset.cfg) { S.modal.cfg[el.dataset.cfg] = el.type === 'checkbox' ? el.checked : (el.type === 'number' ? +el.value : el.value); pintaModal() }
    else if (el.dataset && el.dataset.cfgadd) { const p = (S.paises || []).find(x => x.nom.toLowerCase() === el.value.trim().toLowerCase()), def = cfgDefs().find(x => x.id === el.dataset.cfgadd); if (p && !S.modal.cfg[el.dataset.cfgadd].includes(p.cod)) { if (def && def.max && S.modal.cfg[def.id].length >= def.max) return alert('Máximo ' + def.max + ' países'); S.modal.cfg[el.dataset.cfgadd].push(p.cod) } pintaModal() } });
  function pintaModal() { let h = document.getElementById('mdlHost'); if (!h) { h = document.createElement('div'); h.id = 'mdlHost'; document.body.append(h) } h.innerHTML = modalHtml() }

  /* ---------- CEREBRO 3D v2 · redondo, interactivo (arrastra, pasa el cursor, toca) y con DOS AGENTES: formato y diseño ---------- */
  const DESC_ETAPA = ['Claude lee el pedido y la configuración que elegiste para este video.', 'Escribe el guion y las frases, con el gancho al inicio.', 'Prepara el escenario y los países que juegan.', 'Dibuja los personajes y las escenas del juego.', 'Gráficos y efectos: aquí trabaja el agente de diseño.', 'Voz y tiempos de cada frase.', 'Verificación: tiempos muertos, errores y cuadros del final.', 'Borrador listo para que lo revises en el panel.'];
  const AGENTES = { formato: { nom: 'AGENTE DE FORMATO', col: '#38d6ff', lobulo: 1, hace: 'Trae el mejor formato para la idea: tipo de inicio, duración y estructura.' }, diseno: { nom: 'AGENTE DE DISEÑO', col: '#ff5fd2', lobulo: 4, hace: 'Trae el mejor diseño gráfico del juego: fondo, paleta, estilo y peligro estrella.' } };
  let B = null; const BR = { ry: .4, rx: -.22, vy: 0, drag: false, lx: 0, ly: 0, mx: -999, my: -999, hover: -1, foco: -1, ag: null, last: 0, pulsos: [], orb: [], rotos: null };
  function mkBrain() {
    let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647, N = 560, ga = Math.PI * (3 - Math.sqrt(5)), pts = [];
    for (let i = 0; i < N; i++) {
      const y = 1 - (i / (N - 1)) * 2, r = Math.sqrt(1 - y * y), th = ga * i, x = Math.cos(th) * r, z = Math.sin(th) * r;
      const f = 1 + .075 * Math.sin(5 * x + 3 * y) * Math.cos(4 * z) + .055 * Math.sin(9 * y + 2 * z) + .04 * Math.cos(7 * x - 5 * z);   // surcos y circunvoluciones
      let X = x * 1.3 * f, Y = y * .95 * f * (y < -.55 ? .85 : 1), Z = z * .92 * f; X += (X < 0 ? -1 : 1) * .05;   // fisura central
      const l = Math.floor(((Math.atan2(Z, X) + Math.PI) / (2 * Math.PI)) * 8) % 8; pts.push({ x: X, y: Y, z: Z, l, b: rnd() });
    }
    const ed = []; const d2 = (a, b) => (a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2;
    pts.forEach((a, i) => { pts.map((b, j) => [j, d2(a, b)]).filter(q => q[0] !== i).sort((u, v) => u[1] - v[1]).slice(0, 3).forEach(q => { if (q[0] > i || !ed.some(e => e[0] === q[0] && e[1] === i)) ed.push([i, q[0], a.l]) }) });
    const cen = Array.from({ length: 8 }, (_, k) => { const L = pts.filter(q => q.l === k), n = L.length || 1, c = { x: L.reduce((a, q) => a + q.x, 0) / n, y: L.reduce((a, q) => a + q.y, 0) / n, z: L.reduce((a, q) => a + q.z, 0) / n }, m = Math.hypot(c.x, c.y, c.z) || 1; return { x: c.x / m * 1.38, y: c.y / m * 1.1, z: c.z / m * 1.1 } });
    return { pts, ed, cen };
  }
  const glowCache = {};
  const glowDe = col => { if (!glowCache[col]) { const c = document.createElement('canvas'); c.width = c.height = 64; const g = c.getContext('2d'), gr = g.createRadialGradient(32, 32, 0, 32, 32, 32); gr.addColorStop(0, '#ffffff'); gr.addColorStop(.18, col); gr.addColorStop(.5, col); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.globalAlpha = 1; g.fillStyle = gr; g.fillRect(0, 0, 64, 64); glowCache[col] = c } return glowCache[col] };
  function agentesDe() { const b = S.brain || {}; return b.agentes || {} }
  function pintaCerebro(cv) {
    if (!cv || !document.body.contains(cv)) return; if (!B) B = mkBrain();
    if (!cv._ev) { cv._ev = true;
      const pos = e => { const r = cv.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top] };
      cv.addEventListener('pointerdown', e => { BR.drag = true; [BR.lx, BR.ly] = pos(e); BR.mv = 0; cv.setPointerCapture(e.pointerId); cv.style.cursor = 'grabbing' });
      cv.addEventListener('pointermove', e => { const [x, y] = pos(e); BR.mx = x; BR.my = y; if (BR.drag) { const dx = x - BR.lx, dy = y - BR.ly; BR.ry += dx * .009; BR.rx = Math.max(-1.1, Math.min(1.1, BR.rx + dy * .006)); BR.vy = dx * .009 * 12; BR.lx = x; BR.ly = y; BR.mv += Math.abs(dx) + Math.abs(dy) } });
      cv.addEventListener('pointerup', e => { BR.drag = false; cv.style.cursor = 'grab'; if (BR.mv < 6) { const [x, y] = pos(e); const ag = (BR.orb || []).find(o => Math.hypot(o.X - x, o.Y - y) < 34); if (ag) { BR.ag = BR.ag === ag.k ? null : ag.k; BR.foco = -1 } else { const lb = (BR.rotos || []).find(o => Math.hypot(o.X - x, o.Y - y) < 44); BR.foco = lb && BR.foco !== lb.k ? lb.k : -1; BR.ag = null } actualizaInfoCerebro() } });
      cv.addEventListener('pointerleave', () => { BR.mx = BR.my = -999; BR.drag = false; cv.style.cursor = 'grab' }); cv.style.cursor = 'grab'; cv.style.touchAction = 'none';
    }
    const dpr = window.devicePixelRatio || 1, w = cv.clientWidth, h = cv.clientHeight; if (cv.width !== Math.round(w * dpr)) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr) }
    const c = cv.getContext('2d'); c.setTransform(dpr, 0, 0, dpr, 0, 0); c.clearRect(0, 0, w, h);
    const css = getComputedStyle(document.documentElement), col = n => css.getPropertyValue(n).trim() || '#888', OK = col('--ok'), WARN = col('--warn'), BAD = col('--bad'), GRY = col('--tx3'), TX = col('--tx2');
    const now = performance.now() / 1000, dt = Math.min(.05, now - (BR.last || now)); BR.last = now; if (!BR.drag) { BR.ry += (dt * .3) + BR.vy * dt; BR.vy *= .94 }
    const cs = Math.cos(BR.ry), sn = Math.sin(BR.ry), cx_ = Math.cos(BR.rx), sx_ = Math.sin(BR.rx), sc = Math.min(w / 3.9, h / 3.05), X0 = w / 2, Y0 = h / 2 + 6;
    const proj = p => { let x = p.x * cs + p.z * sn, z = -p.x * sn + p.z * cs, y = p.y * cx_ - z * sx_; z = p.y * sx_ + z * cx_; const s = 3.6 / (3.6 - z); return { X: X0 + x * s * sc, Y: Y0 - y * s * sc, z, s } };
    const br = S.brain || {}, act = br.hecho ? 99 : (br.etapa || 1) - 1, ags = agentesDe();
    const estado = k => br.error && k === act ? 'bad' : (k < act ? 'ok' : (k === act ? 'act' : 'pend')), colDe = k => ({ ok: OK, act: WARN, bad: BAD, pend: GRY })[estado(k)];
    // halo central
    const hg = c.createRadialGradient(X0, Y0, 10, X0, Y0, sc * 1.9); hg.addColorStop(0, (br.hecho ? OK : WARN) + '40'); hg.addColorStop(1, 'rgba(0,0,0,0)'); c.globalCompositeOperation = 'lighter'; c.globalAlpha = .55 + .15 * Math.sin(now * 2); c.fillStyle = hg; c.fillRect(0, 0, w, h); c.globalAlpha = 1;
    const P = B.pts.map(p => ({ ...proj(p), p }));
    // aristas con brillo aditivo
    c.lineWidth = 1; B.ed.forEach(e => { const a = P[e[0]], b = P[e[1]], est = estado(e[2]); c.globalAlpha = (est === 'pend' ? .1 : .34) * (.35 + (a.z + b.z + 2.4) / 5); c.strokeStyle = colDe(e[2]); c.beginPath(); c.moveTo(a.X, a.Y); c.lineTo(b.X, b.Y); c.stroke() });
    // pulsos que viajan por las aristas del lóbulo activo
    if (!br.hecho && Math.random() < dt * 22) { const cand = B.ed.map((e, i) => [i, e]).filter(q => q[1][2] === Math.max(0, act)); if (cand.length) BR.pulsos.push({ e: cand[Math.floor(Math.random() * cand.length)][0], t0: now }) }
    BR.pulsos = BR.pulsos.filter(q => now - q.t0 < .9); BR.pulsos.forEach(q => { const e = B.ed[q.e], a = P[e[0]], b = P[e[1]], f = (now - q.t0) / .9; c.globalAlpha = 1 - f * .5; c.drawImage(glowDe(WARN), a.X + (b.X - a.X) * f - 9, a.Y + (b.Y - a.Y) * f - 9, 18, 18) });
    // neuronas (brillos)
    P.slice().sort((a, b) => a.z - b.z).forEach(q => { const k = q.p.l, est = estado(k), pulse = est === 'act' ? 1 + .35 * Math.sin(now * 5 + q.p.b * 20) : 1, sz = (3.6 + q.p.b * 3) * q.s * pulse; c.globalAlpha = (est === 'pend' ? .3 : .85) * (.4 + (q.z + 1.3) / 2.6); c.drawImage(glowDe(colDe(k)), q.X - sz, q.Y - sz, sz * 2, sz * 2) });
    c.globalCompositeOperation = 'source-over';
    // aro de partículas
    for (let i = 0; i < 46; i++) { const a = now * .5 + i * 6.283 / 46, pr = proj({ x: Math.cos(a) * 1.95, y: Math.sin(a * 2 + i) * .08 + Math.sin(i) * .05, z: Math.sin(a) * 1.5 }); c.globalAlpha = .16 + .3 * ((pr.z + 1.8) / 3.6); c.fillStyle = TX; c.beginPath(); c.arc(pr.X, pr.Y, 1.3 * pr.s, 0, 6.283); c.fill() }
    // etiquetas de etapa
    BR.rotos = []; BR.hover = -1;
    B.cen.forEach((cc, k) => { const q = proj(cc), est = estado(k), front = q.z > -.3; BR.rotos.push({ k, X: q.X, Y: q.Y, z: q.z }); if (est === 'act' || est === 'bad') { const g = c.createRadialGradient(q.X, q.Y, 0, q.X, q.Y, 50 * q.s); g.addColorStop(0, (est === 'bad' ? BAD : WARN) + 'aa'); g.addColorStop(1, 'rgba(0,0,0,0)'); c.globalAlpha = (.5 + .3 * Math.sin(now * 4)) * (front ? 1 : .4); c.fillStyle = g; c.beginPath(); c.arc(q.X, q.Y, 50 * q.s, 0, 6.283); c.fill() }
      if (Math.hypot(q.X - BR.mx, q.Y - BR.my) < 44 && front) BR.hover = k; const sel = BR.foco === k || BR.hover === k;
      c.globalAlpha = front ? 1 : .3; c.font = (sel ? '700 ' : '600 ') + Math.round(12 * q.s + 1) + 'px system-ui'; c.textAlign = 'center'; c.fillStyle = est === 'pend' ? TX : colDe(k); const lab = (est === 'ok' ? '✓ ' : (k + 1) + '. ') + ETAPAS[k]; if (sel) { const tw = c.measureText(lab).width + 14; c.globalAlpha = .85; c.fillStyle = 'rgba(0,0,0,.55)'; c.beginPath(); c.roundRect(q.X - tw / 2, q.Y - 22 * q.s - 13, tw, 20, 8); c.fill(); c.fillStyle = '#fff' } c.fillText(lab, q.X, q.Y - 22 * q.s) });
    // los DOS AGENTES: orbitan, se conectan con su lóbulo y muestran lo que trajeron
    BR.orb = []; Object.keys(AGENTES).forEach((nm, i) => { const A = AGENTES[nm], ag = ags[nm] || {}, ph = now * (.45 + i * .1) + i * 3.1, pr = proj({ x: Math.cos(ph) * 2.15, y: .55 - i * 1.1 + Math.sin(now * .9 + i) * .15, z: Math.sin(ph) * 1.7 }), lobq = proj(B.cen[A.lobulo]), activo = ag.estado === 'pensando', listo = ag.estado === 'listo';
      c.globalCompositeOperation = 'lighter'; c.globalAlpha = (listo ? .55 : .28) * (pr.z > -.5 ? 1 : .5); c.strokeStyle = A.col; c.lineWidth = 1.6; c.setLineDash([5, 5]); c.lineDashOffset = -now * 30; c.beginPath(); c.moveTo(pr.X, pr.Y); c.lineTo(lobq.X, lobq.Y); c.stroke(); c.setLineDash([]);
      if (listo || activo) for (let k = 0; k < 3; k++) { const f = ((now * .6 + k / 3) % 1); c.globalAlpha = .9; c.drawImage(glowDe(A.col), pr.X + (lobq.X - pr.X) * f - 7, pr.Y + (lobq.Y - pr.Y) * f - 7, 14, 14) }
      const r = 17 * pr.s * (activo ? 1 + .15 * Math.sin(now * 8) : 1); c.globalAlpha = .9; c.drawImage(glowDe(A.col), pr.X - r * 2, pr.Y - r * 2, r * 4, r * 4); c.globalCompositeOperation = 'source-over';
      c.globalAlpha = 1; c.lineWidth = 2.2; c.strokeStyle = '#fff'; c.beginPath(); c.arc(pr.X, pr.Y, r * .8, 0, 6.283); c.stroke(); c.font = '700 ' + Math.round(11 * pr.s + 1) + 'px system-ui'; c.textAlign = 'center'; c.fillStyle = '#fff'; c.fillText(nm === 'formato' ? 'F' : 'D', pr.X, pr.Y + 4 * pr.s);
      c.fillStyle = A.col; c.font = '700 ' + Math.round(10.5 * pr.s + 1) + 'px system-ui'; c.fillText(A.nom, pr.X, pr.Y - r * 1.5 - 4);
      const txt = ag.resumen || (listo ? 'Listo' : activo ? 'Pensando…' : 'Esperando'); c.font = '500 ' + Math.round(10.5 * pr.s + 1) + 'px system-ui'; const tw = Math.min(210, c.measureText(txt).width + 14); c.globalAlpha = .92; c.fillStyle = 'rgba(8,12,30,.78)'; c.beginPath(); c.roundRect(pr.X - tw / 2, pr.Y + r * 1.2, tw, 20, 9); c.fill(); c.strokeStyle = A.col; c.lineWidth = 1; c.stroke(); c.fillStyle = '#fff'; c.save(); c.beginPath(); c.rect(pr.X - tw / 2 + 4, pr.Y + r * 1.2, tw - 8, 20); c.clip(); c.fillText(txt, pr.X, pr.Y + r * 1.2 + 14); c.restore();
      BR.orb.push({ k: nm, X: pr.X, Y: pr.Y }); if (Math.hypot(pr.X - BR.mx, pr.Y - BR.my) < 34) { c.globalAlpha = .9; c.strokeStyle = A.col; c.lineWidth = 2; c.beginPath(); c.arc(pr.X, pr.Y, r + 7, 0, 6.283); c.stroke() } });
    c.globalAlpha = 1; requestAnimationFrame(() => pintaCerebro(cv));
  }
  function actualizaInfoCerebro() {
    const el = document.getElementById('brInfo'); if (!el) return; const b = S.brain || {}, ags = agentesDe();
    if (BR.ag) { const A = AGENTES[BR.ag], ag = ags[BR.ag] || {}; el.innerHTML = `<b style="color:${A.col}">${A.nom}</b> · ${esc(ag.estado || 'esperando')}<div class="muted" style="margin:2px 0 6px">${esc(A.hace)}</div>${ag.msg ? '<div>' + esc(ag.msg) + '</div>' : '<div class="muted">Aún no trajo nada: aparecerá aquí cuando Claude lo pida.</div>'}`; return }
    if (BR.foco >= 0) { const k = BR.foco, est = b.error && k === (b.etapa || 1) - 1 ? 'con problemas' : (b.hecho || k < (b.etapa || 1) - 1) ? 'terminada' : k === (b.etapa || 1) - 1 ? 'en curso' : 'pendiente'; el.innerHTML = `<b>${k + 1}. ${esc(ETAPAS[k])}</b> · ${est}<div class="muted" style="margin-top:2px">${esc(DESC_ETAPA[k])}</div>`; return }
    el.innerHTML = '<span class="muted">Arrastra el cerebro para girarlo. Toca una etapa o uno de los dos agentes para ver qué hace.</span>';
  }
  function agentesCards() {
    const ags = agentesDe(); return `<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;padding:12px 16px;border-top:1px solid var(--line)">` + Object.keys(AGENTES).map(nm => { const A = AGENTES[nm], ag = ags[nm] || {}; return `<div style="border:1px solid ${A.col};border-radius:12px;padding:10px 12px;background:rgba(0,0,0,.12)"><div style="display:flex;align-items:center;gap:8px"><span style="width:10px;height:10px;border-radius:50%;background:${A.col};box-shadow:0 0 10px ${A.col}"></span><b style="font-size:12.5px;color:${A.col}">${A.nom}</b><span class="muted" style="margin-left:auto;font-size:12px">${esc(ag.estado === 'listo' ? 'listo' : ag.estado === 'pensando' ? 'pensando…' : 'esperando')}</span></div><div style="font-weight:600;margin:6px 0 2px;font-size:13px">${esc(ag.resumen || '—')}</div><div class="muted" style="font-size:12px;line-height:1.4;max-height:92px;overflow:auto">${esc(ag.msg && ag.msg !== ag.resumen ? ag.msg : A.hace)}</div></div>` }).join('') + '</div>';
  }

  /* ---------- Vista de video EN ESPERA / en construcción ---------- */
  function actualizaBrain(p) {
    const x = pedVideo(p.idea); if (!x) { S.brain = { etapa: 1, hecho: false, error: false, pct: 0, msg: 'Preparando…' }; return }
    S.brain = { etapa: x.etapa || (x.estado === 'pendiente' ? 1 : 2), hecho: x.estado === 'hecho', error: !!x.error, pct: x.pct || 0, msg: x.msg || '', estado: x.estado || 'pendiente', hora: x.hora, agentes: x.agentes || {} };
  }
  function rEspera(p) {
    actualizaBrain(p); const b = S.brain, pend = b.estado === 'pendiente', pct = b.hecho ? 100 : b.pct;
    const estTxt = b.error ? 'Hubo un problema' : b.hecho ? 'Listo' : pend ? (S.est.claude ? 'En espera: Claude lo recibió y empieza enseguida' : 'En espera: Claude está desconectado, lo verá al conectarse') : 'Claude está generando el video';
    const lis = ETAPAS.map((n, k) => { const ok = b.hecho || k < b.etapa - 1, now = !b.hecho && k === b.etapa - 1 && !pend; return `<div class="fr" style="cursor:default"><span class="t" style="color:${ok ? 'var(--ok)' : now ? 'var(--warn)' : 'var(--tx3)'}">${ok ? '<i class="ti ti-check"></i>' : now ? '<i class="ti ti-loader-2"></i>' : (k + 1)}</span><div class="x" style="${ok || now ? '' : 'color:var(--tx3)'}">${n}</div></div>` }).join('');
    const arch = (S.act.codigo.archivos || []).slice(0, 8).map(f => `<div class="fr" data-act="verCodigo" data-c="${esc(S.act.codigo.carpeta)}" data-f="${esc(f.f)}"><span class="t">${esc(f.hora)}</span><div class="x" style="font-family:ui-monospace,Consolas,monospace;font-size:12px">${esc(f.f)}<div class="s">${f.lineas} líneas · ${f.kb} KB</div></div></div>`).join('') || '<div class="empty" style="padding:14px">Aún no hay código nuevo.</div>';
    const logs = (S.act.log || []).slice(-8).reverse().map(l => `<div class="fr" style="cursor:default"><span class="t">${esc(l.hora)}</span><div class="x">${esc(l.msg)}${l.archivos && l.archivos.length ? '<div class="s">' + l.archivos.map(esc).join(' · ') + '</div>' : ''}</div></div>`).join('') || '<div class="empty" style="padding:14px">Esperando el primer aviso de Claude…</div>';
    const px = pedVideo(p.idea), q = px && px.pregunta, banner = q ? `<div class="panel" style="border-color:var(--warn);margin-bottom:14px"><header style="background:var(--warnbg)"><h2 style="color:var(--warn)"><i class="ti ti-help-circle"></i> Claude te pregunta y espera tu respuesta</h2></header><div class="body"><p style="margin:0 0 10px;font-size:15px">${esc(q.texto)}</p><div class="row">${(q.opciones || []).map(o => `<button class="pri mini" data-act="responder" data-idea="${esc(p.idea)}" data-r="${esc(o)}">${esc(o)}</button>`).join('')}</div><div class="row" style="margin-top:10px"><input id="respTxt" placeholder="O escribe tu respuesta…" style="flex:1"><button class="mini" data-act="responder" data-idea="${esc(p.idea)}" data-r="">Enviar</button></div></div></div>` : '';
    return banner + `<div class="row" style="margin-bottom:10px"><button class="mini" data-act="nav" data-p="videos" data-clear="1"><i class="ti ti-arrow-left"></i> Todos los videos</button><b style="font-size:16px">${esc(p.titulo)}</b>${chip(p.aspecto || '', '')}${chip((p.formato === 'largo' ? mmss(p.seg || p.duracion) : (p.seg || p.duracion) + ' s'), '')}${chip(b.hecho ? 'Listo' : b.error ? 'Error' : pend ? 'En espera' : 'Generando', b.hecho ? 'ok' : b.error ? 'bad' : pend ? 'warn' : 'acc')}</div>
    <div class="vid2" style="grid-template-columns:minmax(0,1.5fr) minmax(0,1fr)"><div class="panel"><header><h2>Cerebro de producción</h2><div class="r muted" style="font-size:12px">${esc(estTxt)}</div></header><canvas id="brain" style="width:100%;height:470px;display:block"></canvas><div id="brInfo" style="padding:10px 16px;border-top:1px solid var(--line);font-size:13px;min-height:44px"></div><div id="agCards">${agentesCards()}</div>
      <div style="padding:12px 16px;border-top:1px solid var(--line)"><div style="display:flex;justify-content:space-between;font-size:13px"><b>${pct}%</b><span class="muted" id="brMsg">${esc(b.msg || '')}</span></div><div class="bar" style="margin-top:6px;height:8px;border-radius:4px;background:var(--neu);overflow:hidden"><i style="display:block;height:100%;width:${Math.max(2, pct)}%;background:${b.error ? 'var(--bad)' : 'var(--ok)'}"></i></div></div></div>
     <div><div class="panel"><header><h2>Etapas</h2></header>${lis}</div><div class="panel"><header><h2>Claude acaba de hacer</h2></header>${logs}</div><div class="panel"><header><h2>Código generado</h2><div class="r"><button class="mini" data-act="nav" data-p="actividad">Ver todo</button></div></header>${arch}</div></div></div>`;
  }
  const rVid0 = VIEWS.videos;
  VIEWS.videos = function () {
    if (S.sel && S.sel.indexOf('esp-') === 0 && !S.proy.find(x => x.id === S.sel)) { const r = S.proy.find(x => x.idea === S.sel.slice(4)); S.sel = r ? r.id : null; S.guion = []; if (r) api('/api/guion?id=' + encodeURIComponent(r.id)).then(g => { if (Array.isArray(g)) { S.guion = g; render() } }) }
    const p = S.sel && S.proy.find(x => x.id === S.sel);
    if (p && esEspera(p)) { S.cerebroId = p.id; const h = rEspera(p); setTimeout(() => { pintaCerebro(document.getElementById('brain')); actualizaInfoCerebro() }, 30); return h }
    S.cerebroId = null; return rVid0();
  };
  const parcial0 = window.parcialVideo;
  window.parcialVideo = function () { const p = S.proy.find(x => x.id === S.sel); if (p && esEspera(p)) { if (!document.getElementById('brain')) render(); else { actualizaBrain(p); const m = document.getElementById('brMsg'); if (m) m.textContent = S.brain.msg || ''; const ac = document.getElementById('agCards'); if (ac) ac.innerHTML = agentesCards(); actualizaInfoCerebro() } return } if (S.cerebroId) { render(); return } parcial0() };

  /* ---------- Borrador CON VOZ sincronizado ---------- */
  window.srcDe = function (p) {
    const base = '/series/' + p.carpeta + '/', tieneF = !!(p.existe_final && p.video_final), tieneV = !!p.existe_borrador_voz;
    let v = S.vista; if (v === 'final' && !tieneF) v = tieneV ? 'borradorvoz' : 'mudo'; if (v === 'borradorvoz' && !tieneV) v = 'mudo';
    const src = v === 'final' ? base + p.video_final + '?v=' + (p.unido_t || p.final_t || 0) : v === 'borradorvoz' ? base + p.borrador_voz + '?v=' + (p.borrador_voz_t || 0) : base + (p.video_mudo || '') + '?v=' + (p.mudo_t || 0);
    return { src, vf: v === 'final', vv: v === 'borradorvoz', tieneF, tieneV };
  };
  /* el selector de vista de rVideos: se reescribe el trozo de botones */
  const rVid1 = VIEWS.videos;
  VIEWS.videos = function () {
    let h = rVid1(); const p = S.sel && S.proy.find(x => x.id === S.sel); if (!p || S.cerebroId) return h; const o = srcDe(p);
    const nuevo = `<div class="seg"><button class="${o.vf ? 'on' : ''}" data-act="vista" data-v="final"${o.tieneF ? '' : ' disabled'}>Final con voz</button><button class="${o.vv ? 'on' : ''}" data-act="vista" data-v="borradorvoz"${o.tieneV ? '' : ' disabled'} title="Borrador grabado de nuevo con los tiempos REALES de la voz, con la voz pegada">Borrador con voz</button><button class="${!o.vf && !o.vv ? 'on' : ''}" data-act="vista" data-v="mudo">Borrador sin voz</button></div><button class="mini" data-act="recargarVideo" title="Vuelve a pedir el video al servidor (por si ves uno viejo)"><i class="ti ti-refresh"></i> Recargar video</button>`;
    return h.replace(/<div class="seg"><button class="[^"]*" data-act="vista" data-v="final"[\s\S]*?Sin voz \(borrador\)<\/button><\/div>/, nuevo);
  };

  /* ---------- CAMPANA de avisos ---------- */
  const ICONO = { borrador: 'ti-movie', pregunta: 'ti-help-circle', respuesta: 'ti-message-check', pedido: 'ti-send', ideas: 'ti-bulb', recibido: 'ti-eye-check', avance: 'ti-loader-2', listo: 'ti-circle-check', error: 'ti-alert-triangle', info: 'ti-info-circle' };
  const COLOR = { borrador: 'ok', pregunta: 'warn', respuesta: 'ok', listo: 'ok', error: 'bad', avance: 'acc', recibido: 'acc', pedido: '', ideas: '', info: '' };
  const topbar0 = window.topbar;
  window.topbar = function () {
    topbar0(); const n = S.glog.filter(l => l.ts > S.visto).length, pq = S.ped.filter(x => x.tipo === 'video' && x.pregunta && !x.respuesta);
    const ch = document.getElementById('chips'); if (!ch) return;
    if (pq.length) ch.insertAdjacentHTML('afterbegin', `<button class="mini" data-act="verPregunta" data-idea="${esc(pq[0].idea)}" style="background:var(--warnbg);color:var(--warn);border-color:var(--warn)"><i class="ti ti-help-circle"></i> Claude te pregunta (${pq.length})</button>`);
    ch.insertAdjacentHTML('beforeend', `<button id="bellB" data-act="campana" style="position:relative;padding:5px 10px" title="Avisos de Claude"><i class="ti ti-bell${n ? '-ringing' : ''}" style="font-size:17px"></i>${n ? `<span style="position:absolute;top:-5px;right:-5px;background:var(--bad);color:#fff;border-radius:999px;font-size:10px;padding:0 5px;min-width:16px;text-align:center">${n}</span>` : ''}</button>`);
    let bp = document.getElementById('bellP'); if (!S.bellOpen) { if (bp) bp.remove(); return }
    if (!bp) { bp = document.createElement('div'); bp.id = 'bellP'; document.body.append(bp) }
    bp.style.cssText = 'position:fixed;top:58px;right:22px;width:min(380px,94vw);max-height:70vh;overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:0 14px 40px rgba(0,0,0,.3);z-index:15';
    bp.innerHTML = `<div style="padding:11px 14px;border-bottom:1px solid var(--line);display:flex;align-items:center"><b>Avisos de Claude</b><button class="mini" style="margin-left:auto" data-act="avisosLeidos">Marcar leídos</button></div>` + (S.glog.length ? [...S.glog].reverse().slice(0, 40).map(l => `<div class="fr" style="cursor:default${l.ts > (S.vistoPrev != null ? S.vistoPrev : S.visto) ? ';background:var(--accbg)' : ''}"><span class="t"><i class="ti ${ICONO[l.tipo] || 'ti-info-circle'}" style="color:var(--${COLOR[l.tipo] || 'tx2'})"></i></span><div class="x">${esc(l.msg)}<div class="s">${esc(l.hora)}${l.pct != null ? ' · ' + l.pct + '%' : ''}</div>${l.proyecto ? `<button class="mini" data-act="abrir" data-id="${esc(l.proyecto)}" style="margin-top:6px"><i class="ti ti-player-play"></i> Ver el video</button>` : ''}</div></div>`).join('') : '<div class="empty">Todavía no hay avisos.</div>');
  };
  function beep() { try { const a = new (window.AudioContext || window.webkitAudioContext)(), o = a.createOscillator(), g = a.createGain(); o.frequency.value = 880; g.gain.value = .06; o.connect(g); g.connect(a.destination); o.start(); setTimeout(() => { o.frequency.value = 1320 }, 120); setTimeout(() => { o.stop(); a.close() }, 260) } catch (e) { } }
  async function sondea() {
    const r = await api('/api/actividad'); if (!r || r.error) return; const L = r.log || [];
    if (!S.glogInit) { S.glogInit = true; S.glog = L; topbar(); return }
    const ult = S.glog.length ? S.glog[S.glog.length - 1].ts : 0, nuevos = L.filter(l => l.ts > ult);
    if (nuevos.length) {
      S.glog = L;
      nuevos.forEach(l => { if (l.tipo === 'avance' && !(l.etapa || l.archivos && l.archivos.length) && (l.pct || 0) % 10 !== 0) return; /* los avisos van SOLO a la campana (sin ventanas emergentes abajo) */ if (l.tipo === 'listo' || l.tipo === 'error' || l.tipo === 'pregunta' || l.tipo === 'borrador') beep(); try { if (window.Notification && Notification.permission === 'granted' && document.hidden) new Notification('Elige tu mapa', { body: l.msg }) } catch (e) { } });
      topbar(); if (S.p === 'actividad') render();
    }
  }
  /* ---------- ACTIVIDAD ---------- */
  function rActividad() {
    const vids = [...new Set(S.ped.filter(x => x.tipo === 'video').map(x => x.idea))], sel = S.actSel || vids[vids.length - 1] || '';
    const L = (S.act.log || []).slice().reverse();
    const arch = (S.act.codigo.archivos || []).map(f => `<div class="fr" data-act="verCodigo" data-c="${esc(S.act.codigo.carpeta)}" data-f="${esc(f.f)}"><span class="t">${esc(f.hora)}</span><div class="x" style="font-family:ui-monospace,Consolas,monospace;font-size:12px">${esc(f.f)}<div class="s">${f.lineas} líneas · ${f.kb} KB</div></div></div>`).join('') || '<div class="empty">Sin archivos nuevos para este video.</div>';
    const cv = S.codeView ? `<div class="panel"><header><h2 style="font-family:ui-monospace,Consolas,monospace;font-size:13px">${esc(S.codeView.archivo)}</h2><div class="r muted" style="font-size:12px">${S.codeView.lineas} líneas${S.codeView.cortado ? ' · mostrando 400' : ''}<button class="mini" data-act="cerrarCodigo">Cerrar</button></div></header><pre style="margin:0;padding:12px 16px;max-height:46vh;overflow:auto;font-size:12px;line-height:1.45;background:var(--side)">${esc(S.codeView.texto)}</pre></div>` : '';
    return `<div class="row" style="margin-bottom:12px"><label style="margin:0">Video</label><select id="actSel" style="width:auto;min-width:260px" data-act="actSel">${vids.map(v => { const x = S.ped.find(z => z.idea === v && z.tipo === 'video'); return `<option value="${esc(v)}"${v === sel ? ' selected' : ''}>${esc((x && x.titulo || v).slice(0, 70))}</option>` }).join('') || '<option value="">(sin videos pedidos)</option>'}</select></div>
    <div class="g2"><div class="panel"><header><h2>Lo que Claude va haciendo</h2><div class="r muted" style="font-size:12px">${L.length} avisos</div></header><div style="max-height:62vh;overflow:auto">${L.map(l => `<div class="fr" style="cursor:default"><span class="t"><i class="ti ${ICONO[l.tipo] || 'ti-info-circle'}" style="color:var(--${COLOR[l.tipo] || 'tx2'})"></i></span><div class="x">${esc(l.msg)}<div class="s">${esc(l.dia || '')} ${esc(l.hora)}${l.pct != null ? ' · ' + l.pct + '%' : ''}${l.etapa ? ' · etapa ' + l.etapa + ' ' + esc(ETAPAS[l.etapa - 1] || '') : ''}</div>${l.archivos && l.archivos.length ? '<div class="s" style="font-family:ui-monospace,Consolas,monospace">' + l.archivos.map(esc).join(' · ') + '</div>' : ''}</div></div>`).join('') || '<div class="empty">Todavía no hay actividad de Claude.</div>'}</div></div>
    <div><div class="panel"><header><h2>Código generado</h2><div class="r muted" style="font-size:12px">${esc(S.act.codigo.carpeta || '—')}</div></header><div style="max-height:30vh;overflow:auto">${arch}</div></div>${cv}</div></div>`;
  }
  VIEWS.actividad = rActividad;
  async function cargaAct(id) { const r = await api('/api/actividad' + (id ? '?id=' + encodeURIComponent(id) : '')); if (r && !r.error) { S.act = r; } return r }
  async function cicloAct() {
    await sondea();
    const id = S.p === 'actividad' ? (S.actSel || [...new Set(S.ped.filter(x => x.tipo === 'video').map(x => x.idea))].pop()) : (S.cerebroId && (S.proy.find(x => x.id === S.cerebroId) || {}).idea);
    if (id) { const r = await cargaAct(id); if (r && S.p === 'actividad' && !(document.activeElement && /SELECT|TEXTAREA/.test(document.activeElement.tagName)) && !S.codeView) render(); else if (r && S.cerebroId && !document.getElementById('brain')) render(); else if (r && S.cerebroId) { const p = S.proy.find(x => x.id === S.cerebroId); if (p) { const g = await api('/api/pedidos'); if (Array.isArray(g)) S.ped = g; actualizaBrain(p); const sg = [S.brain.etapa, S.brain.pct, S.brain.estado, S.brain.msg, (S.act.log || []).length, (S.act.codigo.archivos || []).length].join('|'); if (sg !== S._sig) { S._sig = sg; render() } } } }
  }
  setInterval(cicloAct, 3000); cicloAct();

  /* ---------- clics nuevos ---------- */
  document.addEventListener('click', async e => {
    const b = e.target.closest('[data-act]'); if (b && b.dataset.act === 'mdlFuera' && !e.target.closest('[data-stop]')) { S.modal = null; pintaModal(); return }
    if (!b) { if (S.bellOpen && !e.target.closest('#bellP')) { S.bellOpen = false; S.vistoPrev = null; topbar() } return }
    const a = b.dataset.act, d = b.dataset;
    if (a === 'diselo') { const it = S.cat.find(x => x.id === d.id); if (!it) return; if (!S.plugins) { const r = await api('/api/plugins'); if (Array.isArray(r)) S.plugins = r } if (!S.paises) { const r = await api('/api/paises'); if (Array.isArray(r)) S.paises = r } S.modal = { id: it.id, formato: it.formato || 'short', seg: it.formato === 'largo' ? 240 : 60 }; S.modal.cfg = cfgIni(); pintaModal() }
    else if (a === 'mdlFmt') { S.modal.formato = d.v; S.modal.seg = d.v === 'short' ? 60 : 240; pintaModal() }
    else if (a === 'mdlSeg') { S.modal.seg = +d.v; pintaModal() }
    else if (a === 'mdlCerrar') { S.modal = null; pintaModal() }
    else if (a === 'mdlEnviar') {
      const n = document.getElementById('mdlN'); if (n && +n.value) S.modal.seg = +n.value; const m = S.modal; b.disabled = true;
      const r = await api('/api/idea_a_claude', { id: m.id, formato: m.formato, seg: m.seg, config: m.cfg }); S.modal = null; pintaModal();
      if (r && r.error) { alert(r.error); return }
      toast('Enviado a Claude: ahora el video está EN ESPERA'); await cargar(true); S.p = 'videos'; S.sel = r.proyecto; S.cerebroId = r.proyecto; render(); sondea();
    }
    else if (a === 'recargarVideo') { const v = document.getElementById('vp'); if (v) { const t = v.currentTime; const base = (v.dataset.src || v.src).split('&r=')[0]; await cargar(true); const p = S.proy.find(x => x.id === S.sel); const o = p ? srcDe(p) : { src: base }; v.dataset.src = o.src; v.src = o.src + '&r=' + Date.now(); v.load(); v.currentTime = 0; toast('Video recargado') } }
    else if (a === 'verPregunta') { const pr = S.proy.find(x => x.idea === d.idea); if (pr) { S.p = 'videos'; S.sel = pr.id; render() } }
    else if (a === 'responder') { const r = d.r || (document.getElementById('respTxt') || {}).value || ''; if (!r.trim()) return alert('Elige una opción o escribe tu respuesta.'); const x = await api('/api/responder', { idea: d.idea, respuesta: r.trim() }); if (x && x.error) return alert(x.error); toast('Respuesta enviada: Claude sigue con el video'); await cargar(true); render() }
    else if (a === 'irPedidos') { S.p = 'pedidos'; render() }
    else if (a === 'campana') { S.bellOpen = !S.bellOpen; if (S.bellOpen) { S.vistoPrev = S.visto; S.visto = Date.now() / 1000; store.set('act_visto', S.visto) } else S.vistoPrev = null; try { if (window.Notification && Notification.permission === 'default') Notification.requestPermission() } catch (er) { } topbar() }
    else if (a === 'avisosLeidos') { S.visto = Date.now() / 1000; store.set('act_visto', S.visto); topbar() }
    else if (a === 'verCodigo') { const r = await api('/api/archivo?c=' + encodeURIComponent(d.c) + '&f=' + encodeURIComponent(d.f)); if (r && !r.error) { S.codeView = r; if (S.p !== 'actividad') { S.p = 'actividad' } render() } }
    else if (a === 'cerrarCodigo') { S.codeView = null; render() }
  }, true);
  document.addEventListener('change', e => { const b = e.target.closest('[data-act="actSel"]'); if (b) { S.actSel = b.value; S.codeView = null; cicloAct(); } });
  document.addEventListener('input', e => { if (e.target.id === 'mdlN' && S.modal) { S.modal.seg = +e.target.value || S.modal.seg } });
  /* el pedido ahora lleva a «Ideas» */
  document.addEventListener('click', async e => {
    const b = e.target.closest('[data-act="pedido"]'); if (!b) return; e.stopImmediatePropagation(); e.preventDefault();
    const t = (document.getElementById('ped') || {}).value || ''; if (!t.trim()) return alert('Cuéntame qué video quieres.'); const f = document.getElementById('pedf').value;
    const r = await api('/api/pedido', { texto: t.trim(), formato: f }); if (r && r.error) return alert(r.error);
    toast('Listo: te preparé ' + (r.ideas || 0) + ' ideas con cómo podrían suceder'); S.fmt = f; S.p = 'ideas'; await cargar(true); render();
  }, true);

  /* ---------- PLUGINS (abajo en el menú): lo que usamos y su descarga ---------- */
  TIT.plugins = ['Plugins', 'Los plugins que usa el panel y su descarga (solo lo necesario)'];
  (function () { const a = document.querySelector('.nav[data-p="ajustes"]'); if (!a || document.querySelector('.nav[data-p="plugins"]')) return; const b = document.createElement('button'); b.className = 'nav'; b.dataset.act = 'nav'; b.dataset.p = 'plugins'; b.innerHTML = '<i class="ti ti-puzzle"></i><span>Plugins</span>'; a.before(b); })();
  VIEWS.plugins = function () {
    if (!S.plugins) { api('/api/plugins').then(r => { if (Array.isArray(r)) { S.plugins = r; if (S.p === 'plugins') render() } }); return '<div class="empty">Preparando los paquetes…</div>' }
    if (!S.plugins.length) return `<div class="panel"><div class="empty" style="padding:44px 20px"><i class="ti ti-puzzle" style="font-size:34px"></i><p style="margin:10px 0 4px;font-size:16px;color:var(--tx)">No hay ningún plugin instalado</p><p style="margin:0">Pon un plugin en la carpeta <b>plugins/</b> del DevIAs Panel y aparecerá aquí. El panel lo detecta, comprueba que cumpla el esqueleto y te dice qué le falta.</p></div></div>`;
    return `<div class="note" style="margin:0 0 14px">Estos son los plugins que estamos usando. Cada descarga lleva solo lo necesario para que el panel funcione: código, motor, plantillas e instrucciones. No incluye videos, voces, miniaturas, claves ni tus datos.</div>` + S.plugins.map(k => `<div class="panel"${k.recomendado ? ' style="border-color:var(--ok)"' : ''}><header><h2>${esc(k.nombre)}</h2><div class="r">${k.valido ? chip('Cumple el esqueleto', 'ok') : chip('Le falta: ' + (k.falta || []).join(', '), 'warn')}</div></header><div class="body"><p style="margin:0 0 10px">${esc(k.desc)}</p><div class="row"><a href="/api/plugin_zip?id=${encodeURIComponent(k.id)}" download style="background:var(--tx);color:var(--card);padding:8px 16px;border-radius:8px;font-weight:600"><i class="ti ti-download"></i> Descargar (.zip)</a><span class="muted" style="font-size:12px">${k.archivos} archivos · ${k.mb} MB · actualizado ${esc(k.actualizado)}</span><button class="mini" data-act="verPlugin" data-id="${esc(k.id)}">Ver archivos</button></div>${S.pluginLista && S.pluginLista.id === k.id ? `<pre style="margin:12px 0 0;max-height:260px;overflow:auto;font-size:12px;background:var(--side);padding:10px;border-radius:8px">${esc(S.pluginLista.l.join('\n'))}</pre>` : ''}</div></div>`).join('');
  };
  document.addEventListener('click', async e => { const b = e.target.closest('[data-act]'); if (!b) return; if (b.dataset.act === 'nav' && b.dataset.p === 'plugins') S.plugins = null; if (b.dataset.act === 'verPlugin') { if (S.pluginLista && S.pluginLista.id === b.dataset.id) { S.pluginLista = null } else { const r = await api('/api/plugins?detalle=1'); const k = Array.isArray(r) && r.find(x => x.id === b.dataset.id); if (k) S.pluginLista = { id: k.id, l: k.lista } } render() } }, true);

  /* ---------- INICIO del DevIAs Panel vacío: guía de arranque ---------- */
  const rIni0 = VIEWS.inicio;
  VIEWS.inicio = function () {
    if (S.proy.length || S.cat.length) return rIni0();
    if (!S.plugins) { api('/api/plugins').then(r => { if (Array.isArray(r)) { S.plugins = r; if (S.p === 'inicio') render() } }); }
    const n = (S.plugins || []).length, ok = (S.plugins || []).filter(k => k.valido).length;
    const paso = (i, t1, t2, extra) => `<div class="paso"><b>${i}</b><div><span>${t1} ${extra || ''}</span><small>${t2}</small></div></div>`;
    return `<div class="cards"><div class="kpi"><small>Plugins instalados</small><b>${n}</b></div><div class="kpi"><small>Videos en proceso</small><b>0</b></div><div class="kpi"><small>Borradores</small><b>0</b></div><div class="kpi"><small>Videos finales</small><b>0</b></div></div>
    <div class="panel"><div class="hero"><div><h2>Empieza instalando un plugin</h2><p>El DevIAs Panel pone el motor: pedidos, grabación, voces, títulos y memoria. Cada plugin trae un formato de video y completa los campos que al panel le faltan.</p><div class="row"><button class="pri" data-act="nav" data-p="plugins"><i class="ti ti-puzzle"></i> Ver plugins</button><button data-act="nav" data-p="ajustes"><i class="ti ti-plug-connected"></i> Conexión con Claude</button></div></div>
    <div class="pasos">${paso(1, 'Instala un plugin', 'Colócalo en la carpeta plugins/. El panel comprueba que cumpla el esqueleto.', n ? chip(ok + ' de ' + n + ' válidos', ok === n ? 'ok' : 'warn') : chip('ninguno todavía', ''))}${paso(2, 'Pide ideas o un video', 'Escribe lo que quieres y el plugin propone cómo hacerlo.')}${paso(3, 'Revisa el borrador', 'Lo ves sin voz, con el diálogo al lado, antes de gastar tiempo de voz.')}${paso(4, 'Genera la voz y publica', 'Voz, unión final, títulos, descripción y miniaturas.')}</div></div></div>`;
  };

  /* ---------- PLUGINS = plugins: esqueleto, requisitos, ajustes y «mejorar este plugin» ---------- */
  TIT.plugins = ['Plugins', 'Plugins que completan el panel con un formato de video'];
  S.skUI = S.skUI || {};
  const pedPlugin = id => S.ped.filter(x => x.tipo === 'plugin_mejora' && x.plugin === id).slice(-3).reverse();
  const campo = (k, a) => { const id = 'sk_' + k.id + '_' + a.id, v = k.valores[a.id];
    if (a.tipo === 'interruptor') return `<label style="display:flex;gap:10px;align-items:center;margin:10px 0"><input type="checkbox" id="${id}" ${v ? 'checked' : ''} style="width:auto;height:auto"> ${esc(a.etiqueta)}</label>`;
    if (a.tipo === 'opcion') return `<label for="${id}">${esc(a.etiqueta)}</label><select id="${id}">${(a.opciones || []).map(o => `<option${o === v ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
    return `<label for="${id}">${esc(a.etiqueta)}</label><input id="${id}" type="number" value="${esc(v)}" ${a.min != null ? 'min="' + a.min + '"' : ''} ${a.max != null ? 'max="' + a.max + '"' : ''}>`; };
  function tarjetaPlugin(k) {
    const ab = S.skUI[k.id] || '', faltan = k.requisitos.filter(r => !r.ok), pip = faltan.filter(r => r.tipo === 'python');
    const rq = k.requisitos.map(r => `<span class="chip ${r.ok ? 'ok' : 'warn'}" title="${esc(r.tipo)}">${esc(r.nombre)}</span>`).join(' ');
    const fm = (k.formatos || []).map(f => chip((f.nombre || f.id) + ' · ' + f.aspecto + ' · ' + f.defecto + (f.aspecto === '9:16' ? ' s' : ' s'), '')).join(' ');
    return `<div class="panel"${k.activo ? ' style="border-color:var(--acc)"' : ''}><header><h2>${esc(k.nombre)}</h2><span class="muted" style="font-size:12px">v${esc(k.version)}</span><div class="r">${k.activo ? chip('Activo', 'acc') : ''}${k.valido ? chip('Cumple el esqueleto', 'ok') : chip('No cumple el esqueleto', 'bad')}</div></header><div class="body">
      <p style="margin:0 0 10px">${esc(k.desc)}</p>
      ${k.valido ? `<div class="row" style="margin-bottom:10px">${fm}</div><div class="row" style="margin-bottom:12px"><span class="muted" style="font-size:12.5px">Requisitos:</span> ${rq}${pip.length ? `<button class="mini" data-act="skInstalar" data-id="${esc(k.id)}">Instalar lo que falta (${pip.map(x => esc(x.pip)).join(', ')})</button>` : ''}</div>`
        : `<div style="border:1px solid var(--bad);background:var(--badbg);border-radius:10px;padding:12px 14px;margin-bottom:12px"><b style="color:var(--bad)">El panel no usa este plugin porque le falta:</b><ul style="margin:6px 0 0;padding-left:20px">${k.falta.map(x => '<li>' + esc(x) + '</li>').join('')}</ul></div>`}
      <div class="row"><button class="${k.activo ? '' : 'pri'}" data-act="skActivar" data-id="${esc(k.id)}" data-on="${k.activo ? 0 : 1}"${k.valido ? '' : ' disabled'}><i class="ti ti-${k.activo ? 'player-pause' : 'player-play'}"></i> ${k.activo ? 'Desactivar' : 'Activar'}</button>
        <button data-act="skAbrir" data-id="${esc(k.id)}" data-v="cfg"${k.valido ? '' : ' disabled'}><i class="ti ti-adjustments"></i> Configurar</button><button data-act="skAbrir" data-id="${esc(k.id)}" data-v="mej"${k.valido ? '' : ' disabled'}><i class="ti ti-sparkles"></i> Mejorar este plugin</button>
        <a href="/api/plugin_zip?id=${encodeURIComponent(k.id)}" download style="padding:0 4px;font-weight:500"><i class="ti ti-download"></i> Descargar</a><span class="muted" style="font-size:12px">${k.archivos} archivos · ${k.mb} MB · ${esc(k.actualizado)}</span><button class="mini" data-act="verPlugin" data-id="${esc(k.id)}">Ver archivos</button></div>
      ${ab === 'cfg' ? `<div style="margin-top:14px;border-top:1px solid var(--line);padding-top:4px"><h3 style="margin:12px 0 0;font-size:14px">Configuración del plugin</h3>${k.ajustes.map(a => campo(k, a)).join('')}<div class="row" style="margin-top:14px"><button class="pri" data-act="skGuardar" data-id="${esc(k.id)}">Guardar ajustes</button></div></div>` : ''}
      ${ab === 'mej' ? `<div style="margin-top:14px;border-top:1px solid var(--line);padding-top:4px"><h3 style="margin:12px 0 0;font-size:14px">Mejorar este plugin</h3><div class="note" style="margin:4px 0 8px">Lo que escribas llega a Claude marcado con este plugin. Cambia solo este plugin, guarda una copia antes y sube la versión.</div><textarea id="skm_${esc(k.id)}" placeholder="Ej: que el gancho de los largos dure 8 segundos"></textarea><div class="row" style="margin-top:10px"><button class="pri" data-act="skMejora" data-id="${esc(k.id)}"><i class="ti ti-send"></i> Enviar mejora</button></div>${pedPlugin(k.id).map(x => `<div class="note">${chip(x.estado || 'pendiente', x.estado === 'hecho' ? 'ok' : x.estado === 'en_proceso' ? 'acc' : 'warn')} ${esc((x.titulo || '').slice(0, 90))}${x.msg ? ' · ' + esc(x.msg) : ''}</div>`).join('')}</div>` : ''}
      ${S.pluginLista && S.pluginLista.id === k.id ? `<pre style="margin:12px 0 0;max-height:240px;overflow:auto;font-size:12px;background:var(--side);padding:10px;border-radius:8px">${esc(S.pluginLista.l.join('\n'))}</pre>` : ''}</div></div>`;
  }
  VIEWS.plugins = function () {
    if (!S.plugins || !S.esq) { Promise.all([api('/api/plugins'), api('/api/esqueleto')]).then(([r, e]) => { if (Array.isArray(r)) { S.plugins = r; S.esq = Array.isArray(e) ? e : []; if (S.p === 'plugins') render() } }); return '<div class="empty">Buscando plugins…</div>' }
    const lista = S.plugins.length ? PLG_CSS + '<div class="plgGrid">' + S.plugins.map(tarjetaPlugin).join('') + '</div>' : `<div class="panel"><div class="empty" style="padding:44px 20px"><i class="ti ti-puzzle" style="font-size:34px"></i><p style="margin:10px 0 4px;font-size:16px;color:var(--tx)">No hay ningún plugin instalado</p><p style="margin:0">Pon un plugin en la carpeta <b>plugins/</b> del DevIAs Panel y aparecerá aquí.</p></div></div>`;
    const esq = `<details class="panel" id="esqDet"${S.esqAbierto ? ' open' : ''}><summary style="padding:14px 18px;cursor:pointer;font-weight:600">Esqueleto de un plugin <span class="muted" style="font-weight:400;font-size:12.5px">· lo que debe tener su plugin.json para que el panel lo use</span></summary><table><thead><tr><th>Campo</th><th>Tipo</th><th>Para qué sirve</th></tr></thead><tbody>${S.esq.map(c => `<tr><td><code>${esc(c.campo)}</code></td><td class="muted">${esc(c.tipo)}</td><td>${esc(c.para)}</td></tr>`).join('')}</tbody></table></details>`;
    return `<div class="note" style="margin:0 0 14px">El panel pone el motor y cada plugin completa los campos de su formato. Un plugin que no cumpla el esqueleto no se usa.</div>` + lista + esq;
  };
  document.addEventListener('click', async e => { const b = e.target.closest('[data-act]'); if (!b) return; const a = b.dataset.act, id = b.dataset.id, recarga = async () => { const r = await api('/api/plugins'); if (Array.isArray(r)) S.plugins = r; const g = await api('/api/pedidos'); if (Array.isArray(g)) S.ped = g; render() };
    if (a === 'skAbrir') { S.skUI[id] = S.skUI[id] === b.dataset.v ? '' : b.dataset.v; render() }
    else if (a === 'skActivar') { const r = await api('/api/plugin_activar', { id, activar: b.dataset.on === '1' }); if (r && r.error) alert(r.error); else toast(b.dataset.on === '1' ? 'Plugin activado' : 'Plugin desactivado'); recarga() }
    else if (a === 'skGuardar') { const k = S.plugins.find(x => x.id === id), v = {}; k.ajustes.forEach(x => { const el = document.getElementById('sk_' + id + '_' + x.id); if (el) v[x.id] = x.tipo === 'interruptor' ? el.checked : el.value }); const r = await api('/api/plugin_ajustes', { id, valores: v }); if (r && r.error) alert(r.error); else toast('Ajustes guardados'); recarga() }
    else if (a === 'skMejora') { const el = document.getElementById('skm_' + id); const tx = el && el.value.trim(); if (!tx) return alert('Escribe qué quieres mejorar del plugin.'); const r = await api('/api/plugin_mejora', { id, texto: tx }); if (r && r.error) alert(r.error); else { toast('Enviado a Claude: mejora del plugin'); el.value = '' } recarga() }
    else if (a === 'skInstalar') { b.disabled = true; toast('Instalando lo que falta…'); const r = await api('/api/plugin_instalar', { id }); toast(r && r.ok ? 'Listo: instalado' : 'No pude instalar: ' + ((r && (r.error || r.salida)) || '')); recarga() } }, true);

  /* ---------- el núcleo NO trae nada de un formato: todo depende del plugin activo ---------- */
  const skAct = () => (S.plugins || []).find(k => k.activo && k.valido) || null;
  const fmts = () => { const k = skAct(); return k ? k.formatos : []; };
  const fmtDe = id => fmts().find(f => f.id === id) || fmts()[0] || null;
  const labDur = (F, s) => F && F.aspecto === '9:16' ? s + ' s' : mmss(s);
  async function cargaPlugins() { const r = await api('/api/plugins'); if (Array.isArray(r)) { const antes = (skAct() || {}).id; S.plugins = r; const k = skAct(); if (k && !fmts().some(f => f.id === S.fmt)) S.fmt = k.formatos[0].id; if ((k || {}).id !== antes) { topbar(); if (['ideas', 'pedidos', 'inicio'].includes(S.p)) render() } } }
  cargaPlugins(); setInterval(cargaPlugins, 8000);
  const avisoSin = '<div class="panel" style="border-color:var(--warn)"><div class="body" style="display:flex;gap:12px;align-items:center"><i class="ti ti-puzzle" style="font-size:24px;color:var(--warn)"></i><div style="flex:1"><b>No hay ningún plugin activo</b><div class="muted">Sin un plugin el panel no sabe qué video generar, así que aquí no sale nada. Activa uno en Plugins.</div></div><button class="pri" data-act="nav" data-p="plugins">Ir a Plugins</button></div></div>';
  const tbSk = window.topbar; window.topbar = function () { tbSk(); const ch = document.getElementById('chips'); if (!ch) return; const k = skAct(); ch.insertAdjacentHTML('afterbegin', k ? `<button class="mini" data-act="nav" data-p="plugins" title="Plugin activo"><i class="ti ti-puzzle"></i> ${esc(k.nombre)}</button>` : `<button class="mini" data-act="nav" data-p="plugins" style="background:var(--warnbg);color:var(--warn);border-color:var(--warn)"><i class="ti ti-puzzle"></i> Sin plugin activo</button>`) };
  VIEWS.ideas = function () {
    if (!skAct()) return avisoSin;
    const l = S.cat.filter(i => i.estado === 'idea' && i.formato === S.fmt), grupos = {}; l.forEach(i => { const k = String(i.lote || 0); (grupos[k] = grupos[k] || []).push(i) });
    const orden = Object.keys(grupos).sort((a, b) => Number(b) - Number(a));   // cada TANDA (lote) es una página; la más nueva va primero
    const mx = orden.length ? Number(orden[0]) : 0; if (S.ideasMx !== undefined && mx > S.ideasMx) S.ideasPag = 0; S.ideasMx = mx;   // llegó una tanda nueva: se muestra primero
    const np = Math.max(1, orden.length); S.ideasPag = Math.min(Math.max(0, S.ideasPag || 0), np - 1); const k = orden[S.ideasPag];
    const pager = np > 1 ? `<div class="row" style="justify-content:center;gap:10px;padding:12px 18px;border-top:1px solid var(--line)"><button class="mini" data-act="ideasPag" data-d="-1"${S.ideasPag === 0 ? ' disabled' : ''}><i class="ti ti-chevron-left"></i> Más recientes</button><span class="muted">Tanda ${S.ideasPag + 1} de ${np}${S.ideasPag === 0 ? ' · la más nueva' : ''}</span><button class="mini" data-act="ideasPag" data-d="1"${S.ideasPag >= np - 1 ? ' disabled' : ''}>Anteriores <i class="ti ti-chevron-right"></i></button></div>` : '';
    const cuerpo = k === undefined ? '' : (() => { const g = grupos[k], tx = g.find(x => x.pedido_texto); return `<div class="panel" style="margin:0 0 14px;border-radius:0;border-left:0;border-right:0"><div style="padding:10px 18px;background:var(--side);font-size:13px">${tx ? '<b>Basado en tu pedido:</b> «' + esc(tx.pedido_texto) + '»' : '<b>Ideas nuevas</b>'} <span class="muted">· ${g.length} ideas</span></div>${g.map(ideaCard).join('')}</div>` })() + pager;
    return `<div class="panel"><header><h2>Ideas</h2><div class="r"><div class="seg">${fmts().map(f => `<button class="${S.fmt === f.id ? 'on' : ''}" data-act="fmt" data-v="${esc(f.id)}">${esc(f.nombre || f.id)}</button>`).join('')}</div><button class="mini" data-act="irPedidos"><i class="ti ti-message-plus"></i> Nuevo pedido</button><button class="pri mini" data-act="dame10">Dame 100 ideas más</button><button class="mini" data-act="borrar">Borrar y empezar de nuevo</button></div></header>${cuerpo || '<div class="empty">No hay ideas sin empezar en este formato. Escribe un pedido y el plugin te propone ideas, o pulsa «Dame 100 ideas más».</div>'}</div>`;
  };
  document.addEventListener('click', e => { const b = e.target.closest('[data-act]'); if (!b) return; if (b.dataset.act === 'ideasPag') { S.ideasPag = (S.ideasPag || 0) + Number(b.dataset.d); render() } else if (b.dataset.act === 'fmt') S.ideasPag = 0 }, true);
  const rPed2 = VIEWS.pedidos; VIEWS.pedidos = function () { const k = skAct(); let h = rPed2(); if (!k) return avisoSin + h; return h.replace(/<option value="short">Corto<\/option><option value="largo">Largo<\/option>/, fmts().map(f => `<option value="${esc(f.id)}">${esc(f.nombre || f.id)}</option>`).join('')) };
  /* ---------- CONFIGURACIÓN DEL VIDEO que pide el plugin (plugin.json → config_video): se elige aquí, en Ideas, para cada video ---------- */
  const LATAM = ['CHI', 'ARG', 'VEN', 'MEX', 'PER', 'COL', 'URU', 'BRA', 'ECU', 'BOL', 'PAR', 'CUB'];
  const cfgDefs = () => ((skAct() || {}).config_video) || [];
  function cfgIni() { const c = {}; cfgDefs().forEach(f => { c[f.id] = f.defecto !== undefined ? JSON.parse(JSON.stringify(f.defecto)) : (f.tipo === 'paises' ? [] : f.tipo === 'interruptor' ? false : f.tipo === 'equipos' ? { rojo: [], azul: [] } : '') }); return c }
  const nomPais = cod => ((S.paises || []).find(p => p.cod === cod) || {}).nom || cod;
  function equiposAuto(c, f) { const ps = c[f.paises || 'paises'] || [], eq = c[f.id] || { rojo: [], azul: [] }; eq.rojo = eq.rojo.filter(x => ps.includes(x)); eq.azul = eq.azul.filter(x => ps.includes(x)); ps.filter(x => !eq.rojo.includes(x) && !eq.azul.includes(x)).forEach(x => (eq.rojo.length <= eq.azul.length ? eq.rojo : eq.azul).push(x)); c[f.id] = eq }
  function cfgVideoHtml() {
    const defs = cfgDefs(), m = S.modal; if (!defs.length || !m || !m.cfg) return '';
    const campo = f => {
      const v = m.cfg[f.id]; const cab = `<div style="font-weight:600;margin:12px 0 2px">${esc(f.etiqueta)}</div><div class="muted" style="font-size:12.5px;margin-bottom:6px">${esc(f.ayuda)}</div>`;
      if (f.tipo === 'interruptor') return `<label style="display:flex;gap:10px;align-items:flex-start;margin:12px 0 0;cursor:pointer"><input type="checkbox" data-cfg="${esc(f.id)}" ${v ? 'checked' : ''} style="width:auto;height:auto;margin-top:3px"><span><b style="font-weight:600">${esc(f.etiqueta)}</b><span class="muted" style="display:block;font-size:12.5px">${esc(f.ayuda)}</span></span></label>`;
      if (f.tipo === 'opcion') return cab + `<select data-cfg="${esc(f.id)}">${(f.opciones || []).map(o => `<option${o === v ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select>`;
      if (f.tipo === 'numero') return cab + `<input type="number" data-cfg="${esc(f.id)}" value="${esc(v)}" ${f.min != null ? 'min="' + f.min + '"' : ''} ${f.max != null ? 'max="' + f.max + '"' : ''} style="max-width:120px">`;
      if (f.tipo === 'paises') return cab + `<div class="row" style="gap:6px;flex-wrap:wrap">${(v || []).map(c => `<span class="chip acc" style="cursor:pointer" data-act="cfgQuitar" data-f="${esc(f.id)}" data-v="${esc(c)}" title="Quitar">${esc(nomPais(c))} ✕</span>`).join('') || '<span class="muted">Ningún país elegido</span>'}</div>
        <div class="row" style="margin-top:8px;gap:6px"><input list="dlPaises" id="cfgAdd_${esc(f.id)}" placeholder="Escribe un país y pulsa Enter…" style="flex:1" data-cfgadd="${esc(f.id)}"><datalist id="dlPaises">${(S.paises || []).map(p => `<option value="${esc(p.nom)}"></option>`).join('')}</datalist><button class="mini" data-act="cfgPreset" data-f="${esc(f.id)}">Latinoamérica</button><button class="mini" data-act="cfgLimpiar" data-f="${esc(f.id)}">Limpiar</button></div><div class="muted" style="font-size:12px;margin-top:4px">${(v || []).length} elegidos${f.min ? ' · mínimo ' + f.min : ''}${f.max ? ' · máximo ' + f.max : ''}</div>`;
      if (f.tipo === 'ganador') { const ps = m.cfg[f.paises || 'paises'] || []; return cab + `<select data-cfg="${esc(f.id)}"><option value="">Al azar (lo decide el juego)</option>${ps.map(c => `<option value="${esc(c)}"${c === v ? ' selected' : ''}>${esc(nomPais(c))}</option>`).join('')}</select>`; }
      if (f.tipo === 'comentario') { const cm = v || {}; return `<label style="display:flex;gap:10px;align-items:flex-start;margin:12px 0 0;cursor:pointer"><input type="checkbox" data-cfgcm="activo" ${cm.activo ? 'checked' : ''} style="width:auto;height:auto;margin-top:3px"><span><b style="font-weight:600">${esc(f.etiqueta)}</b><span class="muted" style="display:block;font-size:12.5px">${esc(f.ayuda)}</span></span></label>` + (cm.activo ? `<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px"><input data-cfgcm="usuario" placeholder="usuario (sin @)" value="${esc(cm.usuario || '')}"><input data-cfgcm="seg" type="number" min="5" max="70" placeholder="segundo" value="${esc(cm.seg || 11)}"></div><textarea data-cfgcm="texto" placeholder="Mensaje del comentario (lo que escribió el fan)" style="width:100%;min-height:54px;margin-top:8px">${esc(cm.texto || '')}</textarea><input data-cfgcm="voz" value="${esc(cm.voz || '')}" style="margin-top:8px" placeholder="Frase de voz">` : ''); }
      if (f.tipo === 'equipos') { if (f.si && !m.cfg[f.si]) return ''; equiposAuto(m.cfg, f); const eq = m.cfg[f.id], ch = (cod, eqn) => `<span class="chip" style="cursor:pointer;background:${eqn === 'rojo' ? 'rgba(224,38,60,.18)' : 'rgba(34,120,255,.18)'};border:1px solid ${eqn === 'rojo' ? '#e0263c' : '#2278ff'}" data-act="cfgEq" data-f="${esc(f.id)}" data-v="${esc(cod)}" title="Pasar al otro equipo">${esc(nomPais(cod))}</span>`;
        return cab + `<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px"><div><b style="color:#e0263c">Equipo ROJO</b><div class="row" style="gap:6px;flex-wrap:wrap;margin-top:6px">${eq.rojo.map(c => ch(c, 'rojo')).join('') || '<span class="muted">—</span>'}</div></div><div><b style="color:#2278ff">Equipo AZUL</b><div class="row" style="gap:6px;flex-wrap:wrap;margin-top:6px">${eq.azul.map(c => ch(c, 'azul')).join('') || '<span class="muted">—</span>'}</div></div></div><div class="muted" style="font-size:12px;margin-top:4px">Toca un país para pasarlo al otro equipo: así eliges quién juega contra quién.</div>`; }
      return '';
    };
    return `<div style="margin-top:14px;padding-top:6px;border-top:1px solid var(--line)"><div style="font-weight:650;font-size:15px"><i class="ti ti-adjustments"></i> Configuración de este video</div>${defs.map(campo).join('')}</div>`;
  }
  function modalHtml() {
    const m = S.modal; if (!m) return ''; const it = S.cat.find(x => x.id === m.id), F = fmtDe(m.formato); if (!it || !F) return '';
    return `<div id="mdl" style="position:fixed;inset:0;background:rgba(10,12,16,.55);display:flex;align-items:center;justify-content:center;z-index:20" data-act="mdlFuera"><div style="background:var(--card);border:1px solid var(--line);border-radius:14px;width:min(520px,94vw);max-height:90vh;overflow-y:auto;padding:22px;box-shadow:0 20px 60px rgba(0,0,0,.35)" data-stop="1">
      <h2 style="margin:0 0 4px;font-size:18px">Díselo a Claude</h2><div class="muted" style="margin-bottom:14px">${esc(it.titulo)}</div>
      <label>Formato del video</label><div class="seg" style="display:flex">${fmts().map(f => `<button style="flex:1" class="${f.id === F.id ? 'on' : ''}" data-act="mdlFmt" data-v="${esc(f.id)}">${esc(f.aspecto)} · ${esc(f.nombre || f.id)}</button>`).join('')}</div>
      <label>Cuánto debe durar</label>
      <div class="row" style="gap:8px">${F.duraciones.map(s => `<button class="mini${m.seg === s ? ' pri' : ''}" data-act="mdlSeg" data-v="${s}">${labDur(F, s)}</button>`).join('')}<input id="mdlN" type="number" min="15" max="900" value="${m.seg}" style="width:90px"> <span class="muted">seg</span></div>
      ${cfgVideoHtml()}
      <div class="note" style="margin-top:10px">Formato ${esc(F.aspecto)} del plugin «${esc((skAct() || {}).nombre)}». Se graba primero un borrador sin voz para que lo revises.</div>
      <div class="row" style="margin-top:18px;justify-content:flex-end"><button data-act="mdlCerrar">Cancelar</button><button class="pri" data-act="mdlEnviar"><i class="ti ti-send"></i> Enviar a Claude (${esc(F.aspecto)} · ${labDur(F, m.seg)})</button></div></div></div>`;
  }
  document.addEventListener('click', e => { const b = e.target.closest('[data-act]'); if (!b || !S.modal) return; const a = b.dataset.act; if (a === 'diselo' || a === 'mdlFmt') { const F = fmtDe(a === 'mdlFmt' ? b.dataset.v : S.modal.formato); if (F) { S.modal.formato = F.id; S.modal.seg = F.defecto; pintaModal() } } }, true);

  document.addEventListener('toggle', e => { if (e.target && e.target.id === 'esqDet') S.esqAbierto = e.target.open }, true);
  /* ---------- Configurar / Mejorar un plugin: PANEL LATERAL (no se oculta al refrescar, conserva lo que escribes) ---------- */
  S.skDrawer = null; S.skDraft = S.skDraft || {};
  function tarjetaPlugin(k) {
    const faltan = k.requisitos.filter(r => !r.ok), pip = faltan.filter(r => r.tipo === 'python');
    const rq = k.requisitos.map(r => `<span class="chip ${r.ok ? 'ok' : 'warn'}" title="${esc(r.tipo)}">${esc(r.nombre)}</span>`).join(' ');
    const fm = (k.formatos || []).map(f => chip(f.nombre + ' · ' + f.aspecto, '')).join(' ');
    return `<div class="panel"${k.activo ? ' style="border-color:var(--acc)"' : ''}><header><h2>${esc(k.nombre)}</h2><span class="muted" style="font-size:12px">v${esc(k.version)}</span><div class="r">${k.activo ? chip('Activo', 'acc') : ''}${k.valido ? chip('Cumple el esqueleto', 'ok') : chip('No cumple el esqueleto', 'bad')}</div></header><div class="body">
      <p style="margin:0 0 10px">${esc(k.desc)}</p>
      ${k.valido ? `<div class="row" style="margin-bottom:10px"><span class="muted" style="font-size:12.5px">Formatos que soporta:</span> ${fm}</div><div class="row" style="margin-bottom:12px"><span class="muted" style="font-size:12.5px">Requisitos:</span> ${rq}${pip.length ? `<button class="mini" data-act="skInstalar" data-id="${esc(k.id)}">Instalar lo que falta (${pip.map(x => esc(x.pip)).join(', ')})</button>` : ''}</div>`
        : `<div style="border:1px solid var(--bad);background:var(--badbg);border-radius:10px;padding:12px 14px;margin-bottom:12px"><b style="color:var(--bad)">El panel no usa este plugin porque le falta:</b><ul style="margin:6px 0 0;padding-left:20px">${k.falta.map(x => '<li>' + esc(x) + '</li>').join('')}</ul></div>`}
      <div class="row"><button class="${k.activo ? '' : 'pri'}" data-act="skActivar" data-id="${esc(k.id)}" data-on="${k.activo ? 0 : 1}"${k.valido ? '' : ' disabled'}><i class="ti ti-${k.activo ? 'player-pause' : 'player-play'}"></i> ${k.activo ? 'Desactivar' : 'Activar'}</button>
        <button data-act="skCfg" data-id="${esc(k.id)}"${k.valido ? '' : ' disabled'}><i class="ti ti-adjustments"></i> Configurar (${(k.ajustes || []).length})</button><button data-act="skMej" data-id="${esc(k.id)}"${k.valido ? '' : ' disabled'}><i class="ti ti-sparkles"></i> Mejorar este plugin</button>
        <a href="/api/plugin_zip?id=${encodeURIComponent(k.id)}" download style="padding:0 4px;font-weight:500"><i class="ti ti-download"></i> Descargar</a><span class="muted" style="font-size:12px">${k.archivos} archivos · ${k.mb} MB · ${esc(k.actualizado)}</span><button class="mini" data-act="verPlugin" data-id="${esc(k.id)}">Ver archivos</button></div>
      ${S.pluginLista && S.pluginLista.id === k.id ? `<pre style="margin:12px 0 0;max-height:240px;overflow:auto;font-size:12px;background:var(--side);padding:10px;border-radius:8px">${esc(S.pluginLista.l.join('\n'))}</pre>` : ''}</div></div>`;
  }
  const valorDe = (k, a) => (S.skDraft[k.id] && a.id in S.skDraft[k.id]) ? S.skDraft[k.id][a.id] : k.valores[a.id];
  function campo2(k, a) {
    const id = 'skc_' + a.id, v = valorDe(k, a); let ctl;
    if (a.tipo === 'interruptor') ctl = `<label style="display:flex;gap:10px;align-items:flex-start;margin:0;cursor:pointer"><input type="checkbox" id="${id}" data-aj="${esc(a.id)}" ${v ? 'checked' : ''} style="width:auto;height:auto;margin-top:3px"><span><b style="font-weight:600;color:var(--tx)">${esc(a.etiqueta)}</b><span class="muted" style="display:block;font-size:12.5px;margin-top:2px">${esc(a.ayuda)}</span></span></label>`;
    else {
      const input = a.tipo === 'opcion' ? `<select id="${id}" data-aj="${esc(a.id)}">${(a.opciones || []).map(o => `<option${o === v ? ' selected' : ''}>${esc(o)}</option>`).join('')}</select>`
        : a.tipo === 'numero' ? `<div style="display:flex;gap:8px;align-items:center"><input id="${id}" data-aj="${esc(a.id)}" type="number" step="any" value="${esc(v)}" ${a.min != null ? 'min="' + a.min + '"' : ''} ${a.max != null ? 'max="' + a.max + '"' : ''} style="max-width:130px">${a.unidad ? '<span class="muted">' + esc(a.unidad) + '</span>' : ''}${a.min != null ? `<span class="muted" style="font-size:12px">entre ${a.min} y ${a.max}</span>` : ''}</div>`
        : `<input id="${id}" data-aj="${esc(a.id)}" value="${esc(v)}">`;
      ctl = `<label for="${id}" style="margin:0 0 5px;color:var(--tx);font-weight:600">${esc(a.etiqueta)}</label>${input}<div class="muted" style="font-size:12.5px;margin-top:4px">${esc(a.ayuda)}</div>`;
    }
    return `<div style="padding:12px 0;border-top:1px solid var(--line)">${ctl}</div>`;
  }
  function pintaDrawer(msg) {
    let h = document.getElementById('skDrawerHost'); const sd = S.skDrawer, k = sd && (S.plugins || []).find(x => x.id === sd.id);
    if (!sd || !k) { if (h) h.remove(); return }
    if (!h) { h = document.createElement('div'); h.id = 'skDrawerHost'; document.body.append(h) }
    let cuerpo;
    if (sd.tipo === 'cfg') {
      const grupos = []; k.ajustes.forEach(a => { const g = a.grupo || 'General'; let o = grupos.find(x => x[0] === g); if (!o) grupos.push(o = [g, []]); o[1].push(a) });
      cuerpo = `<p class="muted" style="margin:0 0 6px;font-size:13px">Estos ajustes son del plugin «${esc(k.nombre)}»: cambian cómo se ve y se escucha cada video que genera. El formato y la duración se eligen en el panel al pedir el video.</p>` + grupos.map(([g, L]) => `<div style="margin-top:16px"><div class="grp" style="padding:0 0 6px">${esc(g)}</div>${L.map(a => campo2(k, a)).join('')}</div>`).join('');
    } else {
      cuerpo = `<p class="muted" style="margin:0 0 10px;font-size:13px">Lo que escribas llega a Claude marcado con este plugin. Cambia solo este plugin, guarda una copia antes y sube la versión.</p><textarea id="skm_txt" data-draft="mej" placeholder="Ej: que el gancho de los largos dure 8 segundos" style="min-height:140px">${esc((S.skDraft[k.id] || {}).__mej || '')}</textarea>` +
        ((S.ped || []).filter(x => x.tipo === 'plugin_mejora' && x.plugin === k.id).slice(-4).reverse().map(x => `<div class="note">${chip(x.estado || 'pendiente', x.estado === 'hecho' ? 'ok' : x.estado === 'en_proceso' ? 'acc' : 'warn')} ${esc((x.titulo || '').slice(0, 80))}${x.msg ? ' · ' + esc(x.msg) : ''}</div>`).join(''));
    }
    h.innerHTML = `<div data-act="skCerrar" style="position:fixed;inset:0;background:rgba(10,12,16,.45);z-index:30"></div><aside style="position:fixed;top:0;right:0;bottom:0;width:min(480px,100vw);background:var(--card);border-left:1px solid var(--line);box-shadow:var(--sh2);z-index:31;display:flex;flex-direction:column"><header style="display:flex;align-items:center;gap:10px;padding:16px 20px;border-bottom:1px solid var(--line)"><div style="flex:1"><div style="font-weight:650;font-size:16px">${sd.tipo === 'cfg' ? 'Configurar' : 'Mejorar'} · ${esc(k.nombre)}</div><div class="muted" style="font-size:12.5px">v${esc(k.version)}</div></div><button class="mini" data-act="skCerrar"><i class="ti ti-x"></i> Cerrar</button></header><div style="flex:1;overflow:auto;padding:16px 20px">${cuerpo}</div><footer style="display:flex;gap:10px;align-items:center;padding:14px 20px;border-top:1px solid var(--line)">${sd.tipo === 'cfg' ? `<button class="pri" data-act="skGuardar2" data-id="${esc(k.id)}"><i class="ti ti-device-floppy"></i> Guardar ajustes</button><button data-act="skReset" data-id="${esc(k.id)}">Restablecer</button>` : `<button class="pri" data-act="skEnviar" data-id="${esc(k.id)}"><i class="ti ti-send"></i> Enviar mejora</button>`}<span id="skMsg" style="font-size:12.5px;color:var(--ok)">${msg ? esc(msg) : ''}</span></footer></aside>`;
  }
  const leeForm = k => { const v = {}; document.querySelectorAll('#skDrawerHost [data-aj]').forEach(el => { const a = k.ajustes.find(x => x.id === el.dataset.aj); v[a.id] = a.tipo === 'interruptor' ? el.checked : el.value }); return v };
  document.addEventListener('input', e => { const el = e.target; if (!S.skDrawer) return; const k = (S.plugins || []).find(x => x.id === S.skDrawer.id); if (!k) return; (S.skDraft[k.id] = S.skDraft[k.id] || {}); if (el.dataset && el.dataset.aj) S.skDraft[k.id][el.dataset.aj] = el.type === 'checkbox' ? el.checked : el.value; else if (el.id === 'skm_txt') S.skDraft[k.id].__mej = el.value });
  document.addEventListener('change', e => { const el = e.target; if (el && el.dataset && el.dataset.aj && S.skDrawer) { const k = (S.plugins || []).find(x => x.id === S.skDrawer.id); if (k) { (S.skDraft[k.id] = S.skDraft[k.id] || {})[el.dataset.aj] = el.type === 'checkbox' ? el.checked : el.value } } });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && S.skDrawer) { S.skDrawer = null; pintaDrawer() } });
  document.addEventListener('click', async e => { const b = e.target.closest('[data-act]'); if (!b) return; const a = b.dataset.act, id = b.dataset.id; const k = (S.plugins || []).find(x => x.id === (id || (S.skDrawer || {}).id));
    if (a === 'skCfg' || a === 'skMej') { S.skDrawer = { id, tipo: a === 'skCfg' ? 'cfg' : 'mej' }; pintaDrawer() }
    else if (a === 'skCerrar') { S.skDrawer = null; pintaDrawer() }
    else if (a === 'skReset' && k) { delete S.skDraft[k.id]; k.ajustes.forEach(x => { (S.skDraft[k.id] = S.skDraft[k.id] || {})[x.id] = x.defecto }); pintaDrawer('Valores por defecto puestos: pulsa Guardar'); }
    else if (a === 'skGuardar2' && k) { const r = await api('/api/plugin_ajustes', { id: k.id, valores: leeForm(k) }); if (r && r.error) { pintaDrawer(); const m = document.getElementById('skMsg'); if (m) { m.style.color = 'var(--bad)'; m.textContent = r.error } return } delete S.skDraft[k.id]; const n = await api('/api/plugins'); if (Array.isArray(n)) S.plugins = n; pintaDrawer('Guardado ✓'); toast('Ajustes del plugin guardados') }
    else if (a === 'skEnviar' && k) { const el = document.getElementById('skm_txt'); const tx = el && el.value.trim(); if (!tx) { const m = document.getElementById('skMsg'); if (m) { m.style.color = 'var(--bad)'; m.textContent = 'Escribe qué quieres mejorar.' } return } const r = await api('/api/plugin_mejora', { id: k.id, texto: tx }); if (r && r.error) { alert(r.error); return } if (S.skDraft[k.id]) delete S.skDraft[k.id].__mej; const g = await api('/api/pedidos'); if (Array.isArray(g)) S.ped = g; pintaDrawer('Enviado a Claude ✓'); toast('Enviado a Claude: mejora del plugin') } }, true);

  /* ---------- INSTALACIÓN del DevIAs Panel: .bat de encendido e instalador descargable ---------- */
  function instCard() { const i = S.inst; if (!i) return '';
    return `<div class="panel"><header><h2>Instalación del DevIAs Panel</h2><div class="r">${i.bat_existe ? chip('.bat de encendido listo', 'ok') : chip('Falta generar el .bat', 'warn')}</div></header><div class="body"><p style="margin:0 0 10px" class="muted">El DevIAs Panel se instala como un paquete: al ejecutar el instalador genera un <b>.bat</b> para encenderlo a mano, con las rutas de la carpeta donde esté.</p>
      <div class="row" style="margin-bottom:10px;font-size:13px"><span class="muted">Carpeta:</span> <code>${esc(i.ruta)}</code> <span class="muted">· Puerto:</span> <code>${esc(i.puerto)}</code>${i.instalado ? ' <span class="muted">· instalado ' + esc(i.instalado) + '</span>' : ''}</div>
      <div class="row"><button class="pri" data-act="instGenerar"><i class="ti ti-file-code"></i> Generar el .bat de encendido</button><button data-act="instGenerar" data-lnk="1"><i class="ti ti-device-desktop"></i> + Acceso directo en el escritorio</button><a href="/api/devpanel_zip" download style="padding:0 4px;font-weight:500"><i class="ti ti-download"></i> Descargar el instalador (.zip)</a></div>
      ${S.instMsg ? `<pre style="margin:12px 0 0;max-height:180px;overflow:auto;font-size:12px;background:var(--side);padding:10px;border-radius:8px">${esc(S.instMsg)}</pre>` : ''}</div></div>`; }
  /* ---------- CICLO DE VIDA: instalar plugin desde .zip, actualizar, desinstalar ---------- */
  const informeHtml = inf => { if (!inf) return ''; const g = {}; inf.checks.forEach(c => (g[c.grupo] = g[c.grupo] || []).push(c)); const mal = inf.checks.filter(c => !c.ok).length;
    return `<div style="margin-top:14px;border:1px solid var(--${inf.ok ? 'ok' : 'bad'});border-radius:10px;padding:12px 14px"><div style="font-weight:650;margin-bottom:8px;color:var(--${inf.ok ? 'ok' : 'bad'})">${inf.ok ? '✓ ' : '✗ '}${esc(inf.titulo || '')} — ${inf.ok ? 'cumple la estructura del DevIAs Panel (' + inf.checks.length + ' comprobaciones)' : mal + ' fallo' + (mal > 1 ? 's' : '') + ': NO se instaló'}</div><div style="max-height:280px;overflow:auto;font-size:12.5px">${Object.entries(g).map(([k, L]) => `<div style="margin:6px 0 2px;font-weight:600">${esc(k)}</div>` + L.map(c => `<div style="color:var(--${c.ok ? 'tx' : 'bad'})">${c.ok ? '✓' : '✗'} ${esc(c.texto)}</div>`).join('')).join('')}</div><div style="margin-top:8px"><button class="mini" data-act="plgCierraInf">Cerrar informe</button></div></div>`; };
  const PASOS_REV = ['Leyendo el archivo .zip', 'Buscando plugin.json', '¿Es un plugin del DevIAs Panel?', 'Comprobando esqueleto y archivos', 'Comprobando scripts (ideas, voz, títulos, pipeline)', 'Comprobando ajustes'];
  const GRUPOS_REV = [['Esqueleto', ['Ficha', 'Esqueleto']], ['Archivos declarados', ['Archivos']], ['Scripts', ['Pipeline', 'Voz', 'Ideas', 'Títulos']], ['Ajustes', ['Ajustes', 'Requisitos']]];
  const spin = '<span class="plgSpin"></span>';
  function revHtml() {
    const R = S.plgRev; if (!R) return '';
    const pasos = PASOS_REV.map((t, k) => { const hecho = R.res ? true : k < R.paso, activo = !R.res && k === R.paso; let ic = hecho ? '<b style="color:var(--ok)">✓</b>' : activo ? spin : '<span class="muted">○</span>';
      if (R.res && R.res.tipo === 'no-zip') ic = k === 0 ? '<b style="color:var(--bad)">✗</b>' : '<span class="muted">—</span>';
      else if (R.res && !R.res.es_plugin && k >= 2) ic = k === 2 ? '<b style="color:var(--bad)">✗</b>' : '<span class="muted">—</span>';
      if (R.res && R.res.es_plugin && k >= 3 && R.res.informe) { const g = GRUPOS_REV[k - 3 > 2 ? 3 : k - 3]; const L = R.res.informe.filter(c => g[1].includes(c.grupo)); if (L.some(c => !c.ok)) ic = '<b style="color:var(--bad)">✗</b>' }
      return `<div style="display:flex;gap:10px;align-items:center;padding:3px 0;opacity:${hecho || activo ? 1 : .45}"><span style="width:18px;text-align:center">${ic}</span><span>${esc(t)}</span></div>` }).join('');
    let fin = '';
    if (R.res) { const r = R.res, bien = r.es_plugin && r.ok;
      const det = r.informe ? informeHtml({ ok: r.ok, titulo: r.nombre || '', checks: r.informe }).replace('Cerrar informe', 'Ocultar') .replace(/<div style="margin-top:8px"><button[^]*?<\/button><\/div>/, '') : '';
      fin = `<div style="margin-top:12px;padding:12px 14px;border-radius:10px;border:1px solid var(--${bien ? 'ok' : 'bad'});background:var(--card)"><div style="font-weight:650;color:var(--${bien ? 'ok' : 'bad'})">${bien ? '✓ ' : '✗ '}${esc(r.mensaje)}</div>${r.es_plugin ? `<div style="margin-top:6px"><b>${esc(r.nombre)}</b> <span class="muted">v${esc(r.version)} · id ${esc(r.id)}${r.existe ? ' · ya instalado (v' + esc(r.version_instalada) + ')' : ''}</span><div class="muted" style="font-size:12.5px">${esc(r.descripcion || '')}</div></div>` : ''}
        <div class="row" style="margin-top:10px">${bien ? `<button class="pri" data-act="plgConfirmar" data-act2="${r.existe ? 'act' : 'ins'}"><i class="ti ti-${r.existe ? 'refresh' : 'download'}"></i> ${r.existe ? 'Actualizar a v' + esc(r.version) : 'Instalar este plugin'}</button>` : ''}<button data-act="plgCancelar">${bien ? 'Cancelar' : 'Cerrar'}</button><span id="plgMsg" class="muted" style="font-size:12.5px"></span></div></div>${det}`; }
    return `<div style="margin-top:14px;border:1px solid var(--line);border-radius:10px;padding:12px 14px"><div style="font-weight:650;margin-bottom:6px">Revisando «${esc(R.nombre)}» antes de instalar</div>${pasos}${fin}</div>`;
  }
  const instPluginCard = () => `<style>.plgSpin{display:inline-block;width:14px;height:14px;border:2px solid var(--line);border-top-color:var(--acc);border-radius:50%;animation:plgG .7s linear infinite}@keyframes plgG{to{transform:rotate(360deg)}}</style><div class="panel"><header><h2>Instalar un plugin</h2><div class="r">${chip('API del panel: 1', '')}</div></header><div class="body"><p class="muted" style="margin:0 0 10px">Elige el <b>.zip</b> de un plugin. El DevIAs Panel lo lee primero, detecta si es un plugin y si cumple la estructura; solo entonces te deja instalarlo. Si ya existe, te ofrece actualizarlo (la versión anterior queda en <b>_papelera</b>).</p><div class="row"><input type="file" id="plgZip" accept=".zip" style="max-width:340px"${S.plgRev && !S.plgRev.res ? ' disabled' : ''}><span id="plgMsg0" class="muted" style="font-size:12.5px"></span></div>${revHtml()}${informeHtml(S.plgInforme)}</div></div>`;
  const plgMsg = (t, bad) => { const m = document.getElementById('plgMsg'); if (m) { m.style.color = bad ? 'var(--bad)' : 'var(--ok)'; m.textContent = t } };
  const leeZip = f => new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(String(r.result).split(',')[1]); r.onerror = no; r.readAsDataURL(f) });
  document.addEventListener('change', async e => { const el = e.target; if (!el || el.id !== 'plgZip' || !el.files || !el.files[0]) return; const f = el.files[0]; S.plgInforme = null;
    S.plgRev = { nombre: f.name, paso: 0, res: null, zip: null }; render(); const R = S.plgRev;
    const tk = setInterval(() => { if (S.plgRev === R && !R.res && R.paso < 4) { R.paso++; render() } }, 420);
    let res; try { R.zip = await leeZip(f); const [r] = await Promise.all([api('/api/plugin_revisar', { zip_b64: R.zip }), new Promise(ok => setTimeout(ok, 2000))]); res = r } catch (x) { res = { es_plugin: false, ok: false, mensaje: 'No pude leer el archivo.' } }
    clearInterval(tk); if (S.plgRev === R) { R.res = res || { es_plugin: false, ok: false, mensaje: 'Sin respuesta del panel.' }; render() } });
  document.addEventListener('click', async e => { const b = e.target.closest('[data-act]'); if (!b) return; const a = b.dataset.act;
    if (a === 'plgCancelar') { S.plgRev = null; render() }
    else if (a === 'plgConfirmar' && S.plgRev && S.plgRev.zip) { const R = S.plgRev; b.disabled = true; const r = await api('/api/plugin_instalar_zip', { zip_b64: R.zip, actualizar: b.dataset.act2 === 'act' });
      if (r && r.ok) { toast((r.actualizado ? 'Plugin actualizado' : 'Plugin instalado') + ' (v' + r.version + '). Actívalo cuando quieras.'); S.plgRev = null; const n = await api('/api/plugins'); if (Array.isArray(n)) S.plugins = n; render() } else { b.disabled = false; plgMsg((r && r.error) || 'No se pudo instalar', true) } }
    else if (a === 'plgSubir') { const f = (document.getElementById('plgZip') || {}).files && document.getElementById('plgZip').files[0]; if (!f) return plgMsg('Elige un archivo .zip.', true);
      let r = await api('/api/plugin_instalar_zip', { zip_b64: await leeZip(f) });
      if (r && r.existe && confirm((r.error || '') + '\n\n¿Actualizar? La versión anterior se guarda en _papelera.')) r = await api('/api/plugin_instalar_zip', { zip_b64: await leeZip(f), actualizar: true });
      if (r && r.informe) S.plgInforme = { ok: !!r.ok, titulo: 'Paquete «' + f.name + '»', checks: r.informe };
      if (r && r.ok) { toast((r.actualizado ? 'Plugin actualizado' : 'Plugin instalado') + ' (v' + r.version + '). Actívalo cuando quieras.'); const n = await api('/api/plugins'); if (Array.isArray(n)) S.plugins = n; render() } else { render(); plgMsg((r && r.error) || 'No se pudo instalar', true) } }
    else if (a === 'plgCierraInf') { S.plgInforme = null; render() }
    else if (a === 'plgVerificar') { const r = await api('/api/plugin_verificar?id=' + encodeURIComponent(b.dataset.id)); if (r && r.checks) { S.plgInforme = { ok: r.ok, titulo: 'Plugin instalado «' + b.dataset.id + '»', checks: r.checks }; render(); window.scrollTo(0, 0) } }
    else if (a === 'plgBorrar') { const k = (S.plugins || []).find(x => x.id === b.dataset.id); if (!k || !confirm('¿Desinstalar «' + k.nombre + '»?\nSe guarda una copia en la carpeta _papelera (se puede recuperar). Los videos ya hechos con él se conservan, pero no podrás generar voz, unir ni títulos hasta reinstalarlo.')) return;
      const r = await api('/api/plugin_desinstalar', { id: k.id }); if (r && r.ok) { toast('Plugin desinstalado'); const n = await api('/api/plugins'); S.plugins = Array.isArray(n) ? n : []; render() } else alert((r && r.error) || 'No se pudo desinstalar') } }, true);
  const tarjetaPlugin0 = tarjetaPlugin;
  tarjetaPlugin = k => tarjetaPlugin0(k).replace(/(<span class="muted" style="font-size:12px">\d+ archivos)/, `<button class="mini" data-act="plgVerificar" data-id="${esc(k.id)}"><i class="ti ti-checklist"></i> Verificar</button><button class="mini" data-act="plgBorrar" data-id="${esc(k.id)}"${k.activo ? ' disabled title="Desactívalo primero"' : ''}><i class="ti ti-trash"></i> Desinstalar</button>$1`);
  /* ---------- LISTA DE PLUGINS EN TARJETAS (con portada; sin imagen el panel dibuja una por defecto) ---------- */
  const PLG_CSS = `<style>.plgGrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:16px;margin:0 0 16px}.plgCard{background:var(--card);border:1px solid var(--line);border-radius:14px;overflow:hidden;display:flex;flex-direction:column;box-shadow:var(--sh1,none)}.plgCard.act{border-color:var(--acc);box-shadow:0 0 0 1px var(--acc)}.plgCover{height:132px;position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden}.plgCover img{width:100%;height:100%;object-fit:cover}.plgCover .ini{font-size:46px;font-weight:750;letter-spacing:2px;color:rgba(255,255,255,.95);text-shadow:0 2px 12px rgba(0,0,0,.25)}.plgCover .pz{position:absolute;right:10px;bottom:8px;font-size:20px;color:rgba(255,255,255,.7)}.plgCover .tag{position:absolute;left:10px;top:10px}.plgBody{padding:14px 16px;flex:1;display:flex;flex-direction:column;gap:8px}.plgBody p{margin:0;font-size:13.5px;line-height:1.45;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.plgAct{padding:12px 16px;border-top:1px solid var(--line);display:flex;flex-wrap:wrap;gap:8px;align-items:center}.plgIco{padding:5px 8px}</style>`;
  const hueDe = t => { let h = 0; for (const c of String(t)) h = (h * 31 + c.charCodeAt(0)) % 360; return h };
  const iniciales = n => (String(n).split(/[\s\-]+/).filter(Boolean).slice(0, 2).map(w => w[0]).join('') || '?').toUpperCase();
  function portadaPlugin(k) {
    const h = hueDe(k.id), fondo = `linear-gradient(135deg,hsl(${h} 62% 46%),hsl(${(h + 48) % 360} 66% 34%))`;
    const tag = k.activo ? `<span class="tag">${chip('Activo', 'acc')}</span>` : '';
    return k.imagen ? `<div class="plgCover" style="background:${fondo}"><img src="/api/plugin_imagen?id=${encodeURIComponent(k.id)}&t=${esc(k.actualizado)}" alt="">${tag}</div>`
      : `<div class="plgCover" style="background:${fondo}"><span class="ini">${esc(iniciales(k.nombre))}</span><i class="ti ti-puzzle pz"></i>${tag}</div>`;
  }
  tarjetaPlugin = k => {
    const faltan = (k.requisitos || []).filter(r => !r.ok), pip = faltan.filter(r => r.tipo === 'python'), fm = (k.formatos || []).map(f => chip(f.nombre + ' · ' + f.aspecto, '')).join(' ');
    const lista = S.pluginLista && S.pluginLista.id === k.id ? `<pre style="margin:0;max-height:200px;overflow:auto;font-size:11.5px;background:var(--side);padding:8px;border-radius:8px">${esc(S.pluginLista.l.join('\n'))}</pre>` : '';
    return `<div class="plgCard${k.activo ? ' act' : ''}">${portadaPlugin(k)}<div class="plgBody">
      <div style="display:flex;align-items:baseline;gap:8px"><b style="font-size:16px;flex:1">${esc(k.nombre)}</b><span class="muted" style="font-size:12px">v${esc(k.version)}</span></div>
      <div class="row" style="gap:6px">${k.valido ? chip('Cumple el esqueleto', 'ok') : chip('No cumple el esqueleto', 'bad')} ${k.valido ? fm : ''}</div>
      <p class="muted">${esc(k.desc)}</p>
      ${k.valido ? (faltan.length ? `<div class="note" style="font-size:12.5px">Falta: ${faltan.map(r => esc(r.nombre)).join(', ')}${pip.length ? ` <button class="mini" data-act="skInstalar" data-id="${esc(k.id)}">Instalar paquetes</button>` : ''}</div>` : '')
        : `<div style="border:1px solid var(--bad);background:var(--badbg);border-radius:8px;padding:8px 10px;font-size:12.5px"><b style="color:var(--bad)">No se usa porque le falta:</b><ul style="margin:4px 0 0;padding-left:18px">${(k.falta || []).slice(0, 4).map(x => '<li>' + esc(x) + '</li>').join('')}${(k.falta || []).length > 4 ? '<li>… y ' + ((k.falta || []).length - 4) + ' más (botón Verificar)</li>' : ''}</ul></div>`}
      <div class="muted" style="font-size:12px;margin-top:auto">${k.archivos} archivos · ${k.mb} MB · ${esc(k.actualizado)}</div>${lista}</div>
      <div class="plgAct"><button class="${k.activo ? '' : 'pri'}" data-act="skActivar" data-id="${esc(k.id)}" data-on="${k.activo ? 0 : 1}"${k.valido ? '' : ' disabled'}><i class="ti ti-${k.activo ? 'player-pause' : 'player-play'}"></i> ${k.activo ? 'Desactivar' : 'Activar'}</button>
        <button data-act="skCfg" data-id="${esc(k.id)}"${k.valido ? '' : ' disabled'} title="Configurar"><i class="ti ti-adjustments"></i> Configurar</button>
        <button class="mini plgIco" data-act="skMej" data-id="${esc(k.id)}"${k.valido ? '' : ' disabled'} title="Mejorar este plugin"><i class="ti ti-sparkles"></i></button>
        <button class="mini plgIco" data-act="plgVerificar" data-id="${esc(k.id)}" title="Verificar estructura"><i class="ti ti-checklist"></i></button>
        <a class="mini plgIco" href="/api/plugin_zip?id=${encodeURIComponent(k.id)}" download title="Descargar .zip" style="border:1px solid var(--line);border-radius:8px;display:inline-flex"><i class="ti ti-download"></i></a>
        <button class="mini plgIco" data-act="verPlugin" data-id="${esc(k.id)}" title="Ver archivos"><i class="ti ti-folder"></i></button>
        <button class="mini plgIco" data-act="plgBorrar" data-id="${esc(k.id)}"${k.activo ? ' disabled title="Desactívalo primero"' : ' title="Desinstalar"'}><i class="ti ti-trash"></i></button></div></div>`;
  };
  const vSk0 = VIEWS.plugins;
  VIEWS.plugins = function () { if (!S.inst) api('/api/instalacion').then(r => { if (r && !r.error) { S.inst = r; if (S.p === 'plugins') render() } }); return instCard() + instPluginCard() + vSk0(); };
  document.addEventListener('click', async e => { const b = e.target.closest('[data-act="instGenerar"]'); if (!b) return; b.disabled = true; const r = await api('/api/instalar', { acceso_directo: !!b.dataset.lnk }); b.disabled = false; S.inst = (r && r.info) || S.inst; S.instMsg = r && (r.salida || r.error) || ''; toast(r && r.ok ? 'Listo: .bat de encendido generado' : 'No se pudo generar el .bat'); render() }, true);

  function avisoBorrador(l) { const d = document.createElement('div'); d.style.cssText = 'position:fixed;right:20px;bottom:70px;max-width:min(420px,92vw);background:var(--card);color:var(--tx);border:1px solid var(--ok);border-left:6px solid var(--ok);border-radius:12px;padding:14px 16px;box-shadow:var(--sh2);z-index:40;font-size:13.5px';
    d.innerHTML = `<div style="display:flex;gap:10px;align-items:flex-start"><i class="ti ti-movie" style="font-size:22px;color:var(--ok)"></i><div style="flex:1"><b>Cambios en el borrador</b><div style="margin-top:3px">${esc(l.msg)}</div><div class="row" style="margin-top:10px"><button class="pri mini" data-act="verCambio" data-id="${esc(l.proyecto || '')}"><i class="ti ti-player-play"></i> Ver el video</button><button class="mini" data-act="cerrarAviso">Cerrar</button></div></div></div>`; document.body.append(d); setTimeout(() => d.remove(), 30000); }
  document.addEventListener('click', async e => { const b = e.target.closest('[data-act="verCambio"],[data-act="cerrarAviso"]'); if (!b) return; const box = b.closest('div[style*="position:fixed"]'); if (b.dataset.act === 'verCambio' && b.dataset.id) { await cargar(true); S.p = 'videos'; S.sel = b.dataset.id; S.vista = 'borradorvoz'; try { render(); const g = await api('/api/guion?id=' + encodeURIComponent(b.dataset.id)); if (Array.isArray(g)) { S.guion = g; render() } } catch (er) { } } if (box) box.remove() }, true);

  /* ---------- video de un plugin DESACTIVADO: nada del plugin se usa; aviso claro ---------- */
  const avisoPluginOff = (p, txt) => `<div class="panel" style="border-color:var(--warn);margin-bottom:14px"><div class="body" style="display:flex;gap:12px;align-items:center"><i class="ti ti-puzzle" style="font-size:24px;color:var(--warn)"></i><div style="flex:1"><b>Este video es del plugin «${esc(p.plugin)}», que está desactivado</b><div class="muted">${esc(txt || 'Mientras esté desactivado no se genera voz, unión, regrabado ni títulos de este video, para no mezclarlo con otro plugin. Actívalo en Plugins.')}</div></div><button class="pri" data-act="nav" data-p="plugins">Ir a Plugins</button></div></div>`;
  /* ---------- BORRAR un video (a la papelera, recuperable) ---------- */
  const btnBorrar = (id, txt) => `<button class="mini" data-act="borrarVideo" data-id="${esc(id)}" title="Borrar este video (va a la papelera)" style="color:var(--bad)"><i class="ti ti-trash"></i>${txt || ''}</button>`;
  /* ---------- AJUSTES · VOZ del DevIAs Panel (un solo motor para todos los plugins) ---------- */
  function vozCard() {
    const V = S.voces;
    if (!V) { api('/api/voces').then(r => { if (r && !r.error) { S.voces = r; S.vozCfg = r.config; S.vozSel = { motor: r.config.motor, id: r.config.perfil }; if (S.p === 'ajustes') render() } }); return '' }
    const c = S.vozCfg || V.config, vs = V.vs || {}, vsOn = !!vs.activo, tab = S.vozTab || (vsOn ? 'vs' : 'local');
    const icono = m => ({ kokoro: 'ti-cpu', piper: 'ti-feather', clon: 'ti-microphone-2', edge: 'ti-world', voicestudio: 'ti-wave-sine' })[m] || 'ti-feather';
    const actual = V.voces.find(v => v.id === c.perfil && v.motor === c.motor);
    const tarjeta = v => { const enUso = v.id === c.perfil && v.motor === c.motor, off = v.instalada ? '' : ' disabled';
      return `<div style="flex:0 0 calc((100% - 42px) / 4);min-width:240px;box-sizing:border-box;scroll-snap-align:start;display:flex;flex-direction:column;gap:10px;padding:14px;background:${enUso ? 'rgba(34,197,94,.07)' : 'transparent'};border:${enUso ? '2px solid var(--ok, #22c55e)' : '1px solid var(--line)'};border-radius:12px;opacity:${v.instalada ? 1 : .55}">
        <div style="display:flex;gap:10px;align-items:center;min-height:42px"><i class="ti ${icono(v.motor)}" style="font-size:24px;color:var(--acc);flex:none"></i><div style="min-width:0"><div style="font-weight:700;line-height:1.25">${esc(v.nombre)}</div><div class="muted" style="font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(v.id)}</div></div></div>
        <div style="display:flex;flex-wrap:wrap;gap:6px 8px;align-items:center;min-height:44px;align-content:flex-start">${chip(v.motor_txt, 'acc')}<span class="muted" style="font-size:12.5px;flex-basis:100%">${esc(v.donde)}${v.instalada ? '' : ' · sin instalar'}</span></div>
        <div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:auto"><button class="mini" data-act="vozEscuchar" data-m="${esc(v.motor)}" data-id="${esc(v.id)}"${off}><i class="ti ti-player-play"></i> Escuchar</button>${enUso ? '<button class="mini pri" tabindex="-1" style="opacity:1;cursor:default"><i class="ti ti-check"></i> Usando</button>' : `<button class="mini" data-act="vozUsar" data-m="${esc(v.motor)}" data-id="${esc(v.id)}"${off}>Usar esta voz</button>`}${v.borrable ? `<button class="mini" data-act="vozBorrar" data-m="${esc(v.motor)}" data-id="${esc(v.id)}" title="Borrar esta voz" style="color:var(--bad)"><i class="ti ti-trash"></i></button>` : ''}</div></div>` };
    const fila = lista => `<div style="position:relative;padding:0 26px"><div id="vz_fila" style="display:flex;gap:14px;overflow-x:auto;scroll-snap-type:x mandatory;scroll-behavior:smooth;scrollbar-width:none;padding:2px">${lista.map(tarjeta).join('')}</div>
        <button class="mini" data-act="vozFlecha" data-d="-1" title="Anteriores" style="position:absolute;left:-6px;top:50%;transform:translateY(-50%);width:36px;height:36px;border-radius:50%;padding:0;background:var(--card);box-shadow:0 2px 8px rgba(0,0,0,.4)"><i class="ti ti-chevron-left"></i></button>
        <button class="mini" data-act="vozFlecha" data-d="1" title="Siguientes" style="position:absolute;right:-6px;top:50%;transform:translateY(-50%);width:36px;height:36px;border-radius:50%;padding:0;background:var(--card);box-shadow:0 2px 8px rgba(0,0,0,.4)"><i class="ti ti-chevron-right"></i></button></div>`;
    const locales = V.voces.filter(v => v.motor !== 'voicestudio'), perfiles = V.voces.filter(v => v.motor === 'voicestudio');
    const motorBtn = (t, ic, titulo, sub) => { const sel = tab === t, usando = (t === 'vs') === vsOn;
      return `<button data-act="vozMotor" data-t="${t}" style="flex:1;min-width:260px;height:auto;text-align:left;display:flex;gap:12px;align-items:flex-start;padding:14px 16px;border-radius:12px;cursor:pointer;color:inherit;font:inherit;border:${sel ? '2px solid var(--acc)' : '1px solid var(--line)'};background:${sel ? 'rgba(99,102,241,.10)' : 'transparent'}">
        <i class="ti ${ic}" style="font-size:26px;color:var(--acc);flex:none"></i><div><div style="font-weight:700;font-size:15px">${titulo}</div><div class="muted" style="font-size:12.5px;margin-top:2px">${sub}</div>${usando ? `<div style="margin-top:8px">${chip('Usando ahora', 'ok')}</div>` : ''}</div></button>` };
    const carpetaVs = `<div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center"><input id="vs_dir" value="${esc(vs.instalado ? vs.dir : '')}" placeholder="Carpeta «project» de Voice Studio (la que tiene backend y .venv)" style="flex:1;min-width:260px"><button class="mini" data-act="vsGuardarDir">Guardar carpeta</button><button class="mini" data-act="vsBuscar"><i class="ti ti-search"></i> Buscar en el PC</button></div>`;
    let cuerpo;
    if (tab === 'local') cuerpo = `${fila(locales)}
      <div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:14px"><span class="muted" style="font-size:12.5px;font-weight:600;margin-right:4px">Tus voces:</span><button class="mini" data-act="vozCarpeta"><i class="ti ti-folder-open"></i> Abrir carpeta</button><button class="mini" data-act="vozBuscar"><i class="ti ti-refresh"></i> Buscar voces</button></div>`;
    else if (!vs.instalado) cuerpo = `<div style="padding:16px;border:1px dashed var(--acc);border-radius:12px"><div style="font-weight:700;margin-bottom:4px">Primero indica dónde está Voice Studio</div><div class="muted" style="font-size:12.5px;margin-bottom:12px">Pulsa «Buscar en el PC» o escribe la carpeta donde lo instalaste.</div>${carpetaVs}<div id="vsMsg" class="muted" style="font-size:12.5px;margin-top:8px"></div></div>`;
    else cuerpo = `<div style="display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;padding:12px 14px;border:1px solid var(--line);border-radius:12px;margin-bottom:14px">
        <div><div style="font-weight:700">Voice Studio está ${vs.arriba ? '<span style="color:var(--ok, #22c55e)">● encendido</span>' : '<span class="muted">● apagado</span>'}</div><div class="muted" style="font-size:12.5px;margin-top:2px">${vs.arriba ? 'Usa unos 5 GB de tu tarjeta de video. Apágalo si no vas a generar voz.' : 'Se enciende solo cuando generas la voz. También puedes encenderlo ahora.'}</div></div>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="mini" data-act="vsDetectar" title="Vuelve a leer los perfiles de voz que ya tienes en Voice Studio"><i class="ti ti-radar-2"></i> Detectar perfiles de voz</button><button class="mini${vs.arriba ? '' : ' pri'}" data-act="vsPower" data-on="${vs.arriba ? 1 : 0}"><i class="ti ti-power"></i> ${vs.arriba ? 'Apagar Voice Studio' : 'Encender Voice Studio'}</button></div></div>
      <div class="muted" style="font-size:12.5px;margin:-4px 0 12px">${vs.perfiles ? 'Perfiles de voz detectados en tu Voice Studio: ' + vs.perfiles : 'No se detectaron perfiles de voz en esa carpeta.'}</div>
      ${vsOn ? fila(perfiles) : `<div style="padding:14px;border:1px dashed var(--line);border-radius:12px"><span style="font-size:13px">Voice Studio todavía no es el motor de tus videos.</span> <button class="mini pri" data-act="vsActivar" style="margin-left:8px">Usar Voice Studio</button></div>`}
      <details style="margin-top:14px"><summary class="muted" style="cursor:pointer;font-size:12.5px">Cambiar la carpeta de Voice Studio</summary><div style="margin-top:8px">${carpetaVs}</div></details>
      <div id="vsMsg" class="muted" style="font-size:12.5px;margin-top:8px"></div>`;
    return `<div class="panel" data-keep-claude style="margin-top:14px"><header><h2>Voz del DevIAs Panel</h2></header><div class="body">
      <div style="display:flex;align-items:center;gap:12px;padding:12px 16px;border-radius:12px;background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.35);margin-bottom:16px"><i class="ti ti-microphone-2" style="font-size:24px;color:var(--ok, #22c55e)"></i><div><div class="muted" style="font-size:12px">Tus videos hablan ahora con</div><div style="font-weight:700;font-size:15px">${esc(actual ? actual.nombre : c.perfil)} <span class="muted" style="font-weight:400;font-size:13px">· ${esc(actual ? actual.motor_txt : '')}</span></div></div></div>
      <div style="font-weight:700;margin-bottom:2px">1. Elige el motor</div><div class="muted" style="font-size:12.5px;margin-bottom:10px">Se usa uno a la vez. Toca el otro cuando quieras cambiar.</div>
      <div style="display:flex;flex-wrap:wrap;gap:12px;margin-bottom:20px">${motorBtn('local', 'ti-device-desktop', 'Voces del panel', 'Piper, Kokoro y Jorge. No necesitan ningún programa aparte.')}${motorBtn('vs', 'ti-wave-sine', 'Voice Studio', 'Tus propios perfiles de voz (programa aparte).')}</div>
      <div style="font-weight:700;margin-bottom:10px">2. Elige la voz</div>
      ${cuerpo}
      <div style="margin-top:24px;padding-top:16px;border-top:1px solid var(--line)">
        <div style="font-weight:700;margin-bottom:10px">Configuración general <span class="muted" style="font-weight:400;font-size:12.5px">· vale para todas las voces</span></div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px">
          <div><label for="vz_vel" style="font-weight:600;display:block;margin-bottom:4px">Velocidad</label><input id="vz_vel" type="number" step="0.01" min="0.8" max="1.4" value="${esc(c.velocidad ?? 1.1)}" style="max-width:120px"><div class="muted" style="font-size:12.5px;margin-top:4px">Entre 0.8 y 1.4 (1.0 = normal). «Escuchar» usa esta velocidad.</div></div>
          <div><label for="vz_pausa" style="font-weight:600;display:block;margin-bottom:4px">Pausa entre frases</label><input id="vz_pausa" type="number" min="150" max="900" value="${esc(c.pausa_ms ?? 400)}" style="max-width:120px"> <span class="muted">ms</span><div class="muted" style="font-size:12.5px;margin-top:4px">Si la frase no trae su propia pausa.</div></div></div>
        <div class="row" style="margin-top:14px;gap:12px;align-items:center"><button class="pri" data-act="vozGuardar"><i class="ti ti-device-floppy"></i> Guardar configuración</button><button class="mini" data-act="vozDefecto" title="Velocidad 1.1 y pausa 400 ms"><i class="ti ti-restore"></i> Valores predeterminados</button><span id="vzMsg" class="muted" style="font-size:12.5px;overflow-wrap:anywhere"></span></div></div></div></div>`;
  }
  const vAj0 = VIEWS.ajustes; VIEWS.ajustes = function () { return vAj0() + agenteCard() + vozCard() };
  function agenteCard() {
    const A = S.agente;
    if (!A) { api('/api/agente').then(r => { if (r && !r.error) { S.agente = r; if (S.p === 'ajustes') render() } }); return '' }
    const btn = (id, ic, titulo, sub) => { const sel = A.activo === id;
      return `<button data-act="agenteSel" data-id="${id}" style="flex:1;min-width:240px;height:auto;text-align:left;display:flex;gap:12px;align-items:flex-start;padding:14px 16px;border-radius:12px;cursor:pointer;color:inherit;font:inherit;border:${sel ? '2px solid var(--acc)' : '1px solid var(--line)'};background:${sel ? 'rgba(99,102,241,.10)' : 'transparent'}"><i class="ti ${ic}" style="font-size:26px;color:var(--acc);flex:none"></i><div><div style="font-weight:700;font-size:15px">${titulo}</div><div class="muted" style="font-size:12.5px;margin-top:2px">${sub}</div>${sel ? `<div style="margin-top:8px">${chip('Recibe los pedidos', 'ok')}</div>` : ''}</div></button>` };
    return `<div class="panel" data-keep-claude style="margin-top:14px"><header><h2>¿Quién atiende los pedidos?</h2></header><div class="body"><p class="muted" style="margin:0 0 12px">Elige uno: los pedidos llegan solo a ese, el otro no recibe nada. Cámbialo cuando quieras, por ejemplo si a Claude se le acaba el uso.</p>
      <div style="display:flex;flex-wrap:wrap;gap:12px">${btn('claude', 'ti-sparkles', 'Claude', 'Claude Code, como siempre. Desactiva a Codex.')}${btn('codex', 'ti-terminal-2', 'Codex (ChatGPT)', 'Codex CLI de OpenAI, abierto en la carpeta del panel. Desactiva a Claude.')}</div>
      <div id="agMsg" class="muted" style="font-size:12.5px;margin-top:10px">${A.activo === 'codex' ? 'Abre Codex en la carpeta del panel y escríbele «devias». Claude no recibirá pedidos.' : 'Escribe «devias» en Claude para conectarlo. Codex no recibirá pedidos.'}</div></div></div>`;
  }
  document.addEventListener('click', e => { if (e.target.closest('[data-act=irAjustesAgente]')) { const n = document.querySelector('.nav[data-p=ajustes]'); if (n) n.click() } }, true);
  document.addEventListener('click', async e => { const b = e.target.closest('[data-act=agenteSel]'); if (!b) return; const r = await api('/api/agente', { activo: b.dataset.id });
    if (r && r.ok) { S.agente = r; if (S.est) S.est.agente = r.activo; toast('Los pedidos ahora llegan a ' + (r.activo === 'codex' ? 'Codex' : 'Claude') + ' (' + (r.activo === 'codex' ? 'Claude' : 'Codex') + ' queda desactivado)'); render() } else { const m = document.getElementById('agMsg'); if (m) { m.style.color = 'var(--bad)'; m.textContent = (r && r.error) || 'No se pudo cambiar' } } }, true);
  const recargaVoces = async () => { const r = await api('/api/voces'); if (r && !r.error) { S.voces = r; S.vozCfg = r.config; S.vozSel = { motor: r.config.motor, id: r.config.perfil } } render() };   // recarga sin vaciar la sección (así la pantalla no salta arriba)
  const vzMsg = (t, col) => { const m = document.getElementById('vzMsg'); if (m) { m.style.color = col || ''; m.textContent = t } };
  const vsBuscarAuto = async () => { vsMsg('Buscando Voice Studio en tu PC… (hasta 25 s)'); const r = await api('/api/vs_config', { buscar: true }); if (r && r.ok) { toast('Voice Studio encontrado'); await recargaVoces() } else vsMsg((r && r.error) || 'No lo encontré: escribe su carpeta o pulsa «Buscar en el PC»', 'var(--bad)') };
  const vsMsg = (t, col) => { const m = document.getElementById('vsMsg'); if (m) { m.style.color = col || ''; m.textContent = t } };
  document.addEventListener('input', e => { if (e.target.id === 'vz_vel' || e.target.id === 'vz_pausa') { S.vozCfg = Object.assign({}, S.vozCfg, { velocidad: document.getElementById('vz_vel').value, pausa_ms: document.getElementById('vz_pausa').value }); vzMsg('Cambios sin guardar: pulsa «Guardar configuración de voz».', 'var(--warn, #d97706)') } }, true);
  document.addEventListener('click', async e => {
    const b = e.target.closest('[data-act=vozUsar],[data-act=vozEscuchar],[data-act=vozBuscar],[data-act=vozGuardar],[data-act=vozFlecha],[data-act=vozCarpeta],[data-act=vozBorrar],[data-act=vozMotor],[data-act=vsActivar],[data-act=vsPower],[data-act=vsBuscar],[data-act=vsGuardarDir],[data-act=vsDetectar],[data-act=vozDefecto]'); if (!b) return; const act = b.dataset.act;
    if (act === 'vozMotor') { const t = b.dataset.t, vsx = (S.voces && S.voces.vs) || {}, aviso = (m) => { render(); setTimeout(() => vsMsg(m, 'var(--bad)'), 60) };
      if (t === 'vs') { S.vozTab = 'vs'; if (!vsx.instalado) { render(); if (!S.vsAuto) { S.vsAuto = 1; setTimeout(vsBuscarAuto, 80) } return } if (vsx.activo) return render(); b.disabled = true; const r = await api('/api/vs_config', { activo: true });
        if (r && r.ok) { toast('Ahora tus videos usan Voice Studio'); await recargaVoces() } else aviso((r && r.error) || 'No se pudo usar Voice Studio') }
      else { S.vozTab = 'local'; if (!vsx.activo) return render(); b.disabled = true; const r = await api('/api/vs_config', { activo: false });
        if (r && r.ok) { toast('Ahora tus videos usan las voces del panel'); await recargaVoces() } else { render(); vzMsg((r && r.error) || 'No se pudo cambiar', 'var(--bad)') } } }
    else if (act === 'vozFlecha') { const f = document.getElementById('vz_fila'); if (f) f.scrollBy({ left: Number(b.dataset.d) * (f.clientWidth / 2), behavior: 'smooth' }) }
    else if (act === 'vozUsar') { const sel = { motor: b.dataset.m, id: b.dataset.id }, ve = document.getElementById('vz_vel'), pa = document.getElementById('vz_pausa'); b.disabled = true;
      const r = await api('/api/voz_config', { perfil: sel.id, motor: sel.motor, velocidad: ve ? ve.value : undefined, pausa_ms: pa ? pa.value : undefined });
      if (r && r.ok) { S.vozSel = sel; S.vozCfg = r.config; toast('Voz en uso: ' + sel.id); render(); vzMsg('Guardado ✓ · ahora esta voz es la que se usa en todos los videos', 'var(--ok)') } else { b.disabled = false; vzMsg((r && r.error) || 'No se pudo cambiar la voz', 'var(--bad)') } }
    else if (act === 'vozCarpeta') { const r = await api('/api/voz_abrir_carpeta', {}); if (r && r.ok) vzMsg('Carpeta abierta: ' + r.carpeta + ' (si no la ves, mira la barra de tareas)', 'var(--ok)'); else vzMsg((r && r.error) || 'No pude abrir la carpeta', 'var(--bad)') }
    else if (act === 'vozDefecto') { const ve = document.getElementById('vz_vel'), pa = document.getElementById('vz_pausa'); if (ve) ve.value = 1.1; if (pa) pa.value = 400; S.vozCfg = Object.assign({}, S.vozCfg, { velocidad: 1.1, pausa_ms: 400 }); vzMsg('Valores predeterminados puestos (velocidad 1.1, pausa 400 ms): pulsa «Guardar configuración».', 'var(--warn, #d97706)') }
    else if (act === 'vsDetectar') { b.disabled = true; vsMsg('Leyendo los perfiles de Voice Studio…'); await recargaVoces(); const n = ((S.voces || {}).vs || {}).perfiles; toast(n ? n + ' perfiles de voz detectados' : 'No encontré perfiles en Voice Studio'); vsMsg(n ? 'Perfiles detectados: ' + n : 'No encontré perfiles: revisa la carpeta de Voice Studio.', n ? 'var(--ok)' : 'var(--bad)') }
    else if (act === 'vozBorrar') { if (!confirm('¿Borrar la voz «' + b.dataset.id + '»?\n\nSe mueve a la papelera del panel (_papelera/voces), así que se puede recuperar.')) return;
      const r = await api('/api/voz_borrar', { motor: b.dataset.m, id: b.dataset.id }); if (r && r.ok) { toast('Voz borrada: ' + b.dataset.id); await recargaVoces() } else vzMsg((r && r.error) || 'No se pudo borrar', 'var(--bad)') }
    else if (act === 'vsActivar') { const r = await api('/api/vs_config', { activo: !(S.voces && S.voces.vs && S.voces.vs.activo) }); if (r && r.ok) { S.vozTab = r.vs.activo ? 'vs' : 'local'; toast(r.vs.activo ? 'Voice Studio activado: ahora se usan sus perfiles' : 'Voice Studio desactivado: vuelven las voces del panel'); await recargaVoces() } else vsMsg((r && r.error) || 'No se pudo cambiar', 'var(--bad)') }
    else if (act === 'vsPower') { const on = b.dataset.on === '1'; if (on && !confirm('Se apagará Voice Studio para liberar la tarjeta de video. ¿Seguir?')) return; b.disabled = true; vsMsg(on ? 'Apagando Voice Studio…' : 'Encendiendo Voice Studio… (puede tardar un poco)');
      const r = await api(on ? '/api/voice_detener' : '/api/voice_iniciar', {}); if (r && r.error) { b.disabled = false; return vsMsg(r.error, 'var(--bad)') } toast(r.ok ? (on ? 'Voice Studio apagado' : 'Voice Studio encendido') : 'No pude completar la acción'); await recargaVoces() }
    else if (act === 'vsBuscar') { b.disabled = true; vsMsg('Buscando Voice Studio en tu PC… (hasta 25 s)'); const r = await api('/api/vs_config', { buscar: true }); b.disabled = false; if (r && r.ok) { toast('Voice Studio encontrado'); await recargaVoces() } else vsMsg((r && r.error) || 'No lo encontré', 'var(--bad)') }
    else if (act === 'vsGuardarDir') { const d = (document.getElementById('vs_dir') || {}).value; if (!d) return vsMsg('Escribe la carpeta «project» de Voice Studio', 'var(--bad)'); const r = await api('/api/vs_config', { dir: d }); if (r && r.ok) { toast('Carpeta guardada'); await recargaVoces() } else vsMsg((r && r.error) || 'No se pudo guardar', 'var(--bad)') }
    else if (act === 'vozBuscar') { await recargaVoces() }
    else if (act === 'vozEscuchar') { const MOT = { kokoro: 'Kokoro', voicestudio: 'Voice Studio', clon: 'la voz clonada', edge: 'edge-tts (Jorge)', piper: 'Piper' }[b.dataset.m] || b.dataset.m; if (S.escuchando) return vzMsg('Ya se está generando otra muestra: espera a que termine.', 'var(--warn, #d97706)'); S.escuchando = true; b.disabled = true; const t0 = Date.now(), tick = setInterval(() => vzMsg('Generando la muestra con ' + MOT + '… ' + Math.round((Date.now() - t0) / 1000) + ' s' + (b.dataset.m === 'voicestudio' ? ' · Voice Studio genera de a una: puede tardar (la primera vez hasta 2 min)' : '')), 500); const r = await api('/api/voz_escuchar', { motor: b.dataset.m, voz: b.dataset.id, velocidad: document.getElementById('vz_vel') ? document.getElementById('vz_vel').value : 1 }); clearInterval(tick); S.escuchando = false; b.disabled = false;
      if (r && r.ok) { vzMsg('Reproduciendo con ' + MOT + '…'); const au = new Audio(r.audio); au.onended = () => vzMsg('Escuchaste: ' + b.dataset.id + ' · ' + MOT); au.play().catch(() => vzMsg('El navegador bloqueó el audio: vuelve a pulsar Escuchar', 'var(--bad)')) } else vzMsg((r && r.error) || 'No se pudo generar la muestra', 'var(--bad)') }
    else if (act === 'vozGuardar') { const sel = S.vozSel || {}; const r = await api('/api/voz_config', { perfil: sel.id, motor: sel.motor, velocidad: document.getElementById('vz_vel').value, pausa_ms: document.getElementById('vz_pausa').value });
      if (r && r.ok) { S.vozCfg = r.config; toast('Ajustes de voz guardados'); render(); vzMsg('Guardado ✓', 'var(--ok)') } else vzMsg((r && r.error) || 'No se pudo guardar', 'var(--bad)') }
  }, true);
  const btnRehacer = id => `<button class="mini" data-act="rehacerTodo" data-id="${esc(id)}" title="Vuelve a pasar el video por el cerebro: se genera de nuevo, de otra forma, con el motor actualizado"><i class="ti ti-refresh"></i> Rehacer todo</button>`;
  document.addEventListener('click', async e => { const b = e.target.closest('[data-act=rehacerTodo]'); if (!b) return; const id = b.dataset.id, p = S.proy.find(x => x.id === id); if (!p) return;
    if (!confirm('¿Rehacer todo «' + p.titulo + '»?\n\nEl video vuelve al cerebro y se genera DE NUEVO desde cero, de otra forma (otro inicio y otro diseño) y con el motor actualizado. Se conservan la idea y la configuración que elegiste.\nLa versión actual se guarda en la papelera (_papelera/videos), así que se puede recuperar.')) return;
    b.disabled = true; const r = await api('/api/rehacer_todo', { id });
    if (r && r.ok) { toast('Enviado al cerebro: el video se genera de nuevo'); await cargar(true); S.p = 'videos'; S.sel = r.proyecto; S.cerebroId = r.proyecto; render(); sondea() } else { b.disabled = false; alert((r && r.error) || 'No se pudo rehacer el video') } }, true);
  const vVidB = VIEWS.videos;
  VIEWS.videos = function () { let h = vVidB(); const p = S.sel && S.proy.find(x => x.id === S.sel);
    if (!S.sel) return h.replace(/(<button class="mini" data-act="abrir" data-id="([^"]+)">Abrir<\/button>)/g, (m, b, id) => b + ' ' + btnBorrar(id));
    return p ? h.replace('Todos los videos</button>', 'Todos los videos</button>' + btnRehacer(p.id) + btnBorrar(p.id, ' Borrar')) : h; };
  document.addEventListener('click', async e => { const b = e.target.closest('[data-act=borrarVideo]'); if (!b) return; const id = b.dataset.id, p = S.proy.find(x => x.id === id); if (!p) return;
    if (!confirm('¿Borrar «' + p.titulo + '»?\n\nSe borran el video, su voz, el guion y los títulos, y también la idea y los pedidos de este video.\nLa carpeta se guarda en la papelera (_papelera/videos), así que se puede recuperar.')) return;
    b.disabled = true; const r = await api('/api/borrar_video', { id });
    if (r && r.ok) { toast('Video borrado (guardado en la papelera)'); if (S.sel === id) S.sel = null; if (window.cargar) await window.cargar(true); render() } else { b.disabled = false; alert((r && r.error) || 'No se pudo borrar el video') } }, true);
  const vVid3 = VIEWS.videos;
  VIEWS.videos = function () { const h = vVid3(), p = S.sel && S.proy.find(x => x.id === S.sel); return p && p.plugin_ok === false ? avisoPluginOff(p) + h : h };
  const vPub3 = VIEWS.publicar;
  VIEWS.publicar = function () { const p = S.pubId && S.proy.find(x => x.id === S.pubId); if (p && p.plugin_ok === false) return `<div class="row" style="margin-bottom:10px"><button class="mini" data-act="volverPub"><i class="ti ti-arrow-left"></i> Todos los videos</button><b style="font-size:16px">${esc(p.titulo)}</b></div>` + avisoPluginOff(p, 'Los títulos, la descripción y las etiquetas los genera el plugin del video; con el plugin desactivado no se generan. Actívalo en Plugins.'); return vPub3() };

  /* ---------- pestaña Guía: la guía de uso (GUIA_DE_USO.md, copia en static/guia_uso.md) dentro del panel ---------- */
  TIT.guia = ['Guía', 'Cómo se usa cada pantalla del panel'];
  (function () {
    const nav = document.querySelector('.nav[data-p="ajustes"]'); if (!nav || document.querySelector('.nav[data-p="guia"]')) return;
    const b = document.createElement('button'); b.className = 'nav'; b.dataset.act = 'nav'; b.dataset.p = 'guia'; b.innerHTML = '<i class="ti ti-book"></i><span>Guía</span>'; nav.before(b);
  })();
  function mdHtml(md) {   // mini conversor de Markdown (títulos, listas, tablas, código, negritas)
    const inl = s => esc(s).replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>').replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
    const L = md.replace(/\r/g, '').split('\n'); let o = '', i = 0, lista = null;
    const cierra = () => { if (lista) { o += '</' + lista + '>'; lista = null; } };
    while (i < L.length) { const l = L[i];
      if (/^```/.test(l)) { cierra(); let c = ''; i++; while (i < L.length && !/^```/.test(L[i])) { c += L[i] + '\n'; i++; } o += '<pre style="background:#0b1220;border:1px solid var(--line);border-radius:8px;padding:10px;overflow:auto"><code>' + esc(c) + '</code></pre>'; i++; continue; }
      if (/^\|/.test(l) && /^\|[-| :]+\|?$/.test(L[i + 1] || '')) { cierra(); const cel = r => r.replace(/^\||\|$/g, '').split('|').map(x => x.trim()); let h = cel(l); i += 2; let rows = ''; while (i < L.length && /^\|/.test(L[i])) { rows += '<tr>' + cel(L[i]).map(x => '<td>' + inl(x) + '</td>').join('') + '</tr>'; i++; } o += '<table><thead><tr>' + h.map(x => '<th>' + inl(x) + '</th>').join('') + '</tr></thead><tbody>' + rows + '</tbody></table>'; continue; }
      let m;
      if ((m = l.match(/^(#{1,4}) (.*)/))) { cierra(); o += '<h' + (m[1].length + 1) + ' style="margin:18px 0 8px">' + inl(m[2]) + '</h' + (m[1].length + 1) + '>'; }
      else if ((m = l.match(/^\s*[-*] (.*)/))) { if (lista !== 'ul') { cierra(); o += '<ul style="margin:6px 0 6px 20px">'; lista = 'ul'; } o += '<li>' + inl(m[1]) + '</li>'; }
      else if ((m = l.match(/^\s*\d+\. (.*)/))) { if (lista !== 'ol') { cierra(); o += '<ol style="margin:6px 0 6px 20px">'; lista = 'ol'; } o += '<li>' + inl(m[1]) + '</li>'; }
      else if (/^---+$/.test(l)) { cierra(); o += '<hr style="border:0;border-top:1px solid var(--line);margin:16px 0">'; }
      else if ((m = l.match(/^> (.*)/))) { cierra(); o += '<div class="note">' + inl(m[1]) + '</div>'; }
      else if (l.trim()) { cierra(); o += '<p style="margin:6px 0">' + inl(l) + '</p>'; }
      i++; }
    cierra(); return o; }
  VIEWS.guia = function () {
    if (!S.guiaMd && !S.guiaPide) { S.guiaPide = 1; fetch('/static/guia_uso.md').then(r => r.text()).then(t => { S.guiaMd = t; if (S.p === 'guia') render(); }).catch(() => { S.guiaMd = 'No se pudo cargar la guía.'; if (S.p === 'guia') render(); }); }
    return '<div class="panel"><div class="body" style="max-width:900px;line-height:1.55">' + (S.guiaMd ? mdHtml(S.guiaMd) : '<p class="muted">Cargando la guía…</p>') + '</div></div>';
  };
  render();
})();
