/* Nebula dashboard (Asterium Labs). Reads the JSON block that ui/bundle.py
   inlines; draws four pages. No framework, no network. Motion is used for
   three things only: time (replay, cursor), cause (the ring at the
   intervention) and evidence arriving (dots and bars settling). */
(function () {
'use strict';
const D = JSON.parse(document.getElementById('wt-data').textContent);
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const root = document.documentElement;
const NS = 'http://www.w3.org/2000/svg';
const $ = id => document.getElementById(id);

function h(tag, attrs, ...kids) {
  const e = document.createElement(tag);
  for (const k in attrs || {}) {
    if (k === 'class') e.className = attrs[k];
    else if (k === 'style') e.style.cssText = attrs[k];
    else e.setAttribute(k, attrs[k]);
  }
  kids.flat().forEach(c => { if (c != null && c !== false) e.append(c.nodeType ? c : document.createTextNode(String(c))); });
  return e;
}
function sv(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
}
const pct = (v, d = 1) => v == null ? '—' : (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(d) + '%';
const num = (v, d = 1) => (v >= 0 ? '+' : '−') + Math.abs(v).toFixed(d);
const plural = (n, w) => `${n} ${w}${n === 1 ? '' : 's'}`;

const C = {};
function readColors() {
  const s = getComputedStyle(root);
  ['--a', '--b', '--up', '--down', '--ink', '--muted', '--faint', '--line', '--wash', '--surface', '--warn'].forEach(k => C[k] = s.getPropertyValue(k).trim());
}
readColors();
const onTheme = [];
function themeChanged() { readColors(); onTheme.forEach(f => f()); }
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', themeChanged);
new MutationObserver(themeChanged).observe(root, { attributes: true, attributeFilter: ['data-theme'] });

const F = D.flagship, ARMS = F.arms, T0 = F.t0, R = F.rounds;
const nSeeds = Math.min(ARMS.a.length, ARMS.b.length);
const seps = [...Array(nSeeds)].map((_, i) => ARMS.a[i].day_ret - ARMS.b[i].day_ret);
const PAR = F.parity;
const parFail = PAR.filter(p => p.ok === false), parPass = PAR.filter(p => p.ok === true);
const PRE_FIX = '2026-10-29';   // runs before this date predate the gateway race fix

function parityLine(p) {
  if (p.ok === null) return `${p.a} vs ${p.b}: unknown — ${p.reason}.`;
  if (p.ok) return `${p.a} vs ${p.b}: identical before t=${p.t_intervention}.`;
  const worst = Object.entries(p.max_pre_gap).sort((x, y) => y[1] - x[1])[0] || ['-', 0];
  return `${p.a} vs ${p.b}: decisions differ from t=${p.first_intent_diff_t}, prices from t=${p.first_price_diff_t}; largest gap before the intervention ${(worst[1] * 100).toFixed(2)}% on ${worst[0]}.`;
}

/* ================================================================ VERDICT */
function buildVerdict() {
  const k = seps.filter(x => x > 0).length;
  $('v-title').textContent =
    k === nSeeds ? `Neutral wording (A) finished above alarming wording (B) in ${nSeeds === 2 ? 'both' : 'all ' + nSeeds} seeds.`
    : k === 0 ? `Alarming wording (B) finished above neutral wording (A) in every seed.`
    : `The seeds disagree: A finished above B in ${k} of ${nSeeds}.`;
  const chips = $('v-chips');
  chips.append(h('span', { class: 'chip' }, `${F.model} · prompt ${F.prompt}`));
  chips.append(h('span', { class: 'chip' }, `${nSeeds} seeds × 2 arms`));
  chips.append(F.panel_current ? h('span', { class: 'chip' }, 'current panel')
    : h('span', { class: 'chip warn' }, 'older panel — per-agent cards unreliable'));
  if (parFail.length) chips.append(h('span', { class: 'chip bad' }, h('span', { class: 'dot' }), `parity: ${parFail.length} of ${PAR.length} pairs differ before t=${T0}`));
  else if (parPass.length === PAR.length) chips.append(h('span', { class: 'chip ok' }, h('span', { class: 'dot' }), `parity: all pairs identical before t=${T0}`));
  else chips.append(h('span', { class: 'chip warn' }, 'parity: not checked (bulk logs missing)'));

  const ma = F.day_mean.a * 100, mb = F.day_mean.b * 100;
  $('v-tiles').append(
    h('div', { class: 'tile a' }, h('div', { class: 'n' }, pct(ma)), h('div', { class: 'k' }, 'A · neutral wording')),
    h('div', { class: 'tile b' }, h('div', { class: 'n' }, pct(mb)), h('div', { class: 'k' }, 'B · alarming wording')),
    h('div', { class: 'tile' }, h('div', { class: 'n' }, num(ma - mb), h('small', {}, ' pp')), h('div', { class: 'k' }, 'A − B')),
    h('p', { class: 'note' }, `Simulated full-day equity return, mean of ${nSeeds} seeds. Read the order, not the size.`));
  $('v-wording').append(
    h('blockquote', { class: 'qa' }, h('b', {}, `A · t=${T0}`), F.wording.a || '—'),
    h('blockquote', { class: 'qb' }, h('b', {}, `B · t=${T0}`), F.wording.b || '—'));

  const pt = $('v-parity-text');
  if (parFail.length) {
    pt.append(`No. ${parFail.length} of ${PAR.length} same-seed pairs already differ before the statement, so part of the gap is not caused by the wording. `);
    if (ARMS.a.some(s => (s.created || '') < PRE_FIX)) pt.append(`Known cause for runs made before ${PRE_FIX}: concurrent LLM calls raced for a shared answer cache (fixed in runtime/llm.py). Re-run to get a clean pair.`);
    PAR.forEach(p => pt.append(h('span', { style: 'display:block;margin-top:6px;font-family:var(--f-mono);font-size:12px' }, parityLine(p))));
  } else if (parPass.length === PAR.length) {
    pt.textContent = `Yes. Every same-seed pair makes identical decisions at identical prices until t=${T0}, so the gap starts at the statement.`;
  } else {
    pt.textContent = 'Not checked: the bulk run logs are not on this machine. Re-run the experiment to check parity.';
  }
  const rows = D.robustness.rows.filter(r => r.quotable);
  const all = rows.flatMap(r => r.seeds);
  const pos = all.filter(s => s.sep > 0).length;
  const clean = all.filter(s => s.parity === true).length;
  $('v-robust-text').append(`Across ${plural(all.length, 'quotable seed pair')}, A finished higher in ${pos}; ${clean} ${clean === 1 ? 'is' : 'are'} a clean A/B. `,
    h('a', { href: '#robustness' }, 'See every seed →'));
  drawVerdictChart();
}

let verdictAt = null;
function drawVerdictChart() {
  const svg = $('v-svg'), read = $('v-read');
  svg.textContent = '';
  const W = 960, H = 340, L = 44, Rr = 12, T = 16, B = 30;
  const mean = arm => { const n = Math.min(...arm.map(s => s.eq.length)); return [...Array(n)].map((_, i) => arm.reduce((t, s) => t + s.eq[i], 0) / arm.length); };
  const mA = mean(ARMS.a), mB = mean(ARMS.b);
  const all = [...ARMS.a, ...ARMS.b].flatMap(s => s.eq);
  const lo = Math.floor(Math.min(...all) / 5) * 5, hi = Math.ceil(Math.max(...all) / 5) * 5;
  const x = t => L + (W - L - Rr) * t / (R - 1), y = v => T + (H - T - B) * (hi - v) / ((hi - lo) || 1);
  const bad = parFail.map(p => Math.min(p.first_intent_diff_t ?? T0, p.first_price_diff_t ?? T0));
  const contam = bad.length ? Math.min(...bad) : null;
  if (contam != null && contam < T0) {
    sv('rect', { x: x(contam), y: T, width: x(T0) - x(contam), height: H - T - B, fill: 'var(--warn)', 'fill-opacity': .1 }, svg);
    sv('text', { x: x(contam) + 6, y: H - B - 8, class: 'ax', fill: 'var(--warn)', style: 'fill:var(--warn)' }, svg).textContent = `arms already differ from t=${contam}`;
  }
  sv('rect', { x: x(T0), y: T, width: x(Math.min(T0 + 90, R - 1)) - x(T0), height: H - T - B, fill: 'var(--wash)' }, svg);
  for (let v = lo; v <= hi; v += 5) {
    sv('line', { x1: L, x2: W - Rr, y1: y(v), y2: y(v), stroke: 'var(--line)' }, svg);
    sv('text', { x: L - 8, y: y(v) + 4, 'text-anchor': 'end', class: 'ax' }, svg).textContent = (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v) + '%';
  }
  [0, Math.round(R / 4), T0, Math.round(R * 3 / 4), R - 1].forEach(t => sv('text', { x: x(t), y: H - 8, 'text-anchor': 'middle', class: 'ax' }, svg).textContent = 't=' + t);
  sv('line', { x1: x(T0), x2: x(T0), y1: T, y2: H - B, stroke: 'var(--muted)', 'stroke-dasharray': '3 4' }, svg);
  sv('text', { x: x(T0) + 6, y: T + 14, class: 'ax' }, svg).textContent = 'statement published · 90-round window';
  const path = arr => arr.map((v, i) => i % 2 && i !== arr.length - 1 ? '' : (i ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1)).join('');
  ARMS.a.forEach(s => sv('path', { d: path(s.eq), fill: 'none', stroke: 'var(--a)', 'stroke-opacity': .32, 'stroke-width': 1 }, svg));
  ARMS.b.forEach(s => sv('path', { d: path(s.eq), fill: 'none', stroke: 'var(--b)', 'stroke-opacity': .32, 'stroke-width': 1 }, svg));
  sv('path', { d: path(mA), fill: 'none', stroke: 'var(--a)', 'stroke-width': 2.6, 'stroke-linejoin': 'round' }, svg);
  sv('path', { d: path(mB), fill: 'none', stroke: 'var(--b)', 'stroke-width': 2.6, 'stroke-linejoin': 'round' }, svg);
  const cur = sv('line', { y1: T, y2: H - B, stroke: 'var(--ink)', 'stroke-opacity': .35 }, svg);
  const da = sv('circle', { r: 5, fill: 'var(--a)', stroke: 'var(--surface)', 'stroke-width': 2 }, svg);
  const db = sv('circle', { r: 5, fill: 'var(--b)', stroke: 'var(--surface)', 'stroke-width': 2 }, svg);
  verdictAt = t => {
    t = Math.max(0, Math.min(mA.length - 1, Math.round(t)));
    const a = mA[t], b = mB[t];
    cur.setAttribute('x1', x(t)); cur.setAttribute('x2', x(t));
    da.setAttribute('cx', x(t)); da.setAttribute('cy', y(a));
    db.setAttribute('cx', x(t)); db.setAttribute('cy', y(b));
    const bw = svg.getBoundingClientRect().width || 1, px = x(t) / W * bw;
    read.innerHTML = '';
    read.append(`t=${t} · `, h('span', { style: 'color:var(--a)' }, `A ${pct(a)}`), ' · ', h('span', { style: 'color:var(--b)' }, `B ${pct(b)}`), bw > 480 ? ` · gap ${num(a - b)} pp` : '');
    const half = (read.offsetWidth || 200) / 2;
    read.style.left = Math.min(Math.max(px, half), bw - half) + 'px';
  };
  verdictAt(R - 1);
  $('v-legend').innerHTML = '';
  $('v-legend').append(
    h('span', {}, h('i', { class: 'ln', style: 'border-color:var(--a)' }), 'A · seed mean'),
    h('span', {}, h('i', { class: 'ln', style: 'border-color:var(--b)' }), 'B · seed mean'),
    h('span', {}, 'thin lines = single seeds · shaded = 90-round window after the statement'),
    contam != null && contam < T0 ? h('span', { style: 'color:var(--warn)' }, 'amber band = arms not identical before the statement') : null);
}
let verdictT0 = null;
function verdictTick(now) {
  if (current !== 'verdict' || RM || !verdictAt) return;
  if (verdictT0 === null) verdictT0 = now;
  const p = ((now - verdictT0) / 9000) % 1;
  verdictAt(p < .85 ? T0 + (R - 1 - T0) * (p / .85) : R - 1);
  requestAnimationFrame(verdictTick);
}

/* ================================================================ RIPPLE */
const RP = (() => {
  const classes = D.agents.classes, rows = D.agents.rows, N = rows.length;
  const cls = new Array(N), tier = new Array(N);
  let k = 0;
  classes.forEach((c, ci) => { for (let j = 0; j < c.n; j++) { cls[k] = ci; tier[k] = c.tier; k++; } });
  const byT = {}, cnt = {}, eq = {};
  for (const arm of ['a', 'b']) {
    byT[arm] = [...Array(R)].map(() => []);
    cnt[arm] = new Array(R).fill(0);
    D.replay[arm].intents.forEach(r => { if (r[0] < R) { byT[arm][r[0]].push(r); cnt[arm][r[0]]++; } });
    eq[arm] = D.replay[arm].books.EQ.path;
  }
  const cv = $('r-grid'), tl = $('r-tl');
  let pos = [], cell = 10, gap = 2, Wc = 0, Hc = 0, center = [0, 0], dpr = 1;
  const inten = new Float32Array(N), side = new Int8Array(N);
  let pending = [], ring = null, arm = 'a', t = T0, playing = !RM, hold = !RM, acc = 0, last = 0, running = false;
  const SPEED = 520;

  function layout() {
    dpr = window.devicePixelRatio || 1; Wc = cv.clientWidth; if (!Wc) return false;
    cell = Wc < 520 ? 7 : Wc < 820 ? 9 : 11;
    const cols = Math.floor((Wc + gap) / (cell + gap));
    let slot = 0, ci = -1; const slots = [];
    for (let i = 0; i < N; i++) { if (cls[i] !== ci) { if (ci >= 0) slot += 1; ci = cls[i]; } slots.push(slot++); }
    Hc = Math.ceil(slot / cols) * (cell + gap);
    cv.width = Wc * dpr; cv.height = Hc * dpr; cv.style.height = Hc + 'px';
    const off = (Wc - (cols * (cell + gap) - gap)) / 2;
    pos = slots.map(p => [off + (p % cols) * (cell + gap), Math.floor(p / cols) * (cell + gap)]);
    const src = pos.filter((_, i) => tier[i] === 'meta');
    const pick = src.length ? src : pos;
    center = [pick.reduce((s, p) => s + p[0], 0) / pick.length + cell / 2, pick.reduce((s, p) => s + p[1], 0) / pick.length + cell / 2];
    tl.width = tl.clientWidth * dpr; tl.height = 56 * dpr;
    return true;
  }
  const dist = i => Math.hypot(pos[i][0] + cell / 2 - center[0], pos[i][1] + cell / 2 - center[1]);
  function fire(tt, now, animate) {
    const list = byT[arm][tt] || [];
    if (tt === T0 && animate) { ring = { start: now }; list.forEach(r => pending.push({ at: now + dist(r[1]) / SPEED * 1000, i: r[1], s: r[2] })); }
    else list.forEach(r => { inten[r[1]] = 1; side[r[1]] = r[2]; });
  }
  function seek(tt) {
    inten.fill(0); pending = []; ring = null; t = tt;
    for (let q = Math.max(0, tt - 5); q <= tt; q++) (byT[arm][q] || []).forEach(r => { inten[r[1]] = 1 - (tt - q) * .17; side[r[1]] = r[2]; });
    show();
  }
  function show() {
    $('r-t').textContent = t; $('r-tk').textContent = `round of ${R - 1}`;
    $('r-w').textContent = cnt[arm][t];
    const a = eq.a[t], b = eq.b[t];
    $('r-a').textContent = pct(a, 2); $('r-b').textContent = pct(b, 2); $('r-d').textContent = num(a - b, 2);
    $('r-scrub').value = t;
    const ol = $('r-stream'); ol.textContent = '';
    // On a quiet round, keep showing the most recent round that had decisions.
    let at = t; while (at > 0 && !byT[arm][at].length) at--;
    const list = byT[arm][at];
    $('r-stream-n').textContent = `arm ${arm.toUpperCase()} · seed ${D.replay[arm].seed} · ` +
      (list.length ? (at === t ? `t=${t} · ${plural(list.length, 'decision')}` : `quiet since t=${at} · showing t=${at}`) : `t=${t}`);
    if (!list.length) ol.append(h('li', { class: 'empty' }, 'No LLM decision yet. Most agents are not looking.'));
    list.slice(0, 12).forEach(r => {
      const sd = r[2] > 0 ? 'buy' : r[2] < 0 ? 'sell' : 'pass';
      ol.append(h('li', {}, h('span', {}, rows[r[1]][0]), h('span', { class: 's' + r[2] }, `${D.meta.assets[r[3]]} ${sd}`),
        h('span', {}, r[2] ? (r[6] > 0 ? 'filled' : 'no fill') : ''), h('span', { class: 'why', title: r[7] }, r[7] || '')));
    });
    if (list.length > 12) ol.append(h('li', { class: 'empty' }, `+ ${list.length - 12} more this round`));
  }
  function draw(now) {
    if (!Wc) return;
    const g = cv.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0); g.clearRect(0, 0, Wc, Hc);
    const base = { llm: .6, policy: .32, rule: .24, meta: .9 };
    for (let i = 0; i < N; i++) {
      const [px, py] = pos[i];
      g.globalAlpha = base[tier[i]] ?? .3; g.fillStyle = tier[i] === 'meta' ? C['--muted'] : C['--line']; g.fillRect(px, py, cell, cell);
      if (inten[i] > .01) { g.globalAlpha = Math.min(1, inten[i]); g.fillStyle = side[i] > 0 ? C['--up'] : side[i] < 0 ? C['--down'] : C['--faint']; g.fillRect(px, py, cell, cell); }
    }
    g.globalAlpha = 1;
    if (ring) {
      const r = (now - ring.start) / 1000 * SPEED, rmax = Math.hypot(Wc, Hc);
      if (r > rmax) ring = null;
      else for (const off of [0, 38]) {
        const rr = r - off; if (rr <= 0) continue;
        g.beginPath(); g.arc(center[0], center[1], rr, 0, Math.PI * 2);
        g.strokeStyle = C['--a']; g.globalAlpha = Math.max(0, .55 * (1 - rr / rmax)); g.lineWidth = off ? 1 : 2; g.stroke();
      }
      g.globalAlpha = 1;
    }
    const tg = tl.getContext('2d'), tw = tl.clientWidth, th = 56;
    tg.setTransform(dpr, 0, 0, dpr, 0, 0); tg.clearRect(0, 0, tw, th);
    const mx = Math.sqrt(Math.max(1, ...cnt[arm])), bw = tw / R;
    tg.fillStyle = C['--warn']; tg.globalAlpha = .9; tg.fillRect(T0 * bw, 12, 1, th - 24); tg.globalAlpha = 1;
    for (let q = 0; q < R; q++) {
      const c = cnt[arm][q]; if (!c) continue;
      const hh = Math.max(2, (th - 26) * Math.sqrt(c) / mx);
      tg.fillStyle = q <= t ? (arm === 'a' ? C['--a'] : C['--b']) : C['--line'];
      tg.fillRect(q * bw, th - 12 - hh, Math.max(1, bw - .5), hh);
    }
    tg.font = '11px "IBM Plex Mono", ui-monospace, monospace'; tg.fillStyle = C['--muted'];
    tg.textAlign = 'left'; tg.fillText('LLM decisions per round (√ scale)', 0, 10);
    tg.textAlign = 'right'; tg.fillText(`t=${T0}: ${cnt[arm][T0]} decisions`, tw, 10);
    tg.fillStyle = C['--line']; tg.fillRect(0, th - 12, tw, 1);
    tg.fillStyle = C['--ink']; tg.fillRect(t * bw, 12, 1.5, th - 24);
  }
  function tick(now) {
    if (current !== 'ripple') { running = false; return; }
    const dt = Math.min(.1, (now - last) / 1000); last = now;
    if (playing && !hold) {
      acc += dt * ((t >= T0 - 6 && t <= T0 + 6) ? 1.6 : 16);
      while (acc >= 1) { acc -= 1; t++; if (t > R - 1) { t = Math.max(0, T0 - 60); seek(t); } fire(t, now, true); show(); }
    }
    pending = pending.filter(p => { if (now >= p.at) { inten[p.i] = 1; side[p.i] = p.s; return false; } return true; });
    const decay = Math.pow(.955, dt * 60); for (let i = 0; i < N; i++) inten[i] *= decay;
    draw(now);
    requestAnimationFrame(tick);
  }
  function setPlay(v) { playing = v; $('r-play').textContent = v ? 'Pause' : 'Play'; }
  function setArm(a) { arm = a; $('r-armA').setAttribute('aria-pressed', a === 'a'); $('r-armB').setAttribute('aria-pressed', a === 'b'); seek(t); }
  let built = false;
  function start() {
    if (!layout()) return;
    if (!built) {
      built = true;
      $('r-scrub').max = R - 1;
      $('r-legend').append(...classes.map(c => h('span', {}, h('b', { style: 'color:var(--ink);font-weight:500' }, c.name), ` ${c.n} · ${c.tier === 'meta' ? 'event source' : c.tier}`)));
      seek(T0); fire(T0, 0, false);
      if (!RM) setTimeout(() => { hold = false; seek(Math.max(0, T0 - 30)); }, 1600);
      $('r-play').onclick = () => { hold = false; setPlay(!playing); };
      $('r-armA').onclick = () => setArm('a');
      $('r-armB').onclick = () => setArm('b');
      $('r-jump').onclick = () => { hold = false; seek(T0 - 4); setPlay(true); };
      $('r-scrub').oninput = e => { hold = false; seek(+e.target.value); };
      cv.addEventListener('mousemove', e => {
        const r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
        const i = pos.findIndex(p => mx >= p[0] && mx < p[0] + cell && my >= p[1] && my < p[1] + cell);
        if (i < 0) return;
        const a = rows[i], c = classes[cls[i]];
        $('r-hover').textContent = `${a[0]} · ${c.tier} · ${a[1]} · budget ~$${(a[2] / 1000).toFixed(0)}k — ${a[3]}`;
      });
      setPlay(playing);
      buildWho(); buildBooks();
    }
    draw(performance.now());
    if (!running) { running = true; requestAnimationFrame(n => { last = n; tick(n); }); }
  }
  onTheme.push(() => draw(performance.now()));
  addEventListener('resize', () => { if (current === 'ripple' && layout()) draw(performance.now()); });
  return { start };
})();

function buildWho() {
  const box = $('r-who');
  const llm = D.agents.classes.filter(c => c.tier === 'llm');
  const rows = llm.map(c => {
    const a = D.who.a.net[c.name] || 0, b = D.who.b.net[c.name] || 0;
    return { n: c.name, size: c.n, a, b, d: a - b };
  }).sort((p, q) => q.d - p.d);
  const mx = Math.max(1e-9, ...rows.flatMap(r => [Math.abs(r.a), Math.abs(r.b)]));
  rows.forEach(r => box.append(h('div', { class: 'who-row' },
    h('div', { class: 'who-name' }, r.n, h('small', {}, `${r.size} agents`)),
    h('div', { class: 'bars' }, h('div', { class: 'bar a', 'data-v': r.a, title: `A ${num(r.a, 1)}` }), h('div', { class: 'bar b', 'data-v': r.b, title: `B ${num(r.b, 1)}` })),
    h('div', { class: 'who-d' }, num(r.d, 1), h('small', {}, `${num(r.d / r.size, 2)} / agent`)))));
  const set = on => box.querySelectorAll('.bar').forEach(b => { const v = on ? +b.dataset.v : 0, w = Math.abs(v) / mx * 50; b.style.width = w + '%'; b.style.marginLeft = (v >= 0 ? 50 : 50 - w) + '%'; });
  if (RM) set(true); else requestAnimationFrame(() => requestAnimationFrame(() => set(true)));
}

function buildBooks() {
  const box = $('r-books'), A = D.replay.a.books, B = D.replay.b.books;
  D.meta.assets.forEach(as => {
    const pa = A[as].path, pb = B[as].path;
    if (!pa.length) return;
    const W = 200, H = 76, lo = Math.min(0, ...pa, ...pb), hi = Math.max(0, ...pa, ...pb), n = Math.max(pa.length, pb.length);
    const x = i => 2 + (W - 4) * i / (n - 1), y = v => 4 + (H - 8) * (hi - v) / ((hi - lo) || 1);
    const svg = sv('svg', { viewBox: `0 0 ${W} ${H}`, role: 'img', 'aria-label': `${as} path, A vs B` });
    sv('line', { x1: 0, x2: W, y1: y(0), y2: y(0), stroke: 'var(--line)' }, svg);
    sv('line', { x1: x(T0), x2: x(T0), y1: 0, y2: H, stroke: 'var(--faint)', 'stroke-dasharray': '2 3' }, svg);
    const d = arr => arr.map((v, i) => (i ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1)).join('');
    sv('path', { d: d(pb), fill: 'none', stroke: 'var(--b)', 'stroke-width': 1.4 }, svg);
    sv('path', { d: d(pa), fill: 'none', stroke: 'var(--a)', 'stroke-width': 1.4 }, svg);
    const halts = A[as].halts + B[as].halts;
    box.append(h('div', { class: 'book' }, h('h4', {}, D.meta.asset_names[as] || as, halts ? h('span', { class: 'chip bad', style: 'margin-left:6px' }, `${halts} halts`) : null), svg,
      h('div', { class: 'nums' }, h('span', { style: 'color:var(--a)' }, `A ${pct(pa[pa.length - 1])}`), h('span', { style: 'color:var(--b)' }, `B ${pct(pb[pb.length - 1])}`))));
  });
}

/* ================================================================ ROBUSTNESS */
function buildRobustness() {
  const rows = D.robustness.rows, svg = $('b-svg');
  const q = rows.filter(r => r.quotable), qs = q.flatMap(r => r.seeds);
  const pos = qs.filter(s => s.sep > 0).length, clean = qs.filter(s => s.parity === true).length;
  $('b-title').textContent = `A finished higher in ${pos} of ${plural(qs.length, 'quotable seed pair')}` +
    (clean === qs.length ? ', every pair a clean A/B.' : clean === 0 ? ', and none of them is a clean A/B yet.' : `; ${clean} ${clean === 1 ? 'is' : 'are'} a clean A/B.`);
  const rowH = 56, T = 30, L = 230, W = 960, Rr = 24, H = T + rows.length * rowH + 20;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const vals = rows.flatMap(r => r.seeds.map(s => s.sep * 100));
  const lo = Math.min(-10, Math.floor(Math.min(...vals) / 10) * 10), hi = Math.max(10, Math.ceil(Math.max(...vals) / 10) * 10);
  const x = v => L + (W - L - Rr) * (v - lo) / (hi - lo);
  const bottom = T + rows.length * rowH - 12;
  sv('rect', { x: x(lo), y: T - 8, width: x(0) - x(lo), height: bottom - T + 8, fill: 'var(--down)', 'fill-opacity': .05 }, svg);
  for (let v = lo; v <= hi; v += 10) {
    if (v) sv('line', { x1: x(v), x2: x(v), y1: T - 8, y2: bottom, stroke: 'var(--line)' }, svg);
    sv('text', { x: x(v), y: bottom + 18, 'text-anchor': 'middle', class: 'ax' }, svg).textContent = (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v) + ' pp';
  }
  sv('line', { x1: x(0), x2: x(0), y1: T - 12, y2: bottom, stroke: 'var(--ink)', 'stroke-width': 1.4 }, svg);
  sv('text', { x: x(0) - 8, y: T - 14, 'text-anchor': 'end', class: 'ax' }, svg).textContent = '← B higher';
  sv('text', { x: x(0) + 8, y: T - 14, class: 'ax' }, svg).textContent = 'A higher →';
  const dots = [];
  rows.forEach((r, i) => {
    const cy = T + i * rowH + 18, g = sv('g', { opacity: r.quotable ? 1 : .4 }, svg);
    sv('text', { x: 0, y: cy - 2, class: 'lbl' }, g).textContent = r.label;
    sv('text', { x: 0, y: cy + 14, class: 'sub' }, g).textContent = r.sub.length > 34 ? r.sub.slice(0, 33) + '…' : r.sub;
    const v = r.seeds.map(s => s.sep * 100), m = v.reduce((a, b) => a + b, 0) / v.length;
    sv('line', { x1: x(Math.min(...v)), x2: x(Math.max(...v)), y1: cy, y2: cy, stroke: 'var(--muted)', 'stroke-opacity': .4 }, g);
    sv('line', { x1: x(m), x2: x(m), y1: cy - 10, y2: cy + 10, stroke: 'var(--ink)', 'stroke-width': 2 }, g);
    r.seeds.forEach((s, j) => {
      const val = s.sep * 100, fail = s.parity === false;
      const c = sv('circle', { cx: x(val), cy, r: 7, fill: fail ? 'var(--surface)' : (val < 0 ? 'var(--down)' : 'var(--a)'), stroke: fail ? (val < 0 ? 'var(--down)' : 'var(--a)') : 'var(--surface)', 'stroke-width': fail ? 2.5 : 2 }, g);
      c.style.setProperty('--dx', (x(m) - x(val)) + 'px');
      dots.push(c);
      sv('title', {}, c).textContent = `seed ${j}: A ${pct(s.a * 100)} · B ${pct(s.b * 100)} · ${fail ? 'not identical before the intervention' : s.parity ? 'clean A/B' : 'parity unknown'}`;
      const crowded = j > 0 && Math.abs(x(val) - x(r.seeds[j - 1].sep * 100)) < 40;
      sv('text', { x: x(val), y: crowded ? cy + 22 : cy - 13, 'text-anchor': 'middle', class: 'ax' }, g).textContent = num(val, 1);
    });
  });
  if (!RM) dots.forEach(c => c.classList.add('slide'));

  const tb = $('b-table');
  tb.append(h('tr', {}, ...['Brain', 'Prompt', 'A − B per seed', 'Parity', 'LLM errors', 'Every seed agrees?', 'Quotable'].map(c => h('th', {}, c))));
  rows.forEach(r => {
    const v = r.seeds.map(s => s.sep);
    const agree = v.every(x => x > 0) ? 'yes · A higher' : v.every(x => x < 0) ? 'yes · B higher' : 'no · seeds disagree';
    const parTxt = r.seeds.map(s => s.parity === true ? 'pass' : s.parity === false ? 'fail' : '?').join(' / ');
    tb.append(h('tr', { class: r.quotable ? '' : 'dim' },
      h('td', {}, r.label === 'Flagship' ? `${r.model} (flagship)` : r.label), h('td', {}, r.prompt),
      h('td', { class: 'mono' }, v.map(x => num(x * 100, 1)).join(' / ') + ' pp'),
      h('td', {}, h('span', { class: 'chip ' + (r.seeds.every(s => s.parity === true) ? 'ok' : r.seeds.some(s => s.parity === false) ? 'bad' : 'warn') }, parTxt)),
      h('td', { class: 'mono' }, r.errors == null ? '—' : r.errors),
      h('td', {}, agree), h('td', {}, r.quotable ? 'yes' : 'no')));
  });
}

/* ================================================================ EVIDENCE */
function buildEvidence() {
  const E = D.evidence, cov = E.coverage;
  document.querySelectorAll('[data-n-agents]').forEach(e => e.textContent = cov.agents);
  $('e-tiles').append(
    h('div', { class: 'tile' }, h('div', { class: 'n' }, cov.agents), h('div', { class: 'k' }, 'agents in the panel')),
    h('div', { class: 'tile' }, h('div', { class: 'n' }, cov.attribute_records.toLocaleString('en-US')), h('div', { class: 'k' }, 'attribute evidence records')),
    h('div', { class: 'tile' }, h('div', { class: 'n', style: 'color:var(--down)' }, Math.round(cov.grounded_share * 100) + '%'), h('div', { class: 'k' }, 'grounded in real people')),
    h('p', { class: 'note' }, 'Attributes without evidence stay unset and are counted, never filled in.'));
  const colors = { prior: 'var(--faint)', derived: 'var(--a)', unknown: 'var(--wash)' };
  const tot = Object.values(cov.by_evidence_kind).reduce((a, b) => a + b, 0) || 1;
  Object.entries(cov.by_evidence_kind).forEach(([k, n]) => {
    const c = colors[k] || 'var(--up)';
    $('e-stack').append(h('span', { style: `width:${n / tot * 100}%;background:${c}`, title: `${k}: ${n}` }));
    $('e-stack-legend').append(h('span', {}, h('i', { class: 'sw', style: `background:${c};outline:1px solid var(--line)` }), `${k} ${(n / tot * 100).toFixed(0)}%`));
  });
  const unk = Object.entries(cov.unknown_fields);
  $('e-unknown').textContent = unk.length ? `Unset for want of real-person data: ${unk.map(([f, n]) => `${f} (${n})`).join(', ')}.` : '';
  $('e-card-run').textContent = E.card_run;
  if (E.panel_warning) $('e-cards').before(h('p', { class: 'chip warn', style: 'white-space:normal;margin-bottom:12px' }, E.panel_warning));
  E.cards.forEach(c => $('e-cards').append(h('div', { class: 'card' },
    h('h4', {}, c.title), h('div', { class: 'id' }, `${c.id} · ${c.class}/${c.archetype} · tier ${c.tier}`),
    h('div', { class: 'ident' }, c.identity.split('\n')[0]),
    h('div', { class: 'chips' }, h('span', { class: 'chip' }, `${c.decisions} decisions`), h('span', { class: 'chip' }, `${c.fills} fills`)),
    ...c.sections.filter(s => s[1].length).map(([t, rs]) => [h('div', { class: 'sec' }, t), h('table', {}, ...rs.slice(0, 7).map(([k, v]) => h('tr', {}, h('td', {}, k), h('td', {}, v))))]),
    h('div', { class: 'id' }, 'Evidence: ' + Object.entries(c.evidence).map(([k, n]) => `${k}=${n}`).join(' · ')),
    c.unknown.length ? h('div', { class: 'unk' }, 'Unset: ' + c.unknown.join(', ')) : null)));
  const m = D.meta;
  $('e-sources').append(
    h('li', {}, 'Flagship A/B: ', h('code', {}, F.root)),
    h('li', {}, 'Sensitivity: ', h('code', {}, D.robustness.source)),
    h('li', {}, 'Panel: ', h('code', {}, m.panel), ` · hash ${m.panel_hash}`),
    h('li', {}, `Built ${m.generated} from code ${m.code_hash} by `, h('code', {}, 'make ui')));
  $('foot').textContent = `Every page reads recorded evidence packs; nothing is re-executed. Generated ${m.generated} · code ${m.code_hash} · panel ${m.panel_hash}. Simulated results are pipeline validation, not market forecasts.`;
}

/* ================================================================ ROUTING */
const PAGES = ['verdict', 'ripple', 'robustness', 'evidence'];
let current = null;
// Page links are handled in-page: some viewers (embedded previews, data:
// URLs) refuse hash navigation, and the page must still switch.
document.addEventListener('click', e => {
  const a = e.target.closest && e.target.closest('a[href^="#"]');
  if (!a || !PAGES.includes(a.getAttribute('href').slice(1))) return;
  e.preventDefault();
  const id = a.getAttribute('href').slice(1);
  try { history.replaceState(null, '', '#' + id); } catch (_) { /* no URL to update */ }
  route(id);
});
function route(want) {
  let id = typeof want === 'string' ? want : location.hash.slice(1);
  if (!PAGES.includes(id)) id = 'verdict';
  const changed = current !== null && current !== id;
  current = id;
  PAGES.forEach(p => $(p).hidden = p !== id);
  document.querySelectorAll('#nav a').forEach(a => a.setAttribute('aria-current', a.getAttribute('href') === '#' + id ? 'page' : 'false'));
  if (changed) window.scrollTo(0, 0);
  if (id === 'verdict' && !RM) { verdictT0 = null; requestAnimationFrame(verdictTick); }
  if (id === 'ripple') RP.start();
  if (id === 'robustness' && !RM) document.querySelectorAll('#b-svg .slide').forEach(c => { c.classList.remove('slide'); void c.getBBox(); c.classList.add('slide'); });
}
buildVerdict(); buildRobustness(); buildEvidence();
addEventListener('hashchange', route);
addEventListener('resize', () => { if (current === 'verdict' && verdictAt && RM) verdictAt(R - 1); });
route();
})();
