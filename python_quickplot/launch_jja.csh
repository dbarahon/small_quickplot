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
set dpi = 150                   # Increase to 300 for publication/export.
set difference_percentile = 95   # 100 = full range; smaller emphasizes differences.
set special_plots = 1           # Profiles, QBO and vortex (needs Sep-Apr data).
set unify_plots = ""             # Destination directory; empty keeps per-job plots.
set launch_mode = submit         # submit or unify (move already completed plots)
set completed_runs = ( )         # For unify mode: ( /path/to/run1 /path/to/run2 )
set coastlines = ""              # Optional offline .shp file.
set isccp_begdate = ""           # Empty uses model dates; inspect logs if unavailable.
set isccp_enddate = ""
set isccp_climatology = 0
set srb_begdate = 198307
set srb_enddate = 200506
set srb_climatology = 1          # Explicit older-period climatology for SRB.
# Other optional arguments belong here, not on the command line.
# Example: ( --climatology --compare-begdate 200806 --compare-enddate 200808 )
set extra_options = ()

if ( "$launch_mode" == "unify" ) then
    if ( "$unify_plots" == "" || $#completed_runs == 0 ) then
        echo "Set unify_plots and completed_runs for unify mode."
        exit 2
    endif
    python3 unify_plots.py --destination "$unify_plots" $completed_runs:q
    exit $status
endif
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

set options = ( --dpi "$dpi" --difference-percentile "$difference_percentile" )
if ( $special_plots == 1 ) set options = ( $options:q --special-plots )
if ( "$unify_plots" != "" ) set options = ( $options:q --unify-plots "$unify_plots" )
if ( "$coastlines" != "" ) set options = ( $options:q --coastlines "$coastlines" )
if ( "$isccp_begdate" != "" && "$isccp_enddate" != "" ) then
    set options = ( $options:q --verification-period "ISCCP:${isccp_begdate}:${isccp_enddate}" )
endif
if ( $isccp_climatology == 1 ) set options = ( $options:q --verification-climatology ISCCP )
if ( $srb_climatology == 1 ) then
    set options = ( $options:q --verification-period "SRB:${srb_begdate}:${srb_enddate}" --verification-climatology SRB )
endif
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
        "$experiment" "$collection" "$season" "$begdate" "$enddate" "$levels" \
        --geosutil "$GEOSUTIL" \
        --verification-dir "$verification_dir" \
        --verification-root "$verification_root" $options:q $extra_options:q
    if ( $status != 0 ) exit 1
end
