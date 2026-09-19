/* Show Network frontend bundle - generated from the modular panels. */
const SHOW_NETWORK_FRONTEND_VERSION = "0.15.19-dev29";
const SHOW_NETWORK_FRONTEND_BUILD = "functional-chain-audit-20260918-dev31";
window.__SHOW_NETWORK_FRONTEND__ = Object.freeze({version: SHOW_NETWORK_FRONTEND_VERSION, build: SHOW_NETWORK_FRONTEND_BUILD});
console.info(`[Show Network] frontend ${SHOW_NETWORK_FRONTEND_VERSION} (${SHOW_NETWORK_FRONTEND_BUILD})`);
function snDefine(name, ctor){
  if (!customElements.get(name)) customElements.define(name, ctor);
}

/* ===== control-sources-panel.js ===== */
class ControlSourcesPanel extends HTMLElement {
 connectedCallback(){this.innerHTML=`
 <style>
 :host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}
 h2{margin:0}.sub{font-size:11px;color:#8d969f;margin:5px 0 15px}
 .grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
 .card{background:#15181c;border:1px solid #2c3239;border-radius:10px;padding:15px}
 .title{font-weight:700;font-size:16px}.desc{font-size:11px;color:#aab1b8;margin:7px 0 12px}
 .tag{display:inline-block;border:1px solid #3a4148;border-radius:5px;padding:4px 7px;font-size:9px;margin:2px}
 .green{color:#65dc99}.muted{color:#8d969f}
 </style>
 <h2>CONTROL SOURCES</h2>
 <div class="sub">Sources d'entrée pour le Mapping Engine</div>
 <div class="grid">
  <div class="card"><div class="title">◎ OSC IN</div><div class="desc">Contrôleurs réseau, grandMA3, consoles son, médiaserveurs, Hue/HA et OSC générique.</div><span class="tag green">RECEIVE</span><span class="tag">LEARN</span><span class="tag">MAPPING</span></div>
  <div class="card"><div class="title">♫ MIDI IN</div><div class="desc">CC, notes, pitch bend et contrôleurs MIDI pour déclencher ou piloter les mêmes destinations.</div><span class="tag green">RECEIVE</span><span class="tag">LEARN</span><span class="tag">MAPPING</span></div>
 </div>`}
}
snDefine("control-sources-panel",ControlSourcesPanel);


/* ===== device-fingerprint-panel.js ===== */
class ShowNetworkFingerprint extends HTMLElement {
 connectedCallback(){this.innerHTML=`
 <style>
 :host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}
 h2{margin:0}.sub{color:#8d969f;font-size:11px;margin:5px 0 15px}
 .flow{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
 .box{background:#15181c;border:1px solid #2c3239;border-radius:9px;padding:12px 16px;font-size:11px}
 .arrow{color:#65dc99;font-size:18px}.ok{color:#65dc99}.warn{color:#e6bd67}.muted{color:#8d969f}
 .note{margin-top:15px;background:#15181c;border-left:3px solid #65dc99;padding:12px;font-size:11px;line-height:1.5}
 </style>
 <h2>DEVICE FINGERPRINTS</h2>
 <div class="sub">Identification uniquement à partir d'éléments réellement observés</div>
 <div class="flow">
  <div class="box">IP / hostname</div><div class="arrow">→</div>
  <div class="box">DHCP / mDNS</div><div class="arrow">→</div>
  <div class="box">Protocol evidence</div><div class="arrow">→</div>
  <div class="box">HTTP/API/SNMP</div><div class="arrow">→</div>
  <div class="box ok">CONFIRMED</div>
 </div>
 <div class="note"><b>Conservative mode:</b> une IP ouverte n'est jamais suffisante pour déclarer « GigaCore », « grandMA3 » ou « Dante ». Les champs non prouvés restent <span class="muted">—</span>.</div>`}
}
snDefine("show-network-fingerprint",ShowNetworkFingerprint);


/* ===== manufacturer-brand-catalog.js ===== */
const SHOW_NETWORK_BRAND_STORAGE = 'show_network_custom_brands_v1';
class ShowNetworkBrandStore {
  static async loadCatalog(){
    if(this.catalog)return this.catalog;
    try{
      const r=await fetch('/api/dmx_monitor/static/data/brands.json',{cache:'no-store'});
      this.catalog=await r.json();
    }catch(e){this.catalog={categories:{lighting:'Lumière',audio:'Son',video:'Vidéo',network:'Réseaux',show_control:'Contrôle spectacle',intercom:'Intercom / Communication'},brands:[]};}
    return this.catalog;
  }
  static custom(){try{return JSON.parse(localStorage.getItem(SHOW_NETWORK_BRAND_STORAGE)||'[]')}catch(e){return []}}
  static saveCustom(rows){localStorage.setItem(SHOW_NETWORK_BRAND_STORAGE,JSON.stringify(rows));}
  static async all(){const c=await this.loadCatalog(); return [...(c.brands||[]),...this.custom().map(x=>({...x,custom:true}))]}
  static async find(name){const n=String(name||'').trim().toLowerCase(); if(!n)return null; const rows=await this.all(); return rows.find(x=>x.name.toLowerCase()===n)||rows.find(x=>n.includes(x.name.toLowerCase())||x.name.toLowerCase().includes(n))||null}
}

class ShowNetworkBrandCatalog extends HTMLElement {
  set hass(h){this._hass=h; this.render();}
  connectedCallback(){this.render();}
  async render(){
    const catalog=await ShowNetworkBrandStore.loadCatalog();
    const rows=await ShowNetworkBrandStore.all(); this._catalog=catalog;
    const selected=this._filter||'all';
    const q=(this._query||'').toLowerCase();
    const visible=rows.filter(b=>(selected==='all'||b.categories?.includes(selected))&&(!q||b.name.toLowerCase().includes(q)));
    this.innerHTML=`<style>
:host{display:block;background:#0a0d10;color:#eef1f4;font-family:Inter,system-ui,sans-serif;padding:18px;box-sizing:border-box}.head{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;margin-bottom:14px}.title{font-size:24px;font-weight:800}.sub{font-size:11px;color:#89939d;margin-top:4px}.tools{display:flex;gap:8px;flex-wrap:wrap}.tool,input,select{background:#11161b;color:#eef1f4;border:1px solid #303942;border-radius:8px;padding:9px 10px}.tool{cursor:pointer}.primary{background:#1268a5;border-color:#2586c8}.filters{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:12px}.pill{padding:7px 10px;border:1px solid #303942;border-radius:999px;background:#11161b;color:#cbd2d8;cursor:pointer;font-size:10px}.pill.active{background:#164d70;border-color:#2586c8;color:#fff}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}.brand{background:#11161b;border:1px solid #29313a;border-radius:12px;padding:13px;display:grid;cursor:pointer;transition:border-color .15s,transform .15s;grid-template-columns:56px 1fr;gap:11px;min-height:92px}.brand:hover{border-color:#4e6576;transform:translateY(-1px)}.logo{width:56px;height:56px;border:1px solid #303942;border-radius:9px;background:#0a0d10;display:flex;align-items:center;justify-content:center;overflow:hidden;font-size:15px;font-weight:800;color:#7ed7ff}.logo img{width:100%;height:100%;object-fit:contain}.name{font-weight:750}.cat{font-size:9px;color:#8f99a3;margin-top:4px;line-height:1.5}.actions{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}.mini{font-size:9px;padding:5px 7px;border-radius:6px;background:#171d23;color:#dce3e8;border:1px solid #34404a;cursor:pointer}.danger{color:#ff9b9b}.empty{padding:25px;border:1px dashed #39444e;border-radius:10px;color:#8f99a3}.note{margin:12px 0;padding:10px 12px;border-left:3px solid #2a8bd0;background:#10161b;color:#aeb8c1;font-size:10px;line-height:1.5}.dialog{position:fixed;inset:0;background:#000a;display:flex;align-items:center;justify-content:center;z-index:20}.modal{width:min(560px,92vw);background:#11161b;border:1px solid #3a4651;border-radius:14px;padding:16px;box-shadow:0 20px 60px #000}.modal h3{margin:0 0 12px}.form{display:grid;gap:9px}.row{display:grid;grid-template-columns:1fr 1fr;gap:8px}.modal label{font-size:10px;color:#8f99a3}.modal input,.modal select{width:100%;box-sizing:border-box;margin-top:4px}.preview{width:72px;height:72px;border:1px solid #303942;border-radius:8px;object-fit:contain;background:#0a0d10}.foot{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}@media(max-width:700px){.head{display:block}.tools{margin-top:10px}.row{grid-template-columns:1fr}}
</style><div class="head"><div><div class="title">CONSTRUCTEURS</div><div class="sub">Catalogue commun Lumière · Son · Vidéo · Réseaux · Contrôle · Intercom</div></div><div class="tools"><input id="search" placeholder="Rechercher une marque…" value="${esc(q)}"><button class="tool primary" id="add">＋ Ajouter une marque</button></div></div>
<div class="note">Les fabricants et modèles détectés servent à qualifier l’équipement. Le logo est uniquement une identité visuelle : aucune identification n’est déclarée sur la seule présence d’un logo. Les logos intégrés doivent provenir d’une source autorisée ; les logos personnalisés PNG restent locaux à ce navigateur.</div>
<div class="filters">${[['all','Toutes'],...Object.entries(catalog.categories||{})].map(([k,v])=>`<button class="pill ${selected===k?'active':''}" data-filter="${k}">${v}</button>`).join('')}</div>
<div class="grid">${visible.length?visible.map(b=>{const logo=b.logo||'';return `<div class="brand" data-brand="${esc(b.key)}"><div class="logo">${logo?`<img src="${esc(logo)}" alt="">`:esc(b.name.split(/\\s+/).map(x=>x[0]).slice(0,2).join('').toUpperCase())}</div><div><div class="name">${esc(b.name)} ${b.custom?'<span style="font-size:9px;color:#75d7a0">PERSONNALISÉ</span>':''}</div><div class="cat">${(b.categories||[]).map(x=>catalog.categories?.[x]||x).join(' · ')}</div><div class="actions">${b.website?`<button class="mini" data-open="${esc(b.website)}">Site</button>`:''}${b.custom?`<button class="mini danger" data-del="${esc(b.key)}">Supprimer</button>`:''}</div></div></div>`}).join(''):'<div class="empty">Aucun constructeur pour ce filtre.</div>'}</div>`;
    this.querySelector('#search')?.addEventListener('input',e=>{this._query=e.target.value;this.render()});
    this.querySelectorAll('[data-filter]').forEach(x=>x.onclick=()=>{this._filter=x.dataset.filter;this.render()});
    this.querySelector('#add')?.addEventListener('click',()=>this.showEditor());
    this.querySelectorAll('[data-open]').forEach(x=>x.onclick=()=>window.open(x.dataset.open,'_blank','noopener,noreferrer'));
    this.querySelectorAll('[data-del]').forEach(x=>x.onclick=()=>{const next=ShowNetworkBrandStore.custom().filter(b=>b.key!==x.dataset.del);ShowNetworkBrandStore.saveCustom(next);this.render()});
  }
  showEditor(){
    const catalog=this._catalog||ShowNetworkBrandStore.catalog||{};
    const wrap=document.createElement('div');wrap.className='dialog';
    wrap.innerHTML=`<div class="modal"><h3>Ajouter un constructeur</h3><div class="form"><label>Nom<input id="bn" placeholder="Ex. MA Lighting"></label><div class="row"><label>Catégorie<select id="bc">${Object.entries(catalog.categories||{lighting:'Lumière',audio:'Son',video:'Vidéo',network:'Réseaux',show_control:'Contrôle spectacle',intercom:'Intercom / Communication'}).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><label>Site officiel<input id="bw" placeholder="https://…"></label></div><label>Logo PNG (≤ 1 Mo)<input id="bf" type="file" accept="image/png"></label><label>ou URL directe du logo<input id="bu" placeholder="https://…/logo.png"></label><img id="bp" class="preview" alt="Aperçu"></div><div class="foot"><button class="tool" id="cancel">Annuler</button><button class="tool primary" id="save">Ajouter</button></div></div>`;
    this.appendChild(wrap); const file=wrap.querySelector('#bf'),preview=wrap.querySelector('#bp'); let data='';
    file.onchange=()=>{const f=file.files?.[0];if(!f)return;if(f.type!=='image/png'||f.size>1024*1024){alert('PNG uniquement, 1 Mo maximum.');file.value='';return;}const r=new FileReader();r.onload=()=>{data=r.result;preview.src=data};r.readAsDataURL(f)};
    wrap.querySelector('#bu').oninput=e=>{if(e.target.value)preview.src=e.target.value};
    wrap.querySelector('#cancel').onclick=()=>wrap.remove();
    wrap.querySelector('#save').onclick=()=>{const name=wrap.querySelector('#bn').value.trim();if(!name){alert('Nom obligatoire.');return;}const key='custom_'+name.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'');const next=ShowNetworkBrandStore.custom().filter(b=>b.key!==key);next.push({key,name,categories:[wrap.querySelector('#bc').value],website:wrap.querySelector('#bw').value.trim(),logo:data||wrap.querySelector('#bu').value.trim()});ShowNetworkBrandStore.saveCustom(next);wrap.remove();this.render()};
  }
}
snDefine('show-network-brand-catalog',ShowNetworkBrandCatalog);

/* ===== device-inventory-panel.js ===== */
class ShowNetworkInventory extends HTMLElement {
  constructor(){super();this._editing=false;this._filter='all';this._query='';}
  setConfig(c){this._config=c||{}}
  set hass(h){this._hass=h;if(!this._editing)this.render()}
  async render(){
    if(!this._hass)return;
    const st=this._hass.states;
    const brands=await ShowNetworkBrandStore.all(); this._brands=brands;
    const brandFor=(name)=>{const n=String(name||'').toLowerCase();return brands.find(b=>n&&b.name.toLowerCase()===n)||brands.find(b=>n&&n.includes(b.name.toLowerCase())||n&&b.name.toLowerCase().includes(n));};
    const entity=Object.values(st).find(x=>x.entity_id.endsWith('_device_inventory'));
    const allRows=entity?.attributes?.devices||[];
    const q=String(this._query||'').trim().toLowerCase();
    const match=r=>!q||[r.display_name,r.hostname,r.ip,r.mac,r.display_manufacturer,r.display_model,r.custom_role,r.interface].some(v=>String(v||'').toLowerCase().includes(q));
    const filt=r=>this._filter==='favorites'?r.monitor_mode==='monitor':this._filter==='ignored'?r.monitor_mode==='ignore':this._filter==='others'?(r.monitor_mode||'auto')==='auto':true;
    const rows=allRows.filter(r=>match(r)&&filt(r)).sort((a,b)=>(b.monitor_mode==='monitor')-(a.monitor_mode==='monitor')||String(a.display_name||a.ip||'').localeCompare(String(b.display_name||b.ip||'')));
    const modelEntity=Object.values(st).find(x=>x.entity_id.endsWith('_show_network_devices'));
    const modelRows=modelEntity?.attributes?.devices||[]; const modelById=new Map(modelRows.map(x=>[x.id,x]));
    this.innerHTML=`<style>
    :host{display:block;background:#0b0d10;color:#eef1f4;font-family:Inter,system-ui,sans-serif;padding:18px;box-sizing:border-box}
    .top{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:14px}.title{font-size:22px;font-weight:750}.sub{font-size:11px;color:#89939d;margin-top:3px}
    .tools{display:flex;gap:8px;flex-wrap:wrap}.pill{padding:7px 10px;border:1px solid #30363d;border-radius:999px;background:#15191e;font-size:10px}
    table{width:100%;border-collapse:separate;border-spacing:0;background:#11151a;border:1px solid #2b3138;border-radius:12px;overflow:hidden}
    th,td{padding:10px;border-bottom:1px solid #242a30;text-align:left;font-size:11px}th{font-size:9px;color:#8b949e;text-transform:uppercase;background:#15191e}tr:last-child td{border-bottom:0}
    button{background:#1a2026;color:#eef1f4;border:1px solid #38414a;border-radius:7px;padding:6px 9px;cursor:pointer}.muted{color:#8b949e}.ok{color:#63d89a}.warn{color:#e4bb68}
    .edit{display:grid;grid-template-columns:repeat(6,minmax(90px,1fr));gap:7px;padding:10px;background:#0f1317}.edit input{min-width:0;background:#0b0d10;color:#eee;border:1px solid #343b43;border-radius:6px;padding:7px;font-size:10px}.history{margin-bottom:12px;padding:14px;background:#11151a;border:1px solid #30363d;border-radius:12px}.hrow{padding:8px 0;border-top:1px solid #252b31;font-size:11px}.mono{font-family:ui-monospace,monospace}.hdata{color:#8b949e;word-break:break-word;margin-top:3px}
    @media(max-width:900px){.edit{grid-template-columns:repeat(2,1fr)}th:nth-child(3),td:nth-child(3){display:none}}
    </style><div class="top"><div><div class="title">DEVICE INVENTORY</div><div class="sub">Découverte automatique + personnalisation manuelle · l'IP reste une donnée réseau</div></div><div class="tools"><input id="inv-search" placeholder="Nom / IP / MAC / type / interface" value="${esc(this._query||'')}" style="background:#0b0d10;color:#eee;border:1px solid #343b43;border-radius:7px;padding:7px"><button data-filter="all">Tous</button><button data-filter="favorites">★ Favoris</button><button data-filter="others">Non favoris</button><button data-filter="ignored">Ignorés</button><input id="manual-ip" placeholder="IP à ajouter" style="width:125px"><input id="manual-name" placeholder="Nom (optionnel)" style="width:140px"><button id="manual-add">＋ IP ★</button><span class="pill">${rows.length}/${allRows.length}</span></div></div>
    <table><thead><tr><th>Nom</th><th>Fabricant</th><th>Modèle</th><th>Rôle</th><th>Emplacement</th><th>IP</th><th>Surveillance</th><th>État</th><th></th></tr></thead><tbody>${rows.length?rows.map((r,i)=>{const m=r.display_manufacturer||r.manufacturer||'';const b=brandFor(m);return `<tr><td><button data-star="${esc(r.unique_id)}" title="${r.monitor_mode==='monitor'?'Retirer des favoris':'Suivre en favori'}">${r.monitor_mode==='monitor'?'★':'☆'}</button> ${esc(r.display_name||r.hostname||r.unique_id)}</td><td>${b?.logo?`<img src="${esc(b.logo)}" alt="" style="width:24px;height:24px;object-fit:contain;vertical-align:middle;margin-right:6px;border-radius:4px">`:''}${esc(m||'—')}</td><td>${esc(r.display_model||r.model||'—')}</td><td>${esc(r.custom_role||'—')}</td><td>${esc(r.custom_location||'—')}</td><td class="muted">${esc(r.ip||'—')}</td><td>${esc((r.monitor_mode||'auto').toUpperCase())}</td><td class="${r.hidden?'warn':'ok'}">${r.hidden?'MASQUÉ':'VISIBLE'}</td><td><button data-history="${esc(r.unique_id)}">Historique</button> <button data-i="${i}">Modifier</button> <button data-reset="${esc(r.unique_id)}">Réinitialiser</button></td></tr>`}).join(''):'<tr><td colspan="9" class="muted">Aucun équipement découvert.</td></tr>'}</tbody></table>`;
    this.querySelectorAll('[data-history]').forEach(b=>b.onclick=()=>{const d=modelById.get(b.dataset.history);if(!d)return;this.querySelector('.history')?.remove();const box=document.createElement('div');box.className='history';const fmt=(v)=>{if(v==null)return '—';try{return new Date(Number(v)*1000).toLocaleString()}catch(e){return String(v)}};const ev=d.event_history||[];box.innerHTML=`<div class="top"><div><b>${esc(d.name||d.id)} · HISTORIQUE ÉQUIPEMENT</b><div class="sub">Association uniquement sur preuves explicites · historique basé sur les 300 derniers événements persistés du journal</div></div><button data-close>Fermer</button></div><div class="hrow">Première observation inventaire : <b>${esc(fmt(d.first_seen))}</b> · Dernière : <b>${esc(fmt(d.last_seen))}</b></div><div class="hrow">Chemin actuel : <b>${esc(d.switch_name||'switch —')} · port ${esc(d.switch_port||'—')} · VLAN ${esc(d.vlan??'—')} · ${esc(d.interface||'interface —')}</b></div>${ev.length?ev.slice().reverse().map(e=>`<div class="hrow"><span class="mono">${esc(e.ts||'—')}</span> · <b>${esc(e.kind||'—')} / ${esc(e.event||'—')}</b><div class="hdata">${esc(JSON.stringify(e.data||{}))}</div></div>`).join(''):'<div class="hrow muted">Aucun événement récent ne peut être relié à cet équipement sans supposition.</div>'}`;this.prepend(box);box.querySelector('[data-close]').onclick=()=>box.remove();});
    this.querySelector('#inv-search')?.addEventListener('input',e=>{this._query=e.target.value;this.render()});
    this.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{this._filter=b.dataset.filter;this.render()});
    this.querySelector('#manual-add')?.addEventListener('click',async()=>{const ip=this.querySelector('#manual-ip')?.value.trim(),name=this.querySelector('#manual-name')?.value.trim();if(!ip)return;const b=this.querySelector('#manual-add');b.disabled=true;try{await this._hass.callService('dmx_monitor','register_manual_device',{ip,name,monitor_mode:'monitor'});}catch(e){alert(`Show Network: ${e?.message||e}`);}finally{b.disabled=false;setTimeout(()=>this.render(),300);}});
    this.querySelectorAll('[data-star]').forEach(b=>b.onclick=async()=>{const r=allRows.find(x=>x.unique_id===b.dataset.star);if(!r)return;const mode=r.monitor_mode==='monitor'?'auto':'monitor';b.disabled=true;try{await this._hass.callService('dmx_monitor','set_device_override',{unique_id:r.unique_id,monitor_mode:mode});}finally{setTimeout(()=>this.render(),250);}});
    this.querySelectorAll('button[data-i]').forEach(b=>b.onclick=()=>this.editor(rows[+b.dataset.i]));
    this.querySelectorAll('[data-reset]').forEach(b=>b.onclick=async()=>{await this._hass.callService('dmx_monitor','clear_device_override',{unique_id:b.dataset.reset});setTimeout(()=>this.render(),400);setTimeout(()=>this.render(),1500)});
  }
  editor(r){
    this._editing=true;
    const wrap=document.createElement('div'); wrap.className='edit'; wrap.innerHTML=`<input data-k="name" placeholder="Nom" value="${esc(r.custom_name||'')}"><input data-k="manufacturer" list="brand-list" placeholder="Fabricant" value="${esc(r.custom_manufacturer||'')}"><datalist id="brand-list">${(this._brands||[]).map(b=>`<option value="${esc(b.name)}">`).join('')}</datalist><input data-k="model" placeholder="Modèle" value="${esc(r.custom_model||'')}"><input data-k="role" placeholder="Rôle spectacle" value="${esc(r.custom_role||'')}"><input data-k="location" placeholder="Emplacement" value="${esc(r.custom_location||'')}"><select data-k="monitor_mode" style="background:#0b0d10;color:#eee;border:1px solid #343b43;border-radius:6px;padding:7px"><option value="auto" ${(r.monitor_mode||'auto')==='auto'?'selected':''}>Auto</option><option value="monitor" ${r.monitor_mode==='monitor'?'selected':''}>Surveiller</option><option value="ignore" ${r.monitor_mode==='ignore'?'selected':''}>Ignorer</option></select><label style="font-size:10px;display:flex;gap:5px;align-items:center"><input type="checkbox" data-k="hidden" ${r.hidden?'checked':''}> Masquer</label><button data-save>Enregistrer</button><button data-cancel>Annuler</button>`;
    this.prepend(wrap); wrap.querySelector('[data-cancel]').onclick=()=>{this._editing=false;wrap.remove();this.render()}; wrap.querySelector('[data-save]').onclick=async()=>{const data={unique_id:r.unique_id};wrap.querySelectorAll('[data-k]').forEach(x=>data[x.dataset.k]=x.type==='checkbox'?x.checked:x.value);await this._hass.callService('dmx_monitor','set_device_override',data);this._editing=false;wrap.remove();setTimeout(()=>this.render(),400);setTimeout(()=>this.render(),1500)};
  }
}
function esc(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function snCaptureDetails(root){const out={};root?.querySelectorAll?.('details').forEach((d,i)=>{out[d.dataset.persist||d.querySelector('summary')?.textContent?.trim()||String(i)]=d.open});return out}
function snRestoreDetails(root,state){if(!state)return;root?.querySelectorAll?.('details').forEach((d,i)=>{const k=d.dataset.persist||d.querySelector('summary')?.textContent?.trim()||String(i);if(k in state)d.open=!!state[k]})}
snDefine('show-network-inventory',ShowNetworkInventory);


/* ===== discovery-panel.js ===== */
class ShowNetworkDiscovery extends HTMLElement {
  constructor(){super();this._ifFilter='';this._modeFilter='all';this._query='';}
  setConfig(c){this._config=c||{};}
  set hass(h){this._hass=h;this.render();}
  connectedCallback(){this.render();}
  _inventory(){const e=Object.values(this._hass?.states||{}).find(x=>x.entity_id.endsWith('_device_inventory'));return e?.attributes?.devices||[];}
  _status(){const e=Object.values(this._hass?.states||{}).find(x=>x.entity_id.endsWith('_discovery_status'));return e?.attributes||{};}
  render(){
    const open=snCaptureDetails(this);
    const rows=this._inventory(), ds=this._status();
    const interfaceOf=(r)=>r.interface||'';
    const unlocked=(()=>{const c=Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes('security_unlocked'));return c?.state==='true'||c?.state==='on';})();
    const interfaces=[...new Set(rows.map(interfaceOf).filter(Boolean))].sort();
    if(this._ifFilter && !interfaces.includes(this._ifFilter))this._ifFilter='';
    let visibleRows=this._ifFilter?rows.filter(r=>interfaceOf(r)===this._ifFilter):rows;
    const q=String(this._query||'').trim().toLowerCase();
    visibleRows=visibleRows.filter(r=>(this._modeFilter==='all'||(this._modeFilter==='favorites'&&r.monitor_mode==='monitor')||(this._modeFilter==='ignored'&&r.monitor_mode==='ignore')||(this._modeFilter==='others'&&(r.monitor_mode||'auto')==='auto'))&&(!q||[r.ip,r.hostname,r.mac,r.display_name,r.display_manufacturer,r.display_model,r.category,r.interface].some(v=>String(v||'').toLowerCase().includes(q)))).sort((a,b)=>(b.monitor_mode==='monitor')-(a.monitor_mode==='monitor')||String(a.ip||a.hostname||'').localeCompare(String(b.ip||b.hostname||'')));
    this.innerHTML=`<style>
    :host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}h2{margin:0 0 5px}.sub{color:#8d969f;font-size:11px;margin-bottom:15px}.bar{display:flex;gap:8px;align-items:center;background:#15181c;border:1px solid #2c3239;border-radius:10px;padding:12px}button{background:#23282e;color:#eee;border:1px solid #3a4148;border-radius:7px;padding:8px 12px;cursor:pointer}.table{margin-top:12px;border:1px solid #2c3239;border-radius:10px;overflow:hidden}.row{display:grid;grid-template-columns:150px 1fr 130px 130px;gap:10px;padding:10px 12px;border-bottom:1px solid #282d33;font-size:12px}.head{color:#8d969f;background:#15181c;font-size:10px;text-transform:uppercase}.muted{color:#8d969f}</style>
    <h2>AUTO DISCOVERY</h2><div class="sub">Inventaire réseau séparé des protocoles spectacle. Le scan manuel inspecte toutes les interfaces IPv4 disponibles; DMX, Dante, MA-Net3, AES67 et OSC conservent leurs interfaces configurées.</div><div class="bar"><label>Vue interface <select id="if-filter"><option value="">Toutes</option>${interfaces.map(x=>`<option value="${esc(x)}" ${x===this._ifFilter?'selected':''}>${esc(x)}</option>`).join('')}</select></label><input id="disc-search" placeholder="Nom / IP / MAC / type" value="${esc(this._query||'')}" style="background:#0b0d10;color:#eee;border:1px solid #3a4148;border-radius:7px;padding:8px"><button data-mode="all">Tous</button><button data-mode="favorites">★ Favoris</button><button data-mode="others">Non favoris</button><button data-mode="ignored">Ignorés</button><span class="muted">Les couleurs/sections servent uniquement à rendre l’inventaire lisible; elles ne changent aucun routage protocolaire.</span></div><div class="bar"><span class="muted" id="status">${rows.length} équipement(s) · état ${esc(ds.state||'idle')} · mDNS ${ds.mdns_services??0} (${esc(ds.mdns_state||'idle')}) · ARP ${ds.arp_neighbors??0} · HTTP ${ds.http_responders??0}/${ds.http_attempted??0} (${ds.http_identified??0} ident.) · SNMP ${ds.snmp_responders??0}/${ds.snmp_attempted??ds.arp_neighbors??0} · switches ${ds.identified_switches??0}${(ds.errors||[]).length?' · erreurs '+esc((ds.errors||[]).join(' | ')):''}<br><span class="muted">mDNS: ${esc(ds.mdns_detail||'aucun diagnostic')} · SNMP: ${esc(ds.snmp_probe_mode||'—')}</span></span><button id="scan">SCAN NETWORK</button></div><div class="table"><div class="row head"><span>IP / HÔTE</span><span>PROTOCOLES / FABRICANT</span><span>RÔLE / SOURCE</span><span>CONFIANCE</span><span>PAGE WEB</span></div>${visibleRows.length?visibleRows.map(r=>`<div class="row"><span><button data-disc-star="${esc(r.unique_id)}" title="Favori de régie">${r.monitor_mode==='monitor'?'★':'☆'}</button> ${esc(r.ip||r.hostname||'—')}</span><span>${esc((r.protocols||[]).join(', ')||'—')} ${r.display_manufacturer?'· '+esc(r.display_manufacturer):'· marque non identifiée'}</span><span>${esc(r.custom_role||r.category||(r.sources||[]).join(', ')||'—')}</span><span>${esc(r.confidence??'—')}</span><span>${r.ip?`<button data-open-device="${esc(r.ip)}" ${unlocked?'':'disabled title="Déverrouille Show Network pour ouvrir une page web d\u2019appareil"'}>Ouvrir ↗</button>`:'—'}</span></div>`).join(''):'<div class="row"><span class="muted">Aucun équipement observé</span><span>—</span><span>—</span><span>—</span><span>—</span></div>'}</div><details class="table"><summary style="padding:10px;cursor:pointer">Diagnostic SNMP par hôte</summary>${(ds.snmp_hosts||[]).length?(ds.snmp_hosts||[]).map(x=>`<div class="row"><span>${esc(x.ip||'—')}</span><span>${esc(x.manufacturer||x.state||'—')}</span><span>${esc(x.sys_name||'—')}</span><span>${esc(x.sys_object_id||'—')}</span></div>`).join(''):'<div class="row"><span class="muted">Aucun essai SNMP enregistré</span><span>—</span><span>—</span><span>—</span></div>'}</details>`;
    snRestoreDetails(this,open);
    this.querySelector('#if-filter')?.addEventListener('change',e=>{this._ifFilter=e.target.value||'';this.render()});
    this.querySelector('#disc-search')?.addEventListener('input',e=>{this._query=e.target.value;this.render()});
    this.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{this._modeFilter=b.dataset.mode;this.render()});
    this.querySelectorAll('[data-disc-star]').forEach(b=>b.onclick=async()=>{const r=rows.find(x=>x.unique_id===b.dataset.discStar);if(!r)return;const mode=r.monitor_mode==='monitor'?'auto':'monitor';b.disabled=true;try{await this._hass.callService('dmx_monitor','set_device_override',{unique_id:r.unique_id,monitor_mode:mode});}finally{setTimeout(()=>this.render(),250);}});
    this.querySelectorAll('[data-open-device]').forEach(b=>b.onclick=()=>{const ip=b.dataset.openDevice;window.open(`/api/dmx_monitor/device_proxy/${encodeURIComponent(ip)}/`,'_blank');});
    this.querySelector('#scan')?.addEventListener('click',async()=>{const b=this.querySelector('#scan'),st=this.querySelector('#status');b.disabled=true;st.textContent='Scan en cours…';try{await this._hass.callService('dmx_monitor','scan_network',{});st.textContent='Scan terminé. Les résultats vont se rafraîchir.';}catch(e){st.textContent='Erreur: '+(e?.message||e);}finally{b.disabled=false;}});
  }
}
snDefine("show-network-discovery",ShowNetworkDiscovery);


/* ===== dmx-ha-mapping-panel.js ===== */
class DmxHaMappingPanel extends HTMLElement {
  set hass(h){this._hass=h;this.render()}
  call(mapping_id,enabled){this._hass.callService('dmx_monitor','set_dmx_ha_mapping_highlight',{mapping_id,enabled})}
  _security(){const c=Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes('security_unlocked'));return c?.state==='true'||c?.state==='on'}
  async _svc(service,data){try{await this._hass.callService('dmx_monitor',service,data);setTimeout(()=>this.render(),400);setTimeout(()=>this.render(),1500)}catch(e){this._msg=`Erreur: ${e?.message||e}`;this.render()}}
  render(){
    if(!this._hass)return;
    const st=Object.values(this._hass.states).find(x=>x.entity_id.endsWith('dmx_ha_mappings_total'));
    const mappings=(st&&st.attributes&&st.attributes.mappings)||[];
    const on=st?.attributes?.light_sync_enabled===true; const unlocked=this._security();
    this.innerHTML=`<style>:host{display:block;font-family:Inter,system-ui,sans-serif}.wrap{padding:16px}.row{display:grid;grid-template-columns:1fr 100px 1fr 170px;gap:8px;align-items:center;padding:9px 0;border-bottom:1px solid #2c3239;font-size:12px}.muted{color:#8d969f}.btn{background:#171b20;color:#fff;border:1px solid #3a4148;border-radius:6px;padding:6px 9px;cursor:pointer;margin:2px}.btn.primary{background:#164d70}.btn.danger{border-color:#8b3f45}.curve{font-size:10px}.on{color:#68df9a}.off{color:#f0b36a}input,select{box-sizing:border-box;background:#0b0e12;color:#eee;border:1px solid #333b44;border-radius:5px;padding:7px;font-size:11px;margin:3px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:6px}</style><ha-card header="DMX → Home Assistant"><div class="wrap">
    <div class="muted">Liaison DMX → HA · Highlight temporaire · courbe de dimmer</div>
    <div class="muted" style="margin:8px 0">Light Sync : <b class="${on?'on':'off'}">${on?'ACTIF':'INACTIF'}</b> · Sécurité : <b class="${unlocked?'on':'off'}">${unlocked?'DÉVERROUILLÉE':'VERROUILLÉE'}</b></div>
    <button class="btn ${on?'primary':''}" id="toggle-sync" ${unlocked?'':'disabled'}>${on?'Désactiver Light Sync':'Activer Light Sync'}</button>
    ${mappings.length?`<div class="row"><b>Mapping</b><b>Canaux</b><b>Entité</b><b>Action</b></div>${mappings.map(m=>`<div class="row"><span>${m.mapping_id}</span><span>U${m.universe} · ${(m.channels||[]).join(',')}</span><span>${m.entity_id||'—'}<br><span class="muted curve">courbe: ${m.dimmer_curve||'linear'}</span></span><span><button class="btn" data-id="${m.mapping_id}" data-on="1">HIGHLIGHT</button><button class="btn" data-id="${m.mapping_id}" data-on="0">RESTORE</button><button class="btn danger" data-remove="${m.mapping_id}">SUPPR.</button></span></div>`).join('')}`:'<div style="padding-top:14px">Aucun mapping configuré.</div>'}
    <h4 style="margin-top:14px">Nouveau mapping</h4>
    <div class="grid">
      <input id="m-id" placeholder="ID (ex: foh_dimmer1)">
      <input id="m-universe" type="number" min="1" value="1" placeholder="Univers">
      <input id="m-channels" placeholder="Canaux (ex: 1 ou 1-3)">
      <input id="m-entity" placeholder="entity_id (ex: light.foh)">
    </div>
    <div class="grid">
      <input id="m-domain" value="light" placeholder="Domaine HA">
      <input id="m-service" value="turn_on" placeholder="Service HA">
      <select id="m-mode"><option value="dimmer">dimmer</option><option value="rgb">rgb</option><option value="switch">switch</option></select>
      <input id="m-deadband" type="number" min="0" max="255" value="0" placeholder="Deadband">
    </div>
    <button class="btn primary" id="add-mapping">Créer le mapping</button>
    ${this._msg?`<div class="muted" style="margin-top:8px">${this._msg}</div>`:''}
    </div></ha-card>`;
    this.querySelectorAll('button[data-id]').forEach(b=>b.addEventListener('click',()=>this.call(b.dataset.id,b.dataset.on==='1')));
    this.querySelectorAll('[data-remove]').forEach(b=>b.addEventListener('click',()=>this._svc('remove_dmx_ha_mapping',{mapping_id:b.dataset.remove})));
    this.querySelector('#toggle-sync')?.addEventListener('click',()=>this._svc('set_light_sync_enabled',{enabled:!on}));
    this.querySelector('#add-mapping')?.addEventListener('click',()=>{
      const mapping_id=this.querySelector('#m-id').value.trim();
      const channels=this.querySelector('#m-channels').value.trim();
      if(!mapping_id||!channels){this._msg='ID et canaux obligatoires.';this.render();return;}
      this._svc('create_dmx_ha_mapping',{
        mapping_id,
        universe:+this.querySelector('#m-universe').value,
        channels,
        entity_id:this.querySelector('#m-entity').value.trim(),
        domain:this.querySelector('#m-domain').value.trim()||'light',
        service:this.querySelector('#m-service').value.trim()||'turn_on',
        mode:this.querySelector('#m-mode').value,
        deadband:+this.querySelector('#m-deadband').value||0,
        enabled:true,
      });
    });
  }
}
snDefine('dmx-ha-mapping-panel',DmxHaMappingPanel)


/* Removed in v0.13.0: the former dmx-live-view rendered synthetic demo values. */

/* ===== dmx-monitor-panel.js ===== */
class DmxMonitorPanel extends HTMLElement {
  constructor(){super();this.attachShadow({mode:"open"});this.selectionKey="";this.values=Array(512).fill(0);this.source="—";this.protocol="—";this.rate=0;this.active=0;this.priority=null;this.sequence=null;this.selected=new Set();this._framePending=false;this._lastSig="";}
  connectedCallback(){this.render();}
  set hass(hass){this._hass=hass;const a=this.shadowRoot?.activeElement;if(a&&['SELECT','INPUT'].includes(a.tagName)){this._pendingHass=true;return;}this.syncLive();}
  _parseUniverses(raw){
    const out=new Set();
    for(const part of String(raw||'').replace(/\s+/g,'').split(',')){
      if(!part)continue;
      if(part.includes('-')){const [a,b]=part.split('-').map(Number);if(Number.isInteger(a)&&Number.isInteger(b)){for(let x=Math.min(a,b);x<=Math.max(a,b)&&x<=63999;x++)out.add(x)}}
      else {const n=Number(part);if(Number.isInteger(n)&&n>0)out.add(n)}
    }
    return [...out].sort((a,b)=>a-b);
  }
  _findDmxState(){return Object.values(this._hass?.states||{}).find(s=>Array.isArray(s.attributes?.universes));}
  _findConfig(){return Object.values(this._hass?.states||{}).find(s=>s.attributes && ('interface_dmx' in s.attributes || 'dmx_artnet_enabled' in s.attributes))?.attributes||{};}
  _observed(){return this._findDmxState()?.attributes?.universes||[];}
  _rxDiag(){return Object.values(this._hass?.states||{}).find(s=>s.attributes?.dmx&&s.attributes?.ma_net3)?.attributes?.dmx||this._findDmxState()?.attributes?.network_health||{};}
  _choices(){
    const observed=this._observed();
    const cfg=this._findConfig();
    const choices=observed.map((u,i)=>({key:`obs:${u.protocol||''}:${u.universe||''}:${u.source||''}`,observed:true,data:u,label:`U${Number(u.universe)||'?'} · ${u.protocol||'?'} · ${u.source||'source ?'}`}));
    const observedNumbers=new Set(observed.map(u=>Number(u.universe)));
    for(const u of this._parseUniverses(cfg.universes||this._findDmxState()?.attributes?.configured_universes||'')){
      if(!observedNumbers.has(u))choices.push({key:`cfg:${u}`,observed:false,data:{universe:u,protocol:'—',source:'—',packet_rate:0,active_channels:0},label:`U${u} · configuré · aucun trafic`});
    }
    return choices;
  }
  syncLive(){
    if(this._framePending)return;this._framePending=true;
    const run=()=>{this._framePending=false;this._syncLiveNow();};
    if(typeof requestAnimationFrame==='function')requestAnimationFrame(run);else setTimeout(run,100);
  }
  _syncLiveNow(){
    const choices=this._choices();
    if(!choices.length){this.selectionKey='';this.values=Array(512).fill(0);this.source='—';this.protocol='—';this.rate=0;this.active=0;this.render();return;}
    if(!this.selectionKey){try{this.selectionKey=sessionStorage.getItem('show-network-dmx-selection')||''}catch(e){}} let choice=choices.find(x=>x.key===this.selectionKey)||choices[0];this.selectionKey=choice.key;try{sessionStorage.setItem('show-network-dmx-selection',this.selectionKey)}catch(e){}
    const u=choice.data||{};this.universe=Number(u.universe)||null;this.source=u.source||'—';this.protocol=u.protocol||'—';this.rate=Number(u.packet_rate||0);this.active=Number(u.active_channels||0);this.priority=u.priority;this.sequence=u.sequence;
    if(choice.observed&&Array.isArray(u.values))this.values=u.values.slice(0,512).concat(Array(512)).slice(0,512);
    else if(choice.observed&&u.values_b64){try{const bin=atob(u.values_b64);this.values=Array.from(bin,c=>c.charCodeAt(0)).slice(0,512).concat(Array(512)).slice(0,512)}catch(e){this.values=Array(512).fill(0)}}
    else this.values=Array(512).fill(0);
    const sig=`${this.selectionKey}|${this.rate}|${this.active}|${this.priority}|${this.sequence}|${u.values_b64||JSON.stringify(u.values||[])}`;if(sig===this._lastSig)return;this._lastSig=sig;this.render();
  }
  render(){
    const choices=this._choices();const current=choices.find(x=>x.key===this.selectionKey);const isLive=Boolean(current?.observed&&this.rate>0);const hasObserved=Boolean(current?.observed);const rx=this._rxDiag()||{},pdiag=rx.protocols||{},ad=pdiag.ARTNET||{},sd=pdiag.SACN||{};
    const css=`:host{display:block;background:#0c0e10;color:#e8eaed;font-family:Inter,system-ui,sans-serif}.top{background:#171a1e;border-bottom:1px solid #30353b;padding:16px 20px}.title{font-size:22px;font-weight:700}.sub{color:#8f98a3;font-size:11px;margin-top:3px}.tools{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}.pill{background:#20242a;border:1px solid #343a41;border-radius:7px;padding:7px 10px;font-size:11px}.ok{border-color:#2d714b}.warn{border-color:#8a6a2f}.off{color:#9aa3ac}.select{background:#20242a;color:#eee;border:1px solid #343a41;border-radius:7px;padding:7px}.body{padding:14px}.diaggrid{display:grid;grid-template-columns:repeat(2,minmax(280px,1fr));gap:10px;margin-bottom:12px}.diagcard{background:#15181c;border:1px solid #292e34;border-radius:9px;padding:12px}.diagline{display:flex;justify-content:space-between;gap:10px;font-size:10px;padding:3px 0}.bad{color:#ff8e8e}.good{color:#69df9b}.card{background:#15181c;border:1px solid #292e34;border-radius:9px;margin-bottom:12px;overflow:hidden}.bar{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:12px 14px;background:#191c20;border-bottom:1px solid #292e34}.muted{color:#8d969f;font-size:11px}.grid{display:grid;grid-template-columns:repeat(32,minmax(23px,1fr));gap:2px;padding:10px}.cell{height:45px;border-radius:3px;background:#292e34;display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;user-select:none}.cell.active{background:#12472f}.cell.low{background:#303326}.num{font-size:12px;font-weight:700}.ch{font-size:8px;color:#8e969f;margin-top:2px}.active .num{color:#6ae59e}.selected{outline:2px solid #e5e7eb}.foot{padding:10px 14px;color:#8f98a3;font-size:11px}@media(max-width:950px){.grid{grid-template-columns:repeat(16,minmax(23px,1fr));}}`;
    let cells='';for(let i=1;i<=512;i++){const v=Number(this.values[i-1]||0),cls=v>10?'active':(v>0?'low':''),sel=this.selected.has(i)?' selected':'';cells+=`<div class="cell ${cls}${sel}" data-ch="${i}"><span class="num">${v}</span><span class="ch">CH ${i}</span></div>`;}
    const opts=choices.map(x=>`<option value="${esc(x.key)}">${esc(x.label)}</option>`).join('');const status=isLive?'● LIVE':(hasObserved?'● SILENCIEUX':'○ CONFIGURÉ / PAS DE TRAFIC');
    const protoCard=(name,d)=>`<div class="diagcard"><b>${name}</b><div class="diagline"><span>État</span><span class="${d.state==='listening'?'good':d.state==='error'?'bad':''}">${esc(d.state||'—')}</span></div><div class="diagline"><span>Interface / bind</span><span>${esc(d.interface||'—')} · ${esc(d.bound_endpoint||'—')}</span></div><div class="diagline"><span>Paquets reçus / parsés</span><span>${d.packets_received??0} / ${d.packets_parsed??0}</span></div><div class="diagline"><span>Dernière source</span><span>${esc(d.last_source||'—')} · U${d.last_universe??'—'}</span></div><div class="diagline"><span>Dernière erreur</span><span class="${d.last_error?'bad':''}">${esc(d.last_error||'aucune')}</span></div>${name==='sACN'?`<div class="diagline"><span>Interface multicast</span><span>${esc(d.membership_interface||d.interface||'—')}</span></div><div class="diagline"><span>Groupes rejoints</span><span>${(d.joined_groups||[]).length}/${(d.configured_groups||[]).length}</span></div><div class="diagline"><span>Groupes</span><span>${esc((d.joined_groups||[]).join(', ')||'—')}</span></div><div class="diagline"><span>Erreurs multicast</span><span class="${(d.join_errors||[]).length?'bad':''}">${esc((d.join_errors||[]).join(' | ')||'aucune')}</span></div>`:''}</div>`;
    const matrix=this._findDmxState()?.attributes?.matrix||[];
    const matrixHtml=matrix.length?`<section class="card"><div class="bar"><div><b>DMX UNIVERSE MATRIX</b><div class="muted">Sources passives · FPS · priorité · CID sACN · pertes · dernière réception</div></div></div><div style="overflow:auto"><table style="width:100%;border-collapse:collapse;font-size:10px"><thead><tr><th>Univers</th><th>Source</th><th>Nom / CID</th><th>FPS</th><th>Priority</th><th>Loss</th><th>Jitter</th><th>Âge</th><th>État</th></tr></thead><tbody>${matrix.flatMap(r=>(r.sources||[]).map((x,i)=>`<tr style="border-top:1px solid #293039"><td style="padding:6px">${i===0?`${esc(r.protocol)} U${r.universe}${r.multi_source?' ⚠':''}`:''}</td><td>${esc(x.source||'—')}</td><td>${esc(x.source_name||'—')}<br><span class="muted">${esc(x.cid||'CID —')}</span></td><td>${Number(x.packet_rate||0).toFixed(1)}</td><td>${x.priority??'—'}</td><td>${Number(x.sequence_loss_pct||0).toFixed(2)}%</td><td>${Number(x.jitter_ms||0).toFixed(1)} ms</td><td>${Number(x.last_seen_age_s||0).toFixed(1)} s</td><td class="${x.active?'good':'bad'}">${x.active?'LIVE':'LOST'}</td></tr>`)).join('')}</tbody></table></div></section>`:'';
    this.shadowRoot.innerHTML=`<style>${css}</style><header class="top"><div class="title">DMX View</div><div class="sub">RÉCEPTION UNIQUEMENT · données observées réelles · aucune valeur de démonstration</div><div class="tools"><button class="select" id="prev">◀</button><select class="select" id="uni">${opts||'<option value="">Aucun univers configuré/observé</option>'}</select><button class="select" id="next">▶</button><input class="select" id="listen-universes" style="width:120px" value="${esc(this._findConfig().universes||'')}" placeholder="1-16,21"><button class="select" id="apply-universes">Écouter</button><span class="pill ${isLive?'ok':hasObserved?'warn':'off'}">${status}</span><span class="pill">${esc(this.protocol)}</span><span class="pill">Source ${esc(this.source)}</span><span class="pill">${this.rate.toFixed(1)} pkt/s</span><span class="pill">${this.active} actifs</span><span class="pill">Priority ${this.priority??'—'}</span><span class="pill">Seq ${this.sequence??'—'}</span></div></header><main class="body">${matrixHtml}<div class="diaggrid">${protoCard('Art-Net',ad)}${protoCard('sACN',sd)}</div><section class="card"><div class="bar"><div><b>Universe ${this.universe||'—'} · DMX 1–512</b><div class="muted">${hasObserved?'Valeurs reçues du listener sélectionné.':'Univers configuré mais aucun paquet correspondant observé.'}</div></div></div><div class="grid">${cells}</div><div class="foot">Sélection : ${[...this.selected].sort((a,b)=>a-b).join(', ')||'—'} · Aucun paquet n'est émis.</div></section></main>`;
    const sel=this.shadowRoot.querySelector('#uni');if(sel)sel.value=this.selectionKey;sel?.addEventListener('change',e=>{this.selectionKey=e.target.value;try{sessionStorage.setItem('show-network-dmx-selection',this.selectionKey)}catch(err){}this._lastSig='';this.syncLive();});const step=(d)=>{const i=Math.max(0,choices.findIndex(x=>x.key===this.selectionKey));if(choices.length){this.selectionKey=choices[(i+d+choices.length)%choices.length].key;try{sessionStorage.setItem('show-network-dmx-selection',this.selectionKey)}catch(err){}this._lastSig='';this.syncLive();}};this.shadowRoot.querySelector('#prev')?.addEventListener('click',()=>step(-1));this.shadowRoot.querySelector('#next')?.addEventListener('click',()=>step(1));this.shadowRoot.querySelector('#apply-universes')?.addEventListener('click',async()=>{const raw=this.shadowRoot.querySelector('#listen-universes')?.value?.trim();if(!raw)return;const b=this.shadowRoot.querySelector('#apply-universes');b.disabled=true;b.textContent='…';try{await this._hass.callService('dmx_monitor','set_dmx_universes',{universes:raw});b.textContent='OK';}catch(e){b.textContent='Erreur';}setTimeout(()=>{b.disabled=false;b.textContent='Écouter'},1200);});
    this.shadowRoot.querySelectorAll('.cell').forEach(c=>c.addEventListener('click',()=>{const ch=Number(c.dataset.ch);this.selected.has(ch)?this.selected.delete(ch):this.selected.add(ch);c.classList.toggle('selected',this.selected.has(ch));this.dispatchEvent(new CustomEvent('dmx-channel-selected',{detail:{channel:ch,universe:this.universe,source:this.source,protocol:this.protocol},bubbles:true,composed:true}));this.shadowRoot.querySelector('.foot').textContent=`Sélection : ${[...this.selected].sort((a,b)=>a-b).join(', ')||'—'} · Aucun paquet n'est émis.`;}));
  }
}
snDefine("dmx-monitor-panel",DmxMonitorPanel);


/* ===== enttec-panel.js ===== */
class EnttecPanel extends HTMLElement {
  setConfig(c){this.config=c||{}; this.render();}
  set hass(h){this._h=h; this.render();}
  render(){if(!this.shadowRoot){this.attachShadow({mode:"open"});} const h=this._h; const sw=h?.states?.[this.config?.entity||"switch.dmx_monitor_enttec_dmx_input_listen"]; const on=sw?.state==="on"; this.shadowRoot.innerHTML=`<style>ha-card{padding:16px} .row{display:flex;align-items:center;justify-content:space-between;gap:16px}.title{font-size:18px;font-weight:600}.state{opacity:.8;margin-top:4px}button{border:0;border-radius:8px;padding:10px 16px;font-weight:600;cursor:pointer}</style><ha-card><div class="row"><div><div class="title">ENTTEC DMX Input</div><div class="state">${on?"🟢 Écoute active":"⚪ Écoute désactivée"}</div></div><button id="toggle">${on?"Désactiver":"Activer l’écoute"}</button></div></ha-card>`; this.shadowRoot.querySelector('#toggle')?.addEventListener('click',()=>{if(!h||!sw)return; h.callService('switch',on?'turn_off':'turn_on',sw.entity_id);});}
}
snDefine('enttec-panel',EnttecPanel);

/* ===== ma-inspector-panel.js ===== */
class MaInspectorPanel extends HTMLElement {
  constructor(){super();this.attachShadow({mode:"open"});this._hass=null;this.data={};}
  set hass(h){this._hass=h;this.sync();}
  sync(){
    const states=this._hass?.states||{};
    const st=Object.values(states).find(x=>x.attributes?.ma_remote);
    const rx=Object.values(states).find(x=>x.attributes?.ma_net3)?.attributes?.ma_net3||st?.attributes?.rx_diagnostics||{};
    this.data={...(st?.attributes?.ma_remote||{}),rx_diagnostics:rx};
    this.render();
  }
  connectedCallback(){this.render();}
  render(){
    const d=this.data||{}, stations=d.stations||[], osc=d.osc||{}, diag=d.diagnostics||{}, rx=d.rx_diagnostics||{};
    const css=`:host{display:block;background:#0d0f11;color:#e8eaed;min-height:100vh;font-family:Inter,system-ui,sans-serif}.head{padding:18px 22px;background:#17191d;border-bottom:1px solid #30343a}.title{font-size:23px;font-weight:700}.sub{color:#8e969f;font-size:11px;margin-top:3px}.body{padding:14px}.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}.card{background:#16191d;border:1px solid #2d3238;border-radius:9px;padding:13px}.big{font-size:20px;font-weight:700}.muted{font-size:11px;color:#8e969f}.ok{color:#69df9b}.warn{color:#e7bd68}.table{margin-top:12px;background:#16191d;border:1px solid #2d3238;border-radius:9px;overflow:hidden}.row{display:grid;grid-template-columns:1.4fr 1.4fr 1fr 1fr 1fr 1fr 1.3fr;padding:10px 12px;border-bottom:1px solid #282d33;font-size:11px}.headrow{background:#1b1f24;color:#929aa3;font-weight:600}.diag{margin-top:12px}.link{color:#9bc5ff}@media(max-width:1000px){.cards{grid-template-columns:repeat(2,1fr)}.row{grid-template-columns:1.4fr 1fr 1fr}}`;
    const rows=stations.length?stations.map(x=>`<div class="row"><span>${x.name||"MA"}</span><span>${esc(x.device_type||'Non classifiée')}</span><span>${x.ip||"—"}</span><span>${x.session_index??"UNKNOWN"}</span><span class="${x.state==='LIVE'?'ok':'warn'}">${x.state||"UNKNOWN"}</span><span>${x.age_s??"—"} s</span><span><a class="link" target="_blank" href="${x.web_remote_url||'#'}">Web Remote</a></span></div>`).join(""):`<div class="row"><span>—</span><span>Non classifiée</span><span>—</span><span>UNKNOWN</span><span>NO DATA</span><span>—</span><span>—</span></div>`;
    this.shadowRoot.innerHTML=`<style>${css}</style><header class="head"><div class="title">MA Remote</div><div class="sub">grandMA3 · MA-NET3 · PASSIVE DIAGNOSTICS · NO SESSION JOIN / NO CONTROL</div></header><main class="body"><div class="cards"><div class="card"><div class="muted">MA-Net3</div><div class="big ok">${stations.length?'● ACTIVE':'○ WAITING'}</div><div class="muted">UDP 30020</div></div><div class="card"><div class="muted">Stations</div><div class="big">${d.station_count||0}</div></div><div class="card"><div class="muted">Live</div><div class="big">${d.live_stations||0}</div></div><div class="card"><div class="muted">Sessions</div><div class="big">${d.session_count||0}</div><div class="muted">passive only</div></div><div class="card"><div class="muted">OSC</div><div class="big">${osc.default_port||8000}</div><div class="muted">${osc.transport||'UDP/TCP'}</div></div></div><div class="table"><div class="row headrow"><span>Station</span><span>Type prouvé</span><span>IP</span><span>Session</span><span>State</span><span>Age</span><span>Web Remote</span></div>${rows}</div><div class="table diag"><div class="row headrow"><span>Diagnostic</span><span>Result</span><span>Protocol</span><span>Detail</span><span></span><span></span></div><div class="row"><span>UDP listener</span><span class="${rx.state==='listening'?'ok':'warn'}">${esc(rx.state||'—')}</span><span>MA-Net3</span><span>${esc(rx.interface||'—')} · ${esc(rx.bound_endpoint||'—')}</span><span>${rx.last_source?`src ${esc(rx.last_source)}`:'no packets'}</span><span>${rx.last_error?esc(rx.last_error):'no error'}</span></div><div class="row"><span>Multicast groups</span><span>${(rx.joined_groups||[]).length}/${(rx.configured_groups||[]).length}</span><span>MA-Net3</span><span>${esc((rx.joined_groups||[]).join(', ')||'—')}</span><span></span><span>${esc((rx.join_errors||[]).join(' | ')||'')}</span></div><div class="row"><span>Raw packet</span><span>${rx.last_packet_size??'—'} B</span><span>MA-Net3</span><span>${esc(rx.last_packet_prefix_ascii||'—')}</span><span>${esc(rx.last_packet_prefix_hex||'—')}</span><span></span></div>${(rx.raw_sources||[]).map(x=>`<div class="row"><span>Raw source</span><span>${esc(x.source_ip||'—')}</span><span>${x.packets??0} pkt</span><span>${x.last_size??'—'} B</span><span>${esc(x.prefix_ascii||'—')}</span><span>${esc((x.identity_hints||[]).join(' | ')||x.prefix_hex||'—')}</span></div>`).join('')}<div class="row"><span>Session join</span><span class="ok">DISABLED</span><span>MA-Net3</span><span>No join / no control</span><span></span><span></span></div><div class="row"><span>Web Remote probe</span><span class="ok">DISABLED</span><span>HTTP</span><span>URL candidate only</span><span></span><span></span></div><div class="row"><span>OSC commands</span><span class="ok">DISABLED</span><span>OSC</span><span>Info only · default ${osc.default_port||8000}</span><span></span><span></span></div></div></main>`;
  }
}
snDefine("ma-inspector-panel",MaInspectorPanel);


/* ===== osc-learn-panel.js ===== */
class OscLearnPanel extends HTMLElement {
  constructor(){super();this._hass=null;this._busy=false;}
  set hass(h){this._hass=h;this.render();}
  _state(){return Object.values(this._hass?.states||{}).find(x=>x.attributes?.osc_learn)?.attributes||{};}
  async _call(service){if(!this._hass||this._busy)return;this._busy=true;try{await this._hass.callService('dmx_monitor',service,{});}catch(e){this._error=e?.message||String(e);}finally{this._busy=false;this.render();}}
  connectedCallback(){this.render();}
  render(){
    const a=this._state(), learn=a.osc_learn||{}, input=a.osc_input||{}; const rows=learn.suggestions||[]; const active=!!learn.active;
    this.innerHTML=`<style>
 :host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}
 h2{margin:0}.sub{font-size:11px;color:#8d969f;margin:5px 0 14px}
 .toolbar{background:#15181c;border:1px solid #2c3239;border-radius:10px;padding:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
 button{background:#252a30;border:1px solid #3a4148;color:#eee;border-radius:6px;padding:8px 12px;cursor:pointer}.active{border-color:#2f9a65;color:#65dc99}.hint{color:#8d969f;font-size:10px}.err{color:#ef7777;font-size:10px}
 .row{display:grid;grid-template-columns:1.5fr .6fr .7fr .7fr 1fr .8fr;gap:8px;padding:10px;border-bottom:1px solid #282d33;font-size:11px}.table{margin-top:12px;background:#15181c;border:1px solid #2c3239;border-radius:10px;overflow:hidden}.head{color:#8d969f;font-size:9px;text-transform:uppercase}
 </style>
 <h2>OSC LEARN</h2><div class="sub">Apprentissage réel des messages reçus par l'entrée OSC. Aucune commande n'est envoyée.</div>
 <div class="toolbar"><button id="learn" class="${active?'active':''}">${active?'STOP LEARN':'START LEARN'}</button><button id="clear">EFFACER</button><span class="hint">Entrée OSC: ${input.enabled?'ACTIVE':'INACTIVE'} · ${input.messages??0} msg · dernière adresse ${input.last_address||'—'} · source ${input.last_source||'—'}</span>${this._error?`<span class="err">${esc(this._error)}</span>`:''}</div>
 <div class="table"><div class="row head"><span>ADDRESS</span><span>TYPE</span><span>MIN</span><span>MAX</span><span>SUGGESTION</span><span>SAMPLES</span></div>${rows.length?rows.map(x=>`<div class="row"><span>${esc(x.address||'—')}</span><span>${esc(x.value_type||'—')}</span><span>${x.observed_min??'—'}</span><span>${x.observed_max??'—'}</span><span>${esc((x.suggested_destination||'—')+' · '+(x.suggested_attribute||'—'))}</span><span>${x.samples??0}</span></div>`).join(''):`<div class="row"><span class="hint">${active?'En attente de messages OSC…':'Learn arrêté'}</span><span>—</span><span>—</span><span>—</span><span>—</span><span>—</span></div>`}</div>`;
    this.querySelector('#learn')?.addEventListener('click',()=>this._call(active?'stop_osc_learn':'start_osc_learn'));
    this.querySelector('#clear')?.addEventListener('click',()=>this._call('clear_osc_learn'));
  }
}
snDefine("osc-learn-panel",OscLearnPanel);


/* ===== osc-mapping-panel.js ===== */
class OscMappingPanel extends HTMLElement {
  constructor(){super();this._hass=null;this._msg='';}
  set hass(h){this._hass=h;this.render();}
  connectedCallback(){this.render();}
  _state(){return Object.values(this._hass?.states||{}).find(x=>Array.isArray(x.attributes?.mappings)&&Array.isArray(x.attributes?.events))?.attributes||{};}
  async _call(service,data){try{await this._hass.callService('dmx_monitor',service,data);this._msg='Action exécutée';}catch(e){this._msg=`Erreur: ${e?.message||e}`;}this.render();}
  render(){if(!this._hass){this.innerHTML='';return;}const st=this._state(),maps=st.mappings||[];const entities=Object.values(this._hass.states||{}).filter(x=>!x.entity_id.startsWith('sensor.dmx_monitor')).sort((a,b)=>a.entity_id.localeCompare(b.entity_id));
    this.innerHTML=`<style>:host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}h2{margin:0}.sub{font-size:11px;color:#8d969f;margin:5px 0 15px}.card{background:#15181c;border:1px solid #2c3239;border-radius:10px;padding:14px;margin-bottom:10px}.grid{display:grid;grid-template-columns:1.2fr 1fr 1.2fr 1fr;gap:8px}input,select{background:#0e1115;color:#eee;border:1px solid #3a4148;border-radius:6px;padding:8px;min-width:0}.btn{background:#252a30;border:1px solid #3a4148;color:#eee;border-radius:6px;padding:8px 10px;cursor:pointer}.row{display:grid;grid-template-columns:1.4fr 1fr 1.4fr 1fr auto;gap:8px;padding:9px 0;border-top:1px solid #282d33;font-size:11px;align-items:center}.muted{color:#8d969f;font-size:10px}.msg{margin-top:8px;font-size:11px}</style><h2>OSC / MIDI MAPPING ENGINE</h2><div class="sub">Mappings réellement enregistrés. Aucune ligne de démonstration.</div><div class="card"><div class="grid"><input id="address" placeholder="/show/fader/1 ou midi/cc/1/7"><input id="dest" value="light.turn_on" placeholder="domaine.service"><select id="target"><option value="">Choisir une entité HA</option>${entities.map(x=>`<option value="${esc(x.entity_id)}">${esc(x.entity_id)}</option>`).join('')}</select><input id="attr" value="brightness" placeholder="attribut / clé service"></div><button class="btn" id="add" style="margin-top:10px">CRÉER LE MAPPING</button>${this._msg?`<div class="msg">${esc(this._msg)}</div>`:''}</div><div class="card"><b>${maps.length} mapping(s)</b>${maps.length?maps.map(m=>`<div class="row"><span>${esc(m.address)}</span><span>${esc(m.destination)}</span><span>${esc(m.target)}</span><span>${esc(m.attribute||'value')}</span><button class="btn" data-remove="${esc(m.mapping_id)}">Supprimer</button></div>`).join(''):'<div class="muted" style="margin-top:10px">Aucun mapping configuré.</div>'}</div>`;
    this.querySelector('#add')?.addEventListener('click',()=>{const address=this.querySelector('#address').value.trim(),destination=this.querySelector('#dest').value.trim(),target=this.querySelector('#target').value,attribute=this.querySelector('#attr').value.trim()||'value';if(!address||!destination||!target){this._msg='Adresse, service et entité sont obligatoires.';this.render();return;}const mapping_id='map_'+address.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'')+'_'+Date.now().toString(36);this._call('create_control_mapping',{mapping_id,address,destination,target,attribute,in_min:0,in_max:1,out_min:0,out_max:255,min_interval_ms:50,deadband:0});});
    this.querySelectorAll('[data-remove]').forEach(b=>b.addEventListener('click',()=>this._call('remove_control_mapping',{mapping_id:b.dataset.remove})));
  }
}
snDefine("osc-mapping-panel",OscMappingPanel);


/* ===== osc-output-panel.js ===== */
class OscOutputPanel extends HTMLElement {
  connectedCallback(){
    const root=this.attachShadow({mode:'open'});
    root.innerHTML=`<style>:host{display:block;padding:14px;background:#111;color:#eee;font-family:system-ui} .row{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid #333}.ok{color:#6ee7a1}.off{color:#f0b36a} code{font-family:monospace}</style><h3>OSC OUTPUT</h3><div class="row"><span>Safety gate</span><b id="gate">OFF</b></div><div class="row"><span>Messages sent</span><b id="sent">0</b></div><div class="row"><span>Errors</span><b id="errors">0</b></div><div class="row"><span>Last target</span><code id="target">—</code></div><div class="row"><span>Last address</span><code id="address">—</code></div>`;
    this._root=root;
  }
  set hass(hass){this._hass=hass; this._update();}
  _update(){
    // NOTE (bug fix): this used to look for osc_output_enabled etc directly
    // on hass.states, which is a dict keyed by entity_id -- those fields
    // are never there, they are ATTRIBUTES of sensor.dmx_monitor_osc_sent.
    // The readout was therefore always stuck at its blank defaults.
    if(!this._root)return;
    const st=this._hass?.states?.['sensor.dmx_monitor_osc_sent'];
    const d=st?.attributes||{};
    const g=this._root.getElementById('gate'); if(!g)return;
    g.textContent=d.osc_output_enabled?'ON':'OFF'; g.className=d.osc_output_enabled?'ok':'off';
    this._root.getElementById('sent').textContent=d.osc_sent??0;
    this._root.getElementById('errors').textContent=d.osc_errors??0;
    this._root.getElementById('target').textContent=d.osc_last_target||'—';
    this._root.getElementById('address').textContent=d.osc_last_address||'—';
  }
}
snDefine('osc-output-panel',OscOutputPanel);


/* ===== osc-source-profiles.js ===== */
class OscSourceProfiles extends HTMLElement {
  set hass(h){this._hass=h;this.render()}
  _attrs(entityIdFragment){return Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes(entityIdFragment))?.attributes||{}}
  _profiles(){return this._attrs('osc_source_profiles').profiles||[]}
  _targets(){return this._attrs('osc_targets').targets||[]}
  _midiTargets(){return Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes('midi_output_sent'))?.attributes?.targets||[]}
  _security(){const c=Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes('security_unlocked'));return c?.state==='true'||c?.state==='on'}
  async _call(service,data){try{await this._hass.callService('dmx_monitor',service,data);this._msg='Envoyé';this._armed=null;setTimeout(()=>this.render(),400);setTimeout(()=>this.render(),1500)}catch(e){this._msg=`Erreur: ${e?.message||e}`;this.render()}}
  _placeholders(address){const m=(address||'').match(/\{[^}]+\}/g)||[];return [...new Set(m.map(x=>x.slice(1,-1)))]}
  render(){
    if(!this._hass)return;
    const profiles=this._profiles(), targets=this._targets(), midiTargets=this._midiTargets(), unlocked=this._security();
    const oscOutputEnabled=this._attrs('osc_sent').osc_output_enabled===true;
    if(!this._selectedProfile&&profiles.length)this._selectedProfile=profiles[0].key;
    const profile=profiles.find(p=>p.key===this._selectedProfile);
    const actions=profile?.actions||[];
    if(!this._selectedAction&&actions.length)this._selectedAction=actions[0].key;
    const action=actions.find(a=>a.key===this._selectedAction);
    const placeholders=action?this._placeholders(action.address):[];
    this.innerHTML=`<style>:host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}
h2{margin:0}.sub{font-size:11px;color:#8d969f;margin:5px 0 14px}
.help{padding:10px;border-left:3px solid #e5bf6b;background:#151a1f;font-size:11px;line-height:1.5;margin-bottom:14px}
.small{font-size:10px;color:#8f99a3;margin-bottom:12px}.on{color:#68df9a}.error{color:#ef7777}
.section{background:#15181c;border:1px solid #2c3239;border-radius:10px;padding:14px;margin-bottom:14px}
.title{font-weight:700;margin-bottom:8px;color:#eef1f4}
input,select{box-sizing:border-box;width:100%;background:#0b0d10;color:#eee;border:1px solid #343b43;border-radius:6px;padding:8px;margin-bottom:7px}
.grid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:7px}
.btn{padding:8px 10px;background:#171c21;color:#eee;border:1px solid #39424c;border-radius:7px;cursor:pointer;margin:4px 5px 0 0}
.primary{background:#164d70}.danger{border-color:#8b3f45}
.row{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid #23282e;font-size:12px}
code{font-family:monospace;font-size:11px;color:#aab1b8}
.msg{margin-top:10px;padding:8px;border:1px solid #39414a;border-radius:8px;font-size:11px}
.placeholders{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:7px;margin:8px 0}
</style>
<h2>OSC SHOW CONTROL BANK</h2><div class="sub">Bibliothèque de commandes par profil, cibles et envoi réel via Home Assistant.</div>
<div class="small">Sécurité : <b class="${unlocked?'on':'error'}">${unlocked?'DÉVERROUILLÉE':'VERROUILLÉE'}</b>${unlocked?'':' — déverrouille les commandes actives (page Sécurité) avant d\u2019envoyer.'} · Sortie OSC : <b class="${oscOutputEnabled?'on':'error'}">${oscOutputEnabled?'ARMÉE':'DÉSARMÉE'}</b></div>
<button class="btn ${oscOutputEnabled?'primary':''}" id="toggle-osc-output" ${unlocked?'':'disabled'}>${oscOutputEnabled?'Désarmer la sortie OSC':'Armer la sortie OSC'}</button>

<div class="section"><div class="title">CIBLES OSC</div>
${targets.length?targets.map(t=>`<div class="row"><span>${esc(t.name)} · ${esc(t.host)}:${t.port}</span><button class="btn danger" data-del-target="${esc(t.target_id)}">Supprimer</button></div>`).join(''):'<div class="small">Aucune cible configurée.</div>'}
<div class="grid" style="margin-top:10px"><input id="t-name" placeholder="Nom (ex: grandMA3 FOH)"><input id="t-host" placeholder="Adresse IP"><input id="t-port" type="number" value="8000" placeholder="Port"></div>
<button class="btn" id="add-target">+ Ajouter la cible</button>
</div>

<div class="section"><div class="title">CIBLES MIDI</div>
${midiTargets.length?midiTargets.map(t=>`<div class="row"><span>${esc(t.name)} · ${esc(t.port_name)}</span><button class="btn danger" data-del-miditarget="${esc(t.target_id)}">Supprimer</button></div>`).join(''):'<div class="small">Aucune cible configurée.</div>'}
<div class="grid" style="margin-top:10px"><input id="mt-name" placeholder="Nom (ex: Console lumière)"><input id="mt-port" placeholder="Nom du port MIDI système"></div>
<button class="btn" id="add-miditarget">+ Ajouter la cible MIDI</button>
<div class="small" style="margin-top:10px">Envoyer un message MIDI brut :</div>
<div class="grid"><select id="mt-target">${midiTargets.map(t=>`<option value="${esc(t.target_id)}">${esc(t.name)}</option>`).join('')||'<option value="">Aucune cible</option>'}</select><select id="mt-type"><option value="note_on">note_on</option><option value="note_off">note_off</option><option value="control_change">control_change</option><option value="program_change">program_change</option></select><input id="mt-data" placeholder='Data JSON (ex: {"note":60,"velocity":127})'></div>
<button class="btn primary" id="send-midi" ${(unlocked&&midiTargets.length)?'':'disabled'}>Envoyer</button>
</div>

<div class="section"><div class="title">ENVOYER UNE COMMANDE</div>
<select id="profile-select">${profiles.map(p=>`<option value="${esc(p.key)}" ${p.key===this._selectedProfile?'selected':''}>${esc(p.label_fr||p.label_en||p.key)}</option>`).join('')||'<option>Aucun profil</option>'}</select>
${profile?`<div class="small">${esc(profile.description_fr||profile.description_en||'')}</div>`:''}
${profile&&!actions.length&&(profile.setup_steps_fr||[]).length?`<div class="help"><b>Pas de commandes fixes pour ce profil</b> — l'espace d'adresses dépend de l'installation/du show. Marche à suivre : <ol style="margin:6px 0 0 18px;padding:0">${profile.setup_steps_fr.map(s=>`<li>${esc(s)}</li>`).join('')}</ol></div>`:''}
<select id="action-select">${actions.map(a=>`<option value="${esc(a.key)}" ${a.key===this._selectedAction?'selected':''}>${esc(a.label_fr||a.label_en||a.key)}</option>`).join('')||'<option>Aucune action documentée — utiliser OSC générique ou Learn</option>'}</select>
${action?`<div class="small">Adresse : <code>${esc(action.address)}</code>${action.notes_fr?' · '+esc(action.notes_fr):''}</div>`:''}
${placeholders.length?`<div class="placeholders">${placeholders.map(p=>`<input data-ph="${esc(p)}" placeholder="${esc(p)}">`).join('')}</div>`:''}
${action&&action.value_type&&action.value_type!=='none'?`<input id="value" placeholder="Valeur (${esc(action.value_type)})">`:''}
<select id="target-select">${targets.map(t=>`<option value="${esc(t.target_id)}">${esc(t.name)}</option>`).join('')||'<option value="">Aucune cible — ajoute-en une ci-dessus</option>'}</select>
<button class="btn primary" id="send" ${(unlocked&&oscOutputEnabled&&action&&targets.length)?'':'disabled'}>Envoyer</button>
</div>

<div class="section"><div class="title">OSC GÉNÉRIQUE</div>
<div class="small">Adresse et arguments libres, pour tout équipement OSC hors bibliothèque.</div>
<input id="generic-address" placeholder="Adresse (ex: /cue/go)">
<input id="generic-args" placeholder='Args JSON (ex: [1] ou [] ou [0.5,"text"])'>
<select id="generic-target">${targets.map(t=>`<option value="${esc(t.target_id)}">${esc(t.name)}</option>`).join('')||'<option value="">Aucune cible</option>'}</select>
<button class="btn primary" id="send-generic" ${(unlocked&&oscOutputEnabled&&targets.length)?'':'disabled'}>Envoyer</button>
</div>
${this._msg?`<div class="msg">${esc(this._msg)}</div>`:''}`;

    this.querySelector('#add-target')?.addEventListener('click',()=>{
      const name=this.querySelector('#t-name').value.trim(), host=this.querySelector('#t-host').value.trim(), port=+this.querySelector('#t-port').value||8000;
      if(!name||!host){this._msg='Nom et adresse IP obligatoires.';this.render();return;}
      const target_id='t_'+name.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'')+'_'+Date.now().toString(36);
      this._call('create_osc_target',{target_id,name,host,port});
    });
    this.querySelector('#toggle-osc-output')?.addEventListener('click',()=>this._call('set_osc_output_enabled',{enabled:!oscOutputEnabled}));
    this.querySelectorAll('[data-del-target]').forEach(b=>b.addEventListener('click',()=>this._call('remove_osc_target',{target_id:b.dataset.delTarget})));
    this.querySelector('#add-miditarget')?.addEventListener('click',()=>{
      const name=this.querySelector('#mt-name').value.trim(), port_name=this.querySelector('#mt-port').value.trim();
      if(!name||!port_name){this._msg='Nom et port MIDI obligatoires.';this.render();return;}
      const target_id='mt_'+name.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'')+'_'+Date.now().toString(36);
      this._call('create_midi_target',{target_id,name,port_name});
    });
    this.querySelectorAll('[data-del-miditarget]').forEach(b=>b.addEventListener('click',()=>this._call('remove_midi_target',{target_id:b.dataset.delMiditarget})));
    this.querySelector('#send-midi')?.addEventListener('click',()=>{
      const target_id=this.querySelector('#mt-target')?.value;
      if(!target_id)return;
      let data;
      try{data=JSON.parse(this.querySelector('#mt-data').value||'{}');}catch(e){this._msg='JSON invalide.';this.render();return;}
      this._call('send_midi',{target_id,message_type:this.querySelector('#mt-type').value,data});
    });
    this.querySelector('#profile-select')?.addEventListener('change',e=>{this._selectedProfile=e.target.value;this._selectedAction=null;this.render()});
    this.querySelector('#action-select')?.addEventListener('change',e=>{this._selectedAction=e.target.value;this.render()});
    this.querySelector('#send')?.addEventListener('click',()=>{
      const target_id=this.querySelector('#target-select')?.value;
      if(!target_id||!action)return;
      const params={};
      this.querySelectorAll('[data-ph]').forEach(inp=>{params[inp.dataset.ph]=inp.value});
      const missing=placeholders.filter(p=>!params[p]);
      if(missing.length){this._msg=`Paramètre(s) manquant(s) : ${missing.join(', ')}`;this.render();return;}
      const valueInput=this.querySelector('#value');
      let args=[];
      if(valueInput){
        const raw=valueInput.value;
        const asNum=Number(raw);
        args=[raw!==''&&!Number.isNaN(asNum)&&action.value_type!=='string'?asNum:raw];
      }
      this._call('send_osc_profile_action',{profile:this._selectedProfile,action:this._selectedAction,target_id,params,args});
    });
    this.querySelector('#send-generic')?.addEventListener('click',()=>{
      const target_id=this.querySelector('#generic-target')?.value;
      const address=this.querySelector('#generic-address')?.value.trim();
      if(!target_id||!address){this._msg='Cible et adresse obligatoires.';this.render();return;}
      let args=[];
      const raw=this.querySelector('#generic-args')?.value.trim();
      if(raw){
        try{args=JSON.parse(raw);if(!Array.isArray(args))throw new Error();}catch(e){this._msg='Args JSON invalide (doit être une liste, ex: [1]).';this.render();return;}
      }
      this._call('send_osc',{target_id,address,args});
    });
  }
}
snDefine("osc-source-profiles",OscSourceProfiles);


/* ===== rule-builder.js ===== */
class ShowNetworkRuleBuilder extends HTMLElement {
  constructor(){super();this.selected=new Set();this.rules=[];this._hass=null;this.editing=null;this._onDmx=e=>this.acceptDmxSelection(e)}
  connectedCallback(){window.addEventListener('dmx-channel-selected',this._onDmx);this.render();this.sync()}
  disconnectedCallback(){window.removeEventListener('dmx-channel-selected',this._onDmx)}
  set hass(v){this._hass=v;this.sync();this.refreshTargets()}
  acceptDmxSelection(e){const d=e.detail||{};if(!d.channel)return;if(d.universe)this.q('#universe').value=d.universe;if(d.source)this.q('#source').value=d.source;this.selected.add(+d.channel);this.paint()}
  q(id){return this.querySelector(id)}
  async sync(){const states=Object.values(this._hass?.states||{});const s=states.find(x=>Array.isArray(x.attributes?.dmx_rules));if(s)this.rules=s.attributes.dmx_rules.map(r=>({...r,channels:[...(r.channels||[])]}));this.renderList()}
  async call(service,data){if(!this._hass){this.setTrace('Home Assistant non connecté.');return false}try{await this._hass.callService('dmx_monitor',service,data);await new Promise(r=>setTimeout(r,400));await this.sync();setTimeout(()=>this.sync(),1500);return true}catch(e){this.setTrace(`Erreur HA : ${e?.message||e}`);return false}}
  render(){this.innerHTML=`<style>:host{display:block;background:#090b0e;color:#eee;font-family:Inter,system-ui,sans-serif;padding:16px}.layout{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:14px}.panel{background:#111419;border:1px solid #292f36;border-radius:8px;padding:12px}.grid{display:grid;grid-template-columns:repeat(16,1fr);gap:3px}.ch{height:36px;border:1px solid #2a3037;background:#252a30;color:#ddd;border-radius:3px;font-size:9px}.ch.selected{background:#1d5c3a;border-color:#45a56f}.ch.hot{box-shadow:inset 0 -4px 0 #d4a72c}.v{display:block;font-weight:700;margin-top:3px}label{display:block;font-size:10px;color:#9da5ad;margin:8px 0 4px}input,select,textarea{width:100%;box-sizing:border-box;background:#090b0e;color:#eee;border:1px solid #303740;border-radius:5px;padding:7px}.row{display:grid;grid-template-columns:1fr 1fr;gap:8px}.actions{display:flex;gap:7px;margin-top:12px;flex-wrap:wrap}.action{border:1px solid #3b444e;background:#191e24;color:#eee;border-radius:5px;padding:8px 10px}.primary{background:#1d5c3a}.danger{background:#32191c}.list{margin-top:10px;display:grid;gap:6px}.rule{border:1px solid #292f36;border-radius:6px;padding:8px;background:#0d1014}.rule strong{display:block}.pill{font-size:9px;color:#9da5ad}.trace{margin-top:12px;border-top:1px solid #292f36;padding-top:10px;font-size:11px}.mono{font-family:ui-monospace,monospace}.hint{font-size:9px;color:#7f8992}</style>
<h2>RULE BUILDER</h2><div style="font-size:10px;color:#8d969f;margin-bottom:12px">DMX VIEW → RULE · HOME ASSISTANT · RECEIVE ONLY</div>
<div class="layout"><div class="panel"><div class="grid" id="grid"></div><div class="hint" style="margin-top:8px">Clique un canal pour le sélectionner. Jaune = niveau DMX non nul.</div></div><div class="panel">
<label>Nom</label><input id="name" value="Nouvelle règle"><div class="row"><div><label>Univers</label><input id="universe" type="number" min="1" value="1"></div><div><label>Source</label><select id="source"><option value="">Toutes</option><option>ENTTEC</option><option>sACN</option><option>Art-Net</option></select></div></div>
<div class="row"><div><label>Mode</label><select id="mode"><option value="any">ANY</option><option value="all">ALL</option><option value="x_of_y">X OF Y</option></select></div><div><label>X</label><input id="x" type="number" min="1" value="1"></div></div>
<div class="row"><div><label>Threshold ON</label><input id="ton" type="number" min="0" max="255" value="10"></div><div><label>Threshold OFF</label><input id="toff" type="number" min="0" max="255" value="5"></div></div>
<div class="row"><div><label>Délai ON (ms)</label><input id="on" type="number" min="0" value="0"></div><div><label>Délai OFF (ms)</label><input id="off" type="number" min="0" value="0"></div></div>
<label>Action ON — domaine</label><select id="domain"></select><label>Service ON</label><select id="service"></select><label>Entité ON</label><select id="entity"><option value="">Aucune / service global</option></select><label>Données ON JSON</label><textarea id="data" rows="2" placeholder='{"brightness_pct":50}'></textarea>
<label>Action OFF / retour</label><div class="row"><select id="offdomain"></select><select id="offservice"></select></div><select id="offentity" style="margin-top:5px"><option value="">Aucune / service global</option></select><label>Données OFF JSON</label><textarea id="offdata" rows="2" placeholder='{"transition":2}'></textarea>
<div class="actions"><button class="action" id="clear">Effacer sélection</button><button class="action primary" id="save">Créer / enregistrer</button><button class="action" id="test">Tester live</button><button class="action danger" id="clear-history">Effacer l'historique</button></div><div class="trace"><b>Pourquoi active ?</b><div id="trace">Sélectionne des canaux.</div></div><div class="list" id="list"></div></div></div>`;
    const g=this.q('#grid');for(let i=1;i<=512;i++){let b=document.createElement('button');b.className='ch';b.dataset.ch=i;b.textContent=i;b.onclick=()=>this.toggle(i);g.appendChild(b)}
    this.q('#clear').onclick=()=>{this.selected.clear();this.editing=null;this.paint()};this.q('#save').onclick=()=>this.save();this.q('#test').onclick=()=>this.test();this.q('#clear-history').onclick=()=>this.call('clear_rule_history',{});
    this.q('#domain').onchange=()=>this.refreshServices('#domain','#service','#entity');this.q('#offdomain').onchange=()=>this.refreshServices('#offdomain','#offservice','#offentity');this.refreshTargets();this.paint();this.renderList()
  }
  toggle(c){this.selected.has(c)?this.selected.delete(c):this.selected.add(c);this.paint()}
  paint(){this.querySelectorAll('.ch').forEach(b=>b.classList.toggle('selected',this.selected.has(+b.dataset.ch)));const a=[...this.selected].sort((x,y)=>x-y);this.setTrace(a.length?`<span class="mono">${a.join(', ')}</span> · ${a.length} canal(aux)`:'Sélectionne des canaux.')}
  setTrace(t){const e=this.q('#trace');if(e)e.innerHTML=t}
  json(id){try{const v=this.q(id)?.value||'';return v?JSON.parse(v):{}}catch{return null}}
  detail(){const q=id=>this.q(id)?.value||'',on=this.json('#data'),off=this.json('#offdata');const channels=[...this.selected].sort((a,b)=>a-b);if(on===null||off===null){this.setTrace('JSON invalide.');return null}if(!channels.length){this.setTrace('Sélectionne au moins un canal.');return null}if(q('#mode')==='x_of_y'&&(+q('#x')<1||+q('#x')>channels.length)){this.setTrace('X doit être compris entre 1 et le nombre de canaux.');return null}return {name:q('#name').trim(),universe:+q('#universe'),source:q('#source')||null,channels,mode:q('#mode'),x:+q('#x'),threshold_on:+q('#ton'),threshold_off:+q('#toff'),on_delay_ms:+q('#on'),off_delay_ms:+q('#off'),enabled:false,test_mode:false,action:{domain:q('#domain'),entity_id:q('#entity')||null,service:q('#service'),data:on},off_action:{domain:q('#offdomain'),entity_id:q('#offentity')||null,service:q('#offservice'),data:off}}}
  async save(){const d=this.detail();if(!d||!d.name){this.setTrace('Nom obligatoire.');return}const service=this.editing?'update_rule':'create_rule',payload=this.editing?{old_name:this.editing,...d}:d;if(await this.call(service,payload)){this.editing=d.name;this.setTrace('Règle enregistrée. Activation explicite requise.')}}
  async test(){const d=this.detail();if(!d)return;const ok=await this.call('test_rule',{name:this.editing||d.name,values:this.currentValues()});if(ok)this.setTrace('Test exécuté sans action HA et sans modifier l’état de la règle.')}
  currentValues(){
    const u=+this.q('#universe').value,s=this.q('#source').value;const states=this._hass?.states||{};
    for(const st of Object.values(states)){
      const us=st.attributes?.universes;if(!Array.isArray(us))continue;
      for(const x of us){
        if(+x.universe!==u||!(!s||x.source===s||x.protocol===s))continue;
        if(Array.isArray(x.values))return x.values;
        if(x.values_b64){try{const bin=atob(x.values_b64);return Array.from(bin,c=>c.charCodeAt(0))}catch(e){return undefined}}
      }
    }
    return undefined;
  }
  refreshTargets(){if(!this._hass)return;this.refreshServices('#domain','#service','#entity');this.refreshServices('#offdomain','#offservice','#offentity')}
  refreshServices(domainSel,serviceSel,entitySel){const d=this.q(domainSel),s=this.q(serviceSel),e=this.q(entitySel);if(!d||!s||!e)return;const services=this._hass?.services||{}, domains=Object.keys(services).sort();const prevD=d.value;d.innerHTML=domains.map(x=>`<option value="${x}">${x}</option>`).join('');if(domains.includes(prevD))d.value=prevD;const domain=services[d.value]||{}, names=Object.keys(domain).sort(),prevS=s.value;s.innerHTML=names.map(x=>`<option value="${x}">${x}</option>`).join('');if(names.includes(prevS))s.value=prevS;const entities=Object.values(this._hass.states||{}).filter(x=>x.entity_id?.startsWith(`${d.value}.`));const prevE=e.value;e.innerHTML='<option value="">Aucune / service global</option>'+entities.map(x=>`<option value="${x.entity_id}">${x.entity_id} — ${x.attributes?.friendly_name||''}</option>`).join('');if(entities.some(x=>x.entity_id===prevE))e.value=prevE}
  renderList(){const l=this.q('#list');if(!l)return;l.innerHTML='<b>Règles Home Assistant</b>';if(!this.rules.length){l.innerHTML+='<div class="pill">Aucune règle.</div>';return}this.rules.forEach(r=>{const d=document.createElement('div');d.className='rule';d.innerHTML=`<strong>${r.name}</strong><span class="pill">U${r.universe} · ${r.source||'toutes'} · ${(r.channels||[]).length} ch · ${r.enabled?'ACTIVE':'INACTIVE'} · ${r.test_mode?'TEST':''}</span><div class="actions"><button class="action" data-a="toggle">${r.enabled?'Désactiver':'Activer'}</button><button class="action" data-a="testmode">${r.test_mode?'Quitter test':'Mode test'}</button><button class="action" data-a="edit">Éditer</button><button class="action" data-a="duplicate">Dupliquer</button><button class="action danger" data-a="delete">Supprimer</button></div>`;d.querySelectorAll('button').forEach(b=>b.onclick=()=>this.ruleAction(r,b.dataset.a));l.appendChild(d)})}
  async ruleAction(r,a){if(a==='toggle')return this.call('set_rule_enabled',{name:r.name,enabled:!r.enabled});if(a==='testmode')return this.call('set_rule_test_mode',{name:r.name,enabled:!r.test_mode});if(a==='delete')return this.call('remove_rule',{name:r.name});if(a==='duplicate')return this.call('create_rule',{...r,name:`${r.name} copie`,enabled:false});if(a==='edit'){this.editing=r.name;this.selected=new Set(r.channels||[]);const m={'#name':r.name,'#universe':r.universe,'#source':r.source||'','#mode':r.mode||'any','#x':r.x||1,'#ton':r.threshold_on??10,'#toff':r.threshold_off??5,'#on':r.on_delay_ms||0,'#off':r.off_delay_ms||0,'#domain':r.action?.domain||'light','#entity':r.action?.entity_id||'','#service':r.action?.service||'turn_on','#data':JSON.stringify(r.action?.data||{}),'#offdomain':r.off_action?.domain||'light','#offentity':r.off_action?.entity_id||'','#offservice':r.off_action?.service||'turn_off','#offdata':JSON.stringify(r.off_action?.data||{})};for(const[id,v]of Object.entries(m)){const el=this.q(id);if(el)el.value=v}this.refreshTargets();this.paint()}}
}
snDefine('show-network-rule-builder',ShowNetworkRuleBuilder);



/* ===== dmx-circuit-monitor-panel.js ===== */
class DmxCircuitMonitorPanel extends HTMLElement {
  set hass(h){this._hass=h;this.render()}
  _state(){return Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes('dmx_circuit_group_count'))?.attributes||{}}
  async _call(service,data){try{await this._hass.callService('dmx_monitor',service,data);this._msg='Enregistré';setTimeout(()=>this.render(),400);setTimeout(()=>this.render(),1500)}catch(e){this._msg=`Erreur: ${e?.message||e}`;this.render()}}
  render(){if(!this._hass)return;const groups=this._state().groups||[];
    this.innerHTML=`<style>:host{display:block}.box{padding:15px;border:1px solid #30363d;border-radius:12px;background:#111519;color:#eee}.help{padding:10px;border-left:3px solid #2586c8;background:#151a1f;font-size:11px;line-height:1.5;margin-bottom:12px}.grid{display:grid;grid-template-columns:2fr 1fr 1fr 2fr;gap:7px}.row{padding:10px;border:1px solid #293039;border-radius:8px;margin-top:8px}.circuits{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}.chip{font-size:10px;padding:4px 7px;border:1px solid #39424c;border-radius:999px}.on{color:#68df9a}.partial{color:#e5bf6b}.signal_lost{color:#ef7777}input,select{box-sizing:border-box;width:100%;background:#0b0d10;color:#eee;border:1px solid #39424c;border-radius:6px;padding:8px}.btn{padding:8px 10px;background:#171c21;color:#eee;border:1px solid #39424c;border-radius:7px;cursor:pointer;margin:7px 5px 0 0}@media(max-width:800px){.grid{grid-template-columns:1fr}}</style><div class="box"><h3>DMX CIRCUIT MONITOR</h3><div class="help"><b>À quoi ça sert ?</b> Surveille la valeur de plusieurs circuits DMX déjà reçus par Show Network. Il ne transmet rien. Exemple : vérifier que les circuits d'alimentation d'une salle sont réellement à ON. <b>Ce n'est pas le Watchdog</b> : le Watchdog vérifie la présence du signal, pas la valeur des circuits.</div><div class="grid"><input id="n" placeholder="Nom : Alimentations Grande Salle"><select id="p"><option>sACN</option><option>Art-Net</option><option>ENTTEC</option></select><input id="u" type="number" min="1" value="1" placeholder="Univers"><input id="c" placeholder="Circuits : 401,402,403"></div><div class="grid" style="margin-top:7px"><input id="src" placeholder="Source optionnelle"><input id="on" type="number" min="0" max="255" value="128" placeholder="Seuil ON"><input id="off" type="number" min="0" max="255" value="10" placeholder="Seuil OFF"><button class="btn" id="add">Créer le groupe</button></div>${this._msg?`<div class="help">${esc(this._msg)}</div>`:''}${groups.map(g=>`<div class="row"><b>${esc(g.name)}</b> · U${g.universe} · ${esc(g.protocol)} <b class="${esc(g.state)}">${esc(String(g.state||'—').toUpperCase())}</b><div class="circuits">${(g.circuits||[]).map(c=>`<span class="chip ${esc(c.state)}">${esc(c.name||('CH '+c.channel))}: ${c.value??'—'} · ${esc(c.state)}</span>`).join('')}</div><button class="btn" data-del="${esc(g.group_id)}">Supprimer</button></div>`).join('')||'<div class="help">Aucun groupe de circuits configuré.</div>'}</div>`;
    this.querySelector('#add')?.addEventListener('click',()=>{const channels=this.querySelector('#c').value.split(',').map(x=>+x.trim()).filter(x=>x>=1&&x<=512);if(!channels.length)return;this._call('dmx_circuit_monitor_upsert',{name:this.querySelector('#n').value.trim()||'DMX circuits',protocol:this.querySelector('#p').value,universe:+this.querySelector('#u').value,source:this.querySelector('#src').value.trim(),circuits:channels.map(channel=>({channel,on_threshold:+this.querySelector('#on').value,off_threshold:+this.querySelector('#off').value})),enabled:true})});
    this.querySelectorAll('[data-del]').forEach(b=>b.onclick=()=>this._call('dmx_circuit_monitor_remove',{group_id:b.dataset.del}));
  }
}
snDefine('dmx-circuit-monitor-panel',DmxCircuitMonitorPanel);

/* ===== power-manager-panel.js ===== */
class PowerManagerPanel extends HTMLElement {
  constructor(){super();this._channels=[]}
  set hass(h){this._hass=h;this.render()}
  _state(){return Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes('power_manager_button_count'))?.attributes||{}}
  _security(){const c=Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes('security_unlocked'));return c?.state==='true'||c?.state==='on'}
  async _call(service,data){try{await this._hass.callService('dmx_monitor',service,data);this._msg='Action exécutée';setTimeout(()=>this.render(),400);setTimeout(()=>this.render(),1500)}catch(e){this._msg=`Erreur: ${e?.message||e}`;this.render()}}
  render(){if(!this._hass)return;const buttons=this._state().buttons||[],unlocked=this._security();
    this.innerHTML=`<style>:host{display:block}.box{padding:15px;border:1px solid #30363d;border-radius:12px;background:#111519;color:#eee}.help{padding:10px;border-left:3px solid #e5bf6b;background:#151a1f;font-size:11px;line-height:1.5;margin-bottom:12px}.grid{display:grid;grid-template-columns:2fr 1fr 1fr 2fr;gap:7px}.button{padding:12px;border:1px solid #293039;border-radius:9px;margin-top:9px}.state{font-size:20px;font-weight:800}.on{color:#68df9a}.error{color:#ef7777}.off{color:#8f99a3}input,select{box-sizing:border-box;width:100%;background:#0b0d10;color:#eee;border:1px solid #39424c;border-radius:6px;padding:8px}.btn{padding:8px 10px;background:#171c21;color:#eee;border:1px solid #39424c;border-radius:7px;cursor:pointer;margin:7px 5px 0 0}.primary{background:#164d70}.danger{border-color:#8b3f45}.chrow{display:grid;grid-template-columns:70px 1fr 80px 80px 90px 90px 60px;gap:5px;margin-top:5px}.small{font-size:10px;color:#8f99a3}@media(max-width:900px){.grid,.chrow{grid-template-columns:1fr 1fr}}</style><div class="box"><h3>POWER MANAGER</h3><div class="help"><b>À quoi ça sert ?</b> Crée plusieurs boutons personnalisés pour alimenter/éteindre une salle par circuits DMX avec un déphasage afin de limiter l'appel de courant. <b>C'est une sortie DMX active</b>, totalement séparée du DMX Monitor receive-only. Une commande exige le déverrouillage de sécurité Show Network. Les valeurs sont maintenues après la séquence.</div><div class="small">Sécurité : <b class="${unlocked?'on':'error'}">${unlocked?'DÉVERROUILLÉE':'VERROUILLÉE'}</b></div><div class="grid"><input id="name" placeholder="Nom du bouton"><input id="icon" value="mdi:power" placeholder="Icône"><select id="transport"><option value="sacn">sACN</option><option value="artnet">Art-Net</option><option value="enttec">ENTTEC</option></select><input id="host" placeholder="Destination Art-Net / sACN unicast (vide = sACN multicast)"></div><div class="grid" style="margin-top:7px"><input id="universe" type="number" min="1" value="1" placeholder="Univers"><input id="device" placeholder="ENTTEC /dev/…"><input id="priority" type="number" min="1" max="200" value="100" placeholder="Priorité sACN"><button class="btn" id="addch">+ Circuit</button></div><div id="channels"></div><button class="btn primary" id="save">Créer le bouton</button>${this._msg?`<div class="help">${esc(this._msg)}</div>`:''}<h4>Boutons configurés</h4>${buttons.map(b=>`<div class="button"><b>${esc(b.name)}</b> <span class="small">${esc(b.icon||'mdi:power')} · ${esc(b.output?.output||'—')} U${b.output?.universe??'—'}</span><div class="state ${esc(b.state)}">${esc(String(b.state||'unknown').toUpperCase())}</div><div class="small">${(b.channels||[]).length} circuit(s) · ${b.last_error?esc(b.last_error):'aucune erreur'}</div><button class="btn primary" data-run="${esc(b.button_id)}" data-on="1">ON</button><button class="btn" data-run="${esc(b.button_id)}" data-on="0">OFF</button><button class="btn danger" data-del="${esc(b.button_id)}">Supprimer</button></div>`).join('')||'<div class="help">Aucun bouton Power Manager configuré.</div>'}</div>`;
    const paint=()=>{const host=this.querySelector('#channels');host.innerHTML=this._channels.map((c,i)=>`<div class="chrow"><input data-i="${i}" data-k="channel" type="number" min="1" max="512" value="${c.channel||1}"><input data-i="${i}" data-k="name" placeholder="Nom circuit" value="${esc(c.name||'')}"><input data-i="${i}" data-k="on_value" type="number" min="0" max="255" value="${c.on_value??255}"><input data-i="${i}" data-k="off_value" type="number" min="0" max="255" value="${c.off_value??0}"><input data-i="${i}" data-k="on_delay_s" type="number" min="0" step="0.1" value="${c.on_delay_s??0}"><input data-i="${i}" data-k="off_delay_s" type="number" min="0" step="0.1" value="${c.off_delay_s??0}"><button class="btn" data-rm="${i}">×</button></div>`).join('');host.querySelectorAll('input[data-i]').forEach(x=>x.oninput=()=>{const i=+x.dataset.i,k=x.dataset.k;this._channels[i][k]=k==='name'?x.value:+x.value});host.querySelectorAll('[data-rm]').forEach(x=>x.onclick=()=>{this._channels.splice(+x.dataset.rm,1);paint()})};
    if(!this._channels.length)this._channels=[{channel:1,name:'',on_value:255,off_value:0,on_delay_s:0,off_delay_s:.5}];paint();
    this.querySelector('#addch').onclick=()=>{this._channels.push({channel:Math.min(512,(this._channels.at(-1)?.channel||0)+1),name:'',on_value:255,off_value:0,on_delay_s:.5,off_delay_s:.5});paint()};
    this.querySelector('#save').onclick=()=>this._call('power_manager_upsert_button',{name:this.querySelector('#name').value.trim()||'Power',icon:this.querySelector('#icon').value.trim()||'mdi:power',output:{output:this.querySelector('#transport').value,universe:+this.querySelector('#universe').value,host:this.querySelector('#host').value.trim(),enttec_device:this.querySelector('#device').value.trim(),priority:+this.querySelector('#priority').value},channels:this._channels,enabled:true,confirm:true});
    this.querySelectorAll('[data-run]').forEach(b=>b.onclick=()=>{const item=buttons.find(x=>x.button_id===b.dataset.run),arm=`${b.dataset.run}:${b.dataset.on}`;if(item?.confirm&&this._armed!==arm){this._armed=arm;this._msg=`Confirmation : reclique sur ${b.dataset.on==='1'?'ON':'OFF'} pour « ${item.name} ».`;this.render();setTimeout(()=>{if(this._armed===arm){this._armed=null;this._msg='';this.render()}},5000);return;}this._armed=null;this._call('power_manager_run',{button_id:b.dataset.run,on:b.dataset.on==='1'})});
    this.querySelectorAll('[data-del]').forEach(b=>b.onclick=()=>this._call('power_manager_remove_button',{button_id:b.dataset.del}));
  }
}
snDefine('power-manager-panel',PowerManagerPanel);

/* ===== dmx-scene-bank-panel.js ===== */
class DmxSceneBankPanel extends HTMLElement {
  constructor(){super();this._channels=[];this._editing=null;}
  set hass(h){this._hass=h;this.render()}
  _attrs(){return Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes('dmx_scene_bank_count'))?.attributes||{}}
  _security(){const c=Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes('security_unlocked'));return c?.state==='true'||c?.state==='on'}
  async _call(service,data){try{await this._hass.callService('dmx_monitor',service,data);this._msg='Enregistré';setTimeout(()=>this.render(),400);setTimeout(()=>this.render(),1500)}catch(e){this._msg=`Erreur: ${e?.message||e}`;this.render()}}
  render(){
    if(!this._hass)return;
    const d=this._attrs(), scenes=d.scenes||[], out=d.output||{}, unlocked=this._security(), on=d.enabled===true;
    this.innerHTML=`<style>:host{display:block}.box{padding:15px;border:1px solid #30363d;border-radius:12px;background:#111519;color:#eee;margin-top:12px}.help{padding:10px;border-left:3px solid #e5bf6b;background:#151a1f;font-size:11px;line-height:1.5;margin-bottom:12px}.grid{display:grid;grid-template-columns:2fr 1fr 1fr 2fr;gap:7px}.row{padding:10px;border:1px solid #293039;border-radius:8px;margin-top:8px;display:flex;justify-content:space-between;align-items:center;font-size:12px}.small{font-size:10px;color:#8f99a3}.on{color:#68df9a}.error{color:#ef7777}input,select{box-sizing:border-box;width:100%;background:#0b0d10;color:#eee;border:1px solid #39424c;border-radius:6px;padding:8px;margin-bottom:6px}.btn{padding:8px 10px;background:#171c21;color:#eee;border:1px solid #39424c;border-radius:7px;cursor:pointer;margin:3px 4px 3px 0}.primary{background:#164d70}.danger{border-color:#8b3f45}.chrow{display:grid;grid-template-columns:80px 80px 34px;gap:5px;margin-top:5px}@media(max-width:800px){.grid{grid-template-columns:1fr}}</style>
    <div class="box"><h3>DMX SCENE BANK</h3><div class="help"><b>À quoi ça sert ?</b> Jusqu'à 19 scènes DMX complètes (512 canaux), rappelables depuis Home Assistant. <b>Sortie DMX active</b>, séparée du DMX Monitor receive-only et du Power Manager. Un seul transport de sortie à la fois pour toute la banque.</div>
    <div class="small">Sécurité : <b class="${unlocked?'on':'error'}">${unlocked?'DÉVERROUILLÉE':'VERROUILLÉE'}</b> · Banque : <b class="${on?'on':'error'}">${on?'ARMÉE':'DÉSARMÉE'}</b> · ${scenes.length}/${d.limit||19} scène(s)</div>
    <button class="btn ${on?'primary':''}" id="toggle-bank">${on?'Désarmer la banque':'Armer la banque'}</button>

    <h4 style="margin-top:14px">Sortie</h4>
    <div class="grid">
      <select id="protocol"><option value="sacn" ${out.protocol==='sacn'?'selected':''}>sACN</option><option value="artnet" ${out.protocol==='artnet'?'selected':''}>Art-Net</option><option value="enttec" ${out.protocol==='enttec'?'selected':''}>ENTTEC</option></select>
      <input id="universe" type="number" min="1" value="${out.universe||1}" placeholder="Univers">
      <input id="priority" type="number" min="1" max="200" value="${out.priority||100}" placeholder="Priorité sACN">
      <input id="host" value="${esc(out.host||'')}" placeholder="Destination Art-Net (vide = sACN multicast)">
    </div>
    <input id="enttec-device" value="${esc(out.enttec_device||'')}" placeholder="ENTTEC /dev/…">
    <button class="btn" id="save-output">Enregistrer la config. de sortie</button>

    <h4 style="margin-top:14px">Scènes enregistrées</h4>
    ${scenes.length?scenes.map(s=>`<div class="row"><span><b>${esc(s.name||s.scene_id)}</b> <span class="small">${s.active_channels} canal/aux actifs</span></span><span><button class="btn primary" data-recall="${esc(s.scene_id)}" ${unlocked?'':'disabled'}>RECALL</button><button class="btn" data-edit="${esc(s.scene_id)}">Éditer</button><button class="btn danger" data-del="${esc(s.scene_id)}">Suppr.</button></span></div>`).join(''):'<div class="small">Aucune scène enregistrée.</div>'}

    <h4 style="margin-top:14px">${this._editing?'Éditer la scène « '+esc(this._editing)+' »':'Nouvelle scène'}</h4>
    <input id="scene-id" placeholder="ID de la scène" value="${esc(this._sceneId||'')}" ${this._editing?'disabled':''}>
    <input id="scene-name" placeholder="Nom affiché" value="${esc(this._sceneName||'')}">
    <div id="channels"></div>
    <button class="btn" id="addch">+ Canal</button>
    <div style="margin-top:8px"><button class="btn primary" id="save-scene">Enregistrer la scène</button>${this._editing?'<button class="btn" id="cancel-edit">Annuler</button>':''}</div>
    ${this._msg?`<div class="small" style="margin-top:8px">${esc(this._msg)}</div>`:''}
    ${d.last_error?`<div class="error small" style="margin-top:6px">${esc(d.last_error)}</div>`:''}
    </div>`;

    const paint=()=>{const host=this.querySelector('#channels');host.innerHTML=this._channels.map((c,i)=>`<div class="chrow"><input data-i="${i}" data-k="channel" type="number" min="1" max="512" value="${c.channel}"><input data-i="${i}" data-k="value" type="number" min="0" max="255" value="${c.value}"><button class="btn" data-rm="${i}">×</button></div>`).join('');host.querySelectorAll('input[data-i]').forEach(x=>x.oninput=()=>{const i=+x.dataset.i,k=x.dataset.k;this._channels[i][k]=+x.value});host.querySelectorAll('[data-rm]').forEach(x=>x.onclick=()=>{this._channels.splice(+x.dataset.rm,1);paint()})};
    if(!this._channels.length&&!this._editing)this._channels=[{channel:1,value:255}];
    paint();

    this.querySelector('#toggle-bank')?.addEventListener('click',()=>this._call('dmx_scene_set_enabled',{enabled:!on}));
    this.querySelector('#save-output')?.addEventListener('click',()=>this._call('dmx_scene_configure_output',{protocol:this.querySelector('#protocol').value,universe:+this.querySelector('#universe').value,host:this.querySelector('#host').value.trim(),priority:+this.querySelector('#priority').value,enttec_device:this.querySelector('#enttec-device').value.trim()}));
    this.querySelectorAll('[data-recall]').forEach(b=>b.addEventListener('click',()=>this._call('dmx_scene_recall',{scene_id:b.dataset.recall})));
    this.querySelectorAll('[data-del]').forEach(b=>b.addEventListener('click',()=>this._call('dmx_scene_delete',{scene_id:b.dataset.del})));
    this.querySelectorAll('[data-edit]').forEach(b=>b.addEventListener('click',()=>{
      const s=scenes.find(x=>x.scene_id===b.dataset.edit); if(!s)return;
      this._editing=s.scene_id; this._sceneId=s.scene_id; this._sceneName=s.name;
      // NOTE: the scene bank stores full 512-channel frames but only reports
      // active_channels (a count) in its snapshot, not the actual per-channel
      // values -- editing starts from a blank channel list rather than
      // pretending to know values that were never sent to the frontend.
      this._channels=[{channel:1,value:255}];
      this._msg='Édition : les valeurs précédentes ne sont pas rechargées (non exposées par le backend) — redéfinis les canaux à changer.';
      this.render();
    }));
    this.querySelector('#cancel-edit')?.addEventListener('click',()=>{this._editing=null;this._sceneId='';this._sceneName='';this._channels=[];this.render()});
    this.querySelector('#scene-id')?.addEventListener('input',e=>this._sceneId=e.target.value);
    this.querySelector('#scene-name')?.addEventListener('input',e=>this._sceneName=e.target.value);
    this.querySelector('#addch')?.addEventListener('click',()=>{this._channels.push({channel:Math.min(512,(this._channels.at(-1)?.channel||0)+1),value:255});paint()});
    this.querySelector('#save-scene')?.addEventListener('click',()=>{
      const scene_id=(this._sceneId||'').trim();
      if(!scene_id){this._msg='ID de la scène obligatoire.';this.render();return;}
      const maxCh=Math.max(0,...this._channels.map(c=>c.channel));
      const values=new Array(maxCh).fill(0);
      this._channels.forEach(c=>{if(c.channel>=1&&c.channel<=512)values[c.channel-1]=Math.max(0,Math.min(255,c.value))});
      this._call('dmx_scene_save',{scene_id,name:this._sceneName||scene_id,values});
      this._editing=null;this._sceneId='';this._sceneName='';this._channels=[];
    });
  }
}
snDefine('dmx-scene-bank-panel',DmxSceneBankPanel);

/* ===== gdtf-panel.js ===== */
class GdtfPanel extends HTMLElement {
  constructor(){super();this._patchForm={};}
  set hass(h){this._hass=h;this.render()}
  _attrs(){return Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes('gdtf_library_count'))?.attributes||{}}
  _security(){const c=Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes('security_unlocked'));return c?.state==='true'||c?.state==='on'}
  async _call(service,data){try{const r=await this._hass.callService('dmx_monitor',service,data);this._msg='OK';setTimeout(()=>this.render(),400);setTimeout(()=>this.render(),1500);return r}catch(e){this._msg=`Erreur: ${e?.message||e}`;this.render()}}
  render(){
    if(!this._hass)return;
    const d=this._attrs(), library=d.library||[], patches=d.patches||[], on=d.control_enabled===true, unlocked=this._security();
    const selectedFixture=library.find(f=>f.file===this._patchForm.gdtf_file);
    const modes=selectedFixture?.modes||[];
    this.innerHTML=`<style>:host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}
h2{margin:0}.sub{font-size:11px;color:#8d969f;margin:5px 0 14px}
.help{padding:10px;border-left:3px solid #e5bf6b;background:#151a1f;font-size:11px;line-height:1.5;margin-bottom:14px}
.small{font-size:10px;color:#8f99a3;margin-bottom:8px}.on{color:#68df9a}.error{color:#ef7777}
.section{background:#15181c;border:1px solid #2c3239;border-radius:10px;padding:14px;margin-bottom:14px}
.title{font-weight:700;margin-bottom:8px;color:#eef1f4}
input,select{box-sizing:border-box;width:100%;background:#0b0d10;color:#eee;border:1px solid #343b43;border-radius:6px;padding:8px;margin-bottom:7px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:7px}
.btn{padding:8px 10px;background:#171c21;color:#eee;border:1px solid #39424c;border-radius:7px;cursor:pointer;margin:4px 5px 0 0}
.primary{background:#164d70}.danger{border-color:#8b3f45}
.row{display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px solid #23282e;font-size:12px}
.attr-row{display:grid;grid-template-columns:1fr 2fr 70px;gap:6px;align-items:center;margin-bottom:5px;font-size:11px}
</style>
<h2>GDTF / CONTRÔLE PROJECTEURS</h2><div class="sub">GDTF décrit uniquement le contrôle DMX d'un projecteur ; ce n'est pas de la télémétrie.</div>
<div class="small">Sécurité : <b class="${unlocked?'on':'error'}">${unlocked?'DÉVERROUILLÉE':'VERROUILLÉE'}</b> · Contrôle fixtures : <b class="${on?'on':'error'}">${on?'ARMÉ':'DÉSARMÉ'}</b></div>
<button class="btn ${on?'primary':''}" id="toggle-control">${on?'Désarmer le contrôle fixtures':'Armer le contrôle fixtures'}</button>

<div class="section"><div class="title">IMPORTER UN GDTF</div>
<div class="small">Le fichier .gdtf doit déjà être présent dans /config/show_network_gdtf_inbox.</div>
<input id="import-filename" placeholder="nom_du_fichier.gdtf">
<button class="btn" id="import-btn">Importer</button>
</div>

<div class="section"><div class="title">BIBLIOTHÈQUE (${library.length})</div>
${library.length?library.map(f=>`<div class="row"><span>${esc(f.name)} · ${esc(f.manufacturer)}</span><span class="small">${(f.modes||[]).length} mode(s)</span></div>`).join(''):'<div class="small">Aucun fixture importé.</div>'}
</div>

<div class="section"><div class="title">NOUVEAU PATCH</div>
<div class="grid">
<input id="p-name" placeholder="Nom (ex: Wash FOH 1)">
<select id="p-file">${library.map(f=>`<option value="${esc(f.file)}" ${f.file===this._patchForm.gdtf_file?'selected':''}>${esc(f.name)}</option>`).join('')||'<option value="">Importe un GDTF d\u2019abord</option>'}</select>
<select id="p-mode">${modes.map(m=>`<option value="${esc(m.name)}">${esc(m.name)} (${m.channels?.length||0} ch)</option>`).join('')||'<option value="">—</option>'}</select>
</div>
<div class="grid">
<select id="p-protocol"><option value="sacn">sACN</option><option value="artnet">Art-Net</option></select>
<input id="p-universe" type="number" min="1" value="1" placeholder="Univers">
<input id="p-address" type="number" min="1" max="512" value="1" placeholder="Adresse DMX">
<input id="p-priority" type="number" min="1" max="200" value="100" placeholder="Priorité sACN">
</div>
<input id="p-host" placeholder="Destination Art-Net (si Art-Net)">
<button class="btn primary" id="save-patch">Créer le patch</button>
</div>

<div class="section"><div class="title">PATCHES (${patches.length})</div>
${patches.length?patches.map(p=>`<div class="row" style="display:block"><div style="display:flex;justify-content:space-between"><span><b>${esc(p.name)}</b> <span class="small">U${p.universe}.${p.address} · ${esc(p.protocol)}</span></span><button class="btn danger" data-del-patch="${esc(p.patch_id)}" ${unlocked?'':'disabled'}>Supprimer</button></div>
${Object.entries(p.attributes||{}).map(([attr,info])=>`<div class="attr-row"><span>${esc(attr)}</span><input type="range" min="${info.min}" max="${info.max}" step="0.01" value="${p.values?.[attr]??info.min}" data-patch="${esc(p.patch_id)}" data-attr="${esc(attr)}"><button class="btn" data-set-attr="${esc(p.patch_id)}::${esc(attr)}" ${(unlocked&&on)?'':'disabled'}>Envoyer</button></div>`).join('')||'<div class="small">Aucun attribut (mode inconnu ?)</div>'}
</div>`).join(''):'<div class="small">Aucun patch.</div>'}
</div>
${this._msg?`<div class="small">${esc(this._msg)}</div>`:''}`;

    this.querySelector('#toggle-control')?.addEventListener('click',()=>this._call('set_fixture_control_enabled',{enabled:!on}));
    this.querySelector('#import-btn')?.addEventListener('click',()=>{
      const filename=this.querySelector('#import-filename').value.trim();
      if(!filename){this._msg='Nom de fichier requis.';this.render();return;}
      this._call('gdtf_import',{filename});
    });
    this.querySelector('#p-file')?.addEventListener('change',e=>{this._patchForm.gdtf_file=e.target.value;this.render()});
    this.querySelector('#save-patch')?.addEventListener('click',()=>{
      const name=this.querySelector('#p-name').value.trim();
      const gdtf_file=this.querySelector('#p-file').value;
      const mode=this.querySelector('#p-mode').value;
      if(!name||!gdtf_file||!mode){this._msg='Nom, fixture et mode sont obligatoires.';this.render();return;}
      this._call('fixture_patch_upsert',{
        patch_id:'patch_'+name.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'')+'_'+Date.now().toString(36),
        name,gdtf_file,mode,
        universe:+this.querySelector('#p-universe').value,
        address:+this.querySelector('#p-address').value,
        protocol:this.querySelector('#p-protocol').value,
        host:this.querySelector('#p-host').value.trim(),
        priority:+this.querySelector('#p-priority').value,
      });
    });
    this.querySelectorAll('[data-del-patch]').forEach(b=>b.addEventListener('click',()=>this._call('fixture_patch_remove',{patch_id:b.dataset.delPatch})));
    this.querySelectorAll('[data-set-attr]').forEach(b=>b.addEventListener('click',()=>{
      const [patch_id,attribute]=b.dataset.setAttr.split('::');
      const input=this.querySelector(`input[data-patch="${patch_id}"][data-attr="${attribute}"]`);
      this._call('fixture_set_attribute',{patch_id,attribute,value:parseFloat(input.value)});
    }));
  }
}
snDefine('gdtf-panel',GdtfPanel);

/* ===== qlcplus-panel.js ===== */
class QlcPlusPanel extends HTMLElement {
  set hass(h){this._hass=h;this.render()}
  _attrs(){return Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes('qlcplus_status'))?.attributes||{}}
  _security(){const c=Object.values(this._hass?.states||{}).find(x=>x.entity_id.includes('security_unlocked'));return c?.state==='true'||c?.state==='on'}
  async _call(service,data){try{await this._hass.callService('dmx_monitor',service,data);this._msg='OK';setTimeout(()=>this.render(),400);setTimeout(()=>this.render(),1500)}catch(e){this._msg=`Erreur: ${e?.message||e}`;this.render()}}
  render(){
    if(!this._hass)return;
    const d=this._attrs(), widgets=d.widgets||[], functions=d.functions||[], online=d.online===true, unlocked=this._security();
    this.innerHTML=`<style>:host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}
h2{margin:0}.sub{font-size:11px;color:#8d969f;margin:5px 0 14px}
.help{padding:10px;border-left:3px solid #e5bf6b;background:#151a1f;font-size:11px;line-height:1.5;margin-bottom:14px}
.small{font-size:10px;color:#8f99a3;margin-bottom:8px}.on{color:#68df9a}.error{color:#ef7777}
.section{background:#15181c;border:1px solid #2c3239;border-radius:10px;padding:14px;margin-bottom:14px}
.title{font-weight:700;margin-bottom:8px;color:#eef1f4}
input,select{box-sizing:border-box;width:100%;background:#0b0d10;color:#eee;border:1px solid #343b43;border-radius:6px;padding:8px;margin-bottom:7px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:7px}
.btn{padding:8px 10px;background:#171c21;color:#eee;border:1px solid #39424c;border-radius:7px;cursor:pointer;margin:4px 5px 0 0}
.primary{background:#164d70}
.row{display:flex;justify-content:space-between;gap:10px;padding:6px 0;border-bottom:1px solid #23282e;font-size:12px}
</style>
<h2>QLC+ VIRTUAL CONSOLE</h2><div class="sub">Découverte des widgets/fonctions et pilotage direct via l'API WebSocket QLC+ (port 9999 par défaut).</div>
<div class="small">Connexion : <b class="${online?'on':'error'}">${online?'EN LIGNE':'HORS LIGNE'}</b> · Sécurité : <b class="${unlocked?'on':'error'}">${unlocked?'DÉVERROUILLÉE':'VERROUILLÉE'}</b></div>
${d.last_error?`<div class="help">${esc(d.last_error)}</div>`:''}
<button class="btn" id="refresh">Rafraîchir la découverte</button>

<div class="section"><div class="title">WIDGETS VIRTUAL CONSOLE (${widgets.length})</div>
${widgets.length?widgets.map(w=>`<div class="row"><span>${esc(w.name)} <span class="small">#${esc(w.widget_id)} · ${esc(w.type||'?')}</span></span><span>${esc(w.status??'—')}</span></div>`).join(''):'<div class="small">Aucun widget découvert.</div>'}
<div class="grid" style="margin-top:10px"><select id="w-id">${widgets.map(w=>`<option value="${esc(w.widget_id)}">${esc(w.name)} (#${esc(w.widget_id)})</option>`).join('')||'<option value="">Aucun widget</option>'}</select><input id="w-value" type="number" min="0" max="255" placeholder="Valeur (0-255)"></div>
<button class="btn primary" id="set-value" ${(unlocked&&widgets.length)?'':'disabled'}>Définir la valeur</button>
</div>

<div class="section"><div class="title">CUE LIST / FRAME</div>
<div class="grid"><input id="cl-id" placeholder="ID widget Cue List/Frame"><select id="cl-op"><option value="PLAY">PLAY</option><option value="NEXT">NEXT</option><option value="PREV">PREV</option><option value="STEP">STEP</option><option value="NEXT_PG">NEXT_PG (frame)</option><option value="PREV_PG">PREV_PG (frame)</option></select><input id="cl-step" type="number" min="0" placeholder="Step (si STEP)"></div>
<button class="btn primary" id="cl-send" ${unlocked?'':'disabled'}>Envoyer</button>
</div>

<div class="section"><div class="title">FONCTIONS (${functions.length})</div>
${functions.length?functions.map(f=>`<div class="row"><span>${esc(f.name)} <span class="small">#${esc(f.function_id)}</span></span><span>${esc(f.status||'—')}</span></div>`).join(''):'<div class="small">Aucune fonction découverte.</div>'}
<div class="grid" style="margin-top:10px"><select id="f-id">${functions.map(f=>`<option value="${esc(f.function_id)}">${esc(f.name)}</option>`).join('')||'<option value="">Aucune fonction</option>'}</select><select id="f-running"><option value="1">Lancer</option><option value="0">Arrêter</option></select></div>
<button class="btn primary" id="f-set" ${(unlocked&&functions.length)?'':'disabled'}>Appliquer</button>
</div>
${this._msg?`<div class="small">${esc(this._msg)}</div>`:''}`;

    this.querySelector('#refresh')?.addEventListener('click',()=>this._call('qlcplus_refresh',{}));
    this.querySelector('#set-value')?.addEventListener('click',()=>{
      const widget_id=this.querySelector('#w-id')?.value;
      const value=this.querySelector('#w-value')?.value;
      if(!widget_id||value==='')return;
      this._call('qlcplus_set_widget_value',{widget_id,value:+value});
    });
    this.querySelector('#cl-send')?.addEventListener('click',()=>{
      const widget_id=this.querySelector('#cl-id')?.value.trim();
      const operation=this.querySelector('#cl-op')?.value;
      if(!widget_id){this._msg='ID widget obligatoire.';this.render();return;}
      if(operation==='NEXT_PG'||operation==='PREV_PG'){this._call('qlcplus_frame_control',{widget_id,operation});return;}
      const step=this.querySelector('#cl-step')?.value;
      this._call('qlcplus_cue_list_control',{widget_id,operation,step:step?+step:undefined});
    });
    this.querySelector('#f-set')?.addEventListener('click',()=>{
      const function_id=this.querySelector('#f-id')?.value;
      if(!function_id)return;
      this._call('qlcplus_set_function_status',{function_id,running:this.querySelector('#f-running').value==='1'});
    });
  }
}
snDefine('qlcplus-panel',QlcPlusPanel);

/* ===== show-network-archive-panel.js ===== */
class ShowNetworkArchivePanel extends HTMLElement {
  setConfig(c){this._config=c||{};}
  set hass(h){this._hass=h; this.render();}
  async _call(service,data={}){this._msg='Action en cours…';this.render();try{await this._hass.callService('dmx_monitor',service,data);this._msg='Action exécutée';}catch(e){this._msg=`Erreur: ${e?.message||e}`;}this.render();}
  render(){
    const h=this._hass; if(!h)return;
    const st=Object.values(h.states||{}).find(x=>x.attributes&&('recent_events' in x.attributes)&&('configured_destination' in x.attributes))||h.states?.['sensor.dmx_monitor_journal_archive']; const a=st?.attributes||{};const events=(a.recent_events||[]).slice().reverse().slice(0,30);
    const cb=a.configuration_backups||{},dg=a.diagnostics||{},fr=a.flight_recorder||{};const incident=fr.last_incident||null;const sev=fr.severity_counts||{};
    const notif=h.states?.['sensor.dmx_monitor_notification']?.attributes||{};
    this.innerHTML=`<style>:host{display:block}.box{padding:15px;border:1px solid #30363d;border-radius:14px;background:#111519;color:#eee}.row{display:flex;justify-content:space-between;gap:15px;padding:8px 0;border-bottom:1px solid #252b31;font-size:12px}.btn{margin:10px 6px 0 0;padding:9px 12px;border:1px solid #39414a;background:#181d22;color:#eee;border-radius:8px;cursor:pointer}.danger{border-color:#8b3f45}.path{font-family:ui-monospace,monospace;word-break:break-all}.small{font-size:11px;color:#929ba4}.event{padding:8px 0;border-top:1px solid #252b31;font-size:11px}.kind{display:inline-block;min-width:70px;color:#68df9a}.ts{color:#929ba4;font-family:ui-monospace,monospace}.msg{margin-top:10px;padding:8px;border:1px solid #39414a;border-radius:8px}input{box-sizing:border-box;width:100%;background:#0b0d10;color:#eee;border:1px solid #39414a;border-radius:7px;padding:9px;margin-top:8px}</style><div class="box"><b>JOURNAL · BACKUPS</b><div class="row"><span>Destination journal</span><span class="path">${esc(a.configured_destination||a.destination||'—')}</span></div><input id="dest-path" placeholder="Nouvelle destination (ex: show_network_archive)"><button class="btn" id="set-dest">Changer la destination</button><div class="row"><span>Fichiers journal</span><span>${a.files??'—'}</span></div><button class="btn" id="backup">Backup journal</button><button class="btn" id="export">Exporter journal</button><h4>Configuration Show Network</h4><div class="row"><span>Fichiers persistants</span><span>${cb.files_present??0}/${cb.files_known??0}</span></div><div class="row"><span>Dernière sauvegarde</span><span class="path">${esc(cb.last_backup_success||'—')}</span></div><div class="row"><span>Dernière restauration</span><span class="path">${esc(cb.last_restore_success||'—')}</span></div><div class="small">Les ZIP portables n'incluent pas les mots de passe/secrets. Une restauration crée d'abord un point de retour puis recharge l'intégration.</div><button class="btn" id="config-backup">Sauvegarder la configuration</button><input id="restore-path" placeholder="/config/show_network_backups/show_network_config_....zip"><button class="btn danger" id="restore">Restaurer ce ZIP</button><h4>Notifications Show Network</h4><div class="row"><span>État</span><span class="${notif.enabled?'ok':''}">${notif.enabled?'ACTIVES':'INACTIVES'}</span><span>Cible configurée</span><span>${notif.target_configured?'OUI':'NON'}</span></div><div class="grid" style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px"><select id="notif-enabled"><option value="1">Activer</option><option value="0">Désactiver</option></select><input id="notif-target" placeholder="Cible (persistent, mobile_app_xxx…)"><select id="notif-mode"><option value="both">both</option><option value="on_only">on_only</option><option value="off_only">off_only</option></select></div><button class="btn" id="set-notif">Enregistrer les notifications</button><h4>Diagnostics support</h4><div class="row"><span>Dernier bundle</span><span class="path">${esc(dg.last_path||'—')}</span></div><button class="btn" id="diag">Créer bundle diagnostics</button>${this._msg?`<div class="msg">${esc(this._msg)}</div>`:''}<h4>FLIGHT RECORDER · QUE S'EST-IL PASSÉ ?</h4><div class="small">Corrélation temporelle uniquement : Show Network affiche les faits observés ensemble, sans inventer de cause.</div><div class="row"><span>Fenêtre analysée</span><b>± ${fr.window_s??20} s</b><span>Événements</span><b>${fr.events_total??0}</b></div><div class="row"><span>Erreurs</span><b>${sev.error??0}</b><span>Avertissements</span><b>${sev.warning??0}</b><span>Récupérations</span><b>${sev.recovery??0}</b></div>${incident?`<div class="msg"><b>Dernier incident : ${esc(incident.kind||'—')} · ${esc(incident.event||'—')}</b><div class="small ts">${esc(incident.ts||'—')}</div><div class="small">${incident.related_count??0} événement(s) observé(s) dans ±${incident.window_s??20}s · familles : ${esc((incident.related_kinds||[]).join(', ')||'—')}</div><div class="small">Équipements reliés par preuve : ${esc((incident.related_device_ids||[]).join(', ')||'aucun')}</div>${(incident.related_events||[]).map(e=>`<div class="event"><span class="ts">${esc(e.ts||'—')}</span> · <span class="kind">${esc(e.kind||'—')}</span> <b>${esc(e.event||'—')}</b>${e.data&&Object.keys(e.data).length?`<div class="small path">${esc(JSON.stringify(e.data))}</div>`:''}</div>`).join('')}</div>`:'<div class="small">Aucun incident/avertissement dans les événements actuellement en mémoire.</div>'}<h4>Timeline récente</h4>${(fr.timeline||[]).slice().reverse().slice(0,50).map(e=>`<div class="event"><span class="ts">${esc(e.ts||'—')}</span> · <span class="kind">${esc(e.kind||'general')}</span> <b>${esc(e.event||'—')}</b> <span class="small">[${esc(e.severity||'info')}]</span></div>`).join('')}<h4>Événements récents</h4>${events.length?events.map(e=>`<div class="event"><span class="ts">${esc(e.ts||'—')}</span> · <span class="kind">${esc(e.kind||'general')}</span> <b>${esc(e.event||'—')}</b>${e.data&&Object.keys(e.data).length?`<div class="small path">${esc(JSON.stringify(e.data))}</div>`:''}</div>`).join(''):'<div class="small">Aucun événement en mémoire depuis le démarrage de cette version.</div>'}</div>`;
    this.querySelector('#backup')?.addEventListener('click',()=>this._call('archive_backup',{}));
    this.querySelector('#set-dest')?.addEventListener('click',()=>{const destination=this.querySelector('#dest-path')?.value?.trim();if(destination)this._call('archive_set_destination',{destination});else{this._msg='Indique une destination.';this.render();}});
    this.querySelector('#set-notif')?.addEventListener('click',()=>{this._call('set_notification_config',{enabled:this.querySelector('#notif-enabled').value==='1',target:this.querySelector('#notif-target').value.trim()||'persistent',mode:this.querySelector('#notif-mode').value});});
    this.querySelector('#export')?.addEventListener('click',()=>this._call('archive_export',{}));
    this.querySelector('#config-backup')?.addEventListener('click',()=>this._call('config_backup_create',{reason:'ui'}));
    this.querySelector('#diag')?.addEventListener('click',()=>this._call('diagnostics_export',{}));
    this.querySelector('#restore')?.addEventListener('click',()=>{const source=this.querySelector('#restore-path')?.value?.trim();if(source)this._call('config_backup_restore',{source});else{this._msg='Indique le chemin du ZIP de configuration.';this.render();}});
  }
}
snDefine('show-network-archive-panel',ShowNetworkArchivePanel);


/* ===== show-network-dashboard.js ===== */
class ShowNetworkDashboard extends HTMLElement {
  setConfig(c){}
  set hass(h){this._hass=h; const c=h?.states?.["sensor.dmx_monitor_network_interfaces_up"]; const n=this.querySelector("#network-health"); if(n) n.textContent=c?.state ?? "—";}
  connectedCallback(){this.innerHTML=`
  <style>
  :host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;min-height:100vh}
  header{padding:18px 22px;background:#15181c;border-bottom:1px solid #2b3036}
  h1{margin:0;font-size:23px}.sub{color:#8d969f;font-size:11px;margin-top:4px}
  main{padding:16px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
  .card{background:#15181c;border:1px solid #2c3239;border-radius:10px;padding:15px}
  .label{font-size:11px;color:#8d969f}.value{font-size:24px;font-weight:700;margin-top:6px}
  .ok{color:#65dc99}.warn{color:#e6bd67}.off{color:#8d969f}.err{color:#ed6e6e}
  .wide{margin-top:12px}.line{display:flex;justify-content:space-between;padding:10px 12px;border-bottom:1px solid #282d33;font-size:12px}
  @media(max-width:900px){.grid{grid-template-columns:repeat(2,1fr)}}
  </style>
  <header><h1>SHOW NETWORK HEALTH</h1><div class="sub">LIGHT · AUDIO · CONTROL · NETWORK · MA REMOTE</div></header>
  <main>
   <section class="grid">
    <div class="card"><div class="label">LIGHT</div><div class="value off">—</div><div class="label">DMX / sACN / Art-Net</div></div>
    <div class="card"><div class="label">AUDIO</div><div class="value off">—</div><div class="label">Dante / AVB / AES67 / ST2110</div></div>
    <div class="card"><div class="label">NETWORK</div><div class="value off" id="network-health">—</div><div class="label">IGMP / LLDP / QoS / GigaCore</div></div>
    <div class="card"><div class="label">MA</div><div class="value off">—</div><div class="label">MA-Net3 / Web Remote</div></div>
   </section>
   <section class="card wide">
    <div class="label">DIAGNOSTIC</div>
    <div class="line"><span>Telemetry</span><span class="off">Waiting for live data…</span></div>
    <div class="line"><span>Mode</span><span class="ok">READ ONLY</span></div>
    <div class="line"><span>MA session join</span><span class="ok">DISABLED</span></div>
    <div class="line"><span>DMX / sACN / Art-Net output</span><span class="ok">DISABLED</span></div>
    <div class="line"><span>OSC output</span><span class="ok">DISABLED</span></div>
   </section>
  </main>`}
}
snDefine("show-network-dashboard",ShowNetworkDashboard);


/* ===== show-network-ha-builder-panel.js ===== */
class ShowNetworkHABuilderPanel extends HTMLElement {
  setConfig(c){this._config=c||{};}
  set hass(h){this._hass=h; this.render();}
  render(){
    const h=this._hass; if(!h)return;
    const state=h.states?.['sensor.dmx_monitor_ha_builder'];
    const items=state?.attributes?.items||[];
    const call=(service,data={})=>h.callService?.('dmx_monitor',service,data);
    this.innerHTML=`<style>:host{display:block;font-family:system-ui}.box{padding:16px;border:1px solid #30363d;border-radius:14px;background:#111519;color:#eee}.head{display:flex;justify-content:space-between;gap:12px;align-items:center}.title{font-weight:800;letter-spacing:.04em}.small{font-size:11px;color:#929ba4}.grid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:8px;margin-top:12px}@media(max-width:800px){.grid{grid-template-columns:1fr}}input,select{width:100%;box-sizing:border-box;padding:9px;border-radius:8px;border:1px solid #39414a;background:#181d22;color:#eee}.btn{margin-top:10px;padding:9px 12px;border:1px solid #39414a;background:#181d22;color:#eee;border-radius:8px;cursor:pointer}.item{margin-top:8px;padding:10px;border:1px solid #252b31;border-radius:9px}.remove{float:right}.ok{color:#68df9a}</style><div class="box"><div class="head"><div><div class="title">HA BUILDER</div><div class="small">Crée des entités Show Network correctement typées, sans YAML.</div></div><div class="ok">${items.length} élément(s)</div></div><div class="grid"><input id="name" placeholder="Nom : Secours audio"><select id="type"><option value="switch">Switch</option><option value="sensor">Capteur</option><option value="binary_sensor">Binary sensor</option><option value="button">Bouton</option><option value="number">Nombre</option></select><input id="area" placeholder="Zone / Area"></div><button class="btn" id="create">Créer dans Home Assistant</button><div>${items.map(x=>`<div class="item"><button class="btn remove" data-id="${x.item_id}">Supprimer</button><b>${x.name}</b> · ${x.entity_type}<div class="small">${x.item_id}${x.area?` · ${x.area}`:''}</div>${x.entity_type!=='button'?`<div style="margin-top:6px;display:flex;gap:6px"><input data-state-field="${x.item_id}" placeholder="${x.entity_type==='switch'||x.entity_type==='binary_sensor'?'on / off':'valeur'}" style="flex:1"><button class="btn" data-set-state="${x.item_id}" style="margin:0">Définir l'état</button></div>`:''}</div>`).join('')}</div></div>`;
    this.querySelector('#create')?.addEventListener('click',async()=>{const name=this.querySelector('#name').value.trim();if(!name)return;await call('ha_builder_create',{name,entity_type:this.querySelector('#type').value,area:this.querySelector('#area').value.trim()});});
    this.querySelectorAll('.remove').forEach(b=>b.addEventListener('click',()=>call('ha_builder_remove',{item_id:b.dataset.id})));
    this.querySelectorAll('[data-set-state]').forEach(b=>b.addEventListener('click',()=>{const f=this.querySelector(`[data-state-field="${b.dataset.setState}"]`);const v=f?.value?.trim();if(!v)return;call('ha_builder_set_state',{item_id:b.dataset.setState,state:v});}));
  }
}
snDefine('show-network-ha-builder-panel',ShowNetworkHABuilderPanel);


/* ===== show-network-notification-panel.js ===== */
class ShowNetworkNotificationPanel extends HTMLElement {
  setConfig(c){this._config=c||{};}
  set hass(h){this._hass=h; const st=h?.states?.['sensor.dmx_monitor_notification']; const a=st?.attributes||{}; this.innerHTML=`<style>:host{display:block}.box{padding:15px;border:1px solid #30363d;border-radius:14px;background:#111519;color:#eee}.row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #252b31;font-size:12px}.small{font-size:11px;color:#929ba4}.ok{color:#68df9a}.warn{color:#e5bf6b}</style><div class="box"><b>NOTIFICATIONS HA</b><div class="row"><span>État</span><span class="${a.enabled?'ok':'warn'}">${a.enabled?'ACTIF':'INACTIF'}</span></div><div class="row"><span>Mode</span><span>${a.mode||'—'}</span></div><div class="row"><span>Cible</span><span>${a.target_configured?'Configurée':'Non configurée'}</span></div><div class="small" style="margin-top:8px">Les alertes peuvent apparaître dans l'application HA via notification persistante et/ou un service notify mobile.</div></div>`;}
}
snDefine('show-network-notification-panel',ShowNetworkNotificationPanel);


/* ===== show-network-pro-dashboard.js ===== */
class ShowNetworkProDashboard extends HTMLElement {
  constructor(){super();this._view='pro';this._entityMap={};this._registryLoading=false;this._notice='';this._securityOverride=null;this._securityDialog=null;this._securityDraft={password:'',current:''};this._uiDetails={};this._uiScroll={};this._pendingHass=false;this._videoIp=null;this._videoIpLoading=false;this._videoIpLastFetch=0;this._videoPreviewKey=null;this._videoPreviewEntryId=null;this._focusOutHandler=()=>{if(this._pendingHass){this._pendingHass=false;setTimeout(()=>{if(!this.matches(':focus-within')&&!this._securityDialog)this.render()},0)}};}
  setConfig(c){this._config=c||{}; this.render();}
  set hass(h){this._hass=h; this._ensureRegistry(); if(this._view==='module:video')this._loadVideoIp(); if(this.matches?.(':focus-within')||this._securityDialog){this._pendingHass=true;return;} if(this._raf)return; const run=()=>{this._raf=null;if(this._view.startsWith('module:')){const key=this._view.slice(7);this.querySelectorAll('#module-content > *').forEach(el=>{if(el.matches?.(':focus-within'))return;const open=snCaptureDetails(el),top=el.scrollTop;try{el.hass=this._hass}catch(e){}snRestoreDetails(el,open);el.scrollTop=top;});}else{this.render();}}; this._raf=setTimeout(run,750);}
  connectedCallback(){window.addEventListener('show-network-open-module',this._brandNav||(this._brandNav=(e)=>{const m=e.detail?.module;if(m)this._setView(`module:${m}`);}));this.addEventListener('focusout',this._focusOutHandler);this._ensureRegistry();this.render();}
  disconnectedCallback(){this.removeEventListener('focusout',this._focusOutHandler);if(this._raf){clearTimeout(this._raf);this._raf=null;}}
  async _ensureRegistry(){
    if(!this._hass?.connection || this._registryLoading || Object.keys(this._entityMap).length)return;
    this._registryLoading=true;
    try{
      const rows=await this._hass.connection.sendMessagePromise({type:'config/entity_registry/list'});
      for(const row of rows||[]){if(row.platform==='dmx_monitor' && row.unique_id)this._entityMap[row.unique_id]=row.entity_id;}
    }catch(e){console.warn('Show Network: entity registry unavailable',e);}
    finally{this._registryLoading=false;this.render();}
  }
  _entityId(unique,fallback){return this._entityMap[unique]||fallback;}
  _state(unique,fallback){const id=this._entityId(unique,fallback);return this._hass?.states?.[id];}
  _value(unique,fallback='—',fallbackId){const st=this._state(unique,fallbackId);return st?.state ?? fallback;}
  _truthy(v){return ['true','on','1','yes'].includes(String(v??'').toLowerCase());}
  async _loadVideoIp(force=false){
    if(!this._hass?.connection||this._videoIpLoading||this._videoPreviewKey)return;const now=Date.now();if(!force&&now-this._videoIpLastFetch<5000)return;this._videoIpLoading=true;
    try{this._videoIp=await this._hass.connection.sendMessagePromise({type:'dmx_monitor/video_ip_supervision'});this._videoIpLastFetch=Date.now();}
    catch(e){this._videoIp={mode:'supervision_only',entities_created:0,endpoint_count:0,online_count:0,protocols:{},endpoints:[],error:String(e?.message||e)}}
    finally{this._videoIpLoading=false;if(this._view==='module:video'&&!this.matches?.(':focus-within'))this.render();}
  }
  _setView(view){this._uiDetails[this._view]=snCaptureDetails(this);this._uiScroll[this._view]=this.scrollTop;this._view=view;this._notice='';this._skipCapture=true;this.render();if(view==='module:video')this._loadVideoIp(true);}
  _openIntegrationConfig(){window.location.assign('/config/integrations/integration/dmx_monitor');}
  async _call(service,data={}){
    try{await this._hass?.callService?.('dmx_monitor',service,data);this._notice='Action exécutée';this.render();return true;}
    catch(e){this._notice=`Erreur: ${e?.message||e}`;this.render();return false;}
  }
  _securityState(){
    const actual={configured:this._truthy(this._value('security_configured','false')),unlocked:this._truthy(this._value('security_unlocked','false')),remaining:this._value('security_unlock_remaining_s','0')};
    return this._securityOverride?{...actual,...this._securityOverride}:actual;
  }
  _securityHtml(){
    const sec=this._securityState(),dlg=this._securityDialog,d=this._securityDraft||{password:'',current:''};
    const form=dlg?`<div class="notice"><b>${dlg==='unlock'?'Déverrouiller':dlg==='change'?'Changer le mot de passe':'Configurer le mot de passe'}</b>${dlg==='change'?`<input class="sec-input" id="sec-current" type="password" autocomplete="current-password" placeholder="Mot de passe actuel" value="${esc(d.current||'')}">`:''}<input class="sec-input" id="sec-password" type="password" autocomplete="${dlg==='unlock'?'current-password':'new-password'}" placeholder="Mot de passe Show Network (8 caractères minimum)" value="${esc(d.password||'')}"><div class="security-actions"><button class="btn primary" id="sec-submit">Valider</button><button class="btn" id="sec-cancel">Annuler</button></div></div>`:'';
    return `<div class="card security"><div class="title">SÉCURITÉ COMMANDES ACTIVES</div><div class="big ${sec.unlocked?'ok':sec.configured?'warning':'critical'}">${sec.unlocked?'DÉVERROUILLÉ':sec.configured?'CONFIGURÉ — VERROUILLÉ':'NON CONFIGURÉ'}</div><div class="muted">${sec.unlocked?`Encore ${sec.remaining} s`:'OSC OUT, Light Sync, Projector Control et Power Manager restent bloqués.'}</div><div class="security-actions">${!sec.configured?'<button class="btn" id="setpwd">Configurer mot de passe</button>':'<button class="btn" id="unlock">Déverrouiller</button>'}${sec.configured?'<button class="btn" id="changepwd">Changer mot de passe</button><button class="btn" id="lock">Verrouiller</button>':''}</div>${form}</div>`;
  }
  _wireSecurity(){
    this.querySelector('#setpwd')?.addEventListener('click',()=>{this._securityDraft={password:'',current:''};this._securityDialog='set';this.render()});
    this.querySelector('#unlock')?.addEventListener('click',()=>{this._securityDraft={password:'',current:''};this._securityDialog='unlock';this.render()});
    this.querySelector('#changepwd')?.addEventListener('click',()=>{this._securityDraft={password:'',current:''};this._securityDialog='change';this.render()});
    this.querySelector('#sec-password')?.addEventListener('input',e=>{this._securityDraft.password=e.target.value});this.querySelector('#sec-current')?.addEventListener('input',e=>{this._securityDraft.current=e.target.value});
    this.querySelector('#sec-cancel')?.addEventListener('click',()=>{this._securityDraft={password:'',current:''};this._securityDialog=null;this.render()});
    this.querySelector('#sec-submit')?.addEventListener('click',async()=>{const p=this.querySelector('#sec-password')?.value||'',current=this.querySelector('#sec-current')?.value||'';if(!p){this._notice='Mot de passe requis';this.render();return;}if(this._securityDialog!=='unlock'&&p.length<8){this._notice='Erreur: le mot de passe doit contenir au moins 8 caractères';this.render();return;}let ok=false;if(this._securityDialog==='unlock')ok=await this._call('unlock_security',{password:p});else ok=await this._call('set_security_password',{password:p,...(this._securityDialog==='change'?{current_password:current}:{})});if(ok){if(this._securityDialog==='unlock'){this._securityOverride={configured:true,unlocked:true,remaining:this._value('security_unlock_remaining_s','1800')};this._notice='Commandes actives déverrouillées.';}else this._securityOverride={configured:true,unlocked:false,remaining:'0'};this._securityDraft={password:'',current:''};this._securityDialog=null;this.render();}});
    this.querySelector('#lock')?.addEventListener('click',async()=>{if(await this._call('lock_security',{})){this._securityOverride={configured:true,unlocked:false,remaining:'0'};this._notice='Commandes actives verrouillées.';this.render();}});
  }
  _shell(content){return `<style>
:host{display:block;background:#0a0c0f;color:#eef1f4;font-family:Inter,system-ui,sans-serif;min-height:100vh}.wrap{padding:18px;max-width:1500px;margin:auto}.top{display:flex;justify-content:space-between;align-items:center;padding:16px 18px;border:1px solid #293039;background:#12161a;border-radius:12px}.brand{font-size:20px;font-weight:800;letter-spacing:.06em}.brand-logo{height:54px;max-width:360px;object-fit:contain;object-position:left center}.muted{color:#8f99a3;font-size:11px}.badge{padding:7px 10px;border-radius:999px;border:1px solid #343b43;font-size:11px}.grid{display:grid;grid-template-columns:1.4fr 1fr 1fr;gap:12px;margin-top:12px}.card{background:#12161a;border:1px solid #293039;border-radius:12px;padding:15px}.title{font-size:11px;color:#8f99a3;letter-spacing:.08em}.big{font-size:34px;font-weight:800;margin:6px 0}.ok{color:#68df9a}.warning{color:#e5bf6b}.critical{color:#ef7777}.off{color:#8f99a3}.row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #22282e;font-size:12px}.row:last-child{border:0}.topology{height:260px;display:flex;align-items:center;justify-content:center;gap:16px}.node{border:1px solid #39424c;border-radius:10px;padding:12px;text-align:center;background:#171c21;min-width:105px}.arrow{color:#68737d}.footer,.security-actions,.module-nav{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap}.btn{background:#171c21;border:1px solid #39424c;border-radius:8px;padding:9px 12px;color:#eee;cursor:pointer}.btn:hover{background:#20262c}.btn.primary{background:#164d70;border-color:#2586c8}.notice{margin-top:12px;padding:10px 12px;border:1px solid #39424c;border-radius:8px;background:#151a1f;font-size:12px}.back{margin-bottom:12px}.classic-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.module-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px;margin-top:12px}.section-head{margin-top:22px;padding-bottom:6px;border-bottom:1px solid #293039}.section-title{font-size:14px;font-weight:800;letter-spacing:.04em}.config-guide{margin-top:12px;padding:14px;border:1px solid #31536a;border-radius:12px;background:#101b22}.config-steps{display:flex;gap:7px;flex-wrap:wrap;margin:9px 0}.config-steps span{padding:6px 9px;border-radius:999px;background:#172630;border:1px solid #31536a;font-size:11px}.module{cursor:pointer;min-height:90px}.module:hover{border-color:#4e6576}.module .sn-module-title{font-weight:800;font-size:15px;color:#eef1f4}.module .desc{color:#8f99a3;font-size:11px;margin-top:6px;line-height:1.4}.panel-stack{display:grid;gap:12px;margin-top:12px}.entity-table{width:100%;border-collapse:collapse}.entity-table td,.entity-table th{padding:8px;border-bottom:1px solid #252c32;text-align:left;font-size:11px}.entity-table th{color:#8f99a3}.timeline-item{padding:11px 0;border-bottom:1px solid #252b31}.timeline-item:last-child{border:0}.security{margin-top:12px}.sec-input{box-sizing:border-box;width:100%;margin-top:8px;background:#0b0d10;color:#eee;border:1px solid #39424c;border-radius:7px;padding:9px}@media(max-width:900px){.grid,.classic-grid{grid-template-columns:1fr}.wrap{padding:10px}.topology{height:190px}}
</style><div class="wrap">${content}${this._notice?`<div class="notice">${this._notice}</div>`:''}</div>`;}
  _renderPro(){
    const cap=this._value('network_capacity_utilization','—','sensor.dmx_monitor_network_capacity_utilization');
    const nodes=this._value('topology_nodes','—','sensor.dmx_monitor_topology_nodes');
    const links=this._value('topology_links','—','sensor.dmx_monitor_topology_links');
    const archive=this._state('journal_archive','sensor.dmx_monitor_journal_archive')?.attributes||{};
    const cfg=this._state('show_network_config','sensor.dmx_monitor_show_network_config')?.attributes||{};
    const dmx=this._state('dmx_universes','sensor.dmx_monitor_dmx_universes');
    const dmxRows=dmx?.attributes?.universes||[];
    const rx=this._state('protocol_rx_diagnostics','sensor.dmx_monitor_protocol_rx_diagnostics')?.attributes||{};
    const drx=rx.dmx||{}, maRx=rx.ma_net3||{};
    const sacn=drx.protocols?.SACN||{}, art=drx.protocols?.ARTNET||{};
    const enttec=Object.values(this._hass?.states||{}).find(s=>s.entity_id.includes('enttec')&&s.entity_id.startsWith('switch.'));
    const discovery=this._state('discovery_status','sensor.dmx_monitor_discovery_status')?.attributes||{};
    const pct=parseFloat(cap); const status=Number.isFinite(pct)?(pct>=90?'critical':pct>=75?'warning':'ok'):'off';
    const card=(title,value,sub,rows='',go='')=>`<div class="card ${go?'module':''}" ${go?`data-go="${go}"`:''}><div class="title">${title}</div><div class="big">${value}</div><div class="muted">${sub}</div>${rows}</div>`;
    const content=`<div class="top"><div><img class="brand-logo" src="/api/dmx_monitor/static/assets/show-network-logo.png" alt="Show Network"><div class="muted">COCKPIT LIVE · LIGHT · MA · AUDIO · CONTROL · DISCOVERY · UI ${SHOW_NETWORK_FRONTEND_VERSION}/${SHOW_NETWORK_FRONTEND_BUILD}</div></div><div class="badge ${status}">CAPACITY ${cap}%</div></div>
<div class="module-grid">
${card('DMX NETWORK',dmxRows.length,`${(sacn.packets_received??0)+(art.packets_received??0)} paquets RX`, `<div class="row"><span>sACN RX / parsed</span><span>${sacn.packets_received??0} / ${sacn.packets_parsed??0}</span></div><div class="row"><span>Art-Net RX / parsed</span><span>${art.packets_received??0} / ${art.packets_parsed??0}</span></div><div class="row"><span>Univers live</span><span>${dmxRows.filter(x=>Number(x.packet_rate||0)>0).length}</span></div><div class="row"><span>État sACN / Art-Net</span><span class="${sacn.state==='listening'&&art.state==='listening'?'ok':'warn'}">${esc(sacn.state||'—')} / ${esc(art.state||'—')}</span></div><div class="row"><span>Reconnexions sACN / Art-Net</span><span>${sacn.restarts??0} / ${art.restarts??0}</span></div>${(sacn.last_error||art.last_error)?`<div class="notice">${sacn.last_error?'sACN: '+esc(sacn.last_error):''}${sacn.last_error&&art.last_error?' · ':''}${art.last_error?'Art-Net: '+esc(art.last_error):''}</div>`:''}`,'dmx') }
${(()=>{const ot=this._state('ontime_status','sensor.dmx_monitor_ontime_status');const od=ot?.attributes||{};if(!od||Object.keys(od).length===0)return '';
  const fmtMs=(ms)=>{if(ms==null)return '—';const s=Math.round(Math.abs(ms)/1000);const m=Math.floor(s/60);const ss=s%60;return `${ms<0?'-':''}${m}:${String(ss).padStart(2,'0')}`;};
  const online=od.online===true;
  return card('ONTIME',od.timer_playback?od.timer_playback.toUpperCase():(online?'—':'HORS LIGNE'),`Segment ${od.rundown_selected_index!=null?od.rundown_selected_index+1:'—'} / ${od.rundown_num_events??'—'}`,
    `<div class="row"><span>État</span><span class="${online?'ok':'warn'}">${online?'EN LIGNE':'HORS LIGNE'}</span></div><div class="row"><span>Temps restant</span><span>${fmtMs(od.timer_current_ms)}</span></div><div class="row"><span>Décalage planning</span><span class="${(od.offset_absolute_ms||0)<0?'warn':'ok'}">${fmtMs(od.offset_absolute_ms)} (${esc(od.offset_mode||'—')})</span></div><div class="row"><span>Message actif</span><span>${od.message_timer_visible?esc(od.message_timer_text||'—'):'—'}</span></div>${od.last_error?`<div class="notice">${esc(od.last_error)}</div>`:''}`
  );
})()}
${(()=>{const us=this._state('ups_total','sensor.dmx_monitor_ups_total'); const ud=us?.attributes||{}; const units=ud.units||[]; if(!units.length)return '';
  const onBattery=ud.on_battery||0, low=ud.battery_low||0;
  return card('ONDULEURS',`${ud.online??0}/${units.length}`,'en ligne',
    units.map(u=>`<div class="row"><span>${esc(u.name||u.model||u.host)}</span><span class="${u.output_source==='battery'?'warn':(u.online?'ok':'warn')}">${u.online?esc((u.output_source||'—').toUpperCase()):'HORS LIGNE'}${u.estimated_charge_remaining_pct!=null?' · '+u.estimated_charge_remaining_pct+'%':''}</span></div>`).join('')
    +((onBattery||low)?`<div class="notice">${onBattery?onBattery+' onduleur(s) sur batterie. ':''}${low?low+' batterie faible/épuisée.':''}</div>`:'')
  );
})()}
${card('DMX IN / ENTTEC',enttec?.state==='on'?'ON':enttec?'OFF':'—',enttec?.attributes?.friendly_name||'Entrée USB', `<div class="row"><span>État</span><span>${enttec?.state||'indisponible'}</span></div>`,'dmx') }
${card('MA-NET3',this._value('ma_live_stations','—'), 'stations live', `<div class="row"><span>Paquets bruts</span><span>${maRx.packets_received??this._value('ma_packets','—')}</span></div><div class="row"><span>Sessions observées</span><span>${this._value('ma_sessions','—')}</span></div><div class="row"><span>Sources brutes</span><span>${(maRx.raw_sources||[]).length}</span></div>`,'ma') }
${card('DANTE / PTP',this._value('dante_sources','—'),'sources Dante', `<div class="row"><span>Dante packets</span><span>${this._value('dante_packets','—')}</span></div><div class="row"><span>PTP packets</span><span>${this._value('ptp_packets','—')}</span></div><div class="row"><span>AES67 SAP</span><span>${this._value('aes67_sap_packets','—')}</span></div>`,'audio') }
${card('DISCOVERY',this._value('devices_total','—'),'équipements inventoriés', `<div class="row"><span>ARP</span><span>${discovery.arp_neighbors??'—'}</span></div><div class="row"><span>mDNS</span><span>${discovery.mdns_services??'—'}</span></div><div class="row"><span>État</span><span>${esc(discovery.state||'—')}</span></div>`,'inventory') }
${card('PROFILS / CONSTRUCTEURS',this._value('vendor_discovery','—'),'services fabricants observés', `<div class="row"><span>Green-GO observés</span><span>${this._value('green_go_devices','—')}</span></div><div class="row"><span>ELC observés</span><span>${this._value('elc_inventory','—')}</span></div><div class="row"><span>Profils switch actifs</span><span>${this._value('switch_profiles','—')}</span></div><div class="row"><span>Catalogue ETC</span><span>${this._value('etc_sensor_catalog','—')}</span></div>`,'brands') }
${card('TOPOLOGY',nodes,'nœuds', `<div class="row"><span>Liens</span><span>${links}</span></div><div class="row"><span>Interfaces UP</span><span>${this._value('network_interfaces_up','—')}</span></div>`,'network') }
${card('JOURNAL',archive.recent_events?.length??0,'événements récents', `<div class="row"><span>Fichiers</span><span>${archive.files??'—'}</span></div><div class="row"><span>Dernier backup</span><span>${archive.last_backup_success??'—'}</span></div>`,'archive') }
</div>${this._securityHtml()}
<div class="footer"><button class="btn primary" id="modules">Modules & configuration</button><button class="btn" id="ha-config">Configuration générale HA</button><button class="btn" id="classic">Vue classique</button><button class="btn" id="timeline">Show Timeline</button><button class="btn" id="archive">Journal & backups</button></div>`;
    this.innerHTML=this._shell(content);this._wireSecurity();
    this.querySelectorAll('[data-go]').forEach(x=>x.addEventListener('click',()=>this._setView(`module:${x.dataset.go}`)));
    this.querySelector('#modules')?.addEventListener('click',()=>this._setView('modules'));
    this.querySelector('#ha-config')?.addEventListener('click',()=>this._openIntegrationConfig());
    this.querySelector('#classic')?.addEventListener('click',()=>this._setView('classic'));
    this.querySelector('#timeline')?.addEventListener('click',()=>this._setView('timeline'));
    this.querySelector('#archive')?.addEventListener('click',()=>this._setView('archive'));
  }
  _modules(){return [
    ['dmx','DMX / Art-Net / sACN','Monitoring live, univers, ENTTEC DMX IN','protocoles'],
    ['zones','DMX → Home Assistant','Zones, mappings et synchronisation HA','homeassistant'],
    ['gdtf','GDTF / Contrôle projecteurs','Profils GDTF, patch DMX et attributs HA mémorisables dans des scènes','equipements'],
    ['rdm','RDM / RDMnet','Découverte, identité, adresse, personnalité, capteurs et liaison avec GDTF','protocoles'],
    ['osc','OSC / MIDI / PunchLight','Entrées, learn, mappings et sorties actives protégées','protocoles'],
    ['qlcplus','QLC+','Console QLC+ : widgets Virtual Console, cue lists et fonctions','controles'],
    ['show_control','Show Control','Cues HA + OSC + MIDI + scènes DMX, avec gate dédié','controles'],
    ['rules','Rule Builder','Conditions DMX → actions Home Assistant, simulation et historique','controles'],
    ['watchdog','Signal Watchdogs','Surveillance de présence/perte d’un flux attendu','diagnostic'],
    ['circuit_monitor','DMX Circuit Monitor','Retour d’état receive-only de plusieurs circuits DMX','protocoles'],
    ['power','Power Manager','Boutons personnalisés et séquences DMX actives déphasées','controles'],
    ['doctor','Show Network Doctor','Diagnostic transversal, preuves et équipements concernés','diagnostic'],
    ['show_snapshot','Référence spectacle','Comparer la régie actuelle à un état de référence','diagnostic'],
    ['timecode','Timecode Live','TC courant, source, FPS, drop/non-drop et fraîcheur du signal','show-control'],
    ['incident_center','Incident Center','Corréler les symptômes observés sans inventer de cause','diagnostic'],
    ['pre_show','Pre-Show Check','Vérification read-only avant ouverture salle','diagnostic'],
    ['network','Réseau / Topologie','Interfaces, découverte, empreintes et topologie','reseau'],
    ['audio','Audio / Dante / AES67','État audio réseau, PTP, AES67, ST2110 et AVB','protocoles'],
    ['amplifiers','Amplificateurs / Télémetrie','Inventaire amplis, températures, erreurs, niveaux et charge lorsqu’observés','equipements'],
    ['video','Vidéo / Projecteurs','Projecteurs, état, source, lampe, température et erreurs via PJLink ou adaptateur constructeur','equipements'],
    ['ma','grandMA3 / MA-Net3','Inspection passive MA-Net3','protocoles'],
    ['inventory','Inventaire / Découverte','Équipements observés et inventaire','equipements'],
    ['builder','HA Builder','Entités Home Assistant générées par Show Network','homeassistant'],
    ['etc','ETC Sensor3 / CEM3','Capacités documentées ETC et état du transport live','equipements'],
    ['brands','Constructeurs','Catalogue fabricants et profils visuels','equipements'],
    ['reliability','Diagnostics / Reliability','Files, pertes, chaos tests et watchdogs','diagnostic'],
    ['security','Sécurité','Mot de passe, verrouillage et sorties actives','securite'],
    ['archive','Journal / Backups','Archive persistante et sauvegardes','securite']
  ];}
  _renderModules(){
    const cfg=this._state('show_network_config','sensor.dmx_monitor_show_network_config')?.attributes||{};
    const stateFor=(k)=>cfg[k]===true?'ON':cfg[k]===false?'OFF':'—';
    const stateMap={doctor:`${String(this._state('show_network_doctor','sensor.dmx_monitor_show_network_doctor')?.state||'—').toUpperCase()} · ${this._state('show_network_devices','sensor.dmx_monitor_show_network_devices')?.state||'0'} équipement(s)`,show_control:`${this._value('show_control_cue_count','0')} cue(s) · ${this._value('show_control_fired','0')} déclenchement(s)`,gdtf:`${this._value('gdtf_library_count','0')} profil(s) · ${this._value('gdtf_patch_count','0')} patch(s)`,rdm:`${this._value('rdm_devices_total','0')} appareil(s) · RDM ${stateFor('rdm_enabled')} · RDMnet ${stateFor('rdmnet_enabled')}`,dmx:`Art-Net ${stateFor('dmx_artnet_enabled')} · sACN ${stateFor('dmx_sacn_enabled')}`,osc:`OSC ${stateFor('osc_input_enabled')} · MIDI ${stateFor('midi_enabled')} · PunchLight ${stateFor('punchlight_enabled')}`,watchdog:`Watchdog ${stateFor('watchdog_enabled')}`,power:`${this._value('power_manager_button_count','0')} bouton(s)`,circuit_monitor:`${this._value('dmx_circuit_group_count','0')} groupe(s)`,video:`Projecteurs ${stateFor('projector_monitor_enabled')}`,ma:`MA-Net3 ${stateFor('ma_enabled')}`,builder:`HA Builder ${stateFor('ha_builder_enabled')}`,reliability:`Tests ${stateFor('chaos_enabled')}`};
    const cardFor=([k,n,d])=>`<div class="card module" data-module="${k}"><div class="sn-module-title">${n}</div><div class="desc">${d}</div>${stateMap[k]?`<div class="muted" style="margin-top:10px">${stateMap[k]}</div>`:''}</div>`;
    const bySection=(cat)=>this._modules().filter(m=>m[3]===cat).map(cardFor).join('');
    const section=(title,sub,cat)=>`<div class="section-head"><div class="section-title">${title}</div><div class="muted">${sub}</div></div><div class="module-grid">${bySection(cat)}</div>`;
    this.innerHTML=this._shell(`<button class="btn back" id="back">← PRO</button><div class="top"><div><div class="brand">MODULES SHOW NETWORK</div><div class="muted">Configuration organisée par usage. Chaque rubrique explique ce qu’elle observe, ce qu’elle commande et où la configurer.</div></div></div><div class="footer"><button class="btn primary" id="ha-config">Réglages de base Home Assistant (interfaces, univers, ports, projecteurs…)</button></div>
<div class="config-guide"><b>PARCOURS CONSEILLÉ</b><div class="config-steps"><span>1 · Réseau</span><span>2 · Protocoles</span><span>3 · Équipements</span><span>4 · Contrôles</span><span>5 · Home Assistant</span><span>6 · Sécurité & diagnostic</span></div><div class="muted">Commence par les interfaces réseau, puis active uniquement les protocoles réellement utilisés. Les modules de commande restent protégés par la sécurité Show Network.</div></div>
${section('🌐 RÉSEAU & INTERFACES','Cartes réseau, découverte, topologie et séparation des réseaux bâtiment/régie. Commence ici.','reseau')}
${section('📡 PROTOCOLES SPECTACLE','Réception et observation des protocoles lumière, audio et show-control.','protocoles')}
${section('🧩 ÉQUIPEMENTS','Identification et télémétrie des appareils réellement observés : RDM, projecteurs, amplis, ETC, constructeurs…','equipements')}
${section('🎛 CONTRÔLES & AUTOMATISATIONS','Actions pouvant piloter Home Assistant ou le réseau. Les sorties actives sont protégées par le verrouillage sécurité.','controles')}
${section('🏠 HOME ASSISTANT & DASHBOARD','Entités, mappings et outils destinés aux dashboards Home Assistant.','homeassistant')}
${section('🛡 SÉCURITÉ & DIAGNOSTIC','Doctor, Snapshot, watchdogs, fiabilité, sauvegardes et verrouillage des commandes.','diagnostic')}
${section('💾 SAUVEGARDE & MAINTENANCE','Persistance et restauration de la configuration Show Network.','securite')}`);
    this.querySelector('#back')?.addEventListener('click',()=>this._setView('pro'));
    this.querySelector('#ha-config')?.addEventListener('click',()=>this._openIntegrationConfig());
    this.querySelectorAll('[data-module]').forEach(x=>x.addEventListener('click',()=>this._setView(`module:${x.dataset.module}`)));
  }
  _mountPanels(keys){
    const host=this.querySelector('#module-content'); if(!host)return;
    for(const tag of keys){const el=document.createElement(tag);el.setConfig?.({});host.appendChild(el);if('hass' in el)el.hass=this._hass;else try{el.hass=this._hass}catch(e){}}
  }
  _moduleGate(module,label,key){
    const cfg=this._state('show_network_config','sensor.dmx_monitor_show_network_config')?.attributes||{};
    const enabled=cfg[key]===true;
    return `<button class="btn ${enabled?'primary':''}" data-local-toggle="${module}" data-key="${key}" data-enabled="${enabled?'1':'0'}">${label}: ${enabled?'ON':'OFF'}</button>`;
  }
  _wireLocalGates(){this.querySelectorAll('[data-local-toggle]').forEach(b=>b.addEventListener('click',async()=>{const enabled=b.dataset.enabled==='1';b.disabled=true;try{await this._hass.callService('dmx_monitor','set_module_enabled',{module:b.dataset.localToggle,enabled:!enabled});this._notice='Configuration enregistrée. Le module est rechargé.';}catch(err){this._notice=`Erreur activation: ${err?.message||err}`;}this.render();}));}
  _entityRows(patterns){
    const out=[];const seen=new Set();
    for(const [unique,id] of Object.entries(this._entityMap)){if(patterns.some(p=>unique.toLowerCase().includes(p))){const st=this._hass?.states?.[id];if(st){out.push([unique,id,st.state]);seen.add(id);}}}
    for(const st of Object.values(this._hass?.states||{})){if(seen.has(st.entity_id))continue;const hay=`${st.entity_id} ${st.attributes?.friendly_name||''}`.toLowerCase();if(st.entity_id.includes('dmx_monitor')&&patterns.some(p=>hay.includes(p)))out.push([st.attributes?.friendly_name||st.entity_id,st.entity_id,st.state]);}
    return out.sort((a,b)=>String(a[0]).localeCompare(String(b[0])));
  }
  _entityTable(patterns,empty){const rows=this._entityRows(patterns);return `<div class="card"><table class="entity-table"><thead><tr><th>Entité</th><th>Entity ID</th><th>État</th></tr></thead><tbody>${rows.length?rows.map(r=>`<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td></tr>`).join(''):`<tr><td colspan="3" class="muted">${empty}</td></tr>`}</tbody></table></div>`;}
  _renderModule(key){
    const meta=this._modules().find(x=>x[0]===key)||[key,key,''];
    let controls='';
    if(key==='dmx')controls=`<div class="module-nav">${this._moduleGate('artnet','Art-Net','dmx_artnet_enabled')}${this._moduleGate('sacn','sACN','dmx_sacn_enabled')}<button class="btn" id="open-network-config">Interfaces / univers</button></div>`;
    if(key==='osc')controls=`<div class="module-nav">${this._moduleGate('osc_input','OSC IN','osc_input_enabled')}${this._moduleGate('midi_input','MIDI IN','midi_enabled')}${this._moduleGate('punchlight','PunchLight','punchlight_enabled')}</div>`;
    if(key==='watchdog')controls=`<div class="module-nav">${this._moduleGate('watchdog','Watchdog','watchdog_enabled')}<button class="btn" id="open-network-config">Configurer le watchdog</button></div>`;
    if(key==='rdm')controls=`<div class="module-nav">${this._moduleGate('rdm','RDM','rdm_enabled')}${this._moduleGate('rdmnet','RDMnet','rdmnet_enabled')}<button class="btn" id="open-network-config">Configurer bridges / écritures</button></div>`;
    if(key==='video')controls=`<div class="module-nav">${this._moduleGate('projector_monitor','Monitoring projecteurs','projector_monitor_enabled')}<button class="btn" id="open-network-config">Configurer les projecteurs</button></div>`;
    if(key==='ma')controls=`<div class="module-nav">${this._moduleGate('ma_net3','MA-Net3','ma_enabled')}<button class="btn" id="open-network-config">Interface MA</button></div>`;
    if(key==='builder')controls=`<div class="module-nav">${this._moduleGate('ha_builder','HA Builder','ha_builder_enabled')}</div>`;
    if(key==='reliability')controls=`<div class="module-nav">${this._moduleGate('diagnostics','Tests diagnostic','chaos_enabled')}</div>`;
    const help={dmx:"Observe les niveaux DMX reçus. Cette page n'envoie jamais de DMX.",zones:"Transforme des niveaux DMX reçus en actions Home Assistant lorsque Light Sync est explicitement autorisé.",gdtf:"Utilise GDTF uniquement comme description de contrôle DMX. Chaque attribut patché devient une entité Number Home Assistant et peut donc être enregistré dans une scène. La sortie sACN/Art-Net est active uniquement après déverrouillage et armement du gate GDTF.",rdm:"RDM/RDMnet découvre et interroge les appareils sans remplacer le monitoring DMX. Les écritures d’adresse/personnalité/Identify sont séparées, désactivées par défaut et exigent le déverrouillage Show Network.",osc:"Entrées OSC/MIDI, apprentissage et mappings. Les sorties OSC/MIDI restent des commandes actives protégées.",show_control:"Banque de cues Show Control séparée. Chaque cue peut chaîner des actions Home Assistant, OSC, MIDI et les scènes DMX. Le moteur et chaque sortie active gardent leurs propres gates.",rules:"Crée des conditions sur des valeurs DMX et déclenche des actions HA. Ce n'est ni un watchdog de signal ni le Power Manager.",watchdog:"Surveille qu'un flux attendu continue d'arriver. Il ne regarde pas la valeur de circuits individuels.",circuit_monitor:"Surveille les valeurs de circuits DMX précis sans rien transmettre.",power:"Commande volontairement des circuits DMX avec séquençage/déphasage. Sortie active protégée par le verrou Show Network.",network:"Découvre et qualifie les équipements avec preuves ARP/mDNS/HTTP read-only/SNMP. Auto/Surveiller/Ignorer se règle dans Inventaire et sert au filtrage/priorité opérateur; la découverte générale reste large.",audio:"Observe Dante, PTP, AES67/SAP/SDP, ST2110 et AVB. Une valeur 0 signifie non observé, jamais OK.",amplifiers:"Identifie les amplificateurs uniquement sur preuve puis affiche la télémétrie réellement disponible.",video:"Découvre PJLink et observe les projecteurs via le transport explicitement configuré (PJLink ou adaptateur constructeur). Les commandes restent séparées du monitoring.",ma:"Observe MA-Net3 et les sessions sans rejoindre ni contrôler une session. Le type d'appareil n'est affiché que sur marqueur de payload.",etc:"Supervision ETC Sensor3/CEM3 via l’interface Web CEM3 documentée, en lecture seule. Température CPU, secteur, phases, erreurs, version et état des circuits ne sont affichés que s’ils sont réellement retournés par le rack.",inventory:"Inventaire commun à tous les modules. Auto = comportement normal, Surveiller = favori/prioritaire, Ignorer = filtrage opérateur. Aucun de ces choix ne coupe la découverte générale.",reliability:"Diagnostic des files et simulations logiques. N'envoie pas de panne réelle sur le réseau.",builder:"Expose et organise les entités Show Network utilisables dans les dashboards Home Assistant. Les cartes Show Network utilisent ces états réels et affichent INCONNU si une donnée manque.",qlcplus:"Pilote QLC+ uniquement via les services explicitement configurés. Les fonctions de Virtual Console ne sont pas simulées.",doctor:"Croise les diagnostics disponibles et fournit les preuves associées. Un avertissement ne devient jamais automatiquement une cause racine.",show_snapshot:"Enregistre un état de référence de la régie puis signale les écarts observés. Il ne modifie aucun équipement.",incident_center:"Regroupe les événements proches dans le temps et les équipements reliés par preuve. Il ne déduit pas automatiquement une cause racine.",pre_show:"Contrôle read-only avant spectacle. READY exige des contrôles PASS; une donnée non mesurable reste UNKNOWN/CHECK.",brands:"Catalogue d'identification visuelle et de fabricants. Une marque n'est jamais déduite de son logo seul.",security:"Protège les commandes actives. Tant que le verrou n'est pas ouvert, les sorties concernées restent bloquées côté backend.",archive:"Sauvegarde configuration, journal et diagnostics. Les secrets sont exclus des sauvegardes portables."};
    let inner=`<button class="btn back" id="back">← MODULES</button><div class="top"><div><div class="brand">${meta[1]}</div><div class="muted">${meta[2]}</div></div></div>${controls}${help[key]?`<div class="notice"><b>À quoi ça sert ?</b> ${help[key]}</div>`:''}<div class="panel-stack" id="module-content"></div>`;
    if(key==='audio'){
      const ptpEnt=this._state('ptp_clock_present','sensor.dmx_monitor_ptp_clock_present'); const ptpA=ptpEnt?.attributes||{};
      const audioEnt=this._state('audio_protocols_active','sensor.dmx_monitor_audio_protocols_active'); const health=audioEnt?.attributes?.audio_network_health||{}; const managed=audioEnt?.attributes?.dante_managed||{};
      const aesEnt=this._state('aes67_session_count','sensor.dmx_monitor_aes67_session_count')||this._state('aes67_sap_packets','sensor.dmx_monitor_aes67_sap_packets'); const aesA=aesEnt?.attributes||{};
      const sessions=aesA.sessions||[];
      const rx=this._state('protocol_rx_diagnostics','sensor.dmx_monitor_protocol_rx_diagnostics')?.attributes||{}; const cfg=this._state('show_network_config','sensor.dmx_monitor_show_network_config')?.attributes||{};
      const danteDiag=rx.dante||{},ptpDiag=rx.ptp||{}; const danteRows=danteDiag.dante_inventory||[],danteSources=danteDiag.dante_source_stats||[],ptpSources=ptpDiag.ptp_source_stats||[];
      const sw=this._state('switch_telemetry','sensor.dmx_monitor_switch_telemetry')?.attributes?.switches||[];
      const inv=this._state('device_inventory','sensor.dmx_monitor_device_inventory')?.attributes?.devices||[];
      const journal=this._state('journal_archive','sensor.dmx_monitor_journal_archive')?.attributes||{};
      const events=(journal.recent_events||[]).filter(e=>['dante','ptp','switch','lldp','audio'].includes(String(e.kind||'').toLowerCase())).slice().reverse().slice(0,20);
      const fmtRate=(bps)=>{const n=Number(bps);if(!Number.isFinite(n))return '—';if(n>=1e9)return (n/1e9).toFixed(2)+' Gb/s';if(n>=1e6)return (n/1e6).toFixed(1)+' Mb/s';if(n>=1e3)return (n/1e3).toFixed(1)+' kb/s';return n.toFixed(0)+' b/s'};
      const portRows=[]; for(const x of sw)for(const p of (x.ports||[])){const speed=Number(p.speed_mbps);const rxB=Number(p.rx_bps),txB=Number(p.tx_bps);const rxPct=Number.isFinite(speed)&&speed>0&&Number.isFinite(rxB)?rxB/(speed*1e6)*100:null;const txPct=Number.isFinite(speed)&&speed>0&&Number.isFinite(txB)?txB/(speed*1e6)*100:null;const peak=Math.max(rxPct??0,txPct??0);if(p.up||peak||Number(p.rx_errors)||Number(p.tx_errors))portRows.push({sw:x.name||x.ip||'switch',...p,rxPct,txPct,peak});}
      portRows.sort((a,b)=>(b.peak||0)-(a.peak||0));
      const maxUtil=portRows.length?Math.max(...portRows.map(x=>x.peak||0)):null; const warn=maxUtil!=null&&maxUtil>=70,crit=maxUtil!=null&&maxUtil>=85;
      const gm=ptpDiag.ptp_active_grandmaster_identity||ptpA.ptp_active_grandmaster_identity||'—'; const clockPresent=this._truthy(this._value('ptp_clock_present','false'));
      const unavailable=(label,why='Télémétrie Dante appareil non disponible depuis l’observation passive actuelle.')=>`<div class="row"><span>${label}</span><b class="muted">NON MESURÉ</b><span class="muted">${why}</span></div>`;
      const levelEnt=this._state('audio_levels','sensor.dmx_monitor_audio_levels')||this._state('audio_channel_levels','sensor.dmx_monitor_audio_channel_levels');
      const levelA=levelEnt?.attributes||{}; const levelRows=Array.isArray(levelA.channels)?levelA.channels:[];
      const validLevels=levelRows.filter(x=>Number.isFinite(Number(x.peak_db??x.peak))||Number.isFinite(Number(x.rms_db??x.rms)));
      const meter=(x)=>{const peak=Number(x.peak_db??x.peak),rms=Number(x.rms_db??x.rms);const pv=Number.isFinite(peak)?Math.max(0,Math.min(100,(peak+60)/60*100)):0;const rv=Number.isFinite(rms)?Math.max(0,Math.min(100,(rms+60)/60*100)):0;return `<div class="sn-meter"><div class="sn-meter-name">${esc(x.name||x.channel||'Canal')}</div><div class="sn-meter-track"><i class="sn-meter-rms" style="height:${rv}%"></i><i class="sn-meter-peak" style="bottom:${pv}%"></i></div><div class="sn-meter-value">${Number.isFinite(peak)?peak.toFixed(1)+' dB':'—'}<small>PK</small></div><div class="sn-meter-value muted">${Number.isFinite(rms)?rms.toFixed(1)+' dB':'—'}<small>RMS</small></div></div>`};
      const meters=validLevels.length?validLevels.slice(0,16).map(meter).join(''):`<div class="sn-meter-empty"><b>NIVEAUX NON DISPONIBLES</b><span>Peak/RMS apparaîtront ici uniquement lorsqu’une source réelle les expose.</span></div>`;
      const sessRows=sessions.length?sessions.map(x=>`<div class="row"><span>${esc(x.name||'AES67 stream')}</span><span>${esc(x.source||'—')}</span><span>${esc(x.destination||'—')}:${x.port??'—'}</span><span>${esc(x.rtpmap||x.payload_type||'—')}</span><span>${x.age_s??'—'} s</span></div>`).join(''):'<div class="muted">Aucune annonce SDP observée.</div>';
      const devices=danteRows.map(x=>{const ip=x.source;const i=inv.find(y=>y.ip===ip)||{};const st=danteSources.find(y=>y.source===ip)||{};return `<div class="row"><span><b>${esc((x.names||[])[0]||x.display_name||i.display_name||ip||'Dante')}</b><br><span class="muted">${esc(i.display_manufacturer||'constructeur non prouvé')} · ${esc(i.display_model||'modèle non observé')}</span></span><span>${esc(ip||'—')}</span><span>${fmtRate(st.observed_bps)}<br><span class="muted">monitor ${st.monitor_packets??0} pkt · mDNS ${st.mdns_packets??0}</span></span><span>${esc(i.firmware||'firmware non observé')}</span><span>${st.fresh??x.fresh?'FRESH':'STALE'} · ${st.age_s??x.age_s??'—'} s</span></div>`}).join('')||'<div class="muted">Aucun endpoint Dante identifié avec preuve.</div>';
      const bwRows=portRows.slice(0,24).map(p=>`<div class="row"><span>${esc(p.sw)} · ${esc(p.alias||p.name||('port '+p.index))}</span><span>${p.speed_mbps??'—'} Mb/s</span><span>RX ${fmtRate(p.rx_bps)}${p.rxPct!=null?' · '+p.rxPct.toFixed(1)+'%':''}</span><span>TX ${fmtRate(p.tx_bps)}${p.txPct!=null?' · '+p.txPct.toFixed(1)+'%':''}</span><b class="${p.peak>=85?'error':p.peak>=70?'warn':'ok'}">${p.peak? p.peak.toFixed(1)+'%':'—'}</b></div>`).join('')||'<div class="muted">Aucune télémétrie de débit par port disponible.</div>';
      const errRows=portRows.filter(p=>Number(p.rx_errors)||Number(p.tx_errors)).map(p=>`<div class="row"><span>${esc(p.sw)} · ${esc(p.alias||p.name||p.index)}</span><span>RX ${p.rx_errors??0}</span><span>TX ${p.tx_errors??0}</span></div>`).join('')||'<div class="muted">Aucune erreur IF-MIB observée sur les ports actuellement remontés.</div>';
      inner+=`<style>.sn-audio-hero{background:linear-gradient(120deg,#111820,#0b1822);border:1px solid #244457;border-radius:14px;padding:18px;box-shadow:inset 0 1px 0 #ffffff08}.sn-audio-head{display:flex;align-items:center;justify-content:space-between;gap:16px}.sn-audio-title{font-size:25px;font-weight:850}.sn-audio-title span{color:#43c7ff}.sn-audio-kpis{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:9px;margin-top:15px}.sn-kpi{background:#0d141a;border:1px solid #263a48;border-radius:10px;padding:12px}.sn-kpi b{display:block;font-size:20px;margin:5px 0}.sn-audio-grid{display:grid;grid-template-columns:1.1fr 1fr;gap:12px;margin-top:12px}.sn-meter-bank{display:flex;gap:9px;align-items:flex-end;min-height:230px;padding:14px;overflow:auto}.sn-meter{min-width:54px;text-align:center}.sn-meter-name{height:30px;font-size:9px;color:#aab5be;overflow:hidden}.sn-meter-track{position:relative;width:24px;height:150px;margin:auto;background:repeating-linear-gradient(to top,#142029 0,#142029 8px,#0a0f13 9px,#0a0f13 10px);border:1px solid #33444f;border-radius:4px;overflow:hidden}.sn-meter-rms{position:absolute;bottom:0;left:3px;right:3px;background:linear-gradient(to top,#32d07d 0 68%,#e3c34e 82%,#ef6d6d 100%);border-radius:2px}.sn-meter-peak{position:absolute;left:2px;right:2px;height:2px;background:#f4f7fa}.sn-meter-value{font-size:9px;margin-top:5px}.sn-meter-value small{display:block;font-size:7px}.sn-meter-empty{min-height:190px;flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;border:1px dashed #38505f;border-radius:10px;color:#7f929f;gap:8px}.sn-meter-empty b{color:#a8bac5}.sn-device-table .row{display:grid;grid-template-columns:1.5fr .8fr 1fr 1fr .8fr;gap:10px}.sn-section-title{font-size:14px;font-weight:800;margin-bottom:10px;color:#dff5ff}.sn-status-dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:#68df9a;margin-right:6px}@media(max-width:900px){.sn-audio-kpis,.sn-audio-grid{grid-template-columns:1fr 1fr}.sn-audio-head{align-items:flex-start;flex-direction:column}}@media(max-width:600px){.sn-audio-kpis,.sn-audio-grid{grid-template-columns:1fr}}</style><div class="sn-audio-hero"><div class="sn-audio-head"><div><div class="sn-audio-title">◉ <span>Audio Réseau</span></div><div class="muted">Dante · AES67 · PTP · santé réseau professionnelle</div></div><div class="badge ${clockPresent?'ok':'off'}">${clockPresent?'● PTP ACTIF':'PTP NON OBSERVÉ'}</div></div><div class="sn-audio-kpis"><div class="sn-kpi"><div class="title">DANTE</div><b>${this._value('dante_sources','—')} appareils</b><span class="muted">${danteSources.filter(x=>x.fresh).length} frais</span></div><div class="sn-kpi"><div class="title">CLOCK MASTER</div><b class="${clockPresent?'ok':'error'}">${esc(gm)}</b><span class="muted">âge ${this._value('ptp_clock_age_s','—')} s</span></div><div class="sn-kpi"><div class="title">BANDE PASSANTE</div><b class="${crit?'critical':warn?'warning':maxUtil!=null?'ok':'off'}">${maxUtil!=null?maxUtil.toFixed(1)+'%':'NON MESURÉ'}</b><span class="muted">max RX/TX d’un port</span></div><div class="sn-kpi"><div class="title">ÉVÉNEMENTS</div><b>${events.length}</b><span class="muted">audio / clock / réseau</span></div></div></div><div class="sn-audio-grid"><div class="card"><div class="sn-section-title">Niveaux temps réel · Peak / RMS</div><div class="sn-meter-bank">${meters}</div><div class="muted">Les vumètres ne sont alimentés que par <code>sensor.dmx_monitor_audio_levels</code> / <code>audio_channel_levels</code> avec valeurs Peak/RMS réelles.</div></div><div class="card"><div class="sn-section-title">État du réseau audio</div><div class="row"><span><i class="sn-status-dot"></i>PTP Grandmaster</span><b>${esc(gm)}</b></div><div class="row"><span>Clock</span><b class="${clockPresent?'ok':'error'}">${clockPresent?'OBSERVÉ':'ABSENT'}</b></div><div class="row"><span>Jitter arrivée PTP</span><b>${ptpDiag.ptp_jitter_ms??'—'} ms</b></div><div class="row"><span>Charge max lien</span><b class="${crit?'critical':warn?'warning':'ok'}">${maxUtil!=null?maxUtil.toFixed(1)+'%':'—'}</b></div><div class="row"><span>Erreurs interfaces</span><b>${portRows.reduce((n,p)=>n+Number(p.rx_errors||0)+Number(p.tx_errors||0),0)}</b></div></div></div><div class="card sn-device-table" style="margin-top:12px"><div class="sn-section-title">Appareils audio détectés</div>${devices}</div><div class="card" style="margin-top:12px"><div class="sn-section-title">Routing / Subscriptions · Dante Managed API</div>${managed.available?`<div class="row"><span>Domaine</span><b>${esc(managed.selected_domain_name||managed.selected_domain_id||'—')}</b></div><div class="row"><span>Appareils API</span><b>${managed.device_count??0}</b><span>Subscriptions</span><b>${managed.subscription_count??0}</b></div><div class="row"><span>État domaine</span><b>${esc(JSON.stringify(managed.domain_status||{}))}</b></div>${(managed.subscription_issues||[]).length?`<div class="notice"><b>${managed.subscription_issue_count} abonnement(s) à vérifier</b></div>`:`<div class="notice"><b>API disponible</b> · aucune anomalie de subscription signalée par les états reçus.</div>`}${(managed.subscriptions||[]).slice(0,24).map(x=>`<div class="row"><span>${esc(x.source_device||'—')} / ${esc(x.source_channel||'—')}</span><span>→</span><span>${esc(x.receiver_device||'—')} / ${esc(x.rx_channel||'—')}</span><b>${esc(x.status||'—')}</b></div>`).join('')}`:`<div class="notice"><b>NON MESURÉ</b> · ${managed.configured?`Dante Managed API configurée mais indisponible${managed.error?' : '+esc(managed.error):''}`:'Configure Dante Director ou Dante Domain Manager + clé API dans les options pour obtenir les statuts et subscriptions officiels en lecture seule.'}</div>`}</div><div class="card" style="margin-top:12px"><div class="sn-section-title">Signal Presence / Vumètres</div><div class="row"><span>Signal Presence Dante</span><b>PRÉVU VIA SOURCE OFFICIELLE</b></div><div class="row"><span>Peak / RMS continu</span><b>${validLevels.length?'MESURÉ':'NON MESURÉ'}</b></div><div class="muted">Signal Presence n’est pas transformé en dBFS : présence/silence/clipping reste un état. Les vrais Peak/RMS exigent une source de niveau ou la réception audio.</div></div><div class="notice">Supervision factuelle : <b>MESURÉ</b> = donnée réellement reçue, <b>OBSERVÉ</b> = preuve réseau passive, <b>NON MESURÉ</b> = télémétrie indisponible. Aucun niveau, lock ou flux propriétaire n’est simulé.</div>
      <div class="card" style="margin-top:12px"><div class="title">CLOCK STATUS</div><div class="row"><span>PTP présent</span><b class="${clockPresent?'ok':'error'}">${clockPresent?'OUI':'NON OBSERVÉ'}</b></div><div class="row"><span>Leader / Grandmaster décodé</span><b>${esc(gm)}</b></div><div class="row"><span>PTPv1 Dante</span><b>${this._truthy(this._value('ptp_dante_v1_observed','false'))?'OBSERVÉ':'—'}</b></div><div class="row"><span>PTPv2 / AES67</span><b>${this._truthy(this._value('ptp_v2_observed','false'))?'OBSERVÉ':'—'}</b></div>${unavailable('Sync Locked / Not Locked par appareil','Nécessite une télémétrie appareil Dante explicite; le jitter d’arrivée PTP n’est pas un offset d’horloge.')}${unavailable('Clock stability / offset par appareil')}</div>
      <div class="card" style="margin-top:12px"><div class="title">BANDWIDTH · LAYER 1</div><div class="notice">Le seuil 70% est un avertissement conservateur Show Network. 85% correspond au repère Audinate approximatif à ne pas dépasser en RX ou TX pour préserver les performances de synchronisation.</div>${bwRows}${errRows}</div>
      <div class="card" style="margin-top:12px"><div class="title">LATENCY · PACKET HEALTH</div>${unavailable('Latency histogram / late packets')}${unavailable('Paquets Dante perdus/corrompus par appareil')}<div class="row"><span>Erreurs physiques switch (IF-MIB)</span><b>${portRows.reduce((n,p)=>n+Number(p.rx_errors||0)+Number(p.tx_errors||0),0)}</b><span class="muted">compteurs réels, pas assimilés automatiquement à des pertes Dante</span></div></div>
      <div class="card" style="margin-top:12px"><div class="title">ROUTING / SUBSCRIPTIONS</div>${unavailable('Subscriptions Dante TX → RX','La présence de trafic UDP ne permet pas de reconstruire honnêtement la matrice Dante.') }<div class="title" style="margin-top:12px">AES67 / SDP OBSERVÉ</div>${sessRows}</div>
      <div class="card" style="margin-top:12px"><div class="title">REDUNDANCY · PRIMARY / SECONDARY</div>${unavailable('Primary / Secondary par appareil','Aucune bascule ou perte Secondary n’est inventée sans état explicite fourni par l’appareil.')}</div>
      <div class="card" style="margin-top:12px"><div class="title">DEVICES · INVENTAIRE</div>${devices}</div>
      <div class="card" style="margin-top:12px"><div class="title">MULTICAST / UNICAST · IGMP</div><div class="row"><span>Multicast PTP</span><b>OBSERVÉ</b><span>${esc((ptpDiag.ptp_multicast_groups||[]).join(', ')||'groupes PTP')}</span></div>${unavailable('Répartition audio Dante Unicast / Multicast')}${unavailable('État IGMP Snooping par switch','À afficher seulement lorsqu’un switch expose réellement cette télémétrie/configuration.')}</div>
      <div class="card" style="margin-top:12px"><div class="title">AUDIO HEALTH · LEVELS</div><div class="sn-meter-bank">${meters}</div>${validLevels.length?`<div class="row"><span>Canaux réellement mesurés</span><b>${validLevels.length}</b><span class="muted">Peak/RMS issus de la source de niveaux</span></div>`:unavailable('Signal Presence / Peak / RMS','Le débit réseau ne prouve pas la présence audio. Les vumètres restent volontairement inactifs sans télémétrie de niveau.')}</div>
      <div class="card" style="margin-top:12px"><div class="title">EVENT LOGGING</div>${events.length?events.map(e=>`<div class="row"><span>${esc(e.ts||'—')}</span><span>${esc(e.kind||'—')}</span><b>${esc(e.event||'—')}</b><span class="muted">${esc(JSON.stringify(e.data||{}))}</span></div>`).join(''):'<div class="muted">Aucun événement audio/clock/switch récent en mémoire.</div>'}</div>
      <details data-persist="dante-geek" class="card" style="margin-top:12px"><summary style="cursor:pointer;font-weight:800">🧪 DANTE / PTP — GEEK DIAGNOSTICS</summary><div class="row"><span>Interface Dante</span><b>${esc(cfg.interface_dante||'—')}</b></div><div class="row"><span>Interface PTP</span><b>${esc(cfg.interface_ptp||'—')}</b></div><div class="row"><span>Interface audio</span><b>${esc(cfg.interface_audio||'—')}</b></div><div class="row"><span>Sync / FollowUp / Announce / Delay</span><b>${ptpDiag.ptp_sync_packets??0} / ${ptpDiag.ptp_follow_up_packets??0} / ${ptpDiag.ptp_announce_packets??0} / ${ptpDiag.ptp_delay_packets??0}</b></div><h4>Sources Dante</h4>${danteSources.map(x=>`<div class="row"><span>${esc(x.source)}</span><span>${x.packets} pkt</span><span>ports ${esc((x.ports||[]).join(','))}</span><b>${x.age_s}s</b></div>`).join('')||'<div class="muted">Aucune source.</div>'}<h4>Sources PTP</h4>${ptpSources.map(x=>`<div class="row"><span>${esc(x.source)}</span><span>${x.packets} pkt</span><span>v${esc((x.versions||[]).join(','))}</span><span>domain ${esc((x.domains||[]).join(','))}</span><b>${x.age_s}s</b></div>`).join('')||'<div class="muted">Aucune source.</div>'}<details data-persist="dante-raw"><summary style="cursor:pointer">JSON brut</summary><pre style="white-space:pre-wrap;overflow:auto;max-height:420px;font-size:10px">${esc(JSON.stringify({dante:danteDiag,ptp:ptpDiag,audio:health},null,2))}</pre></details></details>`;
    }
    if(key==='amplifiers'){
      const e=this._state('audio_amplifiers_total','sensor.dmx_monitor_audio_amplifiers_total'); const a=e?.attributes||{}; const amps=a.amplifiers||[];
      const cards=`<div class="module-grid"><div class="card"><div class="title">Amplis observés</div><div class="big">${this._value('audio_amplifiers_total','0')}</div></div><div class="card"><div class="title">En ligne</div><div class="big">${this._value('audio_amplifiers_online','0')}</div></div><div class="card"><div class="title">Erreurs</div><div class="big">${this._value('audio_amplifiers_errors','0')}</div></div><div class="card"><div class="title">Température max</div><div class="big">${this._value('audio_amplifier_temperature_max','—')} °C</div></div></div>`;
      const rows=amps.length?amps.map(x=>`<div class="row"><span>${esc(x.manufacturer||'—')} ${esc(x.model||'')}</span><span>${esc(x.device_name||x.host||'—')}</span><span>${x.online?'ONLINE':'STALE'} · ${x.age_s??'—'} s</span><span>${esc((x.protocols||[]).join(', ')||'discovery')}</span><span>${x.temperature_c??'—'} °C</span><span>${esc(x.status||'unknown')}</span><span>${esc(x.error||'—')}</span></div>`).join(''):'<div class="notice">Aucun ampli identifié avec preuve. Les marques supportées par catalogue ne sont pas présentées comme découvertes.</div>';
      const manualAmps=amps.filter(x=>x.protocols&&x.protocols.includes('manual'));
      inner+=`<div class="card"><div class="title">AMPLIFICATEURS AUDIO</div><div class="notice">L-Acoustics prioritaire via AVDECC/Milan, puis AES70/OCA (notamment d&b lorsque réellement exposé), Lab Gruppen/Lake, QSC, Crown, Adamson, Yamaha et autres via découverte générique. Température/niveaux/charge/limiteur uniquement lorsqu’une source réelle les fournit.</div>${cards}<div style="margin-top:12px">${rows}</div>
      <div class="section" style="margin-top:14px"><div class="title">AJOUTER MANUELLEMENT PAR IP</div><div class="notice">Si la détection automatique ne reconnaît pas ta marque (ex : vue seulement via son protocole comme « Dante »), indique son adresse IP ici — aucune donnée n'est inventée, ça sert juste à nommer un ampli que tu sais être là.</div><div class="grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:7px"><input id="amp-host" placeholder="Adresse IP"><input id="amp-mfr" placeholder="Marque (ex: Audiofocus)"><input id="amp-model" placeholder="Modèle (optionnel)"><input id="amp-name" placeholder="Nom affiché (optionnel)"></div><button class="btn primary" id="add-manual-amp" style="margin-top:8px">Ajouter</button>
      ${manualAmps.length?manualAmps.map(x=>`<div class="row" style="margin-top:8px"><span>${esc(x.manufacturer)} ${esc(x.model||'')} · ${esc(x.host)}</span><button class="btn danger" data-del-amp="${esc(x.host)}">Retirer</button></div>`).join(''):''}
      </div></div>`;
    }
    if(key==='video'){
      const cfg=this._state('show_network_config','sensor.dmx_monitor_show_network_config')?.attributes||{};const enabled=cfg.projector_monitor_enabled===true;
      const pstate=this._state('projectors_total','sensor.dmx_monitor_projectors_total'); const ps=pstate?.attributes||{}; const projectors=ps.projectors||[];
      const errLabel=(d)=>Object.entries(d||{}).filter(([,v])=>v&&v!=='ok').map(([k,v])=>`${k}: ${v}`).join(' · ')||'Aucune';
      const ctrlOn=ps.control_enabled===true; const sec=this._securityState(); const unlocked=sec.unlocked;
      const cards=`<div class="module-grid"><div class="card"><div class="title">Projecteurs</div><div class="big">${ps.total??projectors.length}</div></div><div class="card"><div class="title">En ligne</div><div class="big">${ps.online??0}</div></div><div class="card"><div class="title">En erreur</div><div class="big">${ps.errors??0}</div></div><div class="card"><div class="title">Découverts PJLink</div><div class="big">${ps.discovered??0}</div></div></div>`;
      const rows=projectors.length?projectors.map(x=>`<div class="card"><div class="title">${esc(x.name||x.model||x.host||'Projecteur')}</div><div class="muted">${esc([x.manufacturer,x.model].filter(Boolean).join(' · ')||'Identité en attente')}</div><div class="big ${x.online?'ok':'off'}">${x.online?esc((x.power||'online').toUpperCase()):(x.stale?'STALE':'OFFLINE')}</div><div class="row"><span>Adresse</span><b>${esc(x.host||'—')}:${x.port??4352}</b></div><div class="row"><span>Profil / transport</span><b>${esc(x.profile||'auto')} · ${esc(x.telemetry_source||x.transport||'—')}</b></div><div class="row"><span>Authentification</span><b>${x.authenticated===true?'OK':(x.authenticated===false?'NON':'—')} ${esc(x.auth_method||'')}</b></div><div class="row"><span>N° série</span><b>${esc(x.serial_number||'—')}</b></div><div class="row"><span>Firmware</span><b>${esc(x.software_version||'—')}</b></div><div class="row"><span>Entrée</span><b>${esc(x.input_name||x.input_source||'—')}</b></div><div class="row"><span>Mute / shutter</span><b>${esc(x.av_mute||'—')}</b></div><div class="row"><span>Lampe/source</span><b>${x.lamp_hours??'—'} h</b></div><div class="row"><span>Température max</span><b>${x.temperature_c??'—'} °C</b></div><div class="row"><span>Ventilateurs</span><b>${esc(Object.entries(x.fans_rpm||{}).slice(0,4).map(([k,v])=>`${k}:${v}`).join(' · ')||'—')}</b></div><div class="row"><span>Signal</span><b>${esc(x.signal||x.input_resolution||'—')}</b></div><div class="row"><span>Erreurs</span><b>${esc(x.errors||'—')}</b></div><div class="row"><span>Fraîcheur télémétrie</span><b>${x.telemetry_age_s??'—'} s ${x.stale?'· périmée':''}</b></div>${x.last_error?`<div class="notice">${esc(x.last_error)}</div>`:''}<div class="footer"><button class="btn primary" data-proj-power="1" data-host="${esc(x.host||'')}" data-port="${x.port??4352}" ${(unlocked&&ctrlOn)?'':'disabled'}>Power ON</button><button class="btn" data-proj-power="0" data-host="${esc(x.host||'')}" data-port="${x.port??4352}" ${(unlocked&&ctrlOn)?'':'disabled'}>Standby</button><button class="btn" data-proj-mute="1" data-host="${esc(x.host||'')}" data-port="${x.port??4352}" ${(unlocked&&ctrlOn)?'':'disabled'}>Mute ON</button><button class="btn" data-proj-mute="0" data-host="${esc(x.host||'')}" data-port="${x.port??4352}" ${(unlocked&&ctrlOn)?'':'disabled'}>Mute OFF</button></div><div class="row"><input data-proj-input-field="${esc(x.host||'')}" placeholder="Entrée (ex: HDMI1)" style="flex:1"><button class="btn" data-proj-input="${esc(x.host||'')}" data-port="${x.port??4352}" ${(unlocked&&ctrlOn)?'':'disabled'}>Changer</button></div></div>`).join(''):'<div class="notice">Aucun projecteur PJLink observé. La découverte automatique reste PJLink Class 2 ; les protocoles constructeur ne sont utilisés que pour des appareils explicitement configurés.</div>';
      inner+=`<div class="card"><div class="title">VIDÉO / PROJECTEURS</div><div class="big ${enabled?'ok':'off'}">${enabled?'MONITORING ACTIVÉ':'DÉSACTIVÉ'}</div><div class="notice">PJLink Class 1/2 reste le socle et le fallback. Les profils Panasonic Web API, Digital Projection ASCII, Christie HS et Barco Pulse ajoutent uniquement les données réellement renvoyées. Un profil constructeur n'est jamais déduit d'une simple adresse IP.</div>${cards}<div class="row"><span>Dernière recherche PJLink</span><b>${ps.last_discovery_age_s??'—'} s</b></div><div class="row"><span>Sécurité</span><b class="${unlocked?'ok':'off'}">${unlocked?'DÉVERROUILLÉE':'VERROUILLÉE'}</b><span>Contrôle projecteurs</span><b class="${ctrlOn?'ok':'off'}">${ctrlOn?'ARMÉ':'DÉSARMÉ'}</b></div><div class="footer"><button class="btn ${ctrlOn?'primary':''}" id="toggle-projector-control" data-on="${ctrlOn?'1':'0'}">${ctrlOn?'Désarmer le contrôle projecteurs':'Armer le contrôle projecteurs'}</button></div></div><div class="module-grid">${rows}</div>`;
      const vip=this._videoIp||{endpoint_count:0,online_count:0,protocols:{},endpoints:[]};const vrows=vip.endpoints||[];const proto=Object.entries(vip.protocols||{}).map(([k,v])=>`${esc(k)} ${v}`).join(' · ')||'aucun';
      const previewRow=this._videoPreviewKey?vrows.find(x=>x.key===this._videoPreviewKey):null;
      const previewUrl=(previewRow&&this._videoPreviewEntryId)?`/api/dmx_monitor/video_ip_preview?entry_id=${encodeURIComponent(this._videoPreviewEntryId)}&key=${encodeURIComponent(previewRow.key)}&t=${Date.now()}`:'';
      inner+=`<div class="card" style="margin-top:12px"><div class="title">VIDÉO IP — SUPERVISION</div><div class="notice"><b>Aucune entité Sensor HA créée.</b> Le module peut rester totalement passif. L'aperçu vidéo basse qualité est séparé, optionnel et ne s'abonne au flux que pendant l'affichage.</div><div class="module-grid"><div class="card"><div class="title">Fonction</div><div class="big ${vip.enabled?'ok':'off'}" style="font-size:18px">${vip.enabled?'ACTIVÉE':'DÉSACTIVÉE'}</div></div><div class="card"><div class="title">Interface réseau</div><div class="big" style="font-size:18px">${esc(vip.interface||'0.0.0.0')}</div></div><div class="card"><div class="title">Endpoints observés</div><div class="big">${vip.endpoint_count??0}</div></div><div class="card"><div class="title">Aperçu basse qualité</div><div class="big ${vip.preview_enabled?'warning':'off'}" style="font-size:18px">${vip.preview_enabled?'AUTORISÉ':'OFF'}</div></div></div>${previewRow&&previewUrl?`<div class="card" style="margin-top:12px"><div class="title">APERÇU BASSE QUALITÉ · ${esc(previewRow.name||previewRow.host||'flux')}</div><div class="muted">640 px max · 5 fps · sans audio · une seule prévisualisation à la fois. Fermer remet le module en supervision pure.</div><div style="margin-top:10px;background:#050607;min-height:180px;display:flex;align-items:center;justify-content:center"><img src="${previewUrl}" style="max-width:100%;max-height:420px;object-fit:contain" alt="Aperçu vidéo basse qualité"></div><div class="footer"><button class="btn" id="video-preview-close">Fermer l'aperçu</button></div></div>`:''}<div class="notice">Protocoles: ${proto}. Pour changer l'interface réseau, activer/désactiver le module ou autoriser l'aperçu, utilise <b>Configurer les projecteurs</b> puis les options Show Network.</div>${vip.error?`<div class="notice">WebSocket supervision: ${esc(vip.error)}</div>`:''}${vrows.length?vrows.map(x=>`<div class="row"><span><b>${esc(x.name||x.host||'endpoint')}</b><br><span class="muted">${esc(x.evidence?.join(' · ')||x.discovery||'passif')}</span></span><span>${esc(x.protocol||'—')}</span><span>${esc(x.host||'—')}${x.port?':'+x.port:''}</span><span>${x.online?'RÉCENT':'STALE'} · ${x.age_s??'—'} s</span><span>${x.uri?esc(x.uri):'pas d’URI synthétique'}${x.vlc_direct&&vip.preview_enabled?`<br><button class="btn" data-video-preview="${esc(x.key)}" data-entry-id="${esc(x.entry_id||vip.entry_id||'')}">Voir basse qualité</button>`:''}</span></div>`).join(''):'<div class="muted" style="margin-top:12px">Aucun endpoint vidéo IP explicitement identifié. HTTP générique n’est pas classé vidéo sans preuve.</div>'}</div>`;
    }
    if(key==='rdm'){const e=this._state('rdm_devices_total','sensor.dmx_monitor_rdm_devices_total');const a=e?.attributes||{};const dev=a.rdm_devices||[];const cfg=this._state('show_network_config','sensor.dmx_monitor_show_network_config')?.attributes||{};const writesArmed=cfg.rdm_allow_writes===true;const sec=this._securityState();const unlocked=sec.unlocked;const canWrite=writesArmed&&unlocked;const gdtfPatches=this._state('gdtf_library_count','sensor.dmx_monitor_gdtf_library_count')?.attributes?.patches||[];inner+=`<div class="card"><div class="title">RDM / RDMnet — DEVICE MANAGEMENT</div><div class="module-grid"><div class="card"><div class="title">Appareils</div><div class="big">${dev.length}</div></div><div class="card"><div class="title">En ligne</div><div class="big">${dev.filter(x=>x.online).length}</div></div><div class="card"><div class="title">Transports</div><div class="big">${esc((a.transports||[]).join(' / ')||'—')}</div></div></div><div class="notice">Découverte et GET sont read-only. Les SET RDM restent désactivés tant que <b>RDM writes</b> n'est pas armé dans les options et que Show Network n'est pas déverrouillé. Une UID peut être associée à un patch GDTF sans émettre de DMX.</div><div class="row"><span>RDM writes (options)</span><b class="${writesArmed?'ok':'off'}">${writesArmed?'ARMÉ':'DÉSARMÉ — voir Configurer bridges / écritures'}</b><span>Sécurité</span><b class="${unlocked?'ok':'off'}">${unlocked?'DÉVERROUILLÉE':'VERROUILLÉE'}</b></div><div class="footer"><button class="btn" id="rdm-refresh">Rafraîchir RDM</button></div>${dev.map(x=>`<div class="card"><div class="title">${esc(x.device_label||x.model_description||x.uid)}</div><div class="row"><span>UID</span><b>${esc(x.uid)}</b></div><div class="row"><span>Transport</span><b>${esc(x.transport)} ${x.universe!=null?'· U'+x.universe:(x.scope?'· '+esc(x.scope):'')}</b></div><div class="row"><span>Fabricant / modèle</span><b>${esc(x.manufacturer_label||'—')} · ${esc(x.model_description||'—')}</b></div><div class="row"><span>Adresse DMX</span><b>${x.dmx_start_address??'—'} · footprint ${x.dmx_footprint??'—'}</b></div><div class="row"><span>Personnalité</span><b>${x.current_personality??'—'} / ${x.personality_count??'—'}</b></div><div class="row"><span>Capteurs / status</span><b>${(x.sensors||[]).length} / ${(x.status_messages||[]).length}</b></div><div class="row"><span>Fraîcheur</span><b>${x.online?'ONLINE':'STALE'} · ${x.age_s??'—'} s</b></div>
<div class="footer"><button class="btn" data-rdm-identify="1" data-uid="${esc(x.uid)}" data-transport="${esc(x.transport)}" data-universe="${x.universe??''}" data-scope="${esc(x.scope||'')}" ${canWrite?'':'disabled'}>Identify ON</button><button class="btn" data-rdm-identify="0" data-uid="${esc(x.uid)}" data-transport="${esc(x.transport)}" data-universe="${x.universe??''}" data-scope="${esc(x.scope||'')}" ${canWrite?'':'disabled'}>Identify OFF</button></div>
<div class="row"><input type="number" min="1" max="512" placeholder="Nouvelle adresse DMX" data-rdm-addr-field="${esc(x.uid)}" style="flex:1"><button class="btn" data-rdm-addr="${esc(x.uid)}" data-transport="${esc(x.transport)}" data-universe="${x.universe??''}" data-scope="${esc(x.scope||'')}" ${canWrite?'':'disabled'}>Définir</button></div>
<div class="row"><input type="number" min="1" placeholder="N° personnalité" data-rdm-pers-field="${esc(x.uid)}" style="flex:1"><button class="btn" data-rdm-pers="${esc(x.uid)}" data-transport="${esc(x.transport)}" data-universe="${x.universe??''}" data-scope="${esc(x.scope||'')}" ${canWrite?'':'disabled'}>Définir</button></div>
<div class="row"><select data-rdm-link-field="${esc(x.uid)}" style="flex:1">${gdtfPatches.length?gdtfPatches.map(p=>`<option value="${esc(p.patch_id)}" ${p.rdm_uid===x.uid?'selected':''}>${esc(p.name)}${p.rdm_uid===x.uid?' (déjà lié)':''}</option>`).join(''):'<option value="">Aucun patch GDTF — crée-en un dans GDTF</option>'}</select><button class="btn" data-rdm-link="${esc(x.uid)}" ${gdtfPatches.length?'':'disabled'}>Lier au patch</button></div>
</div>`).join('')||'<div class="muted">Aucun responder RDM/RDMnet observé.</div>'}</div>`;}
    if(key==='gdtf'){const e=this._state('gdtf_library_count','sensor.dmx_monitor_gdtf_library_count');const a=e?.attributes||{};const lib=a.library||[];const patches=a.patches||[];inner+=`<div class="card"><div class="title">GDTF — FIXTURE CONTROL</div><div class="module-grid"><div class="card"><div class="title">Profils importés</div><div class="big">${lib.length}</div></div><div class="card"><div class="title">Projecteurs patchés</div><div class="big">${patches.length}</div></div><div class="card"><div class="title">Sortie</div><div class="big ${a.control_enabled?'ok':'off'}">${a.control_enabled?'ARMÉE':'VERROUILLÉE'}</div></div></div><div class="notice">Déposer les fichiers .gdtf dans <b>/config/show_network_gdtf_inbox</b>, puis utiliser le service <b>gdtf_import</b>. Les Number créés pour Dimmer/Pan/Tilt/Zoom/etc. sont de vraies entités HA et peuvent être capturés par une scène.</div>${patches.map(x=>`<div class="card"><div class="title">${esc(x.name||x.patch_id)}</div><div class="row"><span>Patch</span><b>U${x.universe} @ ${x.address}</b></div><div class="row"><span>Mode</span><b>${esc(x.mode||'—')}</b></div><div class="row"><span>Transport</span><b>${esc(x.protocol||'—')} ${esc(x.host||'multicast')}</b></div><div class="row"><span>Attributs</span><b>${esc(Object.keys(x.attributes||{}).join(', ')||'—')}</b></div></div>`).join('')||'<div class="muted">Aucun projecteur GDTF patché.</div>'}</div>`;}
    if(key==='etc'){const e=this._state('etc_cem3_racks_total','sensor.dmx_monitor_etc_cem3_racks_total');const live=e?.attributes||{};const racks=live.racks||[];const cat=this._state('etc_sensor_catalog','sensor.dmx_monitor_etc_sensor_catalog')?.attributes?.sensors||[];inner+=`<div class="card"><div class="title">ETC SENSOR3 / CEM3 · LIVE</div><div class="big">${live.online??0}/${live.total??0}</div><div class="muted">HTTP CEM3 en lecture seule · ${esc(live.source_ip||'route système')}</div><div class="notice">Show Network utilise l’interface Web CEM3 en lecture seule : pages HTTP GET et requêtes de lecture fixes observées sur CEM3. Aucune modification de rack, niveau, preset ou configuration n’est envoyée.</div>${racks.map(r=>{const d=r.data||{},dm=r.dimmers||{};return `<div class="card"><div class="title">${esc(d.rack_name||r.host)} <span class="tag">${r.online?'ONLINE':'OFFLINE'}</span></div><div class="row"><span>IP</span><b>${esc(r.host||'—')}</b></div><div class="row"><span>Type / version</span><b>${esc(d.rack_type||'—')} · ${esc(d.software_version||'—')}</b></div><div class="row"><span>CPU</span><b>${d.cpu_temperature_c??'—'} °C</b></div><div class="row"><span>Secteur</span><b>${d.line_frequency_hz??'—'} Hz</b></div><div class="row"><span>Phases X/Y/Z</span><b>${d.phase_x_voltage_v??'—'} / ${d.phase_y_voltage_v??'—'} / ${d.phase_z_voltage_v??'—'} V</b></div><div class="row"><span>État / Panic</span><b>${esc(d.status||'—')} · ${esc(d.panic_state||'—')}</b></div><div class="row"><span>Erreurs</span><b>${r.errors_count??0}</b></div><div class="row"><span>Circuits visibles</span><b>${dm.circuits_total??'—'} · actifs ${dm.circuits_active??'—'}</b></div><div class="row"><span>Réponse</span><b>${r.response_ms??'—'} ms</b></div>${r.last_error?`<div class="notice">${esc(r.last_error)}</div>`:''}</div>`}).join('')}<div class="title">CAPACITÉS ETC</div>${cat.slice(0,80).map(x=>`<div class="row"><span>${esc(x.label_fr||x.name||x.key||'—')}</span><b>${x.live_supported?'LIVE':'DOCUMENTÉ'}</b></div>`).join('')}</div>`;}
    if(key==='security')inner+=this._securityHtml()+this._entityTable(['security_','osc_output','light_sync','projector_control'],'Les états de sécurité apparaîtront après chargement des entités.');
    if(key==='network'){const cfgState=this._state('show_network_config','sensor.dmx_monitor_show_network_config');const cfg=cfgState?.attributes||{};const yn=(k)=>cfgState?(cfg[k]===true?'Écouté':cfg[k]===false?'Désactivé':'Indisponible'):'État indisponible';const sw=this._state('switch_telemetry','sensor.dmx_monitor_switch_telemetry')?.attributes?.switches||[];
      const healthIssues=(()=>{
        const issues=[];
        const byMfr={};
        sw.forEach(x=>{if(!x.manufacturer)return;(byMfr[x.manufacturer]=byMfr[x.manufacturer]||[]).push(x)});
        for(const [mfr,group] of Object.entries(byMfr)){
          if(group.length<2)continue;
          const vlanCounts=[...new Set(group.map(x=>x.vlan_count).filter(v=>v!=null))];
          if(vlanCounts.length>1)issues.push(`${mfr} : nombre de VLAN incohérent entre switches (${vlanCounts.join(' vs ')}) — vérifier que c'est voulu.`);
          const models=[...new Set(group.map(x=>x.model).filter(Boolean))];
          if(models.length>1)issues.push(`${mfr} : modèle/version différents (${models.map(m=>`« ${m} »`).join(', ')}) — vérifier la cohérence firmware si ces switches doivent être identiques.`);
        }
        sw.forEach(x=>{if((x.ports_up??0)===0&&(x.interface_count??0)>0)issues.push(`${x.name||x.ip} : 0 interface UP sur ${x.interface_count} — switch isolé ou tout est débranché ?`)});
        return issues;
      })();
      inner+=`<div class="card"><div class="title">SWITCHES IDENTIFIÉS — TÉLÉMÉTRIE READ-ONLY</div>${sw.length?sw.map(x=>`<div class="row"><span>${esc(x.name||x.ip)} · ${esc(x.manufacturer||'—')}</span><span>${x.ports_up??0}/${x.interface_count??0} interfaces UP</span><span>${x.temperature_c??'—'} °C</span><span>${esc(x.ip||'—')}</span></div>`).join(''):'<div class="notice">Aucun switch n’a encore répondu avec une preuve suffisante. Luminex peut être reconnu par MAC enregistré, HTTP ou SNMP; la télémétrie de ports nécessite SNMP.</div>'}</div>
      <div class="card"><div class="title">CONTRÔLE DE COHÉRENCE (façon health-check)</div><div class="muted" style="margin-bottom:8px">Calculé uniquement à partir de la télémétrie déjà collectée ci-dessus — comparaison VLAN/modèle entre switches d'une même marque, ports totalement inactifs.</div>${healthIssues.length?healthIssues.map(i=>`<div class="notice">${esc(i)}</div>`).join(''):sw.length?'<div class="row"><span>Aucune incohérence détectée</span><span class="ok">OK</span></div>':'<div class="muted">Pas assez de switches identifiés pour comparer.</div>'}</div>
      <div class="card"><div class="title">CONFIGURATION RÉSEAU SHOW CONTROL</div>${cfgState?'':`<div class="notice">Capteur de configuration indisponible : aucun état activé/désactivé n'est supposé.</div>`}<div class="row"><span>DMX / Art-Net / sACN</span><b>${cfg.interface_dmx??'—'}</b></div><div class="row"><span>grandMA3 / MA-Net3</span><b>${cfg.interface_ma??'—'}</b></div><div class="row"><span>Dante</span><b>${cfg.interface_dante??'—'}</b></div><div class="row"><span>PTP</span><b>${cfg.interface_ptp??'—'}</b></div><div class="row"><span>Audio AES67/ST2110</span><b>${cfg.interface_audio??'—'}</b></div><div class="row"><span>Art-Net</span><b>${yn('dmx_artnet_enabled')}</b></div><div class="row"><span>sACN</span><b>${yn('dmx_sacn_enabled')}</b></div><div class="row"><span>Univers DMX</span><b>${cfg.universes??'—'}</b></div><div class="row"><span>MA-Net3</span><b>${yn('ma_enabled')}</b></div><div class="footer"><button class="btn primary" id="network-config">Modifier les interfaces / protocoles</button></div></div>`;
      const perfState=this._state('performance_level','sensor.dmx_monitor_performance_level');const perf=perfState?.attributes||{};
      inner+=`<div class="card"><div class="title">MODE DE PERFORMANCE</div><div class="notice">Adapte automatiquement l'intervalle de rafraîchissement et la découverte réseau selon la charge CPU/RAM de l'hôte Home Assistant. La réception DMX/sACN/Art-Net reste toujours indépendante et n'est jamais ralentie par ce mécanisme.</div><div class="row"><span>Profil configuré</span><b>${esc(perf.profile||'auto')}</b></div><div class="row"><span>Niveau actuel</span><b class="${perfState?.state==='normal'?'ok':'warn'}">${esc((perfState?.state||'normal').toUpperCase())}</b></div><div class="row"><span>Intervalle de télémétrie actuel</span><b>${perf.telemetry_interval_s??5} s</b></div><div class="row"><span>Découverte réseau</span><b>${perf.discovery_enabled===false?'RALENTIE (charge élevée)':'NORMALE'}</b></div><div class="row"><span>Sondage secondaire (switches/amplis)</span><b>${perf.secondary_polling===false?'RALENTI (charge élevée)':'NORMAL'}</b></div></div>`;
    }
    this.innerHTML=this._shell(inner);this.querySelector('#back')?.addEventListener('click',()=>this._setView('modules'));this._wireLocalGates();
    const map={incident_center:['show-network-incident-center-panel'],pre_show:['show-network-pre-show-panel'],show_snapshot:['show-network-snapshot-panel'],timecode:['show-network-timecode-panel'],doctor:['show-network-doctor-panel'],show_control:['show-control-panel'],dmx:['dmx-monitor-panel','enttec-panel','show-network-timecode-panel'],zones:['dmx-ha-zones-panel','dmx-ha-mapping-panel'],gdtf:['gdtf-panel'],osc:['control-sources-panel','osc-learn-panel','osc-mapping-panel','osc-output-panel','osc-source-profiles','punchlight-network-panel'],qlcplus:['qlcplus-panel'],rules:['show-network-rule-builder'],watchdog:['signal-watchdog-panel'],circuit_monitor:['dmx-circuit-monitor-panel'],power:['power-manager-panel','dmx-scene-bank-panel'],network:['show-network-topology-panel','show-network-discovery','show-network-fingerprint'],ma:['ma-inspector-panel'],inventory:['show-network-inventory'],builder:['show-network-ha-builder-panel'],brands:['show-network-brand-catalog'],reliability:['show-network-reliability-panel'],archive:['show-network-archive-panel']};
    if(map[key])this._mountPanels(map[key]);if(key==='security')this._wireSecurity();this.querySelector('#network-config')?.addEventListener('click',()=>this._openIntegrationConfig());this.querySelector('#open-network-config')?.addEventListener('click',()=>this._openIntegrationConfig());
    if(key==='amplifiers'){
      this.querySelector('#add-manual-amp')?.addEventListener('click',()=>{
        const host=this.querySelector('#amp-host')?.value.trim();
        if(!host){this._msg='Adresse IP obligatoire.';this.render();return;}
        this._call('manual_register_amplifier',{
          host,
          manufacturer:this.querySelector('#amp-mfr')?.value.trim(),
          model:this.querySelector('#amp-model')?.value.trim(),
          name:this.querySelector('#amp-name')?.value.trim(),
        });
      });
      this.querySelectorAll('[data-del-amp]').forEach(b=>b.addEventListener('click',()=>this._call('manual_remove_amplifier',{host:b.dataset.delAmp})));
    }
    if(key==='video'){this.querySelectorAll('[data-video-preview]').forEach(b=>b.addEventListener('click',()=>{this._videoPreviewKey=b.dataset.videoPreview;this._videoPreviewEntryId=b.dataset.entryId;this.render();}));this.querySelector('#video-preview-close')?.addEventListener('click',()=>{this._videoPreviewKey=null;this._videoPreviewEntryId=null;this.render();this._loadVideoIp(true);});
      this.querySelector('#toggle-projector-control')?.addEventListener('click',(e)=>{const on=e.currentTarget.dataset.on==='1';this._call('set_projector_control_enabled',{enabled:!on});});
      this.querySelectorAll('[data-proj-power]').forEach(b=>b.addEventListener('click',()=>this._call('projector_power',{host:b.dataset.host,port:+b.dataset.port,on:b.dataset.projPower==='1'})));
      this.querySelectorAll('[data-proj-mute]').forEach(b=>b.addEventListener('click',()=>this._call('projector_mute',{host:b.dataset.host,port:+b.dataset.port,mute:b.dataset.projMute==='1'})));
      this.querySelectorAll('[data-proj-input]').forEach(b=>b.addEventListener('click',()=>{const field=this.querySelector(`[data-proj-input-field="${b.dataset.host}"]`);const val=field?.value?.trim();if(!val)return;this._call('projector_input',{host:b.dataset.host,port:+b.dataset.port,input:val});}));
    }
    if(key==='rdm'){
      const rdmArgs=(b)=>({uid:b.dataset.uid,transport:b.dataset.transport,universe:b.dataset.universe?+b.dataset.universe:undefined,scope:b.dataset.scope||undefined});
      this.querySelector('#rdm-refresh')?.addEventListener('click',()=>this._call('rdm_refresh',{}));
      this.querySelectorAll('[data-rdm-identify]').forEach(b=>b.addEventListener('click',()=>this._call('rdm_identify',{...rdmArgs(b),value:b.dataset.rdmIdentify==='1'?1:0})));
      this.querySelectorAll('[data-rdm-addr]').forEach(b=>b.addEventListener('click',()=>{const f=this.querySelector(`[data-rdm-addr-field="${b.dataset.uid}"]`);const v=+f?.value;if(!v||v<1||v>512){this._msg='Adresse DMX invalide (1-512).';this.render();return;}this._call('rdm_set_start_address',{...rdmArgs(b),value:v});}));
      this.querySelectorAll('[data-rdm-pers]').forEach(b=>b.addEventListener('click',()=>{const f=this.querySelector(`[data-rdm-pers-field="${b.dataset.uid}"]`);const v=+f?.value;if(!v||v<1){this._msg='Numéro de personnalité invalide.';this.render();return;}this._call('rdm_set_personality',{...rdmArgs(b),value:v});}));
      this.querySelectorAll('[data-rdm-link]').forEach(b=>b.addEventListener('click',()=>{const f=this.querySelector(`[data-rdm-link-field="${b.dataset.rdmLink}"]`);const patch_id=f?.value;if(!patch_id)return;this._call('rdm_link_fixture',{uid:b.dataset.rdmLink,patch_id});}));
    }
  }
  _renderClassic(){
    const rows=[['LIGHT','DMX / sACN / Art-Net',this._value('network_packets_observed','—')],['AUDIO','Dante / AES67 / ST2110 / AVB',this._value('audio_protocols_active','—')],['NETWORK','Interfaces actives',this._value('network_interfaces_up','—')],['MA','Stations actives',this._value('ma_live_stations','—')]];
    const cards=rows.map(r=>`<div class="card"><div class="title">${r[0]}</div><div class="big">${r[2]}</div><div class="muted">${r[1]}</div></div>`).join('');
    this.innerHTML=this._shell(`<button class="btn back" id="back">← PRO</button><div class="top"><div><div class="brand">SHOW NETWORK / CLASSIC</div><div class="muted">Vue diagnostic synthétique</div></div></div><div class="classic-grid" style="margin-top:12px">${cards}</div>${this._securityHtml()}<div class="footer"><button class="btn primary" id="modules">Modules & configuration</button></div>`);this._wireSecurity();this.querySelector('#back')?.addEventListener('click',()=>this._setView('pro'));this.querySelector('#modules')?.addEventListener('click',()=>this._setView('modules'));
  }
  _renderArchive(){
    const a=this._state('journal_archive','sensor.dmx_monitor_journal_archive')?.attributes||{};const events=(a.recent_events||[]).slice().reverse().slice(0,40);const cb=a.configuration_backups||{},dg=a.diagnostics||{},fr=a.flight_recorder||{};const incident=fr.last_incident||null;const sev=fr.severity_counts||{};
    this.innerHTML=this._shell(`<button class="btn back" id="back">← PRO</button><div class="top"><div><div class="brand">PERSISTANCE · BACKUPS · DIAGNOSTICS</div><div class="muted">Sauvegarde cohérente des données Show Network, journal et bundle support expurgé des secrets</div></div></div><div class="card" style="margin-top:12px"><div class="title">CONFIGURATION SHOW NETWORK</div><div class="row"><span>Fichiers persistants détectés</span><b>${cb.files_present??0}/${cb.files_known??0}</b></div><div class="row"><span>Points de sauvegarde</span><b>${cb.backup_count??0}</b></div><div class="row"><span>Dernière sauvegarde</span><span>${esc(cb.last_backup_success||'—')}</span></div><div class="row"><span>Dernière restauration</span><span>${esc(cb.last_restore_success||'—')}</span></div><div class="notice">Le ZIP portable contient les règles, mappings, zones, scènes DMX, patch GDTF, cibles OSC/MIDI, Show Control, Power Manager, inventaire corrigé et HA Builder. <b>Les secrets sont exclus.</b> Une restauration exige le déverrouillage sécurité et recharge l’intégration.</div><div class="footer"><button class="btn primary" id="config-backup">Sauvegarder configuration</button><button class="btn" id="diag">Bundle diagnostics</button></div><input id="restore-path" style="width:100%;box-sizing:border-box;margin-top:10px;padding:9px;background:#0b0d10;color:#eee;border:1px solid #39414a;border-radius:7px" placeholder="/config/show_network_backups/show_network_config_....zip"><button class="btn" id="restore" style="margin-top:8px;border-color:#8b3f45">Restaurer le ZIP</button></div><div class="card" style="margin-top:12px"><div class="title">JOURNAL / SHOW TIMELINE</div><div class="row"><span>Destination</span><span>${esc(a.configured_destination??a.destination??'—')}</span></div><div class="row"><span>Fichiers</span><span>${a.files??'—'}</span></div><div class="row"><span>Taille</span><span>${a.bytes??0} octets</span></div><div class="row"><span>Rétention</span><span>${a.retention_days??'—'} jours</span></div><div class="footer"><button class="btn" id="backup">Backup journal</button><button class="btn" id="export">Exporter journal ZIP</button></div></div><div class="card" style="margin-top:12px"><div class="title">DIAGNOSTICS</div><div class="row"><span>Dernier bundle</span><span>${esc(dg.last_path||'—')}</span></div><div class="row"><span>Dernière réussite</span><span>${esc(dg.last_success||'—')}</span></div><div class="muted">État runtime, ressources et persistance; champs sensibles expurgés; pas de payload DMX brut.</div></div><div class="card" style="margin-top:12px"><div class="title">ÉVÉNEMENTS RÉCENTS</div>${events.length?events.map(e=>`<div class="timeline-item"><b>${esc(e.event||'—')}</b> · ${esc(e.kind||'general')}<div class="muted">${esc(e.ts||'—')} ${e.data&&Object.keys(e.data).length?'· '+esc(JSON.stringify(e.data)):''}</div></div>`).join(''):'<div class="muted" style="margin-top:10px">Aucun événement en mémoire depuis le démarrage.</div>'}</div>`);
    this.querySelector('#back')?.addEventListener('click',()=>this._setView('pro'));this.querySelector('#backup')?.addEventListener('click',()=>this._call('archive_backup',{}));this.querySelector('#export')?.addEventListener('click',()=>this._call('archive_export',{}));this.querySelector('#config-backup')?.addEventListener('click',()=>this._call('config_backup_create',{reason:'ui'}));this.querySelector('#diag')?.addEventListener('click',()=>this._call('diagnostics_export',{}));this.querySelector('#restore')?.addEventListener('click',()=>{const source=this.querySelector('#restore-path')?.value?.trim();if(source)this._call('config_backup_restore',{source});});
  }
  _renderTimeline(){
    const a=this._state('journal_archive','sensor.dmx_monitor_journal_archive')?.attributes||{};const events=(a.recent_events||[]).slice().reverse();
    this.innerHTML=this._shell(`<button class="btn back" id="back">← PRO</button><div class="top"><div><div class="brand">SHOW TIMELINE</div><div class="muted">Événements récents observés par Show Network</div></div></div><div class="card" style="margin-top:12px"><div class="timeline-item"><b>Journal actif</b><div class="muted">${a.timeline_file??'—'}</div></div>${events.length?events.map(e=>`<div class="timeline-item"><b>${esc(e.event||'—')}</b> · ${esc(e.kind||'general')}<div class="muted">${esc(e.ts||'—')} ${e.data&&Object.keys(e.data).length?'· '+esc(JSON.stringify(e.data)):''}</div></div>`).join(''):'<div class="muted" style="margin-top:12px">Aucun événement en mémoire depuis le démarrage.</div>'}</div>`);this.querySelector('#back')?.addEventListener('click',()=>this._setView('pro'));
  }
  render(){const view=this._view;if(!this._skipCapture){this._uiDetails[view]=snCaptureDetails(this);this._uiScroll[view]=this.scrollTop}else this._skipCapture=false;let out;if(view==='classic')out=this._renderClassic();else if(view==='archive')out=this._renderArchive();else if(view==='timeline')out=this._renderTimeline();else if(view==='modules')out=this._renderModules();else if(view.startsWith('module:'))out=this._renderModule(view.slice(7));else out=this._renderPro();snRestoreDetails(this,this._uiDetails[view]);if(this._uiScroll[view]!=null)this.scrollTop=this._uiScroll[view];return out;}
}
snDefine('show-network-pro-dashboard',ShowNetworkProDashboard);


/* ===== show-network-reliability-panel.js ===== */
class ShowNetworkReliabilityPanel extends HTMLElement {
  setConfig(c){this._config=c||{};}
  set hass(h){this._hass=h;this.render();}
  async _call(service,data={}){this._message='Action en cours…';this.render();try{await this._hass.callService('dmx_monitor',service,data);this._message=`${service}: exécuté`; }catch(e){this._message=`Erreur ${service}: ${e?.message||e}`;}this.render();}
  render(){const h=this._hass;if(!h)return;const st=h.states?.['sensor.dmx_monitor_chaos_status'];const cap=h.states?.['sensor.dmx_monitor_network_capacity_utilization'];const d=h.states?.['sensor.dmx_monitor_dmx_universes']?.attributes?.network_health||{};const cfg=Object.values(h.states||{}).find(x=>x.attributes&&('chaos_enabled' in x.attributes))?.attributes||{};const enabled=!!cfg.chaos_enabled;const badge=(n)=>n>0?'⚠️':'🟢';this.innerHTML=`<style>:host{display:block;font-family:system-ui}.box{padding:14px;border:1px solid #30363d;border-radius:12px;background:#111519;color:#eee}.title{font-weight:800}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:10px}.b{padding:9px;border:1px solid #39414a;border-radius:8px;background:#181d22;color:#eee;cursor:pointer}.b:disabled{opacity:.45;cursor:not-allowed}.danger{border-color:#a85b5b}.small{font-size:11px;color:#929ba4}.msg{margin-top:10px;padding:8px;border:1px solid #39414a;border-radius:8px;font-size:11px}.health{margin-top:12px;padding:10px;border:1px solid #30363d;border-radius:9px;background:#151a1f}.row{display:flex;justify-content:space-between;gap:10px;padding:3px 0}.ok{color:#68df9a}.warn{color:#e5bf6b}</style><div class="box"><div class="title">RELIABILITY / NETWORK</div><div class="small">État: ${st?.state||'inactive'} · capacité: ${cap?.state||'—'}% · tests diagnostic <b class="${enabled?'ok':'warn'}">${enabled?'ACTIVÉS':'DÉSACTIVÉS'}</b></div><div class="health"><div class="row"><span>sACN queue</span><b>${badge(d.sacn_queue_drops||0)} ${d.sacn_queue_depth||0}/${d.queue_size||'—'} · drops ${d.sacn_queue_drops||0}</b></div><div class="row"><span>Art-Net queue</span><b>${badge(d.artnet_queue_drops||0)} ${d.artnet_queue_depth||0}/${d.queue_size||'—'} · drops ${d.artnet_queue_drops||0}</b></div><div class="row"><span>sACN reconnexions</span><b>${d.sacn_restarts||0}</b></div><div class="row"><span>Art-Net reconnexions</span><b>${d.artnet_restarts||0}</b></div></div><div class="grid">${enabled?`<button class="b danger" id="loss">Simuler perte watchdog</button><button class="b" id="restore">Restaurer signal</button><button class="b" id="ptp">PTP dérive +1 ms</button><button class="b" id="clear">Arrêter simulation</button>`:`<button class="b" id="enable">Activer les tests diagnostic (redémarre Show Network)</button><button class="b" disabled>Les simulations sont protégées</button>`}</div>${this._message?`<div class="msg">${esc(this._message)}</div>`:''}</div>`;this.querySelector('#enable')?.addEventListener('click',()=>this._call('set_module_enabled',{module:'diagnostics',enabled:true}));this.querySelector('#loss')?.addEventListener('click',()=>this._call('chaos_signal_loss'));this.querySelector('#restore')?.addEventListener('click',()=>this._call('chaos_signal_restore'));this.querySelector('#ptp')?.addEventListener('click',()=>this._call('chaos_ptp_drift',{offset_ms:1}));this.querySelector('#clear')?.addEventListener('click',()=>this._call('chaos_clear'));}
}
snDefine('show-network-reliability-panel',ShowNetworkReliabilityPanel);


/* ===== signal-watchdog-panel.js ===== */
/**
 * Show Network — Signal Watchdog panel.
 * Read-only status view; rule creation is intentionally delegated to the
 * integration Rule Builder so all HA actions use the same safety path.
 */
class SignalWatchdogPanel extends HTMLElement {
  set hass(h){this._hass=h;this.render()}
  render(){if(!this._hass)return;const st=Object.values(this._hass.states||{}).find(x=>x.entity_id.includes('watchdog_rules'));const rules=st?.attributes?.rules||[];this.innerHTML=`<style>:host{display:block}.box{padding:15px;border:1px solid #30363d;border-radius:12px;background:#111519;color:#eee}.help{padding:10px;border-left:3px solid #2586c8;background:#151a1f;font-size:11px;line-height:1.5}.row{display:grid;grid-template-columns:2fr 1fr 1fr 1fr 1fr;gap:8px;padding:9px 0;border-bottom:1px solid #293039;font-size:11px}.ok{color:#68df9a}.warn{color:#e5bf6b}.bad{color:#ef7777}</style><div class="box"><h3>SIGNAL WATCHDOGS</h3><div class="help"><b>À quoi ça sert ?</b> Vérifie qu'un flux attendu continue d'arriver (ex. sACN U1). Après le délai de perte, il peut déclencher une action HA; après retour stable, une action de récupération. <b>Il ne surveille pas les valeurs des circuits</b> et n'envoie aucun DMX. Pour des circuits précis, utilise DMX Circuit Monitor.</div>${rules.length?`<div class="row"><b>Nom</b><b>Signal</b><b>Âge</b><b>Délai perte</b><b>État</b></div>${rules.map(r=>`<div class="row"><span>${esc(r.name||'Watchdog')}</span><span>${esc(r.protocol)} U${r.universe}${r.source?' · '+esc(r.source):''}</span><span>${r.last_signal_age_s??'—'} s</span><span>${r.loss_timeout_s??'—'} s</span><b class="${r.active?'bad':r.signal_ok?'ok':'warn'}">${r.active?'PERDU':r.signal_ok?'OK':'ATTENTE'}</b></div>`).join('')}`:'<div class="help">Aucun Signal Watchdog configuré. Active/configure le Watchdog dans les options générales de l’intégration.</div>'}</div>`}
}
snDefine('signal-watchdog-panel', SignalWatchdogPanel);


/* ===== topology-panel.js ===== */
class ShowNetworkTopologyPanel extends HTMLElement {
  setConfig(config){this.config=config||{};this._vlan='';this._iface='';}
  set hass(hass){this._hass=hass;this.render();}
  _state(suffix){return Object.values(this._hass?.states||{}).find(x=>x.entity_id.endsWith(`_${suffix}`));}
  render(){
    if(!this._hass)return;
    const states=Object.values(this._hass.states||{});
    const topoState=states.find(s=>s.attributes&&s.attributes.topology);
    const topo=topoState?.attributes?.topology||{nodes:[],links:[]};
    const nodes=topo.nodes||[],links=topo.links||[];
    const dm=this._state('show_network_devices')?.attributes||{}; const devices=dm.devices||[];
    const swState=this._state('switch_telemetry'); const switches=swState?.attributes?.switches||[];
    const portHealth=new Map(); let topoWarn=0,topoCrit=0;
    switches.forEach(sw=>(sw.ports||[]).forEach(p=>{const util=(p.speed_mbps&&p.rx_mbps!=null&&p.tx_mbps!=null)?Math.max(p.rx_mbps,p.tx_mbps)/p.speed_mbps*100:null;const errs=(Number(p.rx_errors)||0)+(Number(p.tx_errors)||0);const level=!p.up?'down':util!=null&&util>=85?'critical':util!=null&&util>=70?'warning':errs>0?'error':'ok';if(level==='critical'||level==='error'||level==='down')topoCrit++;else if(level==='warning')topoWarn++;const sid=String(sw.topology_node_id||`switch:${sw.interface||''}:${sw.ip||sw.name||''}`);for(const k of [p.index,p.name])if(k!=null)portHealth.set(`${sid}|${String(k)}`,level);}));
    const deviceById=new Map(); devices.forEach(d=>{deviceById.set(String(d.id),d);(d.topology_nodes||[]).forEach(n=>deviceById.set(String(n),d));});
    const vlans=[...new Set([...devices.map(d=>d.vlan),...links.map(l=>l.vlan)].filter(v=>v!==null&&v!==undefined&&v!==''))].sort((a,b)=>String(a).localeCompare(String(b),undefined,{numeric:true}));
    const ifaces=[...new Set([...devices.map(d=>d.interface),...switches.map(s=>s.interface)].filter(Boolean))].sort();
    const visibleDevice=d=>(!this._vlan||String(d.vlan)===this._vlan)&&(!this._iface||String(d.interface||'')===this._iface);
    const health=n=>String(n.health||'unknown').toLowerCase(), hclass=n=>health(n)==='stale'?'warn':health(n)==='error'?'bad':'ok';
    const sortedNodes=nodes.slice().sort((a,b)=>{const da=deviceById.get(String(a.id))||{},db=deviceById.get(String(b.id))||{};const fa=da.monitor_mode==='monitor'?0:1,fb=db.monitor_mode==='monitor'?0:1;return fa-fb||String(da.name||a.label||a.id).localeCompare(String(db.name||b.label||b.id));});
    const nodeHtml=sortedNodes.slice(0,180).map(n=>{const d=deviceById.get(String(n.id))||{};if(Object.keys(d).length&&!visibleDevice(d))return '';const proto=(d.protocols||[]).slice(0,4).join(' · ');const fav=d.monitor_mode==='monitor'?'★ ':'';return `<button class="tnode ${hclass(n)}" data-node="${esc(n.id)}"><b>${fav}${esc(d.name||n.label||n.id||'Équipement')}</b><span>${esc(d.ip||n.ip||'IP —')}</span><small>${esc(d.manufacturer||'')} ${esc(d.model||'')}</small><small>${esc(proto||n.type||'')}</small></button>`}).join('');
    const linkHtml=links.filter(l=>!this._vlan||String(l.vlan)===this._vlan).slice(0,220).map(l=>{const lh=portHealth.get(`${String(l.source)}|${String(l.source_port)}`)||'ok';return `<div class="link l${lh}"><b>${esc(l.source)}</b><span>→</span><b>${esc(l.target)}</b><span>${l.source_port?`local ${esc(l.source_port)}`:''}${l.target_port?` · distant ${esc(l.target_port)}`:''}</span><span>${l.vlan!=null?`VLAN ${esc(l.vlan)} · `:''}${l.link_speed_mbps?`${esc(l.link_speed_mbps)} Mb/s`:''}</span><span>${esc(l.protocol||'preuve')} · ${Math.round((l.confidence||0)*100)}%</span></div>`}).join('');
    const switchHtml=switches.filter(sw=>!this._iface||String(sw.interface||'')===this._iface).map((sw,si)=>{const ports=sw.ports||[];const neigh=new Map((sw.lldp_neighbors||[]).map(n=>[String(n.local_port_index),n]));return `<div class="switch"><div class="swhead"><div><b>${esc(sw.name||sw.ip||'Switch')}</b><small>${esc(sw.manufacturer||'')} ${esc(sw.model||'')}</small></div><div><b>${sw.ports_up||0}/${ports.length}</b><small>ports UP</small></div></div><div class="portgrid">${ports.map(p=>{const n=neigh.get(String(p.index));const util=(p.speed_mbps&&p.rx_mbps!=null&&p.tx_mbps!=null)?Math.max(p.rx_mbps,p.tx_mbps)/p.speed_mbps*100:null;const errs=(Number(p.rx_errors)||0)+(Number(p.tx_errors)||0);const cls=!p.up?'pdown':util!=null&&util>=85?'pcrit':util!=null&&util>=70?'pwarn':errs>0?'perr':'pup';return `<button class="port ${cls}" data-switch="${si}" data-port="${esc(p.index)}"><b>${esc(p.name||p.index)}</b><small>${p.up?'UP':'DOWN'}${p.speed_mbps?` · ${esc(p.speed_mbps)}M`:''}</small><small>${(p.rx_mbps!=null||p.tx_mbps!=null)?`↓ ${esc(p.rx_mbps??'—')} · ↑ ${esc(p.tx_mbps??'—')} Mb/s`:esc(n?.remote_system||p.alias||'—')}</small></button>`}).join('')||'<span class="muted">Aucun port SNMP disponible.</span>'}</div></div>`}).join('');
    this.innerHTML=`<style>:host{display:block;color:#eef1f4}.box{padding:14px;border:1px solid #30363d;border-radius:12px;background:#111519}.summary,.filters{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 14px}.pill,select{padding:6px 9px;border:1px solid #39414a;border-radius:999px;font-size:10px;background:#171c21;color:#eef1f4}.nodes{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:8px}.tnode{text-align:left;padding:10px;background:#171c21;color:#eee;border:1px solid #39424c;border-radius:9px;cursor:pointer}.tnode span,.tnode small,.swhead small,.port small{display:block;color:#929ba4;margin-top:3px}.tnode.ok{border-left:4px solid #68df9a}.tnode.warn{border-left:4px solid #e5bf6b}.tnode.bad{border-left:4px solid #ef7777}.switches{display:grid;gap:10px;margin:12px 0}.switch{border:1px solid #303841;border-radius:10px;padding:10px;background:#14191e}.swhead{display:flex;justify-content:space-between;gap:12px}.portgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(115px,1fr));gap:6px;margin-top:9px}.port{text-align:left;border-radius:7px;padding:7px;background:#171c21;color:#eee;border:1px solid #39424c;cursor:pointer}.port.pup{border-left:4px solid #68df9a}.port.pwarn{border-left:4px solid #e5bf6b}.port.pcrit,.port.perr{border-left:4px solid #ef7777}.port.pdown{border-left:4px solid #59616a;opacity:.72}.links{margin-top:12px}.link{display:grid;grid-template-columns:1fr 24px 1fr repeat(3,auto);gap:8px;padding:7px 8px;border-bottom:1px solid #252c32;font-size:10px;border-left:3px solid transparent}.link.lwarning{border-left-color:#e5bf6b;background:#241f13}.link.lcritical,.link.lerror,.link.ldown{border-left-color:#ef7777;background:#261617}.detail{margin-top:12px;padding:12px;border:1px solid #39414a;border-radius:9px;background:#151a1f}.row{display:flex;justify-content:space-between;gap:10px;padding:5px 0;border-bottom:1px solid #252c32;font-size:11px}.muted{color:#8f99a3;font-size:10px}@media(max-width:700px){.link{grid-template-columns:1fr 20px 1fr}.link span:nth-last-child(-n+3){display:none}}</style><div class="box"><b>TOPOLOGIE LIVE</b><div class="summary"><span class="pill">${nodes.length} nœuds</span><span class="pill">${links.length} liaisons</span><span class="pill">${devices.length} équipements</span><span class="pill">${switches.length} switches</span><span class="pill">⚠ ${topoWarn} avert.</span><span class="pill">✕ ${topoCrit} critique(s)</span></div><div class="filters"><select id="iface"><option value="">Toutes les interfaces</option>${ifaces.map(x=>`<option ${this._iface===String(x)?'selected':''}>${esc(x)}</option>`).join('')}</select><select id="vlan"><option value="">Tous les VLAN</option>${vlans.map(x=>`<option value="${esc(x)}" ${this._vlan===String(x)?'selected':''}>VLAN ${esc(x)}</option>`).join('')}</select></div><h4>Switches & ports</h4><div class="switches">${switchHtml||'<div class="muted">Aucune télémétrie switch disponible.</div>'}</div><h4>Équipements</h4><div class="nodes">${nodeHtml||'<span>Aucun nœud observé avec ces filtres.</span>'}</div><div id="node-detail"></div><h4>Liaisons prouvées</h4><div class="links">${linkHtml||'<div class="muted">Aucune liaison avec ces filtres.</div>'}</div></div>`;
    this.querySelector('#iface').onchange=e=>{this._iface=e.target.value;this.render();}; this.querySelector('#vlan').onchange=e=>{this._vlan=e.target.value;this.render();};
    this.querySelectorAll('[data-node]').forEach(b=>b.onclick=()=>{const id=b.dataset.node;const n=nodes.find(x=>String(x.id)===id)||{};const d=deviceById.get(id)||{};const related=links.filter(l=>String(l.source)===id||String(l.target)===id);this.querySelector('#node-detail').innerHTML=`<div class="detail"><b>${esc(d.name||n.name||id)}</b><div class="row"><span>IP / MAC</span><b>${esc(d.ip||n.ip||'—')} · ${esc(d.mac||'—')}</b></div><div class="row"><span>Constructeur / modèle</span><b>${esc(d.manufacturer||'—')} · ${esc(d.model||'—')}</b></div><div class="row"><span>Interface / VLAN</span><b>${esc(d.interface||'—')} · ${esc(d.vlan??'—')}</b></div><div class="row"><span>Switch / port</span><b>${esc(d.switch_name||'—')} · ${esc(d.switch_port||'—')}</b></div><div class="row"><span>Protocoles</span><b>${esc((d.protocols||[]).join(', ')||'—')}</b></div><div class="row"><span>Preuves</span><b>${esc((d.evidence_sources||[]).join(', ')||'—')}</b></div><div class="row"><span>Liaisons observées</span><b>${related.length}</b></div>${related.length?related.map(l=>`<div class="row"><span>${esc(String(l.source)===id?l.target:l.source)}</span><b>${esc(l.source_port||'—')} ↔ ${esc(l.target_port||'—')} · ${l.vlan!=null?`VLAN ${esc(l.vlan)} · `:''}${esc(l.protocol||'preuve')} ${Math.round((l.confidence||0)*100)}%</b></div>`).join(''):'<div class="muted">Aucun chemin physique prouvé.</div>'}</div>`;});
    this.querySelectorAll('[data-port]').forEach(b=>b.onclick=()=>{const sw=switches[Number(b.dataset.switch)]||{};const p=(sw.ports||[]).find(x=>String(x.index)===b.dataset.port)||{};const n=(sw.lldp_neighbors||[]).find(x=>String(x.local_port_index)===b.dataset.port);this.querySelector('#node-detail').innerHTML=`<div class="detail"><b>${esc(sw.name||sw.ip||'Switch')} · ${esc(p.name||p.index||'port')}</b><div class="row"><span>État</span><b>${p.up?'UP':'DOWN'}</b></div><div class="row"><span>Vitesse</span><b>${p.speed_mbps?`${esc(p.speed_mbps)} Mb/s`:'—'}</b></div><div class="row"><span>Alias</span><b>${esc(p.alias||'—')}</b></div><div class="row"><span>Trafic RX / TX</span><b>${p.rx_mbps!=null||p.tx_mbps!=null?`${esc(p.rx_mbps??'—')} / ${esc(p.tx_mbps??'—')} Mb/s`:'En attente de 2 mesures'}</b></div><div class="row"><span>Erreurs RX / TX</span><b>${esc(p.rx_errors??'—')} / ${esc(p.tx_errors??'—')}</b></div><div class="row"><span>Voisin LLDP</span><b>${esc(n?.remote_system||'—')}</b></div><div class="row"><span>Port distant</span><b>${esc(n?.remote_port||'—')}</b></div><div class="row"><span>Interface de découverte</span><b>${esc(sw.interface||'—')}</b></div></div>`;});
  }
}
snDefine('show-network-topology-panel', ShowNetworkTopologyPanel);

class ShowNetworkSnapshotPanel extends HTMLElement {
  set hass(v){this._hass=v;this.render();} _state(){return Object.values(this._hass?.states||{}).find(x=>x.attributes?.friendly_name?.includes('Référence spectacle'))||this._hass?.states?.['sensor.dmx_monitor_show_snapshot'];}
  async _call(service,data){try{await this._hass.callService('dmx_monitor',service,data||{});}catch(e){alert(String(e));}}
  render(){if(!this._hass)return;const st=this._state(),a=st?.attributes||{},diff=a.differences||[],names=a.snapshots||[];this.innerHTML=`<style>:host{display:block;color:#eef1f4}.box{padding:14px;border:1px solid #30363d;border-radius:12px;background:#111519}.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}input,select,button{background:#181d22;color:#eef1f4;border:1px solid #3a434c;border-radius:7px;padding:8px}button{cursor:pointer}.big{font-size:25px;font-weight:800}.ok{color:#68df9a}.warn{color:#e5bf6b}.muted{color:#8f99a3;font-size:10px}.d{margin-top:7px;padding:8px;border:1px solid #30363d;border-radius:7px}</style><div class="box"><div class="row"><div><b>RÉFÉRENCE SPECTACLE</b><div class="muted">Capture des faits observés : appareils, sources DMX et identité PTP disponible.</div></div><div style="margin-left:auto" class="big ${a.state==='match'?'ok':'warn'}">${esc(String(a.state||st?.state||'NO REFERENCE').toUpperCase())}</div></div><div class="row" style="margin-top:12px"><input id="nm" placeholder="Nom du spectacle"><button id="save">Enregistrer l’état actuel</button><select id="sel"><option value="">Références…</option>${names.map(n=>`<option ${n===a.active?'selected':''}>${esc(n)}</option>`).join('')}</select><button id="act">Activer</button><button id="del">Supprimer</button></div><div class="muted" style="margin-top:10px">Active : ${esc(a.active||'aucune')} · ${a.warning_count||0} écart(s) important(s)</div><div class="row" style="margin-top:8px"><span class="d">Appareils ${a.reference_counts?.devices||0} → ${a.current_counts?.devices||0}</span><span class="d">DMX ${a.reference_counts?.dmx_sources||0} → ${a.current_counts?.dmx_sources||0}</span><span class="d">Switches ${a.reference_counts?.switches||0} → ${a.current_counts?.switches||0}</span><span class="d">Dante subs ${a.reference_counts?.dante_subscriptions||0} → ${a.current_counts?.dante_subscriptions||0}</span></div>${diff.map(x=>`<div class="d"><b>${x.severity==='warning'?'⚠':'i'} ${esc(x.kind)}</b> — ${esc(x.label||'')}${x.field?' · '+esc(x.field):''}${x.reference!==undefined&&typeof x.reference!=='object'?' · '+esc(String(x.reference))+' → '+esc(String(x.current)):''}</div>`).join('')||'<div class="d">Aucun écart observé avec la référence active.</div>'}</div>`;this.querySelector('#save').onclick=()=>{const n=this.querySelector('#nm').value.trim();if(n)this._call('show_snapshot_create',{name:n});};this.querySelector('#act').onclick=()=>{const n=this.querySelector('#sel').value;if(n)this._call('show_snapshot_activate',{name:n});};this.querySelector('#del').onclick=()=>{const n=this.querySelector('#sel').value;if(n&&confirm(`Supprimer ${n} ?`))this._call('show_snapshot_delete',{name:n});};}}
snDefine('show-network-snapshot-panel', ShowNetworkSnapshotPanel);

class ShowNetworkDoctorPanel extends HTMLElement {
  setConfig(config){this.config=config||{};}
  set hass(hass){this._hass=hass;this.render();}
  _state(suffix){return Object.values(this._hass?.states||{}).find(x=>x.entity_id.endsWith(`_${suffix}`));}
  render(){if(!this._hass)return;const st=this._state('show_network_doctor');const a=st?.attributes||{};const checks=a.checks||[];const counts=a.counts||{};const devices=this._state('show_network_devices')?.attributes?.devices||[];const cls=x=>x==='error'?'bad':x==='warning'?'warn':x==='ok'?'ok':'info';const icon=x=>x==='error'?'✕':x==='warning'?'⚠':x==='ok'?'✓':'i';this.innerHTML=`<style>:host{display:block;color:#eef1f4}.box{padding:14px;border:1px solid #30363d;border-radius:12px;background:#111519}.head{display:flex;justify-content:space-between;gap:12px;align-items:center}.overall{font-size:28px;font-weight:800}.ok{color:#68df9a}.warn{color:#e5bf6b}.bad{color:#ef7777}.info{color:#8f99a3}.summary{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}.pill{padding:6px 9px;border:1px solid #39414a;border-radius:999px;font-size:10px}.check{border:1px solid #30363d;border-left-width:4px;border-radius:9px;margin-top:8px;background:#151a1f}.check.ok{border-left-color:#68df9a}.check.warn{border-left-color:#e5bf6b}.check.bad{border-left-color:#ef7777}.check.info{border-left-color:#68737d}.check summary{cursor:pointer;padding:11px;display:flex;gap:10px;align-items:center}.body{padding:0 12px 12px;font-size:11px;color:#b8c0c7}.evidence{font-family:ui-monospace,monospace;white-space:pre-wrap;word-break:break-word;background:#0b0d10;padding:8px;border-radius:7px;margin-top:8px}.devs{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:7px;margin-top:8px}.dev{border:1px solid #30363d;border-radius:7px;padding:8px}.muted{color:#8f99a3;font-size:10px}</style><div class="box"><div class="head"><div><b>SHOW NETWORK DOCTOR</b><div class="muted">Diagnostic read-only calculé uniquement avec les données réellement observées.</div></div><div class="overall ${cls(a.overall||st?.state)}">${esc(String(a.overall||st?.state||'unknown').toUpperCase())}</div></div><div class="summary"><span class="pill">✓ ${counts.ok||0}</span><span class="pill">i ${counts.info||0}</span><span class="pill">⚠ ${counts.warning||0}</span><span class="pill">✕ ${counts.error||0}</span><span class="pill">${devices.length} équipements</span></div>${checks.map(c=>`<details class="check ${cls(c.status)}" ${c.status==='warning'||c.status==='error'?'open':''}><summary><b>${icon(c.status)}</b><b>${esc(c.title||c.id)}</b><span class="muted">${esc(c.detail||'')}</span></summary><div class="body">${this._related(c,devices)}<div class="evidence">${esc(JSON.stringify(c.evidence||{},null,2))}</div></div></details>`).join('')||'<div class="muted">Diagnostic indisponible.</div>'}</div>`;}
  _related(c,devices){const explicit=new Set(c.evidence?.related_device_ids||[]);const ev=JSON.stringify(c.evidence||{});const found=devices.filter(d=>explicit.has(d.id)||(d.ip&&ev.includes(String(d.ip)))||(d.id&&ev.includes(String(d.id)))).slice(0,12);if(!found.length)return '<div class="muted">Aucun équipement précis ne peut être relié à cette preuve sans supposition.</div>';return `<div class="devs">${found.map(d=>`<div class="dev"><b>${esc(d.name||d.id)}</b><div>${esc(d.ip||'IP —')}</div><div class="muted">${esc(d.switch_name||'switch —')} · port ${esc(d.switch_port||'—')} · ${esc((d.protocols||[]).join(', ')||'protocole —')}</div></div>`).join('')}</div>`;}
}
snDefine('show-network-doctor-panel', ShowNetworkDoctorPanel);


/* ===== dmx-ha-zones-panel.js ===== */
class DmxHaZonesPanel extends HTMLElement {
  set hass(h){this._hass=h;this.render()}
  _state(){return Object.values(this._hass?.states||{}).find(x=>x.entity_id.endsWith('dmx_ha_zones_total'))}
  _zones(){return this._state()?.attributes?.zones||[]}
  async _call(service,data){try{await this._hass.callService('dmx_monitor',service,data);this._msg='Enregistré';setTimeout(()=>this.render(),400);setTimeout(()=>this.render(),1500)}catch(e){this._msg=`Erreur: ${e?.message||e}`;this.render()}}
  _entities(){return Object.values(this._hass.states).filter(s=>s.entity_id.startsWith('light.')).map(s=>({id:s.entity_id,name:s.attributes.friendly_name||s.entity_id}))}
  render(){
    if(!this._hass)return;
    const zones=this._zones(), lights=this._entities();
    this.innerHTML=`<style>
      :host{display:block;background:#090b0e;color:#eee;font-family:Inter,system-ui,sans-serif;padding:16px}h2{margin:0 0 4px;font-size:20px}.sub{color:#89929d;font-size:11px;margin-bottom:14px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:12px}.card{background:#11151a;border:1px solid #293038;border-radius:10px;padding:14px}.head{display:flex;justify-content:space-between;gap:8px;align-items:center}.name{font-weight:700}.pill{font-size:10px;border:1px solid #38414b;border-radius:20px;padding:4px 8px}.on{border-color:#2e9b64;color:#7ee2aa}.off{color:#9aa3ad}.meta{font-size:11px;color:#a9b0b8;margin:8px 0}.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:9px}.row label{font-size:10px;color:#8f99a3;display:flex;flex-direction:column;gap:4px;flex:1;min-width:110px}input,select{background:#0b0e12;color:#eee;border:1px solid #333b44;border-radius:5px;padding:7px;font-size:11px}button{background:#1a222a;color:#eee;border:1px solid #3a4651;border-radius:6px;padding:7px 10px;font-size:11px;cursor:pointer}button:hover{background:#242e38}.new{margin-bottom:12px}
    </style>
    <h2>DMX → HA ZONES</h2><div class="sub">Zones d'éclairage façon Hue · un univers d'écoute par zone · sortie DMX interdite · RDM passif uniquement</div>
    <div class="card new"><div class="head"><span class="name">Créer une zone</span><span class="pill">${zones.length} zone(s)</span></div>
      <div class="row"><label>Nom<input id="zn" value="Nouvelle zone"></label><label>Universe<input id="zu" type="number" min="1" max="63999" value="1"></label><label>Canaux<input id="zc" value="1-3"></label><label>Mode<select id="zm"><option>dimmer</option><option>rgb</option><option>rgbw</option><option>cct</option><option>switch</option></select></label></div>
      <div class="row"><label>Fixture / Hue model<input id="zf" placeholder="LCT001 / fixture"></label><label>Source<input id="zs" placeholder="optionnel"></label></div>
      <div class="sub" style="margin-top:-4px">Fixture: texte libre pour toi (ex: "PAR façade"). Hue model: code produit Hue précis (ex: LCT001) — seulement si tu veux que HA/l'app Hue traite cette zone comme une vraie lampe Hue. Source: laisse vide sauf si plusieurs consoles envoient sur le même univers et que tu veux filtrer par IP.</div>
      <div class="row"><label style="flex:1 1 100%">Lampes HA<div id="zl-list" style="max-height:160px;overflow-y:auto;border:1px solid #333b44;border-radius:5px;padding:7px;background:#0b0e12;display:flex;flex-direction:column;gap:5px">${lights.map(x=>`<label style="flex-direction:row;align-items:center;gap:7px;font-size:12px;color:#eee"><input type="checkbox" class="zl-cb" value="${x.id}"> ${x.name}</label>`).join('')||'<span class="sub">Aucune lampe HA trouvée.</span>'}</div></label><label>Fixture par lampe (JSON, avancé — optionnel)<input id="zft" placeholder='{"light.xxx":"RGB fixture"}'></label></div>
      <div class="sub" style="margin-top:-4px">Coche toutes les lampes de la zone ci-dessus (plusieurs possibles). Le champ JSON ne sert que si une lampe précise de la zone a besoin d'un profil différent des autres — à laisser vide dans la grande majorité des cas.</div>
      <div class="row"><button id="add">AJOUTER LA ZONE</button></div>
      ${this._msg?`<div class="sub" style="margin-top:8px">${esc(this._msg)}</div>`:''}
    </div>
    <div class="grid">${zones.map(z=>this._card(z)).join('')||'<div class="card">Aucune zone configurée.</div>'}</div>`;
    this.querySelector('#add')?.addEventListener('click',()=>{
      const selected=[...this.querySelectorAll('.zl-cb:checked')].map(o=>o.value);
      const name=this.querySelector('#zn').value.trim()||'Zone';
      const id='zone_'+name.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'')+'_'+Date.now().toString(36);
      this._call('create_dmx_ha_zone',{zone_id:id,name,universe:Number(this.querySelector('#zu').value),channels:this.querySelector('#zc').value,mode:this.querySelector('#zm').value,fixture_type:this.querySelector('#zf').value,fixture_types:(()=>{try{return JSON.parse(this.querySelector('#zft').value||'{}')}catch(e){return {}}})(),entity_ids:selected,source:this.querySelector('#zs').value,enabled:true,rdm_enabled:false});
    });
    this.querySelectorAll('[data-zone-toggle]').forEach(b=>b.addEventListener('click',()=>this._call('set_dmx_ha_zone_enabled',{zone_id:b.dataset.zoneToggle,enabled:b.dataset.value!=='true'})));
    this.querySelectorAll('[data-rdm-toggle]').forEach(b=>b.addEventListener('click',()=>this._call('set_dmx_ha_zone_rdm_enabled',{zone_id:b.dataset.rdmToggle,enabled:b.dataset.value!=='true'})));
    this.querySelectorAll('[data-zone-remove]').forEach(b=>b.addEventListener('click',()=>this._call('remove_dmx_ha_zone',{zone_id:b.dataset.zoneRemove})));
    this.querySelectorAll('[data-rdm-observe]').forEach(b=>b.addEventListener('click',()=>{
      const f=this.querySelector(`[data-rdm-uid="${b.dataset.rdmObserve}"]`);
      const uid=f?.value?.trim();
      if(!uid)return;
      this._call('observe_dmx_ha_rdm',{zone_id:b.dataset.rdmObserve,uid});
    }));
  }
  _card(z){
    const model=z.hue_model_id||'—', cap=z.hue_capabilities?.kind||'—';
    return `<div class="card"><div class="head"><span class="name">${z.name}</span><span class="pill ${z.enabled?'on':'off'}">${z.enabled?'ACTIVE':'OFF'}</span></div><div class="meta">Universe ${z.universe} · ${z.mode.toUpperCase()} · canaux ${z.channels.join(', ')} · ${z.entity_ids.length} lampe(s)</div><div class="meta">Fixture: ${z.fixture_type||'non défini'} · Hue: ${model} · ${cap}</div><div class="meta">RDM: ${z.rdm_enabled?'ÉCOUTE ACTIVE':'désactivée'}${z.rdm_enabled?' · détection passive uniquement':''}</div><div class="row"><button data-zone-toggle="${z.zone_id}" data-value="${z.enabled}">${z.enabled?'DÉSACTIVER':'ACTIVER'}</button><button data-rdm-toggle="${z.zone_id}" data-value="${z.rdm_enabled}">${z.rdm_enabled?'COUPER RDM':'ÉCOUTER RDM'}</button><button data-zone-remove="${z.zone_id}">SUPPRIMER</button></div>${z.rdm_enabled?`<div class="row" style="margin-top:6px"><input data-rdm-uid="${z.zone_id}" placeholder="UID RDM observée (xxxx:xxxxxxxx)" style="flex:1;min-width:0"><button data-rdm-observe="${z.zone_id}">Enregistrer</button></div>`:''}</div>`
  }
}
snDefine('dmx-ha-zones-panel',DmxHaZonesPanel);

/* ===== punchlight-network-panel.js ===== */
class PunchLightNetworkPanel extends HTMLElement {
  set hass(h){this._hass=h;this.render()}
  render(){
    if(!this._hass)return;
    const s=this._hass.states['sensor.dmx_monitor_punchlight_network'];
    const data=s?.attributes?.devices||[];
    const list=data.length?data.map(d=>'<div style="border-top:1px solid var(--divider-color);padding:8px 0">'+
      '<b>'+(d.name||'RTP-MIDI')+'</b><br>'+((d.addresses||[]).join(', ')||'IP inconnue')+' · port '+(d.port||'?')+'<br>'+      '<small>'+(d.type==='punchlight_dli_lan'?'PunchLight DLi-LAN — identifié':'Endpoint RTP-MIDI — candidat PunchLight, confirmation nécessaire')+'</small>'+      '</div>').join(''):'Aucun endpoint RTP-MIDI détecté.';
    this.innerHTML=`<ha-card header="🎙 PunchLight — Réseau">
      <div style="padding:12px;font-size:12px;color:var(--secondary-text-color)">
        Détection passive RTP-MIDI / Apple MIDI. Aucun MIDI ni contrôle n'est envoyé.
        <div style="margin-top:10px"><button id="scan">🔎 Rechercher les PunchLight</button></div>
        <div style="margin-top:10px">${list}</div>
      </div></ha-card>`;
    this.querySelector('#scan')?.addEventListener('click',async()=>{const b=this.querySelector('#scan');b.disabled=true;b.textContent='Recherche…';try{const cfg=Object.values(this._hass.states||{}).find(x=>x.attributes&&('interface_dmx' in x.attributes))?.attributes||{};await this._hass.callService('dmx_monitor','discover_punchlight',{interface:cfg.interface_dmx||'0.0.0.0',timeout:3});b.textContent='Recherche terminée';setTimeout(()=>this.render(),250);}catch(e){b.textContent='Erreur: '+(e?.message||e)}finally{setTimeout(()=>{b.disabled=false;if(b.textContent==='Recherche terminée')b.textContent='🔎 Rechercher les PunchLight'},1200)}});
  }
}
snDefine('punchlight-network-panel',PunchLightNetworkPanel);

/* ===== show-control-panel.js ===== */
class ShowControlPanel extends HTMLElement {
  constructor(){super();this._hass=null;this._actions=[];this._editing=null;}
  set hass(v){this._hass=v;this.render()}
  get hass(){return this._hass}
  _state(key){return Object.values(this._hass?.states||{}).find(x=>x.attributes && (key in x.attributes || x.entity_id.includes(key)))||null}
  _attrs(){
    const cueState=this._state('show_control_cue_count')||this._state('show_control_fired');
    const midiState=this._state('midi_output_sent');
    const oscState=this._state('osc_targets');
    return {cue:cueState?.attributes||{},midi:midiState?.attributes||{},oscTargets:oscState?.attributes?.targets||[]};
  }
  async _call(service,data){await this._hass.callService('dmx_monitor',service,data);setTimeout(()=>this.render(),400);setTimeout(()=>this.render(),1500)}
  _newAction(){return {type:'ha_service',delay_s:0,service:'',data_json:'{}',target_id:'',address:'',args_json:'[]',message_type:'',scene_id:''}}
  _actionFields(a,i){
    const upd=(k,v)=>{this._actions[i][k]=v};
    if(a.type==='ha_service')return `<input data-i="${i}" data-k="service" placeholder="domaine.service (ex: light.turn_on)" value="${esc(a.service)}"><input data-i="${i}" data-k="data_json" placeholder='Data JSON (ex: {"entity_id":"light.foh"})' value='${esc(a.data_json)}'>`;
    if(a.type==='osc')return `<select data-i="${i}" data-k="target_id">${(this._attrs().oscTargets||[]).map(t=>`<option value="${esc(t.target_id)}" ${t.target_id===a.target_id?'selected':''}>${esc(t.name)}</option>`).join('')||'<option value="">Aucune cible OSC — configure-en une dans OSC OUT</option>'}</select><input data-i="${i}" data-k="address" placeholder="Adresse OSC (ex: /cue/go)" value="${esc(a.address)}"><input data-i="${i}" data-k="args_json" placeholder="Args JSON (ex: [1])" value='${esc(a.args_json)}'>`;
    if(a.type==='midi')return `<select data-i="${i}" data-k="target_id">${(this._attrs().midi.targets||[]).map(t=>`<option value="${esc(t.target_id)}" ${t.target_id===a.target_id?'selected':''}>${esc(t.name)}</option>`).join('')||'<option value="">Aucune cible MIDI configurée</option>'}</select><input data-i="${i}" data-k="message_type" placeholder="Type (note_on / cc / program_change)" value="${esc(a.message_type)}"><input data-i="${i}" data-k="data_json" placeholder='Data JSON (ex: {"note":60,"velocity":127})' value='${esc(a.data_json)}'>`;
    if(a.type==='dmx_scene')return `<input data-i="${i}" data-k="scene_id" placeholder="ID de la scène DMX" value="${esc(a.scene_id)}">`;
    return '';
  }
  _paintActions(){
    const host=this.querySelector('#actions-list'); if(!host)return;
    host.innerHTML=this._actions.map((a,i)=>`<div class="arow"><div class="arow-top"><select data-i="${i}" data-k="type">${['ha_service','osc','midi','dmx_scene'].map(t=>`<option value="${t}" ${t===a.type?'selected':''}>${t}</option>`).join('')}</select><input data-i="${i}" data-k="delay_s" type="number" min="0" max="300" step="0.1" value="${a.delay_s}" placeholder="délai (s)"><button class="btn danger" data-rm-action="${i}">×</button></div><div class="arow-fields">${this._actionFields(a,i)}</div></div>`).join('');
    host.querySelectorAll('select[data-k="type"],input,select').forEach(el=>{
      el.addEventListener(el.tagName==='SELECT'?'change':'input',()=>{
        const i=+el.dataset.i,k=el.dataset.k;
        this._actions[i][k]=el.value;
        if(k==='type')this._paintActions();
      });
    });
    host.querySelectorAll('[data-rm-action]').forEach(b=>b.addEventListener('click',()=>{this._actions.splice(+b.dataset.rmAction,1);this._paintActions()}));
  }
  render(){
    if(!this._hass){this.innerHTML='';return}
    const {cue,midi}=this._attrs();
    const cues=cue.cues||[]; const mout=midi.midi_output||{}; const targets=midi.targets||[];
    const on=cue.enabled===true; const mon=mout.enabled===true;
    this.innerHTML=`<style>:host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}.top{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}.card{background:#15181c;border:1px solid #2c3239;border-radius:9px;padding:13px;margin-bottom:10px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}.big{font-size:24px;font-weight:800}.muted{font-size:10px;color:#8d969f}.ok{color:#65dc99}.off{color:#f0b36a}.btn{background:#252a30;border:1px solid #3a4148;color:#eee;border-radius:6px;padding:8px 10px;cursor:pointer;margin:3px 4px 3px 0}.btn.active{background:#1d5c3a}.btn.primary{background:#164d70}.btn.danger{border-color:#8b3f45}.row{display:grid;grid-template-columns:1fr 1.4fr 1fr auto;gap:8px;padding:8px 0;border-top:1px solid #282d33;font-size:11px;align-items:center}
input,select{box-sizing:border-box;width:100%;background:#0b0d10;color:#eee;border:1px solid #343b43;border-radius:6px;padding:7px;margin-bottom:6px;font-size:11px}
.arow{border:1px solid #282d33;border-radius:8px;padding:8px;margin-bottom:8px;background:#101317}
.arow-top{display:grid;grid-template-columns:1fr 100px 34px;gap:6px}
.arow-fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:6px;margin-top:6px}
</style>
      <h2>SHOW CONTROL</h2><div class="muted" style="margin-bottom:12px">Moteur séparé inspiré des workflows cue/playback : cues persistants, sorties explicitement armées, aucun remplacement des autres modules.</div>
      <div class="top"><button id="gate" class="btn ${on?'active':''}">SHOW CONTROL ${on?'ON':'OFF'}</button><button id="midi" class="btn ${mon?'active':''}">MIDI OUT ${mon?'ON':'OFF'}</button></div>
      <div class="grid"><div class="card"><div class="muted">Cues</div><div class="big">${cues.length}</div></div><div class="card"><div class="muted">Dernier cue</div><div class="big">${cue.last_cue||'—'}</div></div><div class="card"><div class="muted">MIDI OUT</div><div class="big">${mout.sent??0}</div><div class="muted">${mout.errors??0} erreur(s)</div></div><div class="card"><div class="muted">Cibles MIDI</div><div class="big">${targets.length}</div></div></div>
      <div class="card"><b>Cues enregistrés</b>${cues.length?cues.map(c=>`<div class="row"><span>${c.name||c.cue_id}</span><span>${(c.actions||[]).length} action(s)</span><span>${c.enabled===false?'OFF':'READY'}</span><span><button class="btn" data-fire="${c.cue_id}">GO</button><button class="btn" data-edit="${c.cue_id}">Éditer</button><button class="btn danger" data-del="${c.cue_id}">Suppr.</button></span></div>`).join(''):'<div class="muted" style="margin-top:8px">Aucun cue pour l\u2019instant — crée-en un ci-dessous.</div>'}</div>
      <div class="card"><b>${this._editing?'Éditer le cue « '+esc(this._editing)+' »':'Nouveau cue'}</b>
      <input id="cue-id" placeholder="ID du cue (ex: cue_1)" value="${esc(this._cueId||'')}" ${this._editing?'disabled':''}>
      <input id="cue-name" placeholder="Nom affiché" value="${esc(this._cueName||'')}">
      <div id="actions-list"></div>
      <button class="btn" id="add-action">+ Action</button>
      <div style="margin-top:8px"><button class="btn primary" id="save-cue">Enregistrer le cue</button>${this._editing?'<button class="btn" id="cancel-edit">Annuler l\u2019édition</button>':''}</div>
      ${this._msg?`<div class="muted" style="margin-top:8px">${esc(this._msg)}</div>`:''}
      </div>
      <div class="card"><b>Architecture de sécurité</b><div class="muted" style="margin-top:6px">Show Control revient OFF au redémarrage. OSC OUT, MIDI OUT et Scènes DMX conservent chacun leur propre gate : un cue ne contourne jamais la sécurité du protocole qu'il appelle.</div>${cue.last_error?`<div class="off" style="margin-top:8px">${cue.last_error}</div>`:''}</div>`;
    this.querySelector('#gate')?.addEventListener('click',()=>this._call('set_show_control_enabled',{enabled:!on}));
    this.querySelector('#midi')?.addEventListener('click',()=>this._call('set_midi_output_enabled',{enabled:!mon}));
    this.querySelectorAll('[data-fire]').forEach(b=>b.addEventListener('click',()=>this._call('fire_show_control_cue',{cue_id:b.dataset.fire})));
    this.querySelectorAll('[data-del]').forEach(b=>b.addEventListener('click',()=>this._call('remove_show_control_cue',{cue_id:b.dataset.del})));
    this.querySelectorAll('[data-edit]').forEach(b=>b.addEventListener('click',()=>{
      const c=cues.find(x=>x.cue_id===b.dataset.edit); if(!c)return;
      this._editing=c.cue_id; this._cueId=c.cue_id; this._cueName=c.name;
      this._actions=(c.actions||[]).map(a=>({type:a.type,delay_s:a.delay_s||0,service:a.service||'',data_json:JSON.stringify(a.data||{}),target_id:a.target_id||'',address:a.address||'',args_json:JSON.stringify(a.args||[]),message_type:a.message_type||'',scene_id:a.scene_id||''}));
      this.render();
    }));
    this.querySelector('#cancel-edit')?.addEventListener('click',()=>{this._editing=null;this._cueId='';this._cueName='';this._actions=[];this.render()});
    this.querySelector('#cue-id')?.addEventListener('input',e=>this._cueId=e.target.value);
    this.querySelector('#cue-name')?.addEventListener('input',e=>this._cueName=e.target.value);
    this.querySelector('#add-action')?.addEventListener('click',()=>{this._actions.push(this._newAction());this._paintActions()});
    this._paintActions();
    this.querySelector('#save-cue')?.addEventListener('click',()=>{
      const cue_id=(this._cueId||'').trim();
      if(!cue_id){this._msg='ID du cue obligatoire.';this.render();return;}
      let actions;
      try{
        actions=this._actions.map(a=>{
          const base={type:a.type,delay_s:Number(a.delay_s)||0};
          if(a.type==='ha_service')return {...base,service:a.service,data:JSON.parse(a.data_json||'{}')};
          if(a.type==='osc')return {...base,target_id:a.target_id,address:a.address,args:JSON.parse(a.args_json||'[]')};
          if(a.type==='midi')return {...base,target_id:a.target_id,message_type:a.message_type,data:JSON.parse(a.data_json||'{}')};
          if(a.type==='dmx_scene')return {...base,scene_id:a.scene_id};
          return base;
        });
      }catch(e){this._msg='JSON invalide dans une action (data/args).';this.render();return;}
      this._call('upsert_show_control_cue',{cue_id,name:this._cueName||cue_id,actions,enabled:true});
      this._editing=null;this._cueId='';this._cueName='';this._actions=[];
    });
  }
}
snDefine('show-control-panel',ShowControlPanel);

/* ===== timecode-panel + Lovelace cards (0.15.19-dev10) ===== */
function snFindState(hass, suffix, friendly){
  const states=Object.values(hass?.states||{});
  return states.find(s=>s.entity_id===suffix)||states.find(s=>s.entity_id.endsWith(suffix))||states.find(s=>String(s.attributes?.friendly_name||'').toLowerCase().includes(String(friendly||'').toLowerCase()));
}
class ShowNetworkTimecodePanel extends HTMLElement{
  set hass(v){this._hass=v;this.render()} connectedCallback(){this.render()}
  render(){if(!this._hass){this.innerHTML='';return} const s=snFindState(this._hass,'timecode','timecode'); const a=s?.attributes||{}; const st=String(a.status||'waiting').toUpperCase();
    this.innerHTML=`<style>:host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}.tc{font-variant-numeric:tabular-nums;font-size:clamp(42px,8vw,96px);font-weight:850;letter-spacing:.04em}.card{background:#15181c;border:1px solid #2c3239;border-radius:12px;padding:18px}.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}.tag{border:1px solid #3a4148;border-radius:6px;padding:5px 8px;font-size:11px}.locked{color:#65dc99}.lost{color:#ef6b73}.waiting{color:#8d969f}</style><h2>TIMECODE LIVE</h2><div class="card"><div class="tc">${s?.state||'--:--:--:--'}</div><div class="row"><span class="tag ${String(a.status||'waiting')}">${st}</span><span class="tag">${a.fps??'—'} FPS</span><span class="tag">${a.drop_frame?'DROP':'NON-DROP'}</span><span class="tag">${a.transport||'Art-Net ArtTimeCode'}</span><span class="tag">Source ${a.source||'—'}</span><span class="tag">Âge ${a.age_s==null?'—':a.age_s+' s'}</span><span class="tag">Paquets ${a.packet_count??0}</span><span class="tag">Δ ${a.last_packet_interval_ms==null?'—':a.last_packet_interval_ms+' ms'}</span></div></div>`}
}
snDefine('show-network-timecode-panel',ShowNetworkTimecodePanel);

class ShowNetworkTimecodeCard extends HTMLElement{
  setConfig(config){this.config=config||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
  render(){if(!this._hass)return; const s=this.config?.entity?this._hass.states[this.config.entity]:snFindState(this._hass,'timecode','timecode'); const a=s?.attributes||{}; const ok=a.status==='locked'; this.innerHTML=`<ha-card><style>.wrap{padding:16px}.title{font-size:13px;color:var(--secondary-text-color)}.tc{font-variant-numeric:tabular-nums;font-size:36px;font-weight:800;margin:5px 0}.meta{font-size:12px;color:var(--secondary-text-color)}.dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:${ok?'var(--success-color, #43a047)':'var(--error-color, #db4437)'};margin-right:6px}</style><div class="wrap"><div class="title">${this.config?.name||'Show Network · Timecode'}</div><div class="tc">${s?.state||'--:--:--:--'}</div><div class="meta"><span class="dot"></span>${String(a.status||'waiting').toUpperCase()} · ${a.fps??'—'} fps · ${a.source||'aucune source'}</div></div></ha-card>`}
}
snDefine('show-network-timecode-card',ShowNetworkTimecodeCard);

class ShowNetworkOnAirCard extends HTMLElement{
  setConfig(config){this.config=config||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
  render(){if(!this._hass)return; const rec=this.config?.recording_entity?this._hass.states[this.config.recording_entity]:snFindState(this._hass,'punchlight_recording','punchlight — enregistrement'); const ready=this.config?.ready_entity?this._hass.states[this.config.ready_entity]:snFindState(this._hass,'punchlight_ready','punchlight — ready'); const unavailable=!rec||!ready||rec.state==='unavailable'||ready.state==='unavailable'; const red=!unavailable&&rec?.state==='on', green=!unavailable&&!red&&ready?.state==='on'; const state=unavailable?'INDISPONIBLE':red?'ON AIR':green?'READY':'OFF'; const bg=red?'#b3261e':green?'#267a3e':'#555b62'; this.innerHTML=`<ha-card><style>.tile{padding:22px;border-radius:12px;background:${bg};color:white;text-align:center}.label{font-size:12px;opacity:.85}.state{font-size:34px;font-weight:900;letter-spacing:.06em;margin-top:4px}</style><div class="tile"><div class="label">${this.config?.name||'PunchLight'}</div><div class="state">${state}</div></div></ha-card>`}
}
snDefine('show-network-onair-card',ShowNetworkOnAirCard);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type==='show-network-timecode-card')) window.customCards.push({type:'show-network-timecode-card',name:'Show Network · Timecode',description:'Timecode live avec lock, FPS et source.'});
if(!window.customCards.some(c=>c.type==='show-network-onair-card')) window.customCards.push({type:'show-network-onair-card',name:'Show Network · On Air',description:'État PunchLight: OFF, READY ou ON AIR.'});

/* ===== Lovelace status tiles (0.15.19-dev11) ===== */
function snCardEntity(hass, config, key, friendly){
  const explicit=config?.[key]||config?.entity;
  return explicit?hass?.states?.[explicit]:snFindState(hass,key,friendly);
}
function snMoreInfo(el,hass,entity){
  if(!entity)return;
  el.addEventListener('click',()=>el.dispatchEvent(new CustomEvent('hass-more-info',{detail:{entityId:entity.entity_id},bubbles:true,composed:true})));
}
function snStatusTone(kind){
  return {ok:'var(--success-color,#43a047)',warn:'var(--warning-color,#f9a825)',error:'var(--error-color,#db4437)',idle:'var(--disabled-text-color,#73777b)',info:'var(--info-color,#1976d2)'}[kind]||'var(--disabled-text-color,#73777b)';
}
function snTileHTML(title,value,detail,tone,icon='mdi:lan'){
  return `<ha-card><style>.sn-tile{padding:16px;cursor:pointer;min-height:92px}.head{display:flex;align-items:center;gap:8px;color:var(--secondary-text-color);font-size:12px}.dot{width:10px;height:10px;border-radius:50%;background:${snStatusTone(tone)};box-shadow:0 0 0 3px color-mix(in srgb,${snStatusTone(tone)} 18%,transparent)}.value{font-size:26px;font-weight:800;margin:8px 0 2px}.detail{font-size:12px;color:var(--secondary-text-color)}</style><div class="sn-tile"><div class="head"><ha-icon icon="${icon}"></ha-icon><span>${title}</span><span class="dot"></span></div><div class="value">${value}</div><div class="detail">${detail||''}</div></div></ha-card>`;
}
class ShowNetworkMA3Card extends HTMLElement{
 setConfig(c){this.config=c||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
 render(){if(!this._hass)return;const s=snCardEntity(this._hass,this.config,'ma_live_stations','stations ma actives');const n=Number(s?.state);const known=s&&!['unknown','unavailable'].includes(s.state);this.innerHTML=snTileHTML(this.config?.name||'grandMA3 / MA-Net3',known?`${n} station${n===1?'':'s'}`:'INCONNU',known?(n>0?'MA-Net3 observé':'Aucune station active'):'Entité MA indisponible',known&&n>0?'ok':known?'idle':'warn','mdi:console');snMoreInfo(this,this._hass,s)} }
snDefine('show-network-ma3-card',ShowNetworkMA3Card);

class ShowNetworkPTPCard extends HTMLElement{
 setConfig(c){this.config=c||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
 render(){if(!this._hass)return;const s=snCardEntity(this._hass,this.config,'ptp_clock_present','horloge ptp observée');const on=['true','on','1'].includes(String(s?.state).toLowerCase());const known=s&&!['unknown','unavailable'].includes(s.state);const a=s?.attributes||{};this.innerHTML=snTileHTML(this.config?.name||'PTP / Horloge',known?(on?'CLOCK':'ABSENTE'):'INCONNU',on?`Horloge observée${a.ptp_clock_age_s!=null?' · âge '+a.ptp_clock_age_s+' s':''}`:'Aucune horloge PTP fraîche',known&&on?'ok':known?'warn':'idle','mdi:clock-network');snMoreInfo(this,this._hass,s)} }
snDefine('show-network-ptp-card',ShowNetworkPTPCard);

class ShowNetworkDanteCard extends HTMLElement{
 setConfig(c){this.config=c||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
 render(){if(!this._hass)return;const s=snCardEntity(this._hass,this.config,'dante_sources','sources dante');const n=Number(s?.state);const known=s&&!['unknown','unavailable'].includes(s.state);this.innerHTML=snTileHTML(this.config?.name||'Dante / Audio',known?`${n} source${n===1?'':'s'}`:'INCONNU',known&&n>0?'Trafic Dante observé':known?'Aucune source Dante observée':'Entité Dante indisponible',known&&n>0?'ok':known?'idle':'warn','mdi:audio-input-stereo-minijack');snMoreInfo(this,this._hass,s)} }
snDefine('show-network-dante-card',ShowNetworkDanteCard);

class ShowNetworkDoctorCard extends HTMLElement{
 setConfig(c){this.config=c||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
 render(){if(!this._hass)return;const s=snCardEntity(this._hass,this.config,'show_network_doctor','diagnostic show network');const st=String(s?.state||'unknown').toLowerCase();const tone=['ok','healthy'].includes(st)?'ok':['error','critical'].includes(st)?'error':['warning','warn'].includes(st)?'warn':'idle';const a=s?.attributes||{};const d=[a.errors!=null?`${a.errors} erreur(s)`:null,a.warnings!=null?`${a.warnings} avert.`:null].filter(Boolean).join(' · ')||'Ouvrir pour les contrôles';this.innerHTML=snTileHTML(this.config?.name||'Show Network Doctor',st.toUpperCase(),d,tone,'mdi:stethoscope');snMoreInfo(this,this._hass,s)} }
snDefine('show-network-doctor-card',ShowNetworkDoctorCard);

class ShowNetworkSnapshotCard extends HTMLElement{
 setConfig(c){this.config=c||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
 render(){if(!this._hass)return;const s=snCardEntity(this._hass,this.config,'show_snapshot','référence spectacle');const st=String(s?.state||'no_reference').toLowerCase();const tone=['match','ok','matching'].includes(st)?'ok':st==='no_reference'?'idle':['warning','changed','mismatch'].includes(st)?'warn':'info';const a=s?.attributes||{};this.innerHTML=snTileHTML(this.config?.name||'Référence spectacle',st.replaceAll('_',' ').toUpperCase(),a.active_name||a.name||'Comparer la régie à la référence',tone,'mdi:camera-marker-outline');snMoreInfo(this,this._hass,s)} }
snDefine('show-network-snapshot-card',ShowNetworkSnapshotCard);

class ShowNetworkProjectorsCard extends HTMLElement{
 setConfig(c){this.config=c||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
 render(){if(!this._hass)return;const online=snCardEntity(this._hass,this.config,'projectors_online','projecteurs pjlink en ligne');const errors=snCardEntity(this._hass,{entity:this.config?.errors_entity},'projectors_errors','projecteurs pjlink en erreur');const n=Number(online?.state),e=Number(errors?.state);const known=online&&!['unknown','unavailable'].includes(online.state);this.innerHTML=snTileHTML(this.config?.name||'Projecteurs',known?`${n} EN LIGNE`:'INCONNU',known?`${Number.isFinite(e)?e:'—'} en erreur`:'Télémétrie indisponible',known&&e>0?'error':known&&n>0?'ok':known?'idle':'warn','mdi:projector');snMoreInfo(this,this._hass,online)} }
snDefine('show-network-projectors-card',ShowNetworkProjectorsCard);

class ShowNetworkPowerCard extends HTMLElement{
 setConfig(c){this.config=c||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
 render(){if(!this._hass)return;const s=snCardEntity(this._hass,this.config,'power_manager_active','power manager actifs');const n=Number(s?.state);const known=s&&!['unknown','unavailable'].includes(s.state);this.innerHTML=snTileHTML(this.config?.name||'Alimentations régie',known?`${n} ACTIVE${n===1?'':'S'}`:'INCONNU','Carte d’état uniquement · commandes via Power Manager sécurisé',known&&n>0?'ok':known?'idle':'warn','mdi:power-plug');snMoreInfo(this,this._hass,s)} }
snDefine('show-network-power-card',ShowNetworkPowerCard);

class ShowNetworkDMXCard extends HTMLElement{
 setConfig(c){if(!c?.entity)throw new Error('show-network-dmx-card nécessite entity: binary_sensor DMX universe active');this.config=c;this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
 render(){if(!this._hass)return;const s=this._hass.states[this.config.entity];const known=s&&!['unknown','unavailable'].includes(s.state);const on=s?.state==='on';const a=s?.attributes||{};this.innerHTML=snTileHTML(this.config?.name||'Univers DMX',known?(on?'LIVE':'SILENCIEUX'):'INCONNU',[a.protocol,a.universe!=null?`U${a.universe}`:null].filter(Boolean).join(' · ')||s?.entity_id||'Entité absente',known&&on?'ok':known?'warn':'idle','mdi:waveform');snMoreInfo(this,this._hass,s)} }
snDefine('show-network-dmx-card',ShowNetworkDMXCard);

for(const c of [
 ['show-network-ma3-card','Show Network · grandMA3','État MA-Net3 / stations actives.'],
 ['show-network-ptp-card','Show Network · PTP','Présence de l’horloge PTP observée.'],
 ['show-network-dante-card','Show Network · Dante','Sources Dante observées.'],
 ['show-network-doctor-card','Show Network · Doctor','Santé et diagnostic transversal Show Network.'],
 ['show-network-snapshot-card','Show Network · Show Snapshot','État de comparaison avec la référence spectacle.'],
 ['show-network-projectors-card','Show Network · Projecteurs','Projecteurs PJLink en ligne et erreurs.'],
 ['show-network-power-card','Show Network · Alimentations','État Power Manager sans commande décorative.'],
 ['show-network-dmx-card','Show Network · Univers DMX','État live/silencieux d’un univers DMX.']]){
 if(!window.customCards.some(x=>x.type===c[0]))window.customCards.push({type:c[0],name:c[1],description:c[2]});
}


/* ===== Infrastructure Lovelace cards (0.15.19-dev15) ===== */
class ShowNetworkInterfacesCard extends HTMLElement{
 setConfig(c){this.config=c||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
 render(){if(!this._hass)return;const s=snCardEntity(this._hass,this.config,'network_interfaces_up','interfaces réseau actives');const a=s?.attributes||{};const rows=a.interfaces||[];const up=rows.filter(x=>x.is_up===true);const stale=Number(a.network_health?.interfaces_stale??0);const detail=rows.length?up.slice(0,3).map(x=>`${x.name}: ${(x.addresses||[]).filter(y=>!String(y).includes(':')).join(', ')||'sans IPv4'}`).join(' · '):'Inventaire NIC indisponible';this.innerHTML=snTileHTML(this.config?.name||'Interfaces réseau',s?`${up.length}/${rows.length} UP`:'INCONNU',detail,stale>0?'warn':up.length?'ok':'idle','mdi:ethernet');snMoreInfo(this,this._hass,s)} }
snDefine('show-network-interfaces-card',ShowNetworkInterfacesCard);

class ShowNetworkSwitchesCard extends HTMLElement{
 setConfig(c){this.config=c||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
 render(){if(!this._hass)return;const s=snCardEntity(this._hass,this.config,'switch_telemetry','télémétrie switches');const rows=s?.attributes?.switches||[];let ports=0,up=0;for(const sw of rows)for(const p of (sw.ports||[])){ports++;if(p.up===true)up++}const errs=rows.filter(sw=>sw.error||sw.online===false).length;this.innerHTML=snTileHTML(this.config?.name||'Switches / Ports',s?`${rows.length} SWITCH${rows.length===1?'':'ES'}`:'INCONNU',rows.length?`${up}/${ports} ports UP${errs?' · '+errs+' alerte(s)':''}`:'Aucune télémétrie switch',errs?'warn':rows.length?'ok':'idle','mdi:switch');snMoreInfo(this,this._hass,s)} }
snDefine('show-network-switches-card',ShowNetworkSwitchesCard);

class ShowNetworkAmplifiersCard extends HTMLElement{
 setConfig(c){this.config=c||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
 render(){if(!this._hass)return;const s=snCardEntity(this._hass,this.config,'audio_amplifiers_total','amplis audio');const rows=s?.attributes?.amplifiers||[];const online=rows.filter(x=>x.online===true).length;const errors=rows.filter(x=>x.error&&!['ok','normal','0'].includes(String(x.error).toLowerCase())).length;const temp=rows.map(x=>Number(x.temperature_c??x.temperature)).filter(Number.isFinite);this.innerHTML=snTileHTML(this.config?.name||'Amplificateurs',s?`${online}/${rows.length} ONLINE`:'INCONNU',[errors?`${errors} erreur(s)`:null,temp.length?`max ${Math.max(...temp)} °C`:null].filter(Boolean).join(' · ')||'Télémétrie réellement observée',errors?'error':online?'ok':rows.length?'warn':'idle','mdi:amplifier');snMoreInfo(this,this._hass,s)} }
snDefine('show-network-amplifiers-card',ShowNetworkAmplifiersCard);

class ShowNetworkAppleCard extends HTMLElement{
 setConfig(c){this.config=c||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
 render(){if(!this._hass)return;const s=snCardEntity(this._hass,this.config,'show_network_devices','équipements consolidés');const devices=s?.attributes?.devices||[];const apple=devices.filter(d=>String(d.manufacturer||'').toLowerCase().includes('apple')||/^mac/i.test(String(d.model||'')));const minis=apple.filter(d=>/mac\s*mini|macmini/i.test(`${d.name||''} ${d.model||''}`));const detail=apple.slice(0,3).map(d=>`${d.name||d.ip||d.id}${d.interface?' · '+d.interface:''}`).join(' · ')||'Aucun Apple confirmé par les preuves disponibles';this.innerHTML=snTileHTML(this.config?.name||'Apple / Mac',s?`${apple.length} CONFIRMÉ${apple.length===1?'':'S'}`:'INCONNU',`${minis.length} Mac mini · ${detail}`,apple.length?'ok':'idle','mdi:apple');snMoreInfo(this,this._hass,s)} }
snDefine('show-network-apple-card',ShowNetworkAppleCard);

class ShowNetworkDevicesCard extends HTMLElement{
 setConfig(c){this.config=c||{};this.render()} set hass(v){this._hass=v;this.render()} getCardSize(){return 2}
 render(){if(!this._hass)return;const s=snCardEntity(this._hass,this.config,'show_network_devices','équipements consolidés');const devices=s?.attributes?.devices||[];const conflicts=Number(s?.attributes?.conflict_count||0);const monitored=devices.filter(d=>d.monitor_mode==='monitor').length;this.innerHTML=snTileHTML(this.config?.name||'Équipements',s?`${devices.length} APPAREIL${devices.length===1?'':'S'}`:'INCONNU',`${monitored} surveillé(s)${conflicts?' · '+conflicts+' conflit(s)':''}`,conflicts?'warn':devices.length?'ok':'idle','mdi:devices');snMoreInfo(this,this._hass,s)} }
snDefine('show-network-devices-card',ShowNetworkDevicesCard);

for(const c of [
 ['show-network-interfaces-card','Show Network · Interfaces','Interfaces réseau locales et adresses observées.'],
 ['show-network-switches-card','Show Network · Switches','Switches et état réel des ports observés.'],
 ['show-network-amplifiers-card','Show Network · Amplificateurs','Amplificateurs identifiés et télémétrie disponible.'],
 ['show-network-apple-card','Show Network · Apple / Mac','Appareils Apple confirmés par le Device Model.'],
 ['show-network-devices-card','Show Network · Équipements','Inventaire consolidé et conflits d’identité.']]){if(!window.customCards.some(x=>x.type===c[0]))window.customCards.push({type:c[0],name:c[1],description:c[2]});}

/* ===== dev27 readiness dashboard cards ===== */
class ShowNetworkIncidentCard extends HTMLElement{setConfig(c){this.config=c||{}}set hass(v){this._hass=v;this.render()}getCardSize(){return 2}render(){if(!this._hass)return;const st=Object.values(this._hass.states||{}).find(x=>x.entity_id.endsWith('_incident_center')),a=st?.attributes||{},c=a.counts||{},state=String(a.state||st?.state||'unknown').toUpperCase();this.innerHTML=`<ha-card><style>.c{padding:13px}.v{font-size:25px;font-weight:900}.ok{color:#68df9a}.warning{color:#e5bf6b}.error{color:#ef7777}.m{font-size:11px;color:var(--secondary-text-color)}</style><div class="c"><b>INCIDENTS</b><div class="v ${esc(String(a.state||''))}">${esc(state)}</div><div class="m">${a.incident_count||0} corrélé(s) · ✕ ${c.error||0} · ⚠ ${c.warning||0}</div></div></ha-card>`;}}
snDefine('show-network-incident-card',ShowNetworkIncidentCard);
class ShowNetworkPreShowCard extends HTMLElement{setConfig(c){this.config=c||{}}set hass(v){this._hass=v;this.render()}getCardSize(){return 2}render(){if(!this._hass)return;const st=Object.values(this._hass.states||{}).find(x=>x.entity_id.endsWith('_pre_show')),a=st?.attributes||{},state=String(a.state||st?.state||'CHECK').toUpperCase(),checks=a.checks||[],fails=checks.filter(x=>x.status==='fail').length,unk=checks.filter(x=>x.status==='unknown').length;this.innerHTML=`<ha-card><style>.c{padding:13px}.v{font-size:25px;font-weight:900}.READY{color:#68df9a}.CHECK{color:#e5bf6b}.NOT_READY{color:#ef7777}.m{font-size:11px;color:var(--secondary-text-color)}</style><div class="c"><b>PRE-SHOW <span class="m">${a.profile_enabled?'profil actif':'optionnel'}</span></b><div class="v ${esc(state)}">${esc(state)}</div><div class="m">${fails} échec(s) · ${unk} inconnu(s) · jamais bloquant</div></div></ha-card>`;}}
snDefine('show-network-pre-show-card',ShowNetworkPreShowCard);
window.customCards=window.customCards||[];for(const c of [['show-network-incident-card','Show Network · Incidents'],['show-network-pre-show-card','Show Network · Pre-Show']])if(!window.customCards.some(x=>x.type===c[0]))window.customCards.push({type:c[0],name:c[1],description:'Carte de synthèse Show Network fondée sur les états réels.'});

/* ===== Régie overview dashboard card (0.15.19-dev15) ===== */
class ShowNetworkRegieCard extends HTMLElement{
  setConfig(c){this.config=c||{};this.render()}
  set hass(v){this._hass=v;this.render()}
  getCardSize(){return 8}
  _mount(tag, cfg={}){
    const el=document.createElement(tag); el.setConfig(cfg); el.hass=this._hass; return el;
  }
  render(){
    if(!this._hass)return;
    this.replaceChildren();
    const card=document.createElement('ha-card');
    const wrap=document.createElement('div'); wrap.className='sn-regie';
    const style=document.createElement('style');
    style.textContent=`.sn-regie{padding:14px}.sn-head{display:flex;align-items:end;justify-content:space-between;gap:12px;margin:0 2px 12px}.sn-title{font-size:20px;font-weight:800}.sn-sub{font-size:12px;color:var(--secondary-text-color)}.sn-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(205px,1fr));gap:10px}.sn-wide{grid-column:span 2}@media(max-width:560px){.sn-wide{grid-column:span 1}.sn-grid{grid-template-columns:1fr 1fr}}@media(max-width:390px){.sn-grid{grid-template-columns:1fr}}`;
    const head=document.createElement('div');head.className='sn-head';head.innerHTML=`<div><div class="sn-title">${this.config.name||'Régie · Show Network'}</div><div class="sn-sub">Vue synthèse · données Home Assistant réelles · INCONNU si absent</div></div>`;
    const grid=document.createElement('div');grid.className='sn-grid';
    const items=[
      ['show-network-timecode-card',{name:'Timecode'},'sn-wide'],
      ['show-network-onair-card',{name:'PunchLight / On Air'},''],
      ['show-network-snapshot-card',{name:'Show Snapshot'},''],
      ['show-network-ma3-card',{name:'grandMA3 / MA-Net3'},''],
      ['show-network-dante-card',{name:'Dante'},''],
      ['show-network-ptp-card',{name:'PTP'},''],
      ['show-network-doctor-card',{name:'Doctor'},''],
      ['show-network-incident-card',{name:'Incidents'},''],
      ['show-network-pre-show-card',{name:'Pre-Show'},''],
      ['show-network-interfaces-card',{name:'Interfaces réseau'},''],
      ['show-network-switches-card',{name:'Switches / Ports'},''],
      ['show-network-amplifiers-card',{name:'Amplificateurs'},''],
      ['show-network-apple-card',{name:'Apple / Mac'},''],
      ['show-network-devices-card',{name:'Équipements'},''],
      ['show-network-projectors-card',{name:'Projecteurs'},''],
      ['show-network-power-card',{name:'Alimentations'},'']
    ];
    for(const [tag,cfg,cls] of items){const box=document.createElement('div');if(cls)box.className=cls;box.appendChild(this._mount(tag,cfg));grid.appendChild(box)}
    const universes=Array.isArray(this.config.dmx_entities)?this.config.dmx_entities:[];
    for(const d of universes){const cfg=typeof d==='string'?{entity:d}:{...d};if(!cfg.entity)continue;const box=document.createElement('div');box.appendChild(this._mount('show-network-dmx-card',cfg));grid.appendChild(box)}
    wrap.append(style,head,grid);card.appendChild(wrap);this.appendChild(card);
  }
}
snDefine('show-network-regie-card',ShowNetworkRegieCard);
window.customCards=window.customCards||[];
if(!window.customCards.some(c=>c.type==='show-network-regie-card'))window.customCards.push({type:'show-network-regie-card',name:'Show Network · Dashboard Régie',description:'Vue régie responsive: TC, On Air, MA3, Dante/PTP, Doctor, réseau, switches, amplis, Apple/Mac, équipements, projecteurs, alimentations et univers DMX choisis.'});

/* ===== dev23 operator readiness ===== */
class ShowNetworkIncidentCenterPanel extends HTMLElement{
 set hass(v){this._hass=v;this.render();} _state(){return Object.values(this._hass?.states||{}).find(x=>x.entity_id.endsWith('_incident_center'));}
 render(){if(!this._hass)return;const s=this._state(),a=s?.attributes||{},rows=(a.incidents||[]).slice().reverse(),cnt=a.counts||{};const rank=x=>x==='error'?3:x==='warning'?2:1;this.innerHTML=`<style>:host{display:block;color:#eef1f4}.box{padding:14px;border:1px solid #30363d;border-radius:12px;background:#111519}.head{display:flex;justify-content:space-between;gap:10px;align-items:center}.state{font-weight:900;font-size:24px}.summary{display:flex;gap:7px;flex-wrap:wrap;margin:10px 0}.pill{display:inline-block;margin:5px 4px 0 0;padding:4px 7px;border:1px solid #39414a;border-radius:999px;font-size:9px}.incident{margin-top:9px;padding:10px;border:1px solid #303841;border-radius:9px;background:#151a1f}.error{border-left:4px solid #ef7777}.warning{border-left:4px solid #e5bf6b}.info{border-left:4px solid #68737d}.muted{font-size:10px;color:#8f99a3}.sym{margin-top:6px;padding-top:6px;border-top:1px solid #252c32;font-size:10px}</style><div class="box"><div class="head"><div><b>INCIDENT CENTER</b><div class="muted">Corrélation temporelle fondée sur les preuves observées · aucune cause racine inventée.</div></div><div class="state">${esc(String(a.state||s?.state||'OK').toUpperCase())}</div></div><div class="summary"><span class="pill">${a.active_count||0} actif(s)</span><span class="pill">${a.acknowledged_count||0} reconnu(s)</span><span class="pill">${a.resolved_count||0} résolu(s)</span><span class="pill">✕ ${cnt.error||0} critique(s)</span><span class="pill">⚠ ${cnt.warning||0} avert.</span></div>${rows.sort((x,y)=>rank(y.severity)-rank(x.severity)).map(x=>`<details class="incident ${esc(x.severity||'info')}" ${x.severity==='error'?'open':''}><summary><b>${esc(x.anchor?.kind||'incident')} · ${esc(x.anchor?.event||'')}</b> <span class="muted">${esc(x.ts||'—')} · ${x.symptom_count||0} fait(s) · ${(x.device_ids||[]).length} équipement(s)</span></summary><div>${(x.families||[]).map(k=>`<span class="pill">${esc(k)}</span>`).join('')}</div><div class="sym">${(x.symptoms||[]).map(v=>`• ${esc(v)}`).join('<br>')||'Aucun détail supplémentaire.'}</div><div class="muted" style="margin-top:6px">État: <b>${esc(x.status||'ACTIVE')}</b> · occurrences ${x.occurrences||1} · durée ${x.duration_s==null?'—':esc(String(x.duration_s))+' s'}${x.acknowledged_at?' · reconnu '+esc(x.acknowledged_at):''}${x.resolved_at?' · résolu '+esc(x.resolved_at):''}</div><div class="muted" style="margin-top:6px">${esc(x.statement||'')}</div>${x.status==='ACTIVE'?`<button data-ack="${esc(x.id||'')}" style="margin-top:7px">Acquitter</button>`:''}</details>`).join('')||'<div class="incident">Aucun incident corrélé dans la fenêtre disponible.</div>'}</div>`;this.querySelectorAll('[data-ack]').forEach(b=>b.onclick=async()=>{if(!b.dataset.ack)return;b.disabled=true;try{await this._hass.callService('dmx_monitor','incident_acknowledge',{incident_id:b.dataset.ack});}finally{b.disabled=false;}});}}
snDefine('show-network-incident-center-panel',ShowNetworkIncidentCenterPanel);

class ShowNetworkPreShowPanel extends HTMLElement{
 constructor(){super();this._draft=null;this._pending=false;}
 set hass(v){this._hass=v;if(this.matches?.(':focus-within')){this._pending=true;return;}this.render();}
 _state(){return Object.values(this._hass?.states||{}).find(x=>x.entity_id.endsWith('_pre_show'));}
 render(){if(!this._hass)return;const s=this._state(),a=s?.attributes||{},checks=a.checks||[],p=a.profile||{},d=this._draft||{name:p.name||'',universes:(p.expected_dmx_universes||[]).join(','),devices:(p.expected_devices||[]).join(',')};const icon=x=>x==='pass'?'✓':x==='fail'?'✕':'?';this.innerHTML=`<style>:host{display:block;color:#eef1f4}.box{padding:14px;border:1px solid #30363d;border-radius:12px;background:#111519}.hero{display:flex;justify-content:space-between;align-items:center}.big{font-size:30px;font-weight:900}.READY{color:#68df9a}.NOT_READY{color:#ef7777}.CHECK{color:#e5bf6b}.check{display:grid;grid-template-columns:30px 180px 1fr;gap:8px;padding:9px 0;border-bottom:1px solid #252c32;font-size:11px}.pass{color:#68df9a}.fail{color:#ef7777}.unknown{color:#e5bf6b}.muted{font-size:10px;color:#8f99a3}.profile{margin:12px 0;padding:10px;border:1px solid #30363d;border-radius:9px;background:#151a1f}.prow{display:flex;gap:8px;flex-wrap:wrap;align-items:center}input{background:#0f1317;color:#eef1f4;border:1px solid #3a434c;border-radius:6px;padding:7px}button{background:#202830;color:#eef1f4;border:1px solid #46515c;border-radius:6px;padding:7px;cursor:pointer}</style><div class="box"><div class="hero"><div><b>PRE-SHOW CHECK</b><div class="muted">READY exige que tous les contrôles applicables soient réellement vérifiés. UNKNOWN n'est jamais PASS.</div></div><div class="big ${esc(a.state||'CHECK')}">${esc(a.state||s?.state||'CHECK')}</div></div><div class="profile"><div class="prow"><b>PROFIL SPECTACLE — ${a.profile_enabled?'ACTIF':'OPTIONNEL / INACTIF'}</b><span class="muted">Diagnostic uniquement · jamais bloquant</span></div><div class="prow" style="margin-top:8px"><input id="pn" placeholder="Nom" value="${esc(d.name)}"><input id="pu" placeholder="Univers: 1,2,10" value="${esc(d.universes)}"><input id="pd" placeholder="Appareils attendus, séparés par ," value="${esc(d.devices)}"><button id="pen">Enregistrer + activer</button><button id="pdis">Désactiver</button></div><div class="muted" style="margin-top:6px">Les attentes avancées restent configurables via le service Home Assistant pre_show_profile_set.</div></div>${checks.map(c=>`<div class="check"><b class="${esc(c.status)}">${icon(c.status)}</b><b>${esc(c.title||c.id)}</b><span>${esc(c.detail||'')}</span></div>`).join('')}</div>`;const sync=()=>{this._draft={name:this.querySelector('#pn')?.value||'',universes:this.querySelector('#pu')?.value||'',devices:this.querySelector('#pd')?.value||''}};this.querySelectorAll('#pn,#pu,#pd').forEach(x=>x.addEventListener('input',sync));this.addEventListener('focusout',()=>{setTimeout(()=>{if(this._pending&&!this.matches(':focus-within')){this._pending=false;this.render();}},0)},{once:true});const en=this.querySelector('#pen'),dis=this.querySelector('#pdis');if(en)en.onclick=async()=>{sync();await this._hass.callService('dmx_monitor','pre_show_profile_set',{enabled:true,name:this._draft.name,expected_dmx_universes:this._draft.universes,expected_devices:this._draft.devices});this._draft=null;};if(dis)dis.onclick=async()=>{await this._hass.callService('dmx_monitor','pre_show_profile_disable',{});};}
}
snDefine('show-network-pre-show-panel',ShowNetworkPreShowPanel);
