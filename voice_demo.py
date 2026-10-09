"""Hands-free Recruitment Data Detective demo. Run: python voice_demo.py"""
from pathlib import Path
import os
import threading
import pandas as pd
from flask import Flask, jsonify, request, render_template_string
from dotenv import load_dotenv
from anomaly_detector import detect_bottlenecks
from investigator import investigate

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
app = Flask(__name__)
lock = threading.Lock()
STAGES = ['applied', 'screened', 'interviewed', 'offered', 'hired']
SCENARIOS = {
    'bottleneck': ('Screening bottleneck', 'bottleneck.csv'),
    'normal': ('Healthy funnel', 'normal.csv'),
    'small': ('Small sample', 'small_sample.csv'),
}

def dataset(scenario):
    if scenario not in SCENARIOS:
        raise ValueError('Unknown scenario')
    df = pd.read_csv(ROOT / 'test_data' / SCENARIOS[scenario][1])
    if df.empty or not {'job_id','stage','days_in_process'} <= set(df.columns):
        raise ValueError('Invalid data')
    if df['job_id'].isna().any() or df['stage'].isna().any():
        raise ValueError('Incomplete data')
    df['stage'] = df['stage'].astype(str).str.lower().str.strip()
    df['days_in_process'] = pd.to_numeric(df['days_in_process'], errors='coerce')
    if not df['stage'].isin(STAGES).all() or df['days_in_process'].isna().any() or (df['days_in_process'] < 0).any():
        raise ValueError('Invalid data')
    return df

def summary(scenario):
    df = dataset(scenario)
    ranks = df['stage'].map({v:i for i,v in enumerate(STAGES)})
    counts = {s:int((ranks >= i).sum()) for i,s in enumerate(STAGES)}
    findings = detect_bottlenecks(df)
    return {'scenario':scenario, 'title':SCENARIOS[scenario][0], 'counts':counts,
            'jobs':int(df['job_id'].nunique()), 'applications':len(df),
            'interview_rate':round(counts['interviewed']/len(df)*100,1),
            'hire_rate':round(counts['hired']/len(df)*100,1),
            'flags':sum(x['status']=='REVIEW' for x in findings), 'findings':findings}

@app.route('/')
def index():
    return render_template_string(HTML)

@app.get('/api/scenario/<scenario>')
def get_scenario(scenario):
    try: return jsonify(summary(scenario))
    except (ValueError, OSError) as e: return jsonify({'error':str(e)}),400

@app.post('/api/investigate')
def run_investigation():
    scenario = (request.get_json(silent=True) or {}).get('scenario','bottleneck')
    if scenario not in SCENARIOS: return jsonify({'error':'Unknown scenario'}),400
    key = os.getenv('GEMINI_API_KEY')
    if not key: return jsonify({'error':'GEMINI_API_KEY missing in .env'}),400
    if not lock.acquire(blocking=False): return jsonify({'error':'An investigation is already running'}),429
    try:
        report, calls = investigate(dataset(scenario),key)
        return jsonify({'report':report,'calls':calls,'call_count':len(calls)})
    except Exception as exc:
        app.logger.exception('Investigation failed')
        return jsonify({'error':f'{type(exc).__name__}: {exc}'}),503
    finally: lock.release()

HTML = r'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Recruitment Data Detective • Hands-free</title>
<style>
:root{--paper:#f6f3e9;--cream:#eee8dc;--ink:#213b32;--muted:#65786a;--green:#2e6048;--sage:#dbe6d8;--line:#d7dbd0;--brown:#a36b48;--white:#fffdf8}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font-family:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif} .frame{max-width:1440px;margin:auto;padding:27px 42px 48px}
.top{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:18px}.brand{font-weight:750;letter-spacing:-.03em;font-size:20px}.brand span{color:var(--brown)}.micro{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--muted);font-weight:750}
.status{font-size:13px;background:#e4eadf;border-radius:30px;padding:9px 16px;color:var(--green)}.hero{display:grid;grid-template-columns:1.5fr .65fr;gap:30px;margin-top:42px;align-items:end}.hero h1{font-family:Georgia,serif;font-size:clamp(40px,5vw,70px);line-height:1.04;letter-spacing:-.055em;font-weight:500;margin:10px 0 17px}.hero p{max-width:700px;color:var(--muted);line-height:1.65;font-size:17px}.detail{border-left:2px solid var(--brown);padding-left:20px;margin-bottom:12px}.detail strong{display:block;font-size:20px;margin-top:9px}.controls{display:flex;gap:12px;margin-top:27px;flex-wrap:wrap}.btn{cursor:pointer;border:1px solid #adc1b1;background:var(--white);color:var(--green);padding:12px 18px;border-radius:9px;font-weight:700}.btn.primary{background:var(--green);color:white;border-color:var(--green)}.btn:focus-visible{outline:3px solid var(--brown)}.listen{font-size:13px;color:var(--muted);min-height:26px;padding-top:12px}
.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin-top:35px}.metric{background:var(--white);border:1px solid var(--line);padding:21px 23px;border-radius:11px}.metric label{display:block;font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.1em;font-weight:700}.metric b{display:block;font-family:Georgia,serif;font-size:37px;font-weight:500;letter-spacing:-.035em;margin-top:7px}.content{display:grid;grid-template-columns:1.45fr 1fr;gap:20px;margin-top:21px}.panel{background:var(--white);border:1px solid var(--line);border-radius:12px;padding:24px 27px}.panel h2{font-family:Georgia,serif;font-size:26px;letter-spacing:-.035em;font-weight:500;margin:0 0 21px}.row{display:grid;grid-template-columns:110px 1fr 48px;align-items:center;gap:13px;margin:16px 0;font-size:13px}.track{background:#e9eee5;height:19px;border-radius:4px;overflow:hidden}.bar{background:#668e73;height:100%;transition:width .6s ease}.row:nth-of-type(3) .bar{background:#8da789}.row:nth-of-type(4) .bar{background:#b99975}.row:nth-of-type(5) .bar{background:#9b795b}.row:nth-of-type(6) .bar{background:#648775}.insight{background:#f6ede1;border-left:4px solid var(--brown);padding:14px 15px;border-radius:7px;margin:10px 0}.insight strong{font-size:13px}.insight p{font-size:13px;line-height:1.5;margin:8px 0 0;color:#705d4b}.section{margin-top:23px}.copy{white-space:pre-wrap;line-height:1.6;font-size:14px;color:#334b3c;max-height:400px;overflow:auto}.evidence{white-space:pre-wrap;font-family:ui-monospace,monospace;font-size:12px;max-height:400px;overflow:auto;background:#edf2e9;padding:16px;border-radius:8px}.foot{margin-top:22px;color:var(--muted);font-size:12px;border-top:1px solid var(--line);padding-top:14px}.hidden{display:none}.pill{background:var(--sage);border-radius:20px;padding:6px 11px;color:var(--green);font-size:11px;font-weight:700}.pulse{width:8px;height:8px;background:#a36b48;display:inline-block;border-radius:50%;margin-right:6px;animation:pulse 1.5s infinite}@keyframes pulse{50%{opacity:.2}}@media(max-width:900px){.frame{padding:18px}.hero,.content{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}}@media(prefers-reduced-motion:reduce){.pulse{animation:none}.bar{transition:none}}
</style></head><body><main class="frame"><header class="top"><div class="brand">FIELDNOTES<span> / </span>Data Detective</div><div class="status" id="micstatus">Voice control not armed</div></header>
<section class="hero"><div><div class="micro">ZEIL HACKATHON 2026 / INVESTIGATION STUDIO</div><h1>Good hiring starts<br>with better evidence.</h1><p>Explore recruitment bottlenecks, examine conversion rates and ask Gemini to investigate the evidence. Designed for a complete hands-free presentation.</p><div class="controls"><button class="btn primary" id="arm" onclick="arm()">Arm microphone</button><button class="btn" onclick="command('investigate')">Test investigation</button><button class="btn" onclick="command('evidence')">Show evidence</button></div><div class="listen" id="heard">Prepare the mic before filming. Then keep both hands visible and off all controls.</div></div><div class="detail"><div class="micro">ACTIVE SCENARIO</div><strong id="scenarioTitle">Screening bottleneck</strong><p class="micro" style="line-height:1.9;letter-spacing:.06em">SAY “START INVESTIGATION”<br>SAY “SHOW EVIDENCE”<br>SAY “SHOW REPORT”<br>SAY “HEALTHY FUNNEL”</p></div></section>
<section class="metrics"><div class="metric"><label>Applications</label><b id="applications">—</b></div><div class="metric"><label>Interview rate</label><b id="interview_rate">—</b></div><div class="metric"><label>Hire rate</label><b id="hire_rate">—</b></div><div class="metric"><label>Review flags</label><b id="flags">—</b></div></section>
<section class="content"><article class="panel"><div class="micro">01 / CANDIDATE PROGRESSION</div><h2>Hiring funnel</h2><div id="funnel"></div><div class="foot">Stage counts are cumulative. Synthetic recruitment data only.</div></article><article class="panel"><div class="micro">02 / INVESTIGATION SIGNALS</div><h2>What deserves attention</h2><div id="findings"></div><div class="foot">REVIEW: &lt;30% conversion with at least 10 preceding candidates. Not proof of causality.</div></article></section>
<section class="panel section hidden" id="ai"><div class="micro">03 / AGENT INVESTIGATION</div><h2 id="panelTitle">Investigation report</h2><div id="aiText" class="copy"></div></section><footer class="foot">FIELDNOTES / RECRUITMENT DATA DETECTIVE <span style="float:right">Evidence first. Hypotheses clearly labeled.</span></footer></main>
<script>
let scenario='bottleneck', report='', calls=[], recognition=null, armed=false, busy=false, speaking=false;
const $=id=>document.getElementById(id);const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function loadScenario(name){scenario=name;report='';calls=[];$('ai').classList.add('hidden');try{const r=await fetch('/api/scenario/'+name),d=await r.json();if(!r.ok)throw Error(d.error);$('scenarioTitle').textContent=d.title;['applications','flags'].forEach(k=>$(k).textContent=d[k]);$('interview_rate').textContent=d.interview_rate+'%';$('hire_rate').textContent=d.hire_rate+'%';let max=d.counts.applied||1;$('funnel').innerHTML=Object.entries(d.counts).map(([k,v])=>`<div class="row"><span>${esc(k[0].toUpperCase()+k.slice(1))}</span><div class="track"><div class="bar" style="width:${100*v/max}%"></div></div><b>${v}</b></div>`).join('');const flagged=d.findings.filter(x=>x.status==='REVIEW');$('findings').innerHTML=flagged.length?flagged.map(x=>`<div class="insight"><strong>${esc(x.job_id)} / ${esc(x.transition)}</strong><p>${x.conversion_pct}% conversion. Review the transition before drawing conclusions.</p></div>`).join(''):'<div class="insight" style="background:#e9f0e7;border-color:#668e73"><strong>No flagged bottlenecks</strong><p>Current rules found no REVIEW transitions. LOW_SAMPLE results still require caution.</p></div>'; const low=d.findings.filter(x=>x.status==='LOW_SAMPLE').length;if(low)$('findings').innerHTML+=`<p style="font-size:13px;color:#68786c">${low} low-sample transition(s); insufficient volume for this rule.</p>`;}catch(e){$('heard').textContent='Unable to load demo data: '+e.message}}
function showReport(){ $('ai').classList.remove('hidden');$('panelTitle').textContent='Investigation report';$('aiText').className='copy';$('aiText').textContent=report||'Run an investigation first.'; $('ai').scrollIntoView({behavior:'smooth',block:'start'});}
function showEvidence(){$('ai').classList.remove('hidden');$('panelTitle').textContent='Function calling / execution trace';$('aiText').className='evidence';$('aiText').textContent=calls.length?JSON.stringify(calls,null,2):'Run an investigation first.';$('ai').scrollIntoView({behavior:'smooth',block:'start'});}
async function command(c){if(c==='investigate'){if(busy)return;busy=true;$('heard').textContent='Gemini is investigating. Please wait…';$('micstatus').textContent='Investigation running';try{const r=await fetch('/api/investigate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scenario})}),d=await r.json();if(!r.ok)throw Error(d.error||'Investigation failed');report=d.report;calls=d.calls||[];showReport();$('heard').textContent=`Investigation complete. ${calls.length} tool call(s). Say “show evidence”.`;}catch(e){$('heard').textContent='Investigation error: '+e.message}finally{busy=false;$('micstatus').textContent=armed?'Listening for commands':'Voice control not armed';}}else if(c==='evidence'){showEvidence()}else if(c==='report'){showReport()}else if(c==='normal'||c==='small'||c==='bottleneck'){await loadScenario(c)}else if(c==='finish'){$('ai').classList.add('hidden');window.scrollTo({top:0,behavior:'smooth'});$('heard').textContent='Demo complete.';}}
function parseSpeech(t){t=t.toLowerCase();if(/(start|run|begin|do).*(investigat|analy)|investigate/.test(t))return'investigate';if(/(show|open).*(evidence|tool|trace)/.test(t))return'evidence';if(/(show|open).*(report|result)/.test(t))return'report';if(/healthy|normal funnel/.test(t))return'normal';if(/small sample/.test(t))return'small';if(/bottleneck|screening scenario/.test(t))return'bottleneck';if(/finish|end demo|reset demo/.test(t))return'finish';return null}
function arm(){const SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){$('heard').textContent='Chrome SpeechRecognition unavailable; check browser settings.';return;}if(armed)return;recognition=new SR();recognition.lang='en-NZ';recognition.continuous=true;recognition.interimResults=false;recognition.onresult=e=>{for(let i=e.resultIndex;i<e.results.length;i++){if(!e.results[i].isFinal)continue;let t=e.results[i][0].transcript;$('heard').textContent='Heard: '+t;let c=parseSpeech(t);if(c)command(c);}};recognition.onerror=e=>{$('heard').textContent='Microphone: '+e.error;if(['not-allowed','service-not-allowed'].includes(e.error)){armed=false;$('micstatus').textContent='Microphone permission needed'}};recognition.onend=()=>{if(armed){setTimeout(()=>{try{recognition.start()}catch(e){}},400)}};try{recognition.start();armed=true;$('micstatus').innerHTML='<span class="pulse"></span>Listening · Hands free';$('arm').textContent='Microphone armed';$('heard').textContent='Ready. Say “start investigation”.';}catch(e){$('heard').textContent=e.message}}
loadScenario('bottleneck');
</script></body></html>'''

if __name__ == '__main__':
    print('Open http://127.0.0.1:8765 in Chrome')
    app.run(host='127.0.0.1', port=8765, debug=False, threaded=True)
