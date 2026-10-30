"""Compact scientific maps, pressure sections and dedicated latitude profiles."""
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import ScalarFormatter, FuncFormatter, MaxNLocator, NullFormatter
from .data import zonal


def latlabel(v,pos=None): return 'EQ' if abs(v)<1e-8 else f'{abs(v):g}'+('N' if v>0 else 'S')


def levels(arrays,difference=False,precip=False):
    if precip and not difference: return np.array([0,.1,.5,1,2,3,4,5,6,8,10,12,15,20])
    vals=np.concatenate([a.values[np.isfinite(a.values)] for a in arrays])
    if not len(vals): raise ValueError('All cells undefined')
    lo,hi=float(vals.min()),float(vals.max())
    if difference:
        hi=max(abs(lo),abs(hi),1e-12); return np.linspace(-hi,hi,17)
    if hi==lo: lo-=max(abs(lo)*.01,.01); hi+=max(abs(hi)*.01,.01)
    return MaxNLocator(nbins=18).tick_values(lo,hi)


def panels(arrays,labels,title,path,section=False,precip=False,coastlines=None):
    count=len(arrays); fig,axes=plt.subplots(count,1,figsize=(9,4.8*count if section else 3.8*count),squeeze=False,layout='constrained')
    shared=levels(arrays[:2],precip=precip)
    try:
        for i,(a,label,ax) in enumerate(zip(arrays,labels,axes[:,0])):
            diff=count==3 and i==2
            levs=levels([a],True) if diff else shared
            x='lat' if section else 'lon'; y='lev' if section else 'lat'
            a=a.transpose(y,x)
            im=ax.contourf(a[x],a[y],a.values,levels=levs,cmap='RdBu_r' if diff else 'YlGnBu' if precip else 'Spectral_r',extend='both')
            if np.nanmax(a.values)>np.nanmin(a.values):
                ax.contour(a[x],a[y],a.values,levels=levs[::2],colors='k',linewidths=.35,alpha=.55)
            ax.set_title(label,loc='left',fontsize=10)
            ax.grid(alpha=.25,linewidth=.5)
            if section:
                ax.set_yscale('log'); ax.set_ylim(float(a.lev.max()),float(a.lev.min()))
                ticks=[p for p in (1000,850,700,500,300,200,100,50,20,10,1) if a.lev.min()<=p<=a.lev.max()]
                ax.set_yticks(ticks); ax.yaxis.set_major_formatter(ScalarFormatter()); ax.yaxis.set_minor_formatter(NullFormatter()); ax.set_ylabel('Pressure (hPa)')
                ax.xaxis.set_major_formatter(FuncFormatter(latlabel)); ax.set_xlabel('Latitude')
            else:
                ax.set_xlabel('Longitude'); ax.set_ylabel('Latitude'); ax.yaxis.set_major_formatter(FuncFormatter(latlabel))
                if coastlines:
                    import cartopy.io.shapereader as shp
                    for geometry in shp.Reader(str(coastlines)).geometries():
                        for line in getattr(geometry,'geoms',[geometry]):
                            xy=np.asarray(line.coords); ax.plot(xy[:,0],xy[:,1],color='.2',linewidth=.5)
                    ax.set_xlim(float(a.lon.min()),float(a.lon.max())); ax.set_ylim(float(a.lat.min()),float(a.lat.max()))
            cb=fig.colorbar(im,ax=ax,orientation='horizontal',shrink=.9,pad=.06,aspect=45)
            cb.formatter=ScalarFormatter(useMathText=True); cb.formatter.set_powerlimits((-3,4)); cb.update_ticks()
            cb.set_label(a.attrs.get('units',''),fontsize=9)
        fig.suptitle(title,fontsize=12)
        fig.savefig(path,dpi=150)
    finally: plt.close(fig)


def precip_profile(series,path,title):
    fig,ax=plt.subplots(figsize=(9,4),layout='constrained')
    try:
        for label,a in series: ax.plot(a.lat,zonal(a),label=label)
        ax.set_ylabel('Precipitation (mm/day)'); ax.set_xlabel('Latitude'); ax.xaxis.set_major_formatter(FuncFormatter(latlabel))
        ax.grid(alpha=.25); ax.legend(); ax.set_title(title); fig.savefig(path,dpi=150)
    finally: plt.close(fig)


def radiation(series,path,title):
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    try:
        for label,values in series:
            olr,olc,rsr,rsc=[zonal(a) for a in values]
            line,=axes[0,0].plot(olr.lat,olr,label=label+' all'); color=line.get_color()
            axes[0,0].plot(olc.lat,olc,'--',color=color,label=label+' clear')
            axes[0,1].plot(olr.lat,olc-olr,color=color,label=label)
            axes[1,0].plot(rsr.lat,rsr,color=color,label=label+' all'); axes[1,0].plot(rsc.lat,rsc,'--',color=color,label=label+' clear')
            # Physical SW CRE for net downward SW is all minus clear.
            axes[1,1].plot(rsr.lat,rsr-rsc,color=color,label=label)
        for ax,name in zip(axes.flat,['Outgoing LW','LW CRE: clear − all','Net downward SW','SW CRE: all − clear']):
            ax.set_title(name); ax.set_ylabel('W m$^{-2}$'); ax.set_xlabel('Latitude'); ax.xaxis.set_major_formatter(FuncFormatter(latlabel)); ax.grid(alpha=.25); ax.legend(fontsize=7)
        fig.suptitle(title); fig.savefig(path,dpi=150)
    finally: plt.close(fig)
