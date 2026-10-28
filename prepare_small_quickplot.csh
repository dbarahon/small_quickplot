#!/bin/csh -f
set script_dir = "$0:h"
python3 "$script_dir/prepare_small_quickplot.py" $argv:q
exit $status
