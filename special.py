"""GEOS lcmp vertical/latitude profiles and zcmp1 QBO/vortex diagnostics."""
import copy
import re
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter
from matplotlib.lines import Line2D
import render
from data import zonal, mean, paired
from verification import comparison_climatology
from diagnostics import calculate, compatible, supports

PROFILES={('T','DYN'):(-85,0,85),('U','DYN'):(-30,0,30),
          ('V','DYN'):(-30,0,30),('RH2','MOIST'):(-85,0,85),('Q','MOIST'):(-60,0,60)}
LEVELS={'T':(100,850),'U':(200,850),'V':(200,850),'RH2':(500,925),'Q':(500,925)}


def pressure(ax,low,high,log=True):
    ax.set_yscale('log' if log else 'linear'); ax.set_ylim(high,low)
    ticks=np.array([.1,.2,.4,1,2,3,5,7,10,20,30,50,70,100,200,300,500,700,1000]) if log else np.arange(100,1001,100)
    ax.set_yticks(ticks[(ticks>=low)&(ticks<=high)])
    ax.yaxis.set_major_formatter(ScalarFormatter()); ax.set_ylabel('Pressure (hPa)'); ax.grid(linestyle=':',alpha=.5)


def profiles(series,key,path,title):
    fig,axes=plt.subplots(1,3,figsize=(12,8),layout='constrained')
    try:
        for ax,lat in zip(axes,PROFILES[key]):
            lows=[]; highs=[]
            for label,a in series:
                z=zonal(a).interp(lat=lat)
                if not bool(z.notnull().any()): continue
                ax.plot(z,z.lev,label=label); lows.append(float(z.lev.min())); highs.append(float(z.lev.max()))
            if not lows: raise ValueError(f'No profile data at latitude {lat}')
            pressure(ax,min(lows),max(highs),key[0]=='T')
            ax.set_title(f'Latitude: {lat:g}'); ax.set_xlabel(series[0][1].attrs.get('units','')); ax.legend(fontsize=7)
        render.plot_title(fig,title); fig.savefig(path,dpi=render.DPI)
    finally: plt.close(fig)


def latitude_profiles(series,key,path,title):
    fig,axes=plt.subplots(1,2,figsize=(11,4),layout='constrained')
    try:
        for ax,lev in zip(axes,LEVELS[key[0]]):
            for label,a in series:
                if float(a.lev.min())<=lev<=float(a.lev.max()):
                    z=zonal(a).interp(lev=lev); ax.plot(z.lat,z,label=label)
            ax.set_title(f'{lev} hPa'); ax.set_xlim(-90,90); ax.grid(linestyle=':'); ax.legend(fontsize=7)
            ax.set_xlabel('Latitude'); ax.set_ylabel(series[0][1].attrs.get('units',''))
        render.plot_title(fig,title); fig.savefig(path,dpi=render.DPI)
    finally: plt.close(fig)


def band(a,lo,hi):
    z=zonal(a).sel(lat=slice(lo,hi))
    if not z.sizes['lat']: raise ValueError(f'No latitudes within {lo} to {hi}')
    # GrADS ave(...,lat=lo,lat=hi) is latitude-weighted.
    weights=np.cos(np.deg2rad(z.lat))
    return z.weighted(weights).mean('lat',keep_attrs=True)


def full_months(source,key,col):
    source=copy.copy(source); source.cache={}
    source.window=(*source.window[:2],'ANN')
    a=calculate(source,key,col)
    # Reindex actual calendar months so absent seasons remain missing, never bridged.
    return a.resample(time='MS').mean(keep_attrs=True)


def qbo(series,path,title):
    fields=[(label,band(a,-10,10)) for label,a in series]
    fig,axes=plt.subplots(len(fields),1,figsize=(12,3.6*len(fields)),squeeze=False,layout='constrained')
    try:
        for ax,(label,z) in zip(axes[:,0],fields):
            if z.sizes['time']<2 or z.sizes['lev']<2: raise ValueError('QBO needs at least two months and pressure levels')
            im=ax.contourf(z.time,z.lev,z.transpose('lev','time'),levels=np.arange(-36,40,4),cmap=render.DIFF,extend='both')
            ax.contour(z.time,z.lev,z.transpose('lev','time'),levels=[0],colors='k',linewidths=.7)
            pressure(ax,float(z.lev.min()),float(z.lev.max()))
            ticks=np.array([.1,1,10,100,1000])
            ax.set_yticks(ticks[(ticks>=float(z.lev.min())) & (ticks<=float(z.lev.max()))])
            render.plot_title(fig,label,ax); fig.colorbar(im,ax=ax,orientation='horizontal',pad=.08,label='U (m s⁻¹)')
        render.plot_title(fig,title+'; 10S–10N, all available months'); fig.savefig(path,dpi=render.DPI)
    finally: plt.close(fig)


def vortex(series,path,title):
    fig,ax=plt.subplots(figsize=(10,7),layout='constrained')
    try:
        handles=[]
        for index,(label,a) in enumerate(series):
            z=band(a,-70,-50).sel(lev=slice(.1,100))
            if z.sizes['lev']<2: raise ValueError('Vortex needs at least two pressure levels at or above 100 hPa')
            grouped=z.groupby('time.month')
            clim=grouped.mean('time').reindex(month=np.arange(1,13))
            std=grouped.std('time').reindex(month=np.arange(1,13))
            counts=grouped.count('time').reindex(month=np.arange(1,13),fill_value=0)
            months=[9,10,11,12,1,2,3,4]; x=np.arange(8)
            values=clim.sel(month=months).transpose('lev','month')
            if int(values.notnull().any('lev').sum())<2: raise ValueError('Vortex needs at least two available Sep–Apr months; extend launcher dates')
            color='blue' if index==0 else 'red'
            for levs,style in [([-90,-75,-60,-45,-30,-15],'--'),([15,30,45,60,75,90],'-'),([0],'-')]:
                cs=ax.contour(x,values.lev,values,levels=levs,colors=color,linestyles=style,linewidths=1.5 if levs==[0] else .6)
                if levs==[0]: ax.clabel(cs,fontsize=8)
            spread=std.where(counts>=2).sel(month=months).transpose('lev','month')
            for sign in (-1,1):
                if bool(spread.notnull().any()): ax.contour(x,values.lev,values+sign*spread,levels=[0],colors=color,linestyles=':',linewidths=.7)
            handles.append(Line2D([0],[0],color=color,label=label))
        pressure(ax,max(.1,min(float(a.lev.min()) for _,a in series)),100)
        ax.set_xticks(x,['Sep','Oct','Nov','Dec','Jan','Feb','Mar','Apr'])
        ax.legend(handles=handles,fontsize=8); render.plot_title(fig,title+'; 50–70S; monthly clim.',ax)
        ax.text(.01,.01,'Dotted zero contours: ±1 SD (n≥2)',transform=ax.transAxes,fontsize=7)
        fig.savefig(path,dpi=render.DPI)
    finally: plt.close(fig)


def special_products(model,refs,collections,variables,plots,season,results,record_error):
    for col in collections:
        available={(f['export'],f['component']) for f in model.fields[col]}
        for key in PROFILES:
            if key not in available or (variables and key[0] not in variables and ':'.join(key) not in variables): continue
            tag=col+'_'+key[0]+'_prognostics'
            try:
                raw=calculate(model,key,col)
                if 'lev' not in raw.dims: continue
                groups=[(tag,[(model.name,mean(raw))])]
                for ref in refs:
                    if not supports(ref,key): continue
                    rtag=tag+'_vs_'+re.sub(r'[^A-Za-z0-9_.-]','_',ref.name)
                    try:
                        rr=compatible(raw,calculate(ref,key,col))
                        use_clim=comparison_climatology(ref,raw,rr)
                        l,r,months=paired(raw,rr,use_clim)
                        ref_label=ref.name + (f' (climatology {rr.time.dt.year.min().item()}–{rr.time.dt.year.max().item()})' if use_clim else '')
                        groups.append((rtag,[(model.name,mean(l)),(ref_label,mean(r))]))
                    except Exception as exc: record_error(rtag,exc,'unavailable')
                for name,series in groups:
                    title=f'Zonal Mean {key[0]} {season}; {model.window[0]}–{model.window[1]}'
                    for suffix,func in [('vertical',profiles),('latitude',latitude_profiles)]:
                        func(series,key,plots/(name+'_'+suffix+'.png'),title)
                        results.append(dict(task=name+'_'+suffix,state='ok'))
                if key==('U','DYN'):
                    full=full_months(model,key,col)
                    fullgroups=[(tag,[(model.name,full)])]
                    for ref in refs:
                        if not supports(ref,key): continue
                        rtag=tag+'_vs_'+re.sub(r'[^A-Za-z0-9_.-]','_',ref.name)
                        try:
                            rr=compatible(full,full_months(ref,key,col))
                            # Chronological QBO comparisons require common actual dates.
                            common=np.intersect1d(full.time.values,rr.time.values)
                            if len(common)<2: raise ValueError('Time diagnostics require at least two common calendar months')
                            fullgroups.append((rtag,[(model.name,full.sel(time=common)),(ref.name,rr.sel(time=common))]))
                        except Exception as exc: record_error(rtag+'_time',exc,'unavailable')
                    for name,series in fullgroups:
                        for suffix,func in [('qbo',qbo),('vortex',vortex)]:
                            try:
                                func(series,plots/(name+'_'+suffix+'.png'),f'Zonal Mean U {model.window[0]}–{model.window[1]}')
                                results.append(dict(task=name+'_'+suffix,state='ok'))
                            except Exception as exc: record_error(name+'_'+suffix,exc,'unavailable')
            except Exception as exc: record_error(tag,exc)
            finally:
                model.cache.clear()
                for ref in refs: ref.cache.clear()
