#!/bin/csh -f
if ( $#argv != 3 ) exit 2
setenv GEOSUTIL "$argv[1]"
set source_dir = "$argv[2]"
set driver = "$argv[3]"
if ( ! -f "$GEOSUTIL/plots/.quickplotrc" ) then
    echo "Missing installed plots/.quickplotrc; use existing mapping files instead."
    exit 2
endif
source "$GEOSUTIL/plots/.quickplotrc"
if ( $status != 0 ) exit 2
setenv CMPEXP ""
setenv TAYLOR true
setenv CMPEXP_ONLY FALSE
setenv CMPOPS_ONLY FALSE
setenv STD_DEV false
setenv DO_STD FALSE
"$driver" -v -list -source "$source_dir"
exit $status
