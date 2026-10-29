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
setenv CMPEXP_ONLY TRUE
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
# Check GrADS' initialization and script dispatch in the log.
"$gradsx" -b -p -c "$command"
exit $status
