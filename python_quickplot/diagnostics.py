"""Explicit GEOS export/component formulas, with no executable GrADS parsing."""
import xarray as xr

RECIPES={
 'lwp': [('TQL','AGCM')],
 'tlwp': [('TQL','AGCM'),('TQR','AGCM')],
 'precip': [('CN_PRCP','MOIST'),('LS_PRCP','MOIST'),('AN_PRCP','MOIST')],
 'olrcf': [('OLC','IRRAD'),('OLR','IRRAD')],
 'osrcf': [('RSC','SOLAR'),('RSR','SOLAR')],
 'toacf': [('OLC','IRRAD'),('OLR','IRRAD'),('OSRCLR','SOLAR'),('OSR','SOLAR')],
}
RADIATION=[('OLR','IRRAD'),('OLC','IRRAD'),('RSR','SOLAR'),('RSC','SOLAR')]
KNOWN_UNITS={**{k:'W m-2' for k in RADIATION+[('OSR','SOLAR'),('OSRCLR','SOLAR'),('SLRTP','SOLAR')]},
 ('T','DYN'):'K',('U','DYN'):'m s-1',('V','DYN'):'m s-1',('ZLE','DYN'):'m',('SLP','DYN'):'Pa',
 ('PS','DYN'):'Pa',('Q','MOIST'):'kg kg-1',('RH2','MOIST'):'1',
 ('TQL','AGCM'):'kg m-2',('TQI','AGCM'):'kg m-2',('TQV','AGCM'):'kg m-2',
 ('CLDTT','SOLAR'):'1',('CLDLO','SOLAR'):'1',('CLDMD','SOLAR'):'1',('CLDHI','SOLAR'):'1'}


KNOWN_UNITS.update({(v,'IRRAD'):'W m-2' for v in ('SFCDWNC','SFCDWN','SFCUP','SFCUPC','OLCC5')})
KNOWN_UNITS.update({(v,'SOLAR'):'W m-2' for v in ('SLRSFC','SLRSF','RSRS','RSCS')})
KNOWN_UNITS.update({(v,'MOIST'):'kg m-2 s-1' for v in ('CN_PRCP','LS_PRCP','AN_PRCP','TPREC')})
KNOWN_UNITS.update({('LWP','MOIST'):'kg m-2',('TLWP','AGCM'):'kg m-2',('TQR','AGCM'):'kg m-2'})


def units_text(s):
    return str(s).lower().replace('**','').replace('^','').replace(' ','').replace('per','/').replace('day-1','/day')


def precipitation(a):
    u=units_text(a.attrs.get('units',''))
    if u in ('kgm-2s-1','kg/m2/s','mms-1','mm/s'): fac=86400.
    elif u in ('mm/day','mmd-1','mmday-1'): fac=1.
    elif u in ('m/day','md-1'): fac=1000.
    else: raise ValueError('Precipitation rate units required; cannot infer accumulation interval: '+u)
    a=a*fac; a.attrs['units']='mm/day'; return a


def field(source,key,preferred=None):
    a=source.get(key,preferred).copy(deep=False)
    if not a.attrs.get('units') and key in KNOWN_UNITS: a.attrs['units']=KNOWN_UNITS[key]
    return a


def calculate(source,name,preferred=None):
    if isinstance(name,tuple): return field(source,name,preferred)
    if name in ('lwp','tlwp'):
        obskey=('LWP','MOIST') if name=='lwp' else ('TLWP','AGCM')
        if hasattr(source,'entries') and obskey in source.entries: return field(source,obskey,preferred)
        arrays=xr.align(*(field(source,k,preferred) for k in RECIPES[name]),join='exact')
        for a in arrays:
            if units_text(a.attrs.get('units','')) not in ('kgm-2','kg/m2'): raise ValueError('Water path must be in kg m-2')
        result=sum(arrays); result.attrs['units']='kg m-2'
        result.attrs['long_name']='Cloud liquid water path' if name=='lwp' else 'Total liquid water path (cloud + rain)'
        return result
    if name=='precip':
        # Observations usually provide total precipitation directly.
        try:
            arrays=[precipitation(field(source,k,preferred)) for k in RECIPES[name]]
        except (KeyError, FileNotFoundError, ValueError) as component_error:
            try:
                return precipitation(field(source,('TPREC','MOIST'),preferred))
            except (KeyError, FileNotFoundError, ValueError) as total_error:
                raise ValueError(f'Precipitation components unavailable: {component_error}; '
                                 f'TPREC fallback unavailable: {total_error}') from total_error
        arrays=xr.align(*arrays,join='exact'); result=sum(arrays)
        result.attrs['units']='mm/day'
    else:
        arrays=xr.align(*(field(source,k,preferred) for k in RECIPES[name]),join='exact')
        for a in arrays:
            if units_text(a.attrs.get('units','')) not in ('wm-2','w/m2'): raise ValueError('Radiative flux must be in W m-2')
        result=arrays[0]-arrays[1]
        if name=='toacf': result=result+arrays[2]-arrays[3]
        result.attrs['units']='W m-2'
    result.attrs['long_name']={'precip':'Total precipitation','olrcf':'Longwave cloud radiative effect',
        'osrcf':'GEOS shortwave cloud forcing (clear minus all net SW)',
        'toacf':'Total cloud radiative effect'}[name]
    return result


def compatible(a,b):
    ua,ub=units_text(a.attrs.get('units','')),units_text(b.attrs.get('units',''))
    synonyms={'w/m2':'wm-2','m/s':'ms-1','kg/kg':'kgkg-1','kg/m2':'kgm-2','dimensionless':'1','fraction':'1','kelvin':'k'}
    ua,ub=synonyms.get(ua,ua),synonyms.get(ub,ub)
    if not ua or not ub: raise ValueError('Comparison requires known units on both fields; set manifest units')
    if ua==ub: return b
    if ua in ('kgm-2s-1','kg/m2/s') and ub=='mm/day': b=b/86400
    elif ua=='mm/day' and ub in ('kgm-2s-1','kg/m2/s'): b=b*86400
    elif (ua,ub)==('pa','hpa'): b=b*100
    elif (ua,ub)==('hpa','pa'): b=b/100
    elif (ua,ub)==('1','%'): b=b/100
    elif (ua,ub)==('%','1'): b=b*100
    else: raise ValueError(f'Incompatible units: {ua} vs {ub}; provide explicit scale/units in manifest')
    b.attrs['units']=a.attrs['units']; return b


def supports(source,name):
    if not hasattr(source,'entries'): return True
    available=source.entries
    if isinstance(name,tuple): return name in available
    if name=='toa_radz': return all(k in available for k in RADIATION)
    if name=='precip' and ('TPREC','MOIST') in available: return True
    if name=='lwp' and ('LWP','MOIST') in available: return True
    if name=='tlwp' and ('TLWP','AGCM') in available: return True
    return all(k in available for k in RECIPES[name])
