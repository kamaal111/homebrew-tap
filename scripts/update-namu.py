#!/usr/bin/env python3
"""Compatibility entry point; use update-package.py namu."""
from tap_updater import main

if __name__ == "__main__":
    raise SystemExit(main("namu"))
