"""Rebuild the local report from existing outputs without rerunning SAR analysis."""
import argparse
import hashlib
import json
from html import escape
from map_io import DIRECTORY


def concise_results():
    """One comparable setting, with assumptions visible before technical details."""
    path = DIRECTORY/'fixed_boundary_scenario.json'
    if not path.exists():
        return '<p>Fixed-boundary results have not been generated.</p>'
    report = json.loads(path.read_text())
    experiment = next(e for e in report['experiments']
                      if e['spacing_m']==80 and e['policy']=='offshore_only')
    text = '<section><h2>What did we find?</h2><p>Four dates, the same assumed August water boundary and colony start. Only the candidate barriers change. Example below: 80 m grid, offshore candidates only.</p><table><tr><th>Date</th><th>Model route</th><th>Extra distance due to candidates</th></tr>'
    for result in experiment['dates']:
        date=result['date'];label=f'{date[:4]}-{date[4:6]}-{date[6:]}'
        length=f"{result['distance_m']/1000:.3f} km" if result['status']=='model_path_found' else 'Unavailable'
        extra=result.get('extra_distance_vs_fixed_baseline_m')
        change=f'{extra:.0f} m' if extra is not None else 'Unavailable'
        text+=f'<tr><td>{label}</td><td>{length}</td><td>{change}</td></tr>'
    return text+'</table><p>These are model results, not observed penguin routes. Small differences are sensitive to candidate boundaries; they do not establish a real ecological effect. Corridor experiments restrict the allowed travel area but do not verify ice or water.</p><p><a href="scenario_explorer/index.html">Compare dates and settings</a> · <a href="#corridor-results">Corridor assumptions and results</a></p></section>'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper-scenario', action='store_true')
    args = parser.parse_args()
    summary=json.loads((DIRECTORY/'environment_report.json').read_text())
    associations=json.loads((DIRECTORY/'association_report.json').read_text())
    rows=''.join(f'<tr><td>{d}</td><td>{counts["1"]}</td><td>{sum(counts.values())-counts["1"]}</td><td>{escape(json.loads((DIRECTORY/f"access_{d}.json").read_text())["baseline"]["status"])}</td></tr>' for d,counts in summary.items())
    page=f'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Iceberg Watch — research prototype</title>
<style>body{{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 20px;color:#193047;background:#f5f8fa}}img{{max-width:100%;background:white}}table{{border-collapse:collapse;width:100%}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #ccd}}section{{margin:30px 0}}.notice{{padding:18px;background:#fff1d6}}</style>
<h1>Iceberg Watch</h1><p><a href="scenario_explorer/index.html">Explore dates, barriers and routes</a></p><p><a href="#fixed-results">Fixed-boundary results</a> · <a href="#route-geometry">Route geometry</a> · <a href="#detection-review">Visual review</a> · <a href="#execution">Execution evidence</a></p><p class="notice">Active scope: fixed-boundary counterfactual approved on 18 October 2026. Actual temporal open-water access change is not established. This page displays existing outputs, not a fresh scientific validation.</p><p>Multi-object proposals and conditional open-water access research prototype.</p>
<p class="notice">Not observed penguin GPS routes. Candidate identities and historical colony position are unverified. Missing environmental evidence is reported explicitly.</p>
<table><tr><th>Date</th><th>Offshore proposals</th><th>Review regions</th><th>Real-scene access status</th></tr>{rows}</table>
<section><h2>Provisional associations</h2><p>{len(associations['links'])} mutual-best links. Ambiguous/unmatched regions are not evidence of disappearance.</p><img src="provisional_tracks.png" alt="Provisional candidate centroid associations"></section>
'''
    if (DIRECTORY/'sea_ice_context.png').exists():page+='<section><h2>Regional sea-ice context</h2><p>6.25 km native spacing; not fine-scale open-water ground truth.</p><img src="sea_ice_context.png" alt="Daily regional ice concentration"></section>'
    for date in summary:
        if (DIRECTORY/f'access_{date}.png').exists():page+=f'<section><h2>Conditional model: {date}</h2><img src="access_{date}.png" alt="Modelled access scenario"></section>'
    if args.paper_scenario:
        marker='<table><tr><th>Date</th>'
        page=page.replace(marker,concise_results()+'<details><summary>Detailed analysis and checks</summary>'+marker,1)
    review_path=DIRECTORY/'association_review/review_summary.json'
    if review_path.exists():
        reviews=json.loads(review_path.read_text())
        page+='<section><h2>Human review status</h2><p>'+escape(str(reviews['counts']))+'</p><p>Review decisions are separate from automatic tracks. Acceptance is not measured tracking accuracy.</p><p><a href="association_review/evaluation.md">Review assessment and attention queue</a></p></section>'
    page+='<p><a href="association_review/review.html">Review all provisional associations</a></p>'
    if args.paper_scenario and (DIRECTORY/'fixed_boundary_scenario.png').exists():
        page+='<section id="fixed-results"><h2>Fixed-boundary counterfactual</h2><p>Same August boundary and colony start, different date-specific candidate obstacles. NOT observed July water conditions or penguin routes.</p><img src="fixed_boundary_scenario.png" alt="Fixed-boundary candidate obstacle comparison"><p><a href="fixed_boundary_scenario.json">Assumptions, distances and comparisons</a> · <a href="fixed_boundary_summary.md">Sensitivity summary</a></p></section>'
    if args.paper_scenario and (DIRECTORY/'fixed_boundary_summary.json').exists():
        sensitivity=json.loads((DIRECTORY/'fixed_boundary_summary.json').read_text())
        page+='<section><h2>Change across tested settings</h2><p>Ranges are sensitivity results, not confidence intervals. Small differences do not establish a physical effect.</p><table><tr><th>Date pair</th><th>Change range (m)</th><th>Direction</th></tr>'
        for pair in sensitivity['pairs']:
            value='Unavailable' if pair['min_change_m'] is None else f"{pair['min_change_m']:.0f} to {pair['max_change_m']:.0f}"
            page+=f"<tr><td>{escape(pair['date_pair'])}</td><td>{value}</td><td>{escape(pair['direction_across_tested_settings'])}</td></tr>"
        page+='</table></section>'
    stress_path=DIRECTORY/'obstacle_sensitivity/results.json'
    if args.paper_scenario and stress_path.exists():
        stress=json.loads(stress_path.read_text())
        fresh=stress['source_sha256']==hashlib.sha256((DIRECTORY/'fixed_boundary_scenario.json').read_bytes()).hexdigest()
        page+='<section><h2>Candidate-boundary stability</h2>'
        if fresh:
            page+='<p>Chosen ±40/80 m mask perturbations. All dates use the same water reference and start. Ranges are sensitivity envelopes, not confidence intervals; independent offsets can reverse the sign of small date differences.</p><img src="obstacle_sensitivity/comparison.png" alt="Nominal, shared-offset and independent-offset distance changes"><p><a href="obstacle_sensitivity/summary.md">All settings and limitations</a></p>'
        else:page+='<p class="notice">Boundary sensitivity is stale; rerun the separate experiment.</p>'
        page+='</section>'
    corridor_path=DIRECTORY/'corridor_scenario/results.json'
    if args.paper_scenario and corridor_path.exists():
        corridor=json.loads(corridor_path.read_text())
        sources={'fixed_boundary_scenario.json':corridor['source_sha256'],**corridor['input_sha256']}
        fresh=all((DIRECTORY/name).exists() and hashlib.sha256((DIRECTORY/name).read_bytes()).hexdigest()==digest for name,digest in sources.items())
        page+='<section id="corridor-results"><h2>How much does the allowed travel area matter?</h2><p>Additional experiment: restrict travel to a fixed corridor around the no-candidate reference path. Total widths are 500, 1000 and 2000 m. Obstacles stay unchanged; the August target set is intersected with the corridor.</p>'
        if fresh:
            trials=[r for experiment in corridor['experiments'] for r in experiment['dates']]
            found=sum(r['status']=='model_path_found' for r in trials)
            page+=f'<p>{found} of {len(trials)} trials have a feasible model path; {len(trials)-found} are infeasible under their assumptions. Failed routes are unavailable, not zero-distance routes.</p><p><a href="corridor_scenario/index.html">Compare corridor widths and inspect every outcome</a></p>'
        else:
            page+='<p class="notice">Corridor results are stale relative to current inputs. Rerun corridor_scenario.py and plot_corridor_scenario.py.</p>'
        page+='<p>This does not classify liquid water or establish a safe ice corridor. Nominal results above are retained; no corridor width is selected as scientifically validated. A blocked model corridor does not establish actual colony isolation.</p></section>'
    impact_path=DIRECTORY/'candidate_impact/results.json'
    if args.paper_scenario and impact_path.exists():
        impact=json.loads(impact_path.read_text())
        fresh=all((DIRECTORY/name).exists() and hashlib.sha256((DIRECTORY/name).read_bytes()).hexdigest()==digest for name,digest in impact['input_sha256'].items())
        page+='<section><h2>Which candidates affect the model?</h2>'
        if fresh:
            page+='<p>Each candidate is tested alone and by removing it from the complete barrier set. A counted effect changes distance, feasibility or the selected grid path in at least one test. Counts are scenario specific and are not biological impacts.</p><table><tr><th>Date</th><th>Grid / policy</th><th>Detected</th><th>In route domain</th><th>Any tested effect</th><th>Distance or feasibility effect</th></tr>'
            for row in impact['scenarios']:
                count=row['summary']
                page+=f"<tr><td>{row['date']}</td><td>{row['spacing_m']} / {escape(row['policy'])}</td><td>{count['candidates_detected']}</td><td>{count['in_route_domain']}</td><td>{count['any_tested_effect_count']}</td><td>{count['distance_or_feasibility_effect_count']}</td></tr>"
            page+='</table><p>No retained surface pixels were lost during conservative grid aggregation. Every full route reproduced the saved route, and recalculated paths passed barrier and corner checks. Equal length alternatives and overlapping barriers mean that individual effects cannot be added together.</p><p><a href="candidate_impact/results.json">Candidate interventions and provenance</a></p>'
        else:page+='<p>Candidate impact results are stale and must be regenerated.</p>'
        page+='</section>'
    geometry_path=DIRECTORY/'route_geometry_audit.json'
    if args.paper_scenario and geometry_path.exists():
        audit=json.loads(geometry_path.read_text())
        current=hashlib.sha256((DIRECTORY/'fixed_boundary_scenario.json').read_bytes()).hexdigest()==audit['source_sha256']
        page+='<section id="route-geometry"><h2>Route geometry, beyond length</h2><p>The destination is a fixed SET of boundary cells. The chosen endpoint can differ by date. Equal lengths do not imply identical paths. Exact grid-edge overlap is sensitive to equal-cost alternatives.</p>'
        if not current:
            page+='<p class="notice">Geometry audit is stale; rerun route_geometry_audit.py.</p>'
        else:
            page+='<table><tr><th>Date pair</th><th>Grid / policy</th><th>Same path cells?</th><th>Endpoint shift (m)</th></tr>'
            for row in audit['comparisons']:
                if row['status']!='computed':continue
                page+=f"<tr><td>{row['earlier_date']}–{row['later_date']}</td><td>{row['spacing_m']} / {escape(row['policy'])}</td><td>{row['identical_ordered_cells']}</td><td>{row['endpoint_shift_m']:.0f}</td></tr>"
            page+='</table><p><a href="route_geometry_audit.md">Shared path lengths and geometric differences</a></p>'
        page+='</section>'
    page+='<section id="detection-review"><h2>Blinded visual-review pilot</h2>'
    for review_file in sorted((DIRECTORY/'detection_review').glob('*/comparison_summary.json')):
        visual=json.loads(review_file.read_text());relative=review_file.parent.relative_to(DIRECTORY).as_posix()
        page+=f"<p>{visual['marks']} marks across {visual['reviewed_tiles']} reviewed images. User-selected classes: {escape(str(visual['user_class_counts']))}. The reviewer expressed uncertainty about all marks.</p>"
        page+=f'<p>Recorded point overlaps: {visual["points_on_raw_proposals"]} with raw proposals, {visual["points_on_retained_regions"]} with retained regions. These are historical point/mask overlap counts, NOT precision or recall. A centre outside a mask does not prove a missed iceberg.</p><p><a href="{relative}/comparison_summary.md">Import provenance and limitations</a></p>'
    page+='</section>'
    readiness_path=DIRECTORY/'delivery_readiness.json'
    if readiness_path.exists():
        readiness=json.loads(readiness_path.read_text())
        page+='<section id="execution"><h2>Execution and evidence</h2>'
        page+=f"<p>Fixed-boundary date pairs with results: {readiness.get('fixed_boundary_date_pairs',0)}. Current-source AWS pipeline verification: {readiness['aws_current_pipeline_verified']}.</p>"
        evidence=readiness.get('aws_evidence_file')
        if evidence:page+=f'<p><a href="{escape(evidence)}">AWS execution record and checks</a></p>'
        page+='<p>Prepared common-grid maps to report; raw SAR map preparation is a separate step. Software checks do not establish scientific accuracy.</p></section>'
    if args.paper_scenario:
        page+='<section><h2>21 August: paper-derived conditional access</h2><p>User-approved approximate scenario, NOT surveyed surfaces or observed routes. General reviewed-surface analysis above remains data-limited. See paper_access_scenario.json for sensitivity and assumptions. Boundary/colony reference: <a href="https://www.nature.com/articles/s43247-026-03764-w/figures/5">Park et al. (2026), Figure 5</a>. Local research use; review source rights before public release.</p><img src="paper_access_scenario.png" alt="Conditional August access"><p><a href="paper_access_scenario.json">Scenario results and sensitivity</a></p></section>'
    page+='<section><h2>Algorithm check — synthetic only</h2><p>The example below demonstrates detours and a closed passage. It is not an Antarctic result.</p><img src="synthetic_access_demo.png" alt="Synthetic route test"></section><p>See the final technical report in main_project/submission/TECHNICAL_REPORT.md and the generated JSON reports for assumptions and data sources.</p></html>'
    if args.paper_scenario:
        page=page.replace('</html>','</details></html>')
    (DIRECTORY/'index.html').write_text(page)
    print('Report:',DIRECTORY/'index.html')

if __name__=='__main__':main()
