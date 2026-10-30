#!/usr/bin/env python3
"""Direct launcher; also supports python -m python_quickplot."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from python_quickplot.cli import main
if __name__=='__main__':
    raise SystemExit(main())
