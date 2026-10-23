"""Regenerate fonts/*.pil from the X11 'misc' bitmap fonts (package xfonts-base).

The committed .pil/.pbm pairs were produced with this script; rerun it only
if you want a different set of faces. These fonts are public domain.
"""
import gzip, os, sys
from PIL import PcfFontFile

SRC = "/usr/share/fonts/X11/misc"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts")
faces = sys.argv[1:] or ["4x6", "5x7", "6x10", "6x13B", "7x13B"]
for face in faces:
    with gzip.open(os.path.join(SRC, f"{face}-ISO8859-1.pcf.gz"), "rb") as fp:
        PcfFontFile.PcfFontFile(fp).save(os.path.join(OUT, face))
    print("wrote", face)
