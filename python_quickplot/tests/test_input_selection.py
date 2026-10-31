import numpy as np
import pytest
import xarray as xr
from python_quickplot.data import Experiment, read_files


def test_descriptor_excludes_duplicate_stream_and_reads_max(tmp_path):
    col=tmp_path/'prog'; col.mkdir(); (col/'other').mkdir()
    (tmp_path/'HISTORY.rc').write_text("COLLECTIONS:\n 'prog'\n::\nprog.fields:\n 'T', 'DYN', 'T', 'MAX'\n::\n")
    a=xr.DataArray(np.ones((1,2,2)),dims=('time','lat','lon'),coords={
        'time':np.array(['2009-06-01'],dtype='datetime64[ns]'), 'lat':[-45,45], 'lon':[0,180]})
    a.to_dataset(name='T').to_netcdf(col/'monthly.nc')
    (a*2).to_dataset(name='T').to_netcdf(col/'other'/'daily.nc')
    (col/'xdf.tabl').write_text('DSET ^monthly.nc\n')
    model=Experiment(tmp_path,'200906','200908','JJA')
    assert float(model.get(('T','DYN')).mean())==1
    assert model.provenance['T:DYN']['files']==[str(col/'monthly.nc')]
    explicit=Experiment(tmp_path,'200906','200908','JJA',patterns={'prog':'prog/other/*.nc'})
    assert float(explicit.get(('T','DYN')).mean())==2
    with pytest.raises(ValueError,match='conflicting files:.*monthly.nc.*daily.nc'):
        read_files([str(col/'monthly.nc'),str(col/'other'/'daily.nc')],'T','200906','200908','JJA')


def test_isccp_month_only_date(tmp_path):
    from python_quickplot.verification import binary_field
    np.ones((1,2,2),dtype='<f4').tofile(tmp_path/'data.bin')
    ctl=tmp_path/'data.ctl'
    ctl.write_text('dset ^data.bin\nundef -999\noptions little_endian\nxdef 2 linear 0 180\nydef 2 linear -45 90\nzdef 1 linear 1 1\ntdef 1 linear jul1983 1mo\nvars 1\ncloud 0 99 cloud\nendvars\n')
    a=binary_field(ctl,'cloud')
    assert str(a.time.values[0]).startswith('1983-07-01')
