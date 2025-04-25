"""
Functions for handling and validating FASTA input.
"""
from typing import Dict, List, Tuple
import streamlit as st
from taxotagger.utils import parse_fasta, parse_unite_fasta_header

from constants import MAX_SEQUENCES


def validate_fasta_headers(headers: List[str]) -> List[str]:
    """
    Validate FASTA headers and extract sequence IDs.
    
    Args:
        headers: List of FASTA headers to validate
        
    Returns:
        List of sequence IDs extracted from headers
        
    Raises:
        ValueError: If headers are invalid or duplicates are found
    """
    seq_ids = []
    
    for header in headers:
        # Empty header check
        if not header:
            st.error(
                "Invalid FASTA header(s) found. Please ensure that each header starts with '>' plus at least one more non-empty character.",
                icon="⚠️",
            )
            st.stop()
        
        # Extract and check for duplicate IDs
        seq_id = parse_unite_fasta_header(header)[0]
        if seq_id not in seq_ids:
            seq_ids.append(seq_id)
        else:
            st.error(
                f"Duplicate sequence ID found: `{seq_id}`\n\nPlease ensure all sequence IDs are unique.",
                icon="⚠️",
            )
            st.stop()
    
    return seq_ids


def validate_sequence_content(header_seq_dict: Dict[str, str]) -> Dict[str, str]:
    """
    Validate sequence content for emptiness and duplicates.
    
    Args:
        header_seq_dict: Dictionary of header to sequence mappings
        
    Returns:
        Dictionary mapping sequences to headers (for duplicate checking)
        
    Raises:
        ValueError: If empty or duplicate sequences are found
    """
    seq_header_dict = {}
    
    for header, seq in header_seq_dict.items():
        # Check for empty sequences
        if not seq:
            st.error(
                f"Empty sequence found for: `{header}`. Please ensure all sequences are non-empty.",
                icon="⚠️",
            )
            st.stop()
        
        # Check for duplicate sequences
        if seq in seq_header_dict:
            st.error(
                f"`{header}` and `{seq_header_dict[seq]}` have the same DNA sequence. Please ensure all sequences are unique.",
                icon="⚠️",
            )
            st.stop()
        else:
            seq_header_dict[seq] = header
    
    return seq_header_dict


def validate_sequence_count(count: int) -> None:
    """
    Validate that the number of sequences is within the allowed limit.
    
    Args:
        count: Number of sequences
        
    Raises:
        ValueError: If count exceeds MAX_SEQUENCES
    """
    if count > MAX_SEQUENCES:
        st.error(f"Please limit the number of sequences to {MAX_SEQUENCES} or fewer.", icon="⚠️")
        st.stop()
    else:
        st.markdown(
            f"<p style='font-size: smaller; color: gray;'>You provided {count} valid sequences (max: {MAX_SEQUENCES})</p>",
            unsafe_allow_html=True,
        )


def validate_input(fasta_content: str) -> None:
    """
    Validate the FASTA input. Checks for valid headers, non-empty sequences,
    unique IDs, unique sequences, and maximum sequence count.
    
    Args:
        fasta_content: FASTA format text content
        
    Raises:
        ValueError: On any validation error
    """
    try:
        header_seq_dict = parse_fasta(fasta_content)
    except ValueError as e:
        st.error(
            e.args[0] + "\n\nPlease ensure all FASTA headers are unique.", icon="⚠️"
        )
        st.stop()

    # Validate headers and extract sequence IDs
    seq_ids = validate_fasta_headers(list(header_seq_dict.keys()))
    
    # Validate sequence content
    validate_sequence_content(header_seq_dict)
    
    # Validate sequence count
    validate_sequence_count(len(header_seq_dict))
    
    # Store validated data in session state for further processing
    st.session_state["seq_ids"] = seq_ids
    st.session_state["fasta_content"] = fasta_content


def process_uploaded_files(uploaded_files) -> str:
    """
    Process uploaded FASTA files and combine their content.
    
    Args:
        uploaded_files: List of uploaded file objects
        
    Returns:
        Combined FASTA content from all files
    """
    fasta_content = ""
    for uploaded_file in uploaded_files:
        file_content = uploaded_file.getvalue().decode() + "\n"
        fasta_content += file_content
    return fasta_content