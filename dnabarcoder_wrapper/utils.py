import os
import tempfile
import subprocess
import glob
import json
import pandas as pd
import zipfile
import io
from typing import Dict, List, Any, Tuple, Optional, BinaryIO


def parse_fasta(fasta_content: str) -> Dict[str, str]:
    """
    Parse a FASTA string into a dictionary of sequences.
    
    Args:
        fasta_content: String containing FASTA format data
        
    Returns:
        Dictionary mapping sequence IDs to sequences
    """
    sequences = {}
    current_id = None
    current_seq = []
    
    for line in fasta_content.strip().split('\n'):
        if line.startswith('>'):
            if current_id:
                sequences[current_id] = ''.join(current_seq)
            current_id = line[1:].strip()
            current_seq = []
        else:
            current_seq.append(line.strip())
    
    if current_id:
        sequences[current_id] = ''.join(current_seq)
    
    return sequences


def get_sequence_id(header: str) -> str:
    """Extract sequence ID from FASTA header."""
    # Simply use the first part of the header before any whitespace
    return header.split()[0]


def create_temp_fasta_file(fasta_content: str) -> str:
    """
    Create a temporary FASTA file from the content.
    
    Args:
        fasta_content: String containing FASTA format data
        
    Returns:
        Path to the temporary file
    """
    temp_file = tempfile.mktemp(suffix=".fasta")
    with open(temp_file, 'w') as f:
        f.write(fasta_content)
    return temp_file


def run_command(cmd: List[str]) -> Tuple[str, str, int]:
    """
    Run a command and return its output.
    
    Args:
        cmd: List of command arguments
        
    Returns:
        Tuple of (stdout, stderr, return_code)
    """
    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        return stdout, stderr, process.returncode
    except Exception as e:
        return "", str(e), 1


def load_cutoffs_file(cutoffs_path: str) -> Dict[str, Any]:
    """
    Load a cutoffs file in JSON format.
    
    Args:
        cutoffs_path: Path to the cutoffs JSON file
        
    Returns:
        Dictionary of cutoffs
    """
    with open(cutoffs_path, 'r') as f:
        return json.load(f)


def get_available_reference_datasets(data_dir: str) -> List[Tuple[str, str]]:
    """
    Get a list of available reference datasets based on directories in the dnabarcoder directory.
    
    Args:
        data_dir: Path to the data directory
        
    Returns:
        List of tuples (dataset_id, display_name)
    """
    datasets = []
    dnabarcoder_dir = os.path.join(data_dir, 'dnabarcoder')
    
    if not os.path.exists(dnabarcoder_dir):
        return datasets
    
    # Get all directories in the dnabarcoder directory
    for dataset_dir in os.listdir(dnabarcoder_dir):
        dir_path = os.path.join(dnabarcoder_dir, dataset_dir)
        
        # Skip if not a directory
        if not os.path.isdir(dir_path):
            continue
            
        # Format the dataset name nicely for UI display
        if dataset_dir.startswith("UNITE2024"):
            # Extract region from dataset name (ITS, ITS1, or ITS2)
            region = dataset_dir.replace("UNITE2024", "")
            nice_name = f"UNITE 2024 {region}"
        elif dataset_dir == "CBSITS":
            nice_name = "CBS ITS"
        else:
            nice_name = dataset_dir
            
        # Verify that the directory contains the necessary files
        has_reference = any(f.endswith('.fasta') for f in os.listdir(dir_path))
        has_classification = any(f.endswith('.classification') for f in os.listdir(dir_path))
        has_cutoff = any(f.endswith('.json') for f in os.listdir(dir_path))
        
        if has_reference and has_classification and has_cutoff:
            datasets.append((dataset_dir, nice_name))
    
    # Sort the datasets by name
    datasets.sort(key=lambda x: x[1])
    
    return datasets


def get_cutoffs_file_path(data_dir: str, dataset_name: str) -> str:
    """
    Get the path to the cutoffs file for a dataset.
    
    Args:
        data_dir: Path to the data directory
        dataset_name: Name of the dataset
        
    Returns:
        Path to the cutoffs file
    """
    dataset_dir = os.path.join(data_dir, 'dnabarcoder', dataset_name)
    
    # Look for cutoff files in the dataset directory
    cutoff_files = glob.glob(os.path.join(dataset_dir, "*.json"))
    
    if not cutoff_files:
        raise FileNotFoundError(f"No cutoffs file found for dataset {dataset_name}")
    
    # Return the first cutoff file found
    return cutoff_files[0]


def create_results_zip(file_paths: Dict[str, str]) -> BinaryIO:
    """
    Create a zip file containing multiple result files.
    
    Args:
        file_paths: Dictionary mapping filenames to file paths
        
    Returns:
        In-memory zip file as a binary stream
    """
    # Create an in-memory zip file
    zip_buffer = io.BytesIO()
    
    # Create a new zip file
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add each file to the zip
        for filename, file_path in file_paths.items():
            if os.path.exists(file_path):
                # Read the file and add it to the zip with the given filename
                with open(file_path, 'rb') as f:
                    zip_file.writestr(filename, f.read())
    
    # Seek to the beginning of the buffer
    zip_buffer.seek(0)
    return zip_buffer


def parse_classification_result(result_file: str) -> pd.DataFrame:
    """
    Parse the classification result file into a pandas DataFrame.
    
    Args:
        result_file: Path to the classification result file
        
    Returns:
        DataFrame with the classification results
    """
    # Read the file
    with open(result_file, 'r') as f:
        lines = f.readlines()
    
    # Parse the header
    header = lines[0].strip().split('\t')
    
    # Determine the file type based on the extension
    is_classification_report = result_file.endswith('.classification')
    
    # Parse the data
    data = []
    for line in lines[1:]:
        fields = line.strip().split('\t')
        # Pad with empty strings if necessary
        while len(fields) < len(header):
            fields.append('')
        data.append(fields)
    
    # Create the DataFrame
    df = pd.DataFrame(data, columns=header)
    
    # For .classification format, ensure columns are properly renamed
    if is_classification_report:
        # Map standard column names (lowercase) to our expected format
        column_map = {
            'id': 'Sequence_ID',
            'referenceid': 'ReferenceID',
            'kingdom': 'kingdom',
            'phylum': 'phylum',
            'class': 'class',
            'order': 'order',
            'family': 'family',
            'genus': 'genus',
            'species': 'species',
            'rank': 'rank',
            'score': 'score',
            'cutoff': 'cutoff',
            'confidence': 'confidence'
        }
        
        # Rename columns based on the mapping (case-insensitive)
        renamed_columns = {}
        for col in df.columns:
            if col.lower() in column_map:
                renamed_columns[col] = column_map[col.lower()]
        
        if renamed_columns:
            df = df.rename(columns=renamed_columns)
    
    # For .classified format, we need to extract taxonomy from the full classification column
    elif result_file.endswith('.classified') and 'Full classification' in df.columns:
        # Extract taxonomy from the full classification column if it exists
        for idx, row in df.iterrows():
            if pd.notna(row['Full classification']) and ';' in row['Full classification']:
                taxa = row['Full classification'].split(';')
                for taxon in taxa:
                    if taxon.startswith('k__'):
                        df.at[idx, 'kingdom'] = taxon[3:]
                    elif taxon.startswith('p__'):
                        df.at[idx, 'phylum'] = taxon[3:]
                    elif taxon.startswith('c__'):
                        df.at[idx, 'class'] = taxon[3:]
                    elif taxon.startswith('o__'):
                        df.at[idx, 'order'] = taxon[3:]
                    elif taxon.startswith('f__'):
                        df.at[idx, 'family'] = taxon[3:]
                    elif taxon.startswith('g__'):
                        df.at[idx, 'genus'] = taxon[3:]
                    elif taxon.startswith('s__'):
                        df.at[idx, 'species'] = taxon[3:]
        
        # Map BLAST similarity to score if it exists
        if 'BLAST sim' in df.columns:
            df['score'] = df['BLAST sim']
        
        # Get the rank from the classification file if available
        if 'Rank' in df.columns:
            df['rank'] = df['Rank']
        
        # Copy cutoff value if available
        if 'Cut-off' in df.columns:
            df['cutoff'] = df['Cut-off']
        
        # Copy confidence value if available
        if 'Confidence' in df.columns:
            df['confidence'] = df['Confidence']
    
    # Ensure all taxonomy columns exist with proper lowercase names
    for col in ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']:
        if col not in df.columns:
            df[col] = ""
    
    # Ensure score, cutoff, confidence, and rank columns exist
    for col in ['score', 'cutoff', 'confidence', 'rank']:
        if col not in df.columns:
            df[col] = ""
            
    # Replace "unidentified" with empty string for cleaner display
    taxonomy_cols = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']
    for col in taxonomy_cols:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: "" if pd.isna(x) or x.lower() in ['unidentified', 'unid.', 'na', 'n/a'] else x
            )
    
    # Convert numeric columns that should be numbers
    numeric_cols = ['score', 'cutoff', 'confidence']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df 