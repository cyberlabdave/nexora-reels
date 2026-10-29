#!/usr/bin/env python3
"""Nexora reel renderer v2: AI voiceover (Kokoro, open source) + original music + animated visuals.
Usage: python3 reels2.py spec.json out.mp4 --style chat|kinetic|steps [--voice 1]
spec: {"series":"Prompt Drop #06","segments":[{"say":"...","kind":"hook|line|prompt|reply|cta","text":"optional on-screen text"}]}
"""
import json, math, os, subprocess, sys, wave, argparse, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
TTS_BIN = os.environ.get('NX_TTS_DIR', os.path.join(HERE, 'sherpa-onnx-v1.12.20-linux-x64-shared'))
KOKORO = os.environ.get('NX_KOKORO_DIR', os.path.join(HERE, 'kokoro-en-v0_19'))
F = '/usr/share/fonts/opentype/inter/'
def font(w, s):
    name = {'black': 'Inter-Black.otf', 'xb': 'Inter-ExtraBold.otf', 'b': 'Inter-Bold.otf', 'sb': 'Inter-SemiBold.otf', 'm': 'Inter-Medium.otf'}[w]
    p = F + name
    if not os.path.exists(p): p = '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf'
    return ImageFont.truetype(p, s)
MONO = lambda s: ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf', s)
EMOJI_FONT = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'
_emo = {}
def emoji(ch, size):
    k = (ch, size)
    if k not in _emo:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        im = Image.new('RGBA', (140, 140), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((6, 6), ch, font=f, embedded_color=True)
        im = im.crop(im.getbbox() or (0, 0, 1, 1)).resize((size, size), Image.LANCZOS)
        _emo[k] = im
    return _emo[k]

# palette (Nexora brand)
BG1, BG2 = (14, 20, 32), (21, 29, 44)
MINT, CORAL, INK, PAPER, MUTED = (70, 215, 181), (255, 122, 102), (233, 238, 245), (255, 253, 248), (147, 160, 180)

# ---------------- audio ----------------
def tts(text, path, sid):
    env = dict(os.environ, LD_LIBRARY_PATH=os.path.join(TTS_BIN, 'lib'))
    subprocess.run([os.path.join(TTS_BIN, 'bin', 'sherpa-onnx-offline-tts'), f'--kokoro-model={KOKORO}/model.onnx', f'--kokoro-voices={KOKORO}/voices.bin',
                    f'--kokoro-tokens={KOKORO}/tokens.txt', f'--kokoro-data-dir={KOKORO}/espeak-ng-data', '--num-threads=4', f'--sid={sid}', '--kokoro-length-scale=0.92',
                    f'--output-filename={path}', text], check=True, env=env, capture_output=True)
    with wave.open(path) as w:
        sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    return a, sr

def music(dur, sr, seed=7):
    """Original procedural lo-fi bed: soft chord pad + kick + hats. Written by us, no samples, no copyright."""
    rng = np.random.default_rng(seed); n = int(dur * sr); t = np.arange(n) / sr; out = np.zeros(n, np.float32)
    bpm = 96; beat = 60 / bpm
    prog = [[57, 60, 64, 67], [53, 57, 60, 64], [55, 59, 62, 65], [52, 55, 59, 62]]  # Am7 Fmaj7 G7-ish Em7
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    bar = beat * 4
    for i in range(int(dur / bar) + 1):
        s0 = int(i * bar * sr); s1 = min(n, int((i + 1) * bar * sr))
        if s0 >= n: break
        tt = np.arange(s1 - s0) / sr; env = np.minimum(1, tt / 0.4) * np.exp(-tt / 3.5)
        for m in prog[i % 4]:
            f = hz(m); out[s0:s1] += 0.05 * env * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt + 0.3))
        f = hz(prog[i % 4][0] - 24); out[s0:s1] += 0.10 * env * np.sin(2 * np.pi * f * tt)
    for k in range(int(dur / beat) + 1):
        s0 = int(k * beat * sr)
        if s0 >= n: break
        L = min(n - s0, int(0.25 * sr)); tt = np.arange(L) / sr
        if k % 2 == 0:  # kick
            out[s0:s0 + L] += 0.35 * np.sin(2 * np.pi * (50 + 90 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 12)
        else:  # soft snare-ish noise
            out[s0:s0 + L] += 0.06 * rng.standard_normal(L) * np.exp(-tt * 18)
        h0 = int((k + 0.5) * beat * sr); Lh = min(n - h0, int(0.05 * sr))
        if Lh > 0: out[h0:h0 + Lh] += 0.025 * rng.standard_normal(Lh) * np.exp(-np.arange(Lh) / sr * 80)
    k = int(0.02 * sr); out = np.convolve(out, np.ones(3) / 3, mode='same')  # tiny lowpass
    fade = int(0.8 * sr); out[:fade] *= np.linspace(0, 1, fade); out[-fade:] *= np.linspace(1, 0, fade)
    return out / (np.abs(out).max() + 1e-6)

def build_audio(segs, sid, tmp):
    parts, timeline, cur, sr = [], [], 0.15, 24000
    for i, s in enumerate(segs):
        a, sr = tts(s['say'], os.path.join(tmp, f'seg{i}.wav'), sid)
        a = a[int(0.02 * sr):]
        nz = np.where(np.abs(a) > 0.01)[0]
        if len(nz): a = a[max(0, nz[0] - 200): nz[-1] + 1200]
        d = len(a) / sr; timeline.append((cur, cur + d)); parts.append((cur, a)); cur += d + (0.35 if s.get('kind') != 'prompt' else 0.5)
    total = cur + 0.9
    voice = np.zeros(int(total * sr), np.float32)
    for st, a in parts: voice[int(st * sr):int(st * sr) + len(a)] += a
    voice = voice / (np.abs(voice).max() + 1e-6) * 0.92
    bed = music(total, sr)
    env = np.convolve((np.abs(voice) > 0.02).astype(np.float32), np.ones(int(0.25 * sr)) / int(0.25 * sr), mode='same')
    sfx = np.zeros_like(voice); rng = np.random.default_rng(3)
    for (st, _a) in parts[1:]:
        L = int(0.28 * sr); s0 = max(0, int((st - 0.18) * sr)); tt = np.arange(L) / sr
        nz = rng.standard_normal(L).astype(np.float32); nz = np.convolve(nz, np.ones(6) / 6, mode='same')
        sfx[s0:s0 + L] += (0.18 * nz * np.sin(np.pi * tt / 0.28) ** 2)[:len(sfx[s0:s0 + L])]
    mix = voice + bed * (0.16 - 0.09 * np.clip(env * 3, 0, 1)) + sfx
    mix = np.clip(mix / max(1, np.abs(mix).max() / 0.95), -1, 1)
    path = os.path.join(tmp, 'mix.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return path, timeline, total

# ---------------- visuals ----------------
def ease(x): x = max(0, min(1, x)); return 1 - (1 - x) ** 3
def back(x): x = max(0, min(1, x)); c = 1.7; return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2

def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ''
    for w_ in words:
        t = (cur + ' ' + w_).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines

_bgcache = {}
def background(t, accent=MINT):
    k = round(t * 10) / 10
    if k in _bgcache: return _bgcache[k].copy()
    w, h = 135, 240; y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    img = np.zeros((h, w, 3), np.float32) + np.array(BG1, np.float32)
    for (cx, cy, r, col, sp) in [(0.2, 0.25, 0.55, accent, 0.5), (0.85, 0.7, 0.6, (120, 90, 255), 0.37), (0.5, 1.0, 0.5, CORAL, 0.29)]:
        px = (cx + 0.12 * math.sin(k * sp * 2 + r * 5)) * w; py = (cy + 0.08 * math.cos(k * sp * 2)) * h
        g = np.exp(-(((x - px) ** 2 + (y - py) ** 2) / (2 * (r * w) ** 2)))[..., None]
        img = img + g * (np.array(col, np.float32) - img) * 0.28
    im = Image.fromarray(img.clip(0, 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)
    d = ImageDraw.Draw(im, 'RGBA')
    off = (k * 30) % 90
    for gx in range(0, W + 90, 90): d.line([(gx - off, 0), (gx - off, H)], fill=(255, 255, 255, 9))
    for gy in range(0, H + 90, 90): d.line([(0, gy + off), (W, gy + off)], fill=(255, 255, 255, 9))
    if len(_bgcache) > 40: _bgcache.clear()
    _bgcache[k] = im
    return im.copy()

def rrect(d, box, r, fill, outline=None, width=0): d.rounded_rectangle(box, r, fill=fill, outline=outline, width=width)

def words_at(seg, t, st, en):
    ws = seg['say'].split(); n = len(ws)
    lens = np.cumsum([len(w) + 1 for w in ws]); frac = (t - st) / max(0.01, en - st)
    return ws, int(np.searchsorted(lens / lens[-1], frac, side='right'))

def chrome(d, spec, t, total):
    # top badge + bottom brand + progress
    f = font('b', 34); tag = spec['series'].upper()
    tw = d.textlength(tag, font=f); rrect(d, (64, 110, 64 + tw + 44, 168), 29, (70, 215, 181, 40), MINT, 2); d.text((86, 118), tag, font=f, fill=MINT)
    d.text((64, H - 150), 'NEXORA', font=font('xb', 34), fill=INK); d.text((64 + d.textlength('NEXORA ', font=font('xb', 34)), H - 146), '· made with AI agents', font=font('m', 30), fill=MUTED)
    rrect(d, (64, H - 92, W - 64, H - 82), 5, (255, 255, 255, 35)); rrect(d, (64, H - 92, 64 + (W - 128) * min(1, t / total), H - 82), 5, MINT)

def caption(d, seg, t, st, en, y, size=58, maxw=W - 160, hl=MINT):
    """Word-by-word karaoke caption: spoken words bright, current word highlighted."""
    ws, k = words_at(seg, t, st, en); f = font('xb', size); lines, cur = [], []
    for i, w_ in enumerate(ws):
        if d.textlength(' '.join(x for _, x in cur + [(i, w_)]), font=f) > maxw and cur: lines.append(cur); cur = []
        cur.append((i, w_))
    if cur: lines.append(cur)
    lh = int(size * 1.22); y0 = y - len(lines) * lh // 2
    for li, line in enumerate(lines):
        lw = d.textlength(' '.join(x for _, x in line), font=f); x = (W - lw) / 2
        for i, w_ in line:
            ww = d.textlength(w_, font=f)
            if i == k - 1: rrect(d, (x - 10, y0 + li * lh - 6, x + ww + 10, y0 + li * lh + size + 10), 14, hl)
            col = (14, 20, 32) if i == k - 1 else (INK if i < k else (233, 238, 245, 90))
            d.text((x, y0 + li * lh), w_, font=f, fill=col); x += ww + d.textlength(' ', font=f)

def seg_at(tl, t):
    for i, (s, e) in enumerate(tl):
        if t < e + 0.35: return i, s, e
    return len(tl) - 1, tl[-1][0], tl[-1][1]

def paste_center(base, im, cx, cy, scale=1.0, alpha=1.0):
    if scale != 1.0: im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.LANCZOS)
    if alpha < 1: a = im.split()[3].point(lambda v: int(v * alpha)); im.putalpha(a)
    base.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)

# ---- style A: chat demo ----
def frame_chat(spec, tl, t, total):
    im = background(t); d = ImageDraw.Draw(im, 'RGBA'); segs = spec['segments']
    i, st, en = seg_at(tl, t); seg = segs[i]
    caption(d, seg, t, st, en, 440, 62)
    # phone card
    cx0, cy0, cx1, cy1 = 110, 640, W - 110, 1640
    pin = ease((t - 0.2) / 0.6); off = int((1 - pin) * 300)
    card = Image.new('RGBA', (W, H), (0, 0, 0, 0)); c = ImageDraw.Draw(card, 'RGBA')
    rrect(c, (cx0, cy0 + off, cx1, cy1 + off), 48, (21, 29, 44, 245), (255, 255, 255, 30), 2)
    c.ellipse((cx0 + 40, cy0 + off + 38, cx0 + 92, cy0 + off + 90), fill=MINT); c.text((cx0 + 54, cy0 + off + 44), 'AI', font=font('xb', 28), fill=BG1)
    c.text((cx0 + 112, cy0 + off + 48), 'Your AI chat', font=font('b', 34), fill=INK)
    c.line((cx0 + 30, cy0 + off + 120, cx1 - 30, cy0 + off + 120), fill=(255, 255, 255, 25), width=2)
    pi = next((j for j, s in enumerate(segs) if s.get('kind') == 'prompt'), None)
    by = cy0 + off + 160
    if pi is not None and t >= tl[pi][0] - 0.2:
        ps, pe = tl[pi]; txt = segs[pi].get('text', segs[pi]['say']); n = int(len(txt) * min(1, max(0, (t - ps) / max(0.1, pe - ps - 0.3))))
        shown = txt[:n]; f = font('sb', 40); lines = wrap(c, txt, f, cx1 - cx0 - 220)
        bh = len(lines) * 54 + 50; rrect(c, (cx0 + 150, by, cx1 - 40, by + bh), 34, (70, 215, 181, 235))
        left = n
        for li, line in enumerate(lines):
            part = line[:max(0, left)]; left -= len(line) + 1
            c.text((cx0 + 182, by + 25 + li * 54), part, font=f, fill=BG1)
        if n < len(txt) and int(t * 3) % 2 == 0:
            pass
        by += bh + 40
        if t > pe + 0.1:
            ri = next((j for j, s in enumerate(segs) if s.get('kind') == 'reply'), None)
            rep = segs[ri].get('text') if ri is not None else 'Sure! Here is a simple analogy…'
            dt = t - pe - 0.1
            if dt < 0.9:
                rrect(c, (cx0 + 40, by, cx0 + 250, by + 90), 34, (255, 255, 255, 30))
                for j in range(3):
                    yy = by + 45 + 8 * math.sin(t * 9 + j)
                    c.ellipse((cx0 + 80 + j * 50 - 11, yy - 11, cx0 + 80 + j * 50 + 11, yy + 11), fill=INK)
            else:
                f2 = font('m', 38); rl = wrap(c, rep, f2, cx1 - cx0 - 240); rh = len(rl) * 52 + 50
                a = ease((dt - 0.9) / 0.4)
                rrect(c, (cx0 + 40, by, cx1 - 150, by + rh), 34, (255, 255, 255, int(30 * a)))
                for li, line in enumerate(rl): c.text((cx0 + 72, by + 25 + li * 52), line, font=f2, fill=(233, 238, 245, int(255 * a)))
    else:
        f = font('m', 36); c.text((cx0 + 60, by + 30), 'Type a message…', font=f, fill=(147, 160, 180, 160))
    # input bar
    rrect(c, (cx0 + 30, cy1 + off - 120, cx1 - 30, cy1 + off - 40), 40, (255, 255, 255, 18))
    c.ellipse((cx1 - 110, cy1 + off - 112, cx1 - 46, cy1 + off - 48), fill=MINT); c.text((cx1 - 92, cy1 + off - 108), '↑', font=font('xb', 44), fill=BG1)
    im.paste(card, (0, 0), card)
    if seg.get('emoji'):
        a = back((t - st) / 0.35); paste_center(im, emoji(seg['emoji'], 110), W - 120, 235, 0.4 + 0.6 * a, min(1, a + 0.1))
    chrome(d, spec, t, total)
    return im.convert('RGB')

# ---- style B: kinetic captions ----
def frame_kinetic(spec, tl, t, total):
    segs = spec['segments']; i, st, en = seg_at(tl, t); seg = segs[i]
    accent = [MINT, CORAL, (140, 120, 255), MINT, CORAL][i % 5]
    im = background(t, accent); d = ImageDraw.Draw(im, 'RGBA')
    # punch zoom on segment start
    if seg.get('kind') == 'prompt':
        txt = seg.get('text', seg['say']); f = font('b', 46); lines = wrap(d, txt, f, W - 260); bh = len(lines) * 64 + 140
        a = back((t - st) / 0.45); y0 = 560
        card = Image.new('RGBA', (W, bh + 40), (0, 0, 0, 0)); c = ImageDraw.Draw(card, 'RGBA')
        rrect(c, (90, 0, W - 90, bh), 40, (255, 253, 248, 250)); c.text((130, 34), 'COPY THIS PROMPT', font=font('xb', 30), fill=(15, 140, 126))
        ws, k = words_at(seg, t, st, en); spoken = ' '.join(ws[:k])
        cnt = len(spoken)
        for li, line in enumerate(lines):
            c.text((130, 92 + li * 64), line, font=f, fill=(31, 36, 33) if cnt > 0 else (31, 36, 33, 70)); cnt -= len(line) + 1
        paste_center(im, card, W / 2, y0 + bh / 2, 0.85 + 0.15 * a, min(1, a))
        caption(d, seg, t, st, en, y0 + bh + 200, 52, hl=accent)
    else:
        ws, k = words_at(seg, t, st, en)
        groups, cur = [], []
        for w_ in ws:
            cur.append(w_)
            if w_[-1] in '.,!?' or len(cur) == 3: groups.append(cur); cur = []
        if cur: groups.append(cur)
        acc, ci = 0, 0
        for gi, g in enumerate(groups):
            if k > acc: ci = gi
            acc += len(g)
        words = groups[ci]; chunk_start = sum(len(g) for g in groups[:ci])
        f = font('black', 118 if seg.get('kind') == 'hook' else 104)
        layer = Image.new('RGBA', (W, 700), (0, 0, 0, 0)); c = ImageDraw.Draw(layer, 'RGBA')
        lines = wrap(c, ' '.join(words), f, W - 160); y = 350 - len(lines) * 70
        for line in lines:
            lw = c.textlength(line, font=f); x = (W - lw) / 2
            for w_ in line.split():
                ww = c.textlength(w_, font=f); hot = w_.strip('.,!?"').lower() in [h.lower() for h in seg.get('hot', [])]
                if hot: rrect(c, (x - 14, y - 4, x + ww + 14, y + 132), 22, accent)
                c.text((x, y), w_, font=f, fill=(14, 20, 32) if hot else PAPER); x += ww + c.textlength(' ', font=f)
            y += 140
        local = (t - st) - (en - st) * chunk_start / max(1, len(ws))
        a = back(local / 0.22); paste_center(im, layer, W / 2, 900, 0.82 + 0.18 * a, min(1, a * 1.5))
        if seg.get('emoji'):
            b = back((t - st) / 0.4); paste_center(im, emoji(seg['emoji'], 200), W / 2, 520 + 10 * math.sin(t * 4), 0.3 + 0.7 * b, min(1, b))
    chrome(d, spec, t, total)
    return im.convert('RGB')

# ---- style C: step cards ----
def frame_steps(spec, tl, t, total):
    im = background(t, (140, 120, 255)); d = ImageDraw.Draw(im, 'RGBA'); segs = spec['segments']
    i, st, en = seg_at(tl, t); seg = segs[i]
    caption(d, seg, t, st, en, 470, 62, hl=CORAL)
    steps = [s for s in segs if s.get('step')]
    y = 760
    for j, s in enumerate(steps):
        sj = segs.index(s); s0 = tl[sj][0]
        if t < s0 - 0.1: break
        a = ease((t - s0 + 0.1) / 0.5); x = int((1 - a) * W)
        active = sj == i
        f = font('b', 42); lines = wrap(d, s['step'], f, W - 360); h = max(150, len(lines) * 58 + 70)
        card = Image.new('RGBA', (W, h + 20), (0, 0, 0, 0)); c = ImageDraw.Draw(card, 'RGBA')
        rrect(c, (80, 0, W - 80, h), 36, (255, 253, 248, 250) if active else (255, 255, 255, 30), MINT if active else None, 4 if active else 0)
        c.ellipse((112, h / 2 - 46, 204, h / 2 + 46), fill=CORAL if active else (255, 255, 255, 40)); n = str(j + 1)
        c.text((158 - c.textlength(n, font=font('black', 52)) / 2, h / 2 - 34), n, font=font('black', 52), fill=PAPER)
        for li, line in enumerate(lines): c.text((240, h / 2 - len(lines) * 29 + li * 58), line, font=f, fill=(31, 36, 33) if active else INK)
        im.paste(card, (x, y), card); y += h + 34
    if seg.get('emoji'):
        b = back((t - st) / 0.4); paste_center(im, emoji(seg['emoji'], 110), W - 120, 235, 0.3 + 0.7 * b, min(1, b))
    chrome(d, spec, t, total)
    return im.convert('RGB')

STYLES = {'chat': frame_chat, 'kinetic': frame_kinetic, 'steps': frame_steps}

def render(spec, out, style, sid, tmp):
    os.makedirs(tmp, exist_ok=True)
    wav, tl, total = build_audio(spec['segments'], sid, tmp)
    fr = STYLES[style]; nf = int(total * FPS)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-', '-i', wav,
                          '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-shortest', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    starts = [a for a, _ in tl]
    for k in range(nf):
        t = k / FPS; img = fr(spec, tl, t, total)
        dz = min([t - a for a in starts if t >= a] or [9])
        if dz < 0.3:  # zoom punch on each new line
            z = 1 + 0.06 * (1 - ease(dz / 0.3)); cw, ch = int(W / z), int(H / z)
            img = img.crop(((W - cw) // 2, (H - ch) // 2, (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.BILINEAR)
        p.stdin.write(img.tobytes())
    p.stdin.close(); p.wait()
    return total

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('spec'); ap.add_argument('out'); ap.add_argument('--style', default='kinetic'); ap.add_argument('--voice', type=int, default=1)
    a = ap.parse_args(); spec = json.load(open(a.spec))
    print(round(render(spec, a.out, a.style, a.voice, a.out + '.tmp'), 1), 's')
