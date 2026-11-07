// Exercise the actual application handlers against recorded exports using a minimal DOM.
// This checks state and canvas commands, not browser layout or visual appearance.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const html=await readFile(new URL('./index.html',import.meta.url),'utf8');
const results=JSON.parse(await readFile(new URL('./dist/results.json',import.meta.url),'utf8'));
const nodes=new Map(),contexts=[];
class Element{
  constructor(tag='div'){this.tagName=tag;this.children=[];this.dataset={};this.attributes={};this.handlers={};this.style={};this.checked=false;this.hidden=false;this.value='';this.textContent='';this.classList={toggle(){},add(){},remove(){}};}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.children=children;}
  setAttribute(k,v){this.attributes[k]=v;}
  addEventListener(k,v){this.handlers[k]=v;}
  cloneNode(){const n=new Element(this.tagName);n.dataset={...this.dataset};n.textContent=this.textContent;return n;}
  getContext(){if(this.context)return this.context;const strokes=[];this.context=new Proxy({strokes,stroke(){strokes.push({color:this.strokeStyle,width:this.lineWidth,dash:this.dash});},setLineDash(v){this.dash=v;},drawImage(...args){assert(args.slice(1).every(Number.isFinite));}}, {get:(o,k)=>k in o?o[k]:()=>{}});contexts.push(this.context);return this.context;}
}
for(const match of html.matchAll(/id="([^"]+)"/g))nodes.set(match[1],new Element());
const $=id=>nodes.get(id);
$('spacing').value='80';$('policy').value='offshore_only';$('corridor').value='0';$('route-extent').value='context';
const all=()=>[...nodes.values()].flatMap(n=>[n,...n.children]);
globalThis.document={getElementById:id=>$(id),createElement:tag=>new Element(tag),querySelectorAll:selector=>selector==='[data-date]'?all().filter(n=>n.dataset.date):[]};
globalThis.fetch=async()=>({ok:true,json:async()=>results});
globalThis.Image=class{constructor(){this.width=1100;this.height=1100;}set src(v){this.url=v;queueMicrotask(()=>this.onload());}};
await import('./app.mjs');
const settle=()=>new Promise(resolve=>setImmediate(resolve));await settle();
assert.equal($('route-date-buttons').children.length,4);
assert.equal($('date-buttons').children.length,4);
for(const date of results.dates){
  for(const spacing of [80,200])for(const policy of ['offshore_only','all_retained']){
    $('spacing').value=String(spacing);$('policy').value=policy;
    $('route-date-buttons').children.find(b=>b.dataset.date===date.date).handlers.click();await settle();
    const expected=results.routes.find(r=>r.date===date.date&&r.spacing_m===spacing&&r.policy===policy);
    assert.equal($('distance').textContent,(expected.distance_m/1000).toFixed(3));
    assert.equal($('route-comparison').children.length,4);
    assert.equal($('impact-candidates').children.length,results.impact.scenarios.find(r=>r.date===date.date&&r.spacing_m===spacing&&r.policy===policy).summary.candidates_detected);
    const strokes=$('route-map').context.strokes.filter(s=>['#ffe68b','#ff6ca8'].includes(s.color));
    assert.equal(strokes.at(-1).color,'#ffe68b');assert(strokes.at(-1).dash.length>0);
    assert.equal(strokes.at(-2).color,'#ff6ca8');
  }
}
$('spacing').value='80';$('policy').value='offshore_only';$('corridor').value='500';
$('route-date-buttons').children.find(b=>b.dataset.date==='20250722').handlers.click();await settle();
assert.equal($('distance').textContent,'No path');assert.equal($('distance-unit').hidden,true);
assert($('impact-scope').textContent.includes('not the selected corridor'));
assert.equal($('route-comparison').children.length,4);
$('route-extent').value='region';$('route-extent').handlers.change();await settle();
assert.equal($('route-scale').textContent,'20 km');
assert.equal($('load-error').hidden,true);
console.log('Explorer integration passed: four dates, all 16 nominal selections, visible baseline paint order, no-path corridor and regional extent.');
