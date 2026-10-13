#!/usr/bin/env python3
"""XenonOS logo SVGs: no font required, the letters are drawn with strokes."""
import sys, os

out = sys.argv[1]
os.makedirs(out, exist_ok=True)

LETTERS = {
    'X': [[(0, 0), (1, 1)], [(1, 0), (0, 1)]],
    'E': [[(1, 0), (0, 0), (0, 1), (1, 1)], [(0, .5), (.8, .5)]],
    'N': [[(0, 1), (0, 0), (1, 1), (1, 0)]],
    'O': [[(.2, 0), (.8, 0), (1, .2), (1, .8), (.8, 1), (.2, 1), (0, .8), (0, .2), (.2, 0)]],
    'S': [[(1, .14), (.85, 0), (.15, 0), (0, .15), (0, .35), (.2, .5), (.8, .5), (1, .65),
           (1, .85), (.85, 1), (.15, 1), (0, .86)]],
}


def word(text, x0, y0, w, h, gap, color, sw):
    parts = []
    x = x0
    for ch in text:
        for line in LETTERS[ch]:
            pts = ' '.join(f'{x + px * w:.1f},{y0 + py * h:.1f}' for px, py in line)
            parts.append(f'<polyline points="{pts}"/>')
        x += w + gap
    return (f'<g fill="none" stroke="{color}" stroke-width="{sw}" '
            f'stroke-linecap="round" stroke-linejoin="round">' + ''.join(parts) + '</g>')


def hexagon(cx, cy, r, color, sw, inner=True):
    import math
    def pts(rr):
        return ' '.join(f'{cx + rr * math.cos(math.radians(60 * i - 90)):.1f},'
                        f'{cy + rr * math.sin(math.radians(60 * i - 90)):.1f}' for i in range(6))
    s = (f'<polygon points="{pts(r)}" fill="none" stroke="{color}" stroke-width="{sw}" '
         f'stroke-linejoin="round"/>')
    if inner:
        s += (f'<polygon points="{pts(r * 0.55)}" fill="{color}" opacity="0.9"/>')
    return s


def logo(text_color, hex_color):
    w, h, gap = 14, 26, 6
    total = 7 * w + 6 * gap
    x0 = 190 - total - 2
    body = hexagon(25, 33, 21, hex_color, 4.5) + word('XENONOS', x0, 33 - h / 2, w, h, gap, text_color, 4.2)
    return ('<svg width="190" height="66" viewBox="0 0 190 66" xmlns="http://www.w3.org/2000/svg">'
            + body + '</svg>')


open(os.path.join(out, 'logo-light.svg'), 'w').write(logo('#0d2b3e', '#00a6c0'))
open(os.path.join(out, 'logo-dark.svg'), 'w').write(logo('#e6faff', '#00e5ff'))

# square icon (installer disk icon, 32x32)
icon = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="4" fill="#0d2b3e"/>'
        + hexagon(16, 16, 11, '#00e5ff', 2.4)
        + '</svg>')
open(os.path.join(out, 'icon.svg'), 'w').write(icon)
# symbols: app grid button etc. (GNOME recolors these)
sym = ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
       '<path fill="#bebebe" fill-rule="evenodd" d="M8 .8 14.2 4.4v7.2L8 15.2 1.8 11.6V4.4Z'
       'M8 3 12.3 5.5v5L8 13 3.7 10.5v-5Z"/><circle fill="#bebebe" cx="8" cy="8" r="1.6"/></svg>')
open(os.path.join(out, 'symbolic.svg'), 'w').write(sym)
# ---- app icons (128x128) ----
GRAD = ('<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#00e5ff"/>'
        '<stop offset="1" stop-color="#7c4dff"/></linearGradient></defs>')
BG = '<rect width="128" height="128" rx="26" fill="#0d2b3e"/>'


def svg128(body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="128" height="128" viewBox="0 0 128 128">{GRAD}{BG}{body}</svg>'


# Xenonium: star/sphere
xenonium = svg128(
    '<g fill="none" stroke="url(#g)" stroke-width="6" stroke-linecap="round">'
    '<circle cx="64" cy="64" r="40"/>'
    '<ellipse cx="64" cy="64" rx="17" ry="40"/>'
    '<path d="M24 64h80M31 42h66M31 86h66"/></g>'
    '<circle cx="64" cy="64" r="5" fill="#e6faff"/>')
# XenonPad: notepad
xenonpad = svg128(
    '<rect x="30" y="22" width="68" height="86" rx="9" fill="#e6faff"/>'
    '<rect x="30" y="22" width="68" height="18" rx="9" fill="url(#g)"/>'
    '<rect x="30" y="31" width="68" height="9" fill="url(#g)"/>'
    '<g stroke="#0d2b3e" stroke-width="5" stroke-linecap="round" opacity=".75">'
    '<path d="M42 56h44M42 70h44M42 84h30"/></g>'
    '<g fill="#e6faff"><circle cx="44" cy="22" r="4.5"/><circle cx="64" cy="22" r="4.5"/><circle cx="84" cy="22" r="4.5"/></g>')
# XenonWriter: page + W
xenonwriter = svg128(
    '<path d="M32 18h44l22 22v70a6 6 0 0 1-6 6H32a6 6 0 0 1-6-6V24a6 6 0 0 1 6-6z" fill="#e6faff"/>'
    '<path d="M76 18v22h22z" fill="url(#g)"/>'
    '<path d="M38 52l9 30 9-24 9 24 9-30" fill="none" stroke="url(#g)" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/>'
    '<g stroke="#0d2b3e" stroke-width="4.5" stroke-linecap="round" opacity=".6"><path d="M38 96h46M38 107h30"/></g>')
for name, svg in (('xenonium', xenonium), ('xenonpad', xenonpad), ('xenonwriter', xenonwriter)):
    open(os.path.join(out, name + '.svg'), 'w').write(svg)
print('logolar uretildi:', out)
