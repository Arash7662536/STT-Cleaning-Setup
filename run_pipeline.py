#!/usr/bin/env python3
"""
Convenience script to run the dataset pipeline.

This is a simple wrapper around the CLI for easier execution.
"""

import sys
from src.dataset_pipeline.cli import main

if __name__ == "__main__":
    sys.exit(main())
