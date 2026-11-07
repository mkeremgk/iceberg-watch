"""Reproducible local/EC2 batch entry point; no GUI or remote deployment required."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
import subprocess
import sys
from pathlib import Path
from map_io import DIRECTORY


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild-maps',action='store_true',help='Expensive raw SAR TPS preparation')
    parser.add_argument('--paper-scenario',action='store_true',help='Run approved approximate August paper scenario separately')
    parser.add_argument('--with-sea-ice',action='store_true',help='Download/cache daily AMSR2 context')
    args=parser.parse_args()
    root=Path(__file__).resolve().parent
    def now():
        return datetime.now(timezone.utc).isoformat()
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    history = DIRECTORY / 'pipeline_runs'
    history.mkdir(exist_ok=True)
    record_path = history / (started.strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    record = {'started_utc': started.isoformat(), 'status': 'running',
              'scope': 'raw_to_report' if args.rebuild_maps else 'prepared_common_grid_to_report',
              'arguments': vars(args), 'steps': [],
              'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in sorted(root.glob('*.py'))}}
    def save():
        record_path.write_text(json.dumps(record, indent=2))
    save()
    def run(name,*arguments):
        step = {'script': name, 'arguments': list(arguments), 'started_utc': now(),
                'status': 'running'}
        record['steps'].append(step)
        save()
        try:
            subprocess.run([sys.executable,str(root/name),*arguments],check=True)
        except (subprocess.SubprocessError, OSError, KeyboardInterrupt) as error:
            step.update(status='failed', error=str(error), finished_utc=now())
            record.update(status='failed', finished_utc=now())
            save()
            raise
        step.update(status='passed', finished_utc=now())
        save()
    try:
        if args.rebuild_maps:run('prepare_maps.py')
        dates=sorted(p.stem[4:] for p in DIRECTORY.glob('sar_*.tif'))
        if not dates:raise FileNotFoundError('Prepare common-grid SAR maps first')
        run('extract_candidates.py');run('prepare_environment.py');run('associate_candidates.py')
        if args.with_sea_ice:run('sea_ice_context.py')
        for date in dates:run('run_access.py','--date',date)
        run('temporal_comparison.py')
        run('access_demo.py')
        run('audit_associations.py')
        if args.paper_scenario:
            if '20250821' not in dates:raise ValueError('August21 SAR needed for paper scenario')
            run('register_paper.py');run('paper_access_scenario.py')
            run('fixed_boundary_scenario.py')
            run('summarize_fixed_boundary.py')
            run('validate_fixed_boundary.py')
            run('candidate_impact.py')
            run('route_geometry_audit.py')
            run('build_scenario_explorer.py')
        run('validate_outputs.py')
        run('review_associations.py')
        run('evaluate_reviews.py')
        run('build_review_context.py')
        run('build_review_ui.py')
        run('delivery_readiness.py')
        run('build_report.py', *(['--paper-scenario'] if args.paper_scenario else []))
        run('create_manifest.py')
    except (Exception, KeyboardInterrupt) as error:
        record.update(status='failed', error=str(error), finished_utc=now())
        save()
        raise
    record.update(status='passed', finished_utc=now())
    save()
    print('Pipeline execution record:', record_path)

if __name__=='__main__':main()
