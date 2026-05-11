"""Run the bot for local development.

Usage:
    python run_services.py

Requires: a working virtualenv with project dependencies installed.
"""

import subprocess
import sys

if __name__ == "__main__":
    try:
        result = subprocess.run([sys.executable, "main.py"], cwd=".")
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        sys.exit(130)
