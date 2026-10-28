# Small QuickPlot

Prepare and run a selected 31-task GEOS diagnostic profile **without a MASTERLIST**.
Everything is experiment-local; no edits to the shared GEOS installation are required.
Python 3 (standard library), csh/tcsh and a working GEOS QuickPlot installation are required.

## Prepare a run (csh)

From this repository directory, with the same GEOS modules/environment used by your
normal plotting jobs:

```csh
setenv GEOSUTIL /home/dbarahon/nobck/models/GEOSgcm/install
set expdir = /home/dbarahon/nobck/DEV/v1102_MG3L91
set rundir = $expdir/plot/small_JJA_2009

csh prepare_small_quickplot.csh \
    --source $expdir --season JJA \
    --begdate 200906 --enddate 200908 \
    --run-dir $rundir
```

Use a new run directory each time. Preparation sources the installed
`plots/.quickplotrc` and executes the drivers in **list-only mode** in that new
directory. It never calls `configure`, runs plots, or submits jobs. Enumeration
still scans the installed catalog/HISTORY, but no full MASTERLIST is required or
written. Monthly input files must already be available when plotting starts.

If the installed `.quickplotrc` is unavailable, use mapping files already generated
for the same experiment and installed drivers:

```csh
csh prepare_small_quickplot.csh \
    --source $expdir --season JJA \
    --begdate 200906 --enddate 200908 --run-dir $rundir \
    --portrait-map $expdir/plot/portrait.list \
    --landscape-map $expdir/plot/landscape.list
```

Preparation resolves diagnostic commands to IDs and fails if any selection is
missing or ambiguous. Review `$rundir/selected.mapping.txt` and `plan.json`.
Dates and experiment paths come from your arguments, not the bundled 2009 example.

## Run inside a compute allocation

Use your existing account/partition/module setup. The runner does not allocate
resources or submit jobs; do not launch it as a heavy job on a login node.

```csh
csh run_small_quickplot.csh $rundir/plan.json --workers 2 --timeout 1800
```

Alternatively, place that command (with full paths to this repository and the
plan) in a copy of your normal csh batch script, retaining its scheduler directives
and module setup but replacing the old plotting command. Request enough CPUs and
memory for the chosen worker count; the default is one worker. Submit that batch
script normally. Each worker calls the installed QuickPlot for one selected task.
This avoids the upstream shared `LIST_*` queue and its lock handling.

Outputs go to `$rundir/plots`, logs and task records to `$rundir/logs`, and a final
summary to `$rundir/summary.json`. A timeout stops the task process group. Nonzero
exits/timeouts are recorded, and other tasks continue. To skip previously
zero-return tasks and retry the rest:

```csh
csh run_small_quickplot.csh $rundir/plan.json --workers 2 --resume
```

A run-directory lock prevents concurrent runners. After a scheduler kill, verify
no runner is active before removing a stale `.runner-lock` directory. Resume uses
exit records, **not verified image completeness**: upstream QuickPlot can mask
errors and background converters. Review images/logs before accepting a run.
The wrapper does not fix these upstream rendering/completion limitations.

## Avoid launching the full suite too

For manual diagnostics, set `PLOT_STATUS: OFF` in your experiment's own `plot.rc`.
First check whether that file is a symlink to a shared default; if so, replace the
link with a private copy before editing. Do not modify the shared default.
This does not stop already queued jobs. Run the reduced suite after the required
monthly outputs are complete and the full suite is no longer active.

No automatic model-run hook is installed by this package. To integrate later,
call preparation followed by the runner in an experiment-owned diagnostic batch
job after monthly processing. Avoid modifying `gcm_post.j` blindly: it can run once
per collection, which could launch duplicate diagnostics.

## Selection and numbering

31 tasks: 7 zonal comparisons, 3 horizontal dynamics, 6 TOA radiation diagnostics,
1 total AOD, 3 precipitation, 3 column water, 4 cloud fraction, and 4 global
time-series diagnostics. See [README.txt](README.txt) for the complete selection.
One task may create multiple images or reference comparisons.

The inspected portrait driver counts 23 Taylor tasks in list-only mode but skips
those counter increments when `-taylor FALSE` is used. Generated commands use
`-taylor TRUE` to preserve IDs while selecting **no Taylor tasks**. Comparison-only
modes are deliberately not exposed. Default upstream MERRA-2/ERA5 comparisons
remain enabled. The four selected landscape tasks precede comparison-dependent
numbering. Driver hashes are checked before execution; regenerate the plan if the
installation changes. Installed control flow must match the inspected drivers.

## Existing MASTERLIST workflow

The original filter remains available:

```csh
python3 filter_quickplot.py MASTERLIST portrait.list landscape.list MASTERLIST.next
```

`MASTERLIST.small` and its mapping file are the specific JJA 2009 example. They
are not necessary for the new preparation/runner workflow.

## Validation

Selection was checked against the supplied 6,422-task catalog. Offline tests cover
preparation from mappings, 31-task selection, missing mappings, driver-change
rejection, worker failure, and timeout handling using a fake QuickPlot executable.
Actual csh enumeration, GrADS rendering, NetCDF input and HPC execution still
require a site test. The shared QuickPlot may invoke its own `configure` at runtime;
this package leaves that existing behavior unchanged.

## Ready-to-submit Discover batch script

`gcm_smallplot.j` adapts Donifan's existing csh batch environment for JJA 2009.
It retains `mil`, account `g0620`, partition `preops`, qos `atmtest`, GEOS modules,
and an eight-hour limit. It requests one task with two CPUs and 64 GiB memory;
the memory request is a starting estimate, not a measured requirement or a
verified partition policy. Increase it if accounting shows memory pressure.

```csh
cd /home/dbarahon/nobck/small_quickplot
git pull
sbatch gcm_smallplot.j
```

Submit from the repository directory: the script locates the package using
`SLURM_SUBMIT_DIR`. Edit `season`, `begdate`, `enddate`, and experiment paths for
another run. Each job creates a unique directory under `$EXPDIR/plot` using the
Slurm job ID. It prepares the plan and runs it within the same allocation.
The scheduler log is `smallplot.<jobid>.out` in the submission directory.

There is one `srun` controller, not 120 copies of the runner. Worker count follows
`SLURM_CPUS_PER_TASK` (two by default). Automatic web publication is omitted:
the existing publishing job may read a different output directory, and upstream
QuickPlot exit codes do not establish that every image is complete. Review the
new run directory before publishing. No existing experiment scripts are edited.
Actual csh/Slurm execution and site resource acceptance require a Discover test.
