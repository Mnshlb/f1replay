#!/usr/bin/env python3
"""Run F1 RACE REPLAY from a source checkout without installing it:

    python main.py                 open the session-select screen
    python main.py austria 2019    straight into a race

Installed (`pip install .` / `uv tool install .`), the same CLI is available
as the `f1replay` command from anywhere.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from f1replay.cli import main

if __name__ == "__main__":
    sys.exit(main())
