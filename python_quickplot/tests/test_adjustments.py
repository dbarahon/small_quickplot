import numpy as np
import xarray as xr
from python_quickplot.diagnostics import calculate
from python_quickplot.verification import operational_reanalyses
from python_quickplot.render import panels


def test_precip_fallback_when_components_have_no_data():
    class Source:
        def get(self, key, preferred=None):
            if key[0] != 'TPREC': raise ValueError('No component samples')
            return xr.DataArray([1/86400])  # Known GEOS export has canonical rate units.
    a=calculate(Source(), 'precip')
    assert float(a[0]) == 1
    assert a.attrs['units'] == 'mm/day'


def test_operational_merra_descriptor(tmp_path):
    root=tmp_path/'MERRA2_MEANS'; root.mkdir()
    (root/'HISTORY.rc').write_text("COLLECTIONS:\n 'asm'\n::\nasm.fields:\n 'T', 'DYN', 'T'\n::\n")
    (root/'asm').mkdir(); data=tmp_path/'external.nc'
    xr.Dataset({'T':xr.DataArray(np.ones((1,2,2,4))*270,
        dims=('time','lev','lat','lon'),coords={'time':np.array(['2009-06-01'],dtype='datetime64[ns]'),
        'lev':xr.DataArray([500,1000],dims='lev',attrs={'units':'hPa'}),
        'lat':[-45,45],'lon':[0,90,180,270]},attrs={'units':'K'})}).to_netcdf(data)
    (root/'asm'/'xdf.tabl').write_text(f'DSET {data}\n')
    sources=operational_reanalyses(tmp_path,('200906','200908','JJA'),existing=['ERA5'])
    assert [s.name for s in sources]==['MERRA-2']
    assert float(sources[0].get(('T','DYN')).mean())==270
    assert operational_reanalyses(tmp_path,('200906','200908','JJA'),existing=['MERRA-2','ERA5'])==[]


def test_section_layout_is_linear(tmp_path,monkeypatch):
    import matplotlib.figure
    captured=[]
    def capture(fig,*args,**kwargs):
        captured.extend(fig.axes)
    monkeypatch.setattr(matplotlib.figure.Figure,'savefig',capture)
    a=xr.DataArray(np.arange(24).reshape(4,6),dims=('lev','lat'),
        coords={'lev':[100,300,700,1000],'lat':np.linspace(-90,90,6)})
    panels([a,a+1,a-(a+1)],['model','reference','difference'],'Test',tmp_path/'plot.png',section=True)
    assert len(captured)==5
    assert all(ax.get_yscale()=='linear' for ax in captured[:3])
    assert all(ax.get_ylim()==(1000,100) for ax in captured[:3])
