#!/bin/csh -f
# Run from python_quickplot/ with cloudnet311 activated and GEOSUTIL set.
# Additional arguments are passed to every collection job.
set experiment = /gpfsm/dnb34/dbarahon/DEV/v1102_MG3L91
set collections = ( geosgcm_surf geosgcm_prog geosgcm_moist geosgcm_aercloud )

if ( ! $?GEOSUTIL ) then
    echo "Set GEOSUTIL to your GEOS install directory first."
    exit 2
endif
if ( ! -f gcm_python.j || ! -f run.py ) then
    echo "Run this launcher from the repository's python_quickplot directory."
    exit 2
endif

# Override with --verification-root if the data live elsewhere.
set verification = "$GEOSUTIL/plots/VERIFICATION"

foreach collection ( $collections )
    sbatch --job-name="py_${collection}" gcm_python.j \
        "$experiment" "$collection" \
        --season JJA --begdate 200906 --enddate 200908 \
        --geosutil "$GEOSUTIL" \
        --verification-dir "$GEOSUTIL/plots/VERIFICATION_RCS" \
        --verification-root "$verification" $argv:q
    if ( $status != 0 ) exit 1
end
