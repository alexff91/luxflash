#!/usr/bin/env python3
"""Enable native LOD pronunciation by matching LuxFlash words to LOD entry ids.

The Lëtzebuerger Online Dictionnaire (lod.lu) publishes its data as OPEN DATA
(CC0) on data.public.lu, and hosts pronunciation audio openly at:

    https://lod.lu/uploads/OGG/<id>.ogg      (word audio, id = LOD entry id)
    https://lod.lu/uploads/AAC/<id>.m4a

This script downloads the LOD word list, matches each LuxFlash headword (`lb`)
to its LOD entry id, and writes that id back into the dataset as `lodId`. The app
then plays the real recording from the 🔊 button (falling back to browser speech
for any word without a match).

Run it in an environment that can reach data.public.lu / lod.lu
(a normal machine or CI — the hosted dev sandbox may block those hosts):

    python3 scripts/fetch_lod_audio.py
    python3 scripts/build_data.py        # rebuild data/words.js with the new ids

Notes
-----
* The LOD open-data download URL occasionally changes. Find the current link on
  https://data.public.lu/en/datasets/letzebuerger-online-dictionnaire-lod-linguistesch-daten/
  and pass it with --url, or set LOD_DATA_URL.
* Matching is case-insensitive on the lemma. Where LOD has several entries for a
  spelling (homographs), the first is used; verify nuance on lod.lu.
"""
import argparse
import io
import json
import os
import re
import sys
import tarfile
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNK_DIR = os.path.join(ROOT, "data", "chunks")
DEFAULT_URL = os.environ.get(
    "LOD_DATA_URL",
    # Linguistic data export (XML inside a tar/zip). Update if the portal changes it.
    "https://lod.lu/lod-data.tar.gz",
)


def norm(s):
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def load_lod_index(url):
    """Return {normalised_lemma: entry_id} parsed from the LOD data archive."""
    print(f"Downloading LOD data from {url} …")
    raw = urllib.request.urlopen(url, timeout=120).read()
    index = {}

    def feed_xml(data):
        # Each LOD <ITEM>/<entry> has an id attribute and a lemma/headword element.
        try:
            root = ET.fromstring(data)
        except ET.ParseError:
            return
        for el in root.iter():
            tag = el.tag.split("}")[-1].lower()
            if tag not in ("item", "entry", "article"):
                continue
            eid = el.get("id") or el.get("ID")
            if not eid:
                continue
            lemma = None
            for child in el.iter():
                ctag = child.tag.split("}")[-1].lower()
                if ctag in ("lemma", "headword", "wuert", "word", "form") and (child.text or "").strip():
                    lemma = child.text.strip()
                    break
            if lemma:
                index.setdefault(norm(lemma), str(eid))

    if url.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
            for m in tar.getmembers():
                if m.name.lower().endswith(".xml"):
                    feed_xml(tar.extractfile(m).read())
    elif url.endswith(".xml"):
        feed_xml(raw)
    else:
        # try as XML, then give up with a helpful message
        feed_xml(raw)

    if not index:
        print("WARNING: parsed 0 entries. The archive format may have changed — "
              "inspect it and adjust load_lod_index().", file=sys.stderr)
    return index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL, help="LOD open-data archive URL")
    args = ap.parse_args()

    index = load_lod_index(args.url)
    print(f"LOD entries indexed: {len(index)}")

    matched = total = 0
    for fn in sorted(os.listdir(CHUNK_DIR)):
        if not fn.endswith(".json"):
            continue
        path = os.path.join(CHUNK_DIR, fn)
        data = json.load(open(path, encoding="utf-8"))
        changed = False
        for e in data:
            total += 1
            if e.get("lodId"):
                matched += 1
                continue
            eid = index.get(norm(e.get("lb", "")))
            if eid:
                e["lodId"] = eid
                matched += 1
                changed = True
        if changed:
            json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            print(f"  updated {fn}")

    print(f"Matched {matched}/{total} words to LOD audio ids.")
    print("Now run:  python3 scripts/build_data.py")


if __name__ == "__main__":
    main()
