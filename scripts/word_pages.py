"""Словарь по темам: люксембургские слова, напечатанные, а не за кнопкой.

Зачем. «How do you say hello in Luxembourgish», «luxembourgish words food»,
«Sproochentest vocabulary A1» — так ищут. Карточки отвечают на это только
после того, как их начнут листать; в HTML не было ни одного слова, и
поисковику сайт казался страницей про карточки вообще.

Здесь 2 404 слова напечатаны: по темам, где их хотя бы пятнадцать, и по
четырём уровням. У каждого — перевод на английский, немецкий и французский,
род, часть речи и живой пример с переводом. Источник тот же data/words.json,
который грузит приложение.

    python3 scripts/word_pages.py        # words/**/index.html + sitemap.xml
"""
import html
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'words'
ORIGIN = 'https://luxflash.alftech.space'
MIN_WORDS = 15          # меньше — страница ни о чём

LEVELS = {'A1': 'the first words: greetings, numbers, family, everyday things',
          'A2': 'enough to get through a shop, a doctor’s appointment and small talk',
          'B1': 'work, administration, opinions — the level the Sproochentest expects',
          'B2': 'abstract and formal language: law, economy, science, politics'}

# Английские названия тем: в данных они кодами, человеку нужен заголовок.
NAMES = {
    'verb': 'Verbs', 'separable-verb': 'Separable verbs', 'adverb': 'Adverbs',
    'abstract': 'Abstract words', 'work': 'Work', 'health': 'Health', 'home': 'Home',
    'food': 'Food', 'transport': 'Transport', 'school': 'School', 'admin': 'Administration',
    'nature': 'Nature', 'directions': 'Directions', 'body': 'The body',
    'profession': 'Professions', 'number': 'Numbers', 'kitchen': 'The kitchen',
    'family': 'Family', 'sport': 'Sport', 'actions': 'Everyday actions',
    'emotions': 'Emotions', 'greetings': 'Greetings and politeness', 'people': 'People',
    'pronoun': 'Pronouns', 'household': 'Household', 'geography': 'Geography',
    'relationships': 'Relationships', 'tools': 'Tools', 'animals': 'Animals',
    'tech': 'Technology', 'ages': 'Age and stages of life', 'society': 'Society',
    'shopping': 'Shopping', 'phrase': 'Useful phrases', 'routine': 'Daily routine',
    'cooking': 'Cooking', 'luxembourg': 'Luxembourg itself', 'restaurant': 'At the restaurant',
    'reflexive': 'Reflexive verbs', 'law': 'Law', 'academic': 'Academic words',
    'calendar': 'The calendar', 'time': 'Time', 'adjective': 'Adjectives', 'money': 'Money',
    'holidays': 'Holidays', 'economy': 'Economy', 'plants': 'Plants', 'appearance': 'Appearance',
    'garden': 'The garden', 'material': 'Materials', 'furniture': 'Furniture',
    'clothes': 'Clothes', 'office': 'The office', 'fruit': 'Fruit', 'city': 'The city',
    'buildings': 'Buildings', 'medicine': 'Medicine', 'meal': 'Meals', 'quantity': 'Quantity',
    'travel': 'Travel', 'weather': 'Weather', 'politics': 'Politics', 'philosophy': 'Philosophy',
    'colors': 'Colours', 'vegetable': 'Vegetables', 'tourism': 'Tourism', 'media': 'Media',
    'cleaning': 'Cleaning', 'trait': 'Character traits',
}
GENDER = {'m': 'de', 'f': 'd’', 'n': 'd’', 'pl': 'd’'}

esc = lambda s: html.escape(str(s or ''), quote=True)
slugify = lambda s: re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def shell(title, description, canonical, body):
    ld = {'@context': 'https://schema.org', '@type': 'WebPage', 'name': title,
          'description': description, 'url': canonical, 'inLanguage': 'en',
          'about': {'@type': 'Language', 'name': 'Luxembourgish', 'alternateName': 'lb'},
          'isPartOf': {'@type': 'WebSite', 'name': 'LuxFlash', 'url': ORIGIN}}
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
  h2 {{ font-size:19px; margin:26px 0 10px; }}
  .lede {{ color:var(--soft); margin:0 0 20px; max-width:64ch; }}
  .words {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    overflow:hidden; margin:0 0 18px; }}
  .w {{ display:grid; grid-template-columns:1fr 1fr; gap:2px 16px; padding:13px 16px;
    border-bottom:1px solid var(--line); }}
  .w:last-child {{ border-bottom:0; }}
  .lb {{ font-weight:700; font-size:18px; }}
  .lb small {{ font-weight:400; color:var(--soft); font-size:13px; margin-left:6px; }}
  .en {{ text-align:right; }}
  .other {{ grid-column:1/-1; color:var(--soft); font-size:14px; }}
  .ex {{ grid-column:1/-1; font-size:14.5px; color:var(--soft); margin-top:4px;
    padding-left:11px; border-left:2px solid var(--accent-soft); }}
  .ex b {{ color:var(--ink); font-weight:600; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(190px,1fr)); gap:9px;
    margin:0 0 18px; }}
  .cards a {{ background:var(--card); border:1px solid var(--line); border-radius:11px;
    padding:12px 14px; text-decoration:none; color:var(--ink); }}
  .cards a:hover {{ border-color:var(--accent); }}
  .cards b {{ display:block; font-size:15.5px; }}
  .cards span {{ color:var(--soft); font-size:13.5px; }}
  .cta {{ display:inline-flex; align-items:center; min-height:48px; padding:0 20px;
    border-radius:10px; background:var(--accent); color:#fff; font-weight:600;
    text-decoration:none; margin:6px 0; }}
  footer {{ margin-top:30px; padding-top:16px; border-top:1px solid var(--line);
    color:var(--soft); font-size:13.5px; }}
  @media (max-width:520px) {{ .w {{ grid-template-columns:1fr; }} .en {{ text-align:left; }} }}
</style>
</head>
<body>
<div class="wrap">
{body}
  <footer>
    <p>Words come from the flashcard deck this site drills you on, checked against the
      <a href="https://lod.lu/" rel="noopener">Lëtzebuerger Online Dictionnaire</a>. The gender
      article is given as Luxembourgish uses it.</p>
    <p><a href="{ORIGIN}/">Drill these as flashcards</a> ·
      <a href="https://vivre.alftech.space/">citizenship test practice</a> ·
      <a href="https://alftech.space/">more free tools</a></p>
  </footer>
</div>
</body>
</html>
'''


# В данных артикль у части существительных уже внутри слова («d'Botter»),
# у части нет. Свой добавляем только там, где его нет: иначе выходило
# «d' d'Botter».
HAS_ARTICLE = re.compile(r"^(d['’]|de[nr]?\s|déi\s|dat\s|di\s)", re.I)


def word_html(w):
    article = GENDER.get(w.get('gender', ''), '') if w.get('pos') == 'noun' else ''
    # После апострофа пробела нет: d'Aen, но de Bauch.
    joiner = '' if article.endswith('’') else ' '
    lb = w['lb'] if (not article or HAS_ARTICLE.match(w['lb'])) else f"{article}{joiner}{w['lb']}"
    lb = lb.strip()
    bits = [b for b in (w.get('pos'), w.get('level')) if b]
    other = ' · '.join(f'{lang} {esc(w[k])}' for lang, k in (('DE', 'de'), ('FR', 'fr')) if w.get(k))
    ex = ''
    if w.get('ex_lb'):
        ex = f'<div class="ex"><b>{esc(w["ex_lb"])}</b>{" — " + esc(w["ex_en"]) if w.get("ex_en") else ""}</div>'
    other_html = f'<div class="other">{other}</div>' if other else ''
    return (f'<div class="w"><div class="lb">{esc(lb)}<small>{esc(", ".join(bits))}</small></div>'
            f'<div class="en">{esc(w.get("en"))}</div>{other_html}{ex}</div>')


def main():
    words = json.loads((ROOT / 'data' / 'words.json').read_text(encoding='utf-8'))
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.rglob('*.html'):
        f.unlink()

    by_cat = defaultdict(list)
    by_level = defaultdict(list)
    for w in words:
        by_cat[w['category']].append(w)
        by_level[w['level']].append(w)

    topics = sorted(((c, ws) for c, ws in by_cat.items() if len(ws) >= MIN_WORDS),
                    key=lambda x: -len(x[1]))
    urls = []

    def write(path, title, description, body):
        file = OUT / path / 'index.html' if path else OUT / 'index.html'
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(shell(title, description, f'{ORIGIN}/words/{path}' if path else f'{ORIGIN}/words/', body),
                        encoding='utf-8')
        urls.append(f'/words/{path}' if path else '/words/')

    topic_cards = ''.join(
        f'<a href="/words/{slugify(c)}"><b>{esc(NAMES.get(c, c.title()))}</b>'
        f'<span>{len(ws)} words</span></a>' for c, ws in topics)
    level_cards = ''.join(
        f'<a href="/words/level-{lv.lower()}"><b>{lv}</b><span>{len(by_level[lv])} words</span></a>'
        for lv in sorted(by_level) if by_level[lv])

    for code, ws in topics:
        name = NAMES.get(code, code.title())
        ws = sorted(ws, key=lambda w: (w['level'], w['lb'].lower()))
        sample = ', '.join(f'{w["lb"]} ({w["en"]})' for w in ws[:3])
        title = f'{name} in Luxembourgish — {len(ws)} words with English, German and French'
        description = (f'{len(ws)} Luxembourgish words for {name.lower()}, each with its English, '
                       f'German and French translation and an example sentence: {sample}. Free, no sign-up.')
        body = f'''  <p class="crumbs"><a href="/">LuxFlash</a> ›
    <a href="/words/">Vocabulary</a> › {esc(name)}</p>
  <h1>{esc(name)} in Luxembourgish</h1>
  <p class="lede">{len(ws)} words, sorted by level. Each shows the English, German and French
    translation and a sentence you might actually hear. Nouns carry their article.</p>
  <div class="words">{''.join(word_html(w) for w in ws)}</div>
  <p><a class="cta" href="/">Drill these as flashcards →</a></p>
  <h2>Other topics</h2>
  <div class="cards">{''.join(
        f'<a href="/words/{slugify(c2)}"><b>{esc(NAMES.get(c2, c2.title()))}</b>'
        f'<span>{len(ws2)} words</span></a>' for c2, ws2 in topics if c2 != code)}</div>'''
        write(slugify(code), title, description, body)

    for level, blurb in LEVELS.items():
        ws = sorted(by_level.get(level, []), key=lambda w: (w['category'], w['lb'].lower()))
        if not ws:
            continue
        title = f'Luxembourgish {level} vocabulary — {len(ws)} words with translations'
        description = (f'The {len(ws)} Luxembourgish words at {level}: {blurb}. '
                       f'English, German and French translations, with examples. Free, no sign-up.')
        body = f'''  <p class="crumbs"><a href="/">LuxFlash</a> ›
    <a href="/words/">Vocabulary</a> › Level {esc(level)}</p>
  <h1>Luxembourgish {esc(level)} vocabulary</h1>
  <p class="lede">{esc(blurb.capitalize())}. {len(ws)} words, grouped by topic.</p>
  <div class="words">{''.join(word_html(w) for w in ws)}</div>
  <p><a class="cta" href="/">Drill these as flashcards →</a></p>
  <h2>By topic</h2>
  <div class="cards">{topic_cards}</div>'''
        write(f'level-{level.lower()}', title, description, body)

    body = f'''  <p class="crumbs"><a href="/">LuxFlash</a> › Vocabulary</p>
  <h1>Luxembourgish vocabulary, {len(words)} words by topic</h1>
  <p class="lede">Every word in the deck, printed with its English, German and French
    translation and an example sentence. {len(topics)} topics and four levels — from the
    first greetings to the language the Sproochentest expects.</p>
  <h2>By level</h2>
  <div class="cards">{level_cards}</div>
  <h2>By topic</h2>
  <div class="cards">{topic_cards}</div>
  <p><a class="cta" href="/">Drill them as flashcards →</a></p>'''
    write('', f'Luxembourgish vocabulary — {len(words)} words with English, German and French',
          f'Every one of the {len(words)} Luxembourgish words in the LuxFlash deck, printed by topic '
          f'and level with English, German and French translations and example sentences. Free.', body)

    today = time.strftime('%Y-%m-%d')
    entries = ''.join(
        f'  <url>\n    <loc>{ORIGIN}{u}</loc>\n    <lastmod>{today}</lastmod>\n  </url>\n'
        for u in ['/'] + sorted(set(urls)))
    (ROOT / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + entries + '</urlset>\n',
        encoding='utf-8')
    print(f'страниц: {len(urls)} ({len(topics)} тем, {len(LEVELS)} уровня, оглавление), слов {len(words)}')


if __name__ == '__main__':
    main()
