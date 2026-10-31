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


# Discrete blue/green/yellow/red progression used by the familiar GEOS plots.
from matplotlib.colors import LinearSegmentedColormap
GEOS = LinearSegmentedColormap.from_list('geos',
    ['#4430b5','#168bb8','#50bbef','#b6f4f5','#20c52b','#88ed72',
     '#c3f8ac','#ffffc0','#ffdb55','#ffa000','#ff4b00','#bc0000'])
DIFF = LinearSegmentedColormap.from_list('geos_difference',
    ['#3000a0','#7160dc','#38b8ef','#25d33c','#b2f7a0','#ffffff',
     '#fff6ac','#ffd34b','#ff9500','#ff3500','#b00000'])


def lonlabel(v,pos=None):
    v=v%360
    if abs(v)<1e-8: return '0'
    if v==180: return '180'
    return f'{v:g}E' if v<180 else f'{360-v:g}W'


def map_field(a):
    a=a.assign_coords(lon=a.lon%360).sortby('lon')
    lon=a.lon.values
    if len(lon)>1:
        gaps=np.diff(np.r_[lon,lon[0]+360])
        if gaps.max()<2.5*np.median(gaps):
            import xarray as xr
            a=xr.concat([a,a.isel(lon=[0]).assign_coords(lon=[float(lon[0])+360])],dim='lon')
    return a


def panels(arrays,labels,title,path,section=False,precip=False,coastlines=None):
    count=len(arrays); comparison=count==3
    if coastlines is None:
        try:
            import cartopy
            cached=Path(cartopy.config['data_dir'])/'shapefiles/natural_earth/physical/ne_110m_coastline.shp'
            if cached.is_file(): coastlines=cached
        except ImportError:
            pass
    fig=plt.figure(figsize=(8,10.5) if comparison else (10,7 if section else 5))
    shared=levels(arrays[:2],precip=precip)
    # Display cloud condensate in mg/kg without modifying saved scientific fields.
    factor=1.; units=arrays[0].attrs.get('units','')
    if any(k in title.upper() for k in ('QL:', 'QI:', 'CLDLIQ', 'CLDICE')) and units.replace(' ','') in ('kgkg-1','kg/kg'):
        factor=1e6; units='mg/kg'; shared=shared*factor
    try:
        axes=[]; images=[]
        for i,(original,label) in enumerate(zip(arrays,labels)):
            ax=fig.add_axes([.18,.70-i*.30,.65,.245] if comparison else [.13,.18,.82,.68])
            axes.append(ax)
            diff=comparison and i==2
            a=original*factor
            levs=levels([a],True) if diff else shared
            if not section: a=map_field(a)
            x='lat' if section else 'lon'; y='lev' if section else 'lat'
            a=a.transpose(y,x)
            im=ax.contourf(a[x],a[y],a.values,levels=levs,cmap=DIFF if diff else GEOS,extend='both')
            images.append(im)
            if section and np.nanmax(a.values)>np.nanmin(a.values):
                ax.contour(a[x],a[y],a.values,levels=levs,colors='k',linewidths=.45)
            ax.set_title('Difference (Top − Middle)' if diff else label,fontsize=10,pad=5)
            ax.tick_params(labelsize=8,pad=2)
            if section:
                ax.set_yscale('linear'); ax.set_ylim(float(a.lev.max()),float(a.lev.min()))
                ticks=np.arange(100,1001,100)
                ax.set_yticks(ticks[(ticks>=float(a.lev.min())) & (ticks<=float(a.lev.max()))])
                ax.set_ylabel('Pressure (hPa)',fontsize=11)
                ax.set_xlim(-90,90); ax.set_xticks(np.arange(-90,91,30))
                ax.xaxis.set_major_formatter(FuncFormatter(latlabel))
                ax.grid(color='.65',linestyle=(0,(1,5)),linewidth=.7)
            else:
                ax.set_xlim(0,360); ax.set_ylim(-90,90)
                ax.set_xticks(np.arange(0,361,60)); ax.set_yticks(np.arange(-90,91,30))
                ax.xaxis.set_major_formatter(FuncFormatter(lonlabel)); ax.yaxis.set_major_formatter(FuncFormatter(latlabel))
                if coastlines:
                    import cartopy.io.shapereader as shp
                    for geometry in shp.Reader(str(coastlines)).geometries():
                        for line in getattr(geometry,'geoms',[geometry]):
                            xy=np.asarray(line.coords); xx=xy[:,0]%360
                            breaks=np.flatnonzero(np.abs(np.diff(xx))>180)+1
                            for ids in np.split(np.arange(len(xx)),breaks):
                                ax.plot(xx[ids],xy[ids,1],color='k',linewidth=.6)
            for spine in ax.spines.values(): spine.set_linewidth(1.1)
            if comparison:
                values=np.asarray(original.values)*factor; finite=values[np.isfinite(values)]
                if len(finite):
                    # Explicitly identify cell statistics; spatial bias/RMSE remain area weighted in summary.json.
                    stats=f'Max: {finite.max():.5g}\nMin: {finite.min():.5g}\n\nCell mean: {finite.mean():.5g}\nCell std: {finite.std():.5g}'
                    fig.text(.012,.875-i*.30,stats,fontsize=5.8 if section else 6.8,va='top')
        if comparison:
            cax=fig.add_axes([.88,.405,.025,.49])
            cb=fig.colorbar(images[0],cax=cax,orientation='vertical',drawedges=True)
            cb.ax.tick_params(labelsize=8); cb.set_label(units,fontsize=9)
            cax=fig.add_axes([.14,.055,.73,.019])
            cb=fig.colorbar(images[-1],cax=cax,orientation='horizontal',drawedges=True)
        else:
            cax=fig.add_axes([.14,.105,.80,.025])
            cb=fig.colorbar(images[0],cax=cax,orientation='horizontal',drawedges=True)
        cb.ax.tick_params(labelsize=7)
        cb.formatter=ScalarFormatter(useMathText=True); cb.formatter.set_powerlimits((-3,4)); cb.update_ticks()
        if not comparison: cb.set_label(units,fontsize=9)
        fig.suptitle(title,fontsize=11,y=.985,wrap=True)
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
    fig,axes=plt.subplots(2,2,figsize=(8,10),layout='constrained')
    try:
        for index,(label,values) in enumerate(series):
            olr,olc,rsr,rsc=[zonal(a) for a in values]
            color='blue' if index==0 else 'black' if index==1 else f'C{index}'
            axes[0,0].plot(olr.lat,olr,label=label+' all',color=color,linewidth=1)
            axes[0,0].plot(olc.lat,olc,'--',color=color,label=label+' clear')
            axes[0,1].plot(olr.lat,olc-olr,color=color,label=label)
            axes[1,0].plot(rsr.lat,rsr,color=color,label=label+' all'); axes[1,0].plot(rsc.lat,rsc,'--',color=color,label=label+' clear')
            # Native toa_radz displays positive shortwave cloud forcing: clear minus all.
            axes[1,1].plot(rsr.lat,rsc-rsr,color=color,label=label)
        for ax,name in zip(axes.flat,['Outgoing Longwave Radiation','TOA LW Cloud Forcing (clear − all)','Net TOA Shortwave Radiation','TOA SW Cloud Forcing (clear − all)']):
            ax.set_title(name); ax.set_ylabel('W m$^{-2}$'); ax.set_xlabel('Latitude'); ax.xaxis.set_major_formatter(FuncFormatter(latlabel)); ax.set_xlim(-90,90); ax.set_xticks(np.arange(-90,91,30)); ax.grid(alpha=.5,linestyle=':'); ax.legend(fontsize=7,loc='upper center',bbox_to_anchor=(.5,-.18))
        fig.suptitle(title); fig.savefig(path,dpi=150)
    finally: plt.close(fig)
