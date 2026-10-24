import os
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","examples")
# Fonts: DejaVu Sans is bundled in fonts/ (Bitstream Vera licence); override with
# EZSIGN_FONT_REG / EZSIGN_FONT_BOLD / EZSIGN_FONT_DISPLAY. The display face falls
# back to DejaVu Bold when Inter is not installed.
_FONTS=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","fonts")
FONT_REG=os.environ.get("EZSIGN_FONT_REG") or os.path.join(_FONTS,"DejaVuSans.ttf")
FONT_BOLD=os.environ.get("EZSIGN_FONT_BOLD") or os.path.join(_FONTS,"DejaVuSans-Bold.ttf")
_INTER="/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf"
FONT_DISPLAY=os.environ.get("EZSIGN_FONT_DISPLAY") or (_INTER if os.path.exists(_INTER) else FONT_BOLD)
import math, numpy as np, qrcode, cv2
from PIL import Image, ImageDraw, ImageFont
W,H=400,300
K,Wt,Rd,Yl=(0,0,0),(255,255,255),(255,0,0),(255,255,0)
DJ=FONT_REG; DJB=FONT_BOLD
INT=FONT_DISPLAY
F=lambda p,s: ImageFont.truetype(p,s)
im=Image.new("RGB",(W,H),Wt); d=ImageDraw.Draw(im); d.fontmode="1"
def spaced(xy,txt,font,fill,sp=1,draw=True):
    x,y=xy
    for ch in txt:
        if draw: d.text((x,y),ch,font=font,fill=fill)
        x+=round(d.textlength(ch,font=font))+sp
    return x-sp
# --- QR (vCard) ---
VCARD="BEGIN:VCARD\nVERSION:3.0\nN:Gomez;Kevin\nFN:Kevin Gomez\nORG:Seagate Research Group\nTITLE:Technologist\nADR:;;;Shakopee;MN;;USA\nEND:VCARD"
qr=qrcode.QRCode(version=None,error_correction=qrcode.constants.ERROR_CORRECT_M,box_size=1,border=0)
qr.add_data(VCARD); qr.make(fit=True); m=np.array(qr.get_matrix()); M=3; qs=m.shape[0]*M
qx=W-28-qs; qy=28
for j in range(m.shape[0]):
    for i in range(m.shape[1]):
        if m[j,i]: d.rectangle([qx+i*M,qy+j*M,qx+i*M+M-1,qy+j*M+M-1],fill=K)
o=13; L=12   # corner brackets outside the quiet zone
for (cx,cy,sx,sy) in [(qx-o,qy-o,1,1),(qx+qs+o-1,qy-o,-1,1),(qx-o,qy+qs+o-1,1,-1),(qx+qs+o-1,qy+qs+o-1,-1,-1)]:
    d.rectangle(sorted([cx,cx+sx*L])[:1]+[min(cy,cy+sy)]+sorted([cx,cx+sx*L])[1:]+[max(cy,cy+sy)],fill=Rd)
    d.rectangle([min(cx,cx+sx),min(cy,cy+sy*L),max(cx,cx+sx),max(cy,cy+sy*L)],fill=Rd)
cap="SCAN TO SAVE CONTACT"; fc=F(DJB,8)
cw=spaced((0,0),cap,fc,K,1,draw=False)
spaced((round(qx+qs/2-cw/2),qy+qs+o+7),cap,fc,K,1)
f7=F(DJ,8)
for n,line in enumerate(["Tap a phone to update over NFC.","The image holds on screen with no power."]):
    lw=spaced((0,0),line,f7,K,0,draw=False); spaced((round(qx+qs/2-lw/2),qy+qs+o+23+n*11),line,f7,K,0)
# --- left band + text ---
d.rectangle([0,0,11,H],fill=Rd)
X=30
spaced((X,22),"SEAGATE RESEARCH GROUP",F(DJB,9),K,1)
d.rectangle([X,37,X+27,38],fill=Rd)
fn=F(INT,44)
d.text((X-2,44),"Kevin",font=fn,fill=K); d.text((X-2,88),"Gomez",font=fn,fill=K)
ft=F(DJB,10); tw=spaced((0,0),"TECHNOLOGIST",ft,K,2,draw=False)
d.rectangle([X,150,X+tw+15,167],fill=Yl); d.rectangle([X,150,X+3,167],fill=K)
spaced((X+10,153),"TECHNOLOGIST",ft,K,2)
fs=F(DJ,9)
for n,line in enumerate(["Photonics and Physical Intelligence","Shakopee, Minnesota  ·  USA"]):
    yy=198+n*16
    d.rectangle([X,yy+4,X+2,yy+6],fill=Rd)
    spaced((X+9,yy),line,fs,K,0)
# --- footer: guilloche + microtext ---
FY=250
d.rectangle([12,FY,W,H],fill=K)
for k in range(6):
    col=Yl if k%2 else Rd; prev=None
    for xx in range(12,W):
        yv=FY+14+8.5*math.sin(2*math.pi*(xx-12)/56+k*math.pi/3)*math.cos(2*math.pi*(xx-12)/388*1.0+k*0.9)
        p=(xx,int(round(yv)))
        if prev: d.line([prev,p],fill=col)
        prev=p
fm=F(DJ,8); mt='EZ Sign 4.2"  ·  400 × 300  ·  4-color e-paper  ·  NFC-powered, no battery'
mw=spaced((0,0),mt,fm,Wt,0,draw=False); spaced((W-14-mw,FY+33),mt,fm,Wt,0)
# --- checks + save ---
cols=set(im.get_flattened_data()); assert cols<={K,Wt,Rd,Yl},cols
pal=Image.new("P",(1,1)); pal.putpalette([0,0,0,255,255,255,255,0,0,255,255,0]+[0]*(252*3))
im.quantize(palette=pal,dither=Image.Dither.NONE).save(os.path.join(OUT,"ezsign_namecard_400x300.png"),optimize=True)
big=cv2.cvtColor(np.array(Image.open(os.path.join(OUT,"ezsign_namecard_400x300.png")).convert("RGB").resize((1200,900),Image.NEAREST)),cv2.COLOR_RGB2GRAY)
val,_,_=cv2.QRCodeDetector().detectAndDecode(big)
print("QR version",qr.version,"modules",m.shape[0],"px",qs,"at",qx,qy,"| decode ok:",val==VCARD,"| colors",len(cols))