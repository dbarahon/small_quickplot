QUICKPLOT SMALL PROFILE — 31 tasks

Contents
  MASTERLIST.small: reduced commands for the uploaded experiment, JJA 2009 ONLY.
  MASTERLIST.small.mapping.txt: exact selected mapping lines for review.
  filter_quickplot.py: reusable Python 3 standard-library filter; submits nothing.

Selection
  7 zonal comparisons: U, T, Q, RH2, OMEGA, QLTOT, QITOT.
  3 horizontal dynamics: SLP, U850, U200.
  6 TOA radiation diagnostics: OSR, SW CRE, total CRE, OLR, LW CRE, net TOA.
  1 total aerosol extinction optical depth.
  3 precipitation diagnostics: total, convective/anvil, large-scale.
  3 column-water diagnostics: LWP, TPW, TQI.
  4 cloud fractions: low, middle, high, total (ISCCP reference).
  4 time-series tasks: radiation, surface pressure, precipitation-minus-evaporation,
    total precipitable water.

Taylor numbering
  The uploaded mapping reserves PORTRAIT.15–37 for Taylor tasks. The inspected
  driver skips those numbering increments when -taylor FALSE is used at runtime.
  The reduced list sets -taylor TRUE to preserve those IDs, but selects NO Taylor
  tasks. Do not add -cmpexp_only or -cmpops_only: these also affect dispatch.
  The actual installed portrait driver has not been supplied; this workaround
  assumes the control flow matches the repository version inspected.

Use in a csh terminal, after unpacking in your experiment's plot directory
  python3 filter_quickplot.py MASTERLIST portrait.list landscape.list MASTERLIST.next

The filter matches diagnostic commands, not fixed numerical IDs; it fails if any
selected mapping is absent or ambiguous. It preserves dates and paths from the
input list. Run it against each freshly generated list and matching mappings.
Use a new output filename each time. It never overwrites an existing output.

For the supplied JJA 2009 list ONLY, submission is:
  set expdir = /home/dbarahon/nobck/DEV/v1102_MG3L91
  $GEOSUTIL/post/gcmpost.script -source $expdir -plots JJA -begdate 200906 -enddate 200908 -list $expdir/plot/MASTERLIST.small

That command submits batch jobs; confirm your installed gcmpost.script supports
-list. Do not launch alongside the original full queue. MASTERLIST is a reference
copy; active workers consume LIST_<timestamp>. Editing MASTERLIST alone does not
alter an active queue. Never edit a queue while workers consume it.

For automatic runs, filter the generated LIST_<timestamp> BEFORE submission in an
experiment-local launcher. A recurring hook must filter the fresh list, not reuse
the fixed-date MASTERLIST.small. No shared GEOS installation changes are needed.
Until that hook is installed, PLOT_STATUS: OFF in the experiment plot.rc disables
automatic plotting; manual -plots overrides it in the inspected launcher.

Validation
  6,422 unique input commands; 31 selected, each mapped exactly once.
  No residual, diurnal, Taylor, or automatic miscellaneous tasks selected.
  This is 99.52% fewer tasks, not a predicted runtime reduction or image count.
  Multiple reference datasets/images may still be produced inside each task.
  Static filtering verified; GrADS, NetCDF data and HPC execution not available here.
