#!/usr/bin/env python3
"""Build only the selected QuickPlot tasks; never submit or run plots."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from filter_quickplot import PROFILE, signature

SEASONS = 'JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC DJF MAM JJA SON ANN'.split()


def month(value):
    if not re.fullmatch(r'[0-9]{6}', value) or not 1 <= int(value[4:]) <= 12:
        raise argparse.ArgumentTypeError('Use YYYYMM with a valid month')
    return value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--season', choices=SEASONS, required=True)
    p.add_argument('--begdate', type=month, required=True)
    p.add_argument('--enddate', type=month, required=True)
    p.add_argument('--run-dir', type=Path, required=True, help='New directory for this diagnostic run')
    p.add_argument('--geosutil', type=Path, default=os.environ.get('GEOSUTIL'))
    p.add_argument('--portrait-map', type=Path)
    p.add_argument('--landscape-map', type=Path)
    p.add_argument('--history', type=Path)
    a = p.parse_args()
    if a.begdate > a.enddate:
        p.error('begdate must not follow enddate')
    if not a.geosutil:
        p.error('Set GEOSUTIL or supply --geosutil')
    if bool(a.portrait_map) != bool(a.landscape_map):
        p.error('Supply both mapping files or neither')
    source = a.source.resolve()
    geosutil = Path(a.geosutil).resolve()
    homdir = source
    if (source / '.HOMDIR').exists():
        homdir = Path((source / '.HOMDIR').read_text().strip())
    history = (a.history or homdir / 'HISTORY.rc').resolve()
    if not source.is_dir() or not history.is_file():
        p.error('Experiment directory and HISTORY.rc must exist')
    if not (geosutil / 'plots/quickplot').is_file():
        p.error('GEOSUTIL must contain plots/quickplot')
    run = a.run_dir.resolve()
    run.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(GEOSUTIL=str(geosutil), SOURCE=str(source), CMPEXP='',
               TAYLOR='true', CMPEXP_ONLY='FALSE', CMPOPS_ONLY='FALSE',
               STD_DEV='false', DO_STD='FALSE')
    available = {}
    for kind, supplied in [('PORTRAIT', a.portrait_map), ('LANDSCAPE', a.landscape_map)]:
        if supplied:
            text = supplied.read_text()
        else:
            csh = shutil.which('tcsh') or shutil.which('csh')
            if not csh:
                raise ValueError('csh/tcsh is required to enumerate installed plot drivers')
            driver = geosutil / 'plots' / (kind.lower() + '.script')
            # Source the installed configuration, not configure: do not recreate shared links.
            helper = Path(__file__).resolve().with_name('enumerate_plots.csh')
            with (run / (kind.lower() + '.trace')).open('w') as log:
                result = subprocess.run([csh, '-f', str(helper), str(geosutil),
                                         str(source), str(driver)], cwd=run, env=env,
                                        stdout=log, stderr=subprocess.STDOUT, timeout=600)
            if result.returncode:
                raise ValueError('Enumeration failed; inspect ' + str(run / (kind.lower() + '.trace')))
            text = (run / (kind.lower() + '.trace')).read_text()
        lines = []
        for line in text.splitlines():
            m = re.match(r'\s*if\s*\(\s*plot\s*==\s*(\S+)\s*\)\s*(.*)', line)
            if m:
                lines.append(line)
                available.setdefault((kind, signature(m[2])), []).append((m[1], line))
        (run / (kind.lower() + '.list')).write_text('\n'.join(lines) + '\n')
    tasks = []
    audit = []
    output = run / 'plots'
    for key in PROFILE:
        matches = available.get(key, [])
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous diagnostic: ' + repr(key) +
                             '. No runnable plan was written; inspect mapping files.')
        ident, line = matches[0]
        if not ident.startswith(key[0] + '.'):
            raise ValueError('Unexpected task identifier: ' + ident)
        args = ['-source', str(source), '-season', a.season,
                '-type', 'P' if key[0] == 'PORTRAIT' else 'L', '-plots', ident,
                '-clim', 'false', '-plotsdir', str(output), '-rc', str(history),
                '-begdate', a.begdate, '-enddate', a.enddate,
                '-cintdiff', 'ON', '-taylor', 'TRUE']
        tasks.append({'id': ident, 'args': args, 'mapping': line.strip()})
        audit.append(line)
    if len({t['id'] for t in tasks}) != len(tasks):
        raise ValueError('Multiple diagnostics resolved to the same ID')
    (run / 'selected.mapping.txt').write_text('\n'.join(audit) + '\n')
    hashes = {}
    for name in ['portrait.script', 'landscape.script']:
        path = geosutil / 'plots' / name
        if path.is_file(): hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    plan = {'version': 1, 'geosutil': str(geosutil), 'run_dir': str(run),
            'driver_sha256': hashes, 'tasks': tasks}
    (run / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    print(f'Prepared {len(tasks)} tasks in {run}/plan.json. No plots run; no jobs submitted.')
    print('Review selected.mapping.txt, then run run_small_quickplot.csh inside a compute allocation.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.TimeoutExpired) as e:
        sys.exit('ERROR: ' + str(e))
