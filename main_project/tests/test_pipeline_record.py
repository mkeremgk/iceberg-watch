"""A failed subprocess must never be recorded as a successful full pipeline."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_pipeline


class PipelineRecord(unittest.TestCase):
    def test_missing_inputs_record_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(run_pipeline, 'DIRECTORY', root), \
                 patch.object(sys, 'argv', ['run_pipeline.py']):
                with self.assertRaises(FileNotFoundError):
                    run_pipeline.main()
            record = json.loads(next((root/'pipeline_runs').glob('*.json')).read_text())
            self.assertEqual(record['status'], 'failed')
            self.assertEqual(record['steps'], [])
            self.assertIn('Prepare', record['error'])

    def exercise(self, error=None):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'sar_20250821.tif').touch()
            with patch.object(run_pipeline, 'DIRECTORY', root), \
                 patch.object(sys, 'argv', ['run_pipeline.py', '--paper-scenario']), \
                 patch.object(run_pipeline.subprocess, 'run', side_effect=error):
                if error:
                    with self.assertRaises(subprocess.CalledProcessError):
                        run_pipeline.main()
                else:
                    run_pipeline.main()
            records = list((root / 'pipeline_runs').glob('*.json'))
            self.assertEqual(len(records), 1)
            return json.loads(records[0].read_text())

    def test_failure_stops_and_records_failed_stage(self):
        result = self.exercise(subprocess.CalledProcessError(1, 'extract_candidates.py'))
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(len(result['steps']), 1)
        self.assertEqual(result['steps'][0]['status'], 'failed')

    def test_success_records_complete_order(self):
        result = self.exercise()
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['scope'], 'prepared_common_grid_to_report')
        self.assertEqual(result['steps'][-1]['script'], 'create_manifest.py')
        self.assertTrue(all(s['status'] == 'passed' for s in result['steps']))
        self.assertIn('fixed_boundary_scenario.py', [s['script'] for s in result['steps']])
