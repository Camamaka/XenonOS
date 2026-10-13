#!/usr/bin/env python3
"""XenonOS marka varliklari: her sey Xenon elementi (Xe, atom no 54) kimligiyle uretilir.

Xenon: atom numarasi 54, simge Xe, atom kutlesi 131.293, soy gaz (grup 18, periyot 5),
elektron dizilimi 2-8-18-18-8. Xenon lambasinin isimasi mavi-mor: marka renkleri bundan gelir.
"""
import os
import sys

A, Z, MASS = "Xe", 54, "131.293"
SHELLS = [2, 8, 18, 18, 8]
C1, C2, BG1, BG2, FG = "#6ee7ff", "#9b6bff", "#0b0720", "#1a0f45", "#f1ecff"   # mavi-mor isima

DEFS = (f'<defs>'
        f'<linearGradient id="gl" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C1}"/><stop offset="1" stop-color="{C2}"/></linearGradient>'
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{BG2}"/><stop offset="1" stop-color="{BG1}"/></linearGradient>'
        f'<radialGradient id="glow" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="{C2}" stop-opacity=".55"/><stop offset="1" stop-color="{C2}" stop-opacity="0"/></radialGradient>'
        f'</defs>')
FONT = "font-family=\"DejaVu Sans, Noto Sans, sans-serif\""


def tile(x, y, s, name=True):
    """Periyodik tablo karosu (Xe / 54). (x,y) sol ust, s kenar."""
    r = s * 0.1
    sw = max(2, s * 0.025)
    t = [f'<g transform="translate({x},{y})">',
         f'<rect width="{s}" height="{s}" rx="{r}" fill="url(#bg)" stroke="url(#gl)" stroke-width="{sw}"/>',
         f'<text x="{s*0.09}" y="{s*0.2}" {FONT} font-size="{s*0.14}" font-weight="700" fill="{C1}">{Z}</text>',
         f'<text x="{s*0.91}" y="{s*0.17}" {FONT} font-size="{s*0.085}" text-anchor="end" fill="{FG}" opacity=".6">{MASS}</text>',
         f'<text x="{s/2}" y="{s*0.64}" {FONT} font-size="{s*0.42}" font-weight="700" text-anchor="middle" fill="{FG}">{A}</text>']
    if name:
        t.append(f'<text x="{s/2}" y="{s*0.86}" {FONT} font-size="{s*0.12}" text-anchor="middle" letter-spacing="{s*0.02}" fill="{C1}">Xenon</text>')
    t.append('</g>')
    return "".join(t)


def shells(cx, cy, r0, dr, opacity=0.5, dots=True):
    """Elektron kabuklari: 2-8-18-18-8"""
    import math
    g = [f'<g fill="none" stroke="url(#gl)" stroke-width="2" opacity="{opacity}">']
    for i, n in enumerate(SHELLS):
        r = r0 + i * dr
        g.append(f'<circle cx="{cx}" cy="{cy}" r="{r}"/>')
    g.append('</g>')
    if dots:
        g.append(f'<g fill="{C1}" opacity="{min(1, opacity + .3)}">')
        for i, n in enumerate(SHELLS):
            r = r0 + i * dr
            for k in range(n):
                ang = 2 * math.pi * k / n + i * 0.7
                g.append(f'<circle cx="{cx + r * math.cos(ang):.1f}" cy="{cy + r * math.sin(ang):.1f}" r="{2.2 + (i == 4)}"/>')
        g.append('</g>')
    return "".join(g)


def svg(w, h, body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{DEFS}{body}</svg>'


def logo():           # yatay logo: karo + XENONOS
    return svg(640, 200,
               tile(10, 10, 180) +
               f'<text x="215" y="115" {FONT} font-size="78" font-weight="700" letter-spacing="8" fill="{FG}">XENON<tspan fill="url(#gl)">OS</tspan></text>'
               f'<text x="218" y="160" {FONT} font-size="22" letter-spacing="7" fill="{C1}" opacity=".85">ELEMENT 54  ·  Xe</text>')


def icon():           # kare simge (karo)
    return svg(256, 256, tile(8, 8, 240))


def wallpaper():
    return svg(1920, 1080,
               '<rect width="1920" height="1080" fill="url(#bg)"/>'
               '<circle cx="1360" cy="540" r="520" fill="url(#glow)"/>' +
               shells(1360, 540, 120, 70, 0.55) +
               tile(1250, 430, 220) +
               f'<text x="170" y="520" {FONT} font-size="150" font-weight="700" letter-spacing="10" fill="{FG}">XENON<tspan fill="url(#gl)">OS</tspan></text>'
               f'<text x="178" y="590" {FONT} font-size="34" letter-spacing="10" fill="{C1}" opacity=".9">THE NOBLE GAS OF OPERATING SYSTEMS</text>'
               f'<text x="178" y="650" {FONT} font-size="26" letter-spacing="6" fill="{FG}" opacity=".55">Xe · 54 · 131.293 · [Kr] 4d10 5s2 5p6</text>')


def app_icon(glyph):  # 128x128 uygulama simgesi (karo stili)
    return svg(128, 128,
               f'<rect width="128" height="128" rx="26" fill="url(#bg)" stroke="url(#gl)" stroke-width="3"/>'
               f'<text x="12" y="25" {FONT} font-size="17" font-weight="700" fill="{C1}">{Z}</text>'
               f'<text x="116" y="119" {FONT} font-size="15" font-weight="700" text-anchor="end" fill="{C2}">{A}</text>' + glyph)


GLYPHS = {
    "xenonium": ('<g fill="none" stroke="url(#gl)" stroke-width="5" stroke-linecap="round">'
                 '<circle cx="64" cy="66" r="31"/><ellipse cx="64" cy="66" rx="13" ry="31"/>'
                 '<path d="M33 66h62M39 49h50M39 83h50"/></g>'),
    "xenonpad": ('<rect x="38" y="34" width="52" height="66" rx="7" fill="#f1ecff"/>'
                 '<rect x="38" y="34" width="52" height="14" rx="7" fill="url(#gl)"/><rect x="38" y="41" width="52" height="7" fill="url(#gl)"/>'
                 '<g stroke="#1a0f45" stroke-width="4" stroke-linecap="round" opacity=".7"><path d="M47 62h34M47 74h34M47 86h22"/></g>'),
    "xenonwriter": ('<path d="M42 32h30l18 18v46a5 5 0 0 1-5 5H42a5 5 0 0 1-5-5V37a5 5 0 0 1 5-5z" fill="#f1ecff"/>'
                    '<path d="M72 32v18h18z" fill="url(#gl)"/>'
                    '<path d="M46 58l7 24 8-19 8 19 7-24" fill="none" stroke="url(#gl)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round"/>'),
}


def main(out):
    os.makedirs(out, exist_ok=True)
    files = {"xenonos-logo.svg": logo(), "xenonos-icon.svg": icon(), "xenonos-wallpaper.svg": wallpaper()}
    for k, g in GLYPHS.items():
        files[k + ".svg"] = app_icon(g)
    for name, content in files.items():
        with open(os.path.join(out, name), "w", encoding="utf-8") as f:
            f.write(content)
    print("marka dosyalari:", ", ".join(sorted(files)))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "brand-out")
