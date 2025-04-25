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
    # Search in the data directory
    source_dir = os.path.join(dnabarcoder_path, "data")
    source_path = os.path.join(source_dir, filename)
    
    if os.path.exists(source_path):
        return source_path
    
    # Search in UNITE directories for UNITE datasets
    if dataset.startswith("UNITE"):
        unite_dirs = glob.glob(os.path.join(source_dir, "UNITE*"))
        for unite_dir in unite_dirs:
            source_path = os.path.join(unite_dir, filename)
            if os.path.exists(source_path):
                return source_path
    
    # Search in UNITE_2024_cutoffs for cutoff files
    if filename.endswith(".json") and dataset.startswith("UNITE"):
        cutoffs_dir = os.path.join(source_dir, "UNITE_2024_cutoffs")
        if os.path.exists(cutoffs_dir):
            source_path = os.path.join(cutoffs_dir, filename)
            if os.path.exists(source_path):
                return source_path
    
    # Search in any subdirectory
    for root, _, files in os.walk(source_dir):
        if filename in files:
            return os.path.join(root, filename)
    
    # Look for similar files as a fallback
    similar_files = glob.glob(os.path.join(source_dir, f"*{filename}*"))
    if similar_files:
        print(f"Warning: Exact match for {filename} not found, but found similar files: "
              f"{', '.join(os.path.basename(f) for f in similar_files)}")
    
    return None

def copy_dataset_files(dnabarcoder_path, dataset_name, files_info):
    """Copy all files for a specific dataset."""
    target_dir = f"data/dnabarcoder/{dataset_name}"
    files_copied = 0
    
    for file_type, filename in files_info.items():
        if file_type == "alt_reference":
            continue  # Handle alt_reference separately
        
        source_path = find_file(dnabarcoder_path, filename, dataset_name)
        if source_path:
            target_path = os.path.join(target_dir, filename)
            print(f"Copying {source_path} to {target_path}")
            shutil.copy2(source_path, target_path)
            files_copied += 1
        else:
            print(f"Warning: {file_type} file {filename} not found for {dataset_name}")
    
    # Handle alternative reference file if specified
    if "alt_reference" in files_info:
        alt_filename = files_info["alt_reference"]
        source_path = find_file(dnabarcoder_path, alt_filename, dataset_name)
        if source_path:
            target_path = os.path.join(target_dir, alt_filename)
            print(f"Copying alternative reference {source_path} to {target_path}")
            shutil.copy2(source_path, target_path)
            files_copied += 1
    
    return files_copied

def main():
    """Main function to execute the script."""
    args = parse_args()
    
    # Check if dnabarcoder path exists
    if not os.path.exists(args.dnabarcoder_path):
        print(f"Error: The specified dnabarcoder path '{args.dnabarcoder_path}' does not exist.")
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Copy files for each dataset
    total_files = 0
    results = {}
    
    for dataset_name, files_info in DATASETS.items():
        print(f"\nProcessing dataset: {dataset_name}")
        files_copied = copy_dataset_files(args.dnabarcoder_path, dataset_name, files_info)
        total_files += files_copied
        results[dataset_name] = files_copied
    
    # Report results
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