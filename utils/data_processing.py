"""
Data processing utilities for the MycoAI application.
"""
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import os

from constants import (
    COLUMN_MAPPING, REQUIRED_COLUMNS, NUMERIC_COLUMNS,
    ID_COLUMNS, TAXONOMY_DISPLAY_COLUMNS,
    MIN_ALIGNMENT_LENGTHS
)
from taxotagger.defaults import TAXONOMY_LEVELS


def get_min_alignment_length(dataset: str) -> int:
    """
    Get the appropriate minimum alignment length based on dataset type.
    
    Args:
        dataset: The dataset ID
        
    Returns:
        Minimum alignment length appropriate for the dataset
    """
    if "ITS1" in dataset:
        return MIN_ALIGNMENT_LENGTHS["ITS1"]
    elif "ITS2" in dataset:
        return MIN_ALIGNMENT_LENGTHS["ITS2"]
    else:
        return MIN_ALIGNMENT_LENGTHS["default"]


def process_taxotagger_results(results: Dict[str, Any], seq_ids: List[str], top_n: int) -> Dict[str, List[Dict[str, Any]]]:
    """
    Process results from TaxoTagger into a standardized format.
    
    Args:
        results: Raw results from TaxoTagger
        seq_ids: List of sequence IDs
        top_n: Number of top matches to include
        
    Returns:
        Dictionary of processed results organized by sequence ID
    """
    # Check if the number of results matches the number of input sequences
    if len(results[TAXONOMY_LEVELS[0]]) != len(seq_ids):
        raise ValueError(
            f"Mismatch between number of input sequences ({len(seq_ids)}) and results ({len(results[TAXONOMY_LEVELS[0]])})."
        )

    # Process results
    results_by_seq = {}
    for i, seq_id in enumerate(seq_ids):
        results_by_seq[seq_id] = []
        for j in range(top_n):
            result = {}
            result["Sequence_ID"] = seq_id
            result["Rank"] = j + 1
            for level in TAXONOMY_LEVELS:
                level_cap = level.capitalize()
                try:
                    match = results[level][i][j]
                    value = match["entity"].get(level, "")
                    if value:
                        result[level_cap] = value
                        result[level_cap + "_Hit"] = match["id"]
                        result[level_cap + "_Similarity"] = match["distance"]
                    else:
                        result[level_cap] = ""
                        result[level_cap + "_Hit"] = ""
                        result[level_cap + "_Similarity"] = ""
                except IndexError:
                    result[level_cap] = "No match found"
            results_by_seq[seq_id].append(result)
    
    return results_by_seq


def normalize_dataframe_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize column names in a DataFrame to standard format.
    
    Args:
        df: Input DataFrame with potentially inconsistent column names
        
    Returns:
        DataFrame with normalized column names
    """
    # Make a working copy
    df = df.copy()
    
    # Apply column renaming
    for old_col, new_col in COLUMN_MAPPING.items():
        if old_col in df.columns and new_col not in df.columns:
            df[new_col] = df[old_col]
            
    return df


def extract_taxonomy_from_sequence_id(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract taxonomy information from sequence IDs where available.
    
    Args:
        df: Input DataFrame with Sequence_ID column
        
    Returns:
        DataFrame with taxonomy columns populated from sequence IDs
    """
    # Make a working copy
    df = df.copy()
    
    # Extract just the basic ID part from the full Sequence_ID
    if 'Sequence_ID' in df.columns:
        # This removes any taxonomy information after | characters
        df["Display_ID"] = df["Sequence_ID"].apply(lambda x: x.split('|')[0] if '|' in str(x) else x)
        
        # Check if there's taxonomy information in the Sequence_ID
        # Format: ID|k__Kingdom;p__Phylum;c__Class;o__Order;f__Family;g__Genus;s__Species|...
        if any('|' in str(id) for id in df["Sequence_ID"]):
            # Extract taxonomy from pipe-delimited format
            for idx, row in df.iterrows():
                seq_id = row["Sequence_ID"]
                if '|' in str(seq_id) and len(str(seq_id).split('|')) > 1:
                    taxonomy_part = str(seq_id).split('|')[1]
                    
                    # Extract taxonomy from the format k__Kingdom;p__Phylum;c__Class;...
                    if ';' in taxonomy_part:
                        taxa = taxonomy_part.split(';')
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
    
    return df


def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure all required columns exist in the DataFrame.
    
    Args:
        df: Input DataFrame
        
    Returns:
        DataFrame with all required columns (filled with "N/A" if missing)
    """
    df = df.copy()
    
    # Ensure all required columns exist
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            df[col] = "N/A"
    
    return df


def populate_sequence_ids(df: pd.DataFrame, seq_ids: Optional[List[str]] = None) -> pd.DataFrame:
    """
    Populate Sequence_ID column if missing or empty.
    
    Args:
        df: Input DataFrame
        seq_ids: List of sequence IDs from session state (optional)
        
    Returns:
        DataFrame with populated Sequence_ID column
    """
    # Make a working copy
    df = df.copy()
    
    if "Sequence_ID" in df.columns and df["Sequence_ID"].isna().all():
        if seq_ids and len(df) == len(seq_ids):
            df["Sequence_ID"] = seq_ids
        else:
            df["Sequence_ID"] = [f"Sequence_{i+1}" for i in range(len(df))]
    
    for id_col in ID_COLUMNS:
        if id_col in df.columns and "Sequence_ID" in df.columns and df["Sequence_ID"].eq("N/A").all():
            df["Sequence_ID"] = df[id_col]
    
    return df


def convert_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert columns that should be numeric to numeric types.
    
    Args:
        df: Input DataFrame
        
    Returns:
        DataFrame with numeric columns converted to numeric types
    """
    df = df.copy()
    
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def prepare_dnabarcoder_dataframe(df: pd.DataFrame, seq_ids: Optional[List[str]] = None) -> Tuple[pd.DataFrame, Dict[str, str], bool]:
    """
    Prepare DNABarcoder results DataFrame for display.
    
    Args:
        df: Raw DNABarcoder results DataFrame
        seq_ids: List of sequence IDs from session state (optional)
        
    Returns:
        Tuple containing:
            - Processed DataFrame
            - Dictionary mapping sequence IDs to display names
            - Boolean indicating if multiple sequences are present
    """
    df = df.copy()
    
    df = normalize_dataframe_columns(df)
    df = extract_taxonomy_from_sequence_id(df)
    df = ensure_required_columns(df)
    df = populate_sequence_ids(df, seq_ids)
    df = convert_numeric_columns(df)
    
    has_multiple_sequences = False
    display_ids = {}
    
    # Check DataFrame for multiple sequences
    if 'Sequence_ID' in df.columns and len(df["Sequence_ID"].unique()) > 1:
        sequence_ids = df["Sequence_ID"].unique()
        has_multiple_sequences = True
    elif hasattr(df, 'attrs') and 'original_seq_ids' in df.attrs and len(df.attrs['original_seq_ids']) > 1:
        sequence_ids = df.attrs['original_seq_ids']
        has_multiple_sequences = True
        
    if len(sequence_ids) == len(df):
        df["Sequence_ID"] = sequence_ids
    elif seq_ids and len(seq_ids) > 1:
        sequence_ids = seq_ids
        has_multiple_sequences = True
        
    if len(sequence_ids) == len(df):
        df["Sequence_ID"] = sequence_ids
    else:
        sequence_ids = []
    
    if has_multiple_sequences:
        display_ids = {
            str(seq_id): str(seq_id).split('|')[0] if '|' in str(seq_id) else str(seq_id) 
            for seq_id in sequence_ids
        }
    
    return df, display_ids, has_multiple_sequences


def filter_dataframe_by_sequence(df: pd.DataFrame, sequence_id: str) -> pd.DataFrame:
    """
    Filter DataFrame to show only rows for a specific sequence.
    
    Args:
        df: Input DataFrame
        sequence_id: Sequence ID to filter by
        
    Returns:
        Filtered DataFrame
    """
    filtered_df = df[df["Sequence_ID"].astype(str) == str(sequence_id)]
    
    if filtered_df.empty:
        return df
    
    return filtered_df


def get_available_display_columns(df: pd.DataFrame) -> List[str]:
    """
    Get the list of available display columns in the specified order.
    
    Args:
        df: Input DataFrame
        
    Returns:
        List of column names that exist in the DataFrame
    """
    # Only include columns that exist in the dataframe
    return [col for col in TAXONOMY_DISPLAY_COLUMNS if col in df.columns]