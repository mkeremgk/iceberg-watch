import assert from 'node:assert/strict';
import {projectPoint,routeViewport} from './route_geometry.mjs';
const full=[400000,1800000,500000,1900000];
assert.deepEqual(projectPoint([400000,1900000],full),[0,0]);
assert.deepEqual(projectPoint([500000,1800000],full),[1100,1100]);
assert.deepEqual(projectPoint([450000,1850000],full),[550,550]);
const rows=[{path_xy_m:[[410000,1810000],[420000,1825000]],baseline_xy_m:[[410000,1810000],[425000,1820000]]}];
const view=routeViewport(rows,full);
for(const p of [...rows[0].path_xy_m,...rows[0].baseline_xy_m]){
 const [x,y]=projectPoint(p,view);assert(x>=0&&x<=1100&&y>=0&&y<=1100);
}
assert.equal(view[2]-view[0],view[3]-view[1]);
assert.deepEqual(routeViewport(rows,full,true),full);
assert.deepEqual(routeViewport([],full),full);
console.log('Route projection, framing and regional extent checks passed.');
