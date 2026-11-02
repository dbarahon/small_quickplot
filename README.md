# Python QuickPlot

A standalone Python implementation of GEOS QuickPlot diagnostics. It does not invoke GrADS, modify installed GEOS tools, or compute Taylor diagrams.

## Install and run

Activate your usual Python environment, then from the repository root:

```csh
python3 -m pip install -r requirements.txt
python3 run.py --source /path/to/experiment \
    --collections geosgcm_surf --season JJA --begdate 200906 --enddate 200908 \
    --geosutil "$GEOSUTIL" --verification-root /path/to/VERIFICATION \
    --output /path/to/new_run --execute
```

`--output` must be a new directory, preventing mixing figures from different runs.
Omit `--execute` to write a plan without reading the collection data. All figures
are in one flat `plots/` directory. `summary.json` records every attempted product,
comparison months, map bias/RMSE and input provenance; `logs/` contains tracebacks.
`--save-fields` additionally saves rendered model/reference/difference arrays to
NetCDF for scientific checking. Missing or unsupported comparisons are reported
as `unavailable`; any unavailable comparison or failed model product yields exit 1.
Unmapped variable–dataset combinations are not attempted.

The default maps for pressure-dependent fields are 850, 500 and 250 hPa, plus a
latitude–pressure zonal section. Surface fields receive maps. Use `--levels`,
`--no-zonal`, or `--variables T:DYN CCN01 precip toa_radz` to select a small run.
Variables can be export names, export:component identifiers, or diagnostic names.
Read aliases and component identities from `HISTORY.rc`; use `--history` to override.
`.HOMDIR` is supported. Default file discovery searches each collection directory
recursively for `.nc`, `.nc4`, `.h5`; custom patterns are relative to the experiment.
Do not mix monthly and instantaneous files for the same variable in one pattern.

## Other experiments

Repeat `--compare /path/to/reference_experiment` as needed. Each reference uses
its own HISTORY aliases and source files. Comparisons cover raw variables,
pressure sections, derived fields, precipitation profiles and TOA radiation.
Each comparison has model, reference, and model-minus-reference panels with a
shared scale for the first two and a symmetric difference scale. Names of reference
directories must be distinct. No comparison changes the standalone model mean.

By default only matching year-months within the requested dates are compared.
For intentional comparisons between different periods, specify
`--compare-begdate YYYYMM --compare-enddate YYYYMM --climatology`. The latter
averages each source by calendar month before intersecting months. It also applies
to observations; set their dates with `--obs-begdate` / `--obs-enddate`.
This is useful for older SRB climatologies. Climatology mode is explicitly opt-in.

## Observational verification

The allowed dataset catalog comes only from `VERIFICATION.*.rc` in
`--verification-dir` (default `$GEOSUTIL/plots/VERIFICATION_RCS`), plus MERRA-2
and ERA5. No portrait-script enumeration or other native verification is used.
`--verification-root` replaces the `VERIFICATION/` prefix in resource filenames;
set it to the actual dataset directory on Discover. The fallback is
`$GEOSUTIL/plots/VERIFICATION`, which may not be the installed data location.

The parser preserves export/component mappings and numeric factors, including
multiple files in one resource, trailing commas and fraction scales. Both GrADS
NetCDF DSET descriptors (`.tabl`, `.ddf`) and regular float32 binary descriptors
(`.ctl`, or BIN `.tabl`) are read in Python. Binary support includes LINEAR/LEVELS
axes, endian options, missing values, yrev/zrev, and common date templates.
Sequential Fortran records, PDEF, headers/trailers, unusual templates and other
unsupported layouts fail with a precise log message. They need conversion to
NetCDF or an additional reader after inspecting the actual descriptor.

As in original QuickPlot, MERRA-2 is discovered automatically at
`verification_root/MERRA2_MEANS` using its HISTORY.rc (or .HOMDIR) and collection
files or xdf.tabl/ctl.tabl descriptors. ERA5_Monthly is tried the same way when
ERA5 has no RC entry. Missing directories or metadata are printed at startup.
Explicit resource files and config mappings take precedence. Add `--verification-rc /path/to/VERIFICATION.MERRA2.rc` (or
`VERIFICATION.MERRA-2.rc`). Extra resource files outside the catalog are accepted
only for MERRA-2 and ERA5. If either is unconfigured, startup prints a notice.

A JSON config can override selected catalog entries with NetCDF paths, without
expanding the allowed catalog. Example:

```json
{
  "verification": {
    "GPCP": {
      "TPREC:MOIST": {
        "path": "/data/gpcp/monthly*.nc",
        "variable": "precip", "scale": 1, "units": "mm/day"
      }
    }
  }
}
```

Pass with `--config config.json`. Values are `raw * scale + offset`. Units describe
the converted field, not the raw field. `example_config.json` illustrates file
patterns and MERRA-2 mappings; replace its placeholder paths before use. The
installed catalog must include GPCP for the example above to be accepted.
Use `--no-verification` for model-only or experiment-comparison tests.

## Diagnostics and conventions

| Name | Model definition | Verification |
|---|---|---|
| `precip` | CN_PRCP + LS_PRCP + AN_PRCP; fallback TPREC | Total precipitation, including GPCP and ERA5 |
| `lwp` | TQL:AGCM | LWP:MOIST, including MAC-LWP |
| `tlwp` | TQL:AGCM + TQR:AGCM | TLWP:AGCM, including MAC-LWP |
| `olrcf` | OLC − OLR | Same export formula |
| `osrcf` | RSC − RSR | Same export formula (GEOS sign) |
| `toacf` | OLC − OLR + OSRCLR − OSR | Same export formula |
| `toa_radz` | OLR/OLC, OLC−OLR, RSR/RSC, RSC−RSR | Four-panel latitude profiles |

Precipitation rates are converted from kg m−2 s−1 to mm/day using 86400;
accumulations with unknown intervals are rejected. Native observation TPREC
resource factors produce mm/day. NetCDF overrides should explicitly specify units.
The GEOS `osrcf` convention is clear minus all net SW; the native-style SW cloud-forcing panel in
`toa_radz` also uses clear minus all net SW. Both signs are labeled deliberately.
Cloud fractions and surface radiation are compared directly through resource
export mappings. Derived inputs may come from other enabled collections, with
selected-collection priority, then geosgcm_prog, then HISTORY order. Missing inputs
are reported; zero values are never substituted. Formula inputs must have identical
coordinates/timestamps. Arbitrary GrADS formulas are not executed or translated.

## Averaging, grids and presentation

Time means use equal sample weights within each calendar month, then equal
weights for available monthly means. This is appropriate for monthly QuickPlot
inputs; irregular instantaneous samples should first be reduced to monthly means.
Incomplete seasons are allowed and common month IDs are recorded. No daily-duration
weighting or confidence intervals are inferred. Missing cells are excluded.

Only rectilinear latitude–longitude grids and pressure levels with explicit Pa,
hPa or mb units are supported. Hybrid/model levels are rejected; preprocess them
to pressure levels. Linear pressure interpolation is used without extrapolation.
Zonal means use longitude-width weights and require global longitude coverage.
References are bilinearly interpolated onto the model grid, with a cyclic longitude
seam only for global reference coverage; out-of-domain cells remain missing.
This is **not conservative regridding**. Map bias/RMSE use latitude-band/longitude
cell-area weights on common valid cells. Zonal comparisons have no aggregate RMSE.

Figures use compact horizontal colorbars, contour overlays, readable scientific
multipliers, latitude labels and linear-pressure sections. Native `plot.rc` is not
parsed; automatic shared levels and the fixed precipitation scale replace its
variable-specific styling. No automatic coastline download occurs. For coastlines,
install Cartopy and pass `--coastlines /path/to/ne_110m_coastline.shp`.

## Launcher and Slurm

Edit `launch_jja.csh`, then run `tcsh launch_jja.csh` from the repository root.
The launcher owns dates, season, collections, levels, comparison experiment and
plot options. `gcm_python.j` is its worker; do not submit it with the old two-argument
command. Activate your Python environment and set GEOSUTIL before submitting.

- `dpi = 150`: resolution of every plot; set 300 for higher resolution.
- `difference_percentile = 95`: symmetric limits from the 95th percentile of
  absolute differences. Set 100 for full extrema. Values outside the range
  saturate at the colorbar ends; saved arrays and statistics are unchanged.
- `special_plots = 1`: adds prognostic vertical and latitude profiles, QBO and
  vortex plots. Set 0 to disable.
- `unify_folder = "$experiment/pyPlots-CLIM"`: collect existing plots from all
  `python_${season}*` run directories under the experiment's `plot/` or `plots/`
  directory immediately when the launcher starts. Each new job also moves its
  own plots there on completion. Empty disables collection. No separate mode or
  run list is needed. Run-name prefixes prevent overwrites; logs stay in place.
  To collect only, without submitting jobs, set `collections = ()` in the launcher.
- `coastlines`: optional offline coastline shapefile.
- Observations and operational reanalyses first use the requested dates. If
  no usable seasonal data overlap those dates, they use available seasonal
  climatology automatically. Notices and provenance record the fallback period;
  map and profile comparisons label climatology. Missing variables and malformed
  files remain explicit errors.
- ISCCP uses CLDLOW, CLDMID, CLDHI and CLDTOT, scaled by 0.01, for
  CLDLO, CLDMD, CLDHI and CLDTT respectively, as in GEOS VERIFICATION.ISCCP.rc.
  Find the four comparison maps with `*CLD*_SOLAR_map_vs_ISCCP.png`.
  Optional ISCCP/SRB date and climatology settings select an explicit historical
  period. Empty dates use the automatic policy above.
- Chronological QBO plots still require common actual dates: a climatology is
  not a substitute for interannual evolution.

The Slurm resource requests remain in `gcm_python.j`. One job processes one
collection serially; separate collection jobs run in parallel.

## Zonal mean prognostics

The special figures follow GEOS `plots/lcmp/lplt1`, `lplt2`, and
`plots/zcmp1/qbo` and `vortex` (v3.0.2 conventions). They use only configured
comparison sources; historical native comparison datasets are not added.

Vertical profiles are generated for T, U, V, Q and RH2, together with latitude
profiles at two pressure levels. T uses 85S, equator and 85N with log pressure.
U/V use fixed 30S, equator and 30N; Q uses 60S, equator and 60N; RH2 uses
85S, equator and 85N. These fixed choices deliberately avoid the original
extremum-following latitude selection for U/V/RH2. Reference profiles are paired
in time with the model. Regular latitude-pressure contour sections remain linear.

QBO plots use zonal wind averaged over 10S–10N and a logarithmic pressure axis.
Vortex plots use 50–70S, 0.1–100 hPa, September–April monthly climatologies,
with a thick zero contour and signed 15 m/s contours. Dotted zero contours of
mean ±1 standard deviation appear only where at least two years contribute.
Time plots load all available months between the launcher begin/end dates,
independently of the selected map season. Missing calendar months stay blank.
A JJA-only three-month input cannot make a vortex plot; choose a longer period
with September–April data. No observations are extrapolated beyond their levels
or dates, and chronological comparisons require common calendar months.

## Validation

Run `python3 -m pytest tests -q` from the repository root (pytest
is a test-only dependency). Tests generate independent tiny NetCDF experiments
and binary verification files, check formulas, aliases, units, time intersection,
cyclic interpolation, metrics, catalog restrictions, and complete plotting runs.
These tests do not establish numerical equivalence with Discover's QuickPlot.
Start with precipitation/GPCP, radiation/CERES, and one pressure-level temperature
comparison; inspect saved NetCDF differences alongside the original outputs.

Comparison figures use three stacked panels, a shared vertical model/reference
colorbar and a horizontal difference bar. Pressure axes are linear, with 100 hPa
ticks. Differences are absolute model minus reference; no relative-difference
mask is applied. Side annotations identify unweighted cell statistics; the JSON
comparison bias and RMSE retain area weighting. Coastlines use --coastlines or
an existing Cartopy 110m coastline cache; no network download is attempted.
Failure reasons are printed in the job output and recorded with tracebacks.
