#!/usr/bin/env python3
"""Run a prepared plan in a compute allocation; never submit scheduler jobs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def positive(value):
    number = int(value)
    if number < 1: raise argparse.ArgumentTypeError('Must be positive')
    return number


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan', type=Path)
    p.add_argument('--workers', type=positive, default=1)
    p.add_argument('--timeout', type=positive, default=1800, help='Seconds per task (default 1800)')
    p.add_argument('--resume', action='store_true', help='Skip tasks previously recorded returned_zero; retry others')
    a = p.parse_args()
    plan = json.loads(a.plan.read_text())
    if plan.get('version') != 1: raise ValueError('Unknown plan version')
    run = Path(plan['run_dir'])
    geosutil = Path(plan['geosutil'])
    for name, expected in plan['driver_sha256'].items():
        if hashlib.sha256((geosutil / 'plots' / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Plot driver changed; prepare a new plan: ' + name)
    lock = run / '.runner-lock'
    lock.mkdir()  # Atomic exclusion of a second runner; do not touch somebody else's lock.
    try:
        logs = run / 'logs'
        logs.mkdir(exist_ok=True)
        for task in plan['tasks']:
            if (logs / (task['id'] + '.json')).exists() and not a.resume:
                raise ValueError('Prior task records exist; use --resume or prepare a new run directory')
        env = os.environ.copy()
        env.update(GEOSUTIL=str(geosutil), CMPEXP_ONLY='FALSE', CMPOPS_ONLY='FALSE',
                   STD_DEV='false', DO_STD='FALSE')

        def execute(task):
            ident = task['id']
            record = logs / (ident + '.json')
            if a.resume and record.exists():
                previous = json.loads(record.read_text())
                if previous.get('state') == 'returned_zero':
                    print('SKIP ' + ident, flush=True)
                    return previous
            work = run / 'work' / ident
            work.mkdir(parents=True, exist_ok=True)
            started = time.monotonic()
            state, code = 'failed', None
            print('START ' + ident, flush=True)
            with (logs / (ident + '.log')).open('a') as log:
                log.write('\n=== attempt ' + time.strftime('%Y-%m-%dT%H:%M:%S%z') + ' ===\n')
                log.flush()
                try:
                    proc = subprocess.Popen([str(geosutil / 'plots/quickplot')] + task['args'],
                                            cwd=work, env=env, stdout=log, stderr=subprocess.STDOUT,
                                            start_new_session=True)
                    try:
                        code = proc.wait(timeout=a.timeout)
                        state = 'returned_zero' if code == 0 else 'failed'
                    except subprocess.TimeoutExpired:
                        state = 'timeout'
                        os.killpg(proc.pid, signal.SIGTERM)
                        try: proc.wait(timeout=5)
                        except subprocess.TimeoutExpired: pass
                        # Also stop descendants if the parent exited after SIGTERM.
                        try: os.killpg(proc.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                        proc.wait()
                except OSError as e:
                    log.write(str(e) + '\n')
            result = {'id': ident, 'state': state, 'returncode': code,
                      'elapsed_seconds': round(time.monotonic() - started, 2)}
            temporary = record.with_suffix('.tmp')
            temporary.write_text(json.dumps(result, indent=2) + '\n')
            temporary.replace(record)
            print(state.upper() + ' ' + ident, flush=True)
            return result

        with ThreadPoolExecutor(max_workers=a.workers) as pool:
            results = list(pool.map(execute, plan['tasks']))
        (run / 'summary.json').write_text(json.dumps(results, indent=2) + '\n')
        failed = sum(r['state'] != 'returned_zero' for r in results)
        print(f'{len(results) - failed}/{len(results)} tasks returned zero; {failed} failed/timed out.')
        print('Upstream QuickPlot can mask rendering errors; inspect logs and plots before accepting results.')
        return 1 if failed else 0
    finally:
        lock.rmdir()


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError) as e:
        sys.exit('ERROR: ' + str(e))
