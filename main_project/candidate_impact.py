"""Measure individual candidate interventions without changing the production scenario."""
import csv
import hashlib
import json
import time
from pathlib import Path

import cv2
import numpy as np
from access import frontier, shortest_access
from fixed_boundary_scenario import fill_candidates
from map_io import DIRECTORY, read
from validate_fixed_boundary import check_path


def outcome_change(reference, trial, spacing):
    """Separate feasibility, length, chosen geometry and endpoint changes."""
    found = reference['status'] == trial['status'] == 'model_path_found'
    old, new = reference.get('path', []), trial.get('path', [])
    geometry = [list(p) for p in old] != [list(p) for p in new]
    delta = trial['distance_m'] - reference['distance_m'] if found else None
    endpoint = float(np.linalg.norm(np.array(old[-1])-new[-1])*spacing) if found else None
    return dict(status_changed=reference['status'] != trial['status'],
                distance_change_m=delta, distance_changed=found and abs(delta)>1e-6,
                chosen_path_changed=geometry, endpoint_shift_m=endpoint,
                equal_length_path_change=found and abs(delta)<=1e-6 and geometry)


def interventions(domain, target, start, spacing, cells, baseline=None, full=None):
    """Keep overlap counts so removing one object never removes another object's cells."""
    coverage = np.zeros(domain.size, np.uint16)
    for indices in cells:
        coverage[indices] += 1
    coverage = coverage.reshape(domain.shape)
    def solve(blocked):
        allowed = domain & ~blocked
        result = shortest_access(np.where(allowed, 1., np.inf), target, start, spacing)
        check_path(result, allowed, target, start, spacing)
        return result
    baseline = baseline or solve(np.zeros(domain.shape, bool))
    check_path(baseline, domain, target, start, spacing)
    computed_full = solve(coverage > 0)
    if full is not None and (outcome_change(full, computed_full, spacing)['chosen_path_changed'] or
                             full['status'] != computed_full['status']):
        raise ValueError('Full candidate audit does not reproduce saved route')
    full = computed_full
    records = []
    for indices in cells:
        blocked_single = np.zeros(domain.size, bool)
        blocked_single[indices] = True
        blocked_single = blocked_single.reshape(domain.shape)
        effective = bool(np.any(blocked_single & domain))
        single = solve(blocked_single) if effective else baseline
        remaining = (coverage > 0) & ~(blocked_single & (coverage == 1))
        removed = solve(remaining) if effective else full
        a, b = outcome_change(baseline, single, spacing), outcome_change(full, removed, spacing)
        if a['distance_change_m'] is not None and a['distance_change_m'] < -1e-6:
            raise ValueError('Adding an obstacle shortened a route')
        if b['distance_change_m'] is not None and b['distance_change_m'] > 1e-6:
            raise ValueError('Removing an obstacle lengthened a route')
        records.append(dict(domain_cells=int(np.sum(blocked_single & domain)),
                            unique_domain_cells=int(np.sum(blocked_single & domain & (coverage == 1))),
                            single_candidate=a, removed_from_all=b,
                            single_status=single['status'], removed_status=removed['status']))
    return records, full


def component_cells(labels, stats, identity, factor, valid_domain):
    """Fill each retained object on its native grid, then conservatively aggregate."""
    x,y,w,h,_ = stats[identity]
    region = (labels[y:y+h,x:x+w] == identity).astype('uint8')
    contours,_ = cv2.findContours(region,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    filled = np.zeros(region.shape,np.uint8)
    cv2.drawContours(filled,contours,-1,1,cv2.FILLED)
    selected = (filled>0) & valid_domain[y:y+h,x:x+w]
    rr,cc = np.where(selected)
    indices = np.unique(((rr+y)//factor)*(labels.shape[1]//factor)+(cc+x)//factor)
    return indices, int(selected.sum())


def main():
    began=time.monotonic(); inputs={}
    def record(path):
        inputs[str(path.relative_to(DIRECTORY))]=hashlib.sha256(path.read_bytes()).hexdigest()
        return path
    source=json.loads(record(DIRECTORY/'fixed_boundary_scenario.json').read_text())
    surface,p=read(record(DIRECTORY/'paper_scenario_surface_20250821.tif'))
    land,_=read(record(DIRECTORY/'land_mask.tif'),p)
    dates=sorted({r['date'] for e in source['experiments'] for r in e['dates']})
    common=np.ones(surface.shape,bool)
    for date in dates:
        im,_=read(record(DIRECTORY/f'sar_{date}.tif'),p);common &= np.isfinite(im)
    xy=(~p['transform'])*tuple(source['fixed_start_projected']); h,w=surface.shape
    scenarios=[]
    for date in dates:
        proposal,_=read(record(DIRECTORY/f'proposals_{date}.tif'),p)
        sar,_=read(DIRECTORY/f'sar_{date}.tif',p)
        _,labels,stats,_=cv2.connectedComponentsWithStats(((proposal>0)&(land==0)&np.isfinite(sar)).astype('uint8'),connectivity=8)
        with record(DIRECTORY/f'review_candidates_{date}.csv').open() as f: table=list(csv.DictReader(f))
        review,_=read(record(DIRECTORY/f'review_classes_{date}.tif'),p)
        for row in table:
            identity=int(row['component_id'])
            if abs(stats[identity,cv2.CC_STAT_AREA]*1600/1e6-float(row['area_km2']))>1e-9:
                raise ValueError('Candidate table does not match reconstructed component IDs')
            if not np.all(review[labels==identity]==int(row['class_code'])):
                raise ValueError('Candidate class mismatch')
        for experiment in source['experiments']:
            spacing=experiment['spacing_m'];factor=int(spacing/40);policy=experiment['policy']
            selected=[r for r in table if policy=='all_retained' or r['class_code']=='1']
            def blocks(a): return a.reshape(h//factor,factor,w//factor,factor)
            allowed=blocks((surface>0)&common).all(axis=(1,3))
            ribbon=blocks(surface==2).any(axis=(1,3))&allowed
            approach=allowed&~ribbon;target=frontier(ribbon,approach);domain=approach|target
            start=(int(xy[1])//factor,int(xy[0])//factor)
            pairs=[component_cells(labels,stats,int(row['component_id']),factor,common&(surface>0)) for row in selected]
            cells=[a for a,b in pairs]
            union=np.zeros(domain.size,bool)
            for indices in cells: union[indices]=True
            production=fill_candidates(review,policy)&common&(surface>0)
            expected=blocks(production).any(axis=(1,3))
            if not np.array_equal(union.reshape(domain.shape),expected):
                raise ValueError('Per-object union differs from production obstacle mask')
            saved=next(r for r in experiment['dates'] if r['date']==date)
            records,full=interventions(domain,target,start,spacing,cells,experiment['baseline'],saved)
            for row,metrics,(_,fine_count) in zip(selected,records,pairs):
                metrics.update(component_id=int(row['component_id']),class_code=int(row['class_code']),
                               easting_m=float(row['easting_m']),northing_m=float(row['northing_m']),
                               area_km2=float(row['area_km2']),fine_pixels_in_surface=fine_count)
            for metrics,indices in zip(records,cells):metrics['coarse_cells']=len(indices)
            def changed(r,key):
                v=r[key];return v['status_changed'] or v['distance_changed'] or v['chosen_path_changed']
            summary=dict(candidates_detected=len(records),in_route_domain=sum(r['domain_cells']>0 for r in records),
                single_effect_count=sum(changed(r,'single_candidate') for r in records),
                removal_effect_count=sum(changed(r,'removed_from_all') for r in records),
                any_tested_effect_count=sum(changed(r,'single_candidate') or changed(r,'removed_from_all') for r in records),
                distance_or_feasibility_effect_count=sum(any(r[k]['status_changed'] or r[k]['distance_changed'] for k in ('single_candidate','removed_from_all')) for r in records),
                lost_on_aggregation=sum(r['fine_pixels_in_surface']>0 and r['coarse_cells']==0 for r in records))
            scenarios.append(dict(date=date,spacing_m=spacing,policy=policy,summary=summary,
                baseline_distance_m=experiment['baseline']['distance_m'],all_distance_m=full.get('distance_m'),candidates=records))
            print(date,spacing,policy,summary,flush=True)
    output=dict(status='completed_software_interventions_not_physical_causation',scenarios=scenarios,
        input_sha256=inputs,source_sha256={name:hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest() for name in ('candidate_impact.py','access.py','fixed_boundary_scenario.py','validate_fixed_boundary.py')},
        checks=['candidate IDs and class match source table','per-object union equals production barrier mask','all saved full routes reproduced','every recalculated path checked for barriers and corners','monotonic distance checks','conservative aggregation retention'],
        limitations=['Effect refers to this fixed reference scenario, not biological harm.',
        'Single-candidate addition and removal from all are different interventions; their effects are not additive.',
        'Chosen path changes can be equal-cost tie choices, not distance effects.',
        'Zero effect in these tests does not exclude effects under other candidate subsets, starts, boundaries or corridors.',
        'Candidate IDs are per-date components, not verified iceberg identities.'])
    folder=DIRECTORY/'candidate_impact';folder.mkdir(exist_ok=True)
    (folder/'results.json').write_text(json.dumps(output,indent=2)+'\n')
    print('Candidate impact audit complete in',round(time.monotonic()-began,1),'seconds')

if __name__=='__main__':main()
