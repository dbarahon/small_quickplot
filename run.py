#!/usr/bin/env python3
"""Standalone command-line launcher."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from cli import main
if __name__=='__main__':
    raise SystemExit(main())
