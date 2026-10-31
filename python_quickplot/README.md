# Python QuickPlot

An independent Python implementation alongside `collection_quickplot/`. It never
invokes GrADS, changes the installed GEOS tools, or computes Taylor diagrams.

## Install and run

Activate your usual Python environment, then from the repository root:

```csh
python3 -m pip install -r python_quickplot/requirements.txt
python3 -m python_quickplot --source /path/to/experiment \
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

## Slurm

Submit from `python_quickplot/`, with your Python environment already activated
and GEOSUTIL set. Adjust the season/date settings and Slurm resources in the script:

```csh
sbatch gcm_python.j /path/to/experiment geosgcm_surf \
    --verification-root /path/to/VERIFICATION --variables precip toa_radz
sbatch gcm_python.j /path/to/experiment geosgcm_prog \
    --compare /path/to/reference --no-verification --variables T:DYN
```

One job processes one collection serially, with cached file inventories and
bounded field caches. Submit separate jobs for parallel collections. Large
multi-year 3-D fields can still require substantial memory; use monthly files and
short validation periods first. The implementation does not yet stream seasonal
sums or use distributed execution.

## Validation

Run `python3 -m pytest python_quickplot/tests -q` from the repository root (pytest
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
