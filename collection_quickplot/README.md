# Collection QuickPlot

Standalone GEOS collection plotting tool. No dependency on `small_quickplot`.
Uses the installed GEOS_Util GrADS plotting scripts (genplot, gencmp, progz) and `plots/configure` to initialize their runtime environment. It reads **collections** (`geosgcm_prog`), **exports** (`QLTOT`), **components** (`AGCM`) and **NetCDF aliases** (`QL`) from `HISTORY.rc`.

## Discover use

Edit `gcm_collections.j`: `GEOSUTIL`, experiment directory, `collections`, season and dates. Then submit **from this folder**:

```csh
sbatch gcm_collections.j
```

For an interactive plan-only check (safe on a login node):

```csh
python3 collection_quickplot.py --geosutil "$GEOSUTIL" \
  --source /path/to/experiment --collections geosgcm_prog geosgcm_moistdiag \
  --season JJA --begdate 200906 --enddate 200908 \
  --output /path/to/new/plan_directory
```

The tool writes `plan.json` without running any GrADS processes. Supply `--execute` **inside a compute allocation**. The output directory must not already exist.

To compare with one or more other GEOS experiments, add repeatable `--compare /path/to/other_experiment` options. The comparison format is the same `path:M` convention used by upstream QuickPlot; operational MERRA2/ERA5 datasets are *not* implicitly added. All output is organized under `output/COLLECTION/VARIABLE_COMPONENT_TYPE/`.

`--collections` accepts a space-delimited list, e.g. `--collections geosgcm_prog geosgcm_moist`, comma-delimited values, or `--collections all` for all enabled collections. Only selected collections are dispatched. By default one horizontal `genplot` request per field is produced. Add `--levels 850,500,250` for additional level-specific `gencmp` requests and `--zonal` to attempt `progz` zonal plots. Avoid enabling these indiscriminately for purely surface fields. Worker count defaults to 8; override with `--workers N`.

## Limitations

- This is an initial site-testable implementation. **No Discover/GrADS end-to-end run has been performed.** GEOS `configure` may need additional environment initialization specific to your installation.
- `HISTORY.rc` lists exports and aliases but does **not** reliably establish whether each field has a vertical dimension. The default plot uses `genplot` without `-LEVEL`; for 3D data this typically selects the first level. Specify `--levels` selectively; the current tool does not auto-classify levels.
- The installed `getvar` helper indexes exports by component, not output collection. If the same `VARIABLE:COMPONENT` is found in multiple enabled collections, the tool aborts rather than silently using the wrong one. Truly arbitrary collection-isolated plots require additional changes to the underlying `getvar` machinery or a NetCDF-based back end.
- Some `genplot` behavior depends on collection-specific scale factors and preprocessing. Review logs and generated images. A zero exit code does not guarantee an image was produced.
- GEOS `configure` and `genplot` are invoked inside individual isolated working directories. The script does not alter the installed GEOS repository.

Sources inspected: GEOS-ESM/GEOS_Util tag `v3.0.2` (`plots/quickplot`, `plots/portrait.script`, `plots/grads_util/genplot.gs`, `plots/grads_util/gencmp.gs`, and `plots/configure`).
