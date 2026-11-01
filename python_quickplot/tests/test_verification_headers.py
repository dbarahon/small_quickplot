import numpy as np
import pytest
import xarray as xr
from python_quickplot.verification import binary_field, Observation, rc_entries
from python_quickplot.diagnostics import calculate, compatible


def test_gpcp_header_yrev(tmp_path):
    data=np.arange(24,dtype='float32').reshape(2,3,4)
    (tmp_path/'gpcp.2009').write_bytes(b'x'*576+data.astype('>f4').tobytes())
    ctl=tmp_path/'gpcp.ctl'
    ctl.write_text('DSET ^gpcp.%y4\nfileheader 576\ntheader 0\nxyheader 0\noptions template yrev big_endian\nUNDEF -99999\nXDEF 4 LINEAR 0 90\nYDEF 3 LINEAR -60 60\nZDEF 1 LEVELS 1\nTDEF 2 LINEAR 00Z01JAN2009 1mo\nVARS 1\nprec 0 999 precip\nENDVARS\n')
    np.testing.assert_equal(binary_field(ctl,'prec').values,data[:,::-1,:])


def test_srb_format_and_time_window(tmp_path):
    ctl=tmp_path/'srb.ctl'
    ctl.write_text('DSET ^srb_%y4%m2.binary\nformat big_endian template\nUNDEF 1e16\nXDEF 2 LINEAR 0 180\nYDEF 2 LINEAR -45 90\nZDEF 1 LEVELS 0\nTDEF 2 LINEAR 00:00Z01JUL2005 1mo\nVARS 1\nOLRCLR 0 0 flux\nENDVARS\n')
    (tmp_path/'srb_200507.binary').write_bytes(b'bad')
    np.full((2,2),250,dtype='>f4').tofile(tmp_path/'srb_200508.binary')
    a=binary_field(ctl,'OLRCLR',('200508','200508','JJA'))
    assert float(a.isel(time=1).mean())==250
    with pytest.raises(ValueError,match='No verification time overlap'):
        binary_field(ctl,'OLRCLR',('200906','200908','JJA'))


def test_era5_rc_scaled_precipitation_units(tmp_path):
    a=xr.DataArray(np.full((1,2,2),.002),dims=('time','lat','lon'),coords={
        'time':np.array(['2009-06-01'],dtype='datetime64[ns]'),'lat':[-45,45],'lon':[0,180]},attrs={'units':'m'})
    xr.Dataset({'tp':a,'cp':a,'lsp':a}).to_netcdf(tmp_path/'data.nc')
    rc=tmp_path/'VERIFICATION.ERA5.rc'
    rc.write_text("filename: 'VERIFICATION/data.nc'\nfiletype: 'HDF'\nfields: 'TPREC','MOIST','tp',1000\n 'CN_PRCP','MOIST','cp',1000\n 'LS_PRCP','MOIST','lsp',1000\n::\n")
    obs=Observation('ERA5',rc_entries(rc,tmp_path),('200906','200908','JJA'))
    assert float(calculate(obs,'precip').mean())==2
    cp=obs.get(('CN_PRCP','MOIST'))
    assert cp.attrs['units']=='mm/day'
    model=a.copy();model.attrs['units']='kg m-2 s-1'
    assert float(compatible(model,cp).mean())==pytest.approx(2/86400)


def test_automatic_climatology_netcdf(tmp_path):
    from python_quickplot.verification import comparison_climatology
    from python_quickplot.data import paired
    a=xr.DataArray(np.arange(12).reshape(3,2,2),dims=('time','lat','lon'),
        coords={'time':np.array(['1989-06-01','1989-07-01','1989-08-01'],dtype='datetime64[ns]'),
                'lat':[-45,45],'lon':[0,180]},attrs={'units':'1'})
    a.to_dataset(name='cloud').to_netcdf(tmp_path/'cloud.nc')
    key=('CLDTT','SOLAR')
    obs=Observation('ISCCP',{key:dict(path=str(tmp_path/'cloud.nc'),variable='cloud')},('200906','200908','JJA'))
    result=obs.get(key)
    model=a.assign_coords(time=a.time.values+np.timedelta64(7305,'D'))
    assert comparison_climatology(obs,model,result)
    assert paired(model,result,True)[2]==[6,7,8]
    assert obs.provenance['CLDTT:SOLAR']['climatology_fallback']
    exact=Observation('ISCCP',obs.entries,('198906','198908','JJA'))
    assert not comparison_climatology(exact,a,exact.get(key))
    assert not exact.provenance['CLDTT:SOLAR']['climatology_fallback']


def test_automatic_climatology_binary(tmp_path):
    ctl=tmp_path/'cloud.ctl'
    ctl.write_text('DSET ^cloud.bin\noptions big_endian\nUNDEF -999\nXDEF 2 LINEAR 0 180\nYDEF 2 LINEAR -45 90\nZDEF 1 LEVELS 0\nTDEF 3 LINEAR 01JUN1990 1mo\nVARS 1\ncloud 0 0 cloud\nENDVARS\n')
    np.ones((3,2,2),dtype='>f4').tofile(tmp_path/'cloud.bin')
    obs=Observation('ISCCP',{('CLDTT','SOLAR'):dict(path=str(ctl),variable='cloud')},('200906','200908','JJA'))
    assert obs.get(('CLDTT','SOLAR')).sizes['time']==3
    assert obs.provenance['CLDTT:SOLAR']['available_period']==['199006','199008']
    (tmp_path/'cloud.bin').write_bytes(b'bad')
    obs.cache.clear()
    with pytest.raises(ValueError,match='Binary file size'):
        obs.get(('CLDTT','SOLAR'))


def test_all_four_isccp_maps_nonoverlapping(tmp_path):
    import json
    from python_quickplot.cli import main
    model=tmp_path/'model';(model/'surf').mkdir(parents=True)
    keys=['CLDLO','CLDMD','CLDHI','CLDTT']
    obsvars=['CLDLOW','CLDMID','CLDHI','CLDTOT']
    (model/'HISTORY.rc').write_text("COLLECTIONS:\n 'surf'\n::\nsurf.fields:\n"+
        '\n'.join(f" '{k}', 'SOLAR'" for k in keys)+"\n::\n")
    a=xr.DataArray(np.full((3,3,4),.5),dims=('time','lat','lon'),
        coords={'time':np.array(['2009-06-01','2009-07-01','2009-08-01'],dtype='datetime64[ns]'),
                'lat':[-60,0,60],'lon':[0,90,180,270]},attrs={'units':'1'})
    xr.Dataset({k:a for k in keys}).to_netcdf(model/'surf'/'model.nc')
    (tmp_path/'isccp.tabl').write_text('DSET ^isccp.bin\noptions big_endian\nUNDEF -999\n'
        'XDEF 4 LINEAR 0 90\nYDEF 3 LINEAR -60 60\nZDEF 1 LEVELS 0\n'
        'TDEF 3 LINEAR 01JUN1990 1mo\nVARS 4\n'+
        '\n'.join(f'{v} 0 99 fraction' for v in obsvars)+'\nENDVARS\n')
    np.full((3,4,3,4),40,dtype='>f4').tofile(tmp_path/'isccp.bin')
    catalog=tmp_path/'rcs';catalog.mkdir()
    (catalog/'VERIFICATION.ISCCP.rc').write_text(
        "filename: 'VERIFICATION/isccp.tabl'\nfiletype: 'BIN'\nfields: "+
        '\n'.join(f"'{k}', 'SOLAR', '{v}', 0.01 ," for k,v in zip(keys,obsvars))+'\n::\n')
    out=tmp_path/'out'
    main(['--source',str(model),'--collections','surf','--season','JJA',
          '--begdate','200906','--enddate','200908','--verification-dir',str(catalog),
          '--verification-root',str(tmp_path),'--output',str(out),'--dpi','40','--execute'])
    summary=json.loads((out/'summary.json').read_text())
    comparisons=[r for r in summary['results'] if '_vs_ISCCP' in r['task']]
    assert len(comparisons)==4
    assert all(r['state']=='ok' and r['climatology'] for r in comparisons)
    assert len(list((out/'plots').glob('*_vs_ISCCP.png')))==4
    for value in summary['provenance']['ISCCP'].values():
        assert value['climatology_fallback']
        assert value['available_period']==['199006','199008']


def test_operational_reanalysis_fallback(tmp_path):
    from python_quickplot.verification import VerificationExperiment, comparison_climatology
    (tmp_path/'surf').mkdir()
    (tmp_path/'HISTORY.rc').write_text("COLLECTIONS:\n 'surf'\n::\nsurf.fields:\n 'T','DYN'\n::\n")
    a=xr.DataArray(np.ones((3,2,2))*250,dims=('time','lat','lon'),
        coords={'time':np.array(['1990-06-01','1990-07-01','1990-08-01'],dtype='datetime64[ns]'),
                'lat':[-45,45],'lon':[0,180]},attrs={'units':'K'})
    a.to_dataset(name='T').to_netcdf(tmp_path/'surf'/'data.nc')
    ref=VerificationExperiment(tmp_path,'200906','200908','JJA')
    result=ref.get(('T','DYN'))
    model=a.assign_coords(time=np.array(['2009-06-01','2009-07-01','2009-08-01'],dtype='datetime64[ns]'))
    assert comparison_climatology(ref,model,result)
    assert ref.provenance['T:DYN']['climatology_fallback']
