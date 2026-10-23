import os
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","examples")
# Font paths: DejaVu (fonts-dejavu) and Inter (fonts-inter) on Debian/Ubuntu;
# override with EZSIGN_FONT_REG / EZSIGN_FONT_BOLD / EZSIGN_FONT_DISPLAY on other systems.
FONT_REG=os.environ.get("EZSIGN_FONT_REG","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD=os.environ.get("EZSIGN_FONT_BOLD","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
FONT_DISPLAY=os.environ.get("EZSIGN_FONT_DISPLAY","/usr/share/fonts/opentype/inter/InterDisplay-ExtraBold.otf")
import numpy as np, random
from PIL import Image, ImageDraw, ImageFont
W,H=400,300; BAR=18; SH=H-BAR; S=3; HOR=196
xs=(np.arange(W*S)+0.5)/S; ys=(np.arange(SH*S)+0.5)/S
x,y=np.meshgrid(xs,ys)
def vn(v,seed):
    r=np.random.default_rng(seed).random(4096)
    i=np.floor(v).astype(int); f=v-i; u=f*f*(3-2*f)
    return r[i%4096]*(1-u)+r[(i+1)%4096]*u
def ridge(v,seed,base,amp,freq,rough=0.52):
    h=np.zeros_like(v); a=1.0; tot=0
    for o in range(7):
        n=vn(v*freq*2**o+seed*17.3,seed*10+o)
        if o<2: n=1-np.abs(2*n-1)
        h+=a*n; tot+=a; a*=rough
    return base-amp*(h/tot)
# sky
t=np.clip(y/HOR,0,1)
ts=[0,0.15,0.42,0.66,0.84,1.0]
r=np.interp(t,ts,[0,0.06,0.50,1.0,1.0,1.0]); g=np.interp(t,ts,[0,0,0,0.10,0.48,0.82]); b=np.interp(t,ts,[0,0,0,0,0,0.08])
cx,cy,R=200,126,50
d=np.hypot(x-cx,y-cy)
gl=np.exp(-(d/95)**2)
r=r+gl*0.55; g=g+np.exp(-(d/72)**2)*0.42*np.clip(r,0,1)
# cloud streaks
for (y0,x0,wd,th,ph) in [(60,120,150,3.2,0.3),(74,300,120,2.4,1.9),(92,70,90,2.0,4.0),(101,215,170,3.0,2.2),(118,330,110,2.6,5.1),(136,150,140,2.2,0.9),(46,260,90,1.6,3.3)]:
    env=np.exp(-((x-x0)/wd)**2)
    thick=th*env*(0.55+0.45*np.sin(x/19+ph)+0.25*np.sin(x/7.3+ph*2))
    yc=y0+2.2*np.sin(x/41+ph)
    m=np.clip((thick-np.abs(y-yc))*1.5,0,1)
    under=np.clip((thick+1.2-(y-yc))*1.5,0,1)*(y>yc)*(1-m)   # lit underside
    r=r*(1-m)+0.42*m; g=g*(1-m)+0.0*m; b=b*(1-m)
    g=g+under*0.25*env; 
# sun disc
sm=np.clip((R-d)*1.2,0,1)
sg=1-0.38*np.clip((y-cy)/R,0,1)**1.5
sb=np.clip(1-d/(R*0.85),0,1)**0.8*0.95*np.clip(1-(y-cy)/R,0,1)
# keep streaks over the sun as darker orange bands
band=np.clip(0.75-r,0,1)*2
sr=np.ones_like(r); sgg=sg*(1-0.55*band); sbb=sb*(1-band)
r=r*(1-sm)+sr*sm; g=g*(1-sm)+sgg*sm; b=b*(1-sm)+sbb*sm
img=np.stack([r,g,b],-1)
# mountains
dip=1-0.45*np.exp(-((xs-205)/75)**2)
layers=[(3,186,74,1/105,(0.93,0.30,0.0),(0.07,0.22,0.0)),
        (8,191,54,1/78,(0.62,0.02,0.0),(0.22,0.06,0.0)),
        (5,195,32,1/52,(0.30,0.0,0.0),(0.18,0.0,0.0)),
        (9,198,17,1/34,(0.05,0.0,0.0),(0.05,0.0,0.0))]
for seed,base,amp,fr,col,haze in layers:
    rg=ridge(xs,seed,base,amp*dip,fr)[None,:]
    m=np.clip((y-rg)*S*0.5+0.5,0,1)[...,None]
    tt=np.clip((y-rg)/np.maximum(HOR-rg,1),0,1)[...,None]
    c=np.array(col)[None,None,:]+np.array(haze)[None,None,:]*tt
    img=img*(1-m)+c*m
# water
rows=np.arange(SH*S); wr=rows[rows>=HOR*S]
dy=(wr-HOR*S+0.5)/S
src=np.clip(((HOR-0.8-dy*1.95)*S).astype(int),0,HOR*S-1)
DY=dy[:,None]; X=xs[None,:]
dx=((1.0+DY*0.07)*np.sin(DY*1.9+X*0.06)+ (0.6+DY*0.03)*np.sin(DY*3.7-X*0.021))*S
cols=np.clip((np.arange(W*S)[None,:]+dx).astype(int),0,W*S-1)
ref=img[src[:,None],cols]
stripe=0.5+0.5*np.sin(7.5*np.sqrt(DY*4+1)+2.0*np.sin(X*0.045+DY*0.21)+1.3*np.sin(X*0.11-DY*0.13)+3*vn(X*0.09+DY*0.05,77))
water=ref*(0.40+0.55*stripe[...,None])
gw=np.exp(-((X-cx-1.5*np.sin(DY*0.9))/(5+DY*0.17))**2)*np.clip(1.1-DY/110,0,1)
water[...,0]=np.maximum(water[...,0],gw*0.75)
k=np.clip(np.clip((stripe-0.58)*6,0,1)*gw*1.6,0,1)[...,None]
water=water*(1-k)+np.array([1.0,0.93,0.35])[None,None,:]*k
img[HOR*S:]=water
# downsample, clamp to palette hull (r>=g>=b)
a=img.reshape(SH,S,W,S,3).mean((1,3)).clip(0,1)
a[...,1]=np.minimum(a[...,1],a[...,0]); a[...,2]=np.minimum(a[...,2],a[...,1])
PAL=[(0,0,0),(1,1,1),(1,0,0),(1,1,0)]
# Floyd-Steinberg, serpentine
a=a+np.random.default_rng(1).uniform(-0.035,0.035,a.shape[:2])[...,None]*(a.max(-1,keepdims=True)>0.03)
buf=a.tolist(); out=np.zeros((SH,W),np.uint8)
for j in range(SH):
    rng=range(W) if j%2==0 else range(W-1,-1,-1); sd=1 if j%2==0 else -1
    row=buf[j]; nxt=buf[j+1] if j+1<SH else None
    for i in rng:
        pr,pg,pb=row[i]
        pr=min(1.25,max(-0.25,pr)); pg=min(1.25,max(-0.25,pg)); pb=min(1.25,max(-0.25,pb))
        best=0; bd=9
        for n,(qr,qg,qb) in enumerate(PAL):
            dd=(pr-qr)**2+(pg-qg)**2+(pb-qb)**2
            if dd<bd: bd=dd; best=n
        out[j,i]=best; qr,qg,qb=PAL[best]; er,eg,eb=pr-qr,pg-qg,pb-qb
        def add(p,w):
            p[0]+=er*w; p[1]+=eg*w; p[2]+=eb*w
        if 0<=i+sd<W: add(row[i+sd],7/16)
        if nxt is not None:
            if 0<=i-sd<W: add(nxt[i-sd],3/16)
            add(nxt[i],5/16)
            if 0<=i+sd<W: add(nxt[i+sd],1/16)
K,Wt,Rd,Yl=(0,0,0),(255,255,255),(255,0,0),(255,255,0)
lut=np.array([K,Wt,Rd,Yl],np.uint8)
im=Image.new("RGB",(W,H),Wt); im.paste(Image.fromarray(lut[out]),(0,0))
px=im.load(); d=ImageDraw.Draw(im); d.fontmode="1"
random.seed(4)
# stars
for _ in range(150):
    sx=random.randrange(W); sy=int(random.random()**1.7*80)
    if px[sx,sy] in (K,Rd) and np.hypot(sx-cx,sy-cy)>R+6:
        px[sx,sy]=Wt
        if random.random()<0.10:
            for ddx,ddy in((1,0),(-1,0),(0,1),(0,-1)):
                if 0<=sx+ddx<W and 0<=sy+ddy<SH: px[sx+ddx,sy+ddy]=Wt
# birds
for bx,by in [(243,104),(256,97),(266,108),(231,114),(150,70)]:
    for ddx,ddy in [(-3,0),(-2,-1),(-1,-1),(0,0),(1,-1),(2,-1),(3,0)]: px[bx+ddx,by+ddy]=K
# banks + pines
def bankL(v): return 250+(v/150)**1.6*34
def bankR(v): return 266+((W-v)/95)**1.5*18
for v in range(0,151):
    d.line([(v,int(bankL(v))),(v,SH)],fill=K)
    if random.random()<0.5: d.line([(v,int(bankL(v))-random.randint(1,5)),(v,int(bankL(v)))],fill=K)
for v in range(305,W):
    d.line([(v,int(bankR(v))),(v,SH)],fill=K)
    if random.random()<0.5: d.line([(v,int(bankR(v))-random.randint(1,4)),(v,int(bankR(v)))],fill=K)
def pine(px0,base,h):
    top=base-h
    for yy in range(top,base-3):
        f=(yy-top)/h
        w=f*h*0.24*(0.45+0.55*((yy-top)%7)/7)+random.choice([0,0,1])
        d.line([(px0-int(w),yy),(px0+int(w+0.5),yy)],fill=K)
    d.line([(px0,top-2),(px0,base)],fill=K)
for px0,h in [(9,80),(23,58),(36,96),(52,52),(67,72),(85,42),(101,30),(118,20)]: pine(px0,int(bankL(px0))+2,h)
for px0,h in [(392,50),(377,36),(361,24),(346,14)]: pine(px0,int(bankR(px0))+2,h)
# caption bar
d.rectangle([0,SH,W,H],fill=Wt); d.line([(0,SH),(W,SH)],fill=K)
for i,c in enumerate([K,Rd,Yl,Wt]):
    d.rectangle([5+i*13,SH+4,5+i*13+10,SH+14],fill=c,outline=K)
f=ImageFont.truetype(FONT_BOLD,10)
txt="EZ SIGN 4.2\"  ·  400 x 300  ·  4-COLOR  ·  NFC"
d.text((W-5-d.textlength(txt,font=f),SH+3),txt,font=f,fill=K)
cols=set(im.get_flattened_data()); assert cols<={K,Wt,Rd,Yl},cols
pal=Image.new("P",(1,1)); pal.putpalette([0,0,0,255,255,255,255,0,0,255,255,0]+[0]*(252*3))
im.quantize(palette=pal,dither=Image.Dither.NONE).save(os.path.join(OUT,"ezsign_fine_400x300.png"),optimize=True)
print(im.size,len(cols))