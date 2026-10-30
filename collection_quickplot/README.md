# Collection QuickPlot

Collection-driven GEOS plotting with the installed GEOS_Util/GrADS runtime.
Fields and aliases come from the experiment's `HISTORY.rc`. The program
inspects representative NetCDF files to distinguish 3D and 2D variables.
It leaves all successful image products in **one flat `plots/` directory**.

## Run on Discover

Edit `gcm_collections.j` to set the experiment, `GEOSUTIL`, selected
collections, dates, season, and levels. Submit from this directory:

```csh
sbatch gcm_collections.j
```

Default selection:
- 3D horizontal maps at **850, 500, and 250 hPa**.
- Model-only latitude-pressure zonal sections for 3D fields.
- Surface/2D maps and latitude-profile line plots.
- Model-only four-panel TOA radiation diagnostic when OLR, OLC, RSR, RSC are available.
- Eight concurrent GrADS tasks.

To override in an interactive compute allocation:

```csh
python3 collection_quickplot.py \
  --source /path/to/experiment --geosutil "$GEOSUTIL" \
  --collections geosgcm_prog geosgcm_moist geosgcm_cloudnumber \
  --season JJA --begdate 200906 --enddate 200908 \
  --levels 850,500,250 --workers 8 \
  --output /path/to/new/collections_JJA_run --execute
```

`--levels 850,500,250,100` adds 100 hPa. `--no-zonal` omits zonal
mean diagrams, and `--exclude-2d` omits surface maps and line profiles.
Use `--collections all` to choose all enabled HISTORY collections,
and `--compare /path/to/other/experiment` (repeatable) for GEOS
horizontal comparison plots. Omit `--execute` to produce only a plan.

The output directory must not already exist. Output structure:

```text
collections_JJA_run/
  plots/          # Every successful PNG/GIF, names prefixed with collection/field/level
  logs/           # One GrADS log per attempted task
  plan.json       # Planned tasks and skipped fields
  summary.json    # Outcomes and image paths
```

Temporary per-task work areas are deleted unless `--keep-workdirs`
is specified, including after failures; logs are always retained. Even if a
GEOS process reports a later error, any completed panels are retained and the
task is marked `partial`. Native GEOS panel names are included in the flat
output filenames to identify comparison datasets and plot types.
Task-specific image directories prevent cross-task image attribution.

## Plotting

Without explicit `--compare`, horizontal maps use the local
`model_map.gs`: GEOS `getvar`, time averaging, map styling, a shaded
color key, and PNG output. This is necessary because GEOS `hcmp2`
may refuse to plot a variable without matching comparison/verification
resources. When `--compare` is given, horizontal panels use the installed
`plots/hcmp/hcmp2`. Without explicit comparisons, zonal sections and latitude-profile lines use
`model_zonal.gs`, avoiding the requirement for a comparison experiment.
With explicit comparisons, 3D zonal products use installed
`plots/zcmp/progz`. Individual surface fields still use the model-only
line renderer. Where OLR:IRRAD, OLC:IRRAD, RSR:SOLAR, and RSC:SOLAR
are enabled, `model_radiation.gs` produces a model-only four-panel
`TOA_radz` latitude plot, following the structure of GEOS `olr_z`.
It is not an observational comparison: use the original GEOS radiation
workflow for that product.
The GEOS `plots/configure` runtime selects the appropriate OpenGrADS;
no custom GrADS module or `sdfwrite` is required.

NetCDF variable dimensions are read with Python `netCDF4`. The scan
looks at the first eight NetCDF files in each selected collection folder,
using the aliases from `HISTORY.rc`. Fields whose dimensions cannot
be established, or are not 2D/3D, are listed under `skipped` in
`plan.json`; they are **not** guessed to be 3D. The 2D/3D distinction
does not establish that values are defined at every selected pressure
level. Such cases appear as task failures in `summary.json`.

## Troubleshooting

If a task fails, inspect `summary.json`, followed by its named log under
`logs/`. GrADS can return exit status zero after an interpreter error,
so the runner checks the log and verifies that a graphic was created.
The normal `ga-> [EOF]` line at batch shutdown is **not** an error.

The model-only styling path and NetCDF classification still require
verification on Discover. In particular, locally installed GEOS GrADS
scripts may differ from the upstream version; compare a few representative
maps and zonal products before a large production run.
