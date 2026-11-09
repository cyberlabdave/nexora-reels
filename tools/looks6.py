#!/usr/bin/env python3
"""Nexora "Looks v6": one bright, picture-led look per content category (owner-approved Nov 7, 2026).

Looks: "animal" (Deep Sea Pop), "history" (Paper Documentary), "phone" (Device Demo), "quiz" (Game Show).
Why: the navy text-slide look (reels3.py) held Instagram viewers ~3.4s; the bright picture-led Kids look 6.6s.
Audio: same engine as kids5.py (Jessica voice, natural pace, native voices via {es:...}, original music, pop sounds).

Usage: python3 looks6.py spec.json out.mp4 [--cover out.jpg]
Env: NX_TTS_DIR, NX_KOKORO_MULTI (auto-downloaded next to NX_TTS_DIR if missing), NX_FONT_DIR (repo fonts/).

Spec:
{"look":"animal|history|phone|quiz","series":"Explore: Animal facts #1","tag":"optional pill text","deco":"🪐 (quiz only)",
 "segments":[
  {"kind":"hook","title":"An octopus has THREE hearts","emoji":"🐙","sub":"Wait till you hear **what each one does**","say":"..."},
  {"kind":"line","title":"...","emoji":"🐙","items":[{"e":"💙","label":"gills"},{"e":"💙","label":"gills"},{"e":"❤️","label":"body"}],"sub":"...","say":"..."},
  {"kind":"line","title":"...","bullets":["...","..."],"say":"..."},
  {"kind":"line","title":"...","doc":{"lines":["qokeedy shedy","daiin"],"emoji":"🌿","stamp":"UNSOLVED|1400s?"},"sub":"...","say":"..."},   (history)
  {"kind":"line","title":"...","screen":{"title":"Back Tap","rows":[["Double Tap","Screenshot ›"]],"ring":[310,815,450,120],"back":false},"sub":"...","say":"..."}, (phone)
  {"kind":"quiz","title":"Which planet has the MOST moons?","options":["Jupiter","Saturn","Neptune"],"answer":1,"say":"... Three. Two. One."},
  {"kind":"reveal","title":"It's Saturn!","options":[...],"answer":1,"confetti":true,"sub":"...","say":"..."},
  {"kind":"cta","title2":"SEND THIS","sub":"to a friend who loves weird facts","emoji":"📤","say":"..."}]}
Optional on the cta: "recap":["3 short facts", ...] turns the end card into a "SCREENSHOT THIS" save card (A/B test, Nov 9);
without it the end card is unchanged.
"sub" supports **bold** for the accent colour. Item pop-ins follow the spoken sentences (one sentence per item).
"""
import json, os, sys, argparse, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kids5

FPS = kids5.FPS

def ensure_multi():
    if not kids5.KM or not os.path.exists(os.path.join(kids5.KM, 'model.onnx')):
        import reels2
        m = reels2._multi_dir()
        if m: kids5.KM = m

def page(spec, tl, total, lips):
    segs = []
    keys = ('kind', 'title', 'title2', 'sub', 'emoji', 'items', 'bullets', 'doc', 'screen', 'options', 'answer', 'confetti', 'hot', 'recap')
    for s, t in zip(spec['segments'], tl):
        d = {k: s.get(k) for k in keys}; d.update(st=t['st'], en=t['en'], parts=t['parts']); segs.append(d)
    for i, d in enumerate(segs):
        d['vs'] = 0 if i == 0 else d['st'] - 0.15
        d['ve'] = segs[i + 1]['st'] - 0.15 if i + 1 < len(segs) else total
    data = {'look': spec.get('look', 'animal'), 'tag': spec.get('tag'), 'deco': spec.get('deco'), 'segs': segs, 'total': total, 'lips': lips, 'fps': FPS}
    html = open(os.path.join(HERE, 'looks6.html')).read()
    return html.replace('FONTDIR', 'file://' + os.path.abspath(kids5.FONT_DIR)).replace('/*DATA*/null', json.dumps(data, ensure_ascii=False))

def render(spec, out, sid=4, cover=None):
    ensure_multi()
    tmp = os.path.abspath(out + '.tmp'); os.makedirs(tmp, exist_ok=True)
    wav, tl, total, lips = kids5.build_audio(spec, sid, tmp)
    html = os.path.join(tmp, 'reel.html'); open(html, 'w').write(page(spec, tl, total, lips))
    import reels3
    reels3.capture(html, out, wav, total, cover, 0.05)
    shutil.rmtree(tmp, ignore_errors=True)
    return total

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('spec'); ap.add_argument('out'); ap.add_argument('--cover'); ap.add_argument('--voice', type=int, default=4)
    a = ap.parse_args(); print('%.1fs' % render(json.load(open(a.spec)), a.out, a.voice, a.cover))
