"""HISTORY aliases, bounded file reads, coordinate normalization and averaging."""
from pathlib import Path
import re
import numpy as np
import xarray as xr

SEASONS = dict(ANN=list(range(1,13)), DJF=[12,1,2], MAM=[3,4,5], JJA=[6,7,8], SON=[9,10,11])
SEASONS.update({m:[i+1] for i,m in enumerate('JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC'.split())})


def history(path):
    text = '\n'.join(s.split('#',1)[0] for s in Path(path).read_text().splitlines())
    block = re.search(r'(?ms)^\s*COLLECTIONS:\s*(.*?)::', text)
    if not block:
        raise ValueError('Missing COLLECTIONS in ' + str(path))
    result = {}
    for col in re.findall(r"'([^']+)'", block[1]):
        fields = re.search(r'(?ms)^\s*'+re.escape(col)+r'\.fields:\s*(.*?)::', text)
        if not fields:
            continue
        result[col] = []
        for line in fields[1].splitlines():
            p = re.findall(r"'([^']*)'", line)
            if len(p) < 2:
                continue
            exports = p[0].split(';')
            aliases = p[2].split(';') if len(p)>2 else exports
            # A single bundle export may expand to several on-disk fields.
            # Use each alias as its diagnostic identity so task deduplication
            # and caching cannot collapse all members onto the first field.
            source_export = None
            if len(exports) == 1 and len(aliases) > 1:
                source_export = exports[0]
                exports = aliases
            elif len(aliases)!=len(exports):
                raise ValueError('Ambiguous aliases: '+line)
            for v, a in zip(exports, aliases):
                field = dict(export=v, component=p[1], alias=a,
                             operation=p[3] if len(p)>3 else None)
                if source_export is not None:
                    field['source_export'] = source_export
                result[col].append(field)
    return result


def normalize(a):
    ren = {}
    for d in a.dims:
        low = d.lower()
        if low in ('latitude','lat','ydim'): ren[d]='lat'
        elif low in ('longitude','lon','xdim'): ren[d]='lon'
        elif low in ('level','lev','plev','pressure'): ren[d]='lev'
        elif low in ('time','valid_time'): ren[d]='time'
    a = a.rename({k:v for k,v in ren.items() if k!=v})
    for d in ('lat','lon'):
        if d not in a.coords or a[d].ndim != 1:
            raise ValueError('Only rectilinear latitude/longitude grids are supported')
    if 'lev' in a.dims:
        units = a.lev.attrs.get('units','').lower()
        if units in ('pa','pascal','pascals'):
            a = a.assign_coords(lev=a.lev / 100.)
        elif units not in ('hpa','mb','mbar','millibar','millibars'):
            raise ValueError('Vertical coordinate must be pressure with Pa/hPa units; hybrid/model levels require preprocessing')
        a.lev.attrs['units']='hPa'
        a = a.sortby('lev')
    a = a.assign_coords(lon=(a.lon+180)%360-180).sortby('lon').sortby('lat')
    # Remove the duplicate cyclic endpoint, never count it twice.
    _, indices = np.unique(a.lon, return_index=True)
    a = a.isel(lon=np.sort(indices))
    extras = set(a.dims)-{'time','lat','lon','lev'}
    for dim in extras:
        if a.sizes[dim]!=1: raise ValueError('Unsupported dimension: '+dim)
        a = a.isel({dim:0},drop=True)
    return a


def select_time(a, begin, end, season):
    if 'time' not in a.dims: raise ValueError('Time coordinate required (including climatologies)')
    ym = a.time.dt.year*100+a.time.dt.month
    mask = (ym>=int(begin)) & (ym<=int(end)) & a.time.dt.month.isin(SEASONS[season])
    return a.isel(time=np.flatnonzero(mask.values))


def read_files(paths, alias, begin, end, season):
    chunks=[]
    for path in paths:
        with xr.open_dataset(path) as ds:
            actual = next((v for v in ds.data_vars if v.lower()==alias.lower()), None)
            if actual is None: continue
            a=normalize(ds[actual])
            a=select_time(a,begin,end,season)
            if a.sizes['time']: chunks.append(a.load())
    if not chunks: raise ValueError(f'No {alias} samples for {begin}–{end} {season}')
    a=xr.concat(chunks,dim='time',join='exact').sortby('time')
    if len(np.unique(a.time))!=a.sizes['time']:
        raise ValueError(f'Duplicate timestamps for {alias}; narrow the input file pattern')
    return a


class Experiment:
    def __init__(self, root, begin, end, season, history_path=None, patterns=None):
        self.root=Path(root); self.name=self.root.name
        hom=self.root
        if (hom/'.HOMDIR').is_file():
            hom=Path((hom/'.HOMDIR').read_text().strip())
            if not hom.is_absolute(): hom=self.root/hom
        self.fields=history(history_path or hom/'HISTORY.rc')
        self.window=(begin,end,season); self.patterns=patterns or {}; self.cache={}; self.files={}
        self.provenance={}

    def get(self,key,preferred=None):
        cachekey=(key,preferred)
        if cachekey in self.cache: return self.cache[cachekey]
        candidates=[(col,f) for col,fields in self.fields.items() for f in fields
                    if (f['export'],f['component'])==key]
        candidates.sort(key=lambda item: (item[0]!=preferred,item[0]!='geosgcm_prog'))
        if not candidates: raise KeyError(':'.join(key))
        col,f=candidates[0]
        if f['operation'] not in (None,'','mean','average'):
            raise ValueError('Unsupported HISTORY operation: '+str(f['operation']))
        if col not in self.files:
            import glob
            pattern=self.patterns.get(col)
            self.files[col]=sorted(glob.glob(str(self.root/pattern),recursive=True)) if pattern else sorted(
                str(p) for p in (self.root/col).rglob('*') if p.suffix in ('.nc','.nc4','.h5'))
        a=read_files(self.files[col],f['alias'],*self.window)
        self.cache[cachekey]=a
        self.provenance[':'.join(key)]={'collection':col,'alias':f['alias'],'files':self.files[col]}
        return a


def monthly(a):
    """Equal sample weights within each calendar month; missing cells renormalize."""
    key=a.time.dt.year*100+a.time.dt.month
    return a.assign_coords(month_id=('time',key.values)).groupby('month_id').mean('time',keep_attrs=True)


def mean(a, weighting='equal'):
    if 'month_id' not in a.dims: a=monthly(a)
    if weighting=='equal': return a.mean('month_id',keep_attrs=True)
    # Use calendar-aware month lengths retained from original times by caller.
    raise ValueError('Only equal-month weighting is currently implemented')


def paired(a,b,climatology=False):
    a,b=monthly(a),monthly(b)
    if climatology:
        def clim(x):
            return x.assign_coords(month_id=x.month_id%100).groupby('month_id').mean(keep_attrs=True)
        a,b=clim(a),clim(b)
    common=np.intersect1d(a.month_id,b.month_id)
    if not len(common): raise ValueError('No common months; use --climatology only for intentional seasonal climatology comparisons')
    return a.sel(month_id=common),b.sel(month_id=common),common.tolist()


def zonal(a):
    lon=np.deg2rad(a.lon.values)
    if len(lon)<2: raise ValueError('Zonal mean requires at least two longitudes')
    gaps=np.diff(np.r_[lon,lon[0]+2*np.pi])
    if gaps.max()>2.5*np.median(gaps): raise ValueError('Zonal means require global longitude coverage')
    weights=xr.DataArray((gaps+np.roll(gaps,1))/2,dims='lon',coords={'lon':a.lon})
    return a.weighted(weights).mean('lon',keep_attrs=True)


def regrid(reference, target):
    """Bilinear interpolation onto model grid; cyclic only for global grids."""
    if np.array_equal(reference.lon,target.lon) and np.array_equal(reference.lat,target.lat): return reference
    gaps=np.diff(np.r_[reference.lon.values,reference.lon.values[0]+360])
    if len(gaps)>1 and gaps.max()<2.5*np.median(gaps):
        reference=xr.concat([reference.isel(lon=[-1]).assign_coords(lon=[float(reference.lon[-1])-360]),
                             reference,reference.isel(lon=[0]).assign_coords(lon=[float(reference.lon[0])+360])],dim='lon')
    return reference.interp(lat=target.lat,lon=target.lon)


def metrics(a,b):
    a,b=xr.align(a,b,join='exact'); mask=np.isfinite(a)&np.isfinite(b)
    # Exact latitude-band area weights on a rectilinear grid; lon widths cyclic.
    lat=a.lat.values; edges=np.clip(np.r_[lat[0]-(lat[1]-lat[0])/2,(lat[1:]+lat[:-1])/2,lat[-1]+(lat[-1]-lat[-2])/2],-90,90)
    w=xr.DataArray(np.diff(np.sin(np.deg2rad(edges))),dims='lat',coords={'lat':a.lat})
    if 'lon' in a.dims:
        x=a.lon.values; edges=np.r_[x[0]-(x[1]-x[0])/2,(x[1:]+x[:-1])/2,x[-1]+(x[-1]-x[-2])/2]
        w=w*xr.DataArray(np.diff(edges),dims='lon',coords={'lon':a.lon})
    delta=(a-b).where(mask)
    if not bool(mask.any()): raise ValueError('No overlapping valid cells')
    return dict(bias=float(delta.weighted(w).mean()),rmse=float(np.sqrt((delta**2).weighted(w).mean())),valid_cells=int(mask.sum()))
