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

try:
    from netCDF4 import Dataset
except ImportError:
    Dataset = None

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


def classify_fields(source, data, names):
    """Inspect a representative collection file; never infer vertical structure from HISTORY.rc."""
    if Dataset is None:
        raise RuntimeError('netCDF4 is required to classify 2D/3D fields')
    dimensions = {}
    for col in names:
        folder = source / col
        samples = sorted(p for suffix in ('*.nc4', '*.nc', '*.h5')
                         for p in folder.glob(suffix) if p.is_file())
        if not samples:
            raise RuntimeError(f'No NetCDF samples found in {folder}; cannot classify fields')
        unresolved = {(f['export'], f['component']): f['alias']
                      for f in data[col]}
        for file in samples[:8]:
            if not unresolved:
                break
            try:
                with Dataset(file) as nc:
                    for key, alias in list(unresolved.items()):
                        if alias not in nc.variables:
                            continue
                        dims = nc.variables[alias].dimensions
                        # Time, lat, lon plus an optional vertical dimension.
                        spatial = [d for d in dims if not any(
                            marker in d.lower() for marker in ('time', 'lon', 'lat', 'xdim', 'ydim'))]
                        ndim = len(dims)
                        if ndim == 3:
                            dimensions[(col, *key)] = '2d'
                        elif ndim == 4:
                            dimensions[(col, *key)] = '3d'
                        else:
                            dimensions[(col, *key)] = 'unsupported'
                        del unresolved[key]
            except OSError:
                continue
        for key in unresolved:
            dimensions[(col, *key)] = 'unknown'
    return dimensions


def create_tasks(data, names, levels, zonal, comparisons, dimensions, include_2d=False):
    priority = (['geosgcm_prog'] if 'geosgcm_prog' in data else []) + [
        name for name in data if name != 'geosgcm_prog']
    owner = {}
    for col in priority:
        for field in data[col]:
            owner.setdefault((field['export'], field['component']), col)
    tasks = []
    seen = set()
    skipped = []
    for col in names:
        for field in data[col]:
            key = (field['export'], field['component'])
            if key in seen:
                continue
            seen.add(key)
            actual = owner[key]
            if actual != col:
                print(f'INFO: {key[0]}:{key[1]} requested via {col}; '
                      f'GEOS getvar priority resolves to {actual}')
            kind = dimensions.get((actual, *key), dimensions.get((col, *key), 'unknown'))
            common = {'collection': col, 'resolved_collection': actual,
                      'variable': key[0], 'component': key[1],
                      'compare': bool(comparisons), 'dimension': kind}
            if kind == '3d':
                for lev in levels:
                    tasks.append(dict(common, kind='level', level=lev))
                if zonal:
                    tasks.append(dict(common, kind='zonal', level=None))
            elif kind == '2d' and include_2d:
                tasks.append(dict(common, kind='map', level=None))
            else:
                skipped.append(dict(common, reason='2D excluded' if kind == '2d' else 'unknown/unsupported dimensions'))
    return tasks, skipped


def task_command(task, expid, season, output, geosutil):
    """Use the legacy GEOS scripts that work with GEOS-configured OpenGrADS."""
    var, comp = task['variable'], task['component']
    if task['kind'] == 'zonal':
        script = Path(geosutil) / 'plots/zcmp/progz'
        return f'run {script} {var} {comp} {expid} {output} no_debug {season}'
    level = task['level'] if task['kind'] == 'level' else 'surface'
    # hcmp2 requires a matching verification/comparison variable. Without an
    # explicit comparison use the model-only map driver instead.
    if not task['compare']:
        script = Path(__file__).with_name('model_map.gs')
        return f'run {script} {var} {comp} {level} {expid} {output} {season}'
    script = Path(geosutil) / 'plots/hcmp/hcmp2'
    return f'run {script} {var} {comp} {level} {expid} {output} no_debug {season}'


def run_task(task, config):
    col, var, comp = task['collection'], task['variable'], task['component']
    tag = f'{col}_{var}_{comp}_{task["kind"]}' + (f'_{task["level"]}' if task['level'] else '')
    work = Path(config['out']) / 'work' / tag
    images = work / 'images'
    images.mkdir(parents=True, exist_ok=True)
    command = task_command(task, config['expid'], config['season'], str(images), config['geosutil'])
    env = os.environ.copy()
    env.update(GEOSUTIL=config['geosutil'], SOURCE=config['source'], HISTORYRC=config['history'],
               CMPEXP=' '.join(p + ':M' for p in config['compare']) + ' NULL',
               CMPEXP_ONLY='FALSE', CLIM='false', TAYLOR='false', STD_DEV='false',
               TBEG=config['begdate'], TEND=config['enddate'], SEASONS=config['season'],
               LONSENV='0 360', LATSENV='-90 90', CINTDIFF='ON',
               PLOTS_DIR=str(images), GRADSX=config['gradsx'], DDFFILE='NULL')
    launcher = Path(__file__).with_name('run_grads.csh')
    cmd = ['tcsh', '-f', str(launcher), config['geosutil'], config['source'],
           config['history'], config['gradsx'], command]
    t0 = time.monotonic()
    state = 'ok'
    try:
        with (work / 'run.log').open('w') as log:
            result = subprocess.run(cmd, cwd=work, env=env, stdout=log,
                                    stderr=subprocess.STDOUT, timeout=config['timeout'])
        state = 'ok' if result.returncode == 0 else 'failed'
        logtext = (work / 'run.log').read_text(errors='replace')
        if any(x in logtext for x in ('Undefined variable.', 'Error opening', 'Syntax Error',
                                      'Command not found.', 'ERROR: GrADS executable',
                                      'gadsdf:', 'Request is completely outside file limits',
                                      'Cannot contour grid - all undefined values',
                                      'SET Error:', 'DEFINE error:', 'ERROR:')):
            state = 'failed'
    except subprocess.TimeoutExpired:
        state = 'timeout'
    found = sorted(p for suffix in ('*.gif', '*.png')
                   for p in images.rglob(suffix) if p.is_file() and p.stat().st_size > 0)
    graphics = []
    if state == 'ok' and not found:
        state = 'failed'
        with (work / 'run.log').open('a') as log:
            log.write('\\nERROR: no GIF/PNG produced by task\\n')
    if state == 'ok':
        dest = Path(config['out']) / 'plots'
        dest.mkdir(exist_ok=True)
        for idx, image in enumerate(found):
            # Keep additional GEOS panels without overwriting any other task.
            postfix = f'_{idx+1}' if len(found) > 1 else ''
            target = dest / f'{tag}_{config["season"]}{postfix}{image.suffix.lower()}'
            shutil.move(str(image), str(target))
            graphics.append(str(target))
    logpath = work / 'run.log'
    logs = Path(config['out']) / 'logs'
    logs.mkdir(exist_ok=True)
    saved = logs / (tag + '.log')
    shutil.copy2(logpath, saved)
    logpath = saved
    if not config['keep_workdirs']:
        shutil.rmtree(work)
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
    p.add_argument('--levels', default='850,500,250', help='Pressure levels for 3D fields (default: 850,500,250)')
    p.add_argument('--no-zonal', action='store_true', help='Disable zonal mean plots for 3D fields')
    p.add_argument('--include-2d', action='store_true', help='Also plot horizontal 2D fields')
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
    try:
        dimensions = classify_fields(source, data, names)
    except RuntimeError as exc:
        p.error(str(exc))
    tasks, skipped = create_tasks(data, names, levels, not a.no_zonal,
                                  a.compare, dimensions, a.include_2d)
    for script_name in ('plots/hcmp/hcmp2', 'plots/zcmp/progz'):
        if not (a.geosutil / script_name).is_file():
            p.error('Required GEOS plotting script missing: ' + script_name)
    out = a.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    (out / 'plots').mkdir()
    (out / 'logs').mkdir()
    # Use the unmodified GEOS plotting scripts and configured GrADS runtime.
    config = {'out': str(out), 'source': str(source), 'history': str(rc),
              'geosutil': str(a.geosutil.resolve()), 'expid': expmatch.group(1),
              'season': a.season, 'begdate': a.begdate, 'enddate': a.enddate,
              'compare': [str(x.resolve()) for x in a.compare], 'gradsx': a.gradsx,
              'timeout': a.timeout, 'keep_workdirs': a.keep_workdirs}
    (out/'plan.json').write_text(json.dumps({'config': config, 'collections': names, 'tasks': tasks, 'skipped': skipped}, indent=2))
    print(f'Planned {len(tasks)} plots; skipped {len(skipped)} fields for {len(names)} collections: {", ".join(names)}')
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
    print(f'{len(results) - failures}/{len(results)} tasks produced new graphics without detected errors.')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
