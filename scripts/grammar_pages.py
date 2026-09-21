"""Грамматика и разговорник: то, чего нет ни в одной карточке.

Карточки учат словам, а человек спотыкается о другое: почему «den» вдруг
становится «de», почему глагол уезжает в конец, как вообще сказать «я бы
хотел». Тридцать два правила с примерами и сто шестьдесят шесть готовых
фраз лежали в личном телеграм-боте (репозиторий lux-teacher), который
писал их одному человеку по одной в день. Здесь они напечатаны целиком.

Правила восьми самых трудных тем объяснены ещё и по-русски: среди тех,
кто это учит, русскоязычных примерно столько же, сколько англоязычных.

    python3 scripts/grammar_pages.py     # grammar/ и phrases/ + карта сайта
"""
import html
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = Path.home() / 'Library/Caches/alf-build/lux-teacher/data/lessons.json'
ORIGIN = 'https://luxflash.alftech.space'
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lux_block  # noqa: E402

esc = lambda s: html.escape(str(s or ''), quote=True)

# Правила разложены по тому, обо что спотыкаются, а не по порядку в файле.
GROUPS = [
    ('first-words', 'The first words', [
        'Moien! — the universal greeting', 'Polite magic words', 'Question words',
        'Loan words are your friends', 'The letters ë, é, ä']),
    ('verbs', 'Verbs', [
        'sinn — to be', 'hunn — to have', 'ginn — the multi-tool verb', 'Modal verbs',
        'Perfect tense — how you talk about the past', 'Separable verbs', 'ze + infinitive',
        'Future — usually just present tense', 'wëssen vs. kennen',
        'gär hunn & hätt gär — liking and ordering', 'Et gëtt — ‘there is / there are’']),
    ('word-order', 'Word order', [
        'Verb-second (V2) word order', 'Word order with weil-type clauses', 'Negation: net and keen/keng']),
    ('nouns', 'Nouns, articles and people', [
        'Definite articles: den / d’', 'Indefinite articles: en / eng', 'The Eifeler Reegel (n-rule)',
        'Personal pronouns', 'Possessives', 'du vs. Dir — informal and polite ‘you’',
        'Diminutive -chen / -ercher', 'Common dative prepositions']),
    ('numbers-time', 'Numbers and time', [
        'Numbers 1–12', 'Numbers: units before tens', 'Telling the time', 'Days of the week',
        'Comparison with méi']),
]

# Те же правила, объяснённые по-русски: в файле они идут отдельными записями.
RU_FOR = {
    'Perfekt: hunn/sinn + Partizip': 'Perfect tense — how you talk about the past',
    'Modalverben: kann, muss, wëll, däerf': 'Modal verbs',
    'Wortstellung: verb an zweiter Stelle': 'Verb-second (V2) word order',
    'Nebensätze mit datt/well: глагол в конец': 'Word order with weil-type clauses',
    'Vergläich: méi … wéi / esou … wéi': 'Comparison with méi',
    'Zukunft: einfach das Präsens': 'Future — usually just present tense',
    'Höflechkeet: Dir-Form': 'du vs. Dir — informal and polite ‘you’',
    'Negatioun: net a keen': 'Negation: net and keen/keng',
}

# Разговорник: 166 фраз идут тематическими блоками, границы выставлены по смыслу.
PHRASE_SECTIONS = [
    (0, 24, 'Meeting someone', 'Greetings, names, where you are from.'),
    (24, 48, 'Where you live and work', 'The questions you get asked first, and how to ask them back.'),
    (48, 72, 'At a counter or a doctor', 'Appointments, prices, paperwork.'),
    (72, 96, 'When you do not understand', 'Asking for a repeat, admitting a mistake, asking how a word is written.'),
    (96, 120, 'Practising the language', 'Saying that you are learning, and asking people to keep going in Luxembourgish.'),
    (120, 144, 'Saying what you think', 'Opinions, hedges, agreeing and disagreeing.'),
    (144, 166, 'Your day', 'Meals, work, evenings, the weekend.'),
]


def shell(title, description, canonical, body):
    ld = {'@context': 'https://schema.org', '@type': 'LearningResource', 'name': title,
          'description': description, 'url': canonical, 'inLanguage': 'en',
          'teaches': 'Luxembourgish', 'isAccessibleForFree': True,
          'learningResourceType': 'Reference',
          'isPartOf': {'@type': 'WebSite', 'name': 'LuxFlash', 'url': ORIGIN}}
    lux_css = lux_block.css(line='#e3e8ef', soft='#5b6779', accent='#00a1de')
    lux_html = lux_block.html('luxflash.alftech.space')
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{canonical}">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<meta property="og:type" content="article">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{canonical}">
<meta property="og:image" content="{ORIGIN}/og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="robots" content="index, follow, max-snippet:-1">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>
<style>
  :root {{ --paper:#f5f7fa; --card:#fff; --ink:#111823; --soft:#5b6779; --line:#e3e8ef;
    --accent:#00a1de; --accent-soft:#e6f6fc; --red:#ed2939;
    --sans:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--paper); color:var(--ink); font:17px/1.6 var(--sans);
    -webkit-font-smoothing:antialiased; }}
  .wrap {{ max-width:820px; margin:0 auto; padding:24px 18px 70px; }}
  a {{ color:var(--accent); }}
  .crumbs {{ font-size:13.5px; color:var(--soft); margin:0 0 16px; }}
  h1 {{ font-size:clamp(24px,5vw,34px); line-height:1.12; letter-spacing:-.02em; margin:0 0 10px;
    text-wrap:balance; }}
  h2 {{ font-size:20px; margin:30px 0 12px; letter-spacing:-.01em; }}
  h2 span {{ color:var(--soft); font-weight:400; font-size:15px; }}
  .lede {{ color:var(--soft); margin:0 0 20px; max-width:64ch; }}
  .toc {{ display:flex; flex-wrap:wrap; gap:8px; margin:0 0 8px; padding:0; list-style:none; }}
  .toc a {{ border:1px solid var(--line); background:var(--card); border-radius:999px;
    padding:7px 13px; font-size:14px; text-decoration:none; color:var(--ink); }}
  .toc a:hover {{ border-color:var(--accent); color:var(--accent); }}
  .rule {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    padding:16px 18px; margin:0 0 12px; }}
  .rule h3 {{ margin:0 0 6px; font-size:18px; }}
  .rule p {{ margin:0 0 10px; color:var(--soft); }}
  .rule .ru {{ border-left:3px solid var(--accent-soft); padding-left:11px; font-size:15px; }}
  .ex {{ list-style:none; margin:0; padding:0; }}
  .ex li {{ display:grid; grid-template-columns:1fr 1fr; gap:4px 16px; padding:7px 0;
    border-top:1px solid var(--line); }}
  .ex b {{ font-weight:600; }}
  .ex span {{ color:var(--soft); }}
  .lines {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    overflow:hidden; margin:0 0 18px; }}
  .lines div {{ display:grid; grid-template-columns:1fr 1fr; gap:4px 16px; padding:12px 16px;
    border-bottom:1px solid var(--line); }}
  .lines div:last-child {{ border-bottom:0; }}
  .lines b {{ font-weight:600; font-size:17px; }}
  .lines span {{ color:var(--soft); }}
  .cta {{ display:inline-flex; align-items:center; min-height:48px; padding:0 20px;
    border-radius:10px; background:var(--accent); color:#fff; font-weight:600;
    text-decoration:none; margin:6px 0; }}
  footer {{ margin-top:30px; padding-top:16px; border-top:1px solid var(--line);
    color:var(--soft); font-size:13.5px; }}
{lux_css}  @media (max-width:560px) {{
    .ex li, .lines div {{ grid-template-columns:1fr; }}
  }}
</style>
</head>
<body>
<div class="wrap">
{body}
  {lux_html}

  <footer>
    <p>Rules and phrases were written for a daily lesson bot and are checked against the
      <a href="https://lod.lu/" rel="noopener">Lëtzebuerger Online Dictionnaire</a> and the
      <a href="https://www.inll.lu/" rel="noopener">Institut national des langues</a>.
      Where a rule has exceptions, they are noted; where it has many, only the useful case is given.</p>
    <p><a href="{ORIGIN}/">Drill the vocabulary</a> ·
      <a href="{ORIGIN}/words/">the word list</a> ·
      <a href="https://vivre.alftech.space/questions/">citizenship test questions</a></p>
  </footer>
</div>
</body>
</html>
'''


def rule_html(rule, ru=None):
    examples = ''.join(
        f'<li><b>{esc(a)}</b><span>{esc(b)}</span></li>' for a, b in rule.get('examples', []))
    ru_note = f'<p class="ru">{esc(ru)}</p>' if ru else ''
    return (f'<div class="rule"><h3>{esc(rule["title"])}</h3>'
            f'<p>{esc(rule["explain"])}</p>{ru_note}'
            f'<ul class="ex">{examples}</ul></div>')


def main():
    data = json.loads(SRC.read_text(encoding='utf-8'))
    # Сопоставляем по смыслу, а не по символам: в файле кавычки прямые,
    # в списке ниже — типографские, и три правила терялись молча.
    def key(title):
        return re.sub(r"[^a-z0-9]+", '', title.lower())

    by_title = {key(r['title']): r for r in data['rules']}
    ru_notes = {key(RU_FOR[r['title']]): r['explain'] for r in data['rules'] if r['title'] in RU_FOR}

    # --- грамматика
    toc = ''.join(f'<li><a href="#{gid}">{esc(name)}</a></li>' for gid, name, _ in GROUPS)
    sections = []
    used = 0
    for gid, name, titles in GROUPS:
        rules = [by_title[key(t)] for t in titles if key(t) in by_title]
        used += len(rules)
        sections.append(f'<h2 id="{gid}">{esc(name)} <span>· {len(rules)}</span></h2>'
                        + ''.join(rule_html(r, ru_notes.get(key(r['title']))) for r in rules))
    missing = [t for _, _, ts in GROUPS for t in ts if key(t) not in by_title]
    if missing:
        print('ПРАВИЛА НЕ НАЙДЕНЫ:', missing)

    body = f'''  <p class="crumbs"><a href="/">LuxFlash</a> › Grammar</p>
  <h1>Luxembourgish grammar, {used} rules that actually come up</h1>
  <p class="lede">Not a reference grammar — the things a learner trips over in the first year,
    each with examples you might say out loud. Eight of the hardest are explained in Russian too.</p>
  <ul class="toc">{toc}</ul>
  {''.join(sections)}
  <p><a class="cta" href="/">Drill the words that go with them →</a></p>'''
    out = ROOT / 'grammar'
    out.mkdir(exist_ok=True)
    (out / 'index.html').write_text(shell(
        f'Luxembourgish grammar — {used} rules with examples',
        f'{used} Luxembourgish grammar rules that come up in the first year: articles and the '
        f'Eifeler Reegel, verb-second order, the perfect tense, separable verbs, du and Dir. '
        f'Each with examples. Eight explained in Russian too. Free, no sign-up.',
        f'{ORIGIN}/grammar/', body), encoding='utf-8')

    # --- разговорник
    phrases = data['phrases']
    blocks = []
    nav = []
    for start, end, name, about in PHRASE_SECTIONS:
        chunk = phrases[start:end]
        if not chunk:
            continue
        pid = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        nav.append(f'<li><a href="#{pid}">{esc(name)}</a></li>')
        lines = ''.join(f'<div><b>{esc(a)}</b><span>{esc(b)}</span></div>' for a, b in chunk)
        blocks.append(f'<h2 id="{pid}">{esc(name)} <span>· {len(chunk)}</span></h2>'
                      f'<p class="lede">{esc(about)}</p><div class="lines">{lines}</div>')
    body = f'''  <p class="crumbs"><a href="/">LuxFlash</a> › Phrases</p>
  <h1>{len(phrases)} Luxembourgish phrases, ready to say</h1>
  <p class="lede">Whole sentences rather than words: what you say at a counter, at the doctor,
    when you did not understand, and when you want the other person to keep going in Luxembourgish
    instead of switching to French.</p>
  <ul class="toc">{''.join(nav)}</ul>
  {''.join(blocks)}
  <p><a class="cta" href="/grammar/">Why the words sit in that order →</a></p>'''
    out = ROOT / 'phrases'
    out.mkdir(exist_ok=True)
    (out / 'index.html').write_text(shell(
        f'{len(phrases)} Luxembourgish phrases with English translation',
        f'{len(phrases)} ready-made Luxembourgish sentences with English: greetings, the commune '
        f'counter, the doctor, asking for a repeat, opinions, your day. Free, no sign-up.',
        f'{ORIGIN}/phrases/', body), encoding='utf-8')

    # --- карта сайта: словарь уже там, добавляем два адреса
    sm = ROOT / 'sitemap.xml'
    xml = sm.read_text(encoding='utf-8')
    today = time.strftime('%Y-%m-%d')
    add = ''.join(f'  <url>\n    <loc>{ORIGIN}{u}</loc>\n    <lastmod>{today}</lastmod>\n  </url>\n'
                  for u in ('/grammar/', '/phrases/') if f'<loc>{ORIGIN}{u}</loc>' not in xml)
    if add:
        sm.write_text(xml.replace('</urlset>', add + '</urlset>'), encoding='utf-8')
    print(f'грамматика: {used} правил, из них {len(ru_notes)} с русским пояснением; '
          f'разговорник: {len(phrases)} фраз в {len(blocks)} разделах')


if __name__ == '__main__':
    main()
