# Small QuickPlot

Prepare a reduced GEOS QuickPlot plan and run it inside an existing Slurm allocation. Requires Python 3, csh/tcsh, and GEOS QuickPlot. Does not submit jobs or change the installed GEOS utilities.

## Run (csh)

```csh
setenv GEOSUTIL /path/to/GEOSgcm/install
set expdir = /path/to/experiment
set rundir = $expdir/plot/small_JJA_2009

csh prepare_small_quickplot.csh --source $expdir --season JJA \
    --begdate 200906 --enddate 200908 --run-dir $rundir
csh run_small_quickplot.csh $rundir/plan.json --workers 2 --timeout 1800
```

Preparation generates `plan.json` and `selected.mapping.txt` for inspection. It uses installed portrait/landscape drivers in list-only mode; if that is unavailable, pass both `--portrait-map FILE` and `--landscape-map FILE`. Use a new run directory for every preparation.

## Reference datasets

The tool reads `$GEOSUTIL/plots/VERIFICATION_RCS/VERIFICATION.*.rc` and only selects diagnostics whose **explicit** `-RC` reference is listed there; MERRA2/MERRA-2 is also allowed. Override the directory with `--verification-dir DIR`.

Your current directory lists CERES_EBAF-TOA_Ed4.0, ERA5, GPCP, ISCCP, MAC-LWP and SRB.

**Limitation:** GEOS QuickPlot can produce implicit reference comparisons inside a single mapped task. This utility cannot guarantee filtering *those internal comparisons* without inspecting/changing your installed QuickPlot scripts. It does not edit the shared reference catalogs or claim that unavailable references have been disabled internally.

## Include variables from a collection

```csh
csh prepare_small_quickplot.csh --source $expdir --season JJA \
    --begdate 200906 --enddate 200908 --run-dir $rundir \
    --collection GOCART --variable TOTEXTTAU:GOCART
```

Repeat `--collection COLLECTION` to include all mapped `genplot` diagnostics exporting that collection; repeat `--variable VAR:COLLECTION` to select a specific mapped export. Additional diagnostics must exist in the installed portrait/landscape mappings. A missing requested variable is an error rather than an invented or invalid task ID. The default 31-diagnostic profile remains selected.

## Batch jobs and results

`gcm_smallplot.j` is an example Slurm csh batch file. Edit its environment, experiment, dates and resources and submit from this repository with `sbatch gcm_smallplot.j`. Only one runner process should be launched, with `--workers` controlling task parallelism. Never run heavy plots on the login node.

Outputs: `$rundir/plots`; task logs and status: `$rundir/logs`; summary: `$rundir/summary.json`. To retry failed or timed-out jobs while skipping successful return codes:

```csh
csh run_small_quickplot.csh $rundir/plan.json --workers 2 --resume
```

Review plots and logs: upstream QuickPlot may return success despite rendering failures. If the installed plot drivers have changed, prepare a new plan.

## Execution order and condensate hdiag

The queue puts TOA radiation and the global radiation time series first, followed by horizontal cloud fraction, LWP and TQI plots. Mapped `hdiag_*` plots of liquid/ice condensate (such as QLTOT and QITOT) follow, with the remaining diagnostics afterward. Matching is based on the installed drivers and no plot IDs are assumed. If no matching `hdiag_*` command is exposed, preparation prints a warning and proceeds with the available diagnostics. Parallel workers may finish in a different order from the submission queue.
