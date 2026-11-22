#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera o site estático com as Opções A e B (PT/EN/ES).

  python3 gerar.py                gera ../TRN-propostas-A-B
  python3 gerar.py --out PASTA    gera noutra pasta (usado pela publicação automática no GitHub)
  python3 gerar.py --senha        define a senha do backoffice (pede-a no terminal, não fica escrita em lado nenhum)

Todo o conteúdo editável está em content/*.json (site.json, pt.json, en.json, es.json, chooser.json) e pode ser
editado no backoffice (admin/). Telefone, WhatsApp e Formspree estão em content/site.json."""
import argparse, getpass, base64, hashlib, html, json, os, pathlib, re, shutil, struct

HERE = pathlib.Path(__file__).resolve().parent


def _json(name):
    return json.loads((HERE / 'content' / name).read_text(encoding='utf-8'))


SITE = _json('site.json')
LANGS = {l: _json(l + '.json') for l in ('pt', 'en', 'es')}
CHOOSER = _json('chooser.json')
COMPANY = SITE['company']
ADDRESS = SITE['address']
GARAGE = SITE['garage']
EMAIL = SITE['email']
PHONE = SITE['phone']
WA = re.sub(r'\D', '', SITE.get('whatsapp', ''))
PHONE_TEL = re.sub(r'[^\d+]', '', PHONE)
SERVICE_KEYS = ['workers', 'school', 'tours', 'groups', 'events', 'executive']
OUT = HERE.parent / 'TRN-propostas-A-B'
BASE = SITE['base_url'].rstrip('/') + '/'      # endereço base único (canonical, hreflang, og:url, og:image)
OG_IMAGE = BASE + 'assets/img/og-trn.jpg'
OG_ALT = {l: LANGS[l]['og_alt'] for l in LANGS}
ALT = {l: LANGS[l]['images'] for l in LANGS}
NOINDEX = bool(SITE.get('noindex', True))     # True enquanto for proposta
ROBOTS_META = '<meta name="robots" content="noindex, nofollow">' if NOINDEX else '<meta name="robots" content="index, follow">'


def jpeg_size(p):
    """largura e altura de um JPEG, lidas do cabeçalho (sem bibliotecas externas)"""
    d = p.read_bytes()
    i = 2
    while i < len(d):
        if d[i] != 0xFF:
            i += 1
            continue
        m = d[i + 1]
        if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
            h, w = struct.unpack('>HH', d[i + 5:i + 9])
            return w, h
        i += 2 + struct.unpack('>H', d[i + 2:i + 4])[0]
    raise ValueError('JPEG inválido: %s' % p)


SIZES = {}
for _f in sorted((HERE / 'static' / 'img').glob('*-*.jpg')):
    _m = re.match(r'(.+)-(\d+)\.jpg$', _f.name)
    if _m:
        SIZES.setdefault(_m.group(1), {})[_m.group(2)] = list(jpeg_size(_f))
e = html.escape
OPTS = ('a',)      # a Opção B foi descartada pelo cliente; o código de b_home() fica só como arquivo
PAX = 'min="1" max="500" inputmode="numeric"'

ICONS = {
    'workers': '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>',
    'school': '<path d="M2 9l10-5 10 5-10 5-10-5z"/><path d="M6 11v5c0 1.5 3 3 6 3s6-1.5 6-3v-5"/>',
    'tours': '<path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
    'groups': '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.5"/><path d="M17 14c2.5 0 4.5 2 4.5 4.5"/>',
    'events': '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    'executive': '<path d="M3 13l2-6a2 2 0 0 1 2-1h10a2 2 0 0 1 2 1l2 6v4h-2"/><path d="M5 17H3v-4h18"/><circle cx="7.5" cy="17" r="1.8"/><circle cx="16.5" cy="17" r="1.8"/>',
    'phone': '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2z"/>',
    'wa': '<path d="M21 11.5a8.4 8.4 0 0 1-12.4 7.4L3 21l2.1-5.4A8.4 8.4 0 1 1 21 11.5z"/>',
    'mail': '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/>',
    'pin': '<path d="M12 21s7-6.2 7-11a7 7 0 1 0-14 0c0 4.8 7 11 7 11z"/><circle cx="12" cy="10" r="2.5"/>',
}


def ico(k, s=22, cls=''):
    return f'<svg class="i {cls}" viewBox="0 0 24 24" width="{s}" height="{s}" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">{ICONS[k]}</svg>'


def img(mid, alt, sizes='100vw', lazy=True, cls='', pos=''):
    ws = sorted(int(w) for w in SIZES[mid])
    ss = ', '.join(f'../../assets/img/{mid}-{w}.jpg {w}w' for w in ws)
    w, h = SIZES[mid][str(ws[-1] if len(ws) < 3 else ws[1])]
    src = f'../../assets/img/{mid}-{ws[-1] if len(ws) < 3 else ws[1]}.jpg'
    st = f' style="object-position:{pos}"' if pos else ''
    lz = ' loading="lazy" decoding="async"' if lazy else ' fetchpriority="high"'
    return f'<img src="{src}" srcset="{ss}" sizes="{sizes}" width="{w}" height="{h}" alt="{e(alt)}" class="{cls}"{st}{lz}>'


def path(opt, lang, page):
    return f'opcao-{opt}/{lang}/{LANGS[lang]["files"][page]}'


def link(lang, page, anchor=''):
    return LANGS[lang]['files'][page] + anchor


def swoosh(light=False):
    return ('<svg class="swoosh' + (' swoosh--light' if light else '') + '" viewBox="0 0 1440 90" preserveAspectRatio="none" aria-hidden="true" focusable="false">'
            '<defs><linearGradient id="sg' + ('l' if light else 'd') + '" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ECEEF0"/><stop offset=".55" stop-color="#C3C8CD"/><stop offset="1" stop-color="#A3AAB1"/></linearGradient></defs>'
            '<path d="M0,78 C380,32 860,14 1440,18 L1440,90 L0,90 Z" fill="#fff"/>'
            '<path d="M0,78 C380,32 860,14 1440,18 L1440,50 C900,48 420,62 0,84 Z" fill="url(#sg' + ('l' if light else 'd') + ')"/>'
            '<path class="stripe" d="M0,84 C480,64 980,56 1440,54" fill="none" stroke="#D9822B" stroke-width="6"/></svg>')


def contact_lines(L, cls='cc'):
    return (f'<a class="{cls} js-phone" href="tel:{PHONE_TEL}">{ico("phone")}<span><small>{e(L["phone_label"])}</small><b data-ph="phone">{PHONE}</b></span></a>'
            + (f'<a class="{cls} js-wa" href="https://wa.me/{WA}" target="_blank" rel="noopener">{ico("wa")}<span><small>WhatsApp</small><b data-ph="wa">{e(SITE["whatsapp"])}</b></span></a>' if WA else '') +
            f'<a class="{cls}" href="mailto:{EMAIL}">{ico("mail")}<span><small>{e(L["email_label"])}</small><b>{EMAIL}</b></span></a>'
            f'<div class="{cls}">{ico("pin")}<span><small>{e(L["address_label"])}</small><b>{e(ADDRESS[0])}<br>{e(ADDRESS[1])}</b></span></div>'
            f'<div class="{cls}">{ico("pin")}<span><small>{e(L["garage_label"])}</small><b>{e(GARAGE[0])}<br>{e(GARAGE[1])}</b></span></div>')


def fld(i, label, kind='text', req=False, ph='', attrs='', name=None):
    r = ' required aria-required="true"' if req else ''
    nm = name or i.split('-', 1)[1]
    if kind == 'textarea':
        c = f'<textarea id="{i}" name="{nm}" rows="3"{r}></textarea>'
    else:
        c = f'<input id="{i}" name="{nm}" type="{kind}" placeholder="{e(ph)}"{r} {attrs}>'
    return f'<div class="fld"><label for="{i}">{e(label)}</label>{c}<span class="err" id="{i}-e" role="alert"></span></div>'


def quote_modal(L):
    q = L['q']
    opts = ''.join(f'<option value="{k}">{e(L["services"][k]["name"])}</option>' for k in SERVICE_KEYS)
    msgs = {k: q[k] for k in ('required', 'bad_email', 'got_t', 'got_x', 'mail_hint', 'fail', 'spam', 'sending', 'subject', 'send', 'step')}
    msgs.update({'from': q['from'], 'to': q['to'], 'date': q['date'], 'pax': q['pax'], 'service': q['service'], 'name': q['name'], 'email': q['email'], 'phone': q['phone'], 'notes': q['notes']})
    priv = link(L['code'], 'legal', '#privacidade')
    return (f'<div class="modal" id="m-quote" role="dialog" aria-modal="true" aria-labelledby="m-quote-t" hidden><div class="modal__box">'
            f'<button type="button" class="modal__x" data-close aria-label="{e(L["nav"]["close"])}">×</button>'
            f'<h2 id="m-quote-t">{e(q["title"])}</h2><p class="sub">{e(q["sub"])}</p>'
            f'<form id="quote" action="https://formspree.io/f/[ID]" method="POST" novalidate data-msgs=\'{e(json.dumps(msgs, ensure_ascii=False), quote=True)}\'>'
            f'<p class="stepno" id="stepno" aria-live="polite">{e(q["step"].format(n=1))}</p>'
            f'<fieldset class="step" data-step="1"><legend>{e(q["s1"])}</legend>'
            f'<div class="row2">{fld("q-from", q["from"], req=True, name="partida")}{fld("q-to", q["to"], req=True, name="destino")}</div>'
            f'<div class="row2">{fld("q-date", q["date"], "date", req=True, name="data")}{fld("q-pax", q["pax"], "number", req=True, attrs=PAX, name="passageiros")}</div>'
            f'<div class="actions"><button type="button" class="btn btn--red" data-next>{e(q["next"])}</button></div></fieldset>'
            f'<fieldset class="step" data-step="2" hidden><legend>{e(q["s2"])}</legend>'
            f'<div class="fld"><label for="q-service">{e(q["service"])}</label><select id="q-service" name="servico">{opts}</select></div>'
            f'<div class="row2">{fld("q-name", q["name"], req=True, name="nome")}{fld("q-phone", q["phone"], "tel", name="telefone")}</div>'
            f'{fld("q-email", q["email"], "email", req=True, name="email")}{fld("q-notes", q["notes"], "textarea", name="observacoes")}'
            f'<p class="note">{e(q["privacy"])} <a href="{priv}">{e(q["privacy_link"])}</a>.</p>'
            '<div class="hp" aria-hidden="true"><label>Website<input type="text" name="_gotcha" tabindex="-1" autocomplete="off"></label></div>'
            f'<div class="msg" id="qmsg" role="alert" hidden></div>'
            f'<div class="actions"><button type="button" class="btn btn--line" data-back>{e(q["back"])}</button><button type="submit" class="btn btn--red" id="qsend">{e(q["send"])}</button></div></fieldset>'
            f'<div class="done" id="qdone" role="status" hidden><h3>{e(q["got_t"])}</h3><p>{e(q["got_x"])} <strong id="qref"></strong></p></div>'
            '</form></div></div>')


def workers_modal(L):
    w = L['workers']
    steps = ''.join(f'<li><strong>{e(t)}</strong><span>{e(d)}</span></li>' for t, d in w['steps'])
    perks = ''.join(f'<li>{e(p)}</li>' for p in w['perks'])
    return (f'<div class="modal" id="m-workers" role="dialog" aria-modal="true" aria-labelledby="m-workers-t" hidden><div class="modal__box modal__box--wide">'
            f'<button type="button" class="modal__x" data-close aria-label="{e(L["nav"]["close"])}">×</button>'
            f'<h2 id="m-workers-t">{e(w["title"])}</h2><p class="sub">{e(w["intro"])}</p>'
            f'<ol class="wsteps">{steps}</ol><ul class="perks">{perks}</ul><p class="note">{e(w["note"])}</p>'
            f'<button type="button" class="btn btn--red" data-open-quote data-service="workers">{e(w["cta"])}</button></div></div>')


def layout(opt, lang, page, title, body, desc=None, modals=''):
    L = LANGS[lang]
    n = L['nav']
    desc = desc or L['descs'][page]
    base = f'{BASE}'
    here = lambda l: f'{BASE}{path(opt, l, page)}'
    alts = f'<link rel="canonical" href="{here(lang)}">' + ''.join(f'<link rel="alternate" hreflang="{l}" href="{here(l)}">' for l in LANGS) + f'<link rel="alternate" hreflang="x-default" href="{here("pt")}">'
    og = (f'<meta property="og:type" content="website"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">'
          f'<meta property="og:url" content="{here(lang)}"><meta property="og:image" content="{OG_IMAGE}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{e(OG_ALT[lang])}">'
          f'<meta property="og:locale" content="{L["og"]}"><meta name="twitter:card" content="summary_large_image">')
    on_home = page == 'home'
    def a(anchor): return (anchor if on_home else link(lang, 'home', anchor))
    nav = (f'<nav class="main" id="menu" aria-label="{e(n["menu"])}">'
           f'<a class="l" href="{a("#servicos")}">{e(n["services"])}</a><a class="l" href="{a("#frota")}">{e(n["fleet"])}</a>'
           f'<a class="l" href="{a("#perguntas")}">{e(n["faq"])}</a><a class="l" href="{a("#contactos")}">{e(n["contact"])}</a></nav>')
    langs = ''.join(f'<a href="../{l}/{LANGS[l]["files"][page]}" hreflang="{l}" lang="{l}"' + (' aria-current="true"' if l == lang else '') + f'>{LANGS[l]["label"]}</a>' for l in LANGS)
    header = (f'<header class="site"><div class="wrap">'
              f'<a class="brand" href="{link(lang, "home")}" aria-label="{e(n["home_aria"])}"><img src="../../assets/img/logo-trn.svg" alt="TRN — Rodoviária Internacional e Nacional, Lda." width="124" height="52"></a>'
              f'{nav}'
              f'<div class="hd-right"><a class="hd-c js-phone" href="tel:{PHONE_TEL}" aria-label="{e(n["call"])} {PHONE}">{ico("phone", 20)}<b data-ph="phone">{PHONE}</b></a>'
              + (f'<a class="hd-c hd-c--wa js-wa" href="https://wa.me/{WA}" target="_blank" rel="noopener" aria-label="WhatsApp">{ico("wa", 20)}<b>WhatsApp</b></a>' if WA else '') +
              f'<div class="lang" role="group" aria-label="{e(n["lang"])}">{langs}</div>'
              f'<button type="button" class="btn btn--red hd-cta" data-open-quote>{e(n["quote"])}</button>'
              f'<button class="burger" type="button" aria-label="{e(n["menu"])}" aria-expanded="false" aria-controls="menu"><svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg></button></div>'
              '</div></header>')
    f = L['footer']
    tr = f' <span class="tr">({e(f["complaints_tr"])})</span>' if f['complaints_tr'] else ''
    fcontacts = (f'<div class="fct"><p><b>{e(L["address_label"])}</b><br>{e(ADDRESS[0])}<br>{e(ADDRESS[1])}</p>'
                 f'<p><b>{e(L["garage_label"])}</b><br>{e(GARAGE[0])}<br>{e(GARAGE[1])}</p>'
                 f'<p><a href="tel:{PHONE_TEL}">{PHONE}</a><br><a href="mailto:{EMAIL}">{EMAIL}</a></p></div>')
    footer = (f'<footer class="site"><div class="wrap">{fcontacts}<div class="ft"><a class="brand" href="{link(lang, "home")}"><img src="../../assets/img/logo-trn.svg" alt="TRN — Rodoviária Internacional e Nacional, Lda." width="124" height="52"></a>'
              f'<p class="fl"><a href="{link(lang, "careers")}">{e(f["careers"])}</a> · <a href="{link(lang, "legal", "#privacidade")}">{e(f["privacy"])}</a> · <a href="{link(lang, "legal", "#cookies")}">{e(f["cookies"])}</a> · '
              f'<a href="https://www.livroreclamacoes.pt" target="_blank" rel="noopener">{e(f["complaints"])}</a>{tr}</p></div>'
              f'<div class="bot"><span>{e(f["rights"])}</span><span>{e(f["author"])}</span></div></div></footer>')
    c = L['cookie']
    cookie = (f'<div class="cookie" id="cookie" role="dialog" aria-label="Cookies" hidden><p>{e(c["text"])} <a href="{link(lang, "legal", "#cookies")}">{e(c["more"])}</a></p>'
              f'<div class="cookie__b"><button type="button" class="btn btn--red" data-cookie="yes">{e(c["yes"])}</button><button type="button" class="btn btn--line" data-cookie="no">{e(c["no"])}</button></div></div>')
    wafloat = f'<a class="wafloat js-wa" href="https://wa.me/{WA}" target="_blank" rel="noopener" aria-label="WhatsApp">{ico("wa", 30)}</a>' if WA else ''
    ld = json.dumps({"@context": "https://schema.org", "@type": "LocalBusiness", "name": COMPANY, "email": EMAIL,
                     "address": {"@type": "PostalAddress", "streetAddress": "Rua Padre António Vieira, n.º 2", "postalCode": "2700-632", "addressLocality": "Amadora", "addressCountry": "PT"}, "telephone": PHONE_TEL}, ensure_ascii=False)
    return f'''<!doctype html>
<html lang="{L['locale']}">
<head>
<meta charset="utf-8">
<title>{e(title)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{e(desc)}">
{ROBOTS_META}
<meta name="theme-color" content="#23282D">
{alts}
{og}
<link rel="icon" type="image/svg+xml" href="../../assets/img/logo-trn.svg">
<link rel="preload" href="../../assets/fonts/archivo.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="../../assets/css/base.css">
<link rel="stylesheet" href="../../assets/css/{opt}.css">
<script type="application/ld+json">{ld}</script>
</head>
<body class="opt-{opt} page-{page}">
<a class="skip" href="#conteudo">{e(n['skip'])}</a>
{header}
<main id="conteudo">
{body}
</main>
{footer}{wafloat}{cookie}{modals}
<script src="../../assets/js/config.js"></script>
<script src="../../assets/js/site.js" defer></script>
</body>
</html>'''


def modals_home(L): return quote_modal(L) + workers_modal(L)


# ───────── OPÇÃO A ─────────
def a_home(lang):
    L = LANGS[lang]; a = L['a']; q = L['quick']; alt = ALT[lang]
    quick = (f'<form class="qcard" id="quick" novalidate aria-label="{e(q["title"])}"><h2>{e(q["title"])}</h2>'
             f'<div class="qf"><label for="h-from">{e(q["from"])}</label><input id="h-from" type="text" autocomplete="off" placeholder="{e(q["ph_from"])}"></div>'
             f'<div class="qf"><label for="h-to">{e(q["to"])}</label><input id="h-to" type="text" autocomplete="off" placeholder="{e(q["ph_to"])}"></div>'
             f'<div class="qrow"><div class="qf"><label for="h-date">{e(q["date"])}</label><input id="h-date" type="date"></div><div class="qf"><label for="h-pax">{e(q["pax"])}</label><input id="h-pax" type="number" min="1" max="500" inputmode="numeric"></div></div>'
             f'<button class="btn btn--red" type="submit">{e(q["go"])}</button><p class="qn">{e(q["note"])}</p></form>')
    hero = (f'<section class="a-hero"><div class="wrap a-hero__grid"><div class="a-hero__txt"><h1>{e(a["h1"])}</h1><p class="a-sub">{e(a["sub"])}</p><p class="a-line">{e(a["line"])}</p>'
            f'<div class="cta-row"><button type="button" class="btn btn--red" data-open-quote>{e(a["cta1"])}</button><a class="btn btn--ghost" href="#frota">{e(a["cta2"])}</a></div></div>{quick}</div>'
            f'<div class="a-pano">{img("trn_frota", alt["trn_frota"], sizes="100vw", lazy=False)}</div>{swoosh()}</section>')
    s = L['services']
    wk = s['workers']
    big = (f'<article class="svc svc--big"><span class="svc__ico">{ico("workers", 30)}</span><div><h3>{e(wk["name"])}</h3><p>{e(wk["text"])}</p>'
           f'<ul class="chips">' + ''.join(f'<li>{e(p)}</li>' for p in L['workers']['perks'][:3]) + '</ul></div>'
           f'<div class="svc__cta"><button type="button" class="btn btn--red" data-open-workers>{e(a["workers_btn"])}</button></div></article>')
    small = ''.join(f'<article class="svc"><span class="svc__ico">{ico(k)}</span><h3>{e(s[k]["name"])}</h3><p>{e(s[k]["text"])}</p></article>' for k in SERVICE_KEYS[1:])
    services = f'<section class="sec" id="servicos"><div class="wrap"><div class="head"><h2 class="title">{e(a["services_t"])}</h2></div>{big}<div class="svc-grid">{small}</div></div></section>'
    cards = ''.join(f'<article class="fcard"><div class="fcard__img">{img(it["img"], alt[it["img"]], sizes="(min-width:900px) 270px, 46vw", pos="50% 66%" if it["id"] == "minibus" else "50% 55%")}</div><div class="fcard__b"><h3>{e(it["name"])}</h3><span class="cap">{e(it["cap"])}</span><p>{e(it["text"])}</p></div></article>' for it in L['fleet4'])
    am = L['amen']
    amen = f'<p class="amen"><b>{e(am["title"])}:</b> ' + ' · '.join(e(x) for x in am['items']) + f' <em>({e(am["note"])})</em></p>'
    fleet = f'<section class="sec sec--grey" id="frota"><div class="wrap"><div class="head"><h2 class="title">{e(a["fleet_t"])}</h2></div><div class="fgrid">{cards}</div>{amen}</div></section>'
    video = (f'<section class="sec" id="video"><div class="wrap vid"><div class="head"><h2 class="title">{e(a["video_t"])}</h2><p class="lead">{e(a["video_l"])}</p></div>'
             f'<video controls playsinline preload="none" poster="../../assets/video/promo-trn.jpg" aria-label="{e(a["video_alt"])}" width="1280" height="720"><source src="../../assets/video/promo-trn.mp4" type="video/mp4"></video></div></section>')
    steps = ''.join(f'<li><span class="n" aria-hidden="true">{i + 1}</span><div><strong>{e(t)}</strong><span>{e(d)}</span></div></li>' for i, (t, d) in enumerate(L['steps']))
    faq = ''.join(f'<details class="q"><summary>{e(qq)}</summary><p>{e(aa)}</p></details>' for qq, aa in L['faq'])
    how = (f'<section class="sec" id="perguntas"><div class="wrap duo"><div><h2 class="title sm">{e(a["how_t"])}</h2><ol class="steps">{steps}</ol></div>'
           f'<div><h2 class="title sm">{e(a["faq_t"])}</h2><div class="faqlist">{faq}</div></div></div></section>')
    v = L['values']
    values = f'<section class="values"><div class="wrap"><b>{e(v["title"])}</b><ul>' + ''.join(f'<li>{e(x)}</li>' for x in v['items']) + f'</ul><span>{e(v["text"])}</span></div></section>'
    req = (f'<section class="sec sec--dark" id="contactos"><div class="wrap ctaband"><div><h2 class="title">{e(a["req_t"])}</h2><p class="lead">{e(a["req_l"])}</p>'
           f'<button type="button" class="btn btn--red" data-open-quote>{e(L["nav"]["quote"])}</button></div><div class="cc-list">{contact_lines(L)}</div></div></section>')
    return layout('a', lang, 'home', L['titles']['home'], hero + services + fleet + video + how + values + req, modals=modals_home(L))


# ───────── OPÇÃO B ─────────
def b_home(lang):
    L = LANGS[lang]; b = L['b']; q = L['quick']; alt = ALT[lang]
    badges = ''.join(f'<li>{e(x)}</li>' for x in b['badges'])
    bar = (f'<form class="qbar" id="quick" novalidate aria-label="{e(q["title"])}">'
           f'<div class="qf"><label for="h-from">{e(q["from"])}</label><input id="h-from" type="text" autocomplete="off" placeholder="{e(q["ph_from"])}"></div>'
           f'<div class="qf"><label for="h-to">{e(q["to"])}</label><input id="h-to" type="text" autocomplete="off" placeholder="{e(q["ph_to"])}"></div>'
           f'<div class="qf"><label for="h-date">{e(q["date"])}</label><input id="h-date" type="date"></div>'
           f'<div class="qf"><label for="h-pax">{e(q["pax"])}</label><input id="h-pax" type="number" min="1" max="500" inputmode="numeric"></div>'
           f'<button class="btn btn--red" type="submit">{e(q["go"])}</button><p class="qn">{e(q["note"])}</p></form>')
    hero = (f'<section class="b-hero"><div class="wrap b-hero__grid"><div class="b-hero__txt"><h1>{e(b["h1"])}</h1><p class="b-sub">{e(b["sub"])}</p><ul class="seals">{badges}</ul></div>'
            f'<div class="b-frame"><div class="b-frame__in">{img("trn_man", alt["trn_man"], sizes="(min-width:960px) 46vw, 94vw", lazy=False)}</div><span class="b-frame__line" aria-hidden="true"></span></div></div>'
            f'<div class="wrap">{bar}</div>{swoosh(True)}</section>')
    tabs_btn = ''.join(f'<button type="button" role="tab" id="tab{i}" aria-controls="panel{i}" aria-selected="{"true" if i == 0 else "false"}" tabindex="{0 if i == 0 else -1}">{e(t["label"])}</button>' for i, t in enumerate(L['tabs']))
    panels = ''
    for i, t in enumerate(L['tabs']):
        items = ''.join(f'<li class="card"><strong>{e(n)}</strong><span>{e(d)}</span></li>' for n, d in t['items'])
        extra = f'<button type="button" class="btn btn--ghost" data-open-workers>{e(b["workers_btn"])}</button>' if i == 0 else ''
        pos = '50% 70%' if t['img'] == 'sprinter' else '50% 55%'
        panels += (f'<div class="panel" id="panel{i}" role="tabpanel" aria-labelledby="tab{i}"' + ('' if i == 0 else ' hidden') + '>'
                   f'<div class="pcard"><div class="pcard__img">{img(t["img"], alt[t["img"]], sizes="(min-width:900px) 46vw, 94vw", pos=pos)}</div>'
                   f'<div class="pcard__t"><h3>{e(t["title"])}</h3><p>{e(t["text"])}</p>{extra}</div></div><ul class="cards3">{items}</ul></div>')
    who = f'<section class="sec" id="servicos"><div class="wrap"><div class="head"><h2 class="title">{e(b["who_t"])}</h2></div><div class="tabs" role="tablist" aria-label="{e(b["who_t"])}">{tabs_btn}</div>{panels}</div></section>'
    am = L['amen']
    tags = ''.join(f'<li>{e(x)}</li>' for x in am['items'])
    f3 = ''.join(f'<article class="fc"><h3>{e(it["name"])}</h3><span class="cap">{e(it["cap"])}</span><p>{e(it["text"])}</p></article>' for it in L['fleet3'])
    fleet = (f'<section class="sec sec--grey" id="frota"><div class="wrap"><div class="head head--row"><h2 class="title">{e(b["fleet_t"])}</h2><div><ul class="tags" aria-label="{e(am["title"])}">{tags}</ul><p class="note">{e(am["note"])}</p></div></div>'
             f'<div class="wide">{img("trn_frota", alt["trn_frota"], sizes="(min-width:1180px) 1110px, 94vw")}</div><div class="fc3">{f3}</div></div></section>')
    steps = ''.join(f'<li><span class="n" aria-hidden="true">{i + 1}</span><div><strong>{e(t)}</strong><span>{e(d)}</span></div></li>' for i, (t, d) in enumerate(L['steps']))
    faq = ''.join(f'<details class="q"><summary>{e(qq)}</summary><p>{e(aa)}</p></details>' for qq, aa in L['faq'])
    how = (f'<section class="sec" id="perguntas"><div class="wrap duo"><div><h2 class="title sm">{e(b["steps_t"])}</h2><ol class="steps">{steps}</ol></div>'
           f'<div><h2 class="title sm">{e(b["faq_t"])}</h2><div class="faqlist">{faq}</div></div></div></section>')
    v = L['values']
    values = f'<section class="values"><div class="wrap"><b>{e(v["title"])}</b><ul>' + ''.join(f'<li>{e(x)}</li>' for x in v['items']) + f'</ul><span>{e(v["text"])}</span></div></section>'
    contacts = (f'<section class="sec sec--grey" id="contactos"><div class="wrap"><div class="head"><h2 class="title">{e(b["contacts_t"])}</h2></div><div class="blocks3">'
                f'<div class="blk"><h3>{e(b["contact_t"])}</h3><div class="cc-list">{contact_lines(L)}</div></div>'
                f'<div class="blk blk--dark"><h3>{e(b["exec_t"])}</h3><p>{e(b["exec_x"])}</p><button type="button" class="btn btn--ghost" data-open-quote data-service="executive">{e(b["exec_cta"])}</button></div>'
                f'<div class="blk blk--red"><h3>{e(b["jobs_t"])}</h3><p>{e(b["jobs_x"])}</p><a class="btn btn--white" href="{link(lang, "careers")}">{e(b["jobs_cta"])}</a></div></div></div></section>')
    return layout('b', lang, 'home', L['titles_b']['home'], hero + who + fleet + how + values + contacts, desc=L['descs']['home'], modals=modals_home(L))


# ───────── Recrutamento e Legal (iguais; o estilo muda pela classe opt-a / opt-b) ─────────
def careers(opt, lang):
    L = LANGS[lang]; c = L['careers']; q = L['q']; alt = ALT[lang]
    opts = f'<option value="">{e(c["spont"])}</option>' + ''.join(f'<option>{e(j[0])}</option>' for j in c['jobs'])
    jobs = ''.join(f'<article class="job"><h3>{e(t)}</h3><span class="m">{e(m)}</span><ul class="ticks">' + ''.join(f'<li>{e(r)}</li>' for r in rq) + f'</ul><a class="btn btn--line" href="#candidatura" data-job="{e(t)}">{e(c["apply"])}</a></article>' for t, m, rq in c['jobs'])
    lic = ''.join(f'<label class="chk"><input type="checkbox" name="habilitacoes" value="{e(x)}"><span>{e(x)}</span></label>' for x in c['lics'])
    msgs = {k: q[k] for k in ('required', 'bad_email', 'fail', 'spam', 'sending', 'mail_hint')}
    msgs.update({'got_t': c['got_t'], 'got_x': q['got_x'], 'subject': c['subject'], 'send': c['send']})
    priv = link(L['code'], 'legal', '#privacidade')
    form = (f'<form id="apply" class="aform" action="https://formspree.io/f/[ID]" method="POST" enctype="multipart/form-data" novalidate data-msgs=\'{e(json.dumps(msgs, ensure_ascii=False), quote=True)}\'>'
            f'<h2>{e(c["form_t"])}</h2><div class="fld"><label for="a-job">{e(c["job"])}</label><select id="a-job" name="vaga">{opts}</select></div>'
            f'<div class="row2">{fld("a-name", c["name"], req=True, name="nome")}{fld("a-phone", c["phone"], "tel", req=True, name="telemovel")}</div>'
            f'{fld("a-email", c["email"], "email", req=True, name="email")}'
            f'<fieldset class="lics"><legend>{e(c["lic"])}</legend>{lic}</fieldset>'
            f'<div class="fld"><label for="a-cv">{e(c["cv"])}</label><input id="a-cv" name="curriculo" type="file" accept=".pdf,.doc,.docx"><span class="note">{e(c["cv_hint"])}</span></div>'
            f'<label class="chk"><input type="checkbox" id="a-consent" required><span>{e(c["consent"])} <a href="{priv}">{e(q["privacy_link"])}</a></span></label><span class="err" id="a-consent-e" role="alert"></span>'
            '<div class="hp" aria-hidden="true"><label>Website<input type="text" name="_gotcha" tabindex="-1" autocomplete="off"></label></div>'
            f'<div class="msg" id="amsg" role="alert" hidden></div><div class="actions"><button type="submit" class="btn btn--red" id="asend">{e(c["send"])}</button></div>'
            f'<div class="done" id="adone" role="status" hidden><h3>{e(c["got_t"])}</h3><p>{e(q["got_x"])} <strong id="aref"></strong></p></div></form>')
    body = (f'<section class="page-head"><div class="wrap ph-grid"><div><span class="kicker">{e(c["kicker"])}</span><h1>{e(c["h1"])}</h1><p class="lede">{e(c["sub"])}</p></div>'
            f'<div class="ph-img">{img("trn_man2", alt["trn_man2"], sizes="(min-width:900px) 46vw, 94vw", lazy=False)}</div></div>{swoosh(opt == "b")}</section>'
            f'<section class="sec"><div class="wrap"><div class="head head--row"><h2 class="title">{e(c["jobs_t"])}</h2><span class="example">{e(c["example"])}</span></div><div class="jobs">{jobs}</div></div></section>'
            f'<section class="sec sec--grey" id="candidatura"><div class="wrap narrow">{form}</div></section>')
    return layout(opt, lang, 'careers', L['titles']['careers'], body, modals=quote_modal(L))


def legal(opt, lang):
    L = LANGS[lang]; g = L['legal']
    body = (f'<section class="page-head page-head--s"><div class="wrap"><h1>{e(g["title"])}</h1></div></section>'
            f'<section class="sec"><div class="wrap legal"><p class="note-box">{e(g["note"])}</p><h2 id="privacidade">{e(g["privacy_h"])}</h2>{g["privacy"]}<h2 id="cookies">{e(g["cookies_h"])}</h2>{g["cookies"]}</div></section>')
    return layout(opt, lang, 'legal', L['titles']['legal'], body, modals=quote_modal(L))


# ───────── Página de escolha ─────────
def chooser():
    """Página inicial (index.html): só reencaminha para a Opção A, no idioma do navegador (PT por omissão)."""
    t = '/'.join(CHOOSER['pt']['title'] for _ in [0])
    return f'''<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<title>{e(COMPANY)}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{e(LANGS['pt']['descs']['home'])}">
{ROBOTS_META}
<link rel="canonical" href="{BASE}">
<meta property="og:type" content="website"><meta property="og:title" content="{e(COMPANY)}"><meta property="og:description" content="{e(LANGS['pt']['descs']['home'])}"><meta property="og:locale" content="pt_PT"><meta property="og:url" content="{BASE}"><meta property="og:image" content="{OG_IMAGE}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{e(OG_ALT['pt'])}"><meta name="twitter:card" content="summary_large_image">
<noscript><meta http-equiv="refresh" content="0;url=opcao-a/pt/index.html"></noscript>
<script>var l=(navigator.language||'pt').slice(0,2);location.replace('opcao-a/'+(l==='en'||l==='es'?l:'pt')+'/index.html');</script>
</head>
<body style="font-family:system-ui,sans-serif;padding:24px"><h1>TRN</h1><p><a href="opcao-a/pt/index.html">Português</a> · <a href="opcao-a/en/index.html">English</a> · <a href="opcao-a/es/index.html">Español</a></p></body>
</html>
'''


def chooser_antigo():
    out = []
    for lang in LANGS:
        c = CHOOSER[lang]
        def card(k, href_lang):
            pts = ''.join(f'<li>{e(p)}</li>' for p in c[k + '_p'])
            return (f'<article class="opt opt--{k}"><a class="opt__img" href="opcao-{k}/{lang}/index.html" tabindex="-1" aria-hidden="true"><img src="assets/img/captura-{k}.jpg" width="1200" height="750" alt="{e(c["alt_" + k])}" loading="lazy"></a>'
                    f'<div class="opt__b"><span class="opt__k">{e(c[k + "_t"])}</span><h2>{e(c[k + "_s"])}</h2><ul class="ticks">{pts}</ul>'
                    f'<a class="btn btn--red" href="opcao-{k}/{lang}/index.html" data-optlink="{k}">{e(c["view"])}</a></div></article>')
        out.append((lang, c, card('a', lang) + card('b', lang)))
    # um único index.html com os 3 idiomas (alternados por JS simples; PT por omissão)
    blocks = ''.join(f'<div class="lang-block" data-lang="{lang}"' + ('' if lang == 'pt' else ' hidden') + f'><div class="opts">{cards}</div></div>' for lang, c, cards in out)
    c0 = CHOOSER['pt']
    heading = (f'<h1 id="ch-title" data-pt="{e(CHOOSER["pt"]["title"])}" data-en="{e(CHOOSER["en"]["title"])}" data-es="{e(CHOOSER["es"]["title"])}">{e(c0["title"])}</h1>'
               f'<p class="lead" id="ch-lead" data-pt="{e(CHOOSER["pt"]["lead"])}" data-en="{e(CHOOSER["en"]["lead"])}" data-es="{e(CHOOSER["es"]["lead"])}">{e(c0["lead"])}</p>')
    blocks = heading + blocks
    sw = ''.join(f'<button type="button" data-set="{l}" aria-pressed="{"true" if l == "pt" else "false"}">{LANGS[l]["label"]}</button>' for l in LANGS)
    c = CHOOSER['pt']
    return f'''<!doctype html>
<html lang="pt-PT">
<head>
<meta charset="utf-8">
<title>Proposta de novo website | TRN — Rodoviária Internacional e Nacional</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{e(c['desc'])}">
{ROBOTS_META}
<meta name="theme-color" content="#23282D">
<link rel="canonical" href="{BASE}">
<meta property="og:type" content="website"><meta property="og:title" content="Proposta de novo website | TRN"><meta property="og:description" content="{e(c['desc'])}">
<meta property="og:url" content="{BASE}"><meta property="og:image" content="{OG_IMAGE}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="{e(OG_ALT['pt'])}"><meta property="og:locale" content="pt_PT"><meta property="og:locale:alternate" content="en_GB"><meta property="og:locale:alternate" content="es_ES"><meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/svg+xml" href="assets/img/logo-trn.svg">
<link rel="stylesheet" href="assets/css/base.css">
<link rel="stylesheet" href="assets/css/escolha.css">
</head>
<body class="chooser">
<main id="conteudo"><div class="wrap">
<header class="ch-head"><img src="assets/img/logo-trn.svg" alt="TRN — Rodoviária Internacional e Nacional, Lda." width="170" height="71"><div class="lang lang--btn" role="group" aria-label="Idioma / Language">{sw}</div></header>
{blocks}
</div></main>
<footer class="ch-foot"><div class="wrap"><span>Conceito, design e textos © 2026 Rúben Neves.</span></div></footer>
<script>
(function(){{var b=document.querySelectorAll('[data-set]'),s=document.querySelectorAll('.lang-block');
function set(l){{['ch-title','ch-lead'].forEach(function(i){{var n=document.getElementById(i);n.textContent=n.getAttribute('data-'+l)}});s.forEach(function(x){{x.hidden=x.getAttribute('data-lang')!==l}});b.forEach(function(x){{x.setAttribute('aria-pressed',String(x.getAttribute('data-set')===l))}});document.documentElement.lang=l==='pt'?'pt-PT':l;try{{localStorage.setItem('trn-lang',l)}}catch(e){{}}}}
b.forEach(function(x){{x.addEventListener('click',function(){{set(x.getAttribute('data-set'))}})}});
var l=null;try{{l=localStorage.getItem('trn-lang')}}catch(e){{}}if(!l){{l=(navigator.language||'pt').slice(0,2).toLowerCase()}}if(l==='en'||l==='es')set(l);}})();
</script>
</body>
</html>'''


def set_password():
    """Define a senha do backoffice. Pede-a no terminal; só guarda um código cifrado (PBKDF2-SHA256)."""
    print('Senha do backoffice (utilizador: ADMIN TIC). Mínimo 12 caracteres.')
    p1 = getpass.getpass('Nova senha: ')
    p2 = getpass.getpass('Repita a senha: ')
    if p1 != p2:
        raise SystemExit('As senhas não coincidem. Nada foi guardado.')
    if len(p1) < 12:
        raise SystemExit('Senha demasiado curta (mínimo 12 caracteres). Nada foi guardado.')
    iters, salt = 600000, os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', p1.encode('utf-8'), salt, iters, dklen=64)
    data = {'user': 'ADMIN TIC', 'kdf': 'pbkdf2-sha256', 'iterations': iters, 'salt': base64.b64encode(salt).decode(),
            'hash': base64.b64encode(dk[:32]).decode()}      # os outros 32 bytes (chave) nunca são guardados
    (HERE / 'content' / 'admin.json').write_text(json.dumps(data, indent=1) + '\n', encoding='utf-8')
    print('Feito: content/admin.json atualizado. Envie esse ficheiro para o GitHub (consulte o LEIA-ME-BACKOFFICE.md).')


def main(out=None):
    global OUT
    if out:
        OUT = pathlib.Path(out).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    for opt in OPTS:
        for lang in LANGS:
            d = OUT / f'opcao-{opt}' / lang
            d.mkdir(parents=True, exist_ok=True)
            home = a_home(lang) if opt == 'a' else b_home(lang)
            (d / LANGS[lang]['files']['home']).write_text(home, encoding='utf-8')
            (d / LANGS[lang]['files']['careers']).write_text(careers(opt, lang), encoding='utf-8')
            (d / LANGS[lang]['files']['legal']).write_text(legal(opt, lang), encoding='utf-8')
    (OUT / 'index.html').write_text(chooser(), encoding='utf-8')
    (OUT / '.nojekyll').write_text('')
    for doc in ('LEIA-ME.md', 'LEIA-ME-BACKOFFICE.md'):
        if (HERE / doc).exists():
            shutil.copy(HERE / doc, OUT / doc)
    if NOINDEX:
        (OUT / 'robots.txt').write_text('User-agent: *\nDisallow: /\n')
        if (OUT / 'sitemap.xml').exists():
            (OUT / 'sitemap.xml').unlink()
    else:
        urls = [BASE] + [BASE + path(o, l, p) for o in OPTS for l in LANGS for p in ('home', 'careers', 'legal')]
        (OUT / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join('<url><loc>%s</loc></url>' % u for u in urls) + '</urlset>')
        (OUT / 'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: ' + BASE + 'sitemap.xml\n')
    for f in (HERE / 'static').rglob('*'):
        if f.is_file():
            dest = OUT / 'assets' / f.relative_to(HERE / 'static')
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(f, dest)
    # config.js: vem de content/site.json (telefone, WhatsApp, Formspree)
    cfg = {'phone': PHONE, 'whatsapp': SITE.get('whatsapp', ''), 'formspreeId': SITE.get('formspree_id', ''), 'email': EMAIL}
    (OUT / 'assets' / 'js' / 'config.js').write_text('/* Gerado a partir de content/site.json (backoffice). Não edite à mão. */\nwindow.TRN_CONFIG = ' + json.dumps(cfg, ensure_ascii=False, indent=2) + ';\n', encoding='utf-8')
    # backoffice
    if (HERE / 'admin').exists():
        adm = OUT / 'admin'
        adm.mkdir(parents=True, exist_ok=True)
        for f in (HERE / 'admin').rglob('*'):
            if f.is_file():
                (adm / f.relative_to(HERE / 'admin')).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(f, adm / f.relative_to(HERE / 'admin'))
        auth = HERE / 'content' / 'admin.json'
        (adm / 'auth.json').write_text(auth.read_text(encoding='utf-8') if auth.exists() else json.dumps({'configured': False}), encoding='utf-8')
        (adm / 'repo.json').write_text(json.dumps(SITE['github']), encoding='utf-8')
    print('ok:', len(OPTS) * len(LANGS) * 3 + 1, 'páginas →', OUT)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    ap.add_argument('--senha', action='store_true')
    a = ap.parse_args()
    if a.senha:
        set_password()
    else:
        main(a.out)
