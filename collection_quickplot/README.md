# Collection QuickPlot

Standalone GEOS collection plotting tool. No dependency on `small_quickplot`.
Uses the installed GEOS_Util GrADS plotting scripts (hcmp2, progz) and `plots/configure` to initialize their runtime environment. It reads **collections** (`geosgcm_prog`), **exports** (`QLTOT`), **components** (`AGCM`) and **NetCDF aliases** (`QL`) from `HISTORY.rc`.

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

`--collections` accepts a space-delimited list, e.g. `--collections geosgcm_prog geosgcm_moist`, comma-delimited values, or `--collections all` for all enabled collections. Only selected collections are dispatched. By default one `hcmp2` request at level 1000 is produced per field. Add `--levels 850,500,250` for additional level-specific `hcmp2` requests and `--zonal` to attempt `progz` zonal plots. Avoid enabling these indiscriminately for purely surface fields. Worker count defaults to 8; override with `--workers N`.

## Limitations

- This is an initial site-testable implementation. **No Discover/GrADS end-to-end run has been performed.** GEOS `configure` may need additional environment initialization specific to your installation.
- `HISTORY.rc` lists exports and aliases but does **not** reliably establish whether each field has a vertical dimension. The default plot uses `hcmp2` with level 1000; this may not be available for all 3D data. Specify `--levels` selectively; the current tool does not auto-classify levels.
- The installed `getvar` helper indexes exports by component, not output collection. If the same `VARIABLE:COMPONENT` is found in multiple enabled collections, the tool aborts rather than silently using the wrong one. Truly arbitrary collection-isolated plots require additional changes to the underlying `getvar` machinery or a NetCDF-based back end.
- Some `hcmp2` behavior depends on collection-specific scale factors and preprocessing. Review logs and generated images. A zero exit code does not guarantee an image was produced.
- GEOS `configure` and the plotting scripts are invoked inside individual isolated working directories. The script does not alter the installed GEOS repository.

Sources inspected: GEOS-ESM/GEOS_Util tag `v3.0.2` (`plots/quickplot`, `plots/portrait.script`, `plots/grads_util/genplot.gs`, `plots/grads_util/gencmp.gs`, and `plots/configure`).

## GrADS executable and cleanup

The default `--gradsx auto` uses `$GRADS` chosen by the installed `GEOSUTIL/plots/configure` script (usually `grads` on Discover); `gradsnc4` is no longer assumed. Use `--gradsx /full/path/to/executable` to override. After a successful subprocess exit, task logs are copied into `output/logs/COLLECTION/` and task work directories are deleted. Failed or timed-out tasks retain their working directories and `run.log` for debugging. Use `--keep-workdirs` to retain everything. Verify produced images: GrADS may exit successfully even when rendering fails.

## Initialization failure troubleshooting

The GEOS GrADS scripts expect `DDFFILE` to be defined even if no DDF is supplied. The launcher now exports `DDFFILE=NULL`, matching upstream QuickPlot's sentinel convention. GrADS may exit zero after a script error; the runner scans the log for common errors and validates **one task first** before queuing the rest. If this preflight fails, `summary.json` and that task's `run.log` remain, without creating another full set of task directories. Each task still initializes its own GEOS environment, so plotting a large collection can be slow and create many `.rcx`/temporary files. The next performance improvement would be sharing initialization among tasks within a worker, which is not implemented yet. Cancel a stalled old run using `scancel JOBID` before resubmitting.

## GEOS plotting dispatch (PR #4)

The package now invokes the installed `$GEOSUTIL/plots/hcmp/hcmp2` for map and pressure-level tasks, and `$GEOSUTIL/plots/zcmp/progz` for zonal tasks. Those are the legacy scripts used by GEOS `portrait.script`, including the previously successful U:DYN zonal diagnostic. The standard GEOS `g5_modules` and `configure` GrADS executable remain authoritative; no NetCDF writer patches or external GrADS module are used.

`hcmp2` requires a level argument, so default maps pass `1000`; this does **not** establish that each variable is defined at 1000 hPa. Some fields and collection-only diagnostics will need field-aware level selection or plotting-resource definitions. `CMPEXP_ONLY` is FALSE because the upstream `hcmp2` returns early when TRUE and no comparison plots are requested. For runs with no explicit comparison experiment, whether installed GEOS verification resources produce graphics must still be established on Discover. A task is now considered successful only when new GIF output is detected, in addition to a clean GrADS log.

This is committed but not yet tested end-to-end on Discover. Try a small collection or specific known field before a large run.
