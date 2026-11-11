import os, re, sqlite3, time, secrets
from functools import wraps
from flask import Flask, Request, g, request, session, redirect, jsonify, Response, abort
from jinja2 import Environment, DictLoader
from markupsafe import Markup

MAX_MB = 50


class BigRequest(Request):
    # Werkzeug 3.1+ limits text form fields to 500 KB by default, which blocks large pasted HTML code
    max_form_memory_size = MAX_MB * 1024 * 1024


app = Flask(__name__)
app.request_class = BigRequest
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret")
app.config["MAX_CONTENT_LENGTH"] = MAX_MB * 1024 * 1024
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
DB = os.environ.get("DB_PATH", "data.db")

DEFAULTS = {
    "site_title": "No Rules YT", "handle": "@no_rules_yt_",
    "tagline": "Games, tools and fun stuff, made with zero rules.",
    "notice": "", "followers": "50350", "likes": "976419", "views": "3058865", "videos": "953",
    "tiktok": "", "youtube": "", "instagram": "", "chat_title": "World Chat", "chat_on": "1",
}

ICONS = {
    "bolt": '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
    "heart": '<path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21.2l7.8-7.7 1-1.1a5.5 5.5 0 0 0 0-7.8z"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>',
    "lock": '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
    "code": '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15 15 0 0 1 0 20 15 15 0 0 1 0-20z"/>',
    "star": '<polygon points="12 2 15 9 22 9.3 16.5 14 18.2 21 12 17.3 5.8 21 7.5 14 2 9.3 9 9 12 2"/>',
    "music": '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    "camera": '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>',
    "gamepad": '<rect x="2" y="6" width="20" height="12" rx="4"/><line x1="6" y1="12" x2="10" y2="12"/><line x1="8" y1="10" x2="8" y2="14"/><circle cx="15" cy="11" r="1"/><circle cx="18" cy="13" r="1"/>',
    "puzzle": '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
    "wrench": '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z"/>',
    "chat": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
    "play": '<circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/>',
    "gift": '<polyline points="20 12 20 22 4 22 4 12"/><rect x="2" y="7" width="20" height="5"/><line x1="12" y1="22" x2="12" y2="7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7zM12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/>',
    "bell": '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
    "send": '<line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>',
    "arrow": '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
    "x": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "trash": '<polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6M9 6V4h6v2"/>',
    "eye": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12z"/><circle cx="12" cy="12" r="3"/>',
    "plus": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>',
}
PICKER = [k for k in ICONS if k not in ("arrow", "x", "edit", "trash", "eye", "plus", "settings", "send", "bell")]


def icon(name, cls=""):
    return Markup('<svg class="ic %s" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
                  'stroke-linecap="round" stroke-linejoin="round">%s</svg>' % (cls, ICONS.get(name, ICONS["bolt"])))


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


def q(sql, a=(), one=False):
    r = db().execute(sql, a).fetchall()
    db().commit()
    return (r[0] if r else None) if one else r


def S():
    return {r["k"]: r["v"] for r in q("SELECT k,v FROM settings")}


def init():
    c = sqlite3.connect(DB)
    c.executescript("""
    CREATE TABLE IF NOT EXISTS settings(k TEXT PRIMARY KEY, v TEXT);
    CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, descr TEXT, cat TEXT,
        badge TEXT, icon TEXT, kind TEXT, content TEXT, sort INTEGER DEFAULT 0, visible INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS msgs(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, text TEXT, ts INTEGER);
    CREATE TABLE IF NOT EXISTS online(sid TEXT PRIMARY KEY, ts INTEGER);
    CREATE TABLE IF NOT EXISTS uploads(id INTEGER PRIMARY KEY AUTOINCREMENT, mime TEXT, data BLOB);""")
    if "image" not in [r[1] for r in c.execute("PRAGMA table_info(items)")]:
        c.execute("ALTER TABLE items ADD COLUMN image TEXT DEFAULT ''")
    for k, v in DEFAULTS.items():
        c.execute("INSERT OR IGNORE INTO settings VALUES(?,?)", (k, v))
    c.commit()
    c.close()


init()

CSS = """
:root{--bg:#07090f;--card:#0e121c;--line:#1b2233;--tx:#e8ecf5;--mut:#8a94a9;--a:#7c5cff;--b:#22d3ee;--ok:#22c55e;--bad:#ef4444}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:Inter,system-ui,-apple-system,sans-serif;background:var(--bg);color:var(--tx);min-height:100vh;overflow-x:hidden;line-height:1.5}
body:before{content:"";position:fixed;inset:-20%;z-index:-1;background:radial-gradient(40% 30% at 20% 10%,#7c5cff30,transparent),radial-gradient(35% 30% at 85% 20%,#22d3ee20,transparent);animation:drift 14s ease-in-out infinite alternate}
@keyframes drift{to{transform:translate(3%,4%) scale(1.08)}}
@keyframes up{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes pulse{0%{box-shadow:0 0 0 0 #22c55e88}100%{box-shadow:0 0 0 10px #22c55e00}}
@keyframes float{50%{transform:translateY(-6px)}}
@keyframes shine{to{background-position:200% 0}}
a{color:inherit;text-decoration:none}.ic{width:1.15em;height:1.15em;flex:none}
.wrap{max-width:1000px;margin:auto;padding:28px 16px 100px}.mut{color:var(--mut)}
.fade{opacity:0;animation:up .6s ease forwards;animation-delay:var(--d,0ms)}
.hero{text-align:center;padding:20px 0 10px}
.logo{width:84px;height:84px;margin:auto;border-radius:24px;display:grid;place-items:center;background:linear-gradient(135deg,var(--a),var(--b));box-shadow:0 10px 40px #7c5cff55;animation:float 4s ease-in-out infinite}
.logo .ic{width:40px;height:40px;color:#fff}
h1{font-size:2rem;margin-top:14px;background:linear-gradient(90deg,#fff,#a9b8ff,#fff);background-size:200% 100%;-webkit-background-clip:text;background-clip:text;color:transparent;animation:shine 6s linear infinite}
.hero p{max-width:480px;margin:8px auto}
.notice{display:inline-flex;gap:8px;align-items:center;margin-top:14px;padding:9px 14px;border:1px solid var(--line);border-radius:12px;background:#ffffff08;font-size:.9rem}
.notice .ic{color:var(--b)}
.soc{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin-top:16px}
.chip{display:inline-flex;gap:7px;align-items:center;padding:8px 14px;border-radius:999px;border:1px solid var(--line);background:var(--card);font-size:.88rem;transition:.25s}
.chip:hover{border-color:var(--a);transform:translateY(-2px);box-shadow:0 6px 20px #7c5cff30}
.live{display:inline-flex;gap:7px;align-items:center;margin-top:16px;font-size:.78rem;color:var(--mut)}
.live i{width:8px;height:8px;border-radius:50%;background:var(--ok);animation:pulse 1.6s infinite}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-top:18px}
.stats div{padding:14px;border:1px solid var(--line);border-radius:16px;background:var(--card)}
.stats b{display:block;font-size:1.35rem}.stats span{font-size:.78rem;color:var(--mut)}
.tabs{display:flex;gap:8px;margin:28px 0 16px;flex-wrap:wrap}
.tabs button{display:flex;gap:7px;align-items:center;padding:9px 16px;border-radius:12px;border:1px solid var(--line);background:var(--card);color:var(--mut);cursor:pointer;font:inherit;transition:.25s}
.tabs button em{font-style:normal;font-size:.75rem;padding:1px 7px;border-radius:99px;background:#ffffff10}
.tabs button.on,.tabs button:hover{color:#fff;border-color:var(--a);background:linear-gradient(135deg,#7c5cff30,#22d3ee18)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:12px}
.card{position:relative;display:flex;gap:14px;align-items:center;padding:16px;border:1px solid var(--line);border-radius:18px;background:var(--card);overflow:hidden;transition:.3s}
.card:before{content:"";position:absolute;inset:0;background:linear-gradient(120deg,transparent 30%,#ffffff10 50%,transparent 70%);transform:translateX(-100%);transition:.7s}
.card:hover{transform:translateY(-4px);border-color:var(--a);box-shadow:0 12px 36px #7c5cff28}.card:hover:before{transform:translateX(100%)}
.ico{width:54px;height:54px;border-radius:16px;display:grid;place-items:center;flex:none;background:linear-gradient(135deg,#7c5cff40,#22d3ee30);color:#cfd8ff;transition:.3s}
.ico .ic{width:26px;height:26px}.card:hover .ico{transform:rotate(-8deg) scale(1.08);color:#fff;box-shadow:0 0 24px #7c5cff77}
.card h3{font-size:1rem}.card p{font-size:.83rem;color:var(--mut)}.card>div:nth-child(2){flex:1;min-width:0}
.tags{display:flex;gap:6px;margin-top:6px}.tags u{text-decoration:none;font-size:.65rem;letter-spacing:.06em;padding:2px 8px;border-radius:99px;border:1px solid var(--line);color:var(--mut)}
.tags u.hot{color:#fff;border:0;background:linear-gradient(90deg,var(--a),var(--b))}
.go{color:var(--mut);transition:.3s}.card:hover .go{color:#fff;transform:translateX(4px)}
.empty{padding:30px;text-align:center;color:var(--mut);border:1px dashed var(--line);border-radius:16px}
footer{text-align:center;margin-top:50px;color:var(--mut);font-size:.82rem}
/* chat */
#cfab{position:fixed;right:18px;bottom:18px;width:56px;height:56px;border-radius:50%;border:0;cursor:pointer;color:#fff;display:grid;place-items:center;background:linear-gradient(135deg,var(--a),var(--b));box-shadow:0 10px 30px #7c5cff66;transition:.3s;z-index:20}
#cfab:hover{transform:scale(1.1) rotate(-6deg)}#cfab .ic{width:26px;height:26px}
#cbox{position:fixed;right:18px;bottom:86px;width:min(360px,calc(100vw - 36px));height:460px;max-height:70vh;display:flex;flex-direction:column;border:1px solid var(--line);border-radius:20px;background:#0b0f18f2;backdrop-filter:blur(14px);box-shadow:0 20px 60px #000a;opacity:0;pointer-events:none;transform:translateY(16px) scale(.97);transition:.3s;z-index:20;overflow:hidden}
#cbox.open{opacity:1;pointer-events:auto;transform:none}
.ch{display:flex;justify-content:space-between;align-items:center;padding:14px 16px;border-bottom:1px solid var(--line)}
.ch b{display:flex;gap:8px;align-items:center}.ch small{display:flex;gap:6px;align-items:center;color:var(--mut)}.ch small i{width:7px;height:7px;border-radius:50%;background:var(--ok);animation:pulse 1.6s infinite}
#clist{flex:1;overflow:auto;padding:12px;display:flex;flex-direction:column;gap:8px}
.msg{max-width:84%;padding:8px 12px;border-radius:14px 14px 14px 4px;background:#ffffff0d;animation:up .3s ease}
.msg b{font-size:.74rem;color:var(--b)}.msg p{font-size:.88rem;word-break:break-word}
.msg.me{align-self:flex-end;border-radius:14px 14px 4px 14px;background:linear-gradient(135deg,#7c5cff55,#22d3ee33)}.msg.me b{color:#fff}
.cf{display:flex;gap:8px;padding:10px;border-top:1px solid var(--line)}.cf[hidden],#cjoin[hidden]{display:none}
#cjoin{padding:16px;display:flex;flex-direction:column;gap:10px}
input,textarea,select{width:100%;padding:11px 13px;border-radius:12px;border:1px solid var(--line);background:#0a0d15;color:var(--tx);font:inherit;outline:0;transition:.2s}
input:focus,textarea:focus,select:focus{border-color:var(--a);box-shadow:0 0 0 3px #7c5cff22}
textarea{min-height:90px;resize:vertical}.mono{font-family:ui-monospace,Menlo,monospace;font-size:.82rem;min-height:260px}
.btn{display:inline-flex;gap:7px;align-items:center;justify-content:center;padding:10px 16px;border:0;border-radius:12px;color:#fff;cursor:pointer;font:inherit;font-weight:600;background:linear-gradient(135deg,var(--a),var(--b));transition:.25s}
.btn:hover{transform:translateY(-2px);box-shadow:0 8px 24px #7c5cff44}.btn.sm{padding:7px 11px;font-size:.8rem}
.btn.ghost{background:#ffffff0d;border:1px solid var(--line)}.btn.red{background:#ef444422;color:#ff8a8a;border:1px solid #ef444455}
/* admin */
.top{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:20px}
.top h2{display:flex;gap:10px;align-items:center}.top .r{display:flex;gap:8px}
.box{border:1px solid var(--line);border-radius:18px;background:var(--card);padding:18px;margin-bottom:18px}
.box h3{display:flex;gap:8px;align-items:center;margin-bottom:14px}
.f2{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
label.l{display:block;font-size:.78rem;color:var(--mut);margin-bottom:5px}
.row{display:flex;gap:10px;align-items:center;padding:11px 0;border-top:1px solid var(--line)}.row:first-of-type{border-top:0}
.row .ico{width:40px;height:40px;border-radius:12px}.row .ico .ic{width:20px;height:20px}
.row .g{flex:1;min-width:0}.row .g b{display:block}.row .g span{font-size:.78rem;color:var(--mut);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:block}
.row form{display:inline}.off{opacity:.45}
.picker{display:grid;grid-template-columns:repeat(auto-fill,minmax(54px,1fr));gap:8px}
.ip{display:grid;place-items:center;height:54px;border:1px solid var(--line);border-radius:14px;cursor:pointer;transition:.25s;color:var(--mut)}
.ip input{display:none}.ip .ic{width:24px;height:24px}.ip:hover{color:#fff;transform:translateY(-2px)}
.ip:has(input:checked){color:#fff;border-color:var(--a);background:linear-gradient(135deg,#7c5cff40,#22d3ee25);box-shadow:0 0 20px #7c5cff44}
.sw{display:flex;gap:8px;align-items:center}.sw input{width:auto}
.login{max-width:360px;margin:14vh auto;text-align:center}.login .logo{width:64px;height:64px;border-radius:18px;margin-bottom:12px}
.err{color:#ff8a8a;font-size:.85rem;margin-bottom:10px}
.th{padding:0;overflow:hidden}.th img{width:100%;height:100%;object-fit:cover;display:block}.th .ic{display:none}
.pv{width:96px;height:96px;border-radius:18px;border:1px dashed var(--line);margin-bottom:12px;overflow:hidden;display:grid;place-items:center}
.pv:empty:before{content:"No photo";font-size:.72rem;color:var(--mut)}.pv img{width:100%;height:100%;object-fit:cover}
.fr{margin-bottom:8px}input[type=file]{padding:9px}
"""

T = {}
T["base.html"] = """<!doctype html><html lang="bn"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{% block title %}{{ s.site_title }}{% endblock %}</title>
<style>""" + CSS + """</style></head><body>{% block body %}{% endblock %}</body></html>"""

T["index.html"] = """{% extends "base.html" %}{% block body %}
<div class="wrap">
<header class="hero fade">
  <div class="logo">{{ icon('bolt') }}</div>
  <h1>{{ s.site_title }}</h1><div class="mut">{{ s.handle }}</div><p class="mut">{{ s.tagline }}</p>
  {% if s.notice %}<div class="notice">{{ icon('bell') }}<span>{{ s.notice }}</span></div>{% endif %}
  <div class="soc">{% for k,ic in [('tiktok','music'),('youtube','play'),('instagram','camera')] %}{% if s[k] %}
    <a class="chip" href="{{ s[k] }}" target="_blank" rel="noopener">{{ icon(ic) }}{{ k|capitalize }}</a>{% endif %}{% endfor %}</div>
  <div class="live"><i></i>Live</div>
  <div class="stats">{% for k,l in [('followers','Followers'),('likes','Likes'),('views','Views'),('videos','Videos')] %}
    <div><b data-n>{{ s[k] }}</b><span>{{ l }}</span></div>{% endfor %}</div>
</header>
<nav class="tabs fade" style="--d:150ms">
  <button class="on" data-f="all">{{ icon('star') }}All <em>{{ items|length }}</em></button>
  <button data-f="tool">{{ icon('wrench') }}Tools <em>{{ items|selectattr('cat','equalto','tool')|list|length }}</em></button>
  <button data-f="game">{{ icon('gamepad') }}Games <em>{{ items|selectattr('cat','equalto','game')|list|length }}</em></button>
</nav>
<section class="grid">
{% for it in items %}
  <a class="card fade" data-c="{{ it.cat }}" href="/t/{{ it.id }}" style="--d:{{ 200 + loop.index0*50 }}ms">
    <div class="ico{{ ' th' if it.image }}">{% if it.image %}<img src="{{ it.image }}" alt="" loading="lazy" onerror="this.parentNode.classList.remove('th');this.remove()">{% endif %}{{ icon(it.icon) }}</div>
    <div><h3>{{ it.title }}</h3><p>{{ it.descr }}</p>
      <div class="tags"><u>{{ it.cat|upper }}</u>{% if it.badge %}<u class="hot">{{ it.badge }}</u>{% endif %}</div></div>
    <span class="go">{{ icon('arrow') }}</span>
  </a>
{% else %}<div class="empty">Nothing here yet.</div>{% endfor %}
</section>
<footer>&copy; {{ s.site_title }}</footer>
</div>
{% if s.chat_on == '1' %}
<button id="cfab" aria-label="Chat">{{ icon('chat') }}</button>
<div id="cbox">
  <div class="ch"><b>{{ icon('globe') }}{{ s.chat_title }}</b><small><i></i><span id="con">0</span> online</small></div>
  <div id="cjoin"><p class="mut">Choose a name to start talking</p><input id="cname" maxlength="20" placeholder="Your name"><button class="btn" id="cgo">Join</button></div>
  <div id="clist"></div>
  <form class="cf" id="cform" hidden><input id="ctext" maxlength="300" placeholder="Write a message" autocomplete="off"><button class="btn" aria-label="Send">{{ icon('send') }}</button></form>
</div>
{% endif %}
<script>
document.querySelectorAll('[data-n]').forEach(function(e){var n=parseInt(e.textContent.replace(/\\D/g,''));if(isNaN(n))return;var t0=performance.now();
 (function f(t){var p=Math.min((t-t0)/1200,1);e.textContent=Math.round(n*(1-Math.pow(1-p,3))).toLocaleString();if(p<1)requestAnimationFrame(f)})(t0)});
document.querySelectorAll('.tabs button').forEach(function(b){b.onclick=function(){
 document.querySelectorAll('.tabs button').forEach(function(x){x.classList.remove('on')});b.classList.add('on');
 document.querySelectorAll('.card').forEach(function(c){c.style.display=(b.dataset.f==='all'||c.dataset.c===b.dataset.f)?'':'none'})}});
(function(){var fab=document.getElementById('cfab');if(!fab)return;
 var box=document.getElementById('cbox'),list=document.getElementById('clist'),join=document.getElementById('cjoin'),form=document.getElementById('cform');
 var name=localStorage.getItem('cn')||'',sid=localStorage.getItem('cs');
 if(!sid){sid=Math.random().toString(36).slice(2)+Date.now().toString(36);localStorage.setItem('cs',sid)}
 var sig='',timer;
 function ui(){join.hidden=!!name;form.hidden=!name}
 function load(){fetch('/api/chat?sid='+sid).then(function(r){return r.json()}).then(function(d){
  document.getElementById('con').textContent=d.online;var s=d.msgs.map(function(m){return m.id}).join();if(s===sig)return;sig=s;list.innerHTML='';
  d.msgs.forEach(function(m){var e=document.createElement('div');e.className='msg'+(m.name===name?' me':'');var b=document.createElement('b');b.textContent=m.name;
   var p=document.createElement('p');p.textContent=m.text;e.append(b,p);list.append(e)});list.scrollTop=list.scrollHeight}).catch(function(){})}
 fab.onclick=function(){box.classList.toggle('open');if(box.classList.contains('open')){load();timer=setInterval(load,3000)}else clearInterval(timer)};
 document.getElementById('cgo').onclick=function(){var v=document.getElementById('cname').value.trim();if(!v)return;name=v;localStorage.setItem('cn',v);sig='';ui();load()};
 form.onsubmit=function(e){e.preventDefault();var i=document.getElementById('ctext'),t=i.value.trim();if(!t)return;i.value='';
  fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sid:sid,name:name,text:t})}).then(load)};
 ui()})();
</script>{% endblock %}"""

T["login.html"] = """{% extends "base.html" %}{% block title %}Admin{% endblock %}{% block body %}
<form class="login box fade" method="post">
  <div class="logo">{{ icon('lock') }}</div><h2>Admin Panel</h2><p class="mut" style="margin-bottom:14px">{{ s.site_title }}</p>
  {% if err %}<div class="err">Wrong password</div>{% endif %}
  <input type="password" name="password" placeholder="Password" autofocus style="margin-bottom:10px"><button class="btn" style="width:100%">Sign in</button>
</form>{% endblock %}"""

T["admin.html"] = """{% extends "base.html" %}{% block title %}Admin - {{ s.site_title }}{% endblock %}{% block body %}
<div class="wrap">
<div class="top fade"><h2>{{ icon('shield') }}Admin Panel</h2>
  <div class="r"><a class="btn ghost sm" href="/" target="_blank">{{ icon('eye') }}View site</a>
  <a class="btn ghost sm" href="/admin/logout">Logout</a></div></div>

<div class="box fade" style="--d:60ms"><h3>{{ icon('wrench') }}Tools and Games <a class="btn sm" style="margin-left:auto" href="/admin/item">{{ icon('plus') }}Add new</a></h3>
{% for it in items %}
  <div class="row {{ '' if it.visible else 'off' }}">
    <div class="ico{{ ' th' if it.image }}">{% if it.image %}<img src="{{ it.image }}" alt="" loading="lazy" onerror="this.parentNode.classList.remove('th');this.remove()">{% endif %}{{ icon(it.icon) }}</div>
    <div class="g"><b>{{ it.title }}</b><span>{{ it.cat|upper }} / {{ it.kind|upper }} / {{ it.content[:70] if it.kind == 'link' else 'HTML code' }}</span></div>
    <a class="btn ghost sm" href="/admin/item/{{ it.id }}">{{ icon('edit') }}</a>
    <form method="post" action="/admin/item/{{ it.id }}/toggle"><input type="hidden" name="_t" value="{{ t }}"><button class="btn ghost sm">{{ icon('eye') }}</button></form>
    <form method="post" action="/admin/item/{{ it.id }}/delete" onsubmit="return confirm('Delete this item?')"><input type="hidden" name="_t" value="{{ t }}"><button class="btn red sm">{{ icon('trash') }}</button></form>
  </div>
{% else %}<div class="empty">No items yet. Add your first tool or game.</div>{% endfor %}</div>

<form class="box fade" style="--d:120ms" method="post" action="/admin/settings"><input type="hidden" name="_t" value="{{ t }}">
  <h3>{{ icon('settings') }}Site settings</h3>
  <div class="f2">
  {% for k,l in [('site_title','Site title'),('handle','Handle'),('tagline','Tagline'),('notice','Notice bar (empty = hidden)'),('followers','Followers'),('likes','Likes'),('views','Views'),('videos','Videos'),('tiktok','TikTok link'),('youtube','YouTube link'),('instagram','Instagram link'),('chat_title','Chat title')] %}
    <div><label class="l">{{ l }}</label><input name="{{ k }}" value="{{ s[k] }}"></div>{% endfor %}
  </div>
  <label class="sw" style="margin:14px 0"><input type="checkbox" name="chat_on" value="1" {{ 'checked' if s.chat_on == '1' }}>Enable world chat</label>
  <button class="btn">Save settings</button>
</form>

<div class="box fade" style="--d:180ms"><h3>{{ icon('chat') }}Chat messages ({{ online }} online)
  <form method="post" action="/admin/msgs/clear" style="margin-left:auto" onsubmit="return confirm('Clear all messages?')"><input type="hidden" name="_t" value="{{ t }}"><button class="btn red sm">Clear all</button></form></h3>
{% for m in msgs %}
  <div class="row"><div class="g"><b>{{ m.name }}</b><span>{{ m.text }}</span></div>
  <form method="post" action="/admin/msg/{{ m.id }}/delete"><input type="hidden" name="_t" value="{{ t }}"><button class="btn red sm">{{ icon('x') }}</button></form></div>
{% else %}<div class="empty">No messages.</div>{% endfor %}</div>
</div>{% endblock %}"""

T["item.html"] = """{% extends "base.html" %}{% block title %}Item - Admin{% endblock %}{% block body %}
<div class="wrap">
<div class="top fade"><h2>{{ icon('plus') }}{{ 'Edit item' if it else 'New item' }}</h2><a class="btn ghost sm" href="/admin">Back</a></div>
<form class="box fade" method="post" enctype="multipart/form-data"><input type="hidden" name="_t" value="{{ t }}">
  <div class="f2">
    <div><label class="l">Title</label><input name="title" required maxlength="80" value="{{ it.title if it }}"></div>
    <div><label class="l">Short description</label><input name="descr" maxlength="200" value="{{ it.descr if it }}"></div>
    <div><label class="l">Category</label><select name="cat">{% for c in ['tool','game'] %}<option value="{{ c }}" {{ 'selected' if it and it.cat == c }}>{{ c|capitalize }}</option>{% endfor %}</select></div>
    <div><label class="l">Badge (NEW, HOT, OFFLINE...)</label><input name="badge" maxlength="12" value="{{ it.badge if it }}"></div>
    <div><label class="l">Sort order (small = first)</label><input type="number" name="sort" value="{{ it.sort if it else 0 }}"></div>
    <div><label class="l">Type</label><select name="kind" id="kind" onchange="k()"><option value="link" {{ 'selected' if it and it.kind == 'link' }}>Link</option><option value="html" {{ 'selected' if it and it.kind == 'html' }}>HTML code</option></select></div>
  </div>
  <label class="l" style="margin-top:14px" id="cl">Content</label>
  <div class="fr"><label class="btn ghost sm" id="hfb" for="hf">{{ icon('code') }}Upload HTML file</label><input type="file" id="hf" accept=".html,.htm,text/html" hidden></div>
  <textarea name="content" id="ct" class="mono">{{ it.content if it }}</textarea>
  {% if err %}<div class="err" style="margin-top:8px">{{ err }}</div>{% endif %}
  <label class="l" style="margin-top:14px">Photo (small thumbnail on the card)</label>
  <div class="pv" id="pv">{% if it and it.image %}<img src="{{ it.image }}" alt="">{% endif %}</div>
  <div class="f2">
    <div><label class="l">Photo link</label><input name="image_url" id="iu" placeholder="https://..." value="{{ it.image if it and it.image and not it.image.startswith('/u/') }}"></div>
    <div><label class="l">Or upload from device</label><input type="file" name="image_file" id="if" accept="image/png,image/jpeg,image/gif,image/webp"></div>
  </div>
  {% if it and it.image %}<label class="sw" style="margin-top:10px"><input type="checkbox" name="rm_image" value="1">Remove photo</label>{% endif %}
  <label class="l" style="margin-top:14px">Icon</label>
  <div class="picker">{% for n in picker %}<label class="ip"><input type="radio" name="icon" value="{{ n }}" {{ 'checked' if (it.icon if it else 'bolt') == n }}>{{ icon(n) }}</label>{% endfor %}</div>
  <label class="sw" style="margin:14px 0"><input type="checkbox" name="visible" value="1" {{ 'checked' if (it.visible if it else 1) }}>Visible on site</label>
  <button class="btn">Save</button>
</form></div>
<script>function k(){var h=document.getElementById('kind').value==='html';document.getElementById('cl').textContent=h?'Full HTML code (hosted at /t/ID)':'Link (https://...)';
document.getElementById('hfb').style.display=h?'':'none';
document.getElementById('ct').placeholder=h?'<!doctype html>...':'https://example.com';document.getElementById('ct').style.minHeight=h?'320px':'80px'}k();
document.getElementById('hf').onchange=function(){var f=this.files[0];if(!f)return;var r=new FileReader();r.onload=function(){document.getElementById('ct').value=r.result};r.readAsText(f)};
var pv=document.getElementById('pv');function show(u){pv.innerHTML='';if(!u)return;var i=document.createElement('img');i.src=u;pv.append(i)}
document.getElementById('iu').oninput=function(){show(this.value)};
document.getElementById('if').onchange=function(){var inp=this,f=inp.files[0];if(!f)return;show(URL.createObjectURL(f));
if(f.type==='image/gif'&&f.size<2e6)return;
var im=new Image();im.onload=function(){var r=Math.min(1,600/Math.max(im.width,im.height)),c=document.createElement('canvas');c.width=Math.round(im.width*r);c.height=Math.round(im.height*r);
c.getContext('2d').drawImage(im,0,0,c.width,c.height);
c.toBlob(function(b){if(!b)return;try{var dt=new DataTransfer();dt.items.add(new File([b],'photo.webp',{type:b.type}));inp.files=dt.files}catch(e){}},'image/webp',0.85)};im.src=URL.createObjectURL(f)};</script>{% endblock %}"""

env = Environment(loader=DictLoader(T), autoescape=True)


def render(name, **c):
    c.update(icon=icon, t=session.setdefault("t", secrets.token_hex(16)), picker=PICKER)
    c.setdefault("s", S())
    return env.get_template(name).render(**c)


@app.errorhandler(413)
def too_large(_):
    return "File too large (max " + str(MAX_MB) + " MB). Go back and choose a smaller file.", 413


@app.before_request
def csrf():
    if request.method == "POST" and request.path.startswith("/admin") and request.path != "/admin/login":
        if not session.get("t") or request.form.get("_t") != session.get("t"):
            abort(400)


def need(f):
    @wraps(f)
    def w(*a, **k):
        if not session.get("adm"):
            return redirect("/admin/login")
        return f(*a, **k)
    return w


# ---------------- public ----------------
@app.route("/")
def index():
    items = [dict(r) for r in q("SELECT * FROM items WHERE visible=1 ORDER BY sort, id")]
    return render("index.html", items=items)


@app.route("/t/<int:i>")
def open_item(i):
    it = q("SELECT * FROM items WHERE id=? AND visible=1", (i,), True)
    if not it:
        abort(404)
    if it["kind"] == "html":
        return Response(it["content"], mimetype="text/html")
    return redirect(it["content"])


@app.route("/api/chat", methods=["GET", "POST"])
def chat():
    now = int(time.time())
    d = request.get_json(silent=True) or {}
    sid = (request.args.get("sid") or d.get("sid") or "")[:40]
    if sid:
        q("INSERT OR REPLACE INTO online VALUES(?,?)", (sid, now))
    if request.method == "POST":
        name = re.sub(r"\s+", " ", str(d.get("name", ""))).strip()[:20]
        text = str(d.get("text", "")).strip()[:300]
        if not name or not text or S().get("chat_on") != "1":
            return jsonify(ok=False), 400
        q("INSERT INTO msgs(name,text,ts) VALUES(?,?,?)", (name, text, now))
    q("DELETE FROM online WHERE ts<?", (now - 60,))
    n = q("SELECT COUNT(*) c FROM online WHERE ts>?", (now - 30,), True)["c"]
    rows = q("SELECT id,name,text,ts FROM msgs ORDER BY id DESC LIMIT 60")[::-1]
    return jsonify(msgs=[dict(r) for r in rows], online=n)


# ---------------- admin ----------------
@app.route("/admin/login", methods=["GET", "POST"])
def login():
    err = False
    if request.method == "POST":
        if secrets.compare_digest(request.form.get("password", ""), ADMIN_PASSWORD):
            session["adm"] = True
            return redirect("/admin")
        time.sleep(1)
        err = True
    return render("login.html", err=err)


@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/admin")
@need
def admin():
    items = [dict(r) for r in q("SELECT * FROM items ORDER BY sort, id")]
    msgs = [dict(r) for r in q("SELECT * FROM msgs ORDER BY id DESC LIMIT 100")]
    online = q("SELECT COUNT(*) c FROM online WHERE ts>?", (int(time.time()) - 30,), True)["c"]
    return render("admin.html", items=items, msgs=msgs, online=online)


@app.route("/admin/settings", methods=["POST"])
@need
def settings():
    for k in DEFAULTS:
        if k == "chat_on":
            v = "1" if request.form.get("chat_on") else "0"
        else:
            v = request.form.get(k, "").strip()[:300]
        q("INSERT OR REPLACE INTO settings VALUES(?,?)", (k, v))
    return redirect("/admin")


def sniff(b):
    if b[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if b[:4] == b"GIF8":
        return "image/gif"
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        return "image/webp"
    return None


def drop_upload(path):
    m = re.match(r"^/u/(\d+)$", path or "")
    if m:
        q("DELETE FROM uploads WHERE id=?", (int(m.group(1)),))


@app.route("/u/<int:i>")
def upload(i):
    r = q("SELECT mime,data FROM uploads WHERE id=?", (i,), True)
    if not r:
        abort(404)
    resp = Response(r["data"], mimetype=r["mime"])
    resp.headers["Cache-Control"] = "public, max-age=86400"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.route("/admin/item", methods=["GET", "POST"])
@app.route("/admin/item/<int:i>", methods=["GET", "POST"])
@need
def item(i=None):
    it = dict(q("SELECT * FROM items WHERE id=?", (i,), True) or {}) if i else None
    if i and not it:
        abort(404)
    err = None
    if request.method == "POST":
        f = request.form
        kind = "html" if f.get("kind") == "html" else "link"
        content = f.get("content", "").strip()
        try:
            sort = int(f.get("sort") or 0)
        except ValueError:
            sort = 0
        icn = f.get("icon") if f.get("icon") in ICONS else "bolt"
        vis = 1 if f.get("visible") else 0
        cat = "game" if f.get("cat") == "game" else "tool"
        title = f.get("title", "").strip()[:80]
        descr = f.get("descr", "").strip()[:200]
        badge = f.get("badge", "").strip()[:12].upper()
        if not content:
            err = "Content is empty: add a link, paste code, or upload an HTML file."
        elif kind == "link" and not re.match(r"^(https?://|/)", content):
            content = "https://" + content
        newimg = None
        if not err:
            file = request.files.get("image_file")
            url = f.get("image_url", "").strip()
            if file and file.filename:
                data = file.read()
                mime = sniff(data)
                if not mime:
                    err = "Photo must be a JPG, PNG, GIF or WEBP image."
                else:
                    cur = db().execute("INSERT INTO uploads(mime,data) VALUES(?,?)", (mime, data))
                    db().commit()
                    newimg = "/u/%d" % cur.lastrowid
            elif url:
                newimg = url if re.match(r"^(https?://|/)", url) else "https://" + url
            elif f.get("rm_image"):
                newimg = ""
        if err:
            shown = dict(it or {}, title=title, descr=descr, cat=cat, badge=badge, sort=sort,
                         kind=kind, content=content, visible=vis, icon=icn)
            return render("item.html", it=shown, err=err)
        old = (it or {}).get("image") or ""
        if newimg is None:
            image = old
        else:
            image = newimg
            if old != newimg:
                drop_upload(old)
        vals = (title, descr, cat, badge, icn, kind, content, sort, vis, image)
        if i:
            q("UPDATE items SET title=?,descr=?,cat=?,badge=?,icon=?,kind=?,content=?,sort=?,visible=?,image=? WHERE id=?", vals + (i,))
        else:
            q("INSERT INTO items(title,descr,cat,badge,icon,kind,content,sort,visible,image) VALUES(?,?,?,?,?,?,?,?,?,?)", vals)
        return redirect("/admin")
    return render("item.html", it=it, err=err)


@app.route("/admin/item/<int:i>/toggle", methods=["POST"])
@need
def toggle(i):
    q("UPDATE items SET visible=1-visible WHERE id=?", (i,))
    return redirect("/admin")


@app.route("/admin/item/<int:i>/delete", methods=["POST"])
@need
def delete(i):
    r = q("SELECT image FROM items WHERE id=?", (i,), True)
    if r:
        drop_upload(r["image"])
    q("DELETE FROM items WHERE id=?", (i,))
    return redirect("/admin")


@app.route("/admin/msg/<int:i>/delete", methods=["POST"])
@need
def msg_del(i):
    q("DELETE FROM msgs WHERE id=?", (i,))
    return redirect("/admin")


@app.route("/admin/msgs/clear", methods=["POST"])
@need
def msgs_clear():
    q("DELETE FROM msgs")
    return redirect("/admin")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
