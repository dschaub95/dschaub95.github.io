#!/usr/bin/env python3
"""Serve the website locally using Python's HTTP server."""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Run a local HTTP server to serve the website."""
    parser = argparse.ArgumentParser(
        description="Serve the personal website on localhost"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to serve on (default: 8000)",
    )
    args = parser.parse_args()

    # Get the project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Change to the project root directory
    os.chdir(project_root)

    # Call python -m http.server
    sys.exit(
        subprocess.run([sys.executable, "-m", "http.server", str(args.port)]).returncode
    )


if __name__ == "__main__":
    main()
