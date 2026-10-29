#!/usr/bin/env python3
"""HISTORY.rc collection-driven GEOS plotting, using the installed GrADS scripts."""
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

TOKEN = re.compile(r"'([^']*)'")
IDENT = re.compile(r'^[A-Za-z][A-Za-z0-9_.-]*$')
SEASONS = 'JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC DJF MAM JJA SON ANN'.split()


def parse_history(path):
    """Extract collection fields with optional alias and reduction/operation."""
    text = '\n'.join(x.split('#', 1)[0] for x in path.read_text().splitlines())
    m = re.search(r'(?ms)^\s*COLLECTIONS:\s*(.*?)::', text)
    if not m:
        raise ValueError('COLLECTIONS block absent')
    names = TOKEN.findall(m.group(1))
    result = {}
    for name in names:
        if not IDENT.fullmatch(name):
            raise ValueError('Invalid collection: ' + name)
        block = re.search(r'(?ms)^\s*' + re.escape(name) + r'\.fields:\s*(.*?)::', text)
        if not block:
            raise ValueError('Missing ' + name + '.fields')
        # A semicolon in export notation means multiple field names in a record.
        fields = []
        for raw in block.group(1).splitlines():
            parts = TOKEN.findall(raw)
            if not parts:
                continue
            if len(parts) not in (2, 3, 4):
                raise ValueError('Expected export, component[, alias[, operation]] per line: ' + raw.strip())
            export, component = parts[:2]
            alias = parts[2] if len(parts) >= 3 else export
            operation = parts[3] if len(parts) == 4 else None
            for var in export.split(';'):
                if not IDENT.fullmatch(var) or not IDENT.fullmatch(component):
                    raise ValueError('Unsafe variable/component: ' + export + ':' + component)
                fields.append({'export': var, 'component': component,
                               'alias': alias if ';' not in alias else alias.split(';')[export.split(';').index(var)],
                               'operation': operation})
        result[name] = fields
    return result


def choose(data, requested):
    if requested == ['all']:
        names = list(data)
    else:
        names = list(dict.fromkeys(x for group in requested for x in group.split(',')))
    missing = set(names) - set(data)
    if missing:
        raise ValueError('Disabled or unknown collection(s): ' + ', '.join(sorted(missing)))
    return names


def create_tasks(data, names, levels, zonal, comparisons):
    # Resolve duplicates deterministically: prog first, then HISTORY.rc order.
    # Record the preferred owner while keeping output under the requested collection.
    priority = (['geosgcm_prog'] if 'geosgcm_prog' in data else []) + [
        name for name in data if name != 'geosgcm_prog']
    owner = {}
    for col in priority:
        for field in data[col]:
            owner.setdefault((field['export'], field['component']), col)
    tasks = []
    seen = set()
    for col in names:
        for field in data[col]:
            key = (field['export'], field['component'])
            if key in seen:
                continue
            seen.add(key)
            var, comp = key
            actual = owner[key]
            if actual != col:
                print(f'INFO: {var}:{comp} requested via {col}; '
                      f'GEOS getvar priority resolves to {actual}')
            # Keep outputs grouped under requested collection; ownership is explicit.
            common = {'collection': col, 'resolved_collection': actual,
                      'variable': var, 'component': comp,
                      'compare': bool(comparisons)}
            tasks.append(dict(common, kind='map', level=None))
            for lev in levels:
                tasks.append(dict(common, kind='level', level=lev))
            if zonal:
                tasks.append(dict(common, kind='zonal', level=None))
    return tasks


def task_command(task, expid, season, output, geosutil):
    """Use the legacy GEOS scripts that work with GEOS-configured OpenGrADS."""
    var, comp = task['variable'], task['component']
    if task['kind'] == 'zonal':
        script = Path(geosutil) / 'plots/zcmp/progz'
        return f'run {script} {var} {comp} {expid} {output} no_debug {season}'
    script = Path(geosutil) / 'plots/hcmp/hcmp2'
    # hcmp2 always requires a level; 1000 hPa is the legacy default for
    # nominally 2D fields. Explicit --levels override this for level tasks.
    level = task['level'] if task['kind'] == 'level' else '1000'
    return f'run {script} {var} {comp} {level} {expid} {output} no_debug {season}'


def run_task(task, config):
    col, var, comp = task['collection'], task['variable'], task['component']
    tag = f'{var}_{comp}_{task["kind"]}' + (f'_{task["level"]}' if task['level'] else '')
    work = Path(config['out']) / col / tag
    work.mkdir(parents=True, exist_ok=True)
    command = task_command(task, config['expid'], config['season'], str(Path(config['out']) / col), config['geosutil'])
    env = os.environ.copy()
    env.update(GEOSUTIL=config['geosutil'], SOURCE=config['source'], HISTORYRC=config['history'],
               CMPEXP=' '.join(p + ':M' for p in config['compare']) + ' NULL',
               CMPEXP_ONLY='FALSE', CLIM='false', TAYLOR='false', STD_DEV='false',
               TBEG=config['begdate'], TEND=config['enddate'], SEASONS=config['season'],
               LONSENV='0 360', LATSENV='-90 90', CINTDIFF='ON',
               PLOTS_DIR=str(Path(config['out']) / col), GRADSX=config['gradsx'], DDFFILE='NULL')
    launcher = Path(__file__).with_name('run_grads.csh')
    cmd = ['tcsh', '-f', str(launcher), config['geosutil'], config['source'], config['history'], config['gradsx'], command]
    existing_graphics = {p.resolve() for p in (Path(config['out']) / col).glob('*.gif')}
    t0 = time.monotonic()
    try:
        with (work / 'run.log').open('w') as log:
            result = subprocess.run(cmd, cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT,
                                    timeout=config['timeout'])
        state = 'ok' if result.returncode == 0 else 'failed'
        # GrADS frequently returns zero even after a script/interpreter error.
        logtext = (work / 'run.log').read_text(errors='replace')
        if any(x in logtext for x in ('Undefined variable.', 'Error opening', 'Syntax Error',
                                      'Command not found.', 'ERROR: GrADS executable',
                                      'gadsdf:', 'ga-> [EOF]')):
            state = 'failed'
    except subprocess.TimeoutExpired:
        state = 'timeout'
    # GrADS can exit successfully without rendering a single graphic.
    graphics = [str(p) for p in (Path(config['out']) / col).glob('*.gif')
                if p.resolve() not in existing_graphics]
    if state == 'ok' and not graphics:
        state = 'failed'
        with (work / 'run.log').open('a') as log:
            log.write('\\nERROR: no GIF output detected in collection directory\\n')
    logpath = work / 'run.log'
    if state == 'ok' and not config['keep_workdirs']:
        logs = Path(config['out']) / 'logs' / col
        logs.mkdir(parents=True, exist_ok=True)
        saved = logs / (tag + '.log')
        shutil.copy2(logpath, saved)
        shutil.rmtree(work)
        logpath = saved
    return dict(task=task, state=state, graphics=graphics,
                seconds=round(time.monotonic()-t0, 2), log=str(logpath))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--history', type=Path)
    p.add_argument('--collections', nargs='+', action='append', required=True,
                   help='One or more HISTORY.rc collections (space- or comma-delimited), or all')
    p.add_argument('--compare', action='append', type=Path, default=[], help='Comparison experiment directory (repeat)')
    p.add_argument('--season', choices=SEASONS, required=True)
    p.add_argument('--begdate', required=True)
    p.add_argument('--enddate', required=True)
    p.add_argument('--geosutil', type=Path, default=os.environ.get('GEOSUTIL'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--levels', default='', help='Pressure levels, comma-separated; explicit opt-in for 3D fields')
    p.add_argument('--zonal', action='store_true', help='Attempt zonal plots for selected fields')
    p.add_argument('--workers', type=int, default=8)
    p.add_argument('--timeout', type=int, default=1800)
    p.add_argument('--gradsx', default='auto', help='auto uses GEOS configure GRADS')
    p.add_argument('--execute', action='store_true', help='Run the plan rather than only writing it')
    p.add_argument('--keep-workdirs', action='store_true', help='Retain all task working directories')
    a = p.parse_args(argv)
    if a.workers < 1 or a.timeout < 1:
        p.error('workers and timeout must be positive')
    if not a.geosutil or not (a.geosutil / 'plots/configure').exists():
        p.error('Provide --geosutil pointing to an installed GEOS_Util/plots directory')
    source = a.source.resolve()
    if not source.is_dir():
        p.error('Experiment source directory missing')
    homdir = Path((source/'.HOMDIR').read_text().strip()) if (source/'.HOMDIR').exists() else source
    rc = (a.history or homdir/'HISTORY.rc').resolve()
    data = parse_history(rc)
    groups = [v for group in a.collections for v in group]
    names = choose(data, groups)
    for path in a.compare:
        if not (path/'HISTORY.rc').exists() and not (path/'.HOMDIR').exists():
            p.error('Comparison experiment lacks HISTORY.rc/.HOMDIR: ' + str(path))
    expmatch = re.search(r'(?m)^\s*EXPID:\s*(\S+)', rc.read_text())
    if not expmatch or not IDENT.fullmatch(expmatch.group(1)):
        p.error('Valid EXPID missing from HISTORY.rc')
    levels = [s.strip() for s in a.levels.split(',') if s.strip()]
    if any(not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', x) for x in levels):
        p.error('Pressure levels must be positive numbers')
    tasks = create_tasks(data, names, levels, a.zonal, a.compare)
    for script_name in ('plots/hcmp/hcmp2', 'plots/zcmp/progz'):
        if not (a.geosutil / script_name).is_file():
            p.error('Required GEOS plotting script missing: ' + script_name)
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    # Use the unmodified GEOS plotting scripts and configured GrADS runtime.
    config = {'out': str(out), 'source': str(source), 'history': str(rc),
              'geosutil': str(a.geosutil.resolve()), 'expid': expmatch.group(1),
              'season': a.season, 'begdate': a.begdate, 'enddate': a.enddate,
              'compare': [str(x.resolve()) for x in a.compare], 'gradsx': a.gradsx,
              'timeout': a.timeout, 'keep_workdirs': a.keep_workdirs}
    (out/'plan.json').write_text(json.dumps({'config': config, 'collections': names, 'tasks': tasks}, indent=2))
    print(f'Planned {len(tasks)} plots for {len(names)} collections: {", ".join(names)}')
    if not a.execute:
        print('Dry run. Add --execute inside a compute allocation.')
        return 0
    # Smoke test one task before launching the entire collection. Avoid flooding
    # the filesystem with repeated GEOS setup artifacts if initialization fails.
    first = run_task(tasks[0], config) if tasks else None
    results = [first] if first else []
    if first and first['state'] != 'ok':
        (out/'summary.json').write_text(json.dumps(results, indent=2))
        print('STOP: first task failed; inspect ' + first['log'])
        return 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        results.extend(pool.map(lambda task: run_task(task, config), tasks[1:]))
    (out/'summary.json').write_text(json.dumps(results, indent=2))
    failures = sum(x['state'] != 'ok' for x in results)
    print(f'{len(results) - failures}/{len(results)} tasks produced new GIFs without detected errors.')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
