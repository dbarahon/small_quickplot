"""Move completed PNGs into one directory, preserving run identity and refusing overwrite."""
from pathlib import Path
import shutil


def unify(runs, destination):
    destination=Path(destination).resolve(); destination.mkdir(parents=True,exist_ok=True)
    moved=[]
    for run in runs:
        run=Path(run).resolve()
        folder=run/'plots'
        if folder.resolve()==destination: continue
        for source in sorted(folder.glob('*.png')):
            target=destination/(run.name+'__'+source.name)
            # Exclusive create also protects concurrent collection jobs.
            with target.open('xb') as out:
                try:
                    with source.open('rb') as inp: shutil.copyfileobj(inp,out)
                except BaseException:
                    target.unlink(missing_ok=True)
                    raise
            source.unlink()
            moved.append({'source':str(source),'destination':str(target)})
    return moved


def seasonal_runs(experiment, season):
    """Discover both the existing plot/ layout and the requested plots/ layout."""
    root=Path(experiment)
    return sorted({run.resolve() for parent in (root/'plot',root/'plots')
                   for run in parent.glob('python_'+season+'*') if run.is_dir()})


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',nargs='*',type=Path)
    p.add_argument('--experiment',type=Path); p.add_argument('--season')
    p.add_argument('--destination',required=True,type=Path)
    a=p.parse_args()
    if bool(a.experiment) != bool(a.season): p.error('--experiment and --season must be used together')
    runs=seasonal_runs(a.experiment,a.season) if a.experiment else a.runs
    print(f'Moved {len(unify(runs,a.destination))} plots to {a.destination}')
