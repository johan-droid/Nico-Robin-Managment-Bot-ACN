#!/usr/bin/env python3
"""Apply black formatting to Python files."""

import os
import subprocess
import sys


def run_black():
    """Run black on the current directory."""
    try:
        # Try to run black
        result = subprocess.run(
            [sys.executable, "-m", "black", "."],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        print(f"Black return code: {result.returncode}")
        if result.stdout:
            print("Black stdout:", result.stdout)
        if result.stderr:
            print("Black stderr:", result.stderr)
            
        return result.returncode == 0
        
    except Exception as e:
        print(f"Error running black: {e}")
        return False

if __name__ == "__main__":
    success = run_black()
    sys.exit(0 if success else 1)
