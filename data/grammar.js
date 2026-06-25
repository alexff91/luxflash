/* LuxFlash grammar reference — concise, original notes (not copied from any source).
   Verify forms on lod.lu. Rendered by app.js into the Grammar tab. */
window.LUXFLASH_GRAMMAR = [
  {
    id: "pronunciation",
    title: "Sounds & spelling",
    intro: "Luxembourgish uses the Latin alphabet plus é, ä, ë. A few sounds to know:",
    body: [
      { type: "list", items: [
        "<b>ë</b> — a short, neutral 'uh' sound, as in <i>ech</i> (I).",
        "<b>é</b> — a long, closed 'ay', as in <i>schéin</i> (beautiful).",
        "<b>ä</b> — an open 'e', as in <i>spären</i> (to save).",
        "<b>ch</b> — soft as in German <i>ich</i> after light vowels; hard ('kh') after a, o, u.",
        "<b>w</b> — like English 'v'; <b>v</b> — usually 'f'.",
        "<b>é/è</b>, <b>ee</b>, <b>ii</b> are long vowels; doubled = long."
      ]}
    ]
  },
  {
    id: "gender",
    title: "Nouns, gender & the article",
    intro: "Every noun is masculine, feminine or neuter. The definite article ('the') changes with gender and case.",
    body: [
      { type: "table",
        head: ["", "masc.", "fem.", "neut.", "plural"],
        rows: [
          ["the (nom.)", "den / de", "d'", "d'", "d'"],
          ["a / an", "en", "eng", "en", "—"]
        ]
      },
      { type: "p", text: "Nouns are always written with a capital letter, like in German." },
      { type: "ex", lb: "den Hond, d'Kaz, d'Kand", en: "the dog, the cat, the child" },
      { type: "ex", lb: "en Hond, eng Kaz, en Auto", en: "a dog, a cat, a car" },
      { type: "tip", text: "Tip: learn each noun together with its article — LuxFlash shows it on every noun card." }
    ]
  },
  {
    id: "cases",
    title: "Cases: nominative, accusative, dative",
    intro: "Luxembourgish has three cases. The subject is nominative; the direct object is accusative; after many prepositions and for the indirect object you use the dative.",
    body: [
      { type: "table",
        head: ["case", "masc.", "fem.", "neut.", "plural"],
        rows: [
          ["nominative", "den", "d'", "d'", "d'"],
          ["accusative", "den", "d'", "d'", "d'"],
          ["dative", "dem", "der", "dem", "den"]
        ]
      },
      { type: "p", text: "Masculine and neuter look the same in nom./acc.; the dative is where forms really change." },
      { type: "ex", lb: "Ech ginn dem Mann d'Buch.", en: "I give the man the book. (dative: dem Mann)" },
      { type: "ex", lb: "mat der Kaz, no der Schoul", en: "with the cat, after school (dative after prepositions)" }
    ]
  },
  {
    id: "plurals",
    title: "Plurals",
    intro: "There is no single rule, but common patterns help:",
    body: [
      { type: "list", items: [
        "Add <b>-en</b>: <i>d'Saach → d'Saachen</i> (thing → things).",
        "Add <b>-er</b> + umlaut: <i>d'Buch → d'Bicher</i> (book → books).",
        "Add <b>-(e)n</b> to many words ending in a vowel: <i>de Bléi → d'Bléien</i>.",
        "No change (sometimes umlaut): <i>de Fësch → d'Fësch</i> (fish)."
      ]},
      { type: "p", text: "The plural article is always d' (nom./acc.), den (dative)." }
    ]
  },
  {
    id: "pronouns",
    title: "Personal pronouns",
    body: [
      { type: "table",
        head: ["person", "subject", "example"],
        rows: [
          ["I", "ech", "ech sinn"],
          ["you (sg.)", "du", "du bass"],
          ["he / she / it", "hien / si / et", "hien ass"],
          ["we", "mir", "mir sinn"],
          ["you (pl.)", "dir", "dir sidd"],
          ["they", "si", "si sinn"]
        ]
      },
      { type: "tip", text: "Polite 'you' is Dir (capitalised), used like French vous." }
    ]
  },
  {
    id: "present",
    title: "Present tense & the verbs sinn / hunn",
    intro: "Regular verbs take endings on the stem. The two most important irregular verbs are sinn (to be) and hunn (to have).",
    body: [
      { type: "table",
        head: ["", "schwätzen (speak)", "sinn (be)", "hunn (have)"],
        rows: [
          ["ech", "schwätzen", "sinn", "hunn"],
          ["du", "schwätz(s)", "bass", "hues"],
          ["hien/si/et", "schwätzt", "ass", "huet"],
          ["mir", "schwätzen", "sinn", "hunn"],
          ["dir", "schwätzt", "sidd", "hutt"],
          ["si", "schwätzen", "sinn", "hunn"]
        ]
      },
      { type: "ex", lb: "Ech schwätzen e bëssen Lëtzebuergesch.", en: "I speak a little Luxembourgish." }
    ]
  },
  {
    id: "modals",
    title: "Modal verbs",
    intro: "Modals are followed by an infinitive at the end of the clause.",
    body: [
      { type: "list", items: [
        "<b>kënnen</b> — can / to be able",
        "<b>mussen</b> — must / to have to",
        "<b>wëllen</b> — to want",
        "<b>sollen</b> — should / ought to",
        "<b>däerfen</b> — to be allowed to",
        "<b>mögen</b> — to like"
      ]},
      { type: "ex", lb: "Ech kann haut net kommen.", en: "I can't come today." },
      { type: "ex", lb: "Mir mussen elo goen.", en: "We have to go now." }
    ]
  },
  {
    id: "wordorder",
    title: "Word order (verb second)",
    intro: "In a main clause the conjugated verb is the second element. If something other than the subject comes first, the subject moves after the verb.",
    body: [
      { type: "ex", lb: "Ech ginn muer an d'Stad.", en: "I go to town tomorrow." },
      { type: "ex", lb: "Muer ginn ech an d'Stad.", en: "Tomorrow I go to town. (verb still 2nd)" },
      { type: "p", text: "In subordinate clauses (after datt, well, wann…) the verb goes to the end:" },
      { type: "ex", lb: "…well ech midd sinn.", en: "…because I am tired." }
    ]
  },
  {
    id: "perfect",
    title: "Talking about the past (perfect tense)",
    intro: "Everyday past uses hunn or sinn + a past participle (usually ge-…-t). Verbs of movement/change use sinn.",
    body: [
      { type: "ex", lb: "Ech hunn e Kaffi gedronk.", en: "I drank a coffee." },
      { type: "ex", lb: "Mir hu gespillt.", en: "We played." },
      { type: "ex", lb: "Si ass heem gaang.", en: "She went home. (movement → sinn)" }
    ]
  },
  {
    id: "negation",
    title: "Negation: net & keen",
    body: [
      { type: "p", text: "Use net to negate a verb/sentence, and keen/keng to mean 'no/not a' with nouns." },
      { type: "ex", lb: "Ech verstinn dat net.", en: "I don't understand that." },
      { type: "ex", lb: "Ech hunn keng Zäit.", en: "I have no time." }
    ]
  },
  {
    id: "eifeler",
    title: "The Eifeler Regel (the disappearing -n)",
    intro: "A final -n (or -nn) is dropped when the next word begins with a consonant other than n, d, t, z, or h. This is a hallmark of written Luxembourgish.",
    body: [
      { type: "ex", lb: "ech hu(n) gesinn", en: "'hunn' → 'hu' before 'gesinn' (g)" },
      { type: "ex", lb: "wann ech … / wa mer …", en: "'wann' keeps -n before vowel, drops before 'mer'" },
      { type: "tip", text: "Don't worry about mastering this early — comprehension comes first. LOD shows the correct written form." }
    ]
  },
  {
    id: "numbers",
    title: "Numbers 0–20",
    body: [
      { type: "p", text: "null, eent, zwee, dräi, véier, fënnef, sechs, siwen, aacht, néng, zéng," },
      { type: "p", text: "eelef, zwielef, dräizéng, véierzéng, foffzéng, siechzéng, siwwenzéng, uechtzéng, nonzéng, zwanzeg." }
    ]
  },
  {
    id: "questions",
    title: "Questions",
    intro: "Yes/no questions invert subject and verb. Otherwise start with a question word.",
    body: [
      { type: "list", items: [
        "<b>Wien?</b> who · <b>Wat?</b> what · <b>Wou?</b> where",
        "<b>Wéini?</b> when · <b>Firwat?</b> why · <b>Wéi?</b> how · <b>Wéivill?</b> how much"
      ]},
      { type: "ex", lb: "Schwätzt dir Lëtzebuergesch?", en: "Do you speak Luxembourgish?" },
      { type: "ex", lb: "Wou wunnt dir?", en: "Where do you live?" }
    ]
  }
];
