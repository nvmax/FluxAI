"""
Master setup script that runs all the other setup scripts.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_script(script_name):
    """Run a Python script"""
    script_path = Path(__file__).parent / script_name
    print(f"Running {script_name}...")
    subprocess.run([sys.executable, str(script_path)], check=True)
    print(f"Finished running {script_name}")

def main():
    """Run all setup scripts"""
    # Create directories
    os.makedirs("config", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    os.makedirs("temp", exist_ok=True)
    
    # Run scripts
    run_script("update_env.py")
    run_script("copy_workflows.py")
    run_script("init_content_filter.py")
    
    print("Setup complete!")

if __name__ == "__main__":
    main()
