import numpy as np
import pytest
import xarray as xr
from data import Experiment, read_files


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
    from verification import binary_field
    np.ones((1,2,2),dtype='<f4').tofile(tmp_path/'data.bin')
    ctl=tmp_path/'data.ctl'
    ctl.write_text('dset ^data.bin\nundef -999\noptions little_endian\nxdef 2 linear 0 180\nydef 2 linear -45 90\nzdef 1 linear 1 1\ntdef 1 linear jul1983 1mo\nvars 1\ncloud 0 99 cloud\nendvars\n')
    a=binary_field(ctl,'cloud')
    assert str(a.time.values[0]).startswith('1983-07-01')


def test_descriptor_window_and_metadata_reuse(tmp_path,monkeypatch):
    from python_quickplot import data
    from verification import descriptor_files
    paths=[]
    for year in (2008,2009,2010):
        for month in range(1,13):
            path=tmp_path/f'monthly.{year}{month:02d}.nc'
            a=xr.DataArray(np.ones((1,2,2))*month,dims=('time','lat','lon'),
                coords={'time':np.array([f'{year}-{month:02d}-01'],dtype='datetime64[ns]'),
                        'lat':[-45,45],'lon':[0,180]})
            xr.Dataset({'T':a,'U':a*2}).to_netcdf(path)
            paths.append(str(path))
    ctl=tmp_path/'xdf.tabl';ctl.write_text('DSET ^monthly.%y4%m2.nc\n')
    selected=descriptor_files(ctl,('200906','200908','JJA'))
    assert len(selected)==3
    opened=[];original=xr.open_dataset
    def tracked(path,*args,**kwargs):
        opened.append(str(path))
        return original(path,*args,**kwargs)
    monkeypatch.setattr(xr,'open_dataset',tracked)
    data.file_metadata.cache_clear()
    result=read_files(selected,'T','200906','200908','JJA')
    assert float(result.mean())==7
    assert set(opened)==set(selected)
    opened.clear()
    read_files(selected,'U','200906','200908','JJA')
    assert opened==selected  # Metadata already cached: only three field reads.
    # A broader special-plot window must not inherit the JJA inventory.
    assert len(descriptor_files(ctl,('200901','200912','ANN')))==12


def test_time_subset_before_normalize(tmp_path,monkeypatch):
    from python_quickplot import data
    a=xr.DataArray(np.ones((12,2,2)),dims=('time','lat','lon'),
        coords={'time':np.arange('2009-01','2010-01',dtype='datetime64[M]'),
                'lat':[-45,45],'lon':[0,180]})
    path=tmp_path/'annual.nc';a.to_dataset(name='T').to_netcdf(path)
    original=data.normalize
    def check_subset(field):
        assert field.sizes['time']==3
        return original(field)
    monkeypatch.setattr(data,'normalize',check_subset)
    assert read_files([str(path)],'T','200906','200908','JJA').sizes['time']==3
