import { projectPoint, routeViewport } from './route_geometry.mjs';
import { shortestPath, preset } from './routing.mjs';
const $ = id => document.getElementById(id);
const formatDate = date => new Date(`${date.slice(0,4)}-${date.slice(4,6)}-${date.slice(6,8)}T12:00:00Z`).toLocaleDateString('en-GB', {day:'numeric',month:'long',year:'numeric',timeZone:'UTC'});
const shortDate = date => new Date(`${date.slice(0,4)}-${date.slice(4,6)}-${date.slice(6,8)}T12:00:00Z`).toLocaleDateString('en-GB', {day:'numeric',month:'short',timeZone:'UTC'});
let data, selectedDate='20250716', generation=0;
const images = new Map();
function loadImage(url) {
  if (!images.has(url)) images.set(url,new Promise((resolve,reject)=>{
    const image=new Image();image.onload=()=>resolve(image);image.onerror=()=>{images.delete(url);reject(new Error('A satellite layer could not be loaded. Refresh to retry.'));};image.src=url;
  }));
  return images.get(url);
}
function displayError(message) { $('load-error').hidden=false; $('load-error').textContent=message; }
async function drawMap() {
  const version=++generation, date=selectedDate;
  $('map-loading').hidden=false;
  try {
    const layers=await Promise.all(['sar.webp','offshore.png','review.png'].map(suffix=>loadImage(`assets/${date}_${suffix}`)));
    if (version!==generation) return;
    const ctx=$('map').getContext('2d');ctx.clearRect(0,0,1100,1100);
    ctx.drawImage(layers[0],0,0);
    if ($('show-review').checked) ctx.drawImage(layers[2],0,0);
    if ($('show-offshore').checked) ctx.drawImage(layers[1],0,0);
    $('map').setAttribute('aria-label',`${formatDate(date)} satellite scene; offshore candidates in orange and review areas in blue. Blue does not mean open water.`);
    $('map-loading').hidden=true;$('load-error').hidden=true;
  } catch(error) {if(version===generation){$('map-loading').hidden=true;displayError(error.message);}}
}
function updateResults() {
  if(!data)return;
  const spacing=Number($('spacing').value), policy=$('policy').value;
  const corridor=Number($('corridor').value);
  const rows=(corridor?data.corridors:data.routes).filter(r=>r.spacing_m===spacing&&r.policy===policy&&r.corridor_m===corridor);
  const current=rows.find(r=>r.date===selectedDate);
  $('result-date').textContent=`${formatDate(selectedDate)} / RECORDED SCENARIO`;
  $('distance').textContent=Number.isFinite(current.distance_m)?(current.distance_m/1000).toFixed(3):'No path';
  $('distance-unit').hidden=!Number.isFinite(current.distance_m);
  $('extra').textContent=Number.isFinite(current.extra_m)?`${Math.round(current.extra_m)} m longer than the ${(current.baseline_m/1000).toFixed(3)} km baseline without candidate barriers. Decimal precision does not imply metre accuracy.`:'No feasible path within this assumed corridor. This is not evidence of observed isolation.';
  updateImpact(spacing,policy,corridor);
  drawRecordedMap(rows,current);
  const max=Math.max(...rows.map(r=>r.distance_m||0))*1.05;
  $('route-bars').replaceChildren(...rows.map(r=>{
    const row=document.createElement('div');row.className='bar-row'+(r.date===selectedDate?' selected':'');
    const label=document.createElement('span');label.textContent=shortDate(r.date);
    const track=document.createElement('div');track.className='bar-track';
    const fill=document.createElement('div');fill.className='bar-fill';fill.style.width=`${(r.distance_m||0)/max*100}%`;track.append(fill);
    const distance=document.createElement('strong');distance.textContent=Number.isFinite(r.distance_m)?`${(r.distance_m/1000).toFixed(3)} km`:'No path';
    row.append(label,track,distance);return row;
  }));
}
function updateImpact(spacing,policy,corridor){
  const result=data.impact.scenarios.find(r=>r.date===selectedDate&&r.spacing_m===spacing&&r.policy===policy);
  const n=result.summary;
  $('impact-summary').textContent=`${n.candidates_detected} candidates detected under this policy. ${n.in_route_domain} intersect the route domain, and ${n.any_tested_effect_count} ${n.any_tested_effect_count===1?"changes":"change"} the calculated path, distance or feasibility in the individual tests. ${n.distance_or_feasibility_effect_count} ${n.distance_or_feasibility_effect_count===1?"changes":"change"} distance or feasibility rather than only the chosen geometry.`;
  $('impact-scope').textContent=`${formatDate(selectedDate)}, ${spacing} m grid. Each candidate is added alone and removed from the complete set. No candidate surface pixels were lost during aggregation. ${corridor?'These counts refer to the unrestricted scenario, not the selected corridor.':'These counts apply to the unrestricted scenario shown below.'} They describe model sensitivity, not biological harm.`;
  const changed=c=>['single_candidate','removed_from_all'].some(k=>c[k].chosen_path_changed||c[k].status_changed);
  const format=(v,reverse=false)=>v.distance_change_m===null?'Feasibility changed':`${(v.distance_change_m*(reverse?-1:1)).toFixed(1)} m`;
  $('impact-candidates').replaceChildren(...[...result.candidates].sort((a,b)=>Number(changed(b))-Number(changed(a))||a.component_id-b.component_id).map(c=>{
    const tr=document.createElement('tr');
    for(const value of [c.component_id,c.domain_cells,format(c.single_candidate),format(c.removed_from_all,true),changed(c)?'Yes':'No']){const td=document.createElement('td');td.textContent=value;tr.append(td);}
    return tr;
  }));
}
function chooseDate(date) {
  selectedDate=date;
  document.querySelectorAll('[data-date]').forEach(b=>{b.classList.toggle('active',b.dataset.date===date);b.setAttribute('aria-pressed',String(b.dataset.date===date));});
  const item=data.dates.find(d=>d.date===date);
  $('map-date').textContent=formatDate(date);
  $('offshore-count').textContent=item.offshore_count;$('review-count').textContent=item.review_count;
  updateResults();drawMap();
}
async function initialise() {
  try {
    const response=await fetch('results.json');if(!response.ok)throw new Error('Recorded results are unavailable. Please refresh to retry.');data=await response.json();
    for(const item of data.dates){const button=document.createElement('button');button.dataset.date=item.date;button.textContent=formatDate(item.date);button.addEventListener('click',()=>chooseDate(item.date));$('date-buttons').append(button);const routeButton=button.cloneNode(true);routeButton.addEventListener('click',()=>chooseDate(item.date));$('route-date-buttons').append(routeButton);}
    for(const r of data.routes){const tr=document.createElement('tr');for(const value of [formatDate(r.date),`${r.spacing_m} m`,r.policy==='offshore_only'?'Offshore':'All retained',Number.isFinite(r.distance_m)?`${(r.distance_m/1000).toFixed(3)} km`:'No path',Number.isFinite(r.extra_m)?`${Math.round(r.extra_m)} m`:'—']){const td=document.createElement('td');td.textContent=value;tr.append(td);}$('all-results').append(tr);}
    $('tests').textContent=data.aws.unit_tests_passed;$('stages').textContent=data.aws_stage_count;$('aws-date').textContent=data.aws.checked_date;
    chooseDate(selectedDate);
  } catch(error){displayError(error.message);$('map-loading').hidden=true;}
}
['show-offshore','show-review'].forEach(id=>$(id).addEventListener('change',()=>{if(data)drawMap();}));
['spacing','policy','corridor'].forEach(id=>$(id).addEventListener('change',updateResults));

let routeGeneration=0;
async function drawRecordedMap(rows,current){
  const version=++routeGeneration;
  const date=selectedDate,full=data.dates.find(d=>d.date===date).bounds_m;
  // Keep framing stable across dates, spacings and policies so movement is not a zoom artefact.
  const bounds=routeViewport([...data.routes,...data.corridors],full,$('route-extent').value==='region');
  $('route-map-loading').hidden=false;
  $('route-map-title').textContent=`${formatDate(date)} · ${current.spacing_m} m grid · ${current.corridor_m?`${current.corridor_m} m reference corridor`:'Unrestricted reference domain'}`;
  try{
    const sar=await loadImage(`assets/${date}_sar.webp`);
    const proposals=$('route-proposals').checked?await loadImage(`assets/${date}_offshore.png`):null;
    const review=$('route-proposals').checked&&current.policy==='all_retained'?await loadImage(`assets/${date}_review.png`):null;
    if(version!==routeGeneration)return;
    const canvas=$('route-map'),ctx=canvas.getContext('2d');ctx.clearRect(0,0,1100,1100);
    const [sx,sy]=projectPoint([bounds[0],bounds[3]],full,sar.width,sar.height);
    const sw=(bounds[2]-bounds[0])/(full[2]-full[0])*sar.width,sh=(bounds[3]-bounds[1])/(full[3]-full[1])*sar.height;
    for(const image of [sar,review,proposals])if(image)ctx.drawImage(image,sx,sy,sw,sh,0,0,1100,1100);
    const stroke=(path,color,dash)=>{if(!path.length)return;ctx.beginPath();path.forEach((point,i)=>{const [x,y]=projectPoint(point,bounds);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.setLineDash(dash);ctx.lineWidth=7;ctx.strokeStyle='#102626';ctx.stroke();ctx.lineWidth=4;ctx.strokeStyle=color;ctx.stroke();ctx.setLineDash([]);};
    stroke(current.path_xy_m,'#ff6ca8',[]);stroke(current.baseline_xy_m,'#ffe68b',[13,13]);
    const start=current.baseline_xy_m[0];if(start){const [x,y]=projectPoint(start,bounds);ctx.beginPath();ctx.arc(x,y,9,0,2*Math.PI);ctx.fillStyle='#fff8dc';ctx.fill();ctx.strokeStyle='#183333';ctx.lineWidth=3;ctx.stroke();}
    if(current.path_xy_m.length){const [x,y]=projectPoint(current.path_xy_m.at(-1),bounds);ctx.fillStyle='#ff6ca8';ctx.fillRect(x-8,y-8,16,16);ctx.strokeStyle='#183333';ctx.strokeRect(x-8,y-8,16,16);}
    $('route-scale').textContent=`${((bounds[2]-bounds[0])/5000).toFixed(0)} km`;
    $('route-map-status').textContent=current.path_xy_m.length?`${(current.distance_m/1000).toFixed(3)} km calculated path. ${current.corridor_m?'The corridor is an additional modelling assumption, not a verified strip of solid ice.':'The unrestricted domain does not classify dark pixels as water or ice.'} The target boundary is fixed as a set, but its selected endpoint can change.`:'No route was found for these settings. Only the reference path without candidate barriers is shown; no replacement route or zero distance has been invented.';
    canvas.setAttribute('aria-label',`${formatDate(date)}: ${current.path_xy_m.length?'calculated path in pink and reference path in dashed yellow':'no feasible route; reference path only'}. Fixed August assumptions, not observed penguin tracks.`);
    $('route-map-loading').hidden=true;
    await drawComparison(rows,bounds,version);
  }catch(error){if(version===routeGeneration){$('route-map-loading').hidden=true;$('route-map-status').textContent=error.message;}}
}
async function drawComparison(rows,bounds,version){
  const panels=await Promise.all(rows.map(async row=>{
    const image=await loadImage(`assets/${row.date}_sar.webp`);
    const panel=document.createElement('figure'),title=document.createElement('figcaption');
    title.textContent=`${formatDate(row.date)} · ${Number.isFinite(row.distance_m)?(row.distance_m/1000).toFixed(3)+' km':'No path'}`;
    const canvas=document.createElement('canvas');canvas.width=1100;canvas.height=1100;canvas.setAttribute('role','img');
    canvas.setAttribute('aria-label',`${formatDate(row.date)}: ${row.path_xy_m.length?'pink calculated path and yellow dashed baseline':'no feasible path; baseline only'}`);
    const ctx=canvas.getContext('2d'),full=data.dates.find(d=>d.date===row.date).bounds_m;
    const [sx,sy]=projectPoint([bounds[0],bounds[3]],full,image.width,image.height);
    ctx.drawImage(image,sx,sy,(bounds[2]-bounds[0])/(full[2]-full[0])*image.width,(bounds[3]-bounds[1])/(full[3]-full[1])*image.height,0,0,1100,1100);
    for(const [path,color,dash] of [[row.path_xy_m,'#ff6ca8',[]],[row.baseline_xy_m,'#ffe68b',[16,16]]]){
      if(!path.length)continue;
      ctx.beginPath();path.forEach((point,i)=>{const [x,y]=projectPoint(point,bounds);i?ctx.lineTo(x,y):ctx.moveTo(x,y);});
      ctx.setLineDash(dash);ctx.lineWidth=11;ctx.strokeStyle='#102626';ctx.stroke();ctx.lineWidth=7;ctx.strokeStyle=color;ctx.stroke();
    }
    panel.append(title,canvas);return panel;
  }));
  if(version===routeGeneration)$('route-comparison').replaceChildren(...panels);
}
['route-extent','route-proposals'].forEach(id=>$(id).addEventListener('change',updateResults));

const WIDTH=24,HEIGHT=16,START=8*WIDTH+2,TARGET=8*WIDTH+21;
let blocked=preset('detour',WIDTH,HEIGHT), focusCell=START, showFocus=false;
const canvas=$('sandbox'),ctx=canvas.getContext('2d'),cell=40;
function drawSandbox(){
  const route=shortestPath(WIDTH,HEIGHT,blocked,START,TARGET);
  ctx.fillStyle='#142a2e';ctx.fillRect(0,0,canvas.width,canvas.height);
  for(let y=0;y<HEIGHT;y++)for(let x=0;x<WIDTH;x++){
    const index=y*WIDTH+x;ctx.fillStyle=blocked.has(index)?'#e48543':'#1f3c40';ctx.fillRect(x*cell+1,y*cell+1,cell-2,cell-2);
  }
  if(route){ctx.strokeStyle='#b6ddd4';ctx.lineWidth=5;ctx.lineJoin='round';ctx.beginPath();route.path.forEach((index,i)=>{const x=(index%WIDTH+.5)*cell,y=(Math.floor(index/WIDTH)+.5)*cell;i?ctx.lineTo(x,y):ctx.moveTo(x,y);});ctx.stroke();}
  ctx.fillStyle='#faf4d6';ctx.beginPath();ctx.arc((START%WIDTH+.5)*cell,(Math.floor(START/WIDTH)+.5)*cell,11,0,2*Math.PI);ctx.fill();
  ctx.fillStyle='#79cfce';ctx.fillRect((TARGET%WIDTH)*cell+9,Math.floor(TARGET/WIDTH)*cell+9,22,22);
  if(showFocus){ctx.strokeStyle='white';ctx.lineWidth=2;ctx.strokeRect((focusCell%WIDTH)*cell+3,Math.floor(focusCell/WIDTH)*cell+3,34,34);}
  $('sandbox-status').textContent=route?'A path is available.':'No path under this model.';
  $('sandbox-distance').textContent=route?`${route.distance.toFixed(2)} grid units, compared with ${(TARGET-START).toFixed(2)} in the unobstructed example.`:'The barrier separates the start from the target. Remove a cell to reopen a passage.';
}
function toggle(index){if(index===START||index===TARGET)return;blocked.has(index)?blocked.delete(index):blocked.add(index);document.querySelectorAll('[data-preset]').forEach(b=>{b.classList.remove('active');b.setAttribute('aria-pressed','false');});drawSandbox();}
canvas.addEventListener('click',event=>{const box=canvas.getBoundingClientRect();const x=Math.floor((event.clientX-box.left)/box.width*WIDTH),y=Math.floor((event.clientY-box.top)/box.height*HEIGHT);if(x>=0&&x<WIDTH&&y>=0&&y<HEIGHT){focusCell=y*WIDTH+x;toggle(focusCell);}});
canvas.addEventListener('keydown',event=>{let x=focusCell%WIDTH,y=Math.floor(focusCell/WIDTH);if(event.key==='ArrowLeft')x=Math.max(0,x-1);else if(event.key==='ArrowRight')x=Math.min(WIDTH-1,x+1);else if(event.key==='ArrowUp')y=Math.max(0,y-1);else if(event.key==='ArrowDown')y=Math.min(HEIGHT-1,y+1);else if(event.key===' '||event.key==='Enter'){event.preventDefault();toggle(focusCell);return;}else return;event.preventDefault();focusCell=y*WIDTH+x;showFocus=true;drawSandbox();});
canvas.addEventListener('focus',()=>{showFocus=true;drawSandbox();});canvas.addEventListener('blur',()=>{showFocus=false;drawSandbox();});
document.querySelectorAll('[data-preset]').forEach(button=>{button.setAttribute('aria-pressed',String(button.dataset.preset==='detour'));button.addEventListener('click',()=>{blocked=preset(button.dataset.preset,WIDTH,HEIGHT);document.querySelectorAll('[data-preset]').forEach(b=>{const active=b===button;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});drawSandbox();});});
drawSandbox();initialise();
