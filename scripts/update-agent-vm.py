#!/usr/bin/env python3
"""Compatibility entry point; use update-package.py agent-vm."""
from tap_updater import main

if __name__ == "__main__":
    raise SystemExit(main("agent-vm"))
