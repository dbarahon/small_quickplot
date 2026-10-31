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
