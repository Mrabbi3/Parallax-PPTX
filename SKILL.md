---
name: parallax-presentation
description: Build a cinematic parallax .pptx — a three-plane deck (panorama background, translucent midground, shaded cut-out foreground) wired together with PowerPoint Morph so the camera appears to fly through depth as slides advance. Use this whenever someone asks for a parallax presentation, a scroll/depth/cinematic deck, a "presentation like that video", or asks for a slide deck and supplies a reference image, photo, or colour palette to build it around. Also use it when a plain deck needs to look like a piece of design rather than a template. Do NOT use it for a quick internal status deck, a deck that must match a corporate template, or when the person explicitly wants Google Slides or Keynote as the native format.
---

# Parallax Presentation

Builds a `.pptx` in which every slide is the **same three moving planes**, shot
from a different camera position. PowerPoint's Morph transition interpolates
between those positions; because the three planes travel at three different
rates, the eye reads depth. The headline sits *between* the planes, so the
foreground subject crosses in front of the type.

```
  ┌─────────────────────────────────────────┐
  │  !!fg    shaded cut-out   moves most  ◄─┼── in FRONT of the text
  │  ─────────────────────────────────────  │
  │  TEXT    headline + body                │
  │  ─────────────────────────────────────  │
  │  !!mid   translucent shapes   faster    │
  │  !!bg    colour panorama      slowest   │
  └─────────────────────────────────────────┘
```

## Pipeline

Four commands. Run them from `scripts/`.

```bash
# 1 — planes. Derive the palette from the person's reference image if they gave one.
python3 generate_layers.py --out layers/ --palette-from reference.jpg

# 2 — deck. Author content as JSON, build the pptx.
node build_deck.js deck.json --layers layers/ --out deck.pptx

# 3 — motion. Morph is a Microsoft extension; pptxgenjs cannot write it.
python3 morph_patch.py deck.pptx

# 4 — check. Renders the motion as a GIF without opening PowerPoint.
python3 preview_gif.py --layers layers/ --out preview.gif
```

Requires `pptxgenjs` (`npm i pptxgenjs`), `numpy`, `pillow`, and `zip`.

## How to run this with a person

**1. Get the three things you need.** Topic, reference image (optional), and
whether they want a video at the end. If they gave a reference image, pass it to
`--palette-from` so the panorama is built from their colours — this is the single
biggest factor in the deck feeling like *theirs*. If they gave a cut-out PNG with
transparency, pass it to `--cutout` and it becomes the near plane directly.

**2. Do the research before the design.** A gorgeous deck with thin content
loses to a plain deck with real research. Go to primary sources — the museum, the
manufacturer, the paper, the company's own docs — not the top three search
results. Specific numbers, named people, dates, and one surprising fact per slide.
If you find a contradiction between the person's source material and the record,
that is usually the best slide in the deck.

**3. Write `deck.json`.** See `reference/SCHEMA.md` for all twelve slide types.
Keep to the layouts provided rather than inventing new ones; they are tuned so
text never collides with the near plane. Vary the order and the mix per deck —
reaching for the same sequence every time is what makes decks feel templated.

**4. Build, patch, and LOOK AT IT.** Convert to PDF and view the slides as images
before you hand anything over:

```bash
soffice --headless --convert-to pdf deck.pptx && pdftoppm -jpeg -r 110 deck.pdf s
```

Check three things every time: text never sits under the cut-out except on the
title and closing slides (where it is deliberate); nothing collides with the
top-right footer; the last line of each slide clears the bottom edge.

**5. Tell them the constraints.** Morph needs PowerPoint 2019 / Microsoft 365 —
elsewhere it falls back to a fade. And the file is large (the panorama is embedded
once per slide), so mention the size if they have an upload limit.

## Make it their deck, not this deck

The rig repeats; the deck must not. Before you build, decide these four
separately for every project — never inherit them from a previous run or from
the bundled example:

- **Palette.** `--palette-from` their reference image, or `--hues` picked from
  the subject matter. A deck on deep-sea cable has no business being warm gold.
- **Near-plane subject.** It should belong to the topic. If they gave a cut-out
  PNG, use `--cutout`. If not, either recolour the built-in bloom with
  `--bloom-in/--bloom-out/--bloom-tip` so it reads as an abstract form rather
  than a flower, or generate/source a cut-out that suits the subject.
- **Slide order and mix.** Pick the layouts the argument needs. The example deck
  uses all twelve because it is a demo; a real deck usually should not.
- **The occlusion moment.** One slide where the subject crosses the headline.
  Choose which slide earns it based on the content.

If the finished deck could be swapped with the glass-flowers example by changing
only the words, something went wrong at step 1.

## Design rules that make it look expensive

- **Never black.** The panorama sweeps a hue range; the darkest value is a deep
  saturated colour, not neutral. Type is cream (`FFF7EC`), never pure white.
- **One accent does the pointing.** Gold for emphasis, rose reserved for the one
  slide that carries the twist. If everything is highlighted, nothing is.
- **The cut-out must have a dark separation halo** or it dissolves into the
  panorama. `generate_layers.py` adds one automatically.
- **Peek, don't crowd.** On dense slides the near plane should be 80% off-canvas —
  a single arc of the subject at the bottom edge. Full-frame subject is for the
  title and the closing slide only.
- **Let the headline be occluded once.** On the title slide, position the cut-out
  so it crosses the last word. That one moment is what people remember.
- **Scrims, not solid cards.** Text panels are the scrim colour at 20–30%
  transparency so the panorama still reads through them.

## Video

`{"type": "video", "link": "https://www.youtube.com/embed/ID"}` embeds a live
player. It needs an internet connection at presentation time, so always print the
URL on the slide too as a fallback, and put the video *before* the closing slide —
never end on someone else's footage.

## Reference

- `reference/SCHEMA.md` — every slide type and field
- `reference/TECHNIQUE.md` — why Morph needs `!!` names, what the OOXML looks like
- `examples/glass-flowers/deck.json` — a complete twelve-slide deck
