"""Replace generated example sentences with LOD's own, and fix homonym links.

The examples in data/chunks were written by a model and a quarter of them were
wrong Luxembourgish ("Mäi A deet wéi" for "Mäin A", "Hir Aen sinn blo"). LOD
has edited examples for almost every entry, so:

1. relink each word to the LOD homonym whose English/German matches its own
   (WAND1 is the wind, the wall is WAND2) — the recording follows the link;
2. take LOD's shortest example that has an English translation
   (lux-teacher/data/en-examples.json), preferring one that contains the word;
3. a word with no such example keeps its old sentence only if it passes
   lux-teacher's check_lb (every form known to LOD, n-rule); otherwise it
   shows no example rather than a wrong one.

Before that, data/headword-fixes.json replaces headwords that are not
Luxembourgish at all — German forms and misspellings ("de Gürtel" for Rimm,
"Grouselteren", "Geduld" for Gedold) — with the LOD word for the same meaning,
or drops the card. 335 such words, reviewed by hand on 25 Oct 2026 against
LOD's English search (lux-teacher/data/lf-headwords.txt has the choices).

Last, the gender: LOD's label ("SUBST+M", "SUBST+MF") is in data/lod-genders.json
(fetched 25 Oct 2026). Where the site's gender is not one LOD allows and the
entry's meaning matches the card, the gender and the article in front of the
word follow LOD (d'Telefon → den Telefon, de Messer → d'Messer).

Run: python3 scripts/fix_examples.py  then build_data.py and word_pages.py.
"""
import glob, json, os, re, sys

LT = os.path.expanduser('~/Claude/lux-teacher')
sys.path.insert(0, os.path.join(LT, 'tools'))
from check_lb import check  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
E = {k: v for k, v in json.load(open(os.path.join(LT, 'data', 'lod-entries.json'))).items() if v}
EN = json.load(open(os.path.join(LT, 'data', 'en-examples.json')))

STOP = {'to', 'the', 'a', 'an', 'of', 'be', 'something', 'someone', 'sth', 'sb', 'etwas', 'jemand', 'jemanden',
        'sich', 'der', 'die', 'das', 'ein', 'eine', 'zu', 'in', 'on', 'at', 'for', 'and', 'or', 'with', 'oneself'}


def toks(*ss):
    out = set()
    for s in ss:
        for t in re.findall(r"[a-zA-ZäöüßÄÖÜéèàç]+", (s or '').lower()):
            if t not in STOP and len(t) > 2:
                out.add(t[:5])
    return out


def score(w, e):
    wen = re.sub(r'\(.*?\)', '', (w.get('en') or '').lower()).strip()
    parts = [p.strip() for p in re.split(r'[,/;]', wen)]
    if any(x.lower().strip() in parts for x in e.get('en', []) if x.strip()):
        return 5
    return len(toks(w.get('en'), w.get('de')) & toks(*e.get('en', []), *e.get('de', [])))


def pick(w, e):
    cands = [x['lb'] for x in e['examples'] if x['lb'] in EN]
    if not cands:
        return None
    head = re.sub(r"^(d'|den |de |déi )", '', w['lb'], flags=re.I).lower()[:4]
    return min(cands, key=lambda s: (head not in s.lower(), len(s)))


GEN = json.load(open(os.path.join(ROOT, 'data', 'lod-genders.json')))


def article(g, word):
    if g == 'm':
        return 'den ' if word[:1].lower() in 'aeiouäëéèhdtzn' else 'de '
    return "d'"


def fix_gender(w):
    lab = GEN.get(w.get('lodId') or '')
    if w.get('pos') != 'noun' or not lab or w['lodId'] not in E or score(w, E[w['lodId']]) == 0:
        return False
    allowed = [{'M': 'm', 'F': 'f', 'N': 'n'}[c] for c in lab.split('+')[1] if c in 'MFN']
    if not allowed or w.get('gender') in allowed:
        return False
    w['gender'] = allowed[0]
    m = re.match(r"^(d'|den |de )(.+)$", w['lb'])
    if m:
        w['lb'] = article(w['gender'], m.group(2)) + m.group(2)
    return True


FIX = {(r['old'], r['en']): r for r in json.load(open(os.path.join(ROOT, 'data', 'headword-fixes.json')))}

stats = dict(gender=0, relinked=0, lod=0, kept=0, dropped=0, renamed=0, removed=0)
dropped = []
for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'chunks', '*.json'))):
    words, keep = json.load(open(f)), []
    for w in words:
        r = FIX.get((w['lb'], w['en']))
        if r and r.get('drop'):
            stats['removed'] += 1
            continue
        keep.append(w)
        if r:
            w.update(lb=r['lb'], lodId=r['lodId'], ex_lb=r['ex_lb'], ex_en=r['ex_en'])
            if r['gender']:
                w['gender'] = r['gender']
            stats['renamed'] += 1
            continue
        ex = None
        lid = w.get('lodId')
        if lid and lid in E:
            base = lid.rstrip('0123456789')
            sibs = [k for k in (base + str(i) for i in range(1, 6)) if k in E]
            best = max(sibs, key=lambda k: (score(w, E[k]), k == lid))
            if score(w, E[best]) > 0 and best != lid:
                w['lodId'] = lid = best
                stats['relinked'] += 1
            ex = pick(w, E[lid])
            stats['gender'] += fix_gender(w)
        if ex:
            w['ex_lb'], w['ex_en'] = ex, EN[ex]
            stats['lod'] += 1
        elif w.get('ex_lb') in EN or (w.get('ex_lb') and not check(w['ex_lb'])):
            stats['kept'] += 1
        elif w.get('ex_lb'):
            dropped.append((w['lb'], w['ex_lb']))
            w['ex_lb'] = w['ex_en'] = ''
            stats['dropped'] += 1
    json.dump(keep, open(f, 'w'), ensure_ascii=False, indent=1)

print(stats)
for d in dropped:
    print('  no example now:', d)
