#!/bin/csh -f
# Run from the repository root with cloudnet311 activated and GEOSUTIL set.
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
set unify_folder = "$experiment/pyPlots-CLIM"  # Empty disables collection.
set coastlines = ""              # Optional offline .shp file.
set isccp_begdate = ""           # Empty tries model dates, then available seasonal climatology.
set isccp_enddate = ""
set isccp_climatology = 0
set srb_begdate = 198307
set srb_enddate = 200506
set srb_climatology = 1          # Explicit older-period climatology for SRB.
# Other optional arguments belong here, not on the command line.
# Example: ( --climatology --compare-begdate 200806 --compare-enddate 200808 )
set extra_options = ()

# Collect existing seasonal plots locally; no Slurm job or replotting needed.
if ( "$unify_folder" != "" ) then
    python3 unify_plots.py --experiment "$experiment" --season "$season" --destination "$unify_folder"
    if ( $status != 0 ) exit 1
endif
if ( ! $?GEOSUTIL ) then
    echo "Set GEOSUTIL to your GEOS install directory first."
    exit 2
endif
set verification_dir = "$GEOSUTIL/plots/VERIFICATION_RCS"
set verification_root = "/discover/nobackup/projects/gmao/share/gmao_ops/verification"
# --------------------------------------------------------------------

if ( $#argv != 0 ) then
    echo "Edit the settings in launch_jja.csh, then run without arguments."
    exit 2
endif
if ( ! -f gcm_python.j || ! -f run.py ) then
    echo "Run this launcher from the repository root."
    exit 2
endif

set options = ( --dpi "$dpi" --difference-percentile "$difference_percentile" )
if ( $special_plots == 1 ) set options = ( $options:q --special-plots )
if ( "$unify_folder" != "" ) set options = ( $options:q --unify-plots "$unify_folder" )
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
