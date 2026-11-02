# Python QuickPlot

A Python utility for plotting and comparing NASA GEOS model output, including observational verification. No GrADS required.

## Setup

From the repository root, with your Python environment activated:

```csh
python3 -m pip install -r requirements.txt
```

Set `GEOSUTIL` to your GEOS utilities directory. Verification resource files are read from `$GEOSUTIL/plots/VERIFICATION_RCS`; observation data may require an explicit `--verification-root`.

## Run with Slurm (recommended on Discover)

Edit `launch_jja.csh` to set the experiment, season, collections, dates, comparison experiments and output options. Then run from the repository root:

```csh
tcsh launch_jja.csh
```

The launcher submits `gcm_python.j` jobs for selected collections. Set `unify_folder` in the launcher to collect figures in one directory. Set `special_plots = 1` to include profiles, QBO and vortex plots.

## Run directly

```csh
python3 run.py --source /path/to/experiment \
    --collections geosgcm_surf --season JJA \
    --begdate 200906 --enddate 200908 \
    --geosutil "$GEOSUTIL" \
    --verification-root /path/to/VERIFICATION \
    --output /path/to/new_run --execute
```

Use a new `--output` directory for each run. Figures go into `plots/`, with `summary.json` and logs alongside. Omit `--execute` to preview the planned diagnostics.

Useful options:

- `--variables T:DYN precip toa_radz` selects individual variables or diagnostics.
- `--levels 850 500 250` selects pressure levels; `--no-zonal` omits zonal sections.
- `--compare /path/to/other/experiment` adds a model comparison (repeatable).
- `--no-verification` runs without observational verification.
- `--config example_config.json` provides custom input mappings (edit example paths first).
- `--save-fields` saves plotted arrays as NetCDF for inspection.
- `--coastlines /path/to/ne_110m_coastline.shp` enables offline coastlines.

For additional options, run `python3 run.py --help`.

## Tests

`pytest` is optional and is not included in the runtime dependencies:

```csh
python3 -m pip install pytest
python3 -m pytest tests -q
```

## Notes

The code reads GEOS HISTORY metadata and supports standard pressure-level fields. Verification uses the installed VERIFICATION resource catalog, with MERRA-2/ERA5 handling. Unavailable comparisons and errors are reported in `summary.json` and logs. No original GEOS QuickPlot files are modified.
