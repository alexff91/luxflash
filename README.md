<div align="center">

# 🇱🇺 LuxFlash

### Learn Luxembourgish (Lëtzebuergesch) with flashcards — free, open-source, in your browser.

**[▶ Open the app](https://alexff91.github.io/luxflash/)**

</div>

LuxFlash is a no-account, no-tracking flashcard web app for learning the most
common Luxembourgish words. It runs entirely in your browser: **2000+ words**
across CEFR levels **A1 → B2**, each with an **example sentence**, German &
French glosses, and a **direct link to the official [Lëtzebuerger Online
Dictionnaire (lod.lu)](https://lod.lu)** for audio, gender and full declensions.

Your progress is saved locally (browser `localStorage`) and you can **download
or upload a JSON backup** to move between devices.

---

## ✨ Features

- **Spaced repetition** — a lightweight Leitner system schedules each card so you
  review words right before you'd forget them (`Again / Hard / Good / Easy`).
- **Levels** — filter your study deck by A1, A2, B1, B2 (mix and match).
- **2000+ curated words** — organised by theme (family, food, work, travel,
  nature, verbs, grammar words, adjectives…), each with a natural example
  sentence and its translation.
- **Reverse mode** — practise English → Luxembourgish recall.
- **Browse & search** — scan the whole dictionary, filter by level/category.
- **Grammar tab** — concise, practical notes (gender & articles, cases, plurals,
  verb tenses, word order, the Eifeler Regel, numbers, questions…).
- **Resources tab** — curated links to keep learning (Luxembourgish with Anne,
  LOD, RTL, ZLS and more). LuxFlash links to these, it doesn't reproduce them.
- **Native pronunciation** — plays the real LOD recording when a word has a
  `lodId` (open CC0 audio from lod.lu), falling back to the browser speech engine.
- **lod.lu integration** — every card and list entry deep-links to LOD so you can
  verify spelling, hear the pronunciation and see the full grammar.
- **Progress dashboard** — words learned, due today, day-streak, per-level bars,
  Leitner mastery chart.
- **100% local & private** — nothing is uploaded. Export/import a JSON backup any
  time.
- **Pronunciation** — uses the browser's speech engine (best-effort) to read
  words aloud.
- **Dark mode**, fully responsive, keyboard shortcuts, no build step, no
  dependencies.

## ⌨️ Keyboard shortcuts

| Key | Action |
| --- | --- |
| `Space` | Flip card |
| `1` `2` `3` `4` | Grade: Again / Hard / Good / Easy |

## 🚀 Run it locally

It's a fully static site — just open it.

```bash
git clone https://github.com/alexff91/luxflash.git
cd luxflash
# either open index.html directly, or serve it:
python3 -m http.server 8000   # then visit http://localhost:8000
```

## 🌐 Deploy on GitHub Pages

This repo ships a GitHub Actions workflow (`.github/workflows/pages.yml`).

1. Push to your `main` branch.
2. In the repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. The site publishes to `https://<user>.github.io/luxflash/`.

(You can also just set **Source: Deploy from a branch → main → / (root)**.)

## 🗂️ Project structure

```
index.html              app shell
assets/css/styles.css   styling (light/dark)
assets/js/storage.js    localStorage + JSON import/export
assets/js/srs.js        Leitner spaced-repetition logic
assets/js/app.js        UI controller
data/words.js           the dataset (generated) → window.LUXFLASH_WORDS
data/words.json         same data as plain JSON
data/chunks/*.json      themed source batches
scripts/build_data.py   merges + de-dupes chunks into data/words.*
```

## 🧱 Editing / extending the vocabulary

Each entry looks like:

```json
{
  "lb": "Haus", "en": "house", "de": "Haus", "fr": "maison",
  "pos": "noun", "gender": "n", "level": "A1", "category": "home",
  "ex_lb": "D'Haus ass grouss.", "ex_en": "The house is big."
}
```

Add or fix entries in any `data/chunks/chunkN.json`, then rebuild:

```bash
python3 scripts/build_data.py
```

This regenerates `data/words.js` / `data/words.json` (validated, de-duplicated,
sorted by level). Commit the regenerated files.

## 🔊 Native LOD audio

LOD publishes pronunciation audio openly (CC0) at
`https://lod.lu/uploads/OGG/<id>.ogg` and `…/AAC/<id>.m4a`, where `<id>` is the
LOD entry id. To wire real recordings to LuxFlash words, run (on a machine that
can reach `lod.lu` / `data.public.lu`):

```bash
python3 scripts/fetch_lod_audio.py    # adds "lodId" to data/chunks/*.json
python3 scripts/build_data.py         # rebuild data/words.js
```

The 🔊 button then plays the native recording, and falls back to the browser's
speech engine for any word without a match. The per-word **LOD ↗** link always
opens the official entry with audio regardless.

## 🙏 Vocabulary accuracy & lod.lu

The vocabulary is community-maintained and was seeded automatically. It is a
**learning aid, not an authority** — for definitive spelling, grammatical
gender, plurals, pronunciation and declensions, always consult the official
**[Lëtzebuerger Online Dictionnaire — lod.lu](https://lod.lu)**, which every card
links to directly. Spotted a mistake? Please
[open an issue or pull request](https://github.com/alexff91/luxflash/issues) —
corrections are very welcome. 🐛

## 📄 License

[MIT](LICENSE). LuxFlash is not affiliated with or endorsed by lod.lu / the
Luxembourgish government; it only links to their public dictionary.
