"""Cards linked to the wrong LOD word, and the same word twice.

An audit on 28 Oct 2026 found the very first A1 card, "a" (and), playing the
recording of "A" (eye) with an example about a fly in someone's eye: the
link had been made by spelling, and LOD's ids are case-blind (A1 is the eye).
The same happened to "Nei" (envy) on NEI1 "nei" (new), "de Moies" on the
adverb "moies", "d'Nuddelen" on the verb "nuddelen". And 88 LOD entries were
on two cards: "d'Famill" and "Famill", "d'Glas" and "de Glas" (one of them
with the wrong gender).

1. A link whose LOD part of speech cannot be the card's (a noun on a verb,
   a conjunction on a noun) is looked up again in LOD's own search by the
   word without its article - and, for a word ending in a vowel, its n-rule
   form ("a" is "an" before a consonant). A match with the right part of
   speech replaces the link; the example from the old entry goes, because it
   was about the other word. No match: the link and the example go, and the
   card plays the browser's voice rather than a wrong recording.
2. Cards on the same LOD entry with the same part of speech are one word -
   merged in build_data.py, which assembles the deck from the chunks.

Run after fix_examples.py (which relinks by meaning and would undo this):
    python3 scripts/fix_examples.py && python3 scripts/fix_links_pos.py && python3 scripts/build_data.py
Writes data/chunks/*.json in place and prints what it changed.
"""
import glob, json, os, re, ssl, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LT = os.path.expanduser('~/Claude/lux-teacher')
E = {k: v for k, v in json.load(open(os.path.join(LT, 'data', 'lod-entries.json'))).items() if v}
GEN = json.load(open(os.path.join(ROOT, 'data', 'lod-genders.json')))
try:
    import certifi; CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()

OK = {  # card part of speech -> LOD labels it may sit on
    'noun': ('SUBST', 'NP'), 'verb': ('VRB',), 'adjective': ('ADJ',), 'adverb': ('ADV', 'ADJ', 'PART'),
    'conjunction': ('CONJ',), 'preposition': ('PREP',), 'pronoun': ('PRON', 'ART'), 'determiner': ('ART', 'PRON'),
    'numeral': ('NB', 'NUM'), 'interjection': ('INTERJ', 'PART'),
}
CACHE = os.path.join(ROOT, 'data', 'lod-search-cache.json')
cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}


def fits(card_pos, lod_pos):
    return any((lod_pos or '').startswith(p) for p in OK.get(card_pos, ()))


def search(q):
    if q in cache: return cache[q]
    u = 'https://lod.lu/api/lb/search?' + urllib.parse.urlencode({'query': q, 'lang': 'lb'})
    req = urllib.request.Request(u, headers={'User-Agent': 'luxflash (free study site)'})
    for attempt in range(3):
        try:
            res = json.load(urllib.request.urlopen(req, timeout=30, context=CTX)).get('results', [])
            cache[q] = [{'id': r['article_id'], 'lb': r['word_lb'], 'pos': r['pos']} for r in res]
            time.sleep(0.2)
            return cache[q]
        except Exception as e:
            err = e; time.sleep(2 + attempt * 3)
    print('search failed', q, err, file=sys.stderr)
    return []


def bare(lb):
    return re.sub(r"^(d'|den |de |déi )", '', lb, flags=re.I).strip()


def article_ok(w):
    g = GEN.get(w.get('lodId') or '')
    if not g or w['pos'] != 'noun': return False
    lb = w['lb']
    art = 'f/n' if lb.startswith("d'") else 'm' if re.match(r'^(de|den) ', lb) else ''
    return bool(art) and any(x in g for x in (['F', 'N'] if art == 'f/n' else ['M']))


changes = {'relinked': [], 'unlinked': []}
files = sorted(glob.glob(os.path.join(ROOT, 'data', 'chunks', '*.json')))
decks = {f: json.load(open(f)) for f in files}

# 1. part of speech
for f, words in decks.items():
    for w in words:
        lid = w.get('lodId')
        if not lid: continue
        e = E.get(lid)
        lodpos = e['pos'] if e else None
        if e is None or fits(w['pos'], lodpos): continue
        lemma = bare(w['lb'])
        tries = [lemma] + ([lemma + 'n'] if re.search(r'[aeiouäëéi]$', lemma, re.I) else [])
        found = None
        for q in tries:
            for r in search(q):
                if r['lb'].lower() == q.lower() and fits(w['pos'], r['pos']):
                    found = r; break
            if found: break
        if found:
            changes['relinked'].append((w['lb'], w['pos'], lid, found['id'], found['pos']))
            w['lodId'] = found['id']
        else:
            changes['unlinked'].append((w['lb'], w['pos'], lid, lodpos))
            w.pop('lodId', None)
        # the old example belonged to the other word
        w['ex_lb'] = w['ex_en'] = ''

# 2. (duplicates) is done where the deck is assembled, in build_data.py.

for f, words in decks.items():
    json.dump(words, open(f, 'w'), ensure_ascii=False, indent=1)
json.dump(cache, open(CACHE, 'w'), ensure_ascii=False, indent=0, sort_keys=True)
for k, v in changes.items():
    print(f'{k}: {len(v)}')
    for x in v: print('   ', x)
