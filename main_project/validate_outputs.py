"""Validate generated grid/route contracts without asserting ecological correctness."""
import json,math
from datetime import datetime
import cv2
import numpy as np
from map_io import DIRECTORY,read


def main():
    checks={};reference=None
    for path in sorted(DIRECTORY.glob('sar_*.tif')):
        date=path.stem[4:];image,p=read(path,reference);reference=p
        env,_=read(DIRECTORY/f'environment_{date}.tif',p)
        if not np.array_equal(env==255,~np.isfinite(image)):raise ValueError('No-data mismatch')
        review,_=read(DIRECTORY/f'review_classes_{date}.tif',p)
        if not np.isin(review,[0,1,2,3,4,5]).all():raise ValueError('Unexpected review code')
        if np.any((review>0)&~np.isfinite(image)):raise ValueError('Candidates outside valid SAR')
        checks[date]='grid, no-data, review codes valid'
    associations=json.loads((DIRECTORY/'association_report.json').read_text())['links']
    left=set();right=set()
    for link in associations:
        days=(datetime.strptime(link['to_date'],'%Y%m%d')-datetime.strptime(link['from_date'],'%Y%m%d')).days
        if not 0<days<=12:raise ValueError('Association crosses disallowed temporal gap')
        a=(link['from_date'],link['from_id'],link['to_date']);b=(link['from_date'],link['to_date'],link['to_id'])
        if a in left or b in right:raise ValueError('Association not one-to-one')
        left.add(a);right.add(b)
    scenario_path=DIRECTORY/'paper_access_scenario.json'
    routes_checked=0
    if scenario_path.exists():
        report=json.loads(scenario_path.read_text());surface,p=read(DIRECTORY/'paper_scenario_surface_20250821.tif')
        filled,_=read(DIRECTORY/'paper_scenario_barriers_20250821.tif',p)
        review,_=read(DIRECTORY/'review_classes_20250821.tif',p)
        for result in report['results']:
            if not result['path']:continue
            factor=result['grid_spacing_m']//40;h,w=surface.shape
            def blocks(a):return a.reshape(h//factor,factor,w//factor,factor)
            allowed=blocks(surface>0).all(axis=(1,3))
            obstacles=filled.copy()
            if result['scenario']=='offshore_candidates_only':
                contours,_=cv2.findContours((review==1).astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
                obstacles=np.zeros_like(filled);cv2.drawContours(obstacles,contours,-1,1,cv2.FILLED);obstacles[surface==0]=0
            if result['scenario']!='no_candidate_barriers':
                radius=int(np.ceil(result['buffer_m']/40))
                if radius:obstacles=cv2.dilate(obstacles,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*radius+1,2*radius+1)))
                allowed&=~blocks(obstacles>0).any(axis=(1,3))
            path=[tuple(x) for x in result['path']]
            if not all(allowed[cell] for cell in path):raise ValueError('Route crosses blocked cell')
            target=blocks(surface==2).any(axis=(1,3))
            if not target[path[-1]]:raise ValueError('Route does not end at target')
            length=0
            for a,b in zip(path,path[1:]):
                dr=b[0]-a[0];dc=b[1]-a[1]
                if max(abs(dr),abs(dc))!=1:raise ValueError('Route has non-adjacent steps')
                if dr and dc and not (allowed[a[0],b[1]] and allowed[b[0],a[1]]):raise ValueError('Route cuts blocked corner')
                length+=math.hypot(dr,dc)*result['grid_spacing_m']
            if not math.isclose(length,result['distance_m'],abs_tol=1e-6):raise ValueError('Route distance mismatch')
            routes_checked+=1
    result={'checks':checks,'association_links_checked':len(associations),'scenario_routes_checked':routes_checked,
            'status':'software_contracts_passed_not_scientific_validation'}
    (DIRECTORY/'output_validation.json').write_text(json.dumps(result,indent=2));print(result)

if __name__=='__main__':main()
