#!/bin/csh -f
# Submit a separate Slurm job for each requested HISTORY.rc collection.
# Usage:
#   tcsh submit_collections.csh
#   tcsh submit_collections.csh geosgcm_prog geosgcm_surf

if ( ! -f gcm_collections.j ) then
    echo "Run this script from the collection_quickplot directory."
    exit 2
endif

if ( $#argv > 0 ) then
    set collections = ( $argv )
else
    set collections = ( geosgcm_prog geosgcm_moist geosgcm_surf geosgcm_aercloud )
endif

foreach collection ( $collections )
    echo "Submitting $collection"
    sbatch --job-name="col_$collection" \
          --output="collections.$collection.%j.out" \
          gcm_collections.j "$collection"
    if ( $status != 0 ) then
        echo "ERROR: sbatch submission failed for $collection"
        exit 1
    endif
end
