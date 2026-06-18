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
    g=f'<circle cx="140" cy="205" r="150" fill="none" stroke="#5a5a62" stroke-width="24"/>'
    g+=arc_arrow(140,140,86, -60, -60+min(150,t*0.9), ACC,4)
    return g
def L_inner(t):
    g=f'<circle cx="140" cy="140" r="118" fill="none" stroke="#3a3a42" stroke-width="3" stroke-dasharray="6 10"/>'
    g+=arc_arrow(140,140,86, 240, 240-min(150,t*0.9), "#5ac8fa",4)
    return g
def L_ring(t): return f'<circle cx="140" cy="140" r="112" fill="none" stroke="{WHITE}" stroke-width="22"/>'
def L_dot(t):
    a=math.radians(-90 + t)  # orbit from 12 o'clock, +t
    x=140+112*math.cos(a); y=140+112*math.sin(a)
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="26" fill="{RED}"/>'
def L_number(t):
    a=math.radians(-90 + t); x=140+112*math.cos(a); y=140+112*math.sin(a)
    return (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="26" fill="{RED}"/>'
            f'<text x="{x:.1f}" y="{y:.1f}" fill="#fff" font-family="-apple-system,sans-serif" font-size="26" font-weight="600" text-anchor="middle" dominant-baseline="central">17</text>')

LEVELS=[
 ("window","Window","crops the face", L_window),
 ("outer","Outer  +t","swings the ring’s centre", L_outer),
 ("inner","Inner  −t","un-spins, keeps the ring true", L_inner),
 ("ring","Ring","the track", L_ring),
 ("dot","Hand  +t","sweeps the minutes", L_dot),
 ("number","Number  −t","hour, kept upright", L_number),
]

# faithful assembled watch (iso + clip), scale k
def assembled(t, k):
    tt=t
    inner=f'''<g transform="rotate({tt} 140 140)"><g transform="translate(-140 140)"><g transform="rotate({-tt} 280 280)">
      <circle cx="280" cy="280" r="250" fill="none" stroke="{WHITE}" stroke-width="44"/>
      <g transform="rotate({tt} 280 30)"><circle cx="280" cy="30" r="45" fill="{RED}"/>
      <text x="280" y="30" transform="rotate({-tt} 280 30)" fill="#fff" font-family="-apple-system,sans-serif" font-size="40" font-weight="600" text-anchor="middle" dominant-baseline="central">17</text></g>
    </g></g></g>'''
    return (f'<g transform="scale({k})"><defs><clipPath id="win"><rect x="0" y="0" width="280" height="280" rx="56"/></clipPath></defs>'
            f'<rect x="0" y="0" width="280" height="280" rx="56" fill="#000" stroke="{LINE}"/>'
            f'<g clip-path="url(#win)">{inner}</g></g>')

Wn,Hn=1300,1320
E0=560; baseY=470; GAP=150
def frame(p):
    spin = p*720.0                      # 2 full turns over the loop -> seamless
    if p < 0.45:        spread=1.0; lab=1.0; asm=0.0
    elif p < 0.60:      u=(p-0.45)/0.15; spread=1-u; lab=1-u; asm=u
    elif p < 0.82:      spread=0.0; lab=0.0; asm=1.0
    else:               u=(p-0.82)/0.18; spread=u; lab=u; asm=1-u
    tt=(max(0.60,min(0.82,p))-0.60)/0.22*300.0   # watch ticks; starts dot-visible
    svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{Wn}" height="{Hn}" viewBox="0 0 {Wn} {Hn}">',
         f'<rect width="100%" height="100%" fill="{BG}"/>']
    svg.append(f'<text x="70" y="86" fill="{INK}" font-family="-apple-system,sans-serif" font-size="38" font-weight="700">Concentric</text>')
    svg.append(f'<text x="70" y="120" fill="{MUT}" font-family="-apple-system,sans-serif" font-size="19">A stack of layers that counter-rotate — +t, −t, +t, −t — then resolve into the watch.</text>')
    n=len(LEVELS)
    if spread>0.02:
        for i,(lid,title,sub,fn) in enumerate(LEVELS):
            z = (i-(n-1)/2)*GAP*spread
            F = baseY - z
            svg.append(f'<g transform="{iso(E0,F)}" opacity="{0.18+0.82*spread:.2f}">{fn(spin)}</g>')
            if lab>0.03:
                lc = projC(E0,F,252,28)            # right-ish point on the plate
                ty = lc[1]; tx=980
                svg.append(f'<line x1="{lc[0]:.0f}" y1="{ty:.0f}" x2="{tx-10:.0f}" y2="{ty:.0f}" stroke="{FAINT}" stroke-width="1" opacity="{lab:.2f}"/>')
                svg.append(f'<circle cx="{lc[0]:.0f}" cy="{ty:.0f}" r="2.5" fill="{FAINT}" opacity="{lab:.2f}"/>')
                svg.append(f'<text x="{tx}" y="{ty-3:.0f}" fill="{INK}" font-family="-apple-system,sans-serif" font-size="21" font-weight="600" opacity="{lab:.2f}">{title}</text>')
                svg.append(f'<text x="{tx}" y="{ty+19:.0f}" fill="{MUT}" font-family="-apple-system,sans-serif" font-size="15" opacity="{lab:.2f}">{sub}</text>')
    if asm>0.02:
        k=1.7; wpx=280*k
        tx=(Wn-wpx)/2; ty=180
        svg.append(f'<g transform="translate({tx:.0f} {ty:.0f})" opacity="{asm:.2f}">{assembled(tt, k)}</g>')
        svg.append(f'<text x="{Wn/2:.0f}" y="{ty+wpx+54:.0f}" fill="{INK}" font-family="-apple-system,sans-serif" font-size="23" font-weight="600" text-anchor="middle" opacity="{asm:.2f}">The crescent marks the minute; the hour rides up at the top of the hour, kept upright.</text>')
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
