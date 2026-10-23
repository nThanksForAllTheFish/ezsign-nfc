import os
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","examples")
# Font paths: DejaVu (fonts-dejavu) and Inter (fonts-inter) on Debian/Ubuntu;
# override with EZSIGN_FONT_REG / EZSIGN_FONT_BOLD / EZSIGN_FONT_DISPLAY on other systems.
FONT_REG=os.environ.get("EZSIGN_FONT_REG","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD=os.environ.get("EZSIGN_FONT_BOLD","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
FONT_DISPLAY=os.environ.get("EZSIGN_FONT_DISPLAY","/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf")
from PIL import Image, ImageDraw, ImageFont
import random, math
W,H=400,300
K=(0,0,0); Wt=(255,255,255); R=(255,0,0); Y=(255,255,0)
B8=[[0,32,8,40,2,34,10,42],[48,16,56,24,50,18,58,26],[12,44,4,36,14,46,6,38],[60,28,52,20,62,30,54,22],
    [3,35,11,43,1,33,9,41],[51,19,59,27,49,17,57,25],[15,47,7,39,13,45,5,37],[63,31,55,23,61,29,53,21]]
def dith(x,y,t,a,b):  # t in 0..1 -> fraction of b
    return b if t*64 > B8[y%8][x%8]+0.5 else a
img=Image.new("RGB",(W,H),K); px=img.load()
HOR=206; BAR=272
# sky: black -> red
for y in range(HOR):
    t=min(1,max(0,(y-10)/150))**1.15
    for x in range(W): px[x,y]=dith(x,y,t,K,R)
# stars
random.seed(7)
for _ in range(70):
    x=random.randrange(W); y=int(random.random()**1.6*95)
    px[x,y]=Wt
    if random.random()<0.18:
        for dx,dy in((1,0),(-1,0),(0,1),(0,-1)):
            if 0<=x+dx<W and 0<=y+dy<H: px[x+dx,y+dy]=Wt
# sun
cx,cy,r=200,122,80
slits=[(cy+6,2),(cy+20,3),(cy+34,4),(cy+47,5),(cy+60,6),(cy+72,7)]
for y in range(cy-r,min(HOR,cy+r+1)):
    if any(s<=y<s+h for s,h in slits): continue
    for x in range(cx-r,cx+r+1):
        if (x-cx)**2+(y-cy)**2<=r*r:
            t=min(1,max(0,(y-(cy-r+25))/(1.5*r)))
            px[x,y]=dith(x,y,t,Y,Wt)
d=ImageDraw.Draw(img); d.fontmode="1"
# ridges
def ridge(seed,base,amp,step):
    random.seed(seed); pts=[]; x=-step; y=base
    while x<=W+step:
        y=base-random.random()*amp; pts.append((x,y)); x+=step*(0.6+random.random()*0.8)
    return pts
def fill_ridge(pts,fn):
    for i in range(len(pts)-1):
        (x0,y0),(x1,y1)=pts[i],pts[i+1]
        for x in range(max(0,int(x0)),min(W,int(x1)+1)):
            if x1==x0: continue
            yy=int(y0+(y1-y0)*(x-x0)/(x1-x0))
            for y in range(max(0,yy),HOR): px[x,y]=fn(x,y,yy)
fill_ridge(ridge(3,188,48,34),lambda x,y,yy: Y if y==yy else ((K if (x+y)%2 else R)))
fill_ridge(ridge(11,200,30,22),lambda x,y,yy: K)
# ground + grid
d.rectangle([0,HOR,W,BAR],fill=K)
for i in range(-26,27):
    d.line([(200+i*9,HOR),(200+i*62,BAR)],fill=R)
y=HOR; k=0
while y<BAR:
    d.line([(0,int(y)),(W,int(y))],fill=Y); k+=1; y=HOR+3+(k**1.8)*2.4
d.line([(0,HOR),(W,HOR)],fill=Wt)
# caption bar
d.rectangle([0,BAR,W,H],fill=Wt); d.line([(0,BAR),(W,BAR)],fill=K)
sw=[(K,),(R,),(Y,),(Wt,)]
for i,(c,) in enumerate(sw):
    x0=8+i*22; d.rectangle([x0,BAR+6,x0+17,BAR+23],fill=c,outline=K)
f=ImageFont.truetype(FONT_BOLD,13)
txt="400 x 300  ·  NFC  ·  NO BATTERY"
tw=d.textlength(txt,font=f)
d.text((W-8-tw,BAR+7),txt,font=f,fill=K)
# verify palette
cols=set(img.get_flattened_data()); assert cols<= {K,Wt,R,Y},cols
pal=Image.new("P",(1,1)); pal.putpalette([0,0,0,255,255,255,255,0,0,255,255,0]+[0]*(252*3))
out=img.quantize(palette=pal,dither=Image.Dither.NONE)
out.save(os.path.join(OUT,"ezsign_demo_400x300.png"),optimize=True)
print(img.size,len(cols))