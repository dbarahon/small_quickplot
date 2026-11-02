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

# All scientific settings are passed by launch_jja.csh.
if ( $#argv < 6 ) then
    echo "Run tcsh launch_jja.csh after editing its settings."
    exit 2
endif
set source = "$argv[1]"
set collection = "$argv[2]"
set season = "$argv[3]"
set begdate = "$argv[4]"
set enddate = "$argv[5]"
set levels = "$argv[6]"
@ i = 0
while ( $i < 6 )
    shift argv
    @ i++
end
setenv OMP_NUM_THREADS 1
setenv OPENBLAS_NUM_THREADS 1
setenv MKL_NUM_THREADS 1
set output = "$source/plot/python_${season}_${collection}_${SLURM_JOB_ID}"
python3 "$SLURM_SUBMIT_DIR/run.py" --source "$source" \
    --collections "$collection" --season "$season" \
    --begdate "$begdate" --enddate "$enddate" --levels "$levels" \
    --output "$output" --execute $argv:q
exit $status
