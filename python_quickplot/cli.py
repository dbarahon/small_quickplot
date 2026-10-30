"""Run with python -m python_quickplot from the repository root."""
import argparse
import json
import os
from pathlib import Path
import re
import traceback
import numpy as np
import xarray as xr
from .data import Experiment, SEASONS, mean, paired, regrid, zonal, metrics
from .diagnostics import RECIPES, RADIATION, calculate, compatible, supports
from .verification import catalog
from .render import panels, precip_profile, radiation


def slug(text): return re.sub(r'[^A-Za-z0-9_.-]+','_',str(text))


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True); p.add_argument('--history',type=Path)
    p.add_argument('--collections',nargs='+',required=True)
    p.add_argument('--compare',type=Path,action='append',default=[])
    p.add_argument('--season',choices=SEASONS,default='ANN'); p.add_argument('--begdate',required=True); p.add_argument('--enddate',required=True)
    p.add_argument('--levels',default='850,500,250'); p.add_argument('--variables',nargs='+',help='Exports, EXPORT:COMPONENT, or derived names')
    p.add_argument('--no-zonal',action='store_true'); p.add_argument('--no-verification',action='store_true')
    p.add_argument('--geosutil',type=Path,default=os.environ.get('GEOSUTIL'))
    p.add_argument('--verification-dir',type=Path); p.add_argument('--verification-root',type=Path)
    p.add_argument('--verification-rc',type=Path,action='append',default=[],help='Additional MERRA-2/ERA5 resource files only')
    p.add_argument('--config',type=Path,help='JSON file_patterns and verification overrides')
    p.add_argument('--climatology',action='store_true',help='Compare common calendar months across different years')
    p.add_argument('--compare-begdate'); p.add_argument('--compare-enddate')
    p.add_argument('--obs-begdate'); p.add_argument('--obs-enddate')
    p.add_argument('--coastlines',type=Path,help='Offline Natural Earth line shapefile (requires Cartopy)')
    p.add_argument('--save-fields',action='store_true'); p.add_argument('--output',type=Path,required=True)
    p.add_argument('--execute',action='store_true'); return p


def main(argv=None):
    p=parser(); a=p.parse_args(argv)
    for date in (a.begdate,a.enddate,a.obs_begdate,a.obs_enddate,a.compare_begdate,a.compare_enddate):
        if date and (not re.fullmatch(r'\d{6}',date) or not 1<=int(date[-2:])<=12): p.error('Dates must be YYYYMM')
    if a.begdate>a.enddate: p.error('begdate must not exceed enddate')
    levels=[float(x) for x in a.levels.split(',')]
    if any(not np.isfinite(x) or x<=0 for x in levels): p.error('Levels must be positive hPa')
    cfg=json.loads(a.config.read_text()) if a.config else {}
    model=Experiment(a.source,a.begdate,a.enddate,a.season,a.history,cfg.get('file_patterns'))
    names=list(model.fields) if a.collections==['all'] else [v for group in a.collections for v in group.split(',')]
    if set(names)-model.fields.keys(): p.error('Unknown collection(s): '+str(set(names)-model.fields.keys()))
    refs=[Experiment(path,a.compare_begdate or a.begdate,a.compare_enddate or a.enddate,a.season,patterns=cfg.get('file_patterns')) for path in a.compare]
    folder=a.verification_dir or (a.geosutil/'plots/VERIFICATION_RCS' if a.geosutil else None)
    root=a.verification_root or (a.geosutil/'plots/VERIFICATION' if a.geosutil else Path('VERIFICATION'))
    if not a.no_verification:
        if not folder or not folder.is_dir(): p.error('Provide --verification-dir or --geosutil, or explicitly --no-verification')
        refs+=catalog(folder,root,(a.obs_begdate or a.begdate,a.obs_enddate or a.enddate,a.season),cfg.get('verification'),a.verification_rc)
    labels=[r.name for r in refs]
    configured={r.name for r in refs if hasattr(r,'entries')}
    if not a.no_verification:
        for dataset in ('MERRA-2','ERA5'):
            if dataset not in configured and not (dataset=='MERRA-2' and 'MERRA2' in configured):
                print(f'NOTICE: {dataset} not configured; provide --verification-rc or a manifest mapping')
    if len(set(labels))!=len(labels): p.error('Comparison source names must be distinct')
    tasks=[]
    for col in names:
        selected={(f['export'],f['component']) for f in model.fields[col]}
        for f in model.fields[col]: tasks.append((col,(f['export'],f['component'])))
        for name,keys in RECIPES.items():
            if selected.intersection(keys) or (name=='precip' and ('TPREC','MOIST') in selected): tasks.append((col,name))
        if selected.intersection(RADIATION): tasks.append((col,'toa_radz'))
    if a.variables:
        tasks=[(c,k) for c,k in tasks if (k if isinstance(k,str) else k[0]) in a.variables or (':'.join(k) if isinstance(k,tuple) else k) in a.variables]
    tasks=list(dict.fromkeys(tasks))
    if not tasks: p.error('No tasks selected')
    a.output.mkdir(parents=True,exist_ok=False); plots=a.output/'plots'; plots.mkdir(); logs=a.output/'logs'; logs.mkdir()
    plan=dict(options={k:str(v) if isinstance(v,Path) else [str(x) for x in v] if isinstance(v,list) else v for k,v in vars(a).items()},
              tasks=tasks,comparison_sources=labels,verification_catalog=str(folder),averaging='equal monthly means; equal samples within month',regridding='bilinear reference to model, no extrapolation, nonconservative')
    (a.output/'plan.json').write_text(json.dumps(plan,indent=2))
    print(f'Planned {len(tasks)} diagnostics; reference sources: {", ".join(labels) or "none"}')
    if not a.execute: print('Dry run; add --execute'); return 0
    results=[]
    def save_summary():
        (a.output/'summary.json').write_text(json.dumps(dict(results=results,provenance={r.name:r.provenance for r in [model]+refs}),indent=2,default=str))
    def record_error(tag,exc,state='failed'):
        (logs/(tag+'.log')).write_text(traceback.format_exc())
        results.append(dict(task=tag,state=state,reason=str(exc))); save_summary()
    for col,key in tasks:
        label=':'.join(key) if isinstance(key,tuple) else key; tag=slug(col+'_'+label)
        try:
            if key=='toa_radz':
                base=xr.align(*(calculate(model,k,col) for k in RADIATION),join='exact')
                series=[(model.name,[mean(x) for x in base])]
                # Each reference gets a separate figure with its own common time window.
                radiation(series,plots/(tag+'.png'),f'{model.name} {a.season} {a.begdate}–{a.enddate}')
                results.append(dict(task=tag,state='ok'))
                for ref in refs:
                    if not supports(ref,key): continue
                    rtag=tag+'_vs_'+slug(ref.name)
                    try:
                        other=xr.align(*(calculate(ref,k,col) for k in RADIATION),join='exact')
                        left=[]; right=[]; common=None
                        for x,y in zip(base,other):
                            x,y,months=paired(x,compatible(x,y),a.climatology); common=months
                            left.append(mean(x)); right.append(mean(y))
                        radiation([(model.name,left),(ref.name,right)],plots/(rtag+'.png'),f'TOA radiation {a.season}; {len(common)} common months')
                        results.append(dict(task=rtag,state='ok',months=common))
                    except Exception as exc: record_error(rtag,exc,'unavailable')
                continue
            raw=calculate(model,key,col); field=mean(raw)
            modes=[('map',None)] if 'lev' not in field.dims else [('level',v) for v in levels]+([] if a.no_zonal else [('zonal',None)])
            def product(x,kind,level):
                if kind=='level':
                    if level<float(x.lev.min()) or level>float(x.lev.max()): raise ValueError(f'{level} hPa outside pressure range')
                    return x.interp(lev=level).drop_vars('lev',errors='ignore')
                return zonal(x) if kind=='zonal' else x
            for kind,level in modes:
                ptag=tag+'_'+kind+(f'_{level:g}hPa' if level else '')
                try:
                    v=product(field,kind,level)
                    panels([v],[model.name],f'{label} {str(level)+" hPa" if level else kind}  {a.season}  {a.begdate}–{a.enddate}  n={raw.sizes["time"]}',plots/(ptag+'.png'),section=kind=='zonal',precip=key=='precip',coastlines=a.coastlines)
                    results.append(dict(task=ptag,state='ok',samples=raw.sizes['time']))
                    if a.save_fields: v.to_dataset(name='model').to_netcdf(a.output/(ptag+'.nc'))
                except Exception as exc: record_error(ptag,exc); continue
                for ref in refs:
                    if not supports(ref,key): continue
                    rtag=ptag+'_vs_'+slug(ref.name)
                    try:
                        rr=calculate(ref,key,col); rr=compatible(raw,rr)
                        left,right,months=paired(raw,rr,a.climatology)
                        lm,rm=mean(left),mean(right)
                        if kind=='zonal':
                            rm=regrid(rm,lm).interp(lev=lm.lev); lv,rv=zonal(lm),zonal(rm)
                        else:
                            lv=product(lm,kind,level); rv=regrid(product(rm,kind,level),lv)
                        lv,rv=xr.align(lv,rv,join='exact'); delta=lv-rv; delta.attrs=lv.attrs.copy()
                        stat=metrics(lv,rv) if kind!='zonal' else None
                        panels([lv,rv,delta],[model.name,ref.name,'Model − reference'],f'{label} {str(level)+" hPa" if level else kind} {a.season}; {len(months)} common months',plots/(rtag+'.png'),section=kind=='zonal',precip=key=='precip',coastlines=a.coastlines)
                        results.append(dict(task=rtag,state='ok',months=months,metrics=stat))
                        if a.save_fields: xr.Dataset(dict(model=lv,reference=rv,difference=delta)).to_netcdf(a.output/(rtag+'.nc'))
                        if key=='precip': precip_profile([(model.name,lv),(ref.name,rv)],plots/(rtag+'_profile.png'),f'Precipitation {a.season}')
                    except Exception as exc: record_error(rtag,exc,'unavailable')
            if key=='precip': precip_profile([(model.name,field)],plots/(tag+'_profile.png'),f'Precipitation {a.season}')
        except Exception as exc: record_error(tag,exc)
        finally:
            # Bound RAM across diagnostics; file inventories remain cached.
            model.cache.clear()
            for ref in refs: ref.cache.clear()
            save_summary()
    failed=sum(r['state']=='failed' for r in results); unavailable=sum(r['state']=='unavailable' for r in results)
    print(f'{len(results)-failed-unavailable} successful products, {failed} failed, {unavailable} unavailable comparisons. See summary.json.')
    return 1 if failed or unavailable else 0
