#!/bin/csh -f
#SBATCH --time=08:00:00
#SBATCH --constraint=mil
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=64G
#SBATCH --account=g0620
#SBATCH --partition=preops
#SBATCH --qos=atmtest
#SBATCH --job-name=python_quickplot
#SBATCH --output=python_quickplot.%j.out

# Submit from python_quickplot/ with the Python environment already activated.
# sbatch gcm_python.j /path/to/experiment geosgcm_surf [additional CLI options]
if ( $#argv < 2 ) then
    echo "Usage: sbatch gcm_python.j EXPERIMENT COLLECTION [options]"
    exit 2
endif
set source = "$argv[1]"
set collection = "$argv[2]"
shift argv
shift argv
setenv OMP_NUM_THREADS 1
setenv OPENBLAS_NUM_THREADS 1
setenv MKL_NUM_THREADS 1
set season = JJA
set begdate = 200906
set enddate = 200908
set output = "$source/plot/python_${season}_${collection}_${SLURM_JOB_ID}"
python3 "$SLURM_SUBMIT_DIR/run.py" --source "$source" \
    --collections "$collection" --season "$season" \
    --begdate "$begdate" --enddate "$enddate" --levels 850,500,250 \
    --output "$output" --execute $argv:q
exit $status
