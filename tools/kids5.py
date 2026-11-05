#!/usr/bin/env python3
"""Nexora Kids & Families renderer "Sunny Playground" (owner-approved style A, Nov 5, 2026).

Bright sky + moving clouds/sun + green hills, an original drawn kid (lip-synced, blinking, bouncing, waving),
bubbly Fredoka letters that bounce in, objects that pop in as they are counted, quiz cards with a 3-2-1
countdown, confetti on reveals. Voice: Kokoro multi-lang v1.0 at natural pace, with NATIVE voices for
foreign words (Spanish, French, Hindi, Italian, Portuguese, Japanese, Chinese).

Usage: python3 kids5.py spec.json out.mp4 [--cover out.jpg] [--voice 3]
Env: NX_TTS_DIR (sherpa-onnx v1.12.20 shared build), NX_KOKORO_MULTI (kokoro-multi-lang-v1_0 folder)

Spec (v4 Kids specs work as-is; extras are optional):
{"series":"Kids & Families #6","place":"Spain","flag":"🇪🇸",
 "kid":{"name":"Lucía","skin":"#C98A5E","hair":"#3A2416","hairStyle":"pigtails|bob|puffs|short|long|bun","outfit":"#E8502F"},
 "segments":[
  {"kind":"hook","title":"Count to 5","sub":"in Spanish with Lucía","bubble":"¡Hola!","say":"Hi friends! ..."},
  {"kind":"count","title":"Let's count!","item":"🍊","words":[{"say":"{es:¡Uno!} One!","label":"Uno"}, ...]},
  {"kind":"line","title":"¡Muy bien!","sub":"means: very good!","emoji":"🎉","confetti":true,"say":"{es:¡Muy bien!} That means, very good!"},
  {"kind":"line","title":"...","bullets":["..."],"say":"..."},
  {"kind":"quiz","title":"...","options":["A","B","C"],"answer":1,"say":"... Three. Two. One."},
  {"kind":"reveal","title":"It's the beaver!","options":[...],"answer":1,"source":"...","say":"..."},
  {"kind":"cta","title":"COMMENT BELOW","sub":"...","tiny":"...","emoji":"👇","say":"..."}]}
Inline language: "{es:¡Uno!}" is spoken by the native Spanish voice (es, fr, hi, it, pt, ja, zh).
"""
import json, os, sys, argparse, subprocess, shutil, re, wave, hashlib
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

W, H, FPS, SR = 1080, 1920, 30, 24000
LANG = {'es': (28, 'es'), 'fr': (30, 'fr'), 'hi': (31, 'hi'), 'it': (35, 'it'), 'pt': (42, 'pt-br'), 'ja': (37, 'ja'), 'zh': (47, 'zh')}
TTS_DIR = os.environ.get('NX_TTS_DIR', '')
KM = os.environ.get('NX_KOKORO_MULTI', '')
FONT_DIR = os.environ.get('NX_FONT_DIR', os.path.join(os.path.dirname(HERE), 'fonts'))

def tts(text, path, sid, lang):
    exe = os.path.join(TTS_DIR, 'bin', 'sherpa-onnx-offline-tts')
    env = dict(os.environ); env['LD_LIBRARY_PATH'] = os.path.join(TTS_DIR, 'lib') + ':' + env.get('LD_LIBRARY_PATH', '')
    cmd = [exe, f'--kokoro-model={KM}/model.onnx', f'--kokoro-voices={KM}/voices.bin', f'--kokoro-tokens={KM}/tokens.txt',
           f'--kokoro-data-dir={KM}/espeak-ng-data', f'--kokoro-dict-dir={KM}/dict',
           f'--kokoro-lexicon={KM}/lexicon-us-en.txt,{KM}/lexicon-zh.txt', '--num-threads=4', f'--sid={sid}',
           '--kokoro-length-scale=' + os.environ.get('NX_KIDS_PACE', '1.0'), f'--kokoro-lang={lang}', f'--output-filename={path}', text]
    subprocess.run(cmd, check=True, capture_output=True, env=env)
    with wave.open(path) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    nz = np.where(np.abs(a) > 0.012)[0]
    if len(nz): a = a[max(0, nz[0] - 240): nz[-1] + 1500]
    return a

def split_parts(say, en_sid):
    out = []
    for m in re.finditer(r'\{(\w\w):([^}]*)\}|([^{]+)', say):
        if m.group(1):
            sid, lang = LANG.get(m.group(1), (en_sid, 'en'))
            out.append((m.group(2).strip(), sid, lang))
        elif m.group(3).strip():
            out.append((m.group(3).strip(), en_sid, 'en'))
    return [p for p in out if re.search(r'\w', p[0])]

def plain(say): return re.sub(r'\{\w\w:([^}]*)\}', r'\1', say)

def music(dur, sr, seed=11):
    """Light, bouncy original bed: plucked major arpeggio + soft kick, 112 bpm (procedural, no samples)."""
    rng = np.random.default_rng(seed); n = int(dur * sr); out = np.zeros(n, np.float32)
    bpm = 112; beat = 60 / bpm; prog = [[60, 64, 67, 72], [57, 60, 64, 69], [65, 69, 72, 77], [67, 71, 74, 79]]
    t8 = beat / 2; k = 0; t = 0.0
    while t < dur:
        ch = prog[int(t / (beat * 4)) % 4]; note = ch[k % 4] + (12 if k % 8 >= 6 else 0)
        f = 440 * 2 ** ((note - 69) / 12); L = int(0.35 * sr); tt = np.arange(L) / sr
        tone = (np.sin(2 * np.pi * f * tt) + .35 * np.sin(4 * np.pi * f * tt)) * np.exp(-tt * 9)
        s0 = int(t * sr); out[s0:s0 + L] += (0.22 * tone)[:max(0, n - s0)]
        if k % 2 == 0:
            Lk = int(0.12 * sr); tk = np.arange(Lk) / sr
            kick = np.sin(2 * np.pi * (110 - 400 * tk) * tk) * np.exp(-tk * 30)
            out[s0:s0 + Lk] += (0.25 * kick)[:max(0, n - s0)]
        t += t8; k += 1
    return out / (np.abs(out).max() + 1e-6)

def blip(sr, f=880, L=0.12):
    tt = np.arange(int(L * sr)) / sr
    return (np.sin(2 * np.pi * (f + 600 * tt / L) * tt) * np.exp(-tt * 22)).astype(np.float32)

def build_audio(spec, en_sid, tmp):
    segs = spec['segments']; voice_parts = []; tl = []; cur = 0.2; pops = []; k = 0
    for i, s in enumerate(segs):
        st = cur; partsT = []
        if s.get('kind') == 'count':
            items = s.get('words', [])
            if s.get('say'):
                for (txt, sid, lang) in split_parts(s['say'], en_sid):
                    a = tts(txt, os.path.join(tmp, f'p{k}.wav'), sid, lang); k += 1
                    voice_parts.append((cur, a)); cur += len(a) / SR + 0.15
            for j, w in enumerate(items):
                partsT.append(cur); pops.append(cur)
                for (txt, sid, lang) in split_parts(w['say'], en_sid):
                    a = tts(txt, os.path.join(tmp, f'p{k}.wav'), sid, lang); k += 1
                    voice_parts.append((cur, a)); cur += len(a) / SR + 0.12
                cur += 0.25
        else:
            for (txt, sid, lang) in split_parts(s.get('say', ''), en_sid):
                a = tts(txt, os.path.join(tmp, f'p{k}.wav'), sid, lang); k += 1
                partsT.append(cur); voice_parts.append((cur, a)); cur += len(a) / SR + 0.16
            if s.get('kind') == 'reveal' or s.get('confetti'): pops.append(st + 0.05)
        cur = max(cur, st + 1.2)
        tl.append({'st': st, 'en': cur, 'parts': partsT})
        cur += 0.3 if s.get('kind') != 'quiz' else 0.6
    total = cur + 0.8
    n = int(total * SR); voice = np.zeros(n, np.float32)
    for st, a in voice_parts: voice[int(st * SR):int(st * SR) + len(a)] += a[:max(0, n - int(st * SR))]
    voice = voice / (np.abs(voice).max() + 1e-6) * 0.9
    env = np.convolve((np.abs(voice) > 0.02).astype(np.float32), np.ones(int(0.3 * SR)) / int(0.3 * SR), mode='same')
    bed = music(total, SR); sfx = np.zeros(n, np.float32)
    for p in pops:
        b = blip(SR, 900); s0 = int(p * SR); sfx[s0:s0 + len(b)] += 0.28 * b[:max(0, n - s0)]
    for t in tl[1:]:
        b = blip(SR, 520, .18); s0 = int(max(0, t['st'] - 0.12) * SR); sfx[s0:s0 + len(b)] += 0.12 * b[:max(0, n - s0)]
    mix = voice + bed * (0.17 - 0.1 * np.clip(env * 3, 0, 1)) + sfx
    mix = np.clip(mix / max(1, np.abs(mix).max() / 0.95), -1, 1)
    hop = SR // FPS; nf = n // hop
    ve = np.abs(voice[:nf * hop]).reshape(nf, hop).mean(1)
    ref = np.percentile(ve[ve > 0.004], 90) if (ve > 0.004).any() else 1
    lips = np.clip(ve / (ref + 1e-6), 0, 1).round(3).tolist()
    path = os.path.join(tmp, 'mix.wav')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return path, tl, total, lips

SKINS = ['#F2C9A0', '#E0A87A', '#C98A5E', '#9C6644', '#7A4A2C', '#5C3820']
HAIRS = ['#3A2416', '#1B1B1B', '#6B3E1E', '#C8862B', '#2A1A10']
OUTFITS = ['#E8502F', '#2F6FE8', '#8B5CF6', '#14B8A6', '#F59E0B', '#EC4899']
STYLES = ['pigtails', 'bob', 'puffs', 'short', 'long', 'bun']

def kid_for(spec):
    h = int(hashlib.md5(spec.get('series', 'x').encode()).hexdigest(), 16)
    k = {'skin': SKINS[h % 6], 'hair': HAIRS[(h >> 4) % 5], 'outfit': OUTFITS[(h >> 8) % 6], 'hairStyle': STYLES[(h >> 12) % 6]}
    k.update(spec.get('kid') or {}); return k

PERSON = re.compile('[\U0001F466-\U0001F469\U0001F9D2\U0001F9D1]')

def page(spec, tl, total, lips):
    segs = []
    for s, t in zip(spec['segments'], tl):
        d = {k: s.get(k) for k in ('kind', 'title', 'sub', 'tiny', 'emoji', 'bullets', 'options', 'answer', 'source', 'bubble', 'item', 'confetti', 'tag')}
        if d['emoji'] and PERSON.search(d['emoji']): d['emoji'] = None
        d['words'] = [w.get('label') or plain(w['say']).split()[0] for w in s.get('words', [])]
        d['trans'] = [w.get('trans', '') for w in s.get('words', [])]
        d.update(st=t['st'], en=t['en'], parts=t['parts'])
        segs.append(d)
    for i, d in enumerate(segs):
        d['vs'] = 0 if i == 0 else d['st'] - 0.15
        d['ve'] = segs[i + 1]['st'] - 0.15 if i + 1 < len(segs) else total
    data = {'series': spec.get('series', ''), 'place': spec.get('place', ''), 'flag': spec.get('flag', '🌍'),
            'kid': kid_for(spec), 'segs': segs, 'total': total, 'lips': lips, 'fps': FPS}
    html = open(os.path.join(HERE, 'kids5.html')).read()
    fd = 'file://' + os.path.abspath(FONT_DIR)
    return html.replace('FONTDIR', fd).replace('/*DATA*/null', json.dumps(data, ensure_ascii=False))

def render(spec, out, sid=4, cover=None):
    tmp = os.path.abspath(out + '.tmp'); os.makedirs(tmp, exist_ok=True)
    wav, tl, total, lips = build_audio(spec, sid, tmp)
    html = os.path.join(tmp, 'reel.html'); open(html, 'w').write(page(spec, tl, total, lips))
    sys.path.insert(0, HERE); import reels3
    reels3.capture(html, out, wav, total, cover, 1.3)
    shutil.rmtree(tmp, ignore_errors=True)
    return total

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('spec'); ap.add_argument('out'); ap.add_argument('--cover'); ap.add_argument('--voice', type=int, default=int(os.environ.get('NX_KIDS_VOICE', 4)))
    a = ap.parse_args(); spec = json.load(open(a.spec))
    print('%.1fs' % render(spec, a.out, a.voice, a.cover))
