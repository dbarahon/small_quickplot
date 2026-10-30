#!/bin/csh -f
# Run from python_quickplot/ with cloudnet311 activated and GEOSUTIL set.
# Edit settings here, then run: tcsh launch_jja.csh

# --------------------------- Run settings ---------------------------
set experiment = /gpfsm/dnb34/dbarahon/DEV/v1102_MG3L91
set compare_experiment = ""   # Reference experiment root; empty disables comparison.
# Example: set compare_experiment = "/gpfsm/dnb34/dbarahon/DEV/reference_run"
set collections = ( geosgcm_surf geosgcm_prog geosgcm_moist geosgcm_aercloud )
set season = JJA
set begdate = 200906
set enddate = 200908
set levels = "850,500,250"
set variables = ()           # Empty = all; example: ( precip toa_radz )
set do_verification = 1      # 1 = observations enabled; 0 = disabled
set do_zonal = 1
set save_fields = 0
# Other optional arguments belong here, not on the command line.
# Example: ( --climatology --compare-begdate 200806 --compare-enddate 200808 )
set extra_options = ()

if ( ! $?GEOSUTIL ) then
    echo "Set GEOSUTIL to your GEOS install directory first."
    exit 2
endif
set verification_dir = "$GEOSUTIL/plots/VERIFICATION_RCS"
set verification_root = "$GEOSUTIL/plots/VERIFICATION"
# --------------------------------------------------------------------

if ( $#argv != 0 ) then
    echo "Edit the settings in launch_jja.csh, then run without arguments."
    exit 2
endif
if ( ! -f gcm_python.j || ! -f run.py ) then
    echo "Run this launcher from the repository's python_quickplot directory."
    exit 2
endif

set options = ( --season "$season" --begdate "$begdate" --enddate "$enddate" --levels "$levels" )
if ( "$compare_experiment" != "" ) then
    set options = ( $options:q --compare "$compare_experiment" )
endif
if ( $#variables > 0 ) then
    set options = ( $options:q --variables $variables:q )
endif
if ( $do_verification == 0 ) set options = ( $options:q --no-verification )
if ( $do_zonal == 0 ) set options = ( $options:q --no-zonal )
if ( $save_fields == 1 ) set options = ( $options:q --save-fields )

foreach collection ( $collections )
    sbatch --job-name="py_${collection}" gcm_python.j \
        "$experiment" "$collection" \
        --geosutil "$GEOSUTIL" \
        --verification-dir "$verification_dir" \
        --verification-root "$verification_root" $options:q $extra_options:q
    if ( $status != 0 ) exit 1
end
