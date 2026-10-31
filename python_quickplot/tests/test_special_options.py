import numpy as np
import pandas as pd
import pytest
import xarray as xr
from python_quickplot import render
from python_quickplot.special import profiles, qbo, vortex, band
from python_quickplot.unify_plots import unify
from python_quickplot.verification import Observation


def sample():
    time=pd.date_range('2000-01-01',periods=24,freq='MS')
    lev=np.array([.1,1,10,50,100,500,1000])
    lat=np.arange(-90,91,5); lon=np.arange(0,360,60)
    values=20*np.sin(np.arange(24)[:,None,None,None]/2)+10*np.log10(lev)[None,:,None,None]
    values=np.broadcast_to(values,(24,7,len(lat),len(lon))).copy()
    return xr.DataArray(values,dims=('time','lev','lat','lon'),coords=dict(time=time,lev=lev,lat=lat,lon=lon),attrs={'units':'m s-1'})


def test_percentile_and_dpi(tmp_path,monkeypatch):
    import matplotlib.figure
    saved=[]
    monkeypatch.setattr(matplotlib.figure.Figure,'savefig',lambda self,*args,**kw:saved.append(kw['dpi']))
    render.configure(222,90)
    try:
        a=xr.DataArray(np.r_[np.ones(99),100])
        assert render.levels([a],difference=True)[-1]==1
        z=sample().mean('time')
        profiles([('model',z)],('T','DYN'),tmp_path/'p.png','Temperature')
        qbo([('model',sample())],tmp_path/'q.png','U')
        vortex([('model',sample())],tmp_path/'v.png','U')
        assert saved==[222,222,222]
    finally: render.configure()


def test_unify_refuses_collision(tmp_path):
    run=tmp_path/'run'; (run/'plots').mkdir(parents=True)
    src=run/'plots'/'plot.png'; src.write_bytes(b'example')
    dest=tmp_path/'all'
    rows=unify([run],dest)
    assert len(rows)==1 and not src.exists()
    assert (dest/'run__plot.png').read_bytes()==b'example'
    src.write_bytes(b'new')
    with pytest.raises(FileExistsError): unify([run],dest)
    assert src.read_bytes()==b'new'


def test_isccp_hdf_label_with_binary_tabl(tmp_path):
    np.full((1,2,2),50,dtype='<f4').tofile(tmp_path/'cloud.bin')
    path=tmp_path/'isccp.tabl'
    path.write_text('dset ^cloud.bin\noptions little_endian\nundef -999\nxdef 2 linear 0 180\nydef 2 linear -45 90\nzdef 1 levels 1\ntdef 1 linear jul1983 1mo\nvars 1\ncldtot 0 99 cloud\nendvars\n')
    obs=Observation('ISCCP',{('CLDTT','SOLAR'):dict(path=str(path),variable='cldtot',filetype='HDF',scale=.01)},('198307','198307','JJA'))
    assert float(obs.get(('CLDTT','SOLAR')).mean())==.5


def test_special_pipeline_and_unify(tmp_path):
    import json
    from python_quickplot.cli import main
    root=tmp_path/'experiment'; (root/'prog').mkdir(parents=True)
    (root/'HISTORY.rc').write_text("COLLECTIONS:\n 'prog'\n::\nprog.fields:\n 'U','DYN'\n::\n")
    a=sample(); a.lev.attrs['units']='hPa'
    a.to_dataset(name='U').to_netcdf(root/'prog'/'monthly.nc')
    out=tmp_path/'run'; dest=tmp_path/'all'
    assert main(['--source',str(root),'--collections','prog','--variables','U','--begdate','200001','--enddate','200112',
                 '--season','JJA','--levels','500','--no-verification','--special-plots','--dpi','60',
                 '--unify-plots',str(dest),'--output',str(out),'--execute'])==0
    summary=json.loads((out/'summary.json').read_text())
    assert any(r['task'].endswith('_qbo') for r in summary['results'])
    assert any(r['task'].endswith('_vortex') for r in summary['results'])
    assert not list((out/'plots').glob('*.png'))
    assert len(list(dest.glob('*.png')))>=6
    render.configure()
