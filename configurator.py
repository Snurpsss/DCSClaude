"""Interface web de configuration du Claude Copilot DCS.

Servie par app.py EN MÊME TEMPS que le copilote (état partagé via core.py) :
les changements s'appliquent à la volée, sans redémarrer.
"""
import os
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import numpy as np
import sounddevice as sd
from flask import Flask, jsonify, request

import dcs_config
import ptt
import audioio
import tts
import srs
import core
import voices
import personas

app = Flask(__name__)
STATE = core.STATE  # état partagé avec la boucle du copilote


PAGE = """<!doctype html><html lang=fr><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>Claude Copilot DCS — Configuration</title>
<style>
 :root{--bg:#0d1117;--card:#161b22;--bd:#30363d;--fg:#e6edf3;--mut:#8b949e;
       --acc:#3fb950;--acc2:#1f6feb;--warn:#d29922}
 *{box-sizing:border-box} body{margin:0;font-family:Segoe UI,system-ui,sans-serif;
   background:var(--bg);color:var(--fg);padding:24px}
 h1{font-size:20px;margin:0 0 4px} .sub{color:var(--mut);margin:0 0 20px;font-size:13px}
 .card{background:var(--card);border:1px solid var(--bd);border-radius:10px;
   padding:18px;margin-bottom:16px;max-width:640px}
 .card h2{font-size:15px;margin:0 0 12px;display:flex;align-items:center;gap:8px}
 .num{background:var(--acc2);color:#fff;border-radius:50%;width:22px;height:22px;
   display:inline-flex;align-items:center;justify-content:center;font-size:13px}
 button{background:var(--acc2);color:#fff;border:0;border-radius:6px;padding:9px 14px;
   font-size:14px;cursor:pointer} button:hover{filter:brightness(1.1)}
 button.ghost{background:#21262d;border:1px solid var(--bd)}
 select{background:#0d1117;color:var(--fg);border:1px solid var(--bd);border-radius:6px;
   padding:8px;font-size:14px;width:100%}
 .val{font-weight:600;color:var(--acc)} .row{display:flex;gap:10px;align-items:center;
   flex-wrap:wrap;margin-top:10px}
 .led{width:16px;height:16px;border-radius:50%;background:#30363d;transition:.05s}
 .led.on{background:var(--acc);box-shadow:0 0 12px var(--acc)}
 .msg{font-size:13px;color:var(--mut);margin-top:8px;min-height:18px}
 .ok{color:var(--acc)} .warn{color:var(--warn)}
 .save{background:var(--acc)} kbd{background:#21262d;border:1px solid var(--bd);
   border-radius:4px;padding:2px 6px;font-family:monospace}
 .prow{display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap;
   border-top:1px solid var(--bd);padding:10px 0}
 .prow label{font-size:11px;color:var(--mut);display:flex;flex-direction:column;gap:3px}
 .prow input[type=text]{width:100px} .prow select{width:auto;padding:6px}
</style></head><body>
<h1>🎙️ Claude Copilot DCS — Configuration</h1>
<p class=sub>Choisis ton push-to-talk et ton micro, puis teste. Enregistré dans <kbd>config.json</kbd>.</p>

<div class=card style="max-width:920px">
 <h2>🎭 Personas (opérateurs)</h2>
 <div id=personas></div>
 <div class=row>
   <button class=ghost onclick=addPersona()>➕ Ajouter un persona</button>
   <button class=ghost onclick=testCallsign()>🎤 Tester un indicatif (parle après le clic)</button>
   <span id=csMsg class=msg></span>
 </div>
 <div class=row style=margin-top:8px>
   <label>Mode PTT <select id=pttMode style=width:auto>
     <option value=global>Un seul PTT pour tous</option>
     <option value=per_persona>Un PTT par persona</option>
   </select></label>
   <label><input type=checkbox id=freqReq> Fréquence obligatoire pour joindre un persona (F-18)</label>
 </div>
 <div class=sub style=margin-top:8px>
   Chaque persona a son <b>indicatif</b>, sa <b>fréquence</b>, sa <b>langue</b>, sa
   <b>voix</b> et son <b>rôle</b>. Adresse-le à la voix par son indicatif
   (ex : « Overlord, picture »). Le persona « <b>Défaut</b> » reçoit ce qui n'a pas
   d'indicatif. (Routage par fréquence F-18 et bouton PTT par persona : à venir.)
 </div>
</div>

<div class=card>
 <h2><span class=num>1</span> Push-to-talk (global)</h2>
 <div>Actuel : <span class=val id=pttLabel>…</span></div>
 <div class=row>
   <button onclick=capture()>🎯 Capturer une touche / un bouton</button>
   <span id=capMsg class=msg></span>
 </div>
 <div class=row>
   <div class=led id=led></div><span id=pttState class=msg>Test : appuie sur ton bouton PTT…</span>
 </div>
 <div class=sub style=margin-top:8px>
   Appuie sur n'importe quelle <b>touche clavier</b> ou <b>bouton HOTAS/joystick</b> de ton cockpit.
   La LED s'allume quand le PTT est enfoncé.
 </div>
</div>

<div class=card>
 <h2><span class=num>2</span> Microphone</h2>
 <select id=mic></select>
 <div class=row>
   <button class=ghost onclick=testMic()>🎧 Tester le micro (parle 4 s)</button>
   <span id=micMsg class=msg></span>
 </div>
 <div class=sub style=margin-top:8px>Le périphérique d'entrée utilisé pour t'écouter.</div>
</div>

<div class=card>
 <h2><span class=num>3</span> Reconnaissance vocale</h2>
 <div class=row style=margin-top:0>
   <label>Langue parlée <select id=spoken style=width:auto></select></label>
   <label>Modèle <select id=model style=width:auto></select></label>
 </div>
 <div class=sub style=margin-top:8px>
   La <b>langue parlée</b> règle la reconnaissance ET la langue des réponses de Claude.
   Whisper est <b>multilingue</b> : un seul modèle gère toutes les langues (rien à
   télécharger par langue pour la reconnaissance). Choisis juste une <b>voix</b> de la
   même langue plus bas.
   <br>Tout tourne <b>en local sur le CPU</b> (GPU libre pour la VR). <b>base</b> = rapide ·
   <b>small</b> = équilibré · <b>medium</b> = précis. <b>medium</b> recommandé si ton CPU suit.
 </div>
</div>

<div class=card>
 <h2><span class=num>4</span> Sortie voix (TTS)</h2>
 <div class=row style=margin-top:0>
   <label>Moteur <select id=ttsengine style=width:auto>
     <option value=piper>Piper (neuronal local)</option>
     <option value=sapi>SAPI (voix Windows)</option>
   </select></label>
   <label>Voix Piper <select id=pipervoice style=width:auto></select></label>
 </div>
 <div class=row>
   <label>Langue <select id=voiceLang style=max-width:220px></select></label>
   <label>Voix <select id=voiceDl style=max-width:240px></select></label>
   <button class=ghost onclick=downloadVoice()>⬇️ Télécharger</button>
 </div>
 <div class=row style=margin-top:4px><span id=voiceDlMsg class=msg></span></div>
 <div style=margin-top:10px>Périphérique de sortie :</div>
 <select id=ttsout></select>
 <div class=row>
   <button class=ghost onclick=testVoice()>🔊 Tester la voix</button>
   <span id=voiceMsg class=msg></span>
 </div>
 <div class=sub style=margin-top:8px>
   En VR, choisis ton <b>casque</b> (ex. « Oculus Virtual Audio Device ») pour entendre
   Claude dans le casque. Pour l'entendre <b>à la radio en jeu</b>, configure DCS-SRS ci-dessous.
 </div>
</div>

<div class=card>
 <h2><span class=num>5</span> Radio en jeu (DCS-SRS) <span id=srsBadge class=sub></span></h2>
 <div class=row>
   <label><input type=radio name=vmode value=headset onchange=setMode(this.value)> Casque VR</label>
   <label><input type=radio name=vmode value=srs onchange=setMode(this.value)> Radio SRS</label>
 </div>
 <div style=margin-top:10px>Chemin de <kbd>DCS-SRS-ExternalAudio.exe</kbd> :</div>
 <input id=srsPath type=text style="width:100%;margin-top:4px" placeholder="C:\\Program Files\\DCS-SimpleRadio-Standalone\\DCS-SRS-ExternalAudio.exe">
 <div class=row>
   <label>Fréq (MHz) <input id=srsFreq type=text style=width:80px></label>
   <label>Mod <select id=srsMod style=width:70px><option>AM</option><option>FM</option></select></label>
   <label>Coalition <select id=srsCoal style=width:90px><option value=2>Bleu</option><option value=1>Rouge</option></select></label>
 </div>
 <div class=row>
   <button class=ghost onclick=testSrs()>📻 Tester la radio SRS</button>
   <span id=srsMsg class=msg></span>
 </div>
 <div class=sub style=margin-top:8px>
   Nécessite SRS installé + un serveur SRS lancé + le client SRS connecté, radio réglée sur la fréquence.
 </div>
</div>

<div class=card>
 <h2><span class=num>6</span> Affichage / actions en jeu</h2>
 <div class=row style=margin-top:0>
   <button class=ghost onclick=testControl()>🖥️ Tester</button>
   <span id=ctrlMsg class=msg></span>
 </div>
 <div class=sub style=margin-top:8px>
   Requiert le hook <kbd>dcs_claude_control.lua</kbd> dans
   <kbd>Saved Games\\DCS\\Scripts\\Hooks\\</kbd> et une mission en cours. Le test affiche
   un message à l'écran DCS. C'est ce canal qui permet l'affichage des réponses et le spawn.
 </div>
</div>

<div class=card>
 <h2>🧠 Cerveau (IA)</h2>
 <div class=row style=margin-top:0>
   <label>Fournisseur <select id=llmProv style=width:auto>
     <option value=anthropic>Anthropic (Claude)</option>
     <option value=openai>OpenAI</option>
     <option value=ollama>Ollama (local)</option>
   </select></label>
   <label>Modèle <input id=llmModel type=text style=width:200px placeholder="(défaut du fournisseur)"></label>
 </div>
 <div class=row>
   <label>URL API <input id=llmBase type=text style=width:300px placeholder="(défaut ; ollama: http://localhost:11434/v1)"></label>
 </div>
 <div class=row id=keyRow>
   <label>Clé API <input id=llmKey type=password style=width:240px placeholder="coller la clé ici"></label>
   <button class=ghost onclick=saveKey()>🔑 Enregistrer la clé</button>
   <span id=keyMsg class=msg></span>
 </div>
 <div class=sub style=margin-top:8px>
   Le fournisseur doit gérer le <b>tool calling</b>. La clé est stockée localement
   (<kbd>apikey.txt</kbd> / <kbd>openai_key.txt</kbd>) et n'est jamais affichée en clair.
   <b>Ollama</b> = 100&nbsp;% local, aucune clé. Changer de fournisseur réinitialise
   l'historique de conversation.
 </div>
</div>

<div class=card style="max-width:640px;display:flex;justify-content:space-between;align-items:center">
   <span id=saveMsg class=msg></span>
   <button class=save onclick=save()>💾 Enregistrer la configuration</button>
</div>

<script>
let cfg={};
async function j(u,o){const r=await fetch(u,o);return r.json()}
function setLabel(){document.getElementById('pttLabel').textContent=cfg.ptt?cfg.ptt.label:'aucun'}
async function load(){
  cfg=await j('/api/config');
  setLabel();
  const mics=await j('/api/mics');
  const sel=document.getElementById('mic');sel.innerHTML='';
  const def=document.createElement('option');def.value='';def.textContent='(Défaut système)';sel.appendChild(def);
  mics.forEach(m=>{const o=document.createElement('option');o.value=m.index;o.dataset.name=m.name;
    o.textContent='#'+m.index+' — '+m.name+' ['+m.hostapi+']';
    if(cfg.mic_device_name===m.name||(!cfg.mic_device_name&&cfg.mic_device===m.index))o.selected=true;
    sel.appendChild(o)});
  sel.onchange=()=>{cfg.mic_device=sel.value===''?null:parseInt(sel.value);
    cfg.mic_device_name=sel.value===''?'':sel.options[sel.selectedIndex].dataset.name};
  const ms=document.getElementById('model');ms.innerHTML='';
  ['base','small','medium','large-v3'].forEach(name=>{const o=document.createElement('option');
    o.value=name;o.textContent=name;if(cfg.whisper_model===name)o.selected=true;ms.appendChild(o)});
  ms.onchange=()=>{cfg.whisper_model=ms.value};
  const langs=await j('/api/languages');
  const sp2=document.getElementById('spoken');sp2.innerHTML='';
  langs.forEach(l=>{const o=document.createElement('option');o.value=l.code;o.textContent=l.label;
    if((cfg.language||'fr')===l.code)o.selected=true;sp2.appendChild(o)});
  sp2.onchange=()=>{cfg.language=sp2.value;save(true);syncVoiceLang(sp2.value)};
  const outs=await j('/api/tts_outputs');
  const os=document.getElementById('ttsout');os.innerHTML='';
  const od=document.createElement('option');od.value='';od.textContent='(Défaut Windows)';os.appendChild(od);
  outs.forEach(o2=>{const o=document.createElement('option');o.value=o2.name;o.textContent=o2.name;
    if(cfg.tts_output_name===o2.name)o.selected=true;os.appendChild(o)});
  os.onchange=()=>{cfg.tts_output_name=os.value};
  const te=document.getElementById('ttsengine');te.value=cfg.tts_engine||'piper';
  te.onchange=()=>{cfg.tts_engine=te.value};
  await loadVoices();
  // --- SRS ---
  document.querySelector('input[name=vmode][value='+(cfg.voice_mode||'headset')+']').checked=true;
  const sp=document.getElementById('srsPath');sp.value=cfg.srs_exe_path||'';
  sp.onchange=()=>{cfg.srs_exe_path=sp.value};
  const sf=document.getElementById('srsFreq');sf.value=cfg.srs_freq||'251';
  sf.onchange=()=>{cfg.srs_freq=sf.value};
  const sm=document.getElementById('srsMod');sm.value=cfg.srs_modulation||'AM';
  sm.onchange=()=>{cfg.srs_modulation=sm.value};
  const sc=document.getElementById('srsCoal');sc.value=String(cfg.srs_coalition||2);
  sc.onchange=()=>{cfg.srs_coalition=parseInt(sc.value)};
}
let _roles=[],_pvoices=[];
async function renderPersonas(){
  if(!_roles.length)_roles=await j('/api/roles');
  _pvoices=await j('/api/piper_voices');
  const langs=await j('/api/languages');
  const sel=(arr,val,vk,lk)=>arr.map(o=>'<option value="'+o[vk]+'"'+(o[vk]===val?' selected':'')+'>'+o[lk]+'</option>').join('');
  const box=document.getElementById('personas');
  box.innerHTML=(cfg.personas||[]).map((p,i)=>
    '<div class=prow>'+
    '<label>Défaut<input type=radio name=activep '+(cfg.active_persona===p.id?'checked':'')+' data-idx="'+i+'" data-act="active"></label>'+
    '<label>Actif<input type=checkbox '+(p.enabled!==false?'checked':'')+' data-idx="'+i+'" data-field="enabled"></label>'+
    '<label>Indicatif<input type=text value="'+(p.callsign||'')+'" data-idx="'+i+'" data-field="callsign"></label>'+
    '<label>Fréq<input type=text value="'+(p.freq||'')+'" data-idx="'+i+'" data-field="freq"></label>'+
    '<label>Langue<select data-idx="'+i+'" data-field="language">'+sel(langs,p.language,'code','label')+'</select></label>'+
    '<label>Voix<select data-idx="'+i+'" data-field="voice">'+_pvoices.map(v=>'<option value="'+v.path+'"'+(v.path===p.voice?' selected':'')+'>'+v.name+'</option>').join('')+'</select></label>'+
    '<label>Rôle<select data-idx="'+i+'" data-field="role">'+sel(_roles,p.role,'key','label')+'</select></label>'+
    '<label>PTT dédié<span style="display:flex;gap:4px;align-items:center">'+
      '<span style="font-size:11px;max-width:110px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">'+(p.ptt?p.ptt.label:'—')+'</span>'+
      '<button class=ghost data-idx="'+i+'" data-act="ptt" title="Capturer">🎯</button>'+
      (p.ptt?'<button class=ghost data-idx="'+i+'" data-act="pttclr" title="Effacer">✖</button>':'')+
    '</span></label>'+
    '<label>&nbsp;<button class=ghost data-idx="'+i+'" data-act="del">🗑</button></label>'+
    '</div>').join('');
}
async function testCallsign(){
  const m=document.getElementById('csMsg');
  m.textContent='🎤 Parle maintenant (3 s)… dis un indicatif';m.className='msg warn';
  const r=await j('/api/test_callsign',{method:'POST'});
  if(!r.ok){m.textContent='⚠ '+(r.error||'erreur');m.className='msg warn';return}
  if(r.persona){m.textContent='✔ Reconnu : '+r.persona+'  (entendu : “'+(r.heard||'')+'”)';m.className='msg ok'}
  else{m.textContent='✖ Non reconnu  (entendu : “'+(r.heard||'')+'”)';m.className='msg warn'}
}
function wireLlm(){
  const p=document.getElementById('llmProv');p.value=cfg.llm_provider||'anthropic';
  p.onchange=()=>{cfg.llm_provider=p.value;save(true);refreshKey()};
  const m=document.getElementById('llmModel');m.value=cfg.llm_model||'';
  m.onchange=()=>{cfg.llm_model=m.value;save(true)};
  const b=document.getElementById('llmBase');b.value=cfg.llm_base_url||'';
  b.onchange=()=>{cfg.llm_base_url=b.value;save(true)};
  refreshKey();
}
async function refreshKey(){
  const r=await j('/api/apikey?provider='+encodeURIComponent(cfg.llm_provider||'anthropic'));
  const row=document.getElementById('keyRow'),m=document.getElementById('keyMsg');
  row.style.display=r.needs?'flex':'none';
  if(!r.needs){return}
  m.textContent=r.present?('✔ clé enregistrée : '+r.masked):'⚠ aucune clé — requise pour démarrer';
  m.className=r.present?'msg ok':'msg warn';
}
async function saveKey(){
  const inp=document.getElementById('llmKey'),m=document.getElementById('keyMsg');
  const key=inp.value.trim();
  if(!key){m.textContent='Colle une clé.';m.className='msg';return}
  const r=await j('/api/apikey',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({provider:cfg.llm_provider||'anthropic',key})});
  if(r.ok){inp.value='';m.textContent='✔ clé enregistrée : '+r.masked;m.className='msg ok'}
  else{m.textContent='⚠ '+(r.error||'échec');m.className='msg warn'}
}
function wirePersonaOpts(){
  const pm=document.getElementById('pttMode');pm.value=cfg.ptt_mode||'global';
  pm.onchange=()=>{cfg.ptt_mode=pm.value;save(true)};
  const fr=document.getElementById('freqReq');fr.checked=!!cfg.freq_required;
  fr.onchange=()=>{cfg.freq_required=fr.checked;save(true)};
}
function addPersona(){
  cfg.personas=cfg.personas||[];
  cfg.personas.push({id:'p'+Date.now(),callsign:'Nouveau',freq:'',language:(cfg.language||'fr'),
    voice:(_pvoices[0]&&_pvoices[0].path)||'',role:'operator',enabled:true});
  save(true);renderPersonas();
}
function wirePersonas(){
  const box=document.getElementById('personas');
  box.addEventListener('change',e=>{const t=e.target,i=+t.dataset.idx;if(isNaN(i))return;
    if(t.dataset.act==='active'){cfg.active_persona=cfg.personas[i].id;save(true);return;}
    const f=t.dataset.field;if(!f)return;
    cfg.personas[i][f]=(t.type==='checkbox')?t.checked:t.value;save(true);});
  box.addEventListener('click',e=>{const t=e.target,i=+t.dataset.idx;const a=t.dataset.act;
    if(a==='del'){cfg.personas.splice(i,1);save(true);renderPersonas();}
    else if(a==='ptt'){capturePersona(i);}
    else if(a==='pttclr'){delete cfg.personas[i].ptt;save(true);renderPersonas();}});
}
function setMode(v){cfg.voice_mode=v}
async function loadVoices(){
  const inst=await j('/api/piper_voices');
  const pv=document.getElementById('pipervoice');pv.innerHTML='';
  if(inst.length===0){const o=document.createElement('option');o.value='';o.textContent='(aucune — télécharge une voix)';pv.appendChild(o)}
  inst.forEach(v=>{const o=document.createElement('option');o.value=v.path;o.textContent=v.name;
    if(cfg.piper_model_path===v.path)o.selected=true;pv.appendChild(o)});
  pv.onchange=()=>{cfg.piper_model_path=pv.value;save(true)};
}
let voiceLangLoaded=false;
async function loadLangs(){
  const lang=document.getElementById('voiceLang');
  const r=await j('/api/voice_langs');
  lang.innerHTML='';
  if(!r.ok){const o=document.createElement('option');o.textContent='(hors ligne)';lang.appendChild(o);return}
  r.langs.forEach(l=>{const o=document.createElement('option');o.value=l.code;o.textContent=l.label;
    if(l.code==='fr_FR')o.selected=true;lang.appendChild(o)});
  lang.onchange=loadCatalog;
  voiceLangLoaded=true;
  await loadCatalog();
}
function syncVoiceLang(code){
  const vl=document.getElementById('voiceLang'); if(!vl||!vl.options.length) return;
  for(const o of vl.options){ if(o.value.slice(0,2)===code){ vl.value=o.value; break; } }
  loadCatalog();
}
async function loadCatalog(){
  const lang=document.getElementById('voiceLang').value;
  const dl=document.getElementById('voiceDl');dl.innerHTML='';
  const r=await j('/api/voice_catalog?lang='+encodeURIComponent(lang));
  (r.voices||[]).forEach(v=>{const o=document.createElement('option');o.value=v.key;
    o.textContent=(v.installed?'✓ ':'')+v.label;dl.appendChild(o)});
}
async function downloadVoice(){
  if(!voiceLangLoaded)return;
  const key=document.getElementById('voiceDl').value;
  const m=document.getElementById('voiceDlMsg');
  if(!key){m.textContent='Choisis une voix.';m.className='msg';return}
  m.textContent='⬇️ Téléchargement de '+key+'… (patiente, ça peut prendre 1 min)';m.className='msg warn';
  const r=await j('/api/download_voice',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key})});
  if(r.ok){cfg.piper_model_path=r.path;cfg.tts_engine='piper';await save(true);
    await loadVoices();await loadCatalog();
    document.getElementById('pipervoice').value=r.path;
    document.getElementById('ttsengine').value='piper';
    m.textContent='✔ '+key+' installée et sélectionnée.';m.className='msg ok';}
  else{m.textContent='⚠ '+(r.error||'échec');m.className='msg warn';}
}
async function capture(){
  const m=document.getElementById('capMsg');m.textContent='⏳ Appuie sur une touche ou un bouton…';m.className='msg warn';
  const r=await j('/api/capture',{method:'POST'});
  if(r.binding){cfg.ptt=r.binding;setLabel();save(true);m.textContent='✔ '+r.binding.label;m.className='msg ok'}
  else{m.textContent='Rien détecté (timeout).';m.className='msg'}
}
async function capturePersona(i){
  const m=document.getElementById('csMsg');
  m.textContent='⏳ Appuie sur le bouton/touche pour '+(cfg.personas[i].callsign||'?')+'…';m.className='msg warn';
  const r=await j('/api/capture',{method:'POST'});
  if(r.binding){cfg.personas[i].ptt=r.binding;save(true);renderPersonas();
    m.textContent='✔ '+cfg.personas[i].callsign+' → '+r.binding.label;m.className='msg ok'}
  else{m.textContent='Rien détecté (timeout).';m.className='msg'}
}
async function testMic(){
  const m=document.getElementById('micMsg');m.textContent='⏳ Enregistrement 4 s… parle !';m.className='msg warn';
  const r=await j('/api/test_mic',{method:'POST'});
  if(r.error){m.textContent='⚠ '+r.error;m.className='msg warn';return}
  m.innerHTML='Niveau : '+r.level_bar+'  —  Transcription : <span class=ok>“'+(r.text||'(rien)')+'”</span>';m.className='msg';
}
async function testVoice(){
  const m=document.getElementById('voiceMsg');m.textContent='🔊 Lecture…';m.className='msg warn';
  await save(true);   // applique le moteur/voix/sortie choisis avant de tester
  const r=await j('/api/test_voice',{method:'POST'});
  m.textContent=r.ok?'✔ Rien entendu ? Change la sortie ci-dessus.':'⚠ '+(r.error||'erreur');
  m.className=r.ok?'msg ok':'msg warn';
}
async function testSrs(){
  const m=document.getElementById('srsMsg');m.textContent='📻 Transmission…';m.className='msg warn';
  await save(true);   // sauvegarde prealable pour transmettre chemin et frequence au serveur
  const r=await j('/api/test_srs',{method:'POST'});
  m.textContent=r.ok?'✔ Transmis. Radio réglée sur la fréquence ?':'⚠ '+(r.error||'erreur');
  m.className=r.ok?'msg ok':'msg warn';
}
async function testControl(){
  const m=document.getElementById('ctrlMsg');m.textContent='🖥️ Connexion…';m.className='msg warn';
  await save(true);
  const r=await j('/api/test_control',{method:'POST'});
  m.textContent=r.ok?'✔ Message envoyé à DCS.':'⚠ '+(r.error||'erreur');
  m.className=r.ok?'msg ok':'msg warn';
}
async function save(silent){
  const r=await j('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)});
  if(!silent){const m=document.getElementById('saveMsg');
    m.textContent=r.ok?'✔ Appliqué à la volée (copilote mis à jour).':'Erreur';m.className='msg ok';}
}
async function pollPTT(){
  try{const r=await j('/api/ptt_state');
    document.getElementById('led').className='led'+(r.pressed?' on':'');
    document.getElementById('pttState').textContent=r.pressed?'PTT ENFONCÉ ✔':'Test PTT : appuie sur ton bouton…';
  }catch(e){}
  setTimeout(pollPTT,100);
}
load().then(()=>{wirePersonas();renderPersonas();wirePersonaOpts();wireLlm();});loadLangs();pollPTT();
</script></body></html>"""


@app.get("/")
def index():
    return PAGE


@app.get("/api/config")
def api_get_config():
    return jsonify(core.get_config())


@app.post("/api/config")
def api_set_config():
    data = request.get_json(force=True)
    core.update_config(data)          # applique + persiste + réaligne le monitor
    return jsonify({"ok": True})


@app.get("/api/mics")
def api_mics():
    return jsonify(audioio.list_input_devices())


@app.get("/api/languages")
def api_languages():
    return jsonify(dcs_config.SPOKEN_LANGUAGES)


@app.get("/api/roles")
def api_roles():
    return jsonify([{"key": k, "label": v["label"]} for k, v in personas.ROLES.items()])


@app.get("/api/apikey")
def api_get_key():
    import apikeys
    cfg = core.get_config()
    prov = request.args.get("provider") or cfg.get("llm_provider", "anthropic")
    k = apikeys.current_key(prov, cfg)
    return jsonify({"provider": prov, "present": bool(k),
                    "masked": apikeys.masked(k), "needs": prov != "ollama"})


@app.post("/api/apikey")
def api_set_key():
    import apikeys
    cfg = core.get_config()
    data = request.get_json(force=True) or {}
    prov = data.get("provider") or cfg.get("llm_provider", "anthropic")
    try:
        apikeys.save_key(prov, data.get("key", ""), cfg)
        core.STATE["llm"] = None          # reconstruit le client avec la nouvelle clé
        core.STATE["llm_key"] = None
        k = apikeys.current_key(prov, cfg)
        return jsonify({"ok": True, "masked": apikeys.masked(k), "present": bool(k)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.get("/api/piper_voices")
def api_piper_voices():
    return jsonify(tts.list_piper_voices(dcs_config.PIPER_VOICES_DIR))


@app.get("/api/voice_langs")
def api_voice_langs():
    try:
        return jsonify({"ok": True, "langs": voices.languages()})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "langs": []})


@app.get("/api/voice_catalog")
def api_voice_catalog():
    lang = request.args.get("lang", "")
    try:
        return jsonify({"ok": True, "voices": voices.voices_for(lang)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e), "voices": []})


@app.post("/api/download_voice")
def api_download_voice():
    key = (request.get_json(force=True) or {}).get("key", "")
    try:
        path = voices.download(key)
        return jsonify({"ok": True, "path": path})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.post("/api/capture")
def api_capture():
    if not STATE["capture_lock"].acquire(blocking=False):
        return jsonify({"binding": None, "busy": True})
    try:
        STATE["monitor"].pause()          # libère le joystick pendant la capture
        binding = ptt.capture_binding(timeout=15.0)
        # On renvoie juste le binding ; l'appelant décide (PTT global ou persona).
        return jsonify({"binding": binding})
    finally:
        STATE["monitor"].resume()
        STATE["capture_lock"].release()


@app.get("/api/ptt_state")
def api_ptt_state():
    return jsonify({"pressed": bool(STATE["monitor"].pressed)})


@app.get("/api/tts_outputs")
def api_tts_outputs():
    return jsonify(tts.list_outputs())


@app.post("/api/test_voice")
def api_test_voice():
    try:
        core.speak(tts.test_phrase(core.get_config()))
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.get("/api/srs_status")
def api_srs_status():
    return jsonify({"available": srs.available(core.get_config())})


@app.post("/api/test_srs")
def api_test_srs():
    try:
        srs.transmit(core.get_config(), "Copilote sur la radio. Test un deux trois.")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.post("/api/test_control")
def api_test_control():
    try:
        cli = core.get_control()
        if cli is None:
            return jsonify({"ok": False, "error": "Backend « Désactivé » — choisis Hook Lua ou DCS-gRPC."})
        if not cli.ping():
            return jsonify({"ok": False,
                            "error": "Pas de réponse. Es-tu EN MISSION (non en pause) ? Hook/mod installé ?"})
        reply = cli.out_text("Claude Copilot connecté.", 10)
        # reply == "ERR: ..." révèle un souci d'exécution côté mission (diagnostic).
        if isinstance(reply, str) and reply.startswith("ERR"):
            return jsonify({"ok": False, "error": f"DCS a répondu : {reply}"})
        return jsonify({"ok": True, "reply": reply})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})


@app.post("/api/test_callsign")
def api_test_callsign():
    cfg = core.get_config()
    sr, dur = 16000, 3.0
    try:
        dev = audioio.resolve_input_device(cfg.get("mic_device_name"), cfg.get("mic_device"))
        audio = sd.rec(int(dur * sr), samplerate=sr, channels=1, dtype="float32",
                       device=dev, extra_settings=audioio.input_extra_settings(dev))
        sd.wait()
        audio = audio.flatten()
    except Exception as e:
        return jsonify({"ok": False, "error": f"micro inutilisable : {e}"})
    try:
        heard = core.transcribe(audio, cfg["language"])
    except Exception as e:
        return jsonify({"ok": False, "error": f"transcription impossible : {e}"})
    p = personas.match_callsign(heard, cfg.get("personas", []))
    try:
        if p:
            core.speak_as(p.get("voice"), f"{p['callsign']}, reconnu.")
        else:
            core.speak("Indicatif non reconnu.")
    except Exception:
        pass
    return jsonify({"ok": True, "heard": heard,
                    "persona": p["callsign"] if p else None})


@app.post("/api/test_mic")
def api_test_mic():
    cfg = core.get_config()
    sr = 16000
    dur = 4.0
    try:
        dev = audioio.resolve_input_device(cfg.get("mic_device_name"),
                                           cfg.get("mic_device"))
        audio = sd.rec(int(dur * sr), samplerate=sr, channels=1,
                       dtype="float32", device=dev,
                       extra_settings=audioio.input_extra_settings(dev))
        sd.wait()
        audio = audio.flatten()
    except Exception as e:
        return jsonify({"error": f"micro inutilisable : {e}"})

    rms = float(np.sqrt(np.mean(audio ** 2))) if audio.size else 0.0
    bars = min(20, int(rms * 400))
    level_bar = "█" * bars + "░" * (20 - bars)

    try:
        text = core.transcribe(audio, cfg["language"])
    except Exception as e:
        return jsonify({"error": f"transcription impossible : {e}", "level_bar": level_bar})

    return jsonify({"level_bar": level_bar, "text": text})
