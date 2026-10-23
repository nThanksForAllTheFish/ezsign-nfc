import os
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","examples")
from PIL import Image, ImageDraw, ImageFont
import textwrap
W,H=400,300
K,Wt,Rd,Yl=(0,0,0),(255,255,255),(255,0,0),(255,255,0)
P=lambda n: ImageFont.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fonts", f"{n}.pil"))
f4,f5,f6,f6b,f7b=P("4x6"),P("5x7"),P("6x10"),P("6x13B"),P("7x13B")
im=Image.new("RGB",(W,H),Wt); d=ImageDraw.Draw(im); d.fontmode="1"
def T(x,y,s,f,c=K): d.text((x,y),s,font=f,fill=c)
# ---- header (0..17)
d.rectangle([0,0,W,17],fill=K)
T(4,2,"EZ SIGN 4.2\" 400x300 4-COLOR E-PAPER",f7b,Wt)
T(W-4-6*len("PIXEL FONT TEST"),2,"PIXEL FONT TEST",f6b,Yl)
# ---- font ladder (20..99)
y=20
T(4,y,"FONT LADDER - each row is a bitmap font at its native cell size, 1 glyph pixel = 1 display pixel",f4); y+=8
rows=[("4x6 ",f4,6,"The quick brown fox jumps over the lazy dog 0123456789 !?$%&*()[]{}<>=+-/@#"),
      ("5x7 ",f5,7,"The quick brown fox jumps over the lazy dog 0123456789 !?$%&*()"),
      ("6x10",f6,10,"The quick brown fox jumps over the lazy dog 0123456789"),
      ("6x13B",f6b,13,"The quick brown fox jumps over the lazy dog 01234"),
      ("7x13B",f7b,13,"The quick brown fox jumps over 0123456789")]
for name,f,h,s in rows:
    d.rectangle([4,y,33,y+h-1],fill=Rd); T(5,y+(h-6)//2,name,f4,Wt)
    T(38,y+(0 if f is not f4 else 0),s,f); y+=h+1
# ---- two-column dense body (y..254)
y0=y+3; d.line([(0,y0-2),(W,y0-2)],fill=K)
colA=textwrap.wrap(
 "WHAT THIS SHOWS. The smallest text on this page is the X11 4x6 bitmap font: each glyph is 3 "
 "columns wide plus a 1-pixel gap, 5 rows tall plus 1 row of leading, so a line of text is exactly "
 "6 display pixels high and a full 400-pixel row holds 100 characters. Nothing is anti-aliased; "
 "every stroke lands on whole pixels of the 400x300 panel, so what you see here is what the "
 "e-paper will draw. On the 84.8 x 63.6 mm active area one pixel is 0.212 mm, which makes the 4x6 "
 "cell 0.85 x 1.27 mm: about 1/3 the x-height of 6-point print. Hold the sign at reading distance "
 "and it is legible but demanding; 5x7 is comfortable and 6x10 reads like a datasheet.",98)
colB=textwrap.wrap(
 "FOUR-COLOR BUDGET. Black, white, red and yellow are the only inks. Text uses black on white for "
 "contrast; red and yellow are kept for emphasis bars and rules because thin red or yellow strokes "
 "on white lose contrast fast. The panel takes about 25 s to refresh a 4-color image over NFC, "
 "versus a few seconds for the 2-color variant, and the image then holds with no power at all.",98)
for ln in colA: T(4,y0,ln,f4); y0+=6
y0+=3
for ln in colB: T(4,y0,ln,f4); y0+=6
# ---- spec table (right) and NFC block, in 5x7 and 4x6
y1=y0+4; d.line([(0,y1-2),(W,y1-2)],fill=K)
d.rectangle([4,y1,4+5*17,y1+8],fill=Yl); T(5,y1+1,"PANEL SPEC SHEET",f5)
spec=[("Resolution","400 x 300 px"),("Active area","84.8 x 63.6 mm"),("Pixel pitch","0.212 mm"),
      ("Colors","K / W / R / Y"),("Refresh","~25 s (4-color)"),("Power","NFC field, no battery"),
      ("Thickness","3.4 mm"),("Mass","29 g"),("Rating","IP65, 0-40 C")]
yy=y1+11
for i,(a,b) in enumerate(spec):
    T(4,yy,a,f4); T(4+4*14,yy,":",f4); T(4+4*16,yy,b,f4,Rd if i in(0,2) else K); yy+=6
# right: pixel ruler + character grid
rx=232; T(rx,y1+1,"4x6 CELL, 8X ZOOM",f5)
tmp=Image.new("1",(4,6),1); ImageDraw.Draw(tmp).text((0,0),"A",font=f4,fill=0)
g=[[1-tmp.getpixel((i,j)) for i in range(4)] for j in range(6)]
for j in range(6):
    for i in range(4):
        on=g[j][i]
        d.rectangle([rx+i*8,y1+11+j*8,rx+i*8+7,y1+11+j*8+7],fill=K if on else Wt,outline=Rd if (i==3 or j==5) else K)
T(rx+38,y1+13,"3 col + 1 gap",f4); T(rx+38,y1+21,"5 row + 1 lead",f4)
T(rx+38,y1+29,"=4x6 px / glyph",f4); T(rx+38,y1+37,"=0.85x1.27 mm",f4)
T(rx+38,y1+47,"100 cols x 50 rows",f4,Rd); T(rx+38,y1+55,"= 5000 chars/page",f4,Rd)
y2=max(yy,y1+66)+3; d.line([(0,y2-2),(W,y2-2)],fill=K)
d.rectangle([0,y2,W,y2+7],fill=Rd); T(2,y2+1,"100-COLUMN STRESS BLOCK  4x6 at full width, 6 px line pitch, no margins, 100 characters per line",f4,Wt)
body=("NFC-POWERED E-PAPER. The tag has no battery: a phone held over the antenna supplies both the "
 "energy and the image through the 13.56 MHz field. The controller charges a small reservoir, "
 "clocks the bitmap into the display driver, then runs the waveform that moves the pigment particles "
 "into place. Once the waveform ends the particles stay put, so the image survives with the field "
 "removed. A 4-color panel stacks black, red and yellow pigments and sequences them separately, which "
 "is why its refresh is around 25 s against a few seconds for a 2-color unit. Content tips: keep text "
 "black on white, use red and yellow as fills rather than thin lines, avoid gray (it dithers), and "
 "size the smallest type to a whole-pixel bitmap font so no edge is lost to resampling in the app.")
for ln in textwrap.wrap(body,100)[:9]:
    y2+=6; T(0,y2+3,ln,f4)
# ---- 100-column ruler (bottom)
ry=H-14; d.rectangle([0,ry,W,H],fill=K)
T(0,ry+1,"".join(str(i%10) for i in range(100)),f4,Yl)
T(0,ry+7,"0         10        20        30        40        50        60        70        80        90       ",f4,Wt)
cols=set(im.get_flattened_data()); assert cols<={K,Wt,Rd,Yl},cols
pal=Image.new("P",(1,1)); pal.putpalette([0,0,0,255,255,255,255,0,0,255,255,0]+[0]*(252*3))
im.quantize(palette=pal,dither=Image.Dither.NONE).save(os.path.join(OUT,"ezsign_densetext_400x300.png"),optimize=True)
print(y0,y1,yy,y2,len(cols))