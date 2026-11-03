"""Nexora 'Kids & Families' cast: 6 original drawn cartoon kids (one per inhabited continent), as inline SVG.
Original designs: simple round shapes, no likeness of any real child, person or known cartoon character.
Used by reels3.py when a segment has "cast": "<name>" (the kid replaces the emoji, and blinks + bobs).
"""
CAST = {
    # name: home, skin, hair colour, hair style, shirt colour, accessory
    'amani': {'home': 'Mombasa, Kenya', 'continent': 'Africa', 'skin': '#7A4A2C', 'hair': '#1B1210', 'style': 'puffs', 'shirt': '#FFB547', 'acc': 'none'},
    'priya': {'home': 'Jaipur, India', 'continent': 'Asia', 'skin': '#B07A52', 'hair': '#1E1512', 'style': 'braid', 'shirt': '#FF6FA8', 'acc': 'bindi'},
    'luka': {'home': 'Zagreb, Croatia', 'continent': 'Europe', 'skin': '#F2C9A8', 'hair': '#C98A3A', 'style': 'spiky', 'shirt': '#4FA3FF', 'acc': 'freckles'},
    'maya': {'home': 'Toronto, Canada', 'continent': 'North America', 'skin': '#D9A27A', 'hair': '#3B2416', 'style': 'pony', 'shirt': '#46D7B5', 'acc': 'glasses'},
    'bia': {'home': 'Salvador, Brazil', 'continent': 'South America', 'skin': '#9C6644', 'hair': '#2A1A12', 'style': 'curls', 'shirt': '#FFE14D', 'acc': 'none'},
    'nikau': {'home': 'Rotorua, New Zealand', 'continent': 'Oceania', 'skin': '#A86F48', 'hair': '#141010', 'style': 'short', 'shirt': '#22C55E', 'acc': 'none'},
}

def _hair(style, c):
    if style == 'puffs':
        return (f'<circle cx="62" cy="62" r="34" fill="{c}"/><circle cx="198" cy="62" r="34" fill="{c}"/>'
                f'<path d="M58 118 Q60 52 130 48 Q200 52 202 118 Q170 84 130 86 Q90 84 58 118Z" fill="{c}"/>', '')
    if style == 'braid':
        back = (f'<path d="M190 120 Q228 170 214 236" stroke="{c}" stroke-width="26" fill="none" stroke-linecap="round"/>'
                f'<circle cx="214" cy="244" r="12" fill="#FF6FA8"/>')
        return (f'<path d="M54 128 Q52 46 130 44 Q208 46 206 128 Q196 92 130 82 Q64 92 54 128Z" fill="{c}"/>', back)
    if style == 'spiky':
        return (f'<path d="M56 116 L62 66 L88 80 L100 44 L122 72 L140 40 L156 72 L178 48 L186 82 L206 70 L204 116 Q130 84 56 116Z" fill="{c}"/>', '')
    if style == 'pony':
        back = f'<ellipse cx="216" cy="120" rx="26" ry="46" fill="{c}" transform="rotate(20 216 120)"/>'
        return (f'<path d="M54 124 Q52 48 130 44 Q208 48 206 124 Q178 80 120 84 Q78 88 54 124Z" fill="{c}"/>', back)
    if style == 'curls':
        dots = ''.join(f'<circle cx="{x}" cy="{y}" r="24" fill="{c}"/>' for x, y in
                       [(60, 110), (66, 74), (92, 52), (130, 42), (168, 52), (194, 74), (200, 110), (48, 146), (212, 146)])
        return (dots, '')
    return (f'<path d="M58 118 Q56 52 130 50 Q204 52 202 118 Q176 90 130 90 Q84 90 58 118Z" fill="{c}"/>', '')

def kid_svg(name, size=330):
    k = CAST[name.lower()]
    front, back = _hair(k['style'], k['hair'])
    acc = ''
    if k['acc'] == 'glasses':
        acc = ('<g fill="none" stroke="#0B1026" stroke-width="6"><circle cx="102" cy="138" r="22"/><circle cx="158" cy="138" r="22"/>'
               '<path d="M124 138 L136 138"/></g>')
    elif k['acc'] == 'freckles':
        acc = ''.join(f'<circle cx="{x}" cy="{y}" r="3.5" fill="#B5734A" opacity=".7"/>' for x, y in [(90, 166), (100, 172), (82, 174), (170, 166), (160, 172), (178, 174)])
    elif k['acc'] == 'bindi':
        acc = '<circle cx="130" cy="112" r="5" fill="#E0245E"/>'
    return f'''<svg class="kid" viewBox="0 0 260 300" width="{size}" height="{size*300//260}" xmlns="http://www.w3.org/2000/svg">
<g>{back}
<path d="M58 300 Q58 220 130 220 Q202 220 202 300Z" fill="{k['shirt']}"/>
<rect x="114" y="196" width="32" height="34" rx="12" fill="{k['skin']}"/>
<circle cx="52" cy="146" r="18" fill="{k['skin']}"/><circle cx="208" cy="146" r="18" fill="{k['skin']}"/>
<circle cx="130" cy="136" r="80" fill="{k['skin']}"/>
{front}
<g class="eyes"><ellipse cx="102" cy="140" rx="10" ry="13" fill="#0B1026"/><ellipse cx="158" cy="140" rx="10" ry="13" fill="#0B1026"/>
<circle cx="105" cy="135" r="3.5" fill="#fff"/><circle cx="161" cy="135" r="3.5" fill="#fff"/></g>
<circle cx="84" cy="168" r="11" fill="#FF7A9C" opacity=".45"/><circle cx="176" cy="168" r="11" fill="#FF7A9C" opacity=".45"/>
<path d="M108 174 Q130 198 152 174" stroke="#0B1026" stroke-width="7" fill="#fff" stroke-linecap="round" stroke-linejoin="round"/>
{acc}</g></svg>'''

if __name__ == '__main__':
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else 'cast.html'
    cells = ''.join(f'<div style="text-align:center;color:#fff;font:800 34px Inter,sans-serif">{kid_svg(n, 300)}<div>{n.title()}</div>'
                    f'<div style="font:600 24px Inter,sans-serif;color:#A9B4D6">{v["home"]}<br>{v["continent"]}</div></div>' for n, v in CAST.items())
    open(out, 'w').write(f'<html><body style="margin:0;background:#0B1026;width:1080px;padding:60px 0;display:grid;grid-template-columns:repeat(3,1fr);gap:50px">{cells}</body></html>')
