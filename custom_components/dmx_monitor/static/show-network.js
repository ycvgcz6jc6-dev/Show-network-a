/* Show Network frontend bundle - generated from the modular panels. */

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
customElements.define("control-sources-panel",ControlSourcesPanel);


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
customElements.define("show-network-fingerprint",ShowNetworkFingerprint);


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
:host{display:block;background:#0a0d10;color:#eef1f4;font-family:Inter,system-ui,sans-serif;padding:18px;box-sizing:border-box}.head{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;margin-bottom:14px}.title{font-size:24px;font-weight:800}.sub{font-size:11px;color:#89939d;margin-top:4px}.tools{display:flex;gap:8px;flex-wrap:wrap}.tool,input,select{background:#11161b;color:#eef1f4;border:1px solid #303942;border-radius:8px;padding:9px 10px}.tool{cursor:pointer}.primary{background:#1268a5;border-color:#2586c8}.filters{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:12px}.pill{padding:7px 10px;border:1px solid #303942;border-radius:999px;background:#11161b;color:#cbd2d8;cursor:pointer;font-size:10px}.pill.active{background:#164d70;border-color:#2586c8;color:#fff}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}.brand{background:#11161b;border:1px solid #29313a;border-radius:12px;padding:13px;display:grid;grid-template-columns:56px 1fr;gap:11px;min-height:92px}.logo{width:56px;height:56px;border:1px solid #303942;border-radius:9px;background:#0a0d10;display:flex;align-items:center;justify-content:center;overflow:hidden;font-size:15px;font-weight:800;color:#7ed7ff}.logo img{width:100%;height:100%;object-fit:contain}.name{font-weight:750}.cat{font-size:9px;color:#8f99a3;margin-top:4px;line-height:1.5}.actions{display:flex;gap:6px;margin-top:8px;flex-wrap:wrap}.mini{font-size:9px;padding:5px 7px;border-radius:6px;background:#171d23;color:#dce3e8;border:1px solid #34404a;cursor:pointer}.danger{color:#ff9b9b}.empty{padding:25px;border:1px dashed #39444e;border-radius:10px;color:#8f99a3}.note{margin:12px 0;padding:10px 12px;border-left:3px solid #2a8bd0;background:#10161b;color:#aeb8c1;font-size:10px;line-height:1.5}.dialog{position:fixed;inset:0;background:#000a;display:flex;align-items:center;justify-content:center;z-index:20}.modal{width:min(560px,92vw);background:#11161b;border:1px solid #3a4651;border-radius:14px;padding:16px;box-shadow:0 20px 60px #000}.modal h3{margin:0 0 12px}.form{display:grid;gap:9px}.row{display:grid;grid-template-columns:1fr 1fr;gap:8px}.modal label{font-size:10px;color:#8f99a3}.modal input,.modal select{width:100%;box-sizing:border-box;margin-top:4px}.preview{width:72px;height:72px;border:1px solid #303942;border-radius:8px;object-fit:contain;background:#0a0d10}.foot{display:flex;justify-content:flex-end;gap:8px;margin-top:12px}@media(max-width:700px){.head{display:block}.tools{margin-top:10px}.row{grid-template-columns:1fr}}
</style><div class="head"><div><div class="title">CONSTRUCTEURS</div><div class="sub">Catalogue commun Lumière · Son · Vidéo · Réseaux · Contrôle · Intercom</div></div><div class="tools"><input id="search" placeholder="Rechercher une marque…" value="${esc(q)}"><button class="tool primary" id="add">＋ Ajouter une marque</button></div></div>
<div class="note">Les fabricants et modèles détectés servent à qualifier l’équipement. Le logo est uniquement une identité visuelle : aucune identification n’est déclarée sur la seule présence d’un logo. Les logos intégrés doivent provenir d’une source autorisée ; les logos personnalisés PNG restent locaux à ce navigateur.</div>
<div class="filters">${[['all','Toutes'],...Object.entries(catalog.categories||{})].map(([k,v])=>`<button class="pill ${selected===k?'active':''}" data-filter="${k}">${v}</button>`).join('')}</div>
<div class="grid">${visible.length?visible.map(b=>{const logo=b.logo||'';return `<div class="brand"><div class="logo">${logo?`<img src="${esc(logo)}" alt="">`:esc(b.name.split(/\\s+/).map(x=>x[0]).slice(0,2).join('').toUpperCase())}</div><div><div class="name">${esc(b.name)} ${b.custom?'<span style="font-size:9px;color:#75d7a0">PERSONNALISÉ</span>':''}</div><div class="cat">${(b.categories||[]).map(x=>catalog.categories?.[x]||x).join(' · ')}</div><div class="actions">${b.website?`<button class="mini" data-open="${esc(b.website)}">Site</button>`:''}${b.custom?`<button class="mini danger" data-del="${esc(b.key)}">Supprimer</button>`:''}</div></div></div>`}).join(''):'<div class="empty">Aucun constructeur pour ce filtre.</div>'}</div>`;
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
    document.body.appendChild(wrap); const file=wrap.querySelector('#bf'),preview=wrap.querySelector('#bp'); let data='';
    file.onchange=()=>{const f=file.files?.[0];if(!f)return;if(f.type!=='image/png'||f.size>1024*1024){alert('PNG uniquement, 1 Mo maximum.');file.value='';return;}const r=new FileReader();r.onload=()=>{data=r.result;preview.src=data};r.readAsDataURL(f)};
    wrap.querySelector('#bu').oninput=e=>{if(e.target.value)preview.src=e.target.value};
    wrap.querySelector('#cancel').onclick=()=>wrap.remove();
    wrap.querySelector('#save').onclick=()=>{const name=wrap.querySelector('#bn').value.trim();if(!name){alert('Nom obligatoire.');return;}const key='custom_'+name.toLowerCase().replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'');const next=ShowNetworkBrandStore.custom().filter(b=>b.key!==key);next.push({key,name,categories:[wrap.querySelector('#bc').value],website:wrap.querySelector('#bw').value.trim(),logo:data||wrap.querySelector('#bu').value.trim()});ShowNetworkBrandStore.saveCustom(next);wrap.remove();this.render()};
  }
}
customElements.define('show-network-brand-catalog',ShowNetworkBrandCatalog);

/* ===== device-inventory-panel.js ===== */
class ShowNetworkInventory extends HTMLElement {
  setConfig(c){this._config=c||{}}
  set hass(h){this._hass=h; this.render()}
  async render(){
    if(!this._hass)return;
    const st=this._hass.states;
    const brands=await ShowNetworkBrandStore.all();
    const brandFor=(name)=>{const n=String(name||'').toLowerCase();return brands.find(b=>n&&b.name.toLowerCase()===n)||brands.find(b=>n&&n.includes(b.name.toLowerCase())||n&&b.name.toLowerCase().includes(n));};
    const entity=Object.values(st).find(x=>x.entity_id.endsWith('_device_inventory'));
    const rows=entity?.attributes?.devices||[];
    this.innerHTML=`<style>
    :host{display:block;background:#0b0d10;color:#eef1f4;font-family:Inter,system-ui,sans-serif;padding:18px;box-sizing:border-box}
    .top{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:14px}.title{font-size:22px;font-weight:750}.sub{font-size:11px;color:#89939d;margin-top:3px}
    .tools{display:flex;gap:8px;flex-wrap:wrap}.pill{padding:7px 10px;border:1px solid #30363d;border-radius:999px;background:#15191e;font-size:10px}
    table{width:100%;border-collapse:separate;border-spacing:0;background:#11151a;border:1px solid #2b3138;border-radius:12px;overflow:hidden}
    th,td{padding:10px;border-bottom:1px solid #242a30;text-align:left;font-size:11px}th{font-size:9px;color:#8b949e;text-transform:uppercase;background:#15191e}tr:last-child td{border-bottom:0}
    button{background:#1a2026;color:#eef1f4;border:1px solid #38414a;border-radius:7px;padding:6px 9px;cursor:pointer}.muted{color:#8b949e}.ok{color:#63d89a}.warn{color:#e4bb68}
    .edit{display:grid;grid-template-columns:repeat(6,minmax(90px,1fr));gap:7px;padding:10px;background:#0f1317}.edit input{min-width:0;background:#0b0d10;color:#eee;border:1px solid #343b43;border-radius:6px;padding:7px;font-size:10px}
    @media(max-width:900px){.edit{grid-template-columns:repeat(2,1fr)}th:nth-child(3),td:nth-child(3){display:none}}
    </style><div class="top"><div><div class="title">DEVICE INVENTORY</div><div class="sub">Découverte automatique + personnalisation manuelle · l'IP reste une donnée réseau</div></div><div class="tools"><span class="pill">${rows.length} appareils</span><span class="pill">☑ auto · ✎ manuel</span></div></div>
    <table><thead><tr><th>Nom</th><th>Fabricant</th><th>Modèle</th><th>Rôle</th><th>Emplacement</th><th>IP</th><th>État</th><th></th></tr></thead><tbody>${rows.length?rows.map((r,i)=>{const m=r.display_manufacturer||r.manufacturer||'';const b=brandFor(m);return `<tr><td>${esc(r.display_name||r.hostname||r.unique_id)}</td><td>${b?.logo?`<img src="${esc(b.logo)}" alt="" style="width:24px;height:24px;object-fit:contain;vertical-align:middle;margin-right:6px;border-radius:4px">`:''}${esc(m||'—')}</td><td>${esc(r.display_model||r.model||'—')}</td><td>${esc(r.custom_role||'—')}</td><td>${esc(r.custom_location||'—')}</td><td class="muted">${esc(r.ip||'—')}</td><td class="${r.hidden?'warn':'ok'}">${r.hidden?'MASQUÉ':'VISIBLE'}</td><td><button data-i="${i}">Modifier</button></td></tr>`}).join(''):'<tr><td colspan="8" class="muted">Aucun équipement découvert.</td></tr>'}</tbody></table>`;
    this.querySelectorAll('button[data-i]').forEach(b=>b.onclick=()=>this.editor(rows[+b.dataset.i]));
  }
  editor(r){
    const wrap=document.createElement('div'); wrap.className='edit'; wrap.innerHTML=`<input data-k="name" placeholder="Nom" value="${esc(r.custom_name||'')}"><input data-k="manufacturer" placeholder="Fabricant" value="${esc(r.custom_manufacturer||'')}"><input data-k="model" placeholder="Modèle" value="${esc(r.custom_model||'')}"><input data-k="role" placeholder="Rôle spectacle" value="${esc(r.custom_role||'')}"><input data-k="location" placeholder="Emplacement" value="${esc(r.custom_location||'')}"><label style="font-size:10px;display:flex;gap:5px;align-items:center"><input type="checkbox" data-k="hidden" ${r.hidden?'checked':''}> Masquer</label><button data-save>Enregistrer</button><button data-cancel>Annuler</button>`;
    this.prepend(wrap); wrap.querySelector('[data-cancel]').onclick=()=>wrap.remove(); wrap.querySelector('[data-save]').onclick=async()=>{const data={unique_id:r.unique_id};wrap.querySelectorAll('[data-k]').forEach(x=>data[x.dataset.k]=x.type==='checkbox'?x.checked:x.value);await this._hass.callService('dmx_monitor','set_device_override',data);wrap.remove()};
  }
}
function esc(v){return String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
customElements.define('show-network-inventory',ShowNetworkInventory);


/* ===== discovery-panel.js ===== */
class ShowNetworkDiscovery extends HTMLElement {
  connectedCallback(){this.innerHTML=`
  <style>
  :host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}
  h2{margin:0 0 5px}.sub{color:#8d969f;font-size:11px;margin-bottom:15px}
  .bar{display:flex;gap:8px;align-items:center;background:#15181c;border:1px solid #2c3239;border-radius:10px;padding:12px}
  button{background:#23282e;color:#eee;border:1px solid #3a4148;border-radius:7px;padding:8px 12px}
  button:hover{background:#30363d}.table{margin-top:12px;border:1px solid #2c3239;border-radius:10px;overflow:hidden}
  .row{display:grid;grid-template-columns:150px 1fr 130px 130px;gap:10px;padding:10px 12px;border-bottom:1px solid #282d33;font-size:12px}
  .head{color:#8d969f;background:#15181c;font-size:10px;text-transform:uppercase}
  .good{color:#65dc99}.muted{color:#8d969f}
  </style>
  <h2>AUTO DISCOVERY</h2>
  <div class="sub">Recherche multi-source · DHCP · mDNS/Zeroconf · sondes TCP prudentes</div>
  <div class="bar"><span class="muted">No IP list required.</span><button>SCAN NETWORK</button></div>
  <div class="table">
   <div class="row head"><span>IP</span><span>SERVICES</span><span>SOURCE</span><span>CONFIDENCE</span></div>
   <div class="row"><span class="muted">Waiting…</span><span>—</span><span>—</span><span>—</span></div>
  </div>`}
}
customElements.define("show-network-discovery",ShowNetworkDiscovery);


/* ===== dmx-ha-mapping-panel.js ===== */
class DmxHaMappingPanel extends HTMLElement {
  set hass(h){this._hass=h;this.render()}
  call(mapping_id,enabled){this._hass.callService('dmx_monitor','set_dmx_ha_mapping_highlight',{mapping_id,enabled})}
  render(){
    if(!this._hass)return;
    const st=Object.values(this._hass.states).find(x=>x.entity_id.endsWith('dmx_ha_mappings_total'));
    const mappings=(st&&st.attributes&&st.attributes.mappings)||[];
    this.innerHTML=`<style>:host{display:block;font-family:Inter,system-ui,sans-serif}.wrap{padding:16px}.row{display:grid;grid-template-columns:1fr 100px 1fr 170px;gap:8px;align-items:center;padding:9px 0;border-bottom:1px solid #2c3239;font-size:12px}.muted{color:#8d969f}.btn{background:#171b20;color:#fff;border:1px solid #3a4148;border-radius:6px;padding:6px 9px;cursor:pointer}.curve{font-size:10px}</style><ha-card header="DMX → Home Assistant"><div class="wrap"><div class="muted">Liaison DMX → HA · Highlight temporaire · courbe de dimmer</div>${mappings.length?`<div class="row"><b>Mapping</b><b>Canaux</b><b>Entité</b><b>Action</b></div>${mappings.map(m=>`<div class="row"><span>${m.mapping_id}</span><span>U${m.universe} · ${(m.channels||[]).join(',')}</span><span>${m.entity_id||'—'}<br><span class="muted curve">courbe: ${m.dimmer_curve||'linear'}</span></span><span><button class="btn" data-id="${m.mapping_id}" data-on="1">HIGHLIGHT</button> <button class="btn" data-id="${m.mapping_id}" data-on="0">RESTORE</button></span></div>`).join('')}`:'<div style="padding-top:14px">Aucun mapping configuré.</div>'}</div></ha-card>`;
    this.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>this.call(b.dataset.id,b.dataset.on==='1')));
  }
}
customElements.define('dmx-ha-mapping-panel',DmxHaMappingPanel)


/* ===== dmx-live-view.js ===== */
class DmxLiveView extends HTMLElement {
 connectedCallback(){this.innerHTML=`
 <style>
 :host{display:block;background:#090b0e;color:#eee;font-family:Inter,system-ui,sans-serif;padding:16px}
 h2{margin:0}.sub{font-size:10px;color:#8d969f;margin:4px 0 12px}
 .bar{display:flex;gap:8px;flex-wrap:wrap}.pill{background:#15181c;border:1px solid #2c3239;border-radius:6px;padding:7px 10px;font-size:10px}
 .grid{display:grid;grid-template-columns:repeat(16,1fr);gap:3px;margin-top:12px}
 .ch{height:34px;background:#252a30;border-radius:3px;text-align:center;font-size:9px;padding-top:3px;box-sizing:border-box}
 .active{background:#1d5c3a;color:#fff}.num{display:block;font-size:10px;font-weight:700;margin-top:5px}
 </style>
 <h2>DMX VIEW</h2><div class="sub">LIVE RECEIVE · sACN / Art-Net · NO OUTPUT</div>
 <div class="bar"><span class="pill">Universe —</span><span class="pill">Source —</span><span class="pill">Rate —</span><span class="pill">Active —/512</span><span class="pill">Selection: 1-8,12</span></div>
 <div class="grid">${Array.from({length:128},(_,i)=>`<div class="ch ${i%11===0?'active':''}">${i+1}<span class="num">${i%11===0?Math.floor((i*7)%256):0}</span></div>`).join('')}</div>`}
}
customElements.define("dmx-live-view",DmxLiveView);


/* ===== dmx-monitor-panel.js ===== */
class DmxMonitorPanel extends HTMLElement {
  constructor(){super();this.attachShadow({mode:"open"});this.universe=null;this.values=Array(512).fill(0);this.source="—";this.protocol="—";this.rate=0;this.active=0;this.priority=null;this.sequence=null;this.selected=new Set();this._framePending=false;this._lastSig="";this._renderTimer=null;}
  connectedCallback(){this.render();}
  set hass(hass){this._hass=hass;this.syncLive();}
  syncLive(){
    if(this._framePending)return;
    this._framePending=true;
    const run=()=>{this._framePending=false;this._syncLiveNow();};
    if(typeof requestAnimationFrame==="function") requestAnimationFrame(run); else this._renderTimer=setTimeout(run,100);
  }
  _syncLiveNow(){
    const states=this._hass?.states||{};
    const state=Object.values(states).find(s=>Array.isArray(s.attributes?.universes));
    const list=state?.attributes?.universes||[];
    if(!list.length){this.render();return;}
    if(this.universe==null || !list.some(x=>Number(x.universe)===Number(this.universe))) this.universe=Number(list[0].universe)||1;
    const u=list.find(x=>Number(x.universe)===Number(this.universe))||list[0];
    this.universe=Number(u.universe)||1; this.source=u.source||"—"; this.protocol=u.protocol||"—";
    this.rate=Number(u.packet_rate||0); this.active=Number(u.active_channels||0); this.priority=u.priority; this.sequence=u.sequence;
    if(Array.isArray(u.values)) this.values=u.values.slice(0,512).concat(Array(512)).slice(0,512);
    else if(u.values_b64){try{const bin=atob(u.values_b64);this.values=Array.from(bin, c=>c.charCodeAt(0)).slice(0,512).concat(Array(512)).slice(0,512)}catch(e){this.values=Array(512).fill(0)}}
    else this.values=Array(512).fill(0);
    this._universes=list;
    const sig=`${this.universe}|${this.source}|${this.protocol}|${this.rate}|${this.active}|${this.priority}|${this.sequence}|${u.values_b64||JSON.stringify(u.values||[])}`;
    if(sig===this._lastSig)return;
    this._lastSig=sig; this.render();
  }
  render(){
    const css=`:host{display:block;background:#0c0e10;color:#e8eaed;min-height:100vh;font-family:Inter,system-ui,sans-serif}.top{background:#171a1e;border-bottom:1px solid #30353b;padding:16px 20px;position:sticky;top:0;z-index:5}.title{font-size:22px;font-weight:700}.sub{color:#8f98a3;font-size:11px;margin-top:3px}.tools{display:flex;gap:7px;flex-wrap:wrap;margin-top:12px}.pill{background:#20242a;border:1px solid #343a41;border-radius:7px;padding:7px 10px;font-size:11px}.ok{border-color:#2d714b}.select{background:#20242a;color:#eee;border:1px solid #343a41;border-radius:7px;padding:7px}.body{padding:14px}.card{background:#15181c;border:1px solid #292e34;border-radius:9px;margin-bottom:12px;overflow:hidden}.bar{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:12px 14px;background:#191c20;border-bottom:1px solid #292e34}.muted{color:#8d969f;font-size:11px}.grid{display:grid;grid-template-columns:repeat(32,minmax(23px,1fr));gap:2px;padding:10px}.cell{height:45px;border-radius:3px;background:#292e34;display:flex;flex-direction:column;align-items:center;justify-content:center;cursor:pointer;user-select:none}.cell.active{background:#12472f}.cell.low{background:#303326}.num{font-size:12px;font-weight:700}.ch{font-size:8px;color:#8e969f;margin-top:2px}.active .num{color:#6ae59e}.selected{outline:2px solid #e5e7eb}.foot{padding:10px 14px;color:#8f98a3;font-size:11px}@media(max-width:950px){.grid{grid-template-columns:repeat(16,minmax(23px,1fr));}}`;
    let cells=""; for(let i=1;i<=512;i++){const v=Number(this.values[i-1]||0),cls=v>10?"active":(v>0?"low":""),sel=this.selected.has(i)?" selected":"";cells+=`<div class="cell ${cls}${sel}" data-ch="${i}"><span class="num">${v}</span><span class="ch">CH ${i}</span></div>`;}
    const opts=(this._universes||[]).map(u=>`<option value="${Number(u.universe)}">U${Number(u.universe)} · ${u.protocol||"?"} · ${u.source||"?"}</option>`).join("");
    this.shadowRoot.innerHTML=`<style>${css}</style><header class="top"><div class="title">DMX View</div><div class="sub">LIGHT / DMX MONITOR · RECEIVE ONLY · FR / EN</div><div class="tools"><select class="select" id="uni">${opts||'<option>—</option>'}</select><span class="pill ok">● LIVE</span><span class="pill">${this.protocol}</span><span class="pill">Source ${this.source}</span><span class="pill">${this.rate.toFixed(1)} pkt/s</span><span class="pill">${this.active} active</span><span class="pill">Priority ${this.priority??"—"}</span><span class="pill">Seq ${this.sequence??"—"}</span></div></header><main class="body"><section class="card"><div class="bar"><div><b>Universe ${this.universe||"—"} · DMX 1–512</b><div class="muted">Cliquez sur les canaux pour les sélectionner · Click channels to select</div></div></div><div class="grid">${cells}</div><div class="foot">Sélection : ${[...this.selected].sort((a,b)=>a-b).join(", ")||"—"} · Aucun paquet n'est émis.</div></section></main>`;
    const uni=this.shadowRoot.querySelector('#uni'); if(uni) uni.value=String(this.universe||"");
    uni?.addEventListener('change',e=>{this.universe=Number(e.target.value);this.syncLive();});
    this.shadowRoot.querySelectorAll('.cell').forEach(c=>c.addEventListener('click',()=>{const ch=Number(c.dataset.ch);this.selected.has(ch)?this.selected.delete(ch):this.selected.add(ch);c.classList.toggle('selected',this.selected.has(ch));this.dispatchEvent(new CustomEvent('dmx-channel-selected',{detail:{channel:ch,universe:this.universe,source:this.source,protocol:this.protocol},bubbles:true,composed:true}));this.shadowRoot.querySelector('.foot').textContent=`Sélection : ${[...this.selected].sort((a,b)=>a-b).join(', ')||'—'} · Aucun paquet n'est émis.`;}));
  }
}
customElements.define("dmx-monitor-panel",DmxMonitorPanel);


/* ===== enttec-panel.js ===== */
class EnttecPanel extends HTMLElement {
  setConfig(c){this.config=c||{}; this.render();}
  set hass(h){this._h=h; this.render();}
  render(){if(!this.shadowRoot){this.attachShadow({mode:"open"});} const h=this._h; const sw=h?.states?.[this.config?.entity||"switch.dmx_monitor_enttec_dmx_input_listen"]; const on=sw?.state==="on"; this.shadowRoot.innerHTML=`<style>ha-card{padding:16px} .row{display:flex;align-items:center;justify-content:space-between;gap:16px}.title{font-size:18px;font-weight:600}.state{opacity:.8;margin-top:4px}button{border:0;border-radius:8px;padding:10px 16px;font-weight:600;cursor:pointer}</style><ha-card><div class="row"><div><div class="title">ENTTEC DMX Input</div><div class="state">${on?"🟢 Écoute active":"⚪ Écoute désactivée"}</div></div><button id="toggle">${on?"Désactiver":"Activer l’écoute"}</button></div></ha-card>`; this.shadowRoot.querySelector('#toggle')?.addEventListener('click',()=>{if(!h||!sw)return; h.callService('switch',on?'turn_off':'turn_on',sw.entity_id);});}
}
customElements.define('enttec-panel',EnttecPanel);

/* ===== ma-inspector-panel.js ===== */
class MaInspectorPanel extends HTMLElement {
  constructor(){super();this.attachShadow({mode:"open"});this._hass=null;this.data={};}
  set hass(h){this._hass=h;this.sync();}
  sync(){
    const states=this._hass?.states||{};
    const st=Object.values(states).find(x=>x.attributes?.ma_remote);
    this.data=st?.attributes?.ma_remote||{};
    this.render();
  }
  connectedCallback(){this.render();}
  render(){
    const d=this.data||{}, stations=d.stations||[], osc=d.osc||{}, diag=d.diagnostics||{};
    const css=`:host{display:block;background:#0d0f11;color:#e8eaed;min-height:100vh;font-family:Inter,system-ui,sans-serif}.head{padding:18px 22px;background:#17191d;border-bottom:1px solid #30343a}.title{font-size:23px;font-weight:700}.sub{color:#8e969f;font-size:11px;margin-top:3px}.body{padding:14px}.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}.card{background:#16191d;border:1px solid #2d3238;border-radius:9px;padding:13px}.big{font-size:20px;font-weight:700}.muted{font-size:11px;color:#8e969f}.ok{color:#69df9b}.warn{color:#e7bd68}.table{margin-top:12px;background:#16191d;border:1px solid #2d3238;border-radius:9px;overflow:hidden}.row{display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr 1fr 1.5fr;padding:10px 12px;border-bottom:1px solid #282d33;font-size:11px}.headrow{background:#1b1f24;color:#929aa3;font-weight:600}.diag{margin-top:12px}.link{color:#9bc5ff}@media(max-width:1000px){.cards{grid-template-columns:repeat(2,1fr)}.row{grid-template-columns:1.4fr 1fr 1fr}}`;
    const rows=stations.length?stations.map(x=>`<div class="row"><span>${x.name||"MA"}</span><span>${x.ip||"—"}</span><span>${x.session_index??"UNKNOWN"}</span><span class="${x.state==='LIVE'?'ok':'warn'}">${x.state||"UNKNOWN"}</span><span>${x.age_s??"—"} s</span><span><a class="link" target="_blank" href="${x.web_remote_url||'#'}">Web Remote</a></span></div>`).join(""):`<div class="row"><span>—</span><span>—</span><span>UNKNOWN</span><span>NO DATA</span><span>—</span><span>—</span></div>`;
    this.shadowRoot.innerHTML=`<style>${css}</style><header class="head"><div class="title">MA Remote</div><div class="sub">grandMA3 · MA-NET3 · PASSIVE DIAGNOSTICS · NO SESSION JOIN / NO CONTROL</div></header><main class="body"><div class="cards"><div class="card"><div class="muted">MA-Net3</div><div class="big ok">${stations.length?'● ACTIVE':'○ WAITING'}</div><div class="muted">UDP 30020</div></div><div class="card"><div class="muted">Stations</div><div class="big">${d.station_count||0}</div></div><div class="card"><div class="muted">Live</div><div class="big">${d.live_stations||0}</div></div><div class="card"><div class="muted">Sessions</div><div class="big">${d.session_count||0}</div><div class="muted">passive only</div></div><div class="card"><div class="muted">OSC</div><div class="big">${osc.default_port||8000}</div><div class="muted">${osc.transport||'UDP/TCP'}</div></div></div><div class="table"><div class="row headrow"><span>Station</span><span>IP</span><span>Session</span><span>State</span><span>Age</span><span>Web Remote</span></div>${rows}</div><div class="table diag"><div class="row headrow"><span>Diagnostic</span><span>Result</span><span>Protocol</span><span>Detail</span><span></span><span></span></div><div class="row"><span>Session join</span><span class="ok">DISABLED</span><span>MA-Net3</span><span>No join / no control</span><span></span><span></span></div><div class="row"><span>Web Remote probe</span><span class="ok">DISABLED</span><span>HTTP</span><span>URL candidate only</span><span></span><span></span></div><div class="row"><span>OSC commands</span><span class="ok">DISABLED</span><span>OSC</span><span>Info only · default ${osc.default_port||8000}</span><span></span><span></span></div></div></main>`;
  }
}
customElements.define("ma-inspector-panel",MaInspectorPanel);


/* ===== osc-learn-panel.js ===== */
class OscLearnPanel extends HTMLElement {
 connectedCallback(){this.innerHTML=`
 <style>
 :host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}
 h2{margin:0}.sub{font-size:11px;color:#8d969f;margin:5px 0 14px}
 .toolbar{background:#15181c;border:1px solid #2c3239;border-radius:10px;padding:12px;display:flex;gap:8px;align-items:center}
 button{background:#252a30;border:1px solid #3a4148;color:#eee;border-radius:6px;padding:8px 12px}
 .learn{color:#65dc99;font-weight:700}.hint{color:#8d969f;font-size:10px}
 .row{display:grid;grid-template-columns:1.4fr .7fr .8fr .8fr 1fr;gap:8px;padding:10px;border-bottom:1px solid #282d33;font-size:11px}
 .table{margin-top:12px;background:#15181c;border:1px solid #2c3239;border-radius:10px;overflow:hidden}
 .head{color:#8d969f;font-size:9px;text-transform:uppercase}
 .tag{border:1px solid #3a4148;border-radius:4px;padding:3px 5px}
 </style>
 <h2>OSC LEARN</h2>
 <div class="sub">Bougez un fader ou appuyez sur un bouton : les messages reçus apparaissent automatiquement.</div>
 <div class="toolbar"><button>START LEARN</button><span class="hint">Aucune commande n'est envoyée. Les mappings appris ne sont pas activés automatiquement.</span></div>
 <div class="table">
  <div class="row head"><span>ADDRESS</span><span>TYPE</span><span>MIN</span><span>MAX</span><span>SUGGESTION</span></div>
  <div class="row"><span class="hint">Waiting for OSC…</span><span>—</span><span>—</span><span>—</span><span>—</span></div>
 </div>`}
}
customElements.define("osc-learn-panel",OscLearnPanel);


/* ===== osc-mapping-panel.js ===== */
class OscMappingPanel extends HTMLElement {
 connectedCallback(){this.innerHTML=`
 <style>
 :host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}
 h2{margin:0}.sub{font-size:11px;color:#8d969f;margin:5px 0 15px}
 .map{background:#15181c;border:1px solid #2c3239;border-radius:10px;padding:14px;margin-bottom:10px}
 .path{font-family:ui-monospace,monospace;font-size:12px}.arrow{color:#65dc99;padding:0 8px}
 .chips{display:flex;gap:6px;margin-top:10px;flex-wrap:wrap}.chip{border:1px solid #353b42;border-radius:5px;padding:4px 7px;font-size:10px;color:#b9c0c7}
 .good{color:#65dc99}.warn{color:#e6bd67}
 </style>
 <h2>OSC MAPPING ENGINE</h2>
 <div class="sub">CONTROL transversal · OSC → HA / LIGHT / AUDIO / MA / autres cibles</div>
 <div class="map">
  <div class="path">/show/lobby/color <span class="arrow">→</span> light.lobby <span class="arrow">→</span> rgb_color</div>
  <div class="chips"><span class="chip">OSC</span><span class="chip">RGB</span><span class="chip">deadband</span><span class="chip">rate limit</span><span class="chip good">READ/WRITE TARGET</span></div>
 </div>
 <div class="map">
  <div class="path">/show/lobby/brightness <span class="arrow">→</span> light.lobby <span class="arrow">→</span> brightness</div>
  <div class="chips"><span class="chip">0–1 → 0–255</span><span class="chip">invert optional</span></div>
 </div>
 <div class="map">
  <div class="path">/show/scene/01 <span class="arrow">→</span> scene.show_01</div>
  <div class="chips"><span class="chip">trigger</span><span class="chip good">HA</span></div>
 </div>
 <div class="map">
  <div class="path">/ma/... <span class="arrow">→</span> grandMA3 adapter</div>
  <div class="chips"><span class="chip warn">separate opt-in output</span><span class="chip">/cmd / attributes / executor</span></div>
 </div>`}
}
customElements.define("osc-mapping-panel",OscMappingPanel);


/* ===== osc-output-panel.js ===== */
class OscOutputPanel extends HTMLElement {
  connectedCallback(){
    const root=this.attachShadow({mode:'open'});
    root.innerHTML=`<style>:host{display:block;padding:14px;background:#111;color:#eee;font-family:system-ui} .row{display:flex;justify-content:space-between;gap:12px;padding:8px 0;border-bottom:1px solid #333}.ok{color:#6ee7a1}.off{color:#f0b36a} code{font-family:monospace}</style><h3>OSC OUTPUT</h3><div class="row"><span>Safety gate</span><b id="gate">OFF</b></div><div class="row"><span>Messages sent</span><b id="sent">0</b></div><div class="row"><span>Errors</span><b id="errors">0</b></div><div class="row"><span>Last target</span><code id="target">—</code></div><div class="row"><span>Last address</span><code id="address">—</code></div>`;
    this._root=root;
    this._handler=e=>this._update(e.detail?.data||{});
    window.addEventListener('hass-more-info',this._handler);
  }
  set hass(hass){this._hass=hass; this._update(hass?.states||{});}
  _update(data){const d=data?.osc_output_enabled!==undefined?data:null; if(!d)return; const g=this._root.getElementById('gate'); g.textContent=d.osc_output_enabled?'ON':'OFF'; g.className=d.osc_output_enabled?'ok':'off'; this._root.getElementById('sent').textContent=d.osc_sent??0; this._root.getElementById('errors').textContent=d.osc_errors??0; this._root.getElementById('target').textContent=d.osc_last_target||'—'; this._root.getElementById('address').textContent=d.osc_last_address||'—';}
}
customElements.define('osc-output-panel',OscOutputPanel);


/* ===== osc-source-profiles.js ===== */
class OscSourceProfiles extends HTMLElement {
 connectedCallback(){this.innerHTML=`
 <style>
 :host{display:block;background:#0b0d10;color:#eee;font-family:Inter,system-ui,sans-serif;padding:18px}
 h2{margin:0}.sub{font-size:11px;color:#8d969f;margin:5px 0 14px}
 .profiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
 .card{background:#15181c;border:1px solid #2c3239;border-radius:10px;padding:14px}.title{font-weight:700}.desc{font-size:11px;color:#aab1b8;margin:7px 0 10px;line-height:1.4}.tag{display:inline-block;border:1px solid #3a4148;border-radius:5px;padding:3px 6px;font-size:9px;margin:2px}.actions{margin-top:10px;border-top:1px solid #282d33;padding-top:8px;font-size:10px}.green{color:#65dc99}
 </style>
 <h2>OSC SHOW CONTROL BANK</h2><div class="sub">Profils documentés, cibles et commandes prêtes pour les automatisations Home Assistant.</div>
 <div class="profiles">
  <div class="card"><div class="title">🎛 grandMA3</div><div class="desc">Executors, faders, keys, encoders et /cmd.</div><span class="tag green">Output</span><span class="tag">Learn</span><span class="tag">/cmd</span><div class="actions">Profil documenté · cible + commande + paramètres.</div></div>
  <div class="card"><div class="title">🎛 grandMA2</div><div class="desc">Profil avec apprentissage des adresses réellement utilisées.</div><span class="tag">Learn</span><span class="tag">Custom</span><div class="actions">Les adresses dépendent de la configuration OSC.</div></div>
  <div class="card"><div class="title">🎚 ChamSys MagicQ</div><div class="desc">Playbacks, GO, Flash, Pause, Release, Execute et Blackout.</div><span class="tag green">GO</span><span class="tag">Fader</span><span class="tag">Flash</span><span class="tag">Execute</span><div class="actions">Banque basée sur les adresses OSC documentées MagicQ.</div></div>
  <div class="card"><div class="title">🎚 Yamaha RIVAGE PM</div><div class="desc">Banque issue de la spécification OSC RIVAGE PM.</div><span class="tag green">Cue</span><span class="tag">DCA</span><span class="tag">Parameter</span><div class="actions">Paramètres uniquement lorsqu'ils sont documentés.</div></div>
  <div class="card"><div class="title">🎥 QLab</div><div class="desc">GO, Panic, Save et contrôle des updates.</div><span class="tag green">GO</span><span class="tag">Panic</span><span class="tag">Updates</span><div class="actions">UDP/TCP selon les capacités et la configuration QLab.</div></div>
  <div class="card"><div class="title">🎚 Midas</div><div class="desc">Profil console avec Learn et commandes dépendantes du modèle.</div><span class="tag">Learn</span><span class="tag">Model</span><div class="actions">Aucune adresse inventée.</div></div>
  <div class="card"><div class="title">🎚 Soundcraft</div><div class="desc">Profil console avec Learn et commandes dépendantes du modèle.</div><span class="tag">Learn</span><span class="tag">Model</span><div class="actions">Aucune adresse inventée.</div></div>
  <div class="card"><div class="title">🎛 ETC Eos</div><div class="desc">Profil catalogue avec apprentissage des commandes spécifiques.</div><span class="tag">Learn</span><span class="tag">Custom</span><div class="actions">Adresses selon configuration.</div></div>
  <div class="card"><div class="title">🎛 Avolites</div><div class="desc">Profil catalogue avec apprentissage des commandes spécifiques.</div><span class="tag">Learn</span><span class="tag">Custom</span><div class="actions">Adresses selon console/version.</div></div>
  <div class="card"><div class="title">◎ OSC générique</div><div class="desc">Adresse et arguments libres pour tout équipement OSC.</div><span class="tag">Custom</span><span class="tag">Learn</span><div class="actions">Toujours disponible.</div></div>
 </div>`}
}
customElements.define("osc-source-profiles",OscSourceProfiles);


/* ===== rule-builder.js ===== */
class ShowNetworkRuleBuilder extends HTMLElement {
  constructor(){super();this.selected=new Set();this.rules=[];this._hass=null;this.editing=null;this._onDmx=e=>this.acceptDmxSelection(e)}
  connectedCallback(){window.addEventListener('dmx-channel-selected',this._onDmx);this.render();this.sync()}
  disconnectedCallback(){window.removeEventListener('dmx-channel-selected',this._onDmx)}
  set hass(v){this._hass=v;this.sync();this.refreshTargets()}
  acceptDmxSelection(e){const d=e.detail||{};if(!d.channel)return;if(d.universe)this.q('#universe').value=d.universe;if(d.source)this.q('#source').value=d.source;this.selected.add(+d.channel);this.paint()}
  q(id){return this.querySelector(id)}
  async sync(){const states=Object.values(this._hass?.states||{});const s=states.find(x=>Array.isArray(x.attributes?.dmx_rules));if(s)this.rules=s.attributes.dmx_rules.map(r=>({...r,channels:[...(r.channels||[])]}));this.renderList()}
  async call(service,data){if(!this._hass){this.setTrace('Home Assistant non connecté.');return false}try{await this._hass.callService('dmx_monitor',service,data);await new Promise(r=>setTimeout(r,50));await this.sync();return true}catch(e){this.setTrace(`Erreur HA : ${e?.message||e}`);return false}}
  render(){this.innerHTML=`<style>:host{display:block;background:#090b0e;color:#eee;font-family:Inter,system-ui,sans-serif;padding:16px}.layout{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:14px}.panel{background:#111419;border:1px solid #292f36;border-radius:8px;padding:12px}.grid{display:grid;grid-template-columns:repeat(16,1fr);gap:3px}.ch{height:36px;border:1px solid #2a3037;background:#252a30;color:#ddd;border-radius:3px;font-size:9px}.ch.selected{background:#1d5c3a;border-color:#45a56f}.ch.hot{box-shadow:inset 0 -4px 0 #d4a72c}.v{display:block;font-weight:700;margin-top:3px}label{display:block;font-size:10px;color:#9da5ad;margin:8px 0 4px}input,select,textarea{width:100%;box-sizing:border-box;background:#090b0e;color:#eee;border:1px solid #303740;border-radius:5px;padding:7px}.row{display:grid;grid-template-columns:1fr 1fr;gap:8px}.actions{display:flex;gap:7px;margin-top:12px;flex-wrap:wrap}.action{border:1px solid #3b444e;background:#191e24;color:#eee;border-radius:5px;padding:8px 10px}.primary{background:#1d5c3a}.danger{background:#32191c}.list{margin-top:10px;display:grid;gap:6px}.rule{border:1px solid #292f36;border-radius:6px;padding:8px;background:#0d1014}.rule strong{display:block}.pill{font-size:9px;color:#9da5ad}.trace{margin-top:12px;border-top:1px solid #292f36;padding-top:10px;font-size:11px}.mono{font-family:ui-monospace,monospace}.hint{font-size:9px;color:#7f8992}</style>
<h2>RULE BUILDER</h2><div style="font-size:10px;color:#8d969f;margin-bottom:12px">DMX VIEW → RULE · HOME ASSISTANT · RECEIVE ONLY</div>
<div class="layout"><div class="panel"><div class="grid" id="grid"></div><div class="hint" style="margin-top:8px">Clique un canal pour le sélectionner. Jaune = niveau DMX non nul.</div></div><div class="panel">
<label>Nom</label><input id="name" value="Nouvelle règle"><div class="row"><div><label>Univers</label><input id="universe" type="number" min="1" value="1"></div><div><label>Source</label><select id="source"><option value="">Toutes</option><option>ENTTEC</option><option>sACN</option><option>Art-Net</option></select></div></div>
<div class="row"><div><label>Mode</label><select id="mode"><option value="any">ANY</option><option value="all">ALL</option><option value="x_of_y">X OF Y</option></select></div><div><label>X</label><input id="x" type="number" min="1" value="1"></div></div>
<div class="row"><div><label>Threshold ON</label><input id="ton" type="number" min="0" max="255" value="10"></div><div><label>Threshold OFF</label><input id="toff" type="number" min="0" max="255" value="5"></div></div>
<div class="row"><div><label>Délai ON (ms)</label><input id="on" type="number" min="0" value="0"></div><div><label>Délai OFF (ms)</label><input id="off" type="number" min="0" value="0"></div></div>
<label>Action ON — domaine</label><select id="domain"></select><label>Service ON</label><select id="service"></select><label>Entité ON</label><select id="entity"><option value="">Aucune / service global</option></select><label>Données ON JSON</label><textarea id="data" rows="2" placeholder='{"brightness_pct":50}'></textarea>
<label>Action OFF / retour</label><div class="row"><select id="offdomain"></select><select id="offservice"></select></div><select id="offentity" style="margin-top:5px"><option value="">Aucune / service global</option></select><label>Données OFF JSON</label><textarea id="offdata" rows="2" placeholder='{"transition":2}'></textarea>
<div class="actions"><button class="action" id="clear">Effacer sélection</button><button class="action primary" id="save">Créer / enregistrer</button><button class="action" id="test">Tester live</button></div><div class="trace"><b>Pourquoi active ?</b><div id="trace">Sélectionne des canaux.</div></div><div class="list" id="list"></div></div></div>`;
    const g=this.q('#grid');for(let i=1;i<=512;i++){let b=document.createElement('button');b.className='ch';b.dataset.ch=i;b.textContent=i;b.onclick=()=>this.toggle(i);g.appendChild(b)}
    this.q('#clear').onclick=()=>{this.selected.clear();this.editing=null;this.paint()};this.q('#save').onclick=()=>this.save();this.q('#test').onclick=()=>this.test();
    this.q('#domain').onchange=()=>this.refreshServices('#domain','#service','#entity');this.q('#offdomain').onchange=()=>this.refreshServices('#offdomain','#offservice','#offentity');this.refreshTargets();this.paint();this.renderList()
  }
  toggle(c){this.selected.has(c)?this.selected.delete(c):this.selected.add(c);this.paint()}
  paint(){this.querySelectorAll('.ch').forEach(b=>b.classList.toggle('selected',this.selected.has(+b.dataset.ch)));const a=[...this.selected].sort((x,y)=>x-y);this.setTrace(a.length?`<span class="mono">${a.join(', ')}</span> · ${a.length} canal(aux)`:'Sélectionne des canaux.')}
  setTrace(t){const e=this.q('#trace');if(e)e.innerHTML=t}
  json(id){try{const v=this.q(id)?.value||'';return v?JSON.parse(v):{}}catch{return null}}
  detail(){const q=id=>this.q(id)?.value||'',on=this.json('#data'),off=this.json('#offdata');const channels=[...this.selected].sort((a,b)=>a-b);if(on===null||off===null){this.setTrace('JSON invalide.');return null}if(!channels.length){this.setTrace('Sélectionne au moins un canal.');return null}if(q('#mode')==='x_of_y'&&(+q('#x')<1||+q('#x')>channels.length)){this.setTrace('X doit être compris entre 1 et le nombre de canaux.');return null}return {name:q('#name').trim(),universe:+q('#universe'),source:q('#source')||null,channels,mode:q('#mode'),x:+q('#x'),threshold_on:+q('#ton'),threshold_off:+q('#toff'),on_delay_ms:+q('#on'),off_delay_ms:+q('#off'),enabled:false,test_mode:false,action:{domain:q('#domain'),entity_id:q('#entity')||null,service:q('#service'),data:on},off_action:{domain:q('#offdomain'),entity_id:q('#offentity')||null,service:q('#offservice'),data:off}}}
  async save(){const d=this.detail();if(!d||!d.name){this.setTrace('Nom obligatoire.');return}const service=this.editing?'update_rule':'create_rule',payload=this.editing?{old_name:this.editing,...d}:d;if(await this.call(service,payload)){this.editing=d.name;this.setTrace('Règle enregistrée. Activation explicite requise.')}}
  async test(){const d=this.detail();if(!d)return;const ok=await this.call('test_rule',{name:this.editing||d.name,values:this.currentValues()});if(ok)this.setTrace('Test exécuté sans action HA et sans modifier l’état de la règle.')}
  currentValues(){const u=+this.q('#universe').value,s=this.q('#source').value;const states=this._hass?.states||{};for(const st of Object.values(states)){const us=st.attributes?.universes;if(!Array.isArray(us))continue;for(const x of us){if(+x.universe===u&&(!s||x.source===s||x.protocol===s))return x.values||[]}}return undefined}
  refreshTargets(){if(!this._hass)return;this.refreshServices('#domain','#service','#entity');this.refreshServices('#offdomain','#offservice','#offentity')}
  refreshServices(domainSel,serviceSel,entitySel){const d=this.q(domainSel),s=this.q(serviceSel),e=this.q(entitySel);if(!d||!s||!e)return;const services=this._hass?.services||{}, domains=Object.keys(services).sort();const prevD=d.value;d.innerHTML=domains.map(x=>`<option value="${x}">${x}</option>`).join('');if(domains.includes(prevD))d.value=prevD;const domain=services[d.value]||{}, names=Object.keys(domain).sort(),prevS=s.value;s.innerHTML=names.map(x=>`<option value="${x}">${x}</option>`).join('');if(names.includes(prevS))s.value=prevS;const entities=Object.values(this._hass.states||{}).filter(x=>x.entity_id?.startsWith(`${d.value}.`));const prevE=e.value;e.innerHTML='<option value="">Aucune / service global</option>'+entities.map(x=>`<option value="${x.entity_id}">${x.entity_id} — ${x.attributes?.friendly_name||''}</option>`).join('');if(entities.some(x=>x.entity_id===prevE))e.value=prevE}
  renderList(){const l=this.q('#list');if(!l)return;l.innerHTML='<b>Règles Home Assistant</b>';if(!this.rules.length){l.innerHTML+='<div class="pill">Aucune règle.</div>';return}this.rules.forEach(r=>{const d=document.createElement('div');d.className='rule';d.innerHTML=`<strong>${r.name}</strong><span class="pill">U${r.universe} · ${r.source||'toutes'} · ${(r.channels||[]).length} ch · ${r.enabled?'ACTIVE':'INACTIVE'} · ${r.test_mode?'TEST':''}</span><div class="actions"><button class="action" data-a="toggle">${r.enabled?'Désactiver':'Activer'}</button><button class="action" data-a="testmode">${r.test_mode?'Quitter test':'Mode test'}</button><button class="action" data-a="edit">Éditer</button><button class="action" data-a="duplicate">Dupliquer</button><button class="action danger" data-a="delete">Supprimer</button></div>`;d.querySelectorAll('button').forEach(b=>b.onclick=()=>this.ruleAction(r,b.dataset.a));l.appendChild(d)})}
  async ruleAction(r,a){if(a==='toggle')return this.call('set_rule_enabled',{name:r.name,enabled:!r.enabled});if(a==='testmode')return this.call('set_rule_test_mode',{name:r.name,enabled:!r.test_mode});if(a==='delete')return this.call('remove_rule',{name:r.name});if(a==='duplicate')return this.call('create_rule',{...r,name:`${r.name} copie`,enabled:false});if(a==='edit'){this.editing=r.name;this.selected=new Set(r.channels||[]);const m={'#name':r.name,'#universe':r.universe,'#source':r.source||'','#mode':r.mode||'any','#x':r.x||1,'#ton':r.threshold_on??10,'#toff':r.threshold_off??5,'#on':r.on_delay_ms||0,'#off':r.off_delay_ms||0,'#domain':r.action?.domain||'light','#entity':r.action?.entity_id||'','#service':r.action?.service||'turn_on','#data':JSON.stringify(r.action?.data||{}),'#offdomain':r.off_action?.domain||'light','#offentity':r.off_action?.entity_id||'','#offservice':r.off_action?.service||'turn_off','#offdata':JSON.stringify(r.off_action?.data||{})};for(const[id,v]of Object.entries(m)){const el=this.q(id);if(el)el.value=v}this.refreshTargets();this.paint()}}
}
customElements.define('show-network-rule-builder',ShowNetworkRuleBuilder);


/* ===== show-network-archive-panel.js ===== */
class ShowNetworkArchivePanel extends HTMLElement {
  setConfig(c){this._config=c||{};}
  set hass(h){this._hass=h; this.render();}
  render(){
    const h=this._hass; if(!h)return;
    const st=h.states?.['sensor.dmx_monitor_journal_archive']; const a=st?.attributes||{};
    this.innerHTML=`<style>:host{display:block}.box{padding:15px;border:1px solid #30363d;border-radius:14px;background:#111519;color:#eee}.row{display:flex;justify-content:space-between;gap:15px;padding:8px 0;border-bottom:1px solid #252b31;font-size:12px}.row:last-of-type{border:0}.btn{margin:10px 6px 0 0;padding:9px 12px;border:1px solid #39414a;background:#181d22;color:#eee;border-radius:8px;cursor:pointer}.path{font-family:ui-monospace,monospace;word-break:break-all}.small{font-size:11px;color:#929ba4}</style><div class="box"><b>JOURNAL · BACKUPS</b><div class="row"><span>Destination</span><span class="path">${a.configured_destination||'—'}</span></div><div class="row"><span>Fichiers</span><span>${a.files??'—'}</span></div><div class="row"><span>Taille</span><span>${a.bytes??0} octets</span></div><div class="row"><span>Rétention</span><span>${a.retention_days??'—'} jours</span></div><div class="small">La destination peut être le stockage HA, un second disque monté ou un NAS/SMB déjà monté.</div><button class="btn" id="backup">Backup maintenant</button><button class="btn" id="export">Exporter</button><div class="small" style="margin-top:8px">Pour changer de destination : service <b>dmx_monitor.archive_set_destination</b>.</div></div>`;
    this.querySelector('#backup')?.addEventListener('click',()=>h.callService?.('dmx_monitor','archive_backup',{}));
    this.querySelector('#export')?.addEventListener('click',()=>h.callService?.('dmx_monitor','archive_export',{}));
  }
}
customElements.define('show-network-archive-panel',ShowNetworkArchivePanel);


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
customElements.define("show-network-dashboard",ShowNetworkDashboard);


/* ===== show-network-ha-builder-panel.js ===== */
class ShowNetworkHABuilderPanel extends HTMLElement {
  setConfig(c){this._config=c||{};}
  set hass(h){this._hass=h; this.render();}
  render(){
    const h=this._hass; if(!h)return;
    const state=h.states?.['sensor.dmx_monitor_ha_builder'];
    const items=state?.attributes?.items||[];
    const call=(service,data={})=>h.callService?.('dmx_monitor',service,data);
    this.innerHTML=`<style>:host{display:block;font-family:system-ui}.box{padding:16px;border:1px solid #30363d;border-radius:14px;background:#111519;color:#eee}.head{display:flex;justify-content:space-between;gap:12px;align-items:center}.title{font-weight:800;letter-spacing:.04em}.small{font-size:11px;color:#929ba4}.grid{display:grid;grid-template-columns:2fr 1fr 1fr;gap:8px;margin-top:12px}@media(max-width:800px){.grid{grid-template-columns:1fr}}input,select{width:100%;box-sizing:border-box;padding:9px;border-radius:8px;border:1px solid #39414a;background:#181d22;color:#eee}.btn{margin-top:10px;padding:9px 12px;border:1px solid #39414a;background:#181d22;color:#eee;border-radius:8px;cursor:pointer}.item{margin-top:8px;padding:10px;border:1px solid #252b31;border-radius:9px}.remove{float:right}.ok{color:#68df9a}</style><div class="box"><div class="head"><div><div class="title">HA BUILDER</div><div class="small">Crée des entités Show Network correctement typées, sans YAML.</div></div><div class="ok">${items.length} élément(s)</div></div><div class="grid"><input id="name" placeholder="Nom : Secours audio"><select id="type"><option value="switch">Switch</option><option value="sensor">Capteur</option><option value="binary_sensor">Binary sensor</option><option value="button">Bouton</option><option value="number">Nombre</option></select><input id="area" placeholder="Zone / Area"></div><button class="btn" id="create">Créer dans Home Assistant</button><div>${items.map(x=>`<div class="item"><button class="btn remove" data-id="${x.item_id}">Supprimer</button><b>${x.name}</b> · ${x.entity_type}<div class="small">${x.item_id}${x.area?` · ${x.area}`:''}</div></div>`).join('')}</div></div>`;
    this.querySelector('#create')?.addEventListener('click',async()=>{const name=this.querySelector('#name').value.trim();if(!name)return;await call('ha_builder_create',{name,entity_type:this.querySelector('#type').value,area:this.querySelector('#area').value.trim()});});
    this.querySelectorAll('.remove').forEach(b=>b.addEventListener('click',()=>call('ha_builder_remove',{item_id:b.dataset.id})));
  }
}
customElements.define('show-network-ha-builder-panel',ShowNetworkHABuilderPanel);


/* ===== show-network-notification-panel.js ===== */
class ShowNetworkNotificationPanel extends HTMLElement {
  setConfig(c){this._config=c||{};}
  set hass(h){this._hass=h; const st=h?.states?.['sensor.dmx_monitor_notification']; const a=st?.attributes||{}; this.innerHTML=`<style>:host{display:block}.box{padding:15px;border:1px solid #30363d;border-radius:14px;background:#111519;color:#eee}.row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #252b31;font-size:12px}.small{font-size:11px;color:#929ba4}.ok{color:#68df9a}.warn{color:#e5bf6b}</style><div class="box"><b>NOTIFICATIONS HA</b><div class="row"><span>État</span><span class="${a.enabled?'ok':'warn'}">${a.enabled?'ACTIF':'INACTIF'}</span></div><div class="row"><span>Mode</span><span>${a.mode||'—'}</span></div><div class="row"><span>Cible</span><span>${a.target_configured?'Configurée':'Non configurée'}</span></div><div class="small" style="margin-top:8px">Les alertes peuvent apparaître dans l'application HA via notification persistante et/ou un service notify mobile.</div></div>`;}
}
customElements.define('show-network-notification-panel',ShowNetworkNotificationPanel);


/* ===== show-network-pro-dashboard.js ===== */
class ShowNetworkProDashboard extends HTMLElement {
  setConfig(c){this._config=c||{}; this.render();}
  set hass(h){this._hass=h; if(this._raf)return; const run=()=>{this._raf=null;this.render();}; this._raf=(typeof requestAnimationFrame==="function"?requestAnimationFrame(run):setTimeout(run,100));}
  connectedCallback(){this.render();}
  render(){
    const s=this._hass?.states||{};
    const get=(id)=>s[id]?.state ?? '—';
    const cap=get('sensor.dmx_monitor_network_capacity_utilization');
    const nodes=get('sensor.dmx_monitor_topology_nodes');
    const links=get('sensor.dmx_monitor_topology_links');
    const chaos=get('sensor.dmx_monitor_chaos_status');
    const archive=s['sensor.dmx_monitor_journal_archive']?.attributes||{};
    const pct=parseFloat(cap); const status=Number.isFinite(pct)?(pct>=90?'critical':pct>=75?'warning':'ok'):'off';
    this.innerHTML=`<style>
:host{display:block;background:#0a0c0f;color:#eef1f4;font-family:Inter,system-ui,sans-serif;min-height:100vh}.wrap{padding:18px;max-width:1500px;margin:auto}.top{display:flex;justify-content:space-between;align-items:center;padding:16px 18px;border:1px solid #293039;background:#12161a;border-radius:12px}.brand{font-size:20px;font-weight:800;letter-spacing:.06em}.muted{color:#8f99a3;font-size:11px}.badge{padding:7px 10px;border-radius:999px;border:1px solid #343b43;font-size:11px}.grid{display:grid;grid-template-columns:1.4fr 1fr 1fr;gap:12px;margin-top:12px}.card{background:#12161a;border:1px solid #293039;border-radius:12px;padding:15px}.title{font-size:11px;color:#8f99a3;letter-spacing:.08em}.big{font-size:34px;font-weight:800;margin:6px 0}.ok{color:#68df9a}.warning{color:#e5bf6b}.critical{color:#ef7777}.off{color:#8f99a3}.row{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid #22282e;font-size:12px}.row:last-child{border:0}.topology{height:260px;display:flex;align-items:center;justify-content:center;gap:16px}.node{border:1px solid #39424c;border-radius:10px;padding:12px;text-align:center;background:#171c21;min-width:105px}.arrow{color:#68737d}.footer{margin-top:12px;display:flex;gap:8px;flex-wrap:wrap}.btn{background:#171c21;border:1px solid #39424c;border-radius:8px;padding:9px 12px;color:#eee;cursor:pointer}.btn:hover{background:#20262c}@media(max-width:900px){.grid{grid-template-columns:1fr}.wrap{padding:10px}.topology{height:190px}}
</style><div class="wrap"><div class="top"><div><div class="brand">SHOW NETWORK / PRO</div><div class="muted">IP · FLOW · TOPOLOGY · TIMELINE · RELIABILITY</div></div><div class="badge ${status}">CAPACITY ${cap}%</div></div>
<div class="grid"><div class="card"><div class="title">NETWORK CAPACITY</div><div class="big ${status}">${cap}%</div><div class="row"><span>Link</span><span>${get('sensor.dmx_monitor_network_capacity_link_mbps')} Mb/s</span></div><div class="row"><span>Utilisé</span><span>${get('sensor.dmx_monitor_network_capacity_total_mbps')} Mb/s</span></div><div class="row"><span>Marge</span><span>${get('sensor.dmx_monitor_network_capacity_headroom_mbps')} Mb/s</span></div></div>
<div class="card"><div class="title">TOPOLOGY</div><div class="big">${nodes}</div><div class="muted">NŒUDS</div><div class="row"><span>Liens</span><span>${links}</span></div></div>
<div class="card"><div class="title">RELIABILITY</div><div class="big ${chaos==='inactive'?'ok':'warning'}">${chaos}</div><div class="muted">CHAOS / FAULT INJECTION</div><div class="row"><span>Archive</span><span>${archive.files??'—'} fichiers</span></div><div class="row"><span>Destination</span><span>${archive.configured_destination??'—'}</span></div></div></div>
<div class="card topology"><div class="node">NIC<br><span class="muted">${get('sensor.dmx_monitor_network_interfaces_up')} UP</span></div><div class="arrow">→</div><div class="node">SWITCH<br><span class="muted">${nodes} nodes</span></div><div class="arrow">→</div><div class="node">SHOW DEVICES<br><span class="muted">${get('sensor.dmx_monitor_devices_total')} devices</span></div></div>
<div class="footer"><button class="btn" id="classic">Vue classique</button><button class="btn" id="timeline">Show Timeline</button><button class="btn" id="archive">Journal & backups</button></div></div>`;
    this.querySelector('#classic')?.addEventListener('click',()=>this.dispatchEvent(new CustomEvent('show-network-view',{detail:{view:'classic'},bubbles:true,composed:true})));
  }
}
customElements.define('show-network-pro-dashboard',ShowNetworkProDashboard);


/* ===== show-network-reliability-panel.js ===== */
class ShowNetworkReliabilityPanel extends HTMLElement {
  setConfig(c){this._config=c||{};}
  set hass(h){this._hass=h; const st=h?.states?.['sensor.dmx_monitor_chaos_status']; const cap=h?.states?.['sensor.dmx_monitor_network_capacity_utilization']; const d=h?.states?.['sensor.dmx_monitor_dmx_universes']?.attributes?.network_health||{}; const badge=(n)=>n>0?'⚠️':'🟢'; this.innerHTML=`<style>:host{display:block;font-family:system-ui}.box{padding:14px;border:1px solid #30363d;border-radius:12px;background:#111519;color:#eee}.title{font-weight:800}.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:10px}.b{padding:9px;border:1px solid #39414a;border-radius:8px;background:#181d22;color:#eee}.danger{border-color:#a85b5b}.small{font-size:11px;color:#929ba4}.health{margin-top:12px;padding:10px;border:1px solid #30363d;border-radius:9px;background:#151a1f}.row{display:flex;justify-content:space-between;gap:10px;padding:3px 0}</style><div class="box"><div class="title">RELIABILITY / NETWORK</div><div class="small">État: ${st?.state||'inactive'} · capacité: ${cap?.state||'—'}%</div><div class="health"><div class="row"><span>sACN queue</span><b>${badge(d.sacn_queue_drops||0)} ${d.sacn_queue_depth||0}/${d.queue_size||'—'} · drops ${d.sacn_queue_drops||0}</b></div><div class="row"><span>Art-Net queue</span><b>${badge(d.artnet_queue_drops||0)} ${d.artnet_queue_depth||0}/${d.queue_size||'—'} · drops ${d.artnet_queue_drops||0}</b></div><div class="row"><span>sACN reconnexions</span><b>${d.sacn_restarts||0}</b></div><div class="row"><span>Art-Net reconnexions</span><b>${d.artnet_restarts||0}</b></div></div><div class="grid"><button class="b danger" id="loss">Simuler perte watchdog</button><button class="b" id="restore">Restaurer signal</button><button class="b" id="ptp">PTP dérive +1 ms</button><button class="b" id="clear">Arrêter simulation</button></div></div>`; const call=(service,data={})=>h.callService?.('dmx_monitor',service,data); this.querySelector('#loss')?.addEventListener('click',()=>call('chaos_signal_loss')); this.querySelector('#restore')?.addEventListener('click',()=>call('chaos_signal_restore')); this.querySelector('#ptp')?.addEventListener('click',()=>call('chaos_ptp_drift',{offset_ms:1})); this.querySelector('#clear')?.addEventListener('click',()=>call('chaos_clear'));}
}
customElements.define('show-network-reliability-panel',ShowNetworkReliabilityPanel);


/* ===== signal-watchdog-panel.js ===== */
/**
 * Show Network — Signal Watchdog panel.
 * Read-only status view; rule creation is intentionally delegated to the
 * integration Rule Builder so all HA actions use the same safety path.
 */
class SignalWatchdogPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    this.render();
  }
  render() {
    if (!this._hass) return;
    const states = Object.values(this._hass.states || {}).filter(s => s.entity_id.includes('watchdog'));
    this.innerHTML = `<ha-card header="DMX Signal Watchdog"><div style="padding:16px">${states.length ? states.map(s => `<div><b>${s.attributes?.friendly_name || s.entity_id}</b>: ${s.state}</div>`).join('') : 'No watchdog entities configured.'}</div></ha-card>`;
  }
}
customElements.define('signal-watchdog-panel', SignalWatchdogPanel);


/* ===== topology-panel.js ===== */
class ShowNetworkTopologyPanel extends HTMLElement {
  setConfig(config) { this.config = config || {}; }
  set hass(hass) { this._hass = hass; this.render(); }
  render() {
    if (!this._hass) return;
    const states = Object.values(this._hass.states || {});
    const state = states.find(s => s.attributes && s.attributes.topology);
    const topo = state ? state.attributes.topology : {nodes:[],links:[]};
    const nodes = topo.nodes || [], links = topo.links || [];
    this.innerHTML = `<ha-card header="Show Network · Topology">
      <div style="padding:16px">
        <b>${nodes.length}</b> équipements · <b>${links.length}</b> liaisons observées
        <div style="margin-top:12px">${links.map(l => `<div style="padding:5px 0">${l.source} → ${l.target}${l.source_port ? ` · port ${l.source_port}` : ''}${l.link_speed_mbps ? ` · ${l.link_speed_mbps} Mb/s` : ''} · ${Math.round((l.confidence||0)*100)}%</div>`).join('')}</div>
      </div></ha-card>`;
  }
}
customElements.define('show-network-topology-panel', ShowNetworkTopologyPanel);


/* ===== dmx-ha-zones-panel.js ===== */
class DmxHaZonesPanel extends HTMLElement {
  set hass(h){this._hass=h;this.render()}
  _state(){return Object.values(this._hass?.states||{}).find(x=>x.entity_id.endsWith('dmx_ha_zones_total'))}
  _zones(){return this._state()?.attributes?.zones||[]}
  _call(service,data){return this._hass.callService('dmx_monitor',service,data)}
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
      <div class="row"><label>Lampes HA<select id="zl" multiple size="4">${lights.map(x=>`<option value="${x.id}">${x.name}</option>`).join('')}</select></label><label>Fixture par lampe (JSON)<input id="zft" placeholder='{"light.xxx":"RGB fixture"}'></label></div>
      <div class="row"><button id="add">AJOUTER LA ZONE</button></div>
    </div>
    <div class="grid">${zones.map(z=>this._card(z)).join('')||'<div class="card">Aucune zone configurée.</div>'}</div>`;
    this.querySelector('#add')?.addEventListener('click',()=>{
      const selected=[...this.querySelector('#zl').selectedOptions].map(o=>o.value);
      const name=this.querySelector('#zn').value.trim()||'Zone';
      const id='zone_'+name.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[^a-z0-9]+/g,'_').replace(/^_|_$/g,'')+'_'+Date.now().toString(36);
      this._call('create_dmx_ha_zone',{zone_id:id,name,universe:Number(this.querySelector('#zu').value),channels:this.querySelector('#zc').value,mode:this.querySelector('#zm').value,fixture_type:this.querySelector('#zf').value,fixture_types:(()=>{try{return JSON.parse(this.querySelector('#zft').value||'{}')}catch(e){return {}}})(),entity_ids:selected,source:this.querySelector('#zs').value,enabled:true,rdm_enabled:false});
    });
    this.querySelectorAll('[data-zone-toggle]').forEach(b=>b.addEventListener('click',()=>this._call('set_dmx_ha_zone_enabled',{zone_id:b.dataset.zoneToggle,enabled:b.dataset.value!=='true'})));
    this.querySelectorAll('[data-rdm-toggle]').forEach(b=>b.addEventListener('click',()=>this._call('set_dmx_ha_zone_rdm_enabled',{zone_id:b.dataset.rdmToggle,enabled:b.dataset.value!=='true'})));
    this.querySelectorAll('[data-zone-remove]').forEach(b=>b.addEventListener('click',()=>this._call('remove_dmx_ha_zone',{zone_id:b.dataset.zoneRemove})));
  }
  _card(z){
    const model=z.hue_model_id||'—', cap=z.hue_capabilities?.kind||'—';
    return `<div class="card"><div class="head"><span class="name">${z.name}</span><span class="pill ${z.enabled?'on':'off'}">${z.enabled?'ACTIVE':'OFF'}</span></div><div class="meta">Universe ${z.universe} · ${z.mode.toUpperCase()} · canaux ${z.channels.join(', ')} · ${z.entity_ids.length} lampe(s)</div><div class="meta">Fixture: ${z.fixture_type||'non défini'} · Hue: ${model} · ${cap}</div><div class="meta">RDM: ${z.rdm_enabled?'ÉCOUTE ACTIVE':'désactivée'}${z.rdm_enabled?' · détection passive uniquement':''}</div><div class="row"><button data-zone-toggle="${z.zone_id}" data-value="${z.enabled}">${z.enabled?'DÉSACTIVER':'ACTIVER'}</button><button data-rdm-toggle="${z.zone_id}" data-value="${z.rdm_enabled}">${z.rdm_enabled?'COUPER RDM':'ÉCOUTER RDM'}</button><button data-zone-remove="${z.zone_id}">SUPPRIMER</button></div></div>`
  }
}
customElements.define('dmx-ha-zones-panel',DmxHaZonesPanel);

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
    this.querySelector('#scan')?.addEventListener('click',()=>this._hass.callService('dmx_monitor','discover_punchlight',{timeout:2}));
  }
}
customElements.define('punchlight-network-panel',PunchLightNetworkPanel);
