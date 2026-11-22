/* Backoffice TRN — conceito e código © 2026 Rúben Neves.
   Login (utilizador + senha, PBKDF2-SHA256), token do GitHub guardado cifrado (AES-GCM) com a senha,
   edição de todos os campos de content/*.json e publicação por commit (GitHub Contents API).
   O site é regenerado e publicado pela tarefa automática do GitHub (.github/workflows/publicar.yml). */
(function () {
  'use strict';
  var d = document;
  var $ = function (s, r) { return (r || d).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || d).querySelectorAll(s)); };
  var enc = new TextEncoder(), dec = new TextDecoder();
  var ls = { get: function (k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set: function (k, v) { try { localStorage.setItem(k, v); } catch (e) {} }, del: function (k) { try { localStorage.removeItem(k); } catch (e) {} } };
  var S = { repo: null, auth: null, key: null, token: null, files: {}, tab: 'site.json', labels: { groups: {}, keys: {} }, runTimer: null, idle: null };
  var TABS = [['site.json', 'Dados da empresa'], ['pt.json', 'Português'], ['en.json', 'English'], ['es.json', 'Español'], ['chooser.json', 'Página de escolha'], ['#images', 'Imagens'], ['#security', 'Segurança']];
  var HIDE = { meta: 1, files: 1, github: 1, img: 1, id: 1 };

  /* ───────── utilitários ───────── */
  function b64(u8) { var s = '', i, n = 8192; for (i = 0; i < u8.length; i += n) s += String.fromCharCode.apply(null, u8.subarray(i, i + n)); return btoa(s); }
  function unb64(s) { var r = atob(String(s).replace(/\s/g, '')), u = new Uint8Array(r.length), i; for (i = 0; i < r.length; i++) u[i] = r.charCodeAt(i); return u; }
  function norm(s) { return String(s || '').normalize('NFKC').trim().replace(/\s+/g, ' ').toLowerCase(); }
  function eq(a, b) { if (a.length !== b.length) return false; var r = 0, i; for (i = 0; i < a.length; i++) r |= a[i] ^ b[i]; return r === 0; }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  async function pbkdf2(pw, salt, iters, bytes) {
    var k = await crypto.subtle.importKey('raw', enc.encode(pw), 'PBKDF2', false, ['deriveBits']);
    return new Uint8Array(await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt: salt, iterations: iters }, k, bytes * 8));
  }
  function aesKey(raw) { return crypto.subtle.importKey('raw', raw, 'AES-GCM', false, ['encrypt', 'decrypt']); }
  async function encrypt(key, text) { var iv = crypto.getRandomValues(new Uint8Array(12)); var ct = await crypto.subtle.encrypt({ name: 'AES-GCM', iv: iv }, key, enc.encode(text)); return JSON.stringify({ iv: b64(iv), ct: b64(new Uint8Array(ct)) }); }
  async function decrypt(key, blob) { var o = JSON.parse(blob); return dec.decode(await crypto.subtle.decrypt({ name: 'AES-GCM', iv: unb64(o.iv) }, key, unb64(o.ct))); }
  function show(id) { ['v-login', 'v-nosetup', 'v-token', 'v-app'].forEach(function (v) { $('#' + v).hidden = v !== id; }); }
  function toast(msg, bad) { var t = $('#toast'); t.textContent = msg; t.className = 'toast' + (bad ? ' bad' : ''); t.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(function () { t.hidden = true; }, 6000); }
  function humanize(k) { k = String(k).replace(/_/g, ' '); return k.charAt(0).toUpperCase() + k.slice(1); }

  /* ───────── GitHub ───────── */
  async function gh(path, opt) {
    opt = opt || {};
    var h = { Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' };
    if (S.token) h.Authorization = 'Bearer ' + S.token;
    var r = await fetch('https://api.github.com/repos/' + S.repo.owner + '/' + S.repo.repo + '/' + path, { method: opt.method || 'GET', headers: h, body: opt.body ? JSON.stringify(opt.body) : undefined });
    if (!r.ok && !opt.soft) {
      var msg = r.status === 401 ? 'Token inválido ou expirado.' : r.status === 403 ? 'Sem permissão ou limite do GitHub atingido.' : r.status === 404 ? 'Ficheiro ou repositório não encontrado (ou o token não tem acesso).' : r.status === 409 || r.status === 422 ? 'Conflito: o ficheiro mudou no GitHub. Recarregue a página e repita.' : 'Erro do GitHub (' + r.status + ').';
      var e = new Error(msg); e.status = r.status; throw e;
    }
    return r;
  }
  var GEN = function () { return S.repo.generator_dir; };
  async function loadFile(name) {
    var r = await gh('contents/' + GEN() + '/content/' + name + '?ref=' + encodeURIComponent(S.repo.branch));
    var j = await r.json();
    var obj = JSON.parse(dec.decode(unb64(j.content)));
    S.files[name] = { orig: clone(obj), cur: obj, sha: j.sha };
  }
  async function putFile(path, b64content, message, sha) {
    var body = { message: message, content: b64content, branch: S.repo.branch };
    if (sha) body.sha = sha;
    var r = await gh('contents/' + path, { method: 'PUT', body: body });
    return (await r.json()).content.sha;
  }
  async function shaOf(path) { var r = await gh('contents/' + path + '?ref=' + encodeURIComponent(S.repo.branch), { soft: true }); return r.ok ? (await r.json()).sha : null; }

  /* ───────── arranque e login ───────── */
  async function boot() {
    try {
      S.repo = await (await fetch('repo.json', { cache: 'no-store' })).json();
      S.auth = await (await fetch('auth.json', { cache: 'no-store' })).json();
      try { S.labels = await (await fetch('labels.json', { cache: 'no-store' })).json(); } catch (e) {}
    } catch (e) { show('v-nosetup'); return; }
    if (S.auth.configured === false || !S.auth.hash) { show('v-nosetup'); return; }
    $('#repo-name').textContent = S.repo.owner + '/' + S.repo.repo;
    show('v-login'); $('#u').focus();
  }
  var fails = +(sessionStorage.getItem('bo-fails') || 0);
  $('#f-login').addEventListener('submit', async function (ev) {
    ev.preventDefault();
    var btn = $('#login-btn'), err = $('#login-err');
    btn.disabled = true; err.hidden = true;
    if (fails > 0) await sleep(Math.min(Math.pow(2, fails) * 500, 15000));
    var pw = $('#p').value;
    var ok = false, bits;
    try {
      bits = await pbkdf2(pw, unb64(S.auth.salt), S.auth.iterations, 64);
      ok = norm($('#u').value) === norm(S.auth.user) && eq(bits.subarray(0, 32), unb64(S.auth.hash));
    } catch (e) { ok = false; }
    $('#p').value = '';
    if (!ok) { fails++; sessionStorage.setItem('bo-fails', String(fails)); err.textContent = 'Utilizador ou senha incorretos.'; err.hidden = false; btn.disabled = false; return; }
    fails = 0; sessionStorage.removeItem('bo-fails');
    S.key = await aesKey(bits.subarray(32, 64));
    var blob = ls.get('trn-bo-token'); S.token = null;
    if (blob) { try { S.token = await decrypt(S.key, blob); } catch (e) { S.token = null; } }
    btn.disabled = false;
    if (S.token) startApp(); else show('v-token');
  });
  $('#f-token').addEventListener('submit', async function (ev) {
    ev.preventDefault();
    var t = $('#tk').value.trim(), err = $('#token-err'); err.hidden = true;
    if (!t) { err.textContent = 'Cole o token.'; err.hidden = false; return; }
    S.token = t;
    try {
      var r = await gh(''); var j = await r.json();
      if (j.permissions && j.permissions.push === false) throw new Error('Este token não tem permissão de escrita (Contents: Read and write).');
    } catch (e) { S.token = null; err.textContent = e.message; err.hidden = false; return; }
    ls.set('trn-bo-token', await encrypt(S.key, t)); $('#tk').value = '';
    startApp();
  });
  $('#token-skip').addEventListener('click', function () { S.token = null; startApp(); });

  function idle() { clearTimeout(S.idle); S.idle = setTimeout(function () { location.reload(); }, 20 * 60 * 1000); }
  ['click', 'keydown', 'mousemove', 'touchstart'].forEach(function (e) { d.addEventListener(e, function () { if (S.key) idle(); }, { passive: true }); });
  $('#logout').addEventListener('click', function () { location.reload(); });

  async function startApp() {
    show('v-app'); idle();
    $('#repo-state').textContent = S.token ? 'ligado ao GitHub' : 'só leitura';
    $('#repo-state').className = 'pill' + (S.token ? '' : ' warn');
    $('#content').textContent = 'A carregar…';
    try { await Promise.all(['site.json', 'pt.json', 'en.json', 'es.json', 'chooser.json'].map(loadFile)); }
    catch (e) { $('#content').textContent = ''; toast(e.message, true); $('#repo-state').textContent = 'sem ligação'; $('#repo-state').className = 'pill off'; return; }
    buildTabs(); openTab(S.tab);
  }

  /* ───────── separadores ───────── */
  function buildTabs() {
    var nav = $('#tabs'); nav.textContent = '';
    TABS.forEach(function (t) {
      var b = d.createElement('button'); b.type = 'button'; b.setAttribute('role', 'tab'); b.setAttribute('data-tab', t[0]); b.textContent = t[1];
      b.addEventListener('click', function () { openTab(t[0]); });
      nav.appendChild(b);
    });
  }
  function openTab(id) {
    S.tab = id; $('#q').value = '';
    $$('#tabs button').forEach(function (b) { b.setAttribute('aria-selected', String(b.getAttribute('data-tab') === id)); });
    var c = $('#content'); c.textContent = '';
    $('.search').hidden = id.charAt(0) === '#';
    if (id === '#images') renderImages(c);
    else if (id === '#security') renderSecurity(c);
    else renderFile(c, id);
    refresh();
  }

  /* ───────── edição genérica ───────── */
  function valueAt(o, path) { for (var i = 0; i < path.length; i++) { if (o == null) return undefined; o = o[path[i]]; } return o; }
  function normPath(path) { return path.map(function (k) { return typeof k === 'number' ? '*' : k; }).join('.'); }
  function labelFor(path) {
    var p = normPath(path), last = path[path.length - 1];
    if (S.labels.groups[p]) return S.labels.groups[p];
    if (typeof last === 'number') return 'Item ' + (last + 1);
    return S.labels.keys[last] || humanize(last);
  }
  function hintFor(path) { var p = normPath(path); return (S.labels.hints || {})[p] || ''; }
  function fileObj() { return S.files[S.tab].cur; }

  function renderFile(c, name) {
    var f = S.files[name], root = f.cur;
    Object.keys(root).forEach(function (k) { if (!HIDE[k]) renderNode(c, root, k, [k], name); });
  }
  function renderNode(host, parent, key, path, name) {
    var v = parent[key];
    if (HIDE[key] && typeof key === 'string') return;
    if (typeof v === 'string' || typeof v === 'number') return host.appendChild(field(parent, key, path, name));
    if (typeof v === 'boolean') return host.appendChild(checkbox(parent, key, path, name));
    if (Array.isArray(v)) return host.appendChild(listNode(parent, key, path, name));
    if (v && typeof v === 'object') {
      var g = d.createElement('details'); g.className = 'grp'; g.open = path.length === 1 && false;
      var s = d.createElement('summary'); s.textContent = labelFor(path); g.appendChild(s);
      var inn = d.createElement('div'); inn.className = 'in'; g.appendChild(inn);
      Object.keys(v).forEach(function (k) { if (!HIDE[k]) renderNode(inn, v, k, path.concat([k]), name); });
      return host.appendChild(g);
    }
  }
  function field(parent, key, path, name) {
    var v = parent[key], w = d.createElement('div'), id = 'f' + Math.random().toString(36).slice(2, 9);
    w.className = 'fld'; w.setAttribute('data-path', path.join('/'));
    var lab = d.createElement('label'); lab.setAttribute('for', id); lab.textContent = labelFor(path); w.appendChild(lab);
    var html = /^legal\.(privacy|cookies)$/.test(normPath(path));
    var long = html || (typeof v === 'string' && (v.length > 80 || v.indexOf('\n') > -1));
    var el = d.createElement(long ? 'textarea' : 'input'); el.id = id;
    if (!long) el.type = typeof v === 'number' ? 'number' : 'text';
    if (html) el.className = 'mono';
    el.value = v == null ? '' : v;
    el.addEventListener('input', function () { parent[key] = typeof v === 'number' ? Number(el.value) : el.value; touch(w, name, path, el); });
    w.appendChild(el);
    var h = hintFor(path) || (html ? 'Texto em HTML: pode usar <p>, <strong>, <h2>, <ul>… Os campos [entre parênteses retos] são marcadores a preencher.' : '');
    if (h) { var hh = d.createElement('div'); hh.className = 'hint'; hh.textContent = h; w.appendChild(hh); }
    w.setAttribute('data-q', (lab.textContent + ' ' + el.value).toLowerCase());
    if (!el.value) w.classList.add('empty');
    return w;
  }
  function checkbox(parent, key, path, name) {
    var w = d.createElement('div'); w.className = 'fld'; w.setAttribute('data-path', path.join('/'));
    var l = d.createElement('label'); l.className = 'chk'; var i = d.createElement('input'); i.type = 'checkbox'; i.checked = !!parent[key];
    l.appendChild(i); l.appendChild(d.createTextNode(' ' + labelFor(path)));
    i.addEventListener('change', function () { parent[key] = i.checked; touch(w, name, path, i); });
    w.appendChild(l); var h = hintFor(path); if (h) { var hh = d.createElement('div'); hh.className = 'hint'; hh.textContent = h; w.appendChild(hh); }
    w.setAttribute('data-q', labelFor(path).toLowerCase());
    return w;
  }
  function template(arr) {
    if (!arr.length) return '';
    return JSON.parse(JSON.stringify(arr[0], function (k, v) { return typeof v === 'string' ? '' : v; }));
  }
  function listNode(parent, key, path, name) {
    var arr = parent[key], g = d.createElement('details'); g.className = 'grp'; g.open = arr.length > 0 && arr.length < 8 && path.length > 1;
    var s = d.createElement('summary'); s.textContent = labelFor(path) + ' (' + arr.length + ')'; g.appendChild(s);
    var inn = d.createElement('div'); inn.className = 'in'; g.appendChild(inn);
    arr.forEach(function (it, i) {
      var p = path.concat([i]);
      if (typeof it === 'string') {
        var row = d.createElement('div'); row.className = 'row';
        var fw = field(arr, i, p, name); fw.querySelector('label').textContent = labelFor(p); row.appendChild(fw); row.appendChild(tools(arr, i, name));
        inn.appendChild(row);
      } else {
        var box = d.createElement('div'); box.className = 'item';
        var hd = d.createElement('div'); hd.className = 'itemhead'; var t = d.createElement('span'); t.textContent = labelFor(path).replace(/s$/, '') + ' ' + (i + 1); hd.appendChild(t); hd.appendChild(tools(arr, i, name)); box.appendChild(hd);
        if (Array.isArray(it)) { it.forEach(function (_, j) { renderNode(box, it, j, p.concat([j]), name); }); }
        else Object.keys(it).forEach(function (k) { if (!HIDE[k]) renderNode(box, it, k, p.concat([k]), name); });
        inn.appendChild(box);
      }
    });
    var add = d.createElement('button'); add.type = 'button'; add.className = 'btn btn--line sm add'; add.textContent = '+ Adicionar';
    add.addEventListener('click', function () { arr.push(typeof arr[0] === 'string' || !arr.length ? '' : template(arr)); touch(null, name, path); openTab(S.tab); });
    inn.appendChild(add);
    return g;
  }
  function tools(arr, i, name) {
    var t = d.createElement('div'); t.className = 'tools';
    [['↑', 'Subir', -1], ['↓', 'Descer', 1], ['×', 'Remover', 0]].forEach(function (x) {
      var b = d.createElement('button'); b.type = 'button'; b.textContent = x[0]; b.setAttribute('aria-label', x[1]);
      b.addEventListener('click', function () {
        if (x[2] === 0) { if (!confirm('Remover este item?')) return; arr.splice(i, 1); }
        else { var j = i + x[2]; if (j < 0 || j >= arr.length) return; var tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp; }
        touch(null, name); var y = window.scrollY; openTab(S.tab); window.scrollTo(0, y);
      });
      t.appendChild(b);
    });
    return t;
  }
  function touch(w, name, path, el) {
    if (w && path) {
      var cur = valueAt(S.files[name].cur, path), orig = valueAt(S.files[name].orig, path);
      w.classList.toggle('changed', JSON.stringify(cur) !== JSON.stringify(orig));
      w.classList.toggle('empty', cur === '' || cur == null);
      var lab = w.querySelector('label'); w.setAttribute('data-q', ((lab ? lab.textContent : '') + ' ' + (typeof cur === 'string' ? cur : '')).toLowerCase());
    }
    refresh();
  }
  function countDiff(a, b) {
    if (typeof a !== 'object' || a === null || typeof b !== 'object' || b === null) return JSON.stringify(a) === JSON.stringify(b) ? 0 : 1;
    var n = 0, keys = {}; Object.keys(a).forEach(function (k) { keys[k] = 1; }); Object.keys(b).forEach(function (k) { keys[k] = 1; });
    Object.keys(keys).forEach(function (k) { n += countDiff(a[k], b[k]); });
    return n;
  }
  function dirtyFiles() { return Object.keys(S.files).filter(function (n) { return JSON.stringify(S.files[n].cur) !== JSON.stringify(S.files[n].orig); }); }
  function refresh() {
    var dirty = dirtyFiles(), total = dirty.reduce(function (s, n) { return s + Math.max(1, countDiff(S.files[n].orig, S.files[n].cur)); }, 0);
    $$('#tabs button').forEach(function (b) { var n = b.getAttribute('data-tab'), has = dirty.indexOf(n) > -1; var dot = $('.dot', b); if (has && !dot) { var s = d.createElement('span'); s.className = 'dot'; s.setAttribute('aria-label', 'com alterações'); b.appendChild(s); } else if (!has && dot) dot.remove(); });
    $('#bar-msg').textContent = total ? total + ' alteração(ões) em ' + dirty.length + ' ficheiro(s), ainda não publicadas.' : (S.runMsg || 'Sem alterações.');
    $('#publish').disabled = !total || !S.token; $('#discard').disabled = !total;
    $('#publish').title = S.token ? '' : 'Sem token do GitHub: só leitura.';
  }
  $('#q').addEventListener('input', function () {
    var q = this.value.trim().toLowerCase();
    $$('#content .fld').forEach(function (f) { f.hidden = !!q && (f.getAttribute('data-q') || '').indexOf(q) === -1; });
    $$('#content details.grp').forEach(function (g) { var has = !!$('.fld:not([hidden])', g); g.hidden = !!q && !has; if (q && has) g.open = true; });
  });
  $('#discard').addEventListener('click', function () {
    if (!confirm('Descartar todas as alterações ainda não publicadas?')) return;
    Object.keys(S.files).forEach(function (n) { S.files[n].cur = clone(S.files[n].orig); }); openTab(S.tab);
  });

  /* ───────── publicar ───────── */
  $('#publish').addEventListener('click', async function () {
    var dirty = dirtyFiles(); if (!dirty.length || !S.token) return;
    var total = dirty.reduce(function (s, n) { return s + Math.max(1, countDiff(S.files[n].orig, S.files[n].cur)); }, 0);
    if (!confirm('Publicar ' + total + ' alteração(ões) em: ' + dirty.join(', ') + '?\nO site é refeito automaticamente e fica atualizado em 2 a 3 minutos.')) return;
    $('#publish').disabled = true; $('#bar-msg').textContent = 'A publicar…';
    try {
      for (var i = 0; i < dirty.length; i++) {
        var n = dirty[i], f = S.files[n];
        f.sha = await putFile(GEN() + '/content/' + n, b64(enc.encode(JSON.stringify(f.cur, null, 1) + '\n')), 'Backoffice (ADMIN TIC): ' + n, f.sha);
        f.orig = clone(f.cur);
      }
    } catch (e) { toast(e.message, true); refresh(); return; }
    toast('Publicado. O site atualiza em 2 a 3 minutos.');
    $$('#content .fld').forEach(function (x) { x.classList.remove('changed'); });
    refresh(); watchRun();
  });
  async function watchRun() {
    clearTimeout(S.runTimer); var tries = 0;
    async function poll() {
      tries++;
      try {
        var r = await gh('actions/runs?branch=' + encodeURIComponent(S.repo.branch) + '&per_page=1', { soft: true });
        if (r.ok) {
          var run = (await r.json()).workflow_runs[0];
          if (run) {
            S.runMsg = run.status === 'completed' ? (run.conclusion === 'success' ? 'Publicado: o site já está atualizado.' : 'A publicação falhou (' + run.conclusion + '). Veja o separador Actions no GitHub.') : 'A publicar o site… (' + run.status + ')';
            refresh(); if (run.status === 'completed') return;
          }
        } else { S.runMsg = 'Publicado. Atualiza em 2 a 3 minutos.'; refresh(); return; }
      } catch (e) { return; }
      if (tries < 40) S.runTimer = setTimeout(poll, 8000);
    }
    S.runTimer = setTimeout(poll, 4000);
  }

  /* ───────── imagens ───────── */
  function renderImages(c) {
    var ids = Object.keys(S.files['pt.json'].cur.images || {});
    var p = d.createElement('p'); p.className = 'muted'; p.textContent = 'Substitua uma fotografia. É redimensionada no navegador e enviada nos tamanhos que o site usa. O texto alternativo edita-se nos separadores de cada idioma ("Texto alternativo das fotografias").'; c.appendChild(p);
    var grid = d.createElement('div'); grid.className = 'imgs'; c.appendChild(grid);
    ids.forEach(function (id) {
      var card = d.createElement('div'); card.className = 'imgcard';
      var im = d.createElement('img'); im.src = '../assets/img/' + id + '-640.jpg'; im.alt = S.files['pt.json'].cur.images[id]; card.appendChild(im);
      var t = d.createElement('strong'); t.textContent = (S.labels.keys[id] || id); card.appendChild(t);
      var inp = d.createElement('input'); inp.type = 'file'; inp.accept = 'image/jpeg,image/png,image/webp'; inp.setAttribute('aria-label', 'Nova fotografia para ' + (S.labels.keys[id] || id)); inp.setAttribute('data-img', id); card.appendChild(inp);
      var b = d.createElement('button'); b.type = 'button'; b.className = 'btn btn--red sm'; b.textContent = 'Substituir e publicar'; b.disabled = !S.token;
      b.addEventListener('click', function () { if (!inp.files.length) return toast('Escolha primeiro um ficheiro.', true); replaceImage(id, inp.files[0], b); });
      card.appendChild(b); grid.appendChild(card);
    });
  }
  async function toJpeg(bmp, w) {
    var tw = Math.min(w, bmp.width), th = Math.round(bmp.height * tw / bmp.width), cv = d.createElement('canvas'); cv.width = tw; cv.height = th;
    var ctx = cv.getContext('2d'); ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, tw, th); ctx.drawImage(bmp, 0, 0, tw, th);
    var q = 0.86, blob;
    for (; q >= 0.5; q -= 0.06) { blob = await new Promise(function (r) { cv.toBlob(r, 'image/jpeg', q); }); if (blob.size <= 245 * 1024) break; }
    return blob;
  }
  async function replaceImage(id, file, btn) {
    if (!S.token) return;
    if (!confirm('Substituir a fotografia «' + (S.labels.keys[id] || id) + '» e publicar?')) return;
    btn.disabled = true;
    try {
      var bmp = await createImageBitmap(file), widths = id === 'trn_frota' ? [640, 1024, 1600] : [640, 1024];
      for (var i = 0; i < widths.length; i++) {
        var blob = await toJpeg(bmp, widths[i]), path = GEN() + '/static/img/' + id + '-' + widths[i] + '.jpg';
        await putFile(path, b64(new Uint8Array(await blob.arrayBuffer())), 'Backoffice (ADMIN TIC): imagem ' + id + ' ' + widths[i] + 'px', await shaOf(path));
      }
      toast('Fotografia enviada. O site atualiza em 2 a 3 minutos.'); watchRun();
    } catch (e) { toast(e.message, true); }
    btn.disabled = !S.token;
  }

  /* ───────── segurança ───────── */
  function renderSecurity(c) {
    c.innerHTML = '';
    var box = d.createElement('div'); box.className = 'card'; box.style.padding = '18px';
    box.innerHTML = '<h2>Alterar a senha</h2><p class="muted">A nova senha passa a valer depois de o site ser refeito (2 a 3 minutos). Mínimo 12 caracteres.</p>' +
      '<form id="f-pw" novalidate><label for="pw0">Senha atual</label><input id="pw0" type="password" autocomplete="current-password">' +
      '<label for="pw1">Nova senha</label><input id="pw1" type="password" autocomplete="new-password"><label for="pw2">Repetir a nova senha</label><input id="pw2" type="password" autocomplete="new-password">' +
      '<p class="err" id="pw-err" role="alert" hidden></p><p></p><button class="btn btn--red" type="submit">Alterar senha</button></form>';
    c.appendChild(box);
    var b2 = d.createElement('div'); b2.className = 'card'; b2.style.cssText = 'padding:18px;margin-top:14px';
    b2.innerHTML = '<h2>Token do GitHub</h2><p class="muted">O token está guardado, cifrado com a sua senha, só neste navegador.</p><button class="btn btn--line" id="rm-token" type="button">Remover o token deste navegador</button>';
    c.appendChild(b2);
    $('#rm-token').addEventListener('click', function () { if (confirm('Remover o token deste navegador? Terá de o colar de novo no próximo acesso.')) { ls.del('trn-bo-token'); toast('Token removido.'); } });
    $('#f-pw').addEventListener('submit', async function (ev) {
      ev.preventDefault(); var err = $('#pw-err'); err.hidden = true;
      var p0 = $('#pw0').value, p1 = $('#pw1').value, p2 = $('#pw2').value;
      function bad(m) { err.textContent = m; err.hidden = false; }
      if (!S.token) return bad('Sem token do GitHub: não é possível publicar a nova senha.');
      if (p1.length < 12) return bad('A nova senha precisa de pelo menos 12 caracteres.');
      if (p1 !== p2) return bad('As senhas novas não coincidem.');
      var cur = await pbkdf2(p0, unb64(S.auth.salt), S.auth.iterations, 64);
      if (!eq(cur.subarray(0, 32), unb64(S.auth.hash))) return bad('A senha atual está incorreta.');
      var salt = crypto.getRandomValues(new Uint8Array(16)), bits = await pbkdf2(p1, salt, S.auth.iterations, 64);
      var next = { user: S.auth.user, kdf: 'pbkdf2-sha256', iterations: S.auth.iterations, salt: b64(salt), hash: b64(bits.subarray(0, 32)) };
      try { var path = GEN() + '/content/admin.json'; await putFile(path, b64(enc.encode(JSON.stringify(next, null, 1) + '\n')), 'Backoffice (ADMIN TIC): alteração de senha', await shaOf(path)); }
      catch (e) { return bad(e.message); }
      S.key = await aesKey(bits.subarray(32, 64)); S.auth = next; ls.set('trn-bo-token', await encrypt(S.key, S.token));
      ['pw0', 'pw1', 'pw2'].forEach(function (i) { $('#' + i).value = ''; });
      toast('Senha alterada. Passa a valer em 2 a 3 minutos.'); watchRun();
    });
  }

  boot();
})();
