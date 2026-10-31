"""Restricted GEOS resource catalog and Python readers for legacy descriptors."""
from pathlib import Path
import ast
import glob
import operator
import re
import numpy as np
import pandas as pd
import xarray as xr
from .data import normalize, select_time, read_files


def number(expression):
    ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Pow:operator.pow}
    def visit(n):
        if isinstance(n,ast.Constant) and isinstance(n.value,(int,float)): return n.value
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.USub,ast.UAdd)):
            return (-1 if isinstance(n.op,ast.USub) else 1)*visit(n.operand)
        if isinstance(n,ast.BinOp) and type(n.op) in ops: return ops[type(n.op)](visit(n.left),visit(n.right))
        raise ValueError('Not a numeric scale: '+expression)
    return float(visit(ast.parse(expression,mode='eval').body))


def rc_entries(path, root):
    text=Path(path).read_text(); entries={}
    for block in re.split(r'(?im)^\s*filename:',text)[1:]:
        filename=re.search(r"'([^']+)'",block)[1]
        filename=filename.replace('VERIFICATION/',str(Path(root))+'/')
        fields=re.search(r'(?is)fields:\s*(.*?)::',block)
        if not fields: continue
        for line in fields[1].splitlines():
            m=re.search(r"'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*([^!#]+)",line)
            if m:
                entries[(m[1],m[2])]=dict(path=filename,variable=m[3],scale=number(m[4].strip().rstrip(',').strip()),
                    filetype=(re.search(r"(?i)filetype:\s*'([^']+)'",block)[1] if re.search(r"(?i)filetype:\s*'([^']+)'",block) else 'HDF'))
    return entries


def descriptor_files(path):
    text=Path(path).read_text()
    m=re.search(r'(?im)^\s*dset\s+(.+)$',text)
    if not m: raise ValueError('Descriptor has no DSET: '+str(path))
    pattern=m[1].strip().strip('"\'')
    if pattern.startswith('^'): pattern=str(Path(path).parent/pattern[1:])
    elif not Path(pattern).is_absolute(): pattern=str(Path(path).parent/pattern)
    pattern=re.sub(r'%[a-zA-Z]\d+', '*', pattern)
    return sorted(glob.glob(pattern))


def binary_field(path, variable):
    """Regular GrADS float32 binary grids, monthly/daily/hourly TDEF.

    Unsupported layouts fail explicitly rather than guessing record offsets.
    """
    path=Path(path); text=path.read_text(); lines=[s.strip() for s in text.splitlines() if s.strip() and not s.lstrip().startswith('*')]
    directives={s.split()[0].lower():s.split()[1:] for s in lines}
    opts=directives.get('options',[])
    unsupported=set(opts)-{'little_endian','big_endian','byteswapped','yrev','zrev','template'}
    if directives.get('dtype',['binary'])[0].lower()!='binary': raise ValueError('Only raw binary CTL data supported')
    if unsupported or any(k in directives for k in ('pdef','fileheader','theader','xyheader','trailer')):
        raise ValueError('Unsupported binary layout/options in '+str(path)+': '+str(unsupported))
    def axis(name):
        p=directives[name+'def']; n=int(p[0])
        if p[1].lower()=='linear': return float(p[2])+np.arange(n)*float(p[3])
        if p[1].lower()=='levels':
            tail=re.split(r'(?im)^\s*'+name+r'def\s+\d+\s+levels\s*',text,maxsplit=1)[1]
            vals=[]
            for token in tail.split():
                try: vals.append(float(token))
                except ValueError: break
                if len(vals)==n: return np.array(vals)
        raise ValueError('Unsupported '+name+' axis')
    x,y,z=axis('x'),axis('y'),axis('z')
    td=directives['tdef']
    if td[1].lower()!='linear': raise ValueError('TDEF must be linear')
    start=td[2].lower()
    m=re.fullmatch(r'(?:(\d{1,2})(?::(\d{2}))?z)?(\d{1,2})([a-z]{3})(\d{4})',start)
    if not m: raise ValueError('Unsupported TDEF date: '+start)
    dt=pd.to_datetime(f'{m[3]}{m[4]}{m[5]}',format='%d%b%Y')+pd.Timedelta(hours=int(m[1] or 0),minutes=int(m[2] or 0))
    inc=re.fullmatch(r'(\d+)(mo|yr|dy|hr|mn)',td[3].lower())
    if not inc: raise ValueError('Unsupported time increment')
    offset=pd.DateOffset(**{dict(mo='months',yr='years',dy='days',hr='hours',mn='minutes')[inc[2]]:int(inc[1])})
    times=pd.DatetimeIndex([dt+i*offset for i in range(int(td[0]))])
    vi=next(i for i,s in enumerate(lines) if s.lower().startswith('vars '))
    variables=[s.split() for s in lines[vi+1:vi+1+int(lines[vi].split()[1])]]
    names=[v[0].lower() for v in variables]
    if variable.lower() not in names: raise KeyError(variable)
    index=names.index(variable.lower()); nz=max(1,int(variables[index][1]))
    record=sum(max(1,int(v[1])) for v in variables)*len(x)*len(y)
    skip=sum(max(1,int(v[1])) for v in variables[:index])*len(x)*len(y)
    dtype='>f4' if 'big_endian' in opts else '<f4' if 'little_endian' in opts else '=f4'
    if 'byteswapped' in opts: dtype=np.dtype('=f4').newbyteorder()
    dset=' '.join(directives['dset']).strip('"\'')
    if dset.startswith('^'): dset=str(path.parent/dset[1:])
    elif not Path(dset).is_absolute(): dset=str(path.parent/dset)
    groups={}
    for i,t in enumerate(times):
        filename=dset
        for token,value in {'%y4':t.strftime('%Y'),'%y2':t.strftime('%y'),'%m2':t.strftime('%m'),'%d2':t.strftime('%d'),'%h2':t.strftime('%H'),'%n2':t.strftime('%M')}.items(): filename=filename.replace(token,value)
        if '%' in filename: raise ValueError('Unsupported DSET template: '+filename)
        groups.setdefault(filename,[]).append(i)
    data=np.full((len(times),nz,len(y),len(x)),np.nan,dtype='float32')
    for filename,indices in groups.items():
        if not Path(filename).is_file(): continue
        expected=len(indices)*record*4
        if Path(filename).stat().st_size!=expected: raise ValueError('Binary file size does not match descriptor: '+filename)
        raw=np.memmap(filename,dtype=dtype,mode='r',shape=(len(indices),record))
        data[indices]=raw[:,skip:skip+nz*len(y)*len(x)].reshape(len(indices),nz,len(y),len(x))
        del raw
    undef=float(directives['undef'][0]); data[np.isclose(data,undef,rtol=1e-6,atol=0)]=np.nan
    if 'yrev' in opts: data=data[:,:,::-1,:]
    if 'zrev' in opts: data=data[:,::-1,:,:]
    a=xr.DataArray(data,dims=('time','lev','lat','lon'),coords={'time':times,'lev':z[:nz],'lat':y,'lon':x})
    if int(variables[index][1])==0: a=a.isel(lev=0,drop=True)
    else: a.lev.attrs['units']='hPa' # GrADS ZDEF pressure convention
    return a


class Observation:
    def __init__(self,name,entries,window):
        self.name=name; self.entries=entries; self.window=window; self.cache={}; self.provenance={}
    def get(self,key,preferred=None):
        if key in self.cache: return self.cache[key]
        if key not in self.entries: raise KeyError(':'.join(key))
        e=self.entries[key]; path=Path(e['path'])
        if e.get('filetype','').upper()=='BIN' or path.suffix.lower()=='.ctl':
            a=select_time(normalize(binary_field(path,e['variable'])),*self.window)
        else:
            files=descriptor_files(path) if path.suffix.lower() in ('.tabl','.ddf') else sorted(glob.glob(str(path)))
            a=read_files(files,e['variable'],*self.window)
        if not a.sizes.get('time',0) or not bool(a.notnull().any()): raise ValueError('No verification data: '+str(path))
        attrs=a.attrs.copy(); a=a*e.get('scale',1)+e.get('offset',0); a.attrs=attrs
        from .diagnostics import KNOWN_UNITS
        if e.get('filetype') and key in KNOWN_UNITS: a.attrs['units']=KNOWN_UNITS[key]
        if e.get('units'): a.attrs['units']=e['units']
        # Native resource scales define precipitation in mm/day, unlike model kg m-2 s-1.
        if key==('TPREC','MOIST') and not e.get('units'): a.attrs['units']='mm/day'
        self.cache[key]=a; self.provenance[':'.join(key)]=e
        return a


def catalog(folder,root,window,manifest=None,extra_rcs=()):
    sources={}; allowed={'MERRA-2','MERRA2','ERA5'}
    if folder:
        for rc in sorted(Path(folder).glob('VERIFICATION.*.rc')):
            name=rc.name[len('VERIFICATION.'):-3]; allowed.add(name)
            sources[name]=Observation(name,rc_entries(rc,root),window)
    for rc in extra_rcs:
        name=Path(rc).name[len('VERIFICATION.'):-3]
        if name not in {'MERRA-2','MERRA2','ERA5'}: raise ValueError('Extra RCs are restricted to MERRA-2 and ERA5')
        sources[name]=Observation(name,rc_entries(rc,root),window)
    for name,entries in (manifest or {}).items():
        if name not in allowed: raise ValueError('Verification dataset not in installed folder or MERRA-2/ERA5: '+name)
        parsed={tuple(k.split(':')):v for k,v in entries.items()}
        if name in sources: sources[name].entries.update(parsed)
        else: sources[name]=Observation(name,parsed,window)
    return list(sources.values())


def operational_reanalyses(root, window, existing=()):
    """QuickPlot's cmpops directories, read as experiments, not extra RC catalogs."""
    from .data import Experiment
    sources = []
    for directory, name in [('MERRA2_MEANS', 'MERRA-2'), ('ERA5_Monthly', 'ERA5')]:
        if name in existing or (name == 'MERRA-2' and 'MERRA2' in existing):
            continue
        path = Path(root) / directory
        if not path.is_dir():
            print(f'NOTICE: {name} comparison directory missing: {path}', flush=True)
            continue
        try:
            source = Experiment(path, *window)
            source.name = name
            sources.append(source)
        except (OSError, ValueError) as exc:
            print(f'NOTICE: Cannot initialize {name} at {path}: {exc}', flush=True)
    return sources
