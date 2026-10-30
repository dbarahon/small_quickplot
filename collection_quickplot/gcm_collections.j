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

# Edit these settings; submit from this folder with sbatch gcm_collections.j.
setenv GEOSUTIL /home/dbarahon/nobck/models/GEOSgcm/install
setenv GEOSBIN "$GEOSUTIL/bin"
source "$GEOSBIN/g5_modules"
setenv OMP_NUM_THREADS 1
setenv OPENBLAS_NUM_THREADS 1
setenv MKL_NUM_THREADS 1
set expdir = /home/dbarahon/nobck/DEV/v1102_MG3L91
set collections = ( geosgcm_prog geosgcm_moist geosgcm_cloudnumber )
set season = JJA
set begdate = 200906
set enddate = 200908
set workers = 8
set levels = 850,500,250
# Zonal means are enabled by default. To omit them, add --no-zonal.
# To include surface/2D fields, add --include-2d.
set run = "$expdir/plot/collections_${season}_${SLURM_JOB_ID}"
set script = "$SLURM_SUBMIT_DIR/collection_quickplot.py"
if ( ! -f "$script" ) then
    echo "Submit from the collection_quickplot directory"
    exit 2
endif
python3 "$script" --source "$expdir" --geosutil "$GEOSUTIL" \
    --collections $collections --season "$season" \
    --begdate "$begdate" --enddate "$enddate" \
    --levels "$levels" --output "$run" --workers "$workers" --execute
exit $status
