import json
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from python_quickplot.data import normalize, paired, regrid, zonal, metrics, Experiment
from python_quickplot.diagnostics import calculate
from python_quickplot.verification import binary_field, number, catalog
from python_quickplot.cli import main


def array(value=1.,pressure=False):
    dims=['time','lat','lon']; coords=dict(time=pd.date_range('2009-06-01',periods=3,freq='MS'),lat=[-60.,0.,60.],lon=[0.,90.,180.,270.])
    if pressure: dims.insert(1,'lev'); coords['lev']=[250.,500.,850.]
    a=xr.DataArray(np.full(tuple(len(coords[d]) for d in dims),value),dims=dims,coords=coords,attrs={'units':'K'})
    if pressure: a.lev.attrs['units']='hPa'
    return a


def experiment(root,offset=0):
    root.mkdir(); (root/'surf').mkdir(); (root/'prog').mkdir()
    (root/'HISTORY.rc').write_text("""COLLECTIONS:
 'surf'
 'prog'
::
surf.fields:
 'TPREC', 'MOIST', 'rain'
 'OLR', 'IRRAD'
 'OLC', 'IRRAD'
 'RSR', 'SOLAR'
 'RSC', 'SOLAR'
 'OSR', 'SOLAR'
 'OSRCLR', 'SOLAR'
::
prog.fields:
 'T', 'DYN', 'temp'
::
""")
    rain=array(1/86400+offset/86400); rain.attrs['units']='kg m-2 s-1'
    fields={'rain':rain}
    for name,v in dict(OLR=240,OLC=270,RSR=240,RSC=280,OSR=100,OSRCLR=60).items():
        fields[name]=array(v+offset); fields[name].attrs['units']='W m-2'
    xr.Dataset(fields).to_netcdf(root/'surf'/'data.nc4')
    xr.Dataset({'temp':array(250+offset,True)}).to_netcdf(root/'prog'/'data.nc4')
    return root


def test_units_aliases_and_formulas(tmp_path):
    root=experiment(tmp_path/'model'); source=Experiment(root,'200906','200908','JJA')
    assert float(calculate(source,'precip').mean())==pytest.approx(1)
    assert float(calculate(source,'olrcf').mean())==30
    assert float(calculate(source,'osrcf').mean())==40
    assert float(calculate(source,'toacf').mean())==-10
    assert calculate(source,('T','DYN')).sizes['lev']==3


def test_pressure_validation():
    a=array(1,True); a.lev.attrs['units']='Pa'; a=a.assign_coords(lev=a.lev*100); a.lev.attrs['units']='Pa'
    assert list(normalize(a).lev.values)==[250,500,850]
    a.lev.attrs['units']='1'
    with pytest.raises(ValueError,match='pressure'): normalize(a)


def test_pair_and_cyclic_grid():
    a=normalize(array()); b=a.isel(time=[1,2])+2
    aa,bb,months=paired(a,b)
    assert months==[200907,200908]
    b=b.assign_coords(time=pd.date_range('2010-07-01',periods=2,freq='MS'))
    with pytest.raises(ValueError,match='common months'): paired(a,b)
    aa,bb,months=paired(a,b,True)
    assert months==[7,8]
    target=a.isel(time=0).assign_coords(lon=[-179.,-89.,1.,91.])
    assert bool(regrid(a.isel(time=0),target).notnull().all())
    assert float(zonal(target).mean())==1
    assert metrics(target,target+2)['rmse']==2


def test_binary_and_resource_catalog(tmp_path):
    data=np.arange(24,dtype='<f4').reshape(2,3,4); data.tofile(tmp_path/'test.bin')
    ctl=tmp_path/'test.ctl'
    ctl.write_text('dset ^test.bin\nundef -9999\noptions little_endian\nxdef 4 linear 0 90\nydef 3 linear -60 60\nzdef 1 linear 1 1\ntdef 2 linear 00z01jun2009 1mo\nvars 1\nprec 0 99 rain\nendvars\n')
    result=binary_field(ctl,'prec'); np.testing.assert_array_equal(result,data)
    rcs=tmp_path/'rcs'; rcs.mkdir()
    (rcs/'VERIFICATION.GPCP.rc').write_text("filename: 'VERIFICATION/test.ctl'\nfields: 'TPREC', 'MOIST', 'prec', 1\n::\n")
    obs=catalog(rcs,tmp_path,('200906','200908','JJA'))[0]
    assert calculate(obs,'precip').shape==(2,3,4)
    with pytest.raises(ValueError): number('__import__("os")')
    with pytest.raises(ValueError,match='not in installed'): catalog(rcs,tmp_path,('200906','200908','JJA'),{'OTHER':{}})


def test_end_to_end(tmp_path):
    source=experiment(tmp_path/'model'); reference=experiment(tmp_path/'reference',2)
    output=tmp_path/'output'
    args=['--source',str(source),'--compare',str(reference),'--collections','surf','prog','--begdate','200906','--enddate','200908','--season','JJA','--variables','precip','toa_radz','T','--levels','500','--no-verification','--save-fields','--execute','--output',str(output)]
    assert main(args)==0
    summary=json.loads((output/'summary.json').read_text())
    assert all(r['state']=='ok' for r in summary['results'])
    assert len(list((output/'plots').glob('*.png')))>=10
    entry=next(r for r in summary['results'] if r['task']=='prog_T_DYN_level_500hPa_vs_reference')
    assert entry['metrics']['bias']==pytest.approx(-2)
    with xr.open_dataset(output/'prog_T_DYN_level_500hPa_vs_reference.nc') as ds:
        assert float(ds.difference.mean())==pytest.approx(-2)


def test_obs_scaled_units_binary_tabl_and_lwp(tmp_path):
    from python_quickplot.verification import Observation, rc_entries
    a=array(50); a.attrs['units']='%'; xr.Dataset({'cloud':a,'liquid':a}).to_netcdf(tmp_path/'obs.nc')
    rc=tmp_path/'VERIFICATION.ISCCP.rc'
    rc.write_text("filename: 'VERIFICATION/obs.nc'\nfiletype: 'HDF'\nfields: 'CLDTT', 'SOLAR', 'cloud', 0.01 ,\n::\n")
    obs=Observation('ISCCP',rc_entries(rc,tmp_path),('200906','200908','JJA'))
    assert float(calculate(obs,('CLDTT','SOLAR')).mean())==.5
    assert calculate(obs,('CLDTT','SOLAR')).attrs['units']=='1'
    obs=Observation('MAC-LWP',{('LWP','MOIST'):dict(path=str(tmp_path/'obs.nc'),variable='liquid',scale=.001,units='kg m-2')},('200906','200908','JJA'))
    assert float(calculate(obs,'lwp').mean())==pytest.approx(.05)


def test_verification_end_to_end(tmp_path):
    source=experiment(tmp_path/'model'); folder=tmp_path/'rc'; folder.mkdir()
    data=np.full((3,3,4),2,dtype='<f4'); data.tofile(tmp_path/'rain.bin')
    (tmp_path/'rain.tabl').write_text('dset ^rain.bin\nundef -9999\noptions little_endian\nxdef 4 linear 0 90\nydef 3 linear -60 60\nzdef 1 linear 1 1\ntdef 3 linear 00z01jun2009 1mo\nvars 1\nprec 0 99 rain\nendvars\n')
    (folder/'VERIFICATION.GPCP.rc').write_text("filename: 'VERIFICATION/rain.tabl'\nfiletype: 'BIN'\nfields: 'TPREC', 'MOIST', 'prec', 1 ,\n::\n")
    out=tmp_path/'verification'
    assert main(['--source',str(source),'--collections','surf','--variables','precip','--begdate','200906','--enddate','200908','--season','JJA','--verification-dir',str(folder),'--verification-root',str(tmp_path),'--output',str(out),'--execute'])==0
    result=json.loads((out/'summary.json').read_text())['results']
    assert result[-1]['metrics']['bias']==pytest.approx(-1)


def test_binary_template_endian_and_missing(tmp_path):
    for month in (6,7):
        x=np.array([[1,2],[3,-9999]],dtype='>f4'); x.tofile(tmp_path/f'rain.2009{month:02d}')
    ctl=tmp_path/'a.ctl'; ctl.write_text('dset ^rain.%y4%m2\nundef -9999\noptions big_endian template yrev\nxdef 2 linear 0 180\nydef 2 linear -45 90\nzdef 1 linear 1 1\ntdef 2 linear 00z01jun2009 1mo\nvars 1\nprec 0 99 rain\nendvars\n')
    a=binary_field(ctl,'prec')
    assert float(a[0,0,0])==3
    assert np.isnan(a[0,0,1])
    assert float(a[1,1,0])==1
