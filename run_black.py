#!/usr/bin/env python3
"""Simple script to run black on the codebase."""

import subprocess
import sys


def main():
    """Run black on the current directory."""
    try:
        result = subprocess.run([
            sys.executable, "-m", "black", "."
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Code formatted successfully!")
            if result.stdout:
                print("Black output:", result.stdout)
        else:
            print("❌ Black failed with return code:", result.returncode)
            if result.stderr:
                print("Black errors:", result.stderr)
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error running black: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
