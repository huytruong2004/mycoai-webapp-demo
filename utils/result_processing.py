"""
Result processing for the MycoAI application.
"""
from typing import Dict, List, Tuple, Any, Optional
import os
import tempfile
import streamlit as st
import pandas as pd
from datetime import datetime

from utils.data_processing import (
    process_taxotagger_results, prepare_dnabarcoder_dataframe,
    filter_dataframe_by_sequence, get_available_display_columns,
    get_min_alignment_length
)


def process_fasta_and_run(
    fasta_content: str, 
    method: str, 
    taxotagger, 
    dnabarcoder
) -> Any:
    """
    Process FASTA content and run the selected analysis method.
    
    Args:
        fasta_content: FASTA format text content
        method: Analysis method to use (taxotagger, dnabarcoder, etc.)
        taxotagger: TaxoTagger instance
        dnabarcoder: DNABarcoder wrapper instance
        
    Returns:
        Analysis results in the appropriate format for the method
        
    Raises:
        ValueError: If analysis fails
    """
    if method == "taxotagger":
        return run_taxotagger_analysis(fasta_content, taxotagger)
    elif method == "dnabarcoder":
        return run_dnabarcoder_analysis(fasta_content, dnabarcoder)
    else:
        # Handle MycoAI-CNN and MycoAI-BERT methods
        st.warning(f"The {method} method is not yet implemented.", icon="⚠️")
        st.stop()


def run_taxotagger_analysis(fasta_content: str, taxotagger) -> Dict[str, Any]:
    """
    Run TaxoTagger analysis.
    
    Args:
        fasta_content: FASTA format text content
        taxotagger: TaxoTagger instance
        
    Returns:
        TaxoTagger results
        
    Raises:
        ValueError: If analysis fails
    """
    with tempfile.NamedTemporaryFile(
        mode="w+", delete=False, suffix=".fasta"
    ) as temp_fasta:
        temp_fasta.write(fasta_content)
        temp_fasta.flush()

        try:
            results = taxotagger.search(
                temp_fasta.name,
                model_id=st.session_state["selected_model"],
                limit=st.session_state["top_n"],
            )
            return results
        finally:
            os.unlink(temp_fasta.name)


def run_dnabarcoder_analysis(fasta_content: str, dnabarcoder) -> pd.DataFrame:
    """
    Run DNABarcoder analysis.
    
    Args:
        fasta_content: FASTA format text content
        dnabarcoder: DNABarcoder wrapper instance
        
    Returns:
        DataFrame containing DNABarcoder results
        
    Raises:
        ValueError: If analysis fails
    """
    try:
        dataset = st.session_state["reference_dataset"]
        
        min_alignment_length = get_min_alignment_length(dataset)

        # Get classification method parameters
        classification_method = st.session_state.get("classification_method", "Local").lower()
        cutoff_value = st.session_state.get("custom_cutoff")
        # Since confidence slider was removed, set confidence to None
        confidence_value = None
        
        # Run DNABarcoder classification
        with st.spinner("Running DNABarcoder classification..."):
            # Get the sequence IDs from the session state
            seq_ids = st.session_state.get("seq_ids", [])
            
            results_df = dnabarcoder.run_classification(
                fasta_content=fasta_content,
                reference_dataset=dataset,
                method=classification_method,
                cutoff=cutoff_value,
                min_alignment_length=min_alignment_length,
                rank=st.session_state["taxonomic_rank"],
                confidence=confidence_value
            )
            
            # Save original sequence IDs in DataFrame metadata for reference
            if seq_ids:
                results_df.attrs['original_seq_ids'] = seq_ids
        
        if "Error" in results_df.columns:
            error_msg = results_df["Error"].iloc[0]
            st.error(f"DNABarcoder analysis failed: {error_msg}", icon="⚠️")
            st.stop()
            
        return results_df
    except Exception as e:
        st.error(f"Error running DNABarcoder: {str(e)}", icon="⚠️")
        st.stop()


def process_results(results: Any, method: str) -> None:
    """
    Process the results and store in session state.
    
    Args:
        results: Analysis results
        method: Analysis method used
    """
    if method == "taxotagger":
        process_taxotagger_result(results)
    elif method == "dnabarcoder":
        process_dnabarcoder_result(results)
    else:
        # Handle other methods when implemented
        st.warning(f"Results handling for {method} is not yet implemented.", icon="⚠️")


def process_taxotagger_result(results: Dict[str, Any]) -> None:
    """
    Process TaxoTagger results.
    
    Args:
        results: TaxoTagger results
    """
    from taxotagger.defaults import TAXONOMY_LEVELS
    
    seq_ids = st.session_state["seq_ids"]

    # Check if the number of results matches the number of input sequences
    if len(results[TAXONOMY_LEVELS[0]]) != len(seq_ids):
        st.error(
            f"Mismatch between number of input sequences ({len(seq_ids)}) and results ({len(results[TAXONOMY_LEVELS[0]])}).",
            icon="⚠️",
        )
        return

    # Process results
    results_by_seq = process_taxotagger_results(results, seq_ids, st.session_state["top_n"])
    st.session_state["results_by_seq"] = results_by_seq
    st.session_state["result_type"] = "taxotagger"


def process_dnabarcoder_result(results: pd.DataFrame) -> None:
    """
    Process DNABarcoder results.
    
    Args:
        results: DNABarcoder results DataFrame
    """
    # DNABarcoder returns a DataFrame directly
    st.session_state["dnabarcoder_results"] = results
    st.session_state["result_type"] = "dnabarcoder"


def display_taxotagger_results() -> None:
    """Display TaxoTagger results."""
    from utils.ui_components import create_taxotagger_results_display
    
    if "results_by_seq" in st.session_state:
        create_taxotagger_results_display(st.session_state["results_by_seq"])


def display_dnabarcoder_results() -> None:
    """Display DNABarcoder results."""
    from utils.ui_components import (
        create_sequence_selector, create_classification_tab, 
        create_visualization_tab
    )
    
    if "dnabarcoder_results" not in st.session_state or st.session_state["dnabarcoder_results"] is None:
        st.info("No DNABarcoder results available. Please run an analysis first.")
        return

    df = st.session_state["dnabarcoder_results"]
    
    if df.empty:
        st.info("No results were found. Try adjusting your parameters or using a different dataset.")
        return
    
    # Prepare the DataFrame for display
    prepared_df, display_ids, has_multiple_sequences = prepare_dnabarcoder_dataframe(
        df, st.session_state.get("seq_ids", [])
    )
    
    # Display classification parameters (method, cutoff, confidence)
    classification_params = []
    if hasattr(prepared_df, 'attrs'):
        if 'classification_method' in prepared_df.attrs:
            method = prepared_df.attrs['classification_method'].capitalize()
            classification_params.append(f"Method: {method}")
        if 'cutoff' in prepared_df.attrs and prepared_df.attrs['cutoff'] is not None:
            cutoff = prepared_df.attrs['cutoff']
            classification_params.append(f"Similarity cutoff: {cutoff:.3f}")
        # Confidence is no longer displayed since we removed the confidence threshold slider
    
    if classification_params:
        st.caption("Classification parameters: " + ", ".join(classification_params))
        
    # Place sequence selection dropdown at top level (outside of tabs) for better visibility
    filtered_df = prepared_df
    if has_multiple_sequences:
        selected_seq_id = create_sequence_selector(
            list(display_ids.keys()), display_ids
        )
        filtered_df = filter_dataframe_by_sequence(prepared_df, selected_seq_id)
    
    available_columns = get_available_display_columns(filtered_df)
    
    tabs = st.tabs(["Classification Results", "Taxonomic Visualization"])
    
    # Tab 1: Classification Results
    with tabs[0]:
        # Display the results table
        create_classification_tab(filtered_df, available_columns)
    
    # Tab 2: Taxonomic Visualization (Krona)
    with tabs[1]:
        # Display visualization tab
        create_visualization_tab(prepared_df)

    st.session_state["dnabarcoder_results"] = prepared_df


def display_results() -> None:
    """Display results based on the analysis method used."""
    if "result_type" not in st.session_state:
        return
    
    # Display results header
    st.subheader(
        "Results",
        help="""The predicted taxonomy labels for each input DNA sequence are displayed below.""",
    )
    
    # Display results based on method
    if st.session_state["result_type"] == "taxotagger":
        display_taxotagger_results()
    elif st.session_state["result_type"] == "dnabarcoder":
        display_dnabarcoder_results()


def create_taxotagger_export(results_by_seq: Dict[str, List[Dict[str, Any]]]) -> Tuple[str, str]:
    """
    Create a CSV export of TaxoTagger results.
    
    Args:
        results_by_seq: Dictionary of results by sequence ID
        
    Returns:
        Tuple of (CSV data, filename)
    """
    # Convert the results to a flat dataframe for export
    flat_results = []
    for seq_id, results_list in results_by_seq.items():
        for result in results_list:
            flat_results.append(result)
    export_df = pd.DataFrame(flat_results)
    
    # Prepare CSV for download
    csv = export_df.to_csv(index=False)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    method = st.session_state.get("selected_method", "taxotagger")
    filename = f"{method}_results_{timestamp}.csv"
    
    return csv, filename


def create_dnabarcoder_export(results_df: pd.DataFrame) -> Tuple[bytes, str]:
    """
    Create a ZIP export of DNABarcoder results.
    
    Args:
        results_df: DataFrame containing DNABarcoder results
        
    Returns:
        Tuple of (ZIP data, filename)
    """
    from dnabarcoder_wrapper.utils import create_results_zip
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    method = st.session_state.get("selected_method", "dnabarcoder")
    
    # Check if both files are available
    files_to_zip = {}
    if hasattr(results_df, 'attrs'):
        # Add .classified file if available
        if 'classified_file_path' in results_df.attrs:
            classified_file = results_df.attrs['classified_file_path']
            if os.path.exists(classified_file):
                files_to_zip["classification_results.classified"] = classified_file
        
        # Add Krona HTML file if available
        if 'krona_html_path' in results_df.attrs:
            krona_html_path = results_df.attrs['krona_html_path']
            if os.path.exists(krona_html_path):
                files_to_zip["taxonomic_visualization.html"] = krona_html_path
    
    # Create zip file with all results
    zip_buffer = create_results_zip(files_to_zip)
    filename = f"{method}_results_{timestamp}.zip"
    
    return zip_buffer, filename


def create_export_section() -> None:
    """Create the export results section."""
    if "result_type" not in st.session_state:
        return
    
    st.subheader("Export Results")
    
    if st.session_state["result_type"] == "taxotagger" and "results_by_seq" in st.session_state:
        csv, filename = create_taxotagger_export(st.session_state["results_by_seq"])
        
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=filename,
            mime="text/csv",
        )
        
    elif st.session_state["result_type"] == "dnabarcoder" and "dnabarcoder_results" in st.session_state:
        results_df = st.session_state["dnabarcoder_results"]
        
        # Create the download button if files are available
        if hasattr(results_df, 'attrs') and (
            'classified_file_path' in results_df.attrs or 'krona_html_path' in results_df.attrs
        ):
            # Create zip file with all results
            zip_buffer, filename = create_dnabarcoder_export(results_df)
            
            files_to_zip = {}
            if 'classified_file_path' in results_df.attrs:
                files_to_zip["classification_results.classified"] = True
            if 'krona_html_path' in results_df.attrs:
                files_to_zip["taxonomic_visualization.html"] = True
            
            st.download_button(
                label="Download Results",
                data=zip_buffer,
                file_name=filename,
                mime="application/zip",
                help="Download all result files (.classified and .krona.html) in a zip archive"
            )
            
            file_list = ", ".join([f"{name}" for name in files_to_zip.keys()])
            st.caption(f"Downloaded zip file contains: {file_list}")
        else:
            st.error("No result files are available for download")