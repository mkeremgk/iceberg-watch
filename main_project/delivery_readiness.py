"""Report implementation and evidence gaps without claiming competition compliance."""
import json
import hashlib
from pathlib import Path
from map_io import DIRECTORY


def main():
    def read(name):
        path=DIRECTORY/name
        return json.loads(path.read_text()) if path.exists() else {}
    temporal=read('temporal_comparison.json');reviews=read('association_review/review_summary.json')
    pairs=temporal.get('pairs',[])
    ready=[p for p in pairs if p['status']=='distance_comparison_computed']
    fixed=read('fixed_boundary_scenario.json')
    fixed_ready=any(c.get('status')=='distance_comparison_computed' for e in fixed.get('experiments',[]) for c in e.get('comparisons',[]))
    aws=read('aws_fixed_boundary_validation_20261019.json')
    evidence_files=sorted(DIRECTORY.glob('aws_pipeline_validation_????????.json'))
    pipeline=read(evidence_files[-1].name) if evidence_files else {}
    root=Path(__file__).resolve().parent
    source_hashes=pipeline.get('source_sha256',{})
    sources_current=bool(source_hashes) and all(
        (root/name).exists() and hashlib.sha256((root/name).read_bytes()).hexdigest()==digest
        for name,digest in source_hashes.items())
    pipeline_verified=(pipeline.get('status')=='passed' and sources_current
                       and pipeline.get('unit_tests_passed',0)>0)
    fixed_pairs={ (c['earlier_date'],c['later_date']) for e in fixed.get('experiments',[]) for c in e.get('comparisons',[]) if c.get('status')=='distance_comparison_computed'}
    result={'aws_current_pipeline_verified':pipeline_verified,
            'aws_evidence_file':evidence_files[-1].name if evidence_files else None,
            'fixed_boundary_date_pairs':len(fixed_pairs),
            'aws_fixed_boundary_results_match':aws.get('results_byte_identical',False),
            'active_scope':'fixed-boundary counterfactual approved 2026-10-18',
            'main_question_has_model_results':fixed_ready, 'actual_temporal_access_answered':bool(ready),'comparable_date_pairs':len(ready),
            'human_review_counts':reviews.get('counts',{}),
            'software_checks':read('output_validation.json').get('status','not_run'),
            'remaining':[{'task':'Second date-matched target and surface evidence','type':'evidence','status':'outside_current_fixed_boundary_scope'},
                         {'task':'Independent detection evaluation including missed objects','type':'evaluation','status':'pending'},
                         {'task':'Fragmentation handling without merging real separate objects','type':'algorithm','status':'pending'},
                         {'task':'Prepared-grid-to-report pipeline and tests on AWS','type':'integration','status':'verified' if pipeline_verified else 'pending'}],
            'interpretation':'Readiness checklist, not a completion percentage or competition eligibility certification.'}
    (DIRECTORY/'delivery_readiness.json').write_text(json.dumps(result,indent=2))
    print('Fixed-boundary date pairs:',len(fixed_pairs),'; observed-environment date pairs:',len(ready))

if __name__=='__main__':main()
