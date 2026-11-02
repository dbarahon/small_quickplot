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

The launcher submits one `gcm_python.j` job per collection. Edit these settings:

| Setting | Purpose |
|---|---|
| `experiment`, `compare_experiment` | Model directory and optional comparison run (empty disables comparison). |
| `collections`, `variables` | Collections to plot; empty `variables` plots all available diagnostics. |
| `season`, `begdate`, `enddate` | Season and date range (`YYYYMM`). |
| `levels` | Pressure levels in hPa, e.g. `"850,500,250"`. |
| `do_verification`, `do_zonal` | Enable/disable observation comparisons and zonal sections (1/0). |
| `save_fields` | Save plotted arrays to NetCDF (1/0). |
| `dpi` | PNG resolution (default **100**). |
| `difference_percentile` | Difference color-scale range (95 by default; 100 for full range). |
| `special_plots` | Include profiles, QBO, and vortex plots (1/0). |
| `unify_folder` | Collect figures in one folder; empty disables collection. |
| `coastlines` | Optional offline coastline shapefile path. |
| `isccp_*`, `srb_*` | Optional verification date ranges and climatology switches. |
| `extra_options` | Additional CLI arguments. |

The launcher also sets `verification_dir` and `verification_root` for observation data.

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
- `--levels 850,500,250` selects pressure levels; `--no-zonal` omits zonal sections.
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
