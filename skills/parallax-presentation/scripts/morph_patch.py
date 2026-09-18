#!/usr/bin/env python3
"""
morph_patch.py — add PowerPoint Morph transitions to a generated .pptx.

    python3 morph_patch.py deck.pptx [--duration 1600]

Why this exists
---------------
pptxgenjs cannot write the Morph transition: Morph is a Microsoft extension
element (``p159:morph``), not part of the base OOXML schema. So we patch the
packed XML directly, doing two things to every slide:

1.  Rename the three parallax pictures to ``!!bg`` / ``!!mid`` / ``!!fg``.
    PowerPoint treats a shape name starting with ``!!`` as an EXPLICIT morph
    match: the same name on consecutive slides is interpolated (moved and
    scaled) instead of cross-faded. That interpolation, applied to three
    planes moving at three different rates, is the parallax.

2.  Insert the morph transition after ``</p:clrMapOvr>``, wrapped in
    ``mc:AlternateContent`` with a plain fade in ``mc:Fallback`` so older
    PowerPoint, Keynote and Google Slides degrade instead of breaking.

Video pictures (``<p:pic>`` containing ``videoFile``) are skipped so an
embedded clip never gets claimed as the near plane.
"""
import argparse, os, re, shutil, subprocess, sys, tempfile, zipfile

TRANSITION = (
    '<mc:AlternateContent xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006">'
    '<mc:Choice xmlns:p159="http://schemas.microsoft.com/office/powerpoint/2015/09/main" Requires="p159">'
    '<p:transition xmlns:p14="http://schemas.microsoft.com/office/powerpoint/2010/main"'
    ' spd="slow" p14:dur="{dur}"><p159:morph option="byObject"/></p:transition>'
    '</mc:Choice>'
    '<mc:Fallback><p:transition spd="slow"><p:fade/></p:transition></mc:Fallback>'
    '</mc:AlternateContent>'
)


def patch(pptx_path, duration=1600, verbose=True):
    pptx_path = os.path.abspath(pptx_path)
    work = tempfile.mkdtemp(prefix="morph_")
    try:
        with zipfile.ZipFile(pptx_path) as z:
            z.extractall(work)

        slide_dir = os.path.join(work, "ppt", "slides")
        names = sorted([f for f in os.listdir(slide_dir) if f.endswith(".xml")],
                       key=lambda n: int(re.search(r"\d+", n).group()))

        for name in names:
            p = os.path.join(slide_dir, name)
            xml = open(p, encoding="utf-8").read()

            spans = [m.span() for m in re.finditer(r"<p:pic>.*?</p:pic>", xml, re.S)
                     if "videoFile" not in xml[m.start():m.end()]]
            if spans:
                labels = {0: "!!bg", len(spans) - 1: "!!fg"}
                if len(spans) > 2:
                    labels[1] = "!!mid"
                for i in range(len(spans) - 1, -1, -1):
                    if i not in labels:
                        continue
                    a, b = spans[i]
                    block = re.sub(r'(<p:cNvPr id="\d+" name=")[^"]*(")',
                                   lambda m: m.group(1) + labels[i] + m.group(2),
                                   xml[a:b], count=1)
                    xml = xml[:a] + block + xml[b:]

            if "p159:morph" not in xml:
                t = TRANSITION.format(dur=int(duration))
                if "</p:clrMapOvr>" in xml:
                    xml = xml.replace("</p:clrMapOvr>", "</p:clrMapOvr>" + t, 1)
                else:
                    xml = xml.replace("</p:cSld>", "</p:cSld>" + t, 1)

            open(p, "w", encoding="utf-8").write(xml)
            if verbose:
                print("patched", name)

        os.remove(pptx_path)
        subprocess.run(["zip", "-Xrq", pptx_path, "."], cwd=work, check=True)
        if verbose:
            print("repacked ->", pptx_path)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pptx")
    ap.add_argument("--duration", type=int, default=1600,
                    help="morph duration in ms (default 1600)")
    a = ap.parse_args()
    if not os.path.exists(a.pptx):
        sys.exit("no such file: " + a.pptx)
    patch(a.pptx, a.duration)
