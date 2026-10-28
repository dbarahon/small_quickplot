import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('filter_quickplot', ROOT / 'filter_quickplot.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class LocalWorkflow(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'experiment'
        self.source.mkdir()
        (self.source / 'HISTORY.rc').write_text('EXPID: test\n')
        self.geos = self.base / 'geos'
        (self.geos / 'plots').mkdir(parents=True)
        rcdir = self.geos / 'plots/VERIFICATION_RCS'
        rcdir.mkdir()
        (rcdir / 'VERIFICATION.ISCCP.rc').write_text('')
        self.quickplot = self.geos / 'plots/quickplot'
        self.quickplot.write_text('#!/bin/sh\nexit 0\n')
        self.quickplot.chmod(0o755)
        for kind in ['portrait', 'landscape']:
            (self.geos / 'plots' / (kind + '.script')).write_text('driver fixture\n')
            rows = []
            for i, (orientation, command) in enumerate(module.PROFILE, 100):
                if orientation.lower() == kind:
                    rows.append(f'if ( plot == {orientation}.{i} ) {command}')
            (self.base / (kind + '.list')).write_text('\n'.join(rows) + '\n')
        self.run = self.base / 'run'

    def prepare(self):
        return subprocess.run([sys.executable, str(ROOT / 'prepare_small_quickplot.py'),
                               '--source', str(self.source), '--geosutil', str(self.geos),
                               '--season', 'DJF', '--begdate', '201912', '--enddate', '202002',
                               '--run-dir', str(self.run),
                               '--portrait-map', str(self.base / 'portrait.list'),
                               '--landscape-map', str(self.base / 'landscape.list')],
                              capture_output=True, text=True)

    def test_prepare_without_masterlist_and_preserve_new_dates(self):
        result = self.prepare()
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads((self.run / 'plan.json').read_text())
        self.assertEqual(len(plan['tasks']), 31)
        self.assertFalse((self.run / 'logs').exists())
        for task in plan['tasks']:
            args = task['args']
            self.assertEqual(args[args.index('-begdate') + 1], '201912')
            self.assertEqual(args[args.index('-enddate') + 1], '202002')
            self.assertEqual(args[args.index('-taylor') + 1], 'TRUE')
        self.assertNotEqual(self.prepare().returncode, 0)

    def test_missing_mapping_does_not_create_runnable_plan(self):
        (self.base / 'portrait.list').write_text('')
        self.assertNotEqual(self.prepare().returncode, 0)
        self.assertFalse((self.run / 'plan.json').exists())

    def test_references_loaded_from_directory(self):
        self.assertEqual(self.prepare().returncode, 0)
        plan = json.loads((self.run / 'plan.json').read_text())
        self.assertIn('ISCCP', plan['allowed_verification_rcs'])
        self.assertIn('MERRA2', plan['allowed_verification_rcs'])

    def test_runner_records_failure_and_timeout(self):
        self.assertEqual(self.prepare().returncode, 0)
        self.quickplot.write_text('#!' + sys.executable + '\nimport sys,time\n'
                                 'task=sys.argv[sys.argv.index("-plots")+1]\n'
                                 'if task.endswith(".100"): sys.exit(7)\n'
                                 'if task.endswith(".101"): time.sleep(30)\n')
        result = subprocess.run([sys.executable, str(ROOT / 'run_small_quickplot.py'),
                                 str(self.run / 'plan.json'), '--workers', '4', '--timeout', '1'],
                                capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 1, result.stderr)
        records = json.loads((self.run / 'summary.json').read_text())
        states = [r['state'] for r in records]
        self.assertEqual(states.count('failed'), 1)
        self.assertEqual(states.count('timeout'), 1)
        self.assertEqual(states.count('returned_zero'), 29)
        self.assertFalse((self.run / '.runner-lock').exists())

    def test_driver_change_blocks_execution(self):
        self.assertEqual(self.prepare().returncode, 0)
        (self.geos / 'plots/portrait.script').write_text('changed\n')
        result = subprocess.run([sys.executable, str(ROOT / 'run_small_quickplot.py'),
                                 str(self.run / 'plan.json')], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('driver changed', result.stderr)
        self.assertFalse((self.run / 'logs').exists())


if __name__ == '__main__':
    unittest.main()
