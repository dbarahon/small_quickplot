import numpy as np
import pytest
import xarray as xr
from python_quickplot.data import Experiment, history
from python_quickplot.cli import main
import json


def test_bundle_aliases_are_separate_fields(tmp_path):
    root = tmp_path / "model"
    (root / "surf").mkdir(parents=True)
    (root / "HISTORY.rc").write_text("""COLLECTIONS:
 'surf'
::
surf.fields:
 'DUEM', 'DU', 'DUEM001;DUEM002;DUEM003;DUEM004;DUEM005'
 'T', 'DYN', 'temp'
 'A;B', 'TEST', 'a;b'
::
""")
    names = [f"DUEM{i:03d}" for i in range(1, 6)]
    coords = dict(time=np.array(["2009-06-01"], dtype="datetime64[ns]"),
                  lat=[-45., 45.], lon=[0., 90., 180., 270.])
    xr.Dataset({name: xr.DataArray(np.full((1, 2, 4), i),
                dims=("time", "lat", "lon"), coords=coords)
                for i, name in enumerate(names, 1)}).to_netcdf(root / "surf" / "data.nc")
    model = Experiment(root, "200906", "200908", "JJA")
    assert [f["export"] for f in model.fields["surf"][:5]] == names
    assert all(f["source_export"] == "DUEM" for f in model.fields["surf"][:5])
    for i, name in enumerate(names, 1):
        assert float(model.get((name, "DU")).mean()) == i
    assert [(f["export"], f["alias"]) for f in model.fields["surf"][5:]] == [
        ("T", "temp"), ("A", "a"), ("B", "b")]
    output = tmp_path / "plan"
    assert main(["--source", str(root), "--collections", "surf",
                 "--begdate", "200906", "--enddate", "200908",
                 "--no-verification", "--variables", *names,
                 "--output", str(output)]) == 0
    tasks = json.loads((output / "plan.json").read_text())["tasks"]
    assert len(tasks) == 5


def test_mismatched_lists_still_rejected(tmp_path):
    path = tmp_path / "HISTORY.rc"
    path.write_text("COLLECTIONS:\n 'surf'\n::\nsurf.fields:\n 'A;B', 'X', 'a;b;c'\n::\n")
    with pytest.raises(ValueError, match="Ambiguous aliases"):
        history(path)
