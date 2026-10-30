#!/bin/tcsh -f
# Isolated working directory is required: configure and GrADS write local files.
if ( $#argv != 5 ) exit 2
setenv GEOSUTIL "$argv[1]"
setenv SOURCE "$argv[2]"
setenv HISTORYRC "$argv[3]"
set gradsx = "$argv[4]"
set command = "$argv[5]"
if ( ! -f "$GEOSUTIL/plots/configure" ) exit 2
"$GEOSUTIL/plots/configure"
if ( $status != 0 ) exit 2
if ( ! -f .quickplotrc ) exit 2
source .quickplotrc
if ( $status != 0 ) exit 2
# Configure may set plotting environment; reassert per-task selections.
setenv CMPEXP_ONLY FALSE
setenv CLIM false
setenv TAYLOR false
setenv ANALYSIS false
setenv STD_DEV false
setenv DO_STD FALSE
setenv BEGDATE "$TBEG"
setenv ENDDATE "$TEND"
setenv CLIMATE false
setenv DEBUG no_debug
if ( ! $?CMPEXP ) setenv CMPEXP NULL
if ( "$CMPEXP" == "" ) setenv CMPEXP NULL
if ( ! -f "$GEOSUTIL/plots/chckhist.new" ) exit 2
/bin/cp "$GEOSUTIL/plots/chckhist.new" chckhist
# Use the executable configured by installed GEOS unless overridden.
if ( "$gradsx" == "auto" ) then
    if ( ! $?GRADS ) then
        echo "ERROR: configure did not set GRADS"
        exit 127
    endif
    set gradsx = "$GRADS"
endif
echo "GEOS GrADS executable: $gradsx"
which "$gradsx" >& /dev/null
if ( $status != 0 ) then
    echo "ERROR: GrADS executable unavailable: $gradsx"
    exit 127
endif
"$gradsx" -b -p -c "$command"
exit $status
