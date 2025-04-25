"""
Constants and configuration values for the MycoAI web-application.
"""
from typing import Dict, List, Tuple, Any

# UI Constants
LOGO_IMAGE = "images/TaxoTagger-logo.svg"
PAGE_TITLE = "MycoAI DNA Barcode Identification"

# Application limits
MAX_SEQUENCES = 100
DEFAULT_CUTOFF = 0.97
MIN_ALLOWED_CUTOFF = 0.90
MAX_ALLOWED_CUTOFF = 1.0

# Default dataset values
DEFAULT_DATASETS: List[Tuple[str, str]] = [
    ("unite2024ITS", "UNITE 2024 ITS"),
    ("unite2024ITS1", "UNITE 2024 ITS1"),
    ("unite2024ITS2", "UNITE 2024 ITS2"),
    ("CBSITS", "CBS ITS Dataset")
]

# Method options
METHOD_OPTIONS = ["taxotagger", "dnabarcoder", "MycoAI-CNN", "MycoAI-BERT"]

# Column mappings for result normalization
COLUMN_MAPPING: Dict[str, str] = {
    'Similarity': 'score',
    'BLAST sim': 'score',
    'Cutoff': 'cutoff',
    'Cut-off': 'cutoff',
    'Confidence': 'confidence',
    'Kingdom': 'kingdom',
    'Phylum': 'phylum',
    'Class': 'class',
    'Order': 'order',
    'Family': 'family',
    'Genus': 'genus',
    'Species': 'species',
    'Rank': 'rank'
}

# Required columns for DNABarcoder results
REQUIRED_COLUMNS = [
    "Sequence_ID", "ReferenceID", "kingdom", "phylum", "class", 
    "order", "family", "genus", "species", "rank", "score", "cutoff", "confidence"
]

# Dataset-specific minimum alignment lengths
MIN_ALIGNMENT_LENGTHS: Dict[str, int] = {
    "default": 400,  # Default for full ITS
    "ITS1": 50,      # Shorter for ITS1
    "ITS2": 50       # Shorter for ITS2
}

# Numeric columns that should be converted for display
NUMERIC_COLUMNS = ['score', 'cutoff', 'confidence']

# Alternative ID column names
ID_COLUMNS = ["ID", "Query", "Query ID", "QueryID", "Name", "SequenceID"]

# Taxonomy display columns in order
TAXONOMY_DISPLAY_COLUMNS = [
    "kingdom", "phylum", "class", "order", "family", "genus", "species", 
    "rank", "score", "cutoff", "confidence"
]

# Standard display columns for TaxoTagger results
TAXOTAGGER_DISPLAY_COLUMNS = [
    "Rank", "Kingdom", "Phylum", "Class", "Order", "Family", "Genus", "Species"
]