#!/usr/bin/env python3
"""Nexora reel renderer v3: same voice + music as reels2 (Kokoro, procedural bed), new HTML/CSS motion graphics
captured frame by frame in headless Chromium (Playwright) and encoded with ffmpeg. HyperFrames-style, fully local, free.

Usage: python3 reels3.py spec.json out.mp4 [--voice 1] [--accent cyan|mint|violet|coral]
spec: {"series":"AI Reality Check #02","segments":[{"kind":"hook|line|prompt|reply|step|cta","say":"spoken","title":"<=6 words on screen",
        "text":"prompt / reply / step text","emoji":"📅","hot":["word"]}]}
Kinds: hook = big headline; line = headline; prompt = typing chat card (You); reply = AI answer card; step = numbered step card; cta = save/follow end card.
Text rule: light text on navy, or navy text on white cards. Never dark text on navy.
"""
import json, os, sys, argparse, subprocess, shutil, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reels2  # audio pipeline (tts + music + mix) is reused unchanged

W, H, FPS = 1080, 1920, 30
ACCENTS = {'cyan': '#22D3EE', 'mint': '#46D7B5', 'violet': '#A78BFA', 'coral': '#FF7A66'}
SERIES_ACCENT = [('reality', 'cyan'), ('prompt', 'mint'), ('free tool', 'coral'), ('update', 'violet'), ('showdown', 'violet'),
                 ('workflow', 'mint'), ('fail', 'coral'), ('worth', 'cyan'), ('tool drop', 'coral')]

PAGE = r"""<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Inter;font-weight:900;src:url(file:///usr/share/fonts/opentype/inter/Inter-Black.otf)}
@font-face{font-family:Inter;font-weight:800;src:url(file:///usr/share/fonts/opentype/inter/Inter-ExtraBold.otf)}
@font-face{font-family:Inter;font-weight:700;src:url(file:///usr/share/fonts/opentype/inter/Inter-Bold.otf)}
@font-face{font-family:Inter;font-weight:600;src:url(file:///usr/share/fonts/opentype/inter/Inter-SemiBold.otf)}
@font-face{font-family:Inter;font-weight:500;src:url(file:///usr/share/fonts/opentype/inter/Inter-Medium.otf)}
@font-face{font-family:Emo;src:url(file:///usr/share/fonts/truetype/noto/NotoColorEmoji.ttf)}
:root{--acc:ACCENT;--bg:#0B1026;--bg2:#141B3A;--ink:#FFFFFF;--muted:#A9B4D6;--card:#FFFFFF;--cardink:#0B1026}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1920px;overflow:hidden;background:var(--bg);font-family:Inter,sans-serif;color:var(--ink)}
#bg{position:absolute;inset:0;background:radial-gradient(circle at 50% 40%,#18214a 0%,var(--bg) 70%)}
.blob{position:absolute;width:900px;height:900px;border-radius:50%;filter:blur(120px);opacity:.35}
#grid{position:absolute;inset:-200px;background-image:linear-gradient(rgba(255,255,255,.045) 2px,transparent 2px),linear-gradient(90deg,rgba(255,255,255,.045) 2px,transparent 2px);background-size:90px 90px}
.layer{position:absolute;left:0;top:0;width:1080px;height:1920px}
#top{position:absolute;top:300px;left:80px;right:80px;display:flex;justify-content:space-between;align-items:center}
.pill{padding:12px 26px;border-radius:999px;background:rgba(255,255,255,.1);border:2px solid rgba(255,255,255,.18);font:800 30px Inter;letter-spacing:.08em;text-transform:uppercase;color:var(--ink)}
.pill b{color:var(--acc)}
#prog{position:absolute;top:270px;left:80px;right:80px;height:8px;border-radius:9px;background:rgba(255,255,255,.12);overflow:hidden}
#prog i{display:block;height:100%;background:var(--acc);border-radius:9px}
#made{position:absolute;bottom:330px;right:80px;font:600 26px Inter;color:var(--muted);letter-spacing:.04em}
.scene{position:absolute;left:0;top:0;width:1080px;height:1920px;display:none}
.center{position:absolute;left:80px;right:80px;top:420px;bottom:420px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:56px;text-align:center}
.emo{font-family:Emo;font-size:230px;line-height:1;filter:drop-shadow(0 20px 40px rgba(0,0,0,.45))}
.head{font:900 118px/1.04 Inter;letter-spacing:-.025em;text-wrap:balance;color:var(--ink)}
.head.big{font-size:132px}
.w{display:inline-block;margin:0 .14em;will-change:transform,opacity}
.w.hot{color:var(--acc)}
.w.hl{background:var(--acc);color:var(--cardink);padding:0 .14em;border-radius:12px}
.chat{width:100%;display:flex;flex-direction:column;gap:30px;align-items:stretch;text-align:left}
.who{font:800 30px Inter;letter-spacing:.1em;text-transform:uppercase;color:var(--acc);display:flex;align-items:center;gap:14px}
.who .av{width:54px;height:54px;border-radius:50%;background:var(--acc);display:grid;place-items:center;color:var(--cardink);font:900 26px Inter}
.card{background:var(--card);color:var(--cardink);border-radius:44px;padding:56px 56px 60px;font:800 70px/1.18 Inter;box-shadow:0 30px 80px rgba(0,0,0,.45),0 0 0 6px rgba(255,255,255,.08)}
.card.ai{background:#1E2750;color:var(--ink);font:700 58px/1.25 Inter;border:3px solid rgba(255,255,255,.14)}
.caret{display:inline-block;width:8px;height:66px;background:var(--cardink);vertical-align:-8px;margin-left:6px}
.save{align-self:center;display:inline-flex;align-items:center;gap:16px;padding:20px 36px;border-radius:999px;background:var(--acc);color:var(--cardink);font:900 40px Inter;letter-spacing:.04em;text-transform:uppercase;box-shadow:0 18px 50px rgba(0,0,0,.4)}
.save .e{font-family:Emo;font-size:44px}
.step{display:flex;gap:36px;align-items:flex-start;text-align:left;width:100%}
.num{flex:none;width:150px;height:150px;border-radius:40px;background:var(--acc);color:var(--cardink);display:grid;place-items:center;font:900 96px Inter}
.step .card{flex:1;font-size:62px}
.cta .emo{font-size:300px}
.cta .head{font-size:150px}
.cta .sub{font:800 56px/1.2 Inter;color:var(--acc)}
.cta .tiny{font:700 38px Inter;color:var(--muted)}
ul.bul{list-style:none;width:100%;display:flex;flex-direction:column;gap:22px}
ul.bul li{display:flex;align-items:center;gap:26px;padding:30px 36px;border-radius:30px;background:var(--card);color:var(--cardink);font:800 54px/1.15 Inter;text-align:left;box-shadow:0 18px 50px rgba(0,0,0,.35)}
ul.bul li i{flex:none;width:58px;height:58px;border-radius:50%;background:var(--acc);display:grid;place-items:center;font:900 34px Inter;font-style:normal;color:var(--cardink)}
.head.sm{font-size:96px}
#flash{position:absolute;inset:0;background:var(--acc);opacity:0;pointer-events:none}
</style></head><body>
<div id="bg"><div class="blob" id="b1" style="background:var(--acc)"></div><div class="blob" id="b2" style="background:#7C5CFF"></div><div id="grid"></div></div>
<div id="scenes"></div>
<div id="prog"><i id="progi"></i></div>
<div id="top"><span class="pill" id="series"></span></div>
<div id="made">Made with AI agents</div>
<div id="flash"></div>
<script>
const D=DATA;const $=s=>document.querySelector(s);
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));const ease=x=>1-Math.pow(1-clamp(x,0,1),3);
const back=x=>{x=clamp(x,0,1);const c=1.7;return 1+(c+1)*Math.pow(x-1,3)+c*Math.pow(x-1,2)};
const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
$('#series').innerHTML=esc(D.series).replace(/(#\d+)/,'<b>$1</b>');
const root=$('#scenes');
D.segs.forEach((s,i)=>{const el=document.createElement('div');el.className='scene '+s.kind;el.id='s'+i;let h='';
  const words=(s.title||'').split(/\s+/).filter(Boolean);
  let hot=(s.hot||[]).map(x=>x.toLowerCase().replace(/[^a-z0-9']/g,''));
  if((s.kind==='hook'||s.kind==='line')&&!words.some(w=>hot.includes(w.toLowerCase().replace(/[^a-z0-9']/g,'')))){const c=words.map(w=>w.toLowerCase().replace(/[^a-z0-9']/g,'')).filter(w=>w.length>3);if(c.length){hot=[c.reduce((x,y)=>y.length>x.length?y:x)]}}
  const wspan=(w,j)=>{const k=w.toLowerCase().replace(/[^a-z0-9']/g,'');const cls=hot.includes(k)?(s.kind==='hook'?'w hl':'w hot'):'w';return `<span class="${cls}" data-j="${j}">${esc(w)}</span>`};
  if((s.kind==='hook'||s.kind==='line')&&s.bullets&&s.bullets.length){h=`<div class="center" style="gap:44px">${s.emoji?`<div class="emo" style="font-size:150px">${s.emoji}</div>`:''}<div class="head sm">${words.map(wspan).join(' ')}</div><ul class="bul">${s.bullets.map((b,k)=>`<li><i>${k+1}</i><span>${esc(b)}</span></li>`).join('')}</ul></div>`}
  else if(s.kind==='hook'||s.kind==='line'){h=`<div class="center">${s.emoji?`<div class="emo">${s.emoji}</div>`:''}<div class="head ${s.kind==='hook'?'big':''}">${words.map(wspan).join(' ')}</div></div>`}
  else if(s.kind==='prompt'){h=`<div class="center"><div class="chat"><div class="who"><span class="av">YOU</span>Paste this prompt</div><div class="card"><span class="ty"></span><span class="caret"></span></div></div><div class="save"><span class="e">🔖</span>Save this prompt</div></div>`}
  else if(s.kind==='reply'){h=`<div class="center"><div class="chat"><div class="who"><span class="av">AI</span>Example reply</div><div class="card ai"><span class="ty"></span></div></div></div>`}
  else if(s.kind==='step'){h=`<div class="center"><div class="step"><div class="num">${s.n}</div><div class="card"><span class="ty"></span></div></div>${s.title?`<div class="head" style="font-size:84px">${words.map(wspan).join(' ')}</div>`:''}</div>`}
  else if(s.kind==='cta'){h=`<div class="center cta"><div class="emo">${s.emoji||'🔖'}</div><div class="head">${esc(s.title||'SAVE THIS')}</div><div class="sub">${esc(s.sub||'')}</div><div class="tiny">${esc(s.tiny||'')}</div></div>`}
  el.innerHTML=h;root.appendChild(el);});
const scenes=[...document.querySelectorAll('.scene')];
function seek(t){
  const T=D.total;$('#progi').style.width=(100*clamp(t/T,0,1))+'%';
  $('#b1').style.transform=`translate(${-200+160*Math.sin(t*.35)}px,${100+120*Math.cos(t*.27)}px)`;
  $('#b2').style.transform=`translate(${450+140*Math.cos(t*.31)}px,${1050+160*Math.sin(t*.22)}px)`;
  $('#grid').style.transform=`translateY(${(t*22)%90}px)`;
  let cur=0;D.segs.forEach((s,i)=>{if(t>=s.vs)cur=i});
  scenes.forEach((el,i)=>{el.style.display=i===cur?'block':'none'});
  const s=D.segs[cur],el=scenes[cur],lt=t-s.vs,dur=s.ve-s.vs;
  const since=t-s.vs;$('#flash').style.opacity=cur>0&&since<.12?(.18*(1-since/.12)):0;
  const c=el.querySelector('.center');c.style.transform=`scale(${1+.03*(1-ease(lt/.35))+.012*lt/Math.max(dur,1)})`;
  if(s.kind==='hook'||s.kind==='line'||(s.kind==='step'&&s.title)){
    const ws=[...el.querySelectorAll('.w')];const per=Math.min(.16,(Math.max(dur*.55,.3))/Math.max(ws.length,1));
    ws.forEach((w,j)=>{const p=back((lt-.04-j*per)/.32);const o=clamp((lt-.04-j*per)/.12,0,1);w.style.opacity=o;w.style.transform=`translateY(${(1-p)*60}px) scale(${.7+.3*p})`});}
  const lis=[...el.querySelectorAll('ul.bul li')];if(lis.length){const gap=Math.min(.9,Math.max(dur*.7,.6)/lis.length);lis.forEach((li,j)=>{const q=back((lt-.35-j*gap)/.35);li.style.opacity=clamp((lt-.35-j*gap)/.12,0,1);li.style.transform=`translateX(${(1-q)*-140}px)`})}
  const emo=el.querySelector('.emo');if(emo){const p=back(lt/.45);emo.style.opacity=clamp(lt/.15,0,1);emo.style.transform=`scale(${.4+.6*p}) rotate(${(1-p)*-18+3*Math.sin(t*2.2)}deg) translateY(${8*Math.sin(t*3)}px)`}
  const ty=el.querySelector('.ty');if(ty){const full=s.text||'';const p=clamp((lt-.25)/Math.max(dur*.62,.6),0,1);const n=Math.round(full.length*p);ty.textContent=full.slice(0,n);
    const card=el.querySelector('.card');const q=back(lt/.4);card.style.transform=`translateY(${(1-q)*120}px) scale(${.92+.08*q})`;card.style.opacity=clamp(lt/.15,0,1);
    const caret=el.querySelector('.caret');if(caret)caret.style.opacity=(p<1||Math.floor(t*2.4)%2===0)?1:0;}
  const who=el.querySelector('.who');if(who){who.style.opacity=clamp(lt/.2,0,1)}
  const num=el.querySelector('.num');if(num){const q=back(lt/.35);num.style.transform=`scale(${q}) rotate(${(1-q)*-30}deg)`}
  const sv=el.querySelector('.save');if(sv){const q=back((lt-dur*.55)/.35);sv.style.opacity=clamp((lt-dur*.55)/.12,0,1);sv.style.transform=`scale(${.6+.4*q+.03*Math.sin(t*6)})`}
  if(s.kind==='cta'){[...el.querySelectorAll('.head,.sub,.tiny')].forEach((x,j)=>{const q=back((lt-.15-j*.18)/.35);x.style.opacity=clamp((lt-.15-j*.18)/.12,0,1);x.style.transform=`translateY(${(1-q)*50}px)`});
    if(emo)emo.style.transform=`scale(${(.4+.6*back(lt/.45))*(1+.06*Math.sin(t*5))})`;}
}
window.seek=seek;window.ready=document.fonts.ready.then(()=>true);
</script></body></html>"""

def accent_for(series, forced=None):
    if forced: return ACCENTS[forced]
    s = (series or '').lower()
    for k, v in SERIES_ACCENT:
        if k in s: return ACCENTS[v]
    return ACCENTS['cyan']

def short_title(seg):
    if seg.get('title'): return seg['title']
    words = re.sub(r'\s+', ' ', seg.get('say', '')).strip().split(' ')
    return ' '.join(words[:6])

def build(spec, tl, total, accent):
    segs, n = [], 0
    for i, s in enumerate(spec['segments']):
        st, en = tl[i]
        vs = 0 if i == 0 else max(0.0, st - 0.12)  # cut slightly before the line is spoken
        ve = tl[i + 1][0] - 0.12 if i + 1 < len(tl) else total
        k = s.get('kind', 'line')
        d = {'kind': k, 'vs': vs, 've': ve, 'emoji': s.get('emoji', ''), 'hot': s.get('hot', []), 'text': s.get('text', ''), 'bullets': s.get('bullets', [])}
        if k in ('hook', 'line'): d['title'] = short_title(s)
        if k == 'step': n += 1; d['n'] = s.get('n', n); d['text'] = s.get('step', s.get('text', '')); d['title'] = s.get('title', '')
        if k == 'cta':
            say = s.get('say', ''); low = say.lower(); hot = [h.lower() for h in s.get('hot', [])]
            if s.get('title'): t = s['title']
            elif 'save' in low or 'save' in hot: t = 'SAVE THIS'
            elif 'comment' in low or 'comment' in hot: t = 'COMMENT BELOW'
            elif 'send' in low or 'share' in low: t = 'SEND THIS'
            else: t = 'FOLLOW FOR MORE'
            d['title'] = t
            d['emoji'] = s.get('emoji') or {'SAVE THIS': '🔖', 'COMMENT BELOW': '👇', 'SEND THIS': '📨'}.get(t, '👀')
            m = re.search(r'follow for (.+?)[.!]?$', say, re.I)
            if s.get('sub'): d['sub'] = s['sub']
            elif t == 'COMMENT BELOW': d['sub'] = 'Want a real hands-on test?'
            elif m: d['sub'] = 'Follow for ' + m.group(1)
            else: d['sub'] = 'Follow for one AI tip a day'
            has_prompt = any(x.get('kind') == 'prompt' for x in spec['segments'])
            d['tiny'] = s.get('tiny', 'Full prompt in the caption' if has_prompt else 'Details in the caption')
        segs.append(d)
    data = {'series': spec.get('series', ''), 'segs': segs, 'total': total}
    return PAGE.replace('ACCENT', accent).replace('DATA', json.dumps(data, ensure_ascii=False))

def capture(html_path, out_video, wav, total, cover=None, cover_t=None):
    js = r"""
const {chromium}=require('playwright');const {spawn}=require('child_process');
const [html,out,wav,total,cover,coverT]=process.argv.slice(2);
(async()=>{const fps=%d,W=%d,H=%d;const b=await chromium.launch();const p=await b.newPage({viewport:{width:W,height:H}});
await p.goto('file://'+html);await p.evaluate(()=>window.ready);
const ff=spawn('ffmpeg',['-v','error','-y','-f','image2pipe','-framerate',String(fps),'-c:v','mjpeg','-i','-','-i',wav,'-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',out],{stdio:['pipe','inherit','inherit']});
const n=Math.ceil(parseFloat(total)*fps);
for(let i=0;i<n;i++){await p.evaluate(t=>window.seek(t),i/fps);const buf=await p.screenshot({type:'jpeg',quality:90});if(!ff.stdin.write(buf))await new Promise(r=>ff.stdin.once('drain',r));}
ff.stdin.end();await new Promise(r=>ff.on('close',r));
if(cover&&cover!=='-'){await p.evaluate(t=>window.seek(t),parseFloat(coverT));await p.screenshot({path:cover,type:'jpeg',quality:92});}
await b.close();})().catch(e=>{console.error(e);process.exit(1)});
""" % (FPS, W, H)
    jsp = html_path + '.cap.js'; open(jsp, 'w').write(js)
    env = dict(os.environ)
    gr = subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True).stdout.strip()
    if gr: env['NODE_PATH'] = gr + (':' + env['NODE_PATH'] if env.get('NODE_PATH') else '')
    subprocess.run(['node', jsp, html_path, out_video, wav, str(total), cover or '-', str(cover_t if cover_t is not None else 1.2)], check=True, env=env)

def render(spec, out, sid=1, accent=None, cover=None):
    tmp = out + '.tmp'; os.makedirs(tmp, exist_ok=True)
    wav, tl, total = reels2.build_audio(spec['segments'], sid, tmp)
    acc = accent_for(spec.get('series'), accent)
    html = os.path.join(os.path.abspath(tmp), 'reel.html'); open(html, 'w').write(build(spec, tl, total, acc))
    # cover = the hook headline once fully animated in
    ct = min(tl[0][1], 1.4)
    capture(html, out, wav, total, cover, ct)
    shutil.rmtree(tmp, ignore_errors=True)
    return total

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('spec'); ap.add_argument('out'); ap.add_argument('--voice', type=int, default=1)
    ap.add_argument('--accent', choices=list(ACCENTS)); ap.add_argument('--cover')
    a = ap.parse_args(); spec = json.load(open(a.spec))
    print(round(render(spec, a.out, a.voice, a.accent, a.cover), 1), 's')
