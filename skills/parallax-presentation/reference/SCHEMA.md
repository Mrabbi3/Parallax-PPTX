# `deck.json` schema

```jsonc
{
  "meta":   { "title": "...", "author": "...", "footer": "short footer text" },
  "theme":  { "cream": "FFF7EC", "gold": "FFCB8E", "rose": "FFA9B8",
              "mint": "9FE9D2", "scrim": "0C1A2E", "bg": "12304A",
              "serif": "Cambria", "sans": "Calibri" },
  "slides": [ /* see below */ ]
}
```

Everything in `theme` is optional; those are the defaults. Fonts must be safe
across machines — `Cambria`, `Georgia`, `Calibri`, `Garamond`, `Trebuchet MS`.

## Inline emphasis

Any paragraph, row text, card text or step text may contain `**double
asterisks**`. Those words render bold in the accent colour. Use it once or twice
per slide, not everywhere.

## Near-plane placement

Each slide may set `"fgSlot"` to one of:

| slot | where the cut-out sits |
|---|---|
| `hero-right` | full bleed right, crosses the headline — title slides |
| `hero-right-mid` | large right, slightly lower — closing slides |
| `right` / `left` | half-visible at one edge, mid height |
| `left-mid` | smaller, left, sits beside a text column |
| `peek-right` | a sliver at the right edge |
| `peek-bottom`, `peek-bottom-c`, `peek-bottom-l`, `peek-bottom-m`, `peek-bottom-x` | an arc rising from the bottom edge, in different horizontal positions |

Omit it and a sensible slot is chosen from the slide type. Override with
`"fg": [x, y, width]` in inches if you need something exact. `"fgAsset"` swaps in
a different PNG from the layers folder for that one slide.

## Slide types

### `title`
```json
{ "type": "title", "eyebrow": "...", "title": "Two Lines\nLike This",
  "subtitle": "...", "meta": "NAME    DATE    CONTEXT", "size": 68 }
```

### `quote` — a pull quote plus a numbered scene breakdown
```json
{ "type": "quote", "eyebrow": "01  introduce", "title": "...",
  "quote": "the quoted line", "cite": "source, page",
  "list": [ { "label": "Bold lead", "text": "the rest of the beat" } ],
  "footnote": "italic line under the block" }
```

### `list` — numbered rows on a scrim, text on one side
```json
{ "type": "list", "side": "right", "eyebrow": "...", "title": "...",
  "rows": [ { "label": "...", "text": "..." } ], "footnote": "..." }
```

### `stats` — a strip of big numbers, paragraphs, optional timeline
```json
{ "type": "stats", "eyebrow": "...", "title": "...",
  "stats": [ { "value": "4,300", "label": "models" } ],
  "paragraphs": [ "...", "..." ],
  "timeline": [ { "year": "1886", "text": "...", "accent": true } ] }
```

### `steps` — a numbered process, one row each
```json
{ "type": "steps", "eyebrow": "...", "title": "...", "intro": "...",
  "steps": [ { "label": "Short name", "text": "...", "accent": false } ] }
```

### `compare` — two panels side by side
```json
{ "type": "compare", "eyebrow": "...", "title": "...",
  "left":  { "label": "WHAT X SAYS", "paras": ["lead", "follow-up"] },
  "right": { "label": "WHAT Y SAYS", "paras": ["lead", "follow-up"] },
  "footnote": "full-width line underneath" }
```

### `split` — argument on the left, evidence rows on the right
```json
{ "type": "split", "eyebrow": "...", "title": "...",
  "paragraphs": ["..."], "pull": "italic pull quote",
  "rows": [ { "label": "...", "text": "..." } ] }
```

### `feature` — image-led slide, text right, optional highlighted panel
```json
{ "type": "feature", "eyebrow": "...", "title": "...", "accent": "rose",
  "paragraphs": ["..."],
  "panel": { "label": "AND THE TWIST", "bullets": ["...", "..."] },
  "after": ["closing paragraph"], "pull": "last italic line" }
```
Pair this with `"fgAsset"` when you have a second cut-out for the subject.

### `cards` — three parallel points
```json
{ "type": "cards", "eyebrow": "...", "title": "...",
  "cards": [ { "title": "...", "text": "..." } ], "footnote": "..." }
```

### `video` — embedded online player
```json
{ "type": "video", "eyebrow": "...", "title": "...",
  "link": "https://www.youtube.com/embed/ID",
  "paragraphs": ["..."], "note": "italic timing note",
  "url": "youtube.com/watch?v=ID" }
```

### `closing`
```json
{ "type": "closing", "eyebrow": "10  takeaway", "title": "Three\nShort\nLines",
  "paragraphs": ["...", "..."] }
```

### `references`
```json
{ "type": "references", "title": "Sources",
  "items": [ { "cite": "Author, Title.", "source": "domain.com/path",
               "plain": false } ] }
```
`plain: true` renders the second line in body colour instead of link colour —
use it for publisher details and for the artwork credit.

## Notes

Any slide accepts `"notes": "..."`, which becomes the PowerPoint speaker note.
Write them as delivery instructions, not a repeat of the slide.
