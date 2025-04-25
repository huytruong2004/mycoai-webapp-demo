#!/usr/bin/env python
"""
Setup script to copy DNABarcoder datasets to the MycoAI webapp.

This script copies reference FASTA files, classification files, and cutoff files
from a dnabarcoder repository to the appropriate locations in the MycoAI webapp.

Usage:
    python setup_datasets.py --dnabarcoder_path /path/to/dnabarcoder

Arguments:
    --dnabarcoder_path: Path to the dnabarcoder repository
"""

import os
import argparse
import shutil
import glob
import sys

# Define the datasets and their associated files
DATASETS = {
    "UNITE2024ITS": {
        "reference": "unite2024ITS.fasta",
        "classification": "unite2024ITS.classification",
        "cutoff": "unite2024ITS.unique.cutoffs.best.json"
    },
    "UNITE2024ITS1": {
        "reference": "unite2024ITS1.fasta",
        "classification": "unite2024ITS1.classification",
        "cutoff": "unite2024ITS1.unique.cutoffs.best.json"
    },
    "UNITE2024ITS2": {
        "reference": "unite2024ITS2.fasta",
        "classification": "unite2024ITS2.classification",
        "cutoff": "unite2024ITS2.unique.cutoffs.best.json"
    },
    "CBSITS": {
        "reference": "CBSITS.fasta",
        "classification": "CBSITS.current.classification",
        "cutoff": "CBSITS.cutoffs.json",
        "alt_reference": "CBSITS_classification.fasta"
    }
}

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Copy DNABarcoder datasets to MycoAI webapp"
    )
    parser.add_argument(
        "--dnabarcoder_path", 
        required=True,
        help="Path to the dnabarcoder repository"
    )
    return parser.parse_args()

def create_directories():
    """Create the necessary directories if they don't exist."""
    os.makedirs("data/dnabarcoder", exist_ok=True)
    for dataset in DATASETS.keys():
        os.makedirs(f"data/dnabarcoder/{dataset}", exist_ok=True)

def find_file(dnabarcoder_path, filename, dataset):
    """Find a file in the dnabarcoder repository."""
    source_dir = os.path.join(dnabarcoder_path, "data")
    
    search_paths = [
        os.path.join(source_dir, filename)
    ]
    
    # Add UNITE-specific paths for UNITE datasets
    if dataset.startswith("UNITE"):
        # Add UNITE directories
        unite_dirs = glob.glob(os.path.join(source_dir, "UNITE*"))
        for unite_dir in unite_dirs:
            search_paths.append(os.path.join(unite_dir, filename))
        
        # Add cutoff directory for json files
        if filename.endswith(".json"):
            cutoffs_dir = os.path.join(source_dir, "UNITE_2024_cutoffs")
            if os.path.exists(cutoffs_dir):
                search_paths.append(os.path.join(cutoffs_dir, filename))
    
    for path in search_paths:
        if os.path.exists(path):
            return path
    
    for root, _, files in os.walk(source_dir):
        if filename in files:
            return os.path.join(root, filename)
    
    return None

def copy_dataset_files(dnabarcoder_path, dataset_name, files_info):
    """Copy all files for a specific dataset."""
    target_dir = f"data/dnabarcoder/{dataset_name}"
    files_copied = 0
    
    for file_type, filename in files_info.items():
        source_path = find_file(dnabarcoder_path, filename, dataset_name)
        if source_path:
            target_path = os.path.join(target_dir, filename)
            print(f"Copying {source_path} to {target_path}")
            shutil.copy2(source_path, target_path)
            files_copied += 1
        else:
            print(f"Warning: {file_type} file {filename} not found for {dataset_name}")
    
    return files_copied

def main():
    """Main function to execute the script."""
    args = parse_args()
    
    if not os.path.exists(args.dnabarcoder_path):
        print(f"Error: The specified dnabarcoder path '{args.dnabarcoder_path}' does not exist.")
        sys.exit(1)
    
    create_directories()
    
    total_files = 0
    results = {}
    
    for dataset_name, files_info in DATASETS.items():
        print(f"\nProcessing dataset: {dataset_name}")
        files_copied = copy_dataset_files(args.dnabarcoder_path, dataset_name, files_info)
        total_files += files_copied
        results[dataset_name] = files_copied
    
    print(f"\nTotal files copied: {total_files}")
    for dataset_name, files_copied in results.items():
        print(f"  {dataset_name}: {files_copied} files")
    
    if total_files > 0:
        print("\nSetup completed successfully.")
        print("\nImportant: Make sure to update the DNABarcoderWrapper to use the new directory structure.")
    else:
        print("\nWarning: No files were copied. Please check the paths and file names.")

if __name__ == "__main__":
    main() 