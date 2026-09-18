# How the parallax actually works

## The idea

Parallax is not an effect you switch on. It is a consequence of moving several
planes at different rates and letting the viewer's brain do the rest. A deck only
needs three planes to sell it convincingly:

| plane | shape name | travel per slide | role |
|---|---|---|---|
| panorama | `!!bg` | ~1.7 in | colour, mood, sense of place |
| midground | `!!mid` | ~2.5 in | the plane that proves there *is* depth |
| cut-out | `!!fg` | 4–12 in, plus scaling | the subject; crosses the type |

The panorama is authored many screens wide — roughly 2.4× the slide width — and
each slide shows a different window onto it. Over twelve slides the deck travels
the whole image, so the colour evolves continuously without any slide having a
"background colour" of its own.

## Why the type has to be in the middle

The move that makes people ask how you did it is a headline running *behind* the
subject. In practice that means z-order per slide is:

```
panorama  →  midground  →  TEXT  →  cut-out
```

In `build_deck.js` this is enforced structurally: `stage()` adds the two back
planes, the layout function adds the type, and `cutout()` is always called last.
There is no way to author a slide that gets this wrong.

The cut-out needs real transparency and a dark separation halo. Without the halo
a coloured subject sitting on a coloured panorama turns to mush — the halo is a
blurred copy of the alpha channel in near-black, composited underneath.

## Why `morph_patch.py` exists

Morph is not in the base OOXML schema. It is a Microsoft extension, so PowerPoint
writes it inside an `mc:AlternateContent` block that older readers skip:

```xml
<mc:AlternateContent xmlns:mc="...markup-compatibility/2006">
  <mc:Choice xmlns:p159="...powerpoint/2015/09/main" Requires="p159">
    <p:transition xmlns:p14="...powerpoint/2010/main" spd="slow" p14:dur="1600">
      <p159:morph option="byObject"/>
    </p:transition>
  </mc:Choice>
  <mc:Fallback>
    <p:transition spd="slow"><p:fade/></p:transition>
  </mc:Fallback>
</mc:AlternateContent>
```

It belongs after `</p:clrMapOvr>` — schema order inside `<p:sld>` is `cSld`,
`clrMapOvr`, `transition`, `timing`, and PowerPoint will refuse a file that gets
that order wrong.

No JavaScript pptx library writes this, so the build is two stages: generate a
valid ordinary deck, then patch the packed XML.

## Why the shapes are named `!!bg`, `!!mid`, `!!fg`

Left alone, Morph guesses which shapes on slide N correspond to which shapes on
slide N+1. With three large overlapping pictures on every slide it guesses badly,
and you get a blink instead of a glide.

A shape whose name begins with `!!` is an **explicit** morph match. PowerPoint
pairs `!!fg` on one slide with `!!fg` on the next and interpolates position,
size and rotation between them, no matter how different the two slides look. That
one convention is the difference between a slideshow and a camera move.

Pictures containing `videoFile` are skipped when assigning names, so an embedded
clip is never mistaken for the near plane.

## Choreographing the camera

Two rules produce nearly all of the good compositions:

1. **Alternate sides.** If the subject was right on slide 4, put it left on 5.
   The morph then sweeps it across the whole frame, which is the most legible
   possible expression of "this thing is close to you".

2. **Peek on dense slides.** When a slide carries a table, three cards or a
   timeline, push the subject 80% off canvas so only an arc shows. Depth is still
   read, and nothing competes with the content.

The one deliberate exception is the title slide, where the subject is full-bleed
and deliberately crosses the last word of the headline.

## Checking it without PowerPoint

`preview_gif.py` reproduces the interpolation — same eased timing, same three
rates, same cross-fade on the type — and writes an animated GIF. It is not a
renderer for the real deck; it is a fast way to see whether the choreography
reads before committing to a build.

To check layout rather than motion, convert and rasterise:

```bash
soffice --headless --convert-to pdf deck.pptx
pdftoppm -jpeg -r 110 deck.pdf slide
```

LibreOffice ignores Morph, which is the point: what you are checking there is
that no text collides with anything on any single slide.

## Known limits

- Morph requires PowerPoint 2019 or Microsoft 365. Keynote, Google Slides and
  LibreOffice fall back to the fade in `mc:Fallback`.
- The panorama is embedded once per slide, so a twelve-slide deck runs 30–40 MB.
  Downsample `--pano-width` if there is an upload cap.
- Embedded online video needs a live connection at presentation time.
