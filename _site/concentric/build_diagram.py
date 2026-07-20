import math, io, cairosvg
from PIL import Image

BG="#0d0d0f"; INK="#f3f1ea"; MUT="#8a8a93"; FAINT="#3a3a42"
ACC="#ff5c38"; RED="#ff3b30"; WHITE="#e6e6e6"; LINE="#2c2c33"
C=math.cos(math.radians(30)); S=math.sin(math.radians(30))
def iso(E,F): return f"matrix({C:.4f},{S:.4f},{-C:.4f},{S:.4f},{E},{F})"
def projC(E,F,lx,ly): return (E + C*lx - C*ly, F + S*lx + S*ly)  # local->screen
L=280; CX=140; CY=140

def arc_arrow(cx,cy,r,a0,a1,col,w=4):
    # curved arrow from angle a0 to a1 (deg), with arrowhead at a1
    def pt(a):
        ra=math.radians(a); return (cx+r*math.cos(ra), cy+r*math.sin(ra))
    x0,y0=pt(a0); x1,y1=pt(a1)
    large=1 if abs(a1-a0)>180 else 0
    sweep=1 if a1>a0 else 0
    # arrowhead
    ah=math.radians(a1); tx,ty=math.cos(ah+ (math.pi/2 if sweep else -math.pi/2)), math.sin(ah+(math.pi/2 if sweep else -math.pi/2))
    h=9
    p1=(x1+tx*h - math.cos(ah)*h, y1+ty*h - math.sin(ah)*h)
    p2=(x1-tx*h - math.cos(ah)*h, y1-ty*h - math.sin(ah)*h)
    return (f'<path d="M{x0:.1f} {y0:.1f} A{r} {r} 0 {large} {sweep} {x1:.1f} {y1:.1f}" fill="none" stroke="{col}" stroke-width="{w}"/>'
            f'<path d="M{x1:.1f} {y1:.1f} L{p1[0]:.1f} {p1[1]:.1f} M{x1:.1f} {y1:.1f} L{p2[0]:.1f} {p2[1]:.1f}" stroke="{col}" stroke-width="{w}" fill="none" stroke-linecap="round"/>')

# ---- level drawers (flat 280 box) ----
def L_window(t): return f'<rect x="22" y="22" width="236" height="236" rx="48" fill="#0a0a0c" stroke="{FAINT}" stroke-width="2"/>'
def L_outer(t):
    g=f'<g transform="rotate({t} 140 140)"><circle cx="140" cy="215" r="150" fill="none" stroke="#5a5a62" stroke-width="24"/></g>'
    g+=arc_arrow(140,140,86, -60, -60+min(150,t*0.9), ACC,4)
    return g
def L_inner(t):
    g=f'<circle cx="140" cy="140" r="118" fill="none" stroke="#3a3a42" stroke-width="3" stroke-dasharray="6 10"/>'
    g+=arc_arrow(140,140,86, 240, 240-min(150,t*0.9), "#5ac8fa",4)
    return g
def L_ring(t): return f'<circle cx="140" cy="140" r="112" fill="none" stroke="{WHITE}" stroke-width="22"/>'
def L_dot(t):
    a=math.radians(-90+t); x=140+112*math.cos(a); y=140+112*math.sin(a)
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="26" fill="{RED}"/>'
def L_number(t):
    a=math.radians(-90+t); x=140+112*math.cos(a); y=140+112*math.sin(a)
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="26" fill="{RED}"/>'
            f'<text x="{x:.1f}" y="{y:.1f}" fill="#fff" font-family="-apple-system,sans-serif" font-size="26" font-weight="600" text-anchor="middle" dominant-baseline="central">17</text>')

LEVELS=[
 ("window","Window","crops the face", L_window),
 ("outer","Outer  +t","sweeps the crop", L_outer),
 ("inner","Inner  −t","keeps the ring true", L_inner),
 ("ring","Ring","the track", L_ring),
 ("dot","Dot  +t","rides once an hour = minute", L_dot),
 ("number","Number  −t","the hour, upright", L_number),
]

# faithful assembled watch (iso + clip), scale k
def assembled(t, k):
    ring=f'<g transform="rotate({t} 140 140)"><g transform="translate(-140 140)"><circle cx="280" cy="280" r="250" fill="none" stroke="{WHITE}" stroke-width="44"/></g></g>'
    dot=f'<circle cx="140" cy="140" r="46" fill="{RED}"/><text x="140" y="140" fill="#fff" font-family="-apple-system,sans-serif" font-size="42" font-weight="600" text-anchor="middle" dominant-baseline="central">17</text>'
    return (f'<g transform="scale({k})"><defs><clipPath id="win"><rect x="0" y="0" width="280" height="280" rx="56"/></clipPath></defs>'
            f'<rect x="0" y="0" width="280" height="280" rx="56" fill="#000" stroke="{LINE}"/>'
            f'<g clip-path="url(#win)">{ring}</g>{dot}</g>')

Wn,Hn=1300,1320
E0=560; baseY=470; GAP=150
def frame(p):
    spin = p*720.0                       # 2 turns over the loop -> seamless
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wn}" height="{Hn}" viewBox="0 0 {Wn} {Hn}">',
         f'<rect width="100%" height="100%" fill="{BG}"/>']
    svg.append(f'<text x="70" y="86" fill="{INK}" font-family="-apple-system,sans-serif" font-size="38" font-weight="700">Concentric</text>')
    svg.append(f'<text x="70" y="120" fill="{MUT}" font-family="-apple-system,sans-serif" font-size="19">Six layers, counter-rotating — +t, −t, +t, −t. The spins cancel where they should, survive where they shouldn\'t.</text>')
    n=len(LEVELS)
    for i,(lid,title,sub,fn) in enumerate(LEVELS):
        z = (i-(n-1)/2)*GAP
        F = baseY - z
        svg.append(f'<g transform="{iso(E0,F)}">{fn(spin)}</g>')
        lc = projC(E0,F,252,28); tx=980
        svg.append(f'<line x1="{lc[0]:.0f}" y1="{lc[1]:.0f}" x2="{tx-10:.0f}" y2="{lc[1]:.0f}" stroke="{FAINT}" stroke-width="1"/>')
        svg.append(f'<circle cx="{lc[0]:.0f}" cy="{lc[1]:.0f}" r="2.5" fill="{FAINT}"/>')
        svg.append(f'<text x="{tx}" y="{lc[1]-3:.0f}" fill="{INK}" font-family="-apple-system,sans-serif" font-size="21" font-weight="600">{title}</text>')
        svg.append(f'<text x="{tx}" y="{lc[1]+19:.0f}" fill="{MUT}" font-family="-apple-system,sans-serif" font-size="15">{sub}</text>')
    svg.append('</svg>')
    return "\n".join(svg)

def png(svg,w): return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=w, output_height=int(w*Hn/Wn)))).convert("RGB")

# static = exploded hold
cairosvg.svg2png(bytestring=frame(0.2).encode(), write_to="/tmp/clock-static.png", output_width=2*Wn, output_height=2*Hn)
N=48
frames=[png(frame(i/N), 1000) for i in range(N)]
frames[0].save("/tmp/clock-anim.gif", save_all=True, append_images=frames[1:], duration=80, loop=0, optimize=True, disposal=2)
import os
print("static", os.path.getsize("/tmp/clock-static.png"), "gif", os.path.getsize("/tmp/clock-anim.gif"))
