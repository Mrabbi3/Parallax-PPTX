#!/usr/bin/env python3
"""
preview_gif.py — render the parallax motion as an animated GIF.

PowerPoint's Morph only exists inside PowerPoint, so this reproduces what it
does: it composites the three planes at interpolated positions and cross-fades
the type between slides. Useful for checking the choreography before you open
the deck, and for putting a moving demo in a README.

    python3 preview_gif.py --layers layers/ --out preview.gif
    python3 preview_gif.py --layers layers/ --out preview.gif \
        --captions "Flowers That Never Fade|The Glass Flowers|A father, a son"
"""
import argparse, math, os, sys
from PIL import Image, ImageDraw, ImageFont

SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def ease(t):
    return t * t * (3 - 2 * t)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layers", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=900)
    ap.add_argument("--frames", type=int, default=18, help="frames per transition")
    ap.add_argument("--captions", default="Three planes|One camera|That is the whole trick")
    ap.add_argument("--hold", type=int, default=6, help="held frames at each stop")
    a = ap.parse_args()

    W = a.width
    H = int(W * 9 / 16)
    def layer(name):
        p = os.path.join(a.layers, name)
        if not os.path.exists(p):
            sys.exit("missing layer: %s\nRun generate_layers.py --out %s first." % (p, a.layers))
        return Image.open(p).convert("RGBA")

    pano = layer("pano.jpg")
    mid = layer("mid.png")
    fg = layer("bloom.png")

    # scale planes so the far plane is ~2.3 screens wide, mid wider still
    pano_h = int(H * 1.20)
    pano_w = int(pano.width * pano_h / pano.height)
    pano_s = pano.resize((pano_w, pano_h), Image.LANCZOS)
    mid_h = int(H * 1.24)
    mid_w = int(mid.width * mid_h / mid.height)
    mid_s = mid.resize((mid_w, mid_h), Image.LANCZOS)

    caps = a.captions.split("|")
    n = len(caps)

    # camera stops: (bg_x, mid_x, fg_x, fg_y, fg_scale)
    stops = []
    for i in range(n):
        t = i / max(1, n - 1)
        stops.append((
            -0.02 * W - (pano_w - W) * t,
            0.06 * W - (mid_w - W) * t,
            (0.46 if i % 2 == 0 else -0.14) * W,
            (-0.10 if i % 2 == 0 else 0.20) * H,
            (0.95 if i % 2 == 0 else 0.62),
        ))

    f_title = font(SERIF, int(W * 0.052))
    f_eyebrow = font(SANS, int(W * 0.015))

    frames = []
    for i in range(n):
        j = (i + 1) % n
        for k in range(a.frames + a.hold):
            t = ease(min(1.0, max(0.0, (k - a.hold) / a.frames)))
            s0, s1 = stops[i], stops[j]
            bx = s0[0] + (s1[0] - s0[0]) * t
            mx = s0[1] + (s1[1] - s0[1]) * t
            fx = s0[2] + (s1[2] - s0[2]) * t
            fy = s0[3] + (s1[3] - s0[3]) * t
            fs = s0[4] + (s1[4] - s0[4]) * t

            frame = Image.new("RGBA", (W, H), (18, 48, 74, 255))
            frame.alpha_composite(pano_s, (int(bx), int(-0.10 * H)))
            m = mid_s.copy()
            m.putalpha(m.getchannel("A").point(lambda v: int(v * 0.55)))
            frame.alpha_composite(m, (int(mx), int(-0.12 * H)))

            # type sits between the mid plane and the cut-out
            d = ImageDraw.Draw(frame)
            fade_out = 1.0 - min(1.0, t / 0.45)
            fade_in = max(0.0, (t - 0.55) / 0.45)
            for text, alpha, dy in ((caps[i], fade_out, -10 * t), (caps[j], fade_in, 16 * (1 - t))):
                if alpha <= 0.02:
                    continue
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ld = ImageDraw.Draw(layer)
                ld.text((int(W * 0.055), int(H * 0.30)), "PARALLAX PRESENTATION",
                        font=f_eyebrow, fill=(255, 203, 142, int(230 * alpha)))
                ld.text((int(W * 0.052), int(H * 0.38 + dy)), text,
                        font=f_title, fill=(255, 247, 236, int(255 * alpha)))
                frame.alpha_composite(layer)

            fw = int(W * 0.62 * fs)
            f_img = fg.resize((fw, int(fw * fg.height / fg.width)), Image.LANCZOS)
            frame.alpha_composite(f_img, (int(fx), int(fy)))

            frames.append(frame.convert("P", palette=Image.ADAPTIVE, colors=200))

    frames[0].save(a.out, save_all=True, append_images=frames[1:],
                   duration=55, loop=0, optimize=True)
    print("wrote", a.out, len(frames), "frames")


if __name__ == "__main__":
    main()
