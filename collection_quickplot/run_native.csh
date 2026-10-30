#!/bin/tcsh -f
# Run one numbered GEOS portrait recipe in an isolated work directory.
# Args: GEOSUTIL SOURCE HISTORYRC GRADSX EXPID PLOTID OUTPUT SEASON
if ( $#argv != 8 ) exit 2
setenv GEOSUTIL "$argv[1]"
setenv SOURCE "$argv[2]"
setenv HISTORYRC "$argv[3]"
set gradsx = "$argv[4]"
set expid = "$argv[5]"
set plotid = "$argv[6]"
set output = "$argv[7]"
set season = "$argv[8]"

"$GEOSUTIL/plots/configure"
if ( $status != 0 || ! -f .quickplotrc ) exit 2
source .quickplotrc
if ( $status != 0 ) exit 2
if ( "$gradsx" == "auto" ) then
    if ( ! $?GRADS ) exit 127
    set gradsx = "$GRADS"
endif
setenv CMPEXP_ONLY FALSE
setenv ANALYSIS false
setenv CLIMATE false
setenv STD_DEV false
setenv TAYLOR false
setenv BEGDATE "$TBEG"
setenv ENDDATE "$TEND"
setenv SEASONS "$season"
setenv LONSENV "0 360"
setenv LATSENV "-90 90"
setenv CINTDIFF ON
setenv DDFFILE NULL

# QuickPlot defaults to the operational MERRA-2 and ERA5 comparisons when
# those locations actually exist at this GEOS site.
set comparisons = ()
if ( $?VERIFICATION ) then
    if ( -d "$VERIFICATION/MERRA2_MEANS" ) set comparisons = ( $comparisons "$VERIFICATION/MERRA2_MEANS:A" )
    if ( -d "$VERIFICATION/ERA5_Monthly" ) set comparisons = ( $comparisons "$VERIFICATION/ERA5_Monthly:V" )
endif
if ( $?CMPEXP ) then
    if ( "$CMPEXP" != "" && "$CMPEXP" != "NULL" ) then
        set comparisons = ( $comparisons $CMPEXP )
    endif
endif
setenv CMPEXP "$comparisons NULL"

if ( ! -f "$GEOSUTIL/plots/chckhist.new" ) exit 2
/bin/cp "$GEOSUTIL/plots/chckhist.new" chckhist

# An optional, locally patched genplot.gs lives in the current task directory.
# It takes precedence over GEOSUTIL without modifying the installed scripts.
if ( $?GASCRP ) then
    setenv GASCRP "${cwd}:$GASCRP"
else
    setenv GASCRP "${cwd}:$GEOSUTIL/plots/grads_util"
endif
echo "Native QuickPlot recipe: $plotid; GrADS: $gradsx"
tcsh -f "$GEOSUTIL/plots/portrait.script" \
    -expid "$expid" -source "$SOURCE" -plot "$plotid" \
    -output "$output" -geosutil "$GEOSUTIL" -grads "$gradsx" \
    -batch -season "$season"
exit $status
