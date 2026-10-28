#!/bin/csh -f
#SBATCH --time=8:00:00
#SBATCH --constraint=mil
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --job-name=MG3_smallplot
#SBATCH --account=g0620
#SBATCH --output=smallplot.%j.out
#SBATCH --partition=preops
#SBATCH --qos=atmtest

# Submit from the small_quickplot checkout: sbatch gcm_smallplot.j
# Memory is an initial request, not a measured requirement. Tune after one run.
umask 022
limit stacksize unlimited

setenv ARCH `uname`
setenv SITE NCCS
setenv GEOSBIN /home/dbarahon/nobck/models/GEOSgcm/install/bin
setenv GEOSUTIL /home/dbarahon/nobck/models/GEOSgcm/install
source "$GEOSBIN/g5_modules"
if ( $status != 0 ) exit 1
if ( ! $?LD_LIBRARY_PATH ) setenv LD_LIBRARY_PATH ""
if ( $?BASEDIR ) then
    setenv LD_LIBRARY_PATH "${LD_LIBRARY_PATH}:${BASEDIR}/${ARCH}/lib"
endif

# Keep the supplied site's MPI environment for any upstream utilities.
setenv I_MPI_ADJUST_ALLREDUCE 12
setenv I_MPI_ADJUST_GATHERV 3
setenv I_MPI_FABRICS shm:ofi
setenv I_MPI_OFI_PROVIDER psm3
setenv FI_PSM3_CONN_TIMEOUT 120
# Avoid each plotting process starting a separate multithreaded pool.
setenv OMP_NUM_THREADS 1
setenv MKL_NUM_THREADS 1
setenv OPENBLAS_NUM_THREADS 1
setenv NUMEXPR_NUM_THREADS 1
setenv MAGICK_THREAD_LIMIT 1

setenv EXPID v1102_MG3L91
setenv EXPDIR /home/dbarahon/nobck/DEV/v1102_MG3L91
setenv HOMDIR /home/dbarahon/nobck/DEV/v1102_MG3L91

# EDIT these three settings for a different diagnostic period.
set season = JJA
set begdate = 200906
set enddate = 200908

if ( ! $?SLURM_JOB_ID ) then
    echo "Submit with sbatch; do not run this batch script on a login node."
    exit 2
endif
# Slurm copies the script to spool, so use the submission directory, not $0:h.
set repo = "$SLURM_SUBMIT_DIR"
if ( ! -f "$repo/prepare_small_quickplot.py" ) then
    echo "Submit from the small_quickplot checkout directory."
    exit 2
endif
set workers = 2
if ( $?SLURM_CPUS_PER_TASK ) set workers = "$SLURM_CPUS_PER_TASK"
set rundir = "$EXPDIR/plot/small_${season}_${begdate}_${enddate}_${SLURM_JOB_ID}"
echo "Diagnostic run directory: $rundir"

# No MASTERLIST required. Uses installed verification RCs and a reduced profile.
# If enumeration lacks plots/.quickplotrc, append these options:
# --portrait-map $EXPDIR/plot/portrait.list --landscape-map $EXPDIR/plot/landscape.list
csh "$repo/prepare_small_quickplot.csh" \
    --source "$EXPDIR" --season "$season" \
    --begdate "$begdate" --enddate "$enddate" --run-dir "$rundir"
set prepare_rc = $status
if ( $prepare_rc != 0 ) then
    echo "Preparation failed; no plots launched."
    exit $prepare_rc
endif

# Exactly ONE controller, with two local workers by default.
# Never use the former 120-task srun invocation for this runner.
srun --nodes=1 --ntasks=1 --cpus-per-task=$workers \
    csh "$repo/run_small_quickplot.csh" "$rundir/plan.json" \
    --workers $workers --timeout 1800
set plot_rc = $status

echo "Plots:   $rundir/plots"
echo "Logs:    $rundir/logs"
echo "Summary: $rundir/summary.json"
echo "Runner exit status: $plot_rc"

# Publishing is intentionally manual: gcm_moveplot.j may read plots_CLIM,
# whereas this job writes a separate run directory. Inspect outputs first.
exit $plot_rc
