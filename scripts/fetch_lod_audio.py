#!/usr/bin/env python3
"""Enable native LOD pronunciation by matching LuxFlash words to LOD entry ids.

The Lëtzebuerger Online Dictionnaire (lod.lu) publishes its full linguistic
dataset as OPEN DATA (CC0) on data.public.lu, and hosts pronunciation audio
openly at:

    https://lod.lu/uploads/OGG/<id>.ogg      (word audio, id = LOD entry id, lowercase)
    https://lod.lu/uploads/AAC/<id>.m4a

This script downloads (or reads locally) the LOD dump, matches each LuxFlash
headword (`lb`) to its LOD entry id — preferring entries whose part of speech
agrees — and writes that id back into data/chunks/*.json as `lodId`. The app
then plays the real native recording from the 🔊 button, falling back to
browser speech for any word without a match.

Typical run (needs network access to data.public.lu / lod.lu):

    python3 scripts/fetch_lod_audio.py --verify
    python3 scripts/build_data.py        # rebuild data/words.js with the new ids

Options:
    --local FILE   use an already-downloaded dump (.xml or .zip) instead of downloading
    --url URL      explicit dump URL (otherwise the newest resource is auto-discovered
                   from the data.public.lu dataset API)
    --verify       HEAD-check every matched audio URL and drop ids without audio
    --force        re-match entries that already have a lodId
"""
import argparse
import io
import json
import os
import re
import sys
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNK_DIR = os.path.join(ROOT, "data", "chunks")

DATASET_API = ("https://data.public.lu/api/1/datasets/"
               "letzebuerger-online-dictionnaire-lod-linguistesch-daten/")
AUDIO_URL = "https://lod.lu/uploads/OGG/{id}.ogg"

# LOD partOfSpeech tag -> LuxFlash pos
LOD_POS = {
    "SUBST": "noun", "VRB": "verb", "ADJ": "adjective", "ADV": "adverb",
    "PRON": "pronoun", "PRONADV": "pronoun", "PREP": "preposition",
    "CONJ": "conjunction", "NB": "numeral", "INTERJ": "interjection",
    "ART": "determiner",
}


def norm(s):
    """Normalise a headword for matching: casefold + squeeze spaces.
    Accents are kept — ä/é/ë distinguish real Luxembourgish words."""
    s = unicodedata.normalize("NFC", str(s))
    return re.sub(r"\s+", " ", s).strip().casefold()


def strip_article(s):
    s = re.sub(r"^d['’]\s*", "", s, flags=re.I)
    s = re.sub(r"^(den|déi|de|eng?)\s+", "", s, flags=re.I)
    return s.strip()


def latest_dump_url():
    print("Discovering newest LOD dump via data.public.lu API …")
    with urllib.request.urlopen(DATASET_API, timeout=60) as r:
        meta = json.load(r)
    resources = [res for res in meta.get("resources", []) if res.get("url")]
    if not resources:
        sys.exit("No resources found in the dataset — pass --url explicitly.")
    # resources are listed newest-first; keep zip/xml ones
    for res in resources:
        if res["url"].lower().endswith((".zip", ".xml", ".tar.gz", ".tgz")):
            return res["url"]
    return resources[0]["url"]


def read_dump(args):
    """Return a file-like object with the LOD XML."""
    if args.local:
        path = args.local
        print(f"Reading local dump {path}")
        if path.lower().endswith(".zip"):
            zf = zipfile.ZipFile(path)
            name = next(n for n in zf.namelist() if n.lower().endswith(".xml"))
            return zf.open(name)
        return open(path, "rb")
    url = args.url or latest_dump_url()
    print(f"Downloading LOD data from {url} …")
    raw = urllib.request.urlopen(url, timeout=600).read()
    if url.lower().endswith(".zip") or raw[:2] == b"PK":
        zf = zipfile.ZipFile(io.BytesIO(raw))
        name = next(n for n in zf.namelist() if n.lower().endswith(".xml"))
        return zf.open(name)
    return io.BytesIO(raw)


def load_lod_index(fh):
    """Stream-parse the LOD XML.
    Returns {norm_lemma: [(entry_id, pos), …]} in document order."""
    index = {}
    n = 0
    for _, el in ET.iterparse(fh, events=("end",)):
        if el.tag.split("}")[-1] != "entry":
            continue
        eid = el.get("id")
        lemma = el.findtext("lemma") or ""
        pos_el = el.find(".//partOfSpeech")
        pos = LOD_POS.get((pos_el.text or "").strip() if pos_el is not None else "", "")
        if eid and lemma.strip():
            index.setdefault(norm(lemma), []).append((str(eid), pos))
            n += 1
        el.clear()
    print(f"LOD entries indexed: {n} ({len(index)} distinct lemmas)")
    return index


def pick_id(candidates, want_pos):
    """Prefer the first entry whose POS agrees; else the first entry at all
    (LOD numbers homographs HAUS1, HAUS2… in relevance order)."""
    if not candidates:
        return None
    for eid, pos in candidates:
        if pos and pos == want_pos:
            return eid
    return candidates[0][0]


def verify_ids(ids):
    """HEAD-check audio for each id; return the set of ids that have audio."""
    ok = set()

    def check(eid):
        url = AUDIO_URL.format(id=eid.lower())
        req = urllib.request.Request(url, method="HEAD")
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                if r.status == 200:
                    ok.add(eid)
        except Exception:
            pass

    print(f"Verifying audio for {len(ids)} matched entries …")
    with ThreadPoolExecutor(max_workers=16) as pool:
        list(pool.map(check, ids))
    print(f"  {len(ok)}/{len(ids)} have a native recording")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", help="explicit LOD dump URL")
    ap.add_argument("--local", help="path to an already-downloaded dump (.zip or .xml)")
    ap.add_argument("--verify", action="store_true",
                    help="HEAD-check every matched audio URL; drop ids without audio")
    ap.add_argument("--force", action="store_true",
                    help="re-match entries that already have a lodId")
    args = ap.parse_args()

    index = load_lod_index(read_dump(args))
    if not index:
        sys.exit("Parsed 0 entries — the dump format may have changed.")

    # pass 1: match every chunk entry
    files = {}
    matches = {}   # filename -> [(entry_dict, lod_id), …]
    for fn in sorted(os.listdir(CHUNK_DIR)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(CHUNK_DIR, fn)
        data = json.load(open(path, encoding="utf-8"))
        files[fn] = (path, data)
        for e in data:
            if e.get("lodId") and not args.force:
                continue
            lb = str(e.get("lb", ""))
            cands = index.get(norm(lb)) or index.get(norm(strip_article(lb)))
            eid = pick_id(cands, str(e.get("pos", "")).lower())
            if eid:
                matches.setdefault(fn, []).append((e, eid))

    all_ids = {eid for pairs in matches.values() for _, eid in pairs}
    good = verify_ids(all_ids) if args.verify else all_ids

    # pass 2: write back
    total = sum(len(d) for _, d in files.values())
    written = 0
    for fn, (path, data) in files.items():
        changed = False
        for e, eid in matches.get(fn, []):
            if eid in good and e.get("lodId") != eid:
                e["lodId"] = eid
                written += 1
                changed = True
        if changed:
            json.dump(data, open(path, "w", encoding="utf-8"),
                      ensure_ascii=False, indent=1)
            print(f"  updated {fn}")

    kept = sum(1 for _, d in files.values() for e in d if e.get("lodId"))
    print(f"Matched {written} words this run; {kept}/{total} entries now carry a lodId.")
    print("Now run:  python3 scripts/build_data.py")


if __name__ == "__main__":
    main()
