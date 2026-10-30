#!/bin/csh -f
#SBATCH --time=08:00:00
#SBATCH --constraint=mil
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --account=g0620
#SBATCH --partition=preops
#SBATCH --qos=atmtest
#SBATCH --job-name=collections
#SBATCH --output=collections.%j.out

# One collection per Slurm job. Submit with:
# sbatch gcm_collections.j geosgcm_prog
# Or use submit_collections.csh for multiple separate jobs.
setenv GEOSUTIL /home/dbarahon/nobck/models/GEOSgcm/install
setenv GEOSBIN "$GEOSUTIL/bin"
source "$GEOSBIN/g5_modules"
setenv OMP_NUM_THREADS 1
setenv OPENBLAS_NUM_THREADS 1
setenv MKL_NUM_THREADS 1
set expdir = /home/dbarahon/nobck/DEV/v1102_MG3L91
if ( $#argv != 1 ) then
    echo "Usage: sbatch gcm_collections.j COLLECTION_NAME"
    exit 2
endif
set collection = "$argv[1]"
set season = JJA
set begdate = 200906
set enddate = 200908
set workers = 8
set levels = 850,500,250
# Zonal means are enabled by default. To omit them, add --no-zonal.
# Surface/2D fields are included by default; --exclude-2d omits them.
set run = "$expdir/plot/collections_${season}_${collection}_${SLURM_JOB_ID}"
set script = "$SLURM_SUBMIT_DIR/collection_quickplot.py"
if ( ! -f "$script" ) then
    echo "Submit from the collection_quickplot directory"
    exit 2
endif
python3 "$script" --source "$expdir" --geosutil "$GEOSUTIL" \
    --collections "$collection" --season "$season" \
    --begdate "$begdate" --enddate "$enddate" \
    --levels "$levels" --output "$run" --workers "$workers" --execute
exit $status
