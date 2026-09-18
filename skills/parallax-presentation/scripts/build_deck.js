#!/usr/bin/env node
/**
 * build_deck.js — turn a deck spec (JSON) into a parallax .pptx.
 *
 *   node build_deck.js deck.json --layers layers/ --out deck.pptx
 *
 * Every slide stacks three planes plus type:
 *
 *      pano.jpg   (!!bg)   far    — pans slowly across all slides
 *      mid.png    (!!mid)  middle — pans faster
 *      <text>              middle — sits BETWEEN the planes
 *      bloom.png  (!!fg)   near   — moves most, and covers the type
 *
 * The cut-out is added LAST on every slide, so headlines run behind it.
 * Run morph_patch.py afterwards to add the Morph transitions that turn the
 * three different pan rates into actual parallax.
 *
 * Inline emphasis: wrap words in **double asterisks** to get accent-coloured
 * bold inside any paragraph string.
 */
const pptxgen = require("pptxgenjs");
const fs = require("fs");
const path = require("path");

// ---------------------------------------------------------------- args
const argv = process.argv.slice(2);
if (!argv.length) {
  console.error("usage: node build_deck.js deck.json [--layers DIR] [--out FILE]");
  process.exit(1);
}
const specPath = argv[0];
const arg = (name, dflt) => {
  const i = argv.indexOf("--" + name);
  return i > -1 && argv[i + 1] ? argv[i + 1] : dflt;
};
const spec = JSON.parse(fs.readFileSync(specPath, "utf8"));
const LAYERS = path.resolve(arg("layers", path.join(path.dirname(specPath), "layers")));
const OUT = path.resolve(arg("out", "deck.pptx"));

// ---------------------------------------------------------------- theme
const T = Object.assign({
  cream: "FFF7EC", creamDim: "E7D8CB", gold: "FFCB8E",
  mint: "9FE9D2", rose: "FFA9B8", scrim: "0C1A2E", bg: "12304A",
  serif: "Cambria", sans: "Calibri"
}, spec.theme || {});

const W = 13.333, H = 7.5, M = 0.75;
const slides = spec.slides || [];
const N = slides.length;

// ---------------------------------------------------------------- images
const cache = {};
function img(file) {
  if (!cache[file]) {
    const p = path.join(LAYERS, file);
    if (!fs.existsSync(p)) {
      console.error("missing layer: " + p + "\nRun generate_layers.py first.");
      process.exit(1);
    }
    const mime = file.endsWith(".png") ? "image/png" : "image/jpeg";
    cache[file] = { data: mime + ";base64," + fs.readFileSync(p).toString("base64"),
                    size: require("child_process") && null };
  }
  return { data: cache[file].data };
}
function has(file) { return fs.existsSync(path.join(LAYERS, file)); }

const aspectCache = {};
function aspect(file) {
  if (aspectCache[file] !== undefined) return aspectCache[file];
  // png/jpeg header sniff, enough for the sizes we generate
  const buf = fs.readFileSync(path.join(LAYERS, file));
  if (buf[0] === 0x89) return (aspectCache[file] = buf.readUInt32BE(16) / buf.readUInt32BE(20));
  let i = 2;
  while (i < buf.length) {
    if (buf[i] !== 0xff) { i++; continue; }
    const m = buf[i + 1];
    if (m >= 0xc0 && m <= 0xcf && m !== 0xc4 && m !== 0xc8 && m !== 0xcc) {
      return (aspectCache[file] = buf.readUInt16BE(i + 7) / buf.readUInt16BE(i + 5));
    }
    i += 2 + buf.readUInt16BE(i + 2);
  }
  return (aspectCache[file] = 1);
}

// ---------------------------------------------------------------- camera
const PANO_A = aspect("pano.jpg");
const MID_A = aspect("mid.png");
const BG_H = 9.0, BG_W = BG_H * PANO_A, BG_Y = -0.78;
const MD_H = 9.3, MD_W = MD_H * MID_A * 1.16, MD_Y = -0.95;
const span = (w) => Math.max(0.1, w - W);
const bgX = (i) => -0.30 - span(BG_W) * 0.98 * (N > 1 ? i / (N - 1) : 0);
const mdX = (i) =>  0.80 - span(MD_W) * 1.00 * (N > 1 ? i / (N - 1) : 0);

// near-plane slots: [x, y, width]
const SLOTS = {
  "hero-right":     [ 5.10, -0.60, 9.60],
  "hero-right-mid": [ 7.40,  0.40, 8.60],
  "right":          [ 9.40,  2.00, 6.30],
  "left":           [-2.00,  2.30, 6.50],
  "left-mid":       [ 0.30,  1.70, 4.80],
  "peek-right":     [12.40,  1.40, 4.60],
  "peek-bottom":    [ 7.90,  6.50, 4.30],
  "peek-bottom-c":  [ 7.60,  6.55, 4.00],
  "peek-bottom-l":  [ 1.00,  6.70, 3.80],
  "peek-bottom-m":  [ 8.60,  6.40, 4.20],
  "peek-bottom-x":  [ 2.10,  6.45, 4.00]
};
const AUTO_SLOT = {
  title: "hero-right", quote: "right", list: "left", stats: "peek-bottom-c",
  steps: "peek-right", compare: "peek-bottom", split: "peek-bottom-x",
  feature: "left-mid", cards: "peek-bottom-l", video: "peek-bottom-m",
  closing: "hero-right-mid", references: "peek-right"
};

// ---------------------------------------------------------------- text
/** "plain **accent** plain" -> pptxgenjs rich-text runs */
function rt(str, base, accent, bold) {
  if (Array.isArray(str)) return str;
  const runs = [];
  String(str).split(/(\*\*[^*]+\*\*)/).forEach((part) => {
    if (!part) return;
    if (part.startsWith("**") && part.endsWith("**")) {
      runs.push({ text: part.slice(2, -2), options: { color: accent, bold: true } });
    } else {
      runs.push({ text: part, options: { color: base, bold: !!bold } });
    }
  });
  return runs.length ? runs : [{ text: "", options: { color: base } }];
}

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE";
pres.author = (spec.meta && spec.meta.author) || "";
pres.title = (spec.meta && spec.meta.title) || "Parallax deck";

let idx = 0;
function stage() {
  const i = idx++;
  const s = pres.addSlide();
  s.background = { color: T.bg };
  s.addImage(Object.assign({ x: bgX(i), y: BG_Y, w: BG_W, h: BG_H }, img("pano.jpg")));
  s.addImage(Object.assign({ x: mdX(i), y: MD_Y, w: MD_W, h: MD_H, transparency: 40 },
                           img("mid.png")));
  s._i = i;
  return s;
}

const warned = {};
function cutout(s, sl) {
  let asset = sl.fgAsset || "bloom.png";
  if (!has(asset)) {
    if (!warned[asset]) {
      console.warn("note: layer \"" + asset + "\" not found, falling back to bloom.png");
      warned[asset] = true;
    }
    asset = "bloom.png";
  }
  const slot = sl.fg || SLOTS[sl.fgSlot || AUTO_SLOT[sl.type] || "peek-bottom"];
  const ratio = 1 / aspect(asset);
  s.addImage(Object.assign({ x: slot[0], y: slot[1], w: slot[2], h: slot[2] * ratio },
                           img(asset)));
  if (s._i > 0 && spec.meta && spec.meta.footer !== false) {
    const f = (spec.meta && spec.meta.footer) || pres.title;
    s.addText(f + "   \u00b7   " + (s._i + 1) + " / " + N, {
      x: W - M - 4.6, y: 0.5, w: 4.6, h: 0.3, isTextBox: true, margin: 0, align: "right",
      fontFace: T.sans, fontSize: 9, color: T.creamDim, charSpacing: 0.7, transparency: 25
    });
  }
  if (sl.notes) s.addNotes(sl.notes);
}

function scrim(s, x, y, w, h, t) {
  s.addShape(pres.ShapeType.roundRect, {
    x: x, y: y, w: w, h: h, rectRadius: 0.11,
    fill: { color: T.scrim, transparency: t === undefined ? 28 : t },
    line: { color: T.cream, width: 0.5, transparency: 82 }
  });
}

function head(s, sl, x, w, size) {
  if (sl.eyebrow) {
    s.addText(sl.eyebrow.toUpperCase(), {
      x: x, y: 0.5, w: w, h: 0.28, isTextBox: true, margin: 0, fontFace: T.sans,
      fontSize: 10.5, bold: true, color: sl.accent === "rose" ? T.rose : T.gold,
      charSpacing: 2.2
    });
  }
  s.addText(sl.title || "", {
    x: x, y: 0.84, w: w, h: 1.05, isTextBox: true, margin: 0,
    fontFace: T.serif, fontSize: size, bold: true, color: T.cream, lineSpacing: size * 1.06,
    shadow: { type: "outer", color: "061120", blur: 10, offset: 2, angle: 90, opacity: 0.55 }
  });
}

function para(s, str, x, y, w, h, size) {
  s.addText(rt(str, T.creamDim, T.gold), {
    x: x, y: y, w: w, h: h, isTextBox: true, margin: 0,
    fontFace: T.sans, fontSize: size || 12.5, lineSpacing: (size || 12.5) * 1.46
  });
}

function dot(s, x, y, label, col) {
  const c = col || T.gold;
  s.addShape(pres.ShapeType.ellipse, { x: x, y: y, w: 0.42, h: 0.42,
    fill: { color: c, transparency: 78 }, line: { color: c, width: 0.75 } });
  s.addText(String(label), { x: x, y: y + 0.015, w: 0.42, h: 0.39, isTextBox: true,
    margin: 0, align: "center", valign: "middle", fontFace: T.sans, fontSize: 11,
    bold: true, color: T.cream });
}

function footnote(s, str, x, y, w) {
  if (!str) return;
  s.addText(rt(str, T.gold, T.gold), { x: x, y: y, w: w, h: 0.4, isTextBox: true,
    margin: 0, fontFace: T.serif, fontSize: 14, italic: true, color: T.gold });
}

// ---------------------------------------------------------------- layouts
const LAYOUT = {

  title(s, sl) {
    if (sl.eyebrow) s.addText(sl.eyebrow.toUpperCase(), {
      x: M, y: 1.95, w: 8.0, h: 0.3, isTextBox: true, margin: 0, fontFace: T.sans,
      fontSize: 11, bold: true, color: T.gold, charSpacing: 2.4 });
    s.addText(sl.title || "", {
      x: M, y: 2.30, w: 9.4, h: 2.4, isTextBox: true, margin: 0, fontFace: T.serif,
      fontSize: sl.size || 68, bold: true, color: T.cream, lineSpacing: (sl.size || 68) * 1.10,
      shadow: { type: "outer", color: "05101E", blur: 16, offset: 3, angle: 90, opacity: 0.6 } });
    if (sl.subtitle) s.addText(sl.subtitle, {
      x: M, y: 5.02, w: 6.4, h: 0.5, isTextBox: true, margin: 0, fontFace: T.serif,
      fontSize: 17, italic: true, color: T.rose });
    if (sl.meta) s.addText(sl.meta.toUpperCase(), {
      x: M, y: 5.86, w: 8.0, h: 0.32, isTextBox: true, margin: 0, fontFace: T.sans,
      fontSize: 11, color: T.creamDim, charSpacing: 1.5 });
  },

  quote(s, sl) {
    head(s, sl, M, 7.6, sl.size || 38);
    s.addText("\u201C" + sl.quote + "\u201D", {
      x: M, y: 2.08, w: 7.4, h: 1.7, isTextBox: true, margin: 0, fontFace: T.serif,
      fontSize: 36, italic: true, color: T.gold, lineSpacing: 44,
      shadow: { type: "outer", color: "05101E", blur: 12, offset: 2, angle: 90, opacity: 0.55 } });
    if (sl.cite) s.addText(sl.cite.toUpperCase(), {
      x: M, y: 3.90, w: 7.4, h: 0.3, isTextBox: true, margin: 0, fontFace: T.sans,
      fontSize: 9.5, color: T.creamDim, charSpacing: 1.3 });
    const rows = sl.list || [];
    if (rows.length) {
      scrim(s, M, 4.32, 8.2, 0.42 + rows.length * 0.66);
      let y = 4.55;
      rows.forEach((r, i) => {
        dot(s, M + 0.3, y, i + 1);
        s.addText([{ text: r.label + "  ", options: { bold: true, color: T.cream } },
                   { text: "\u2014  " + r.text, options: { color: T.creamDim } }],
          { x: M + 0.88, y: y + 0.04, w: 7.0, h: 0.34, isTextBox: true, margin: 0,
            fontFace: T.sans, fontSize: 12.5 });
        y += 0.66;
      });
    }
    if (sl.footnote) s.addText(sl.footnote, { x: M, y: 6.72, w: 8.4, h: 0.4,
      isTextBox: true, margin: 0, fontFace: T.sans, fontSize: 11, italic: true, color: T.gold });
  },

  list(s, sl) {
    const right = sl.side !== "left";
    const x = right ? 4.6 : M;
    head(s, sl, x, 8.0, sl.size || 34);
    const rows = sl.rows || [];
    scrim(s, x, 2.62, 8.0, 0.3 + rows.length * 0.93);
    let y = 2.9;
    rows.forEach((r, i) => {
      dot(s, x + 0.32, y, i + 1);
      s.addText(r.label, { x: x + 0.9, y: y - 0.02, w: 6.85, h: 0.3, isTextBox: true,
        margin: 0, fontFace: T.sans, fontSize: 13, bold: true, color: T.cream });
      s.addText(rt(r.text, T.creamDim, T.gold), { x: x + 0.9, y: y + 0.3, w: 6.85, h: 0.55,
        isTextBox: true, margin: 0, fontFace: T.sans, fontSize: 11, lineSpacing: 15 });
      y += 0.93;
    });
    footnote(s, sl.footnote, x, Math.max(y + 0.12, 6.68), 8.0);
  },

  stats(s, sl) {
    head(s, sl, M, 8.6, sl.size || 38);
    const st = sl.stats || [];
    let sx = M, wid = st.length ? (11.8 - (st.length - 1) * 0.16) / st.length : 0;
    st.forEach((c) => {
      scrim(s, sx, 1.98, wid, 1.30, 24);
      s.addText(c.value, { x: sx, y: 2.06, w: wid, h: 0.72, isTextBox: true, margin: 0,
        align: "center", fontFace: T.serif, fontSize: 38, bold: true, color: T.gold });
      s.addText(c.label.toUpperCase(), { x: sx, y: 2.82, w: wid, h: 0.34, isTextBox: true,
        margin: 0, align: "center", fontFace: T.sans, fontSize: 9.5, bold: true,
        color: T.creamDim, charSpacing: 1.3 });
      sx += wid + 0.16;
    });
    const tl = sl.timeline || [];
    const pw = tl.length ? 5.85 : 11.8;
    let py = 3.58;
    (sl.paragraphs || []).forEach((p) => { para(s, p, M, py, pw, 1.7, 12); py += 1.78; });
    if (tl.length) {
      scrim(s, 7.45, 3.42, 5.18, 0.2 + tl.length * 0.465);
      let ty = 3.62;
      tl.forEach((t) => {
        const c = t.accent ? T.rose : T.mint;
        s.addShape(pres.ShapeType.ellipse, { x: 7.73, y: ty + 0.14, w: 0.11, h: 0.11,
          fill: { color: c }, line: { color: c, width: 0.5 } });
        s.addText(t.year, { x: 7.99, y: ty, w: 0.92, h: 0.40, isTextBox: true, margin: 0,
          valign: "middle", fontFace: T.serif, fontSize: 14, bold: true, color: c });
        s.addText(t.text, { x: 8.95, y: ty, w: 3.47, h: 0.40, isTextBox: true, margin: 0,
          valign: "middle", fontFace: T.sans, fontSize: 10, color: T.creamDim, lineSpacing: 13 });
        ty += 0.465;
      });
    }
  },

  steps(s, sl) {
    head(s, sl, M, 8.6, sl.size || 38);
    if (sl.intro) para(s, sl.intro, M, 2.00, 11.8, 0.9, 13);
    let y = sl.intro ? 3.12 : 2.20;
    (sl.steps || []).forEach((st, i) => {
      scrim(s, M, y, 11.1, 0.72, st.accent ? 20 : 30);
      dot(s, M + 0.24, y + 0.15, i + 1, st.accent ? T.rose : T.gold);
      s.addText(st.label, { x: M + 0.82, y: y + 0.08, w: 2.3, h: 0.5, isTextBox: true,
        margin: 0, valign: "middle", fontFace: T.sans, fontSize: 12, bold: true, color: T.cream });
      s.addText(rt(st.text, T.creamDim, T.gold), { x: M + 3.2, y: y + 0.06, w: 7.6, h: 0.6,
        isTextBox: true, margin: 0, valign: "middle", fontFace: T.sans, fontSize: 10,
        lineSpacing: 13 });
      y += 0.80;
    });
  },

  compare(s, sl) {
    head(s, sl, M, 9.4, sl.size || 38);
    [[sl.left, M, T.mint, 28], [sl.right, 6.85, T.rose, 20]].forEach(([p, x, col, tr]) => {
      if (!p) return;
      scrim(s, x, 2.08, 5.8, 2.78, tr);
      s.addText(p.label.toUpperCase(), { x: x + 0.38, y: 2.32, w: 5.0, h: 0.3,
        isTextBox: true, margin: 0, fontFace: T.sans, fontSize: 10, bold: true,
        color: col, charSpacing: 1.8 });
      (p.paras || []).slice(0, 2).forEach((t, i) => {
        s.addText(rt(t, T.creamDim, i ? T.creamDim : T.cream), {
          x: x + 0.38, y: i ? 3.86 : 2.68, w: 5.02, h: i ? 0.8 : 1.0, isTextBox: true,
          margin: 0, fontFace: T.sans, fontSize: i ? 11.5 : 12.5, lineSpacing: i ? 16 : 18 });
      });
    });
    if (sl.footnote) para(s, sl.footnote, M, 5.18, 11.85, 1.0, 13);
  },

  split(s, sl) {
    head(s, sl, M, 5.6, sl.size || 32);
    let y = 2.62;
    (sl.paragraphs || []).forEach((p) => { para(s, p, M, y, 5.4, 1.5, 12.5); y += 1.58; });
    if (sl.pull) s.addText(sl.pull, { x: M, y: Math.max(y, 4.2), w: 5.4, h: 1.2,
      isTextBox: true, margin: 0, fontFace: T.serif, fontSize: 17, italic: true,
      color: T.gold, lineSpacing: 24 });
    const rows = sl.rows || [];
    scrim(s, 6.6, 1.72, 6.03, 0.2 + rows.length * 1.22);
    let ry = 1.98;
    rows.forEach((r, i) => {
      dot(s, 6.92, ry + 0.06, i + 1);
      s.addText(r.label, { x: 7.5, y: ry, w: 4.85, h: 0.3, isTextBox: true, margin: 0,
        fontFace: T.sans, fontSize: 13, bold: true, color: T.cream });
      s.addText(rt(r.text, T.creamDim, T.gold), { x: 7.5, y: ry + 0.3, w: 4.85, h: 0.75,
        isTextBox: true, margin: 0, fontFace: T.sans, fontSize: 10.5, lineSpacing: 14 });
      ry += 1.22;
    });
  },

  feature(s, sl) {
    const x = 5.6;
    head(s, sl, x, 7.1, sl.size || 32);
    let y = 2.30;
    (sl.paragraphs || []).forEach((p) => { para(s, p, x, y, 7.0, 1.1, 12.5); y += 1.22; });
    if (sl.panel) {
      const b = sl.panel.bullets || [];
      scrim(s, x, y, 7.03, 0.5 + b.length * 0.40, 20);
      s.addText(sl.panel.label.toUpperCase(), { x: x + 0.3, y: y + 0.2, w: 6.4, h: 0.28,
        isTextBox: true, margin: 0, fontFace: T.sans, fontSize: 9.5, bold: true,
        color: T.rose, charSpacing: 1.6 });
      let by = y + 0.50;
      b.forEach((t) => {
        s.addShape(pres.ShapeType.ellipse, { x: x + 0.32, y: by + 0.10, w: 0.1, h: 0.1,
          fill: { color: T.rose }, line: { color: T.rose, width: 0.5 } });
        s.addText(rt(t, T.creamDim, T.gold), { x: x + 0.58, y: by, w: 6.2, h: 0.36,
          isTextBox: true, margin: 0, fontFace: T.sans, fontSize: 10.5, lineSpacing: 13.5 });
        by += 0.40;
      });
      y = by + 0.20;
    }
    (sl.after || []).forEach((p) => { para(s, p, x, y, 7.0, 1.1, 12.5); y += 1.10; });
    if (sl.pull) s.addText(sl.pull, { x: x, y: Math.min(y, 6.86), w: 7.0, h: 0.4,
      isTextBox: true, margin: 0, fontFace: T.serif, fontSize: 16, italic: true, color: T.rose });
  },

  cards(s, sl) {
    head(s, sl, M, 11.6, sl.size || 34);
    const cards = (sl.cards || []).slice(0, 3);
    let cx = M, wid = 3.86;
    cards.forEach((c, i) => {
      scrim(s, cx, 2.02, wid, 3.4);
      dot(s, cx + 0.34, 2.3, i + 1);
      s.addText(c.title, { x: cx + 0.34, y: 2.88, w: wid - 0.66, h: 0.78, isTextBox: true,
        margin: 0, valign: "top", fontFace: T.serif, fontSize: 17, bold: true,
        color: T.cream, lineSpacing: 21 });
      s.addText(rt(c.text, T.creamDim, T.gold), { x: cx + 0.34, y: 3.7, w: wid - 0.66, h: 1.6,
        isTextBox: true, margin: 0, valign: "top", fontFace: T.sans, fontSize: 10,
        lineSpacing: 13.5 });
      cx += wid + 0.18;
    });
    if (sl.footnote) para(s, sl.footnote, M, 5.66, 11.85, 0.9, 13);
  },

  video(s, sl) {
    head(s, sl, M, 8.6, sl.size || 38);
    s.addShape(pres.ShapeType.roundRect, { x: M - 0.1, y: 1.96, w: 7.82, h: 4.48,
      rectRadius: 0.1, fill: { color: T.scrim, transparency: 12 },
      line: { color: T.cream, width: 0.5, transparency: 70 } });
    s.addMedia({ x: M, y: 2.06, w: 7.62, h: 4.28, type: "online", link: sl.link });
    let y = 2.10;
    (sl.paragraphs || []).forEach((p) => { para(s, p, 8.75, y, 3.85, 1.7, 11.5); y += 1.80; });
    if (sl.note) s.addText(sl.note, { x: 8.75, y: Math.min(y, 5.30), w: 3.85, h: 0.7,
      isTextBox: true, margin: 0, fontFace: T.sans, fontSize: 10.5, italic: true,
      color: T.rose, lineSpacing: 14 });
    if (sl.url) s.addText(sl.url, { x: 8.75, y: 6.06, w: 3.85, h: 0.4, isTextBox: true,
      margin: 0, fontFace: T.sans, fontSize: 9.5, color: T.mint });
  },

  closing(s, sl) {
    if (sl.eyebrow) s.addText(sl.eyebrow.toUpperCase(), { x: M, y: 1.3, w: 7.0, h: 0.3,
      isTextBox: true, margin: 0, fontFace: T.sans, fontSize: 10.5, bold: true,
      color: T.gold, charSpacing: 2.2 });
    s.addText(sl.title || "", { x: M, y: 1.72, w: 7.2, h: 2.6, isTextBox: true, margin: 0,
      fontFace: T.serif, fontSize: sl.size || 44, bold: true, color: T.cream,
      lineSpacing: (sl.size || 44) * 1.18,
      shadow: { type: "outer", color: "05101E", blur: 16, offset: 3, angle: 90, opacity: 0.6 } });
    let y = 4.5;
    (sl.paragraphs || []).forEach((p) => { para(s, p, M, y, 6.6, 1.3, 12.5); y += 1.16; });
  },

  references(s, sl) {
    head(s, sl, M, 7.0, sl.size || 32);
    const items = sl.items || [];
    const half = Math.ceil(items.length / 2);
    [[items.slice(0, half), M], [items.slice(half), 6.85]].forEach(([list, x]) => {
      let y = 1.98;
      list.forEach((it) => {
        s.addText(it.cite, { x: x, y: y, w: 5.55, h: 0.56, isTextBox: true, margin: 0,
          fontFace: T.sans, fontSize: 11, color: T.cream, lineSpacing: 14.5 });
        s.addText(it.source, { x: x, y: y + 0.57, w: 5.55, h: 0.56, isTextBox: true,
          margin: 0, fontFace: T.sans, fontSize: 10,
          color: it.plain ? T.creamDim : T.mint, lineSpacing: 13.5 });
        y += 1.22;
      });
    });
  }
};

// ---------------------------------------------------------------- render
slides.forEach((sl) => {
  const fn = LAYOUT[sl.type];
  if (!fn) { console.error("unknown slide type: " + sl.type); process.exit(1); }
  const s = stage();
  fn(s, sl);
  cutout(s, sl);
});

pres.writeFile({ fileName: OUT }).then((f) => {
  console.log("wrote " + f + "  (" + N + " slides)");
  console.log("next: python3 morph_patch.py \"" + f + "\"");
});
