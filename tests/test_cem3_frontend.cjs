// Run with node tests/test_cem3_frontend.cjs. Lightweight DOM adapter, not HA browser QA.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const registered=new Map();
class Element {querySelector(){return null;}querySelectorAll(){return [];}addEventListener(){}removeEventListener(){}matches(){return false;}}
const context={HTMLElement:Element,window:{addEventListener(){},removeEventListener(){}},customElements:{get:n=>registered.get(n),define:(n,c)=>registered.set(n,c)},console,document:{},setTimeout,clearTimeout,setInterval,clearInterval,Date};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../custom_components/dmx_monitor/static/show-network.js'),'utf8'),context);
const Panel=registered.get('show-network-pro-dashboard');
const panel=new Panel();panel._hass={states:{}};panel._shell=x=>x;panel._cem3={online:2,total:2,source_ips:['10.1.0.1','10.2.0.1'],racks:[1,2].map(n=>({host:`10.${n}.0.2`,source_ip:`10.${n}.0.1`,online:true,fresh:true,data:{rack_name:`Rack ${n}`},freshness:{levels:true,properties:true,spaces:true},spaces:[{space:1,name:'<img onerror=bad>',active_preset:0,active_sequence:0}],dimmers:{circuits_total:72,circuits_active:30,circuits:Array.from({length:72},(_,i)=>({udn:i+97,circuit:i+1,space:1,level:99,wsource:'sACN',module_type:'ETD15AFR'}))}}))};
panel._renderModule('etc');
assert.equal((panel.innerHTML.match(/<td style=/g)||[]).length,2*72*12);
assert(panel.innerHTML.includes('&lt;img onerror=bad&gt;'));
assert(!panel.innerHTML.includes('<img onerror=bad>'));
assert(panel.innerHTML.includes('10.2.0.1'));
assert(!panel.innerHTML.includes('Set Levels'));
panel._cem3.racks[0].online=false;panel._cem3.racks[0].fresh=false;panel._renderModule('etc');assert(panel.innerHTML.includes('OFFLINE'));
console.log('CEM3 panel: 144 circuits, both NICs, offline status and HTML escaping verified.');
