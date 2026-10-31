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


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',nargs='+',type=Path); p.add_argument('--destination',required=True,type=Path)
    a=p.parse_args(); print(f'Moved {len(unify(a.runs,a.destination))} plots')
