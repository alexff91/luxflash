"""30 days to the Sproochentest: one page a day, printed, in English and Russian.

Why. The site had a deck of 2,300 words and nothing that said where to start or
what to do on Tuesday. People who come for Luxembourgish come for one exam —
the Sproochentest (speaking at A2, listening at B1) — so the path is built
backwards from it: every day one grammar rule with two exercises, two of the
exam's own speaking questions with a model answer, eight words around the same
topic with the dictionary's recording, and one episode of INLL's podcast, the
institute that runs the exam.

Everything here comes from data that has already been checked: words and
examples from lod.lu via lux-teacher/tools/match_lod.py, grammar and answers
from the lesson bot after two review passes and tools/check_lb.py. The page
adds no Luxembourgish of its own.

    python3 scripts/path_pages.py      # path/index.html + path/day-N/index.html
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LT = Path.home() / 'Claude' / 'lux-teacher' / 'data'
OUT = ROOT / 'path'
ORIGIN = 'https://luxflash.alftech.space'
DAYS = 30
PER_DAY = 8

esc = lambda s: html.escape(str(s or ''), quote=True)

# Exam topic → deck categories that hold its vocabulary.
TOPIC_CATS = {
    'famill': ['family', 'people', 'ages', 'relationships'],
    'aarbecht': ['work', 'profession', 'office', 'money'],
    'wunneng': ['home', 'furniture', 'household', 'buildings'],
    'gesondheet': ['health', 'body', 'medicine'],
    'vakanz': ['travel', 'tourism', 'holidays', 'country', 'geography'],
    'hobbyen': ['actions', 'sport', 'emotions', 'routine'],
    'sproochen': ['greetings', 'phrase', 'school', 'question'],
    'akaf': ['shopping', 'money', 'clothes', 'quantity', 'colors'],
    'transport': ['transport', 'directions', 'city'],
    'joreszait': ['weather', 'calendar', 'time', 'nature'],
    'technologie': ['tech', 'media', 'office'],
    'stot': ['household', 'cleaning', 'kitchen', 'routine'],
    'sport': ['sport', 'body', 'health'],
    'iessen': ['food', 'kitchen', 'cooking', 'fruit', 'vegetable', 'meal', 'restaurant'],
    'schoul': ['school', 'academic', 'number'],
    'frenn': ['people', 'relationships', 'emotions', 'greetings'],
    'lëtzebuerg': ['luxembourg', 'geography', 'country', 'society'],
    'feierdeeg': ['holidays', 'calendar', 'luxembourg'],
}
# The answer bank describes a real person in two places; the public path uses
# an invented learner instead (sproochentest-en.json, lb_public).
RU_PUBLIC = {
    'Ech si bestuet an ech hunn eng Fra a Kanner. Meng Famill kënnt aus Portugal, mee mir wunnen elo zu Lëtzebuerg. Mir verstinn eis gutt.':
        'Я женат, у меня жена и дети. Моя семья из Португалии, но сейчас мы живём в Люксембурге. Мы хорошо ладим.',
    'Ech schwätze Portugisesch, Englesch an e bësse Lëtzebuergesch. Ech léieren ëmmer nach dobäi.':
        'Я говорю по-португальски, по-английски и немного по-люксембургски. Я всё ещё учусь.',
}


def article(gender, word):
    """den/de/d' as Luxembourgish writes them, n-rule included."""
    if gender == 'm':
        return 'den ' if word[:1].lower() in 'aeiouäëéèhdtzn' else 'de '
    if gender in ('f', 'n'):
        return "d'"
    return ''


def load():
    words = json.loads((LT / 'lesson-words.json').read_text())
    en_ex = json.loads((LT / 'en-examples.json').read_text())
    g_en = json.loads((LT / 'grammar-en.json').read_text())['rules']
    g_ru = json.loads((LT / 'grammar-ru.json').read_text())['rules']
    st = json.loads((LT / 'sproochentest.json').read_text())['topics']
    st_en = json.loads((LT / 'sproochentest-en.json').read_text())['topics']
    pods = json.loads((LT / 'podcasts.json').read_text())['inll']
    return words, en_ex, g_en, g_ru, st, st_en, pods


def plan():
    words, en_ex, g_en, g_ru, st, st_en, pods = load()
    assert len(g_en) == len(g_ru)

    # Speaking: walk the 18 topics in order, two questions a day.
    qs = []
    for t in st:
        te = st_en[t['key']]
        for q, qe in zip(t['qs'], te['qs']):
            a = qe.get('lb_public', q['a'])
            qs.append({'topic': t['key'], 'topic_lb': t['lb'], 'topic_en': te['en'], 'topic_ru': t['ru'],
                       'q': q['q'], 'q_en': qe['q'], 'q_ru': q['qru'],
                       'a': a, 'a_en': qe['a'], 'a_ru': RU_PUBLIC.get(a, q['aru'])})

    # Listening: INLL episodes from the easiest level up, oldest first.
    rank = {'A1': 0, 'A1-A2': 1, 'A2': 2, 'A2-B1': 3}
    eps = sorted((e for e in pods if e.get('level') in rank and e.get('link')),
                 key=lambda e: (rank[e['level']], e['date']))

    # Words: A1 before A2, only those with a recording and a translated example.
    usable = [w for w in words if w.get('lodId') and w.get('examples') and w['level'] in ('A1', 'A2')
              and w['examples'][0]['lb'] in en_ex]
    used = set()

    days = []
    for d in range(DAYS):
        day = {'n': d + 1}
        if d < len(g_en):
            day['grammar'] = {'en': g_en[d], 'ru': g_ru[d]}
        day['questions'] = qs[(2 * d) % len(qs):(2 * d) % len(qs) + 2]
        topic = day['questions'][0]['topic']
        cats = TOPIC_CATS.get(topic, [])
        pick = []
        for level in ('A1', 'A2'):
            for w in usable:
                if len(pick) >= PER_DAY:
                    break
                if w['id'] not in used and w['level'] == level and w['category'] in cats:
                    pick.append(w); used.add(w['id'])
        for w in usable:                       # topic ran dry: fill with the next A1/A2 words
            if len(pick) >= PER_DAY:
                break
            if w['id'] not in used:
                pick.append(w); used.add(w['id'])
        day['words'] = []
        for w in pick:
            ex = w['examples'][0]
            lb = w['lb'] if w['pos'] != 'noun' else article(w.get('gender'), w['lb']) + w['lb']
            day['words'].append({'id': w['id'], 'lb': lb, 'en': w['en'], 'ru': w.get('ru', ''),
                                 'audio': w['lodId'].lower(), 'ex': ex['lb'], 'ex_en': en_ex[ex['lb']],
                                 'ex_ru': ex.get('ru') or ''})
        if d < len(eps):
            e = eps[d]
            day['listen'] = {'title': e['title'], 'level': e['level'], 'link': e['link'], 'audio': e.get('audio')}
        days.append(day)
    return days


UI = {
    'en': {'day': 'Day', 'grammar': 'Rule of the day', 'try': 'Try it', 'show': 'Show answer',
           'speak': 'Say it out loud', 'speak_note': 'These are questions from the oral part of the Sproochentest. Answer in your own words first, then compare.',
           'model': 'Model answer', 'words': 'Eight words', 'words_note': '▶ plays the recording from lod.lu.',
           'listen': 'Listen', 'listen_note': 'An episode of Poterkëscht, the podcast of INLL — the institute that runs the exam. Listen once without reading, then again.',
           'done': 'Mark day {n} as done', 'doneok': 'Day {n} done — see you tomorrow', 'next': 'Next day →', 'prev': '← Previous day',
           'all': 'All 30 days', 'drill': 'Drill these words', 'review': 'Review day: go back over the rules you found hardest and answer every question below out loud.',
           'mock': 'Mock exam: answer each question in at least three sentences, without looking.'},
    'ru': {'day': 'День', 'grammar': 'Правило дня', 'try': 'Попробуй', 'show': 'Показать ответ',
           'speak': 'Скажи вслух', 'speak_note': 'Это вопросы устной части Sproochentest. Сначала ответь сам, потом сравни.',
           'model': 'Пример ответа', 'words': 'Восемь слов', 'words_note': '▶ — запись из lod.lu. Кнопка внизу — повторить все восемь карточками.',
           'listen': 'Послушай', 'listen_note': 'Выпуск Poterkëscht — подкаста INLL, института, который проводит экзамен. Сначала послушай без текста, потом ещё раз.',
           'done': 'Отметить день {n}', 'doneok': 'День {n} пройден — до завтра', 'next': 'Следующий день →', 'prev': '← Предыдущий день',
           'all': 'Все 30 дней', 'drill': 'Повторить слова карточками', 'review': 'День повторения: вернись к самым трудным правилам и ответь вслух на все вопросы ниже.',
           'mock': 'Пробный экзамен: на каждый вопрос — минимум три предложения, не подглядывая.'},
}


def bi(key, n=None, tag='span'):
    en, ru = UI['en'][key], UI['ru'][key]
    if n is not None:
        en, ru = en.format(n=n), ru.format(n=n)
    return f'<{tag} class="l-en">{esc(en)}</{tag}><{tag} class="l-ru">{esc(ru)}</{tag}>'


def two(en, ru, tag='span'):
    return f'<{tag} class="l-en">{esc(en)}</{tag}><{tag} class="l-ru">{esc(ru or en)}</{tag}>'


CSS = '''
  /* the corner café, as in the app: cream, Septfontaines blue, an awning (28 Oct 2026) */
  @import url("https://fonts.googleapis.com/css2?family=Bree+Serif&family=Lato:wght@400;700;900&display=swap");
  :root { --paper:#fbeee0; --card:#fffaf0; --ink:#1d3346; --soft:#5b6470; --line:#ecd2bd;
    --accent:#245877; --accent-soft:#e3edf3; --red:#b84638; --ok:#3f7d56;
    --sans:Lato,-apple-system,"Segoe UI",Roboto,sans-serif; --serif:"Bree Serif",Georgia,serif; }
  h1, h2, h3 { font-family:var(--serif); font-weight:400; }
  body::before { content:""; display:block; height:22px; background:repeating-linear-gradient(90deg,#b84638 0 24px,#fff4d5 24px 48px);
    -webkit-mask:linear-gradient(#000,#000) 0 0/100% 10px no-repeat,radial-gradient(12px 12px at 12px 10px,#000 98%,transparent) 0 0/24px 22px repeat-x; mask:linear-gradient(#000,#000) 0 0/100% 10px no-repeat,radial-gradient(12px 12px at 12px 10px,#000 98%,transparent) 0 0/24px 22px repeat-x; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--paper); color:var(--ink); font:17px/1.6 var(--sans); -webkit-font-smoothing:antialiased; }
  html[data-lang="ru"] .l-en, html:not([data-lang="ru"]) .l-ru { display:none !important; }
  .wrap { max-width:760px; margin:0 auto; padding:18px 16px 70px; }
  a { color:var(--accent); }
  .top { display:flex; justify-content:space-between; align-items:center; gap:12px; font-size:14px; margin-bottom:18px; }
  .top a { text-decoration:none; font-weight:600; }
  .lang { display:flex; border:1px solid var(--line); border-radius:999px; overflow:hidden; }
  .lang button { border:0; background:var(--card); padding:7px 12px; font:600 13px var(--sans); color:var(--soft); cursor:pointer; min-height:36px; }
  .lang button[aria-pressed="true"] { background:var(--ink); color:#fff; }
  .flag { display:inline-block; width:22px; height:14px; border-radius:2px; vertical-align:-1px; margin-right:6px;
    background:linear-gradient(#ed2939 0 33%, #fff 33% 66%, #00a1de 66%); box-shadow:0 0 0 1px var(--line); }
  h1 { font-size:clamp(26px,6vw,38px); line-height:1.1; letter-spacing:-.02em; margin:6px 0 8px; text-wrap:balance; }
  .eyebrow { font-size:13px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:var(--accent); }
  .lede { color:var(--soft); margin:0 0 22px; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:18px; margin:0 0 16px; }
  .card h2 { font-size:13px; letter-spacing:.07em; text-transform:uppercase; color:var(--soft); margin:0 0 10px; }
  .card h3 { font-size:21px; line-height:1.25; margin:0 0 8px; }
  .rule { margin:0 0 12px; }
  .ex { margin:0; padding:0; list-style:none; }
  .ex li { padding:8px 0; border-top:1px solid var(--line); }
  .ex b { display:block; font-weight:650; }
  .ex span { color:var(--soft); font-size:15px; }
  details { border-top:1px solid var(--line); padding:10px 0 2px; }
  summary { cursor:pointer; color:var(--ink); list-style:none; }
  summary::-webkit-details-marker { display:none; }
  summary::before { content:'＋ '; color:var(--accent); font-weight:700; }
  details[open] summary::before { content:'－ '; }
  details .ans { margin-top:6px; padding:9px 12px; background:var(--accent-soft); border-radius:10px; font-weight:600; }
  .q { padding:12px 0; border-top:1px solid var(--line); }
  .q:first-of-type { border-top:0; }
  .q .lb { font-size:19px; font-weight:650; }
  .q .tr { color:var(--soft); font-size:15px; }
  .note { color:var(--soft); font-size:14.5px; margin:-4px 0 10px; }
  .w { display:grid; grid-template-columns:auto 1fr; gap:2px 12px; padding:11px 0; border-top:1px solid var(--line); }
  .w:first-of-type { border-top:0; }
  .say { width:40px; height:40px; border-radius:50%; border:1px solid var(--line); background:var(--accent-soft); color:var(--accent); cursor:pointer; font-size:13px; grid-row:1 / span 2; }
  .say.on { background:var(--accent); color:#fff; }
  .w .lb { font-weight:700; font-size:18px; }
  .w .mean { color:var(--soft); font-size:15px; margin-left:6px; font-weight:400; }
  .w .wex { grid-column:2; font-size:14.5px; color:var(--soft); }
  .w .wex b { color:var(--ink); font-weight:600; }
  audio { width:100%; margin:8px 0 4px; }
  .btn { display:inline-flex; align-items:center; justify-content:center; min-height:50px; padding:0 22px; border-radius:12px;
    background:var(--accent); color:#fff; font:700 16px var(--sans); border:0; cursor:pointer; text-decoration:none; }
  .btn.ghost { background:var(--card); color:var(--ink); border:1px solid var(--line); }
  .btn.done { background:var(--ok); }
  .row { display:flex; gap:10px; flex-wrap:wrap; justify-content:space-between; align-items:center; margin:22px 0; }
  .grid { display:grid; grid-template-columns:repeat(5,1fr); gap:8px; margin:18px 0; }
  .grid a { display:flex; flex-direction:column; align-items:center; justify-content:center; min-height:62px; border-radius:12px;
    background:var(--card); border:1px solid var(--line); text-decoration:none; color:var(--ink); font-weight:700; }
  .grid a small { font-weight:500; font-size:11px; color:var(--soft); text-align:center; line-height:1.2; padding:0 4px; overflow-wrap:anywhere; hyphens:auto; }
  .grid a.done { background:var(--ok); color:#fff; border-color:var(--ok); }
  .grid a.done small { color:#dff5e9; }
  .grid a.today { border:2px solid var(--accent); }
  .facts { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; margin:16px 0 22px; }
  .facts div { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; }
  .facts b { display:block; font-size:22px; }
  .facts span { font-size:13px; color:var(--soft); }
  footer { margin-top:30px; padding-top:16px; border-top:1px solid var(--line); color:var(--soft); font-size:13.5px; }
  @media (max-width:520px) { .grid { grid-template-columns:repeat(3,1fr); gap:6px; } .facts { grid-template-columns:1fr; } }
'''

JS = '''
<script>
(function () {
  var KEY = 'lux-path-v1', st;
  try { st = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { st = {}; }
  st.done = st.done || {};
  function save() { try { localStorage.setItem(KEY, JSON.stringify(st)); } catch (e) {} }
  function setLang(l) {
    document.documentElement.dataset.lang = l; st.lang = l; save();
    document.querySelectorAll('.lang button').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.l === l ? 'true' : 'false'); });
  }
  var nav = (navigator.language || '').toLowerCase();
  setLang(st.lang || (nav.indexOf('ru') === 0 || nav.indexOf('uk') === 0 ? 'ru' : 'en'));
  document.querySelectorAll('.lang button').forEach(function (b) { b.onclick = function () { setLang(b.dataset.l); }; });

  var day = Number(document.body.dataset.day || 0);
  var doneBtn = document.getElementById('done');
  function paint() {
    if (doneBtn && st.done[day]) { doneBtn.classList.add('done'); doneBtn.querySelectorAll('.d1').forEach(function (x) { x.hidden = true; }); doneBtn.querySelectorAll('.d2').forEach(function (x) { x.hidden = false; }); }
    var next = 0; for (var i = 1; i <= 30; i++) if (!st.done[i]) { next = i; break; }
    document.querySelectorAll('.grid a').forEach(function (a) {
      var n = Number(a.dataset.n); a.classList.toggle('done', !!st.done[n]); a.classList.toggle('today', n === next);
    });
    var go = document.getElementById('continue');
    if (go && next) { go.href = 'day-' + next + '/'; go.querySelector('.n').textContent = next; }
  }
  if (doneBtn) doneBtn.onclick = function () {
    if (!st.done[day]) { st.done[day] = Date.now(); save(); try { fetch('/_used?path=' + day, { method: 'POST', keepalive: true }); } catch (e) {} }
    paint();
  };
  paint();

  var audio = new Audio(), ext = audio.canPlayType('audio/ogg; codecs=vorbis') ? ['OGG', 'ogg'] : ['AAC', 'm4a'];
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.say'); if (!b) return;
    document.querySelectorAll('.say.on').forEach(function (x) { x.classList.remove('on'); });
    audio.pause(); audio.src = 'https://lod.lu/uploads/' + ext[0] + '/' + b.dataset.id + '.' + ext[1];
    b.classList.add('on'); audio.onended = audio.onerror = function () { b.classList.remove('on'); };
    audio.play().catch(function () { b.classList.remove('on'); });
  });
})();
</script>'''


def page(title, desc, canonical, body, day=0):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{ORIGIN}/og.png">
<meta name="twitter:card" content="summary_large_image">
<style>{CSS}</style>
</head>
<body data-day="{day}">
<div class="wrap">
<div class="top"><a href="/path/"><span class="flag"></span>{bi("all")}</a>
<div class="lang" role="group" aria-label="Language"><button data-l="en" aria-pressed="true">EN</button><button data-l="ru" aria-pressed="false">RU</button></div></div>
{body}
<footer>
  <p>{two("Not official, not affiliated with INLL or the state. Words and examples are checked against the Lëtzebuerger Online Dictionnaire (lod.lu); recordings are LOD's. Progress stays in this browser.", "Неофициально и не связано с INLL или государством. Слова и примеры сверены со словарём LOD (lod.lu), записи — из LOD. Прогресс хранится в этом браузере.")}</p>
  <p><a href="{ORIGIN}/">LuxFlash — 2,300 words as flashcards</a> · <a href="https://vivre.alftech.space/">{two("Vivre ensemble test practice", "Тренажёр теста Vivre ensemble")}</a> · <a href="mailto:a@alftech.space?subject=Lux%2030%20days">a@alftech.space</a></p>
</footer>
</div>
{JS}
</body>
</html>
'''


def day_html(day, total):
    n = day['n']
    parts = [f'<div class="eyebrow">{bi("day")} {n} / {total}</div>']
    g = day.get('grammar')
    title_en = g['en']['t'] if g else ('Review' if n < total else 'Mock exam')
    title_ru = g['ru']['t'] if g else ('Повторение' if n < total else 'Пробный экзамен')
    parts.append(f'<h1>{two(title_en, title_ru)}</h1>')
    t0 = day['questions'][0]
    parts.append(f'<p class="lede">{two("Speaking topic: " + t0["topic_en"], "Тема разговора: " + t0["topic_ru"])} · <i>{esc(t0["topic_lb"])}</i></p>')

    if g:
        ex = ''.join(f'<li><b>{esc(lb)}</b>{two(en, ru)}</li>' for (lb, en), (_, ru) in zip(g['en']['ex'], g['ru']['ex']))
        drills = ''.join(f'<details><summary>{two(pe, pr)}</summary><div class="ans">{esc(ans)}</div></details>'
                         for (pe, ans), (pr, _) in zip(g['en']['dr'], g['ru']['dr']))
        parts.append(f'<section class="card"><h2>{bi("grammar")}</h2><p class="rule">{two(g["en"]["r"], g["ru"]["r"])}</p>'
                     f'<ul class="ex">{ex}</ul><h2 style="margin-top:14px">{bi("try")}</h2>{drills}</section>')
    else:
        parts.append(f'<section class="card"><p class="rule">{bi("review" if n < total else "mock")}</p></section>')

    qs = ''.join(f'<div class="q"><div class="lb">{esc(q["q"])}</div><div class="tr">{two(q["q_en"], q["q_ru"])}</div>'
                 f'<details><summary>{bi("model")}</summary><div class="ans">{esc(q["a"])}</div>'
                 f'<p class="tr">{two(q["a_en"], q["a_ru"])}</p></details></div>' for q in day['questions'])
    parts.append(f'<section class="card"><h2>{bi("speak")}</h2><p class="note">{bi("speak_note")}</p>{qs}</section>')

    ws = ''.join(f'<div class="w"><button class="say" data-id="{esc(w["audio"])}" aria-label="Play {esc(w["lb"])}">▶</button>'
                 f'<div><span class="lb">{esc(w["lb"])}</span><span class="mean">{two(w["en"], w["ru"])}</span></div>'
                 f'<div class="wex"><b>{esc(w["ex"])}</b> — {two(w["ex_en"], w["ex_ru"] or w["ex_en"])}</div></div>' for w in day['words'])
    drill = '/drill/#w=' + ','.join(w['id'] for w in day['words']) + f'&n={n}'
    parts.append(f'<section class="card"><h2>{bi("words")}</h2><p class="note">{bi("words_note")}</p>{ws}'
                 # The drill speaks both languages since 28 Oct 2026 (&ui=en / &ui=ru).
                 f'<p style="margin:14px 0 0"><a class="btn ghost l-ru" href="{drill}&ui=ru">{esc(UI["ru"]["drill"])}</a>'
                 f'<a class="btn ghost l-en" href="{drill}&ui=en">{esc(UI["en"]["drill"])}</a></p></section>')

    l = day.get('listen')
    if l:
        au = f'<audio controls preload="none" src="{esc(l["audio"])}"></audio>' if l.get('audio') else ''
        parts.append(f'<section class="card"><h2>{bi("listen")}</h2><p class="note">{bi("listen_note")}</p>'
                     f'<h3>{esc(l["title"])}</h3>{au}<p style="margin:4px 0 0"><a href="{esc(l["link"])}" rel="noopener">{two("Episode page →", "Страница выпуска →")}</a></p></section>')

    nav = []
    nav.append(f'<a class="btn ghost" href="../day-{n - 1}/">{bi("prev")}</a>' if n > 1 else '<span></span>')
    nav.append(f'<button class="btn" id="done"><span class="d1">{bi("done", n)}</span><span class="d2" hidden>{bi("doneok", n)}</span></button>')
    nav.append(f'<a class="btn ghost" href="../day-{n + 1}/">{bi("next")}</a>' if n < total else '<span></span>')
    parts.append('<div class="row">' + ''.join(nav) + '</div>')
    return '\n'.join(parts)


def index_html(days):
    grid = ''.join(f'<a href="day-{d["n"]}/" data-n="{d["n"]}">{d["n"]}<small>{esc(d["questions"][0]["topic_lb"].replace(chr(39), "’")[:10])}</small></a>' for d in days)
    return f'''<div class="eyebrow">Sproochentest · A2</div>
<h1>{two("30 days to the Sproochentest", "30 дней до Sproochentest")}</h1>
<p class="lede">{two("Fifteen minutes a day for the Luxembourgish exam you need for citizenship: one grammar rule with exercises, two of the exam's speaking questions with a model answer, eight words with native recordings, and one episode of the official INLL podcast. Free, no account.", "Пятнадцать минут в день к экзамену по люксембургскому, который нужен для гражданства: одно правило с упражнениями, два вопроса устной части с примером ответа, восемь слов с записями носителей и выпуск официального подкаста INLL. Бесплатно, без регистрации.")}</p>
<div class="facts"><div><b>A2</b><span>{two("speaking — what the exam asks", "говорение — уровень экзамена")}</span></div><div><b>B1</b><span>{two("listening — the harder half", "аудирование — сложная половина")}</span></div><div><b>240</b><span>{two("words with LOD recordings", "слов с записями LOD")}</span></div></div>
<p><a class="btn" id="continue" href="day-1/"><span><span class="l-en">Start — day&nbsp;</span><span class="l-ru">Начать — день&nbsp;</span><span class="n">1</span>&nbsp;→</span></a></p>
<div class="grid">{grid}</div>
<section class="card"><h2>{two("How it works", "Как это устроено")}</h2>
<p class="rule">{two("Each day stands on its own, so a missed day costs nothing: open the next one. Mark a day done and the grid remembers it in this browser. Days 27–30 are review and a mock oral exam. The written and listening parts of the Sproochentest are trained by the podcast; the citizenship course test (Vivre ensemble) has its own trainer.", "Каждый день самостоятельный — пропуск ничего не ломает, открывай следующий. Отметь день — сетка запомнит в этом браузере. Дни 27–30 — повторение и пробный устный экзамен. Аудирование тренирует подкаст, а для теста по курсу гражданства (Vivre ensemble) есть отдельный тренажёр.")}</p>
<p style="margin:0"><a href="https://vivre.alftech.space/">{two("Vivre ensemble practice →", "Тренажёр Vivre ensemble →")}</a></p></section>'''


def main():
    days = plan()
    OUT.mkdir(exist_ok=True)
    total = len(days)
    for d in days:
        g = d.get('grammar')
        topic = d['questions'][0]['topic_en']
        title = f'Luxembourgish day {d["n"]}: {g["en"]["t"] if g else "review"} · {topic} — 30 days to the Sproochentest'
        desc = (f'Day {d["n"]} of 30: {g["en"]["t"].lower() if g else "review"}, two Sproochentest speaking questions on '
                f'{topic.lower()} with a model answer, eight words with native recordings and an INLL podcast episode.')
        path = OUT / f'day-{d["n"]}' / 'index.html'
        path.parent.mkdir(exist_ok=True)
        path.write_text(page(title, desc, f'{ORIGIN}/path/day-{d["n"]}/', day_html(d, total), d['n']))
    (OUT / 'index.html').write_text(page('30 days to the Sproochentest — free Luxembourgish practice',
                                         'A free 30-day path to the Luxembourgish Sproochentest: grammar, the exam\'s speaking questions with model answers, words with native recordings, the INLL podcast. In English and Russian.',
                                         f'{ORIGIN}/path/', index_html(days)))
    words = sum(len(d['words']) for d in days)
    print(f'path: {total} days, {words} words, {sum(len(d["questions"]) for d in days)} questions, '
          f'{sum(1 for d in days if d.get("listen"))} episodes')


if __name__ == '__main__':
    main()
