"""
Script to copy workflow files to the config directory.
"""

import os
import sys
import shutil
from pathlib import Path

def copy_workflows():
    """Copy workflow files to the config directory"""
    # Define paths
    comfyui_dir = os.getenv('COMFYUI_DIR', 'C:/Users/NVMax/Desktop/ComfyUI_cu128_50XX')
    datasets_dir = os.path.join(comfyui_dir, 'ComfyUI', 'Main', 'Datasets')
    config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config')
    
    # Create config directory if it doesn't exist
    os.makedirs(config_dir, exist_ok=True)
    
    # Get workflow filenames from environment variables
    flux_version = os.getenv('fluxversion', '').strip('"')
    pulid_workflow = os.getenv('PULIDWORKFLOW', '').strip('"')
    
    # Copy flux version workflow
    if flux_version:
        source_path = os.path.join(datasets_dir, flux_version)
        dest_path = os.path.join(config_dir, flux_version)
        
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
            print(f"Copied {flux_version} to {dest_path}")
        else:
            print(f"Could not find {flux_version} at {source_path}")
            
            # Try to find the file in the datasets directory
            for file in os.listdir(datasets_dir):
                if file.lower() == flux_version.lower():
                    source_path = os.path.join(datasets_dir, file)
                    dest_path = os.path.join(config_dir, file)
                    shutil.copy2(source_path, dest_path)
                    print(f"Copied {file} to {dest_path}")
                    break
    
    # Copy PuLID workflow
    if pulid_workflow:
        source_path = os.path.join(datasets_dir, pulid_workflow)
        dest_path = os.path.join(config_dir, pulid_workflow)
        
        if os.path.exists(source_path):
            shutil.copy2(source_path, dest_path)
            print(f"Copied {pulid_workflow} to {dest_path}")
        else:
            print(f"Could not find {pulid_workflow} at {source_path}")
            
            # Try to find the file in the datasets directory
            for file in os.listdir(datasets_dir):
                if file.lower() == pulid_workflow.lower():
                    source_path = os.path.join(datasets_dir, file)
                    dest_path = os.path.join(config_dir, file)
                    shutil.copy2(source_path, dest_path)
                    print(f"Copied {file} to {dest_path}")
                    break

if __name__ == "__main__":
    copy_workflows()
