// Project coordinates onto an image without changing the solver's path geometry.
export function projectPoint(point, bounds, width=1100, height=1100) {
  return [(point[0]-bounds[0])/(bounds[2]-bounds[0])*width,
          (bounds[3]-point[1])/(bounds[3]-bounds[1])*height];
}
export function routeViewport(rows, fullBounds, regional=false) {
  if(regional)return [...fullBounds];
  const points=rows.flatMap(r=>[...(r.path_xy_m||[]),...(r.baseline_xy_m||[])]);
  if(!points.length)return [...fullBounds];
  const xs=points.map(p=>p[0]),ys=points.map(p=>p[1]);
  const minX=Math.min(...xs),maxX=Math.max(...xs),minY=Math.min(...ys),maxY=Math.max(...ys);
  const size=Math.min(Math.max(maxX-minX+18000,maxY-minY+18000,40000),fullBounds[2]-fullBounds[0],fullBounds[3]-fullBounds[1]);
  const left=Math.max(fullBounds[0],Math.min((minX+maxX-size)/2,fullBounds[2]-size));
  const bottom=Math.max(fullBounds[1],Math.min((minY+maxY-size)/2,fullBounds[3]-size));
  return [left,bottom,left+size,bottom+size];
}
