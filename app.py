"""
MycoAI Web Application

Web application for identifying fungal DNA barcodes using multiple methods:
- TaxoTagger (embeddings-based matching)
- DNABarcoder (sequence alignment-based classification)
- MycoAI-CNN (neural network classifier)
- MycoAI-BERT (language model classifier)
"""
import streamlit as st
from taxotagger import ProjectConfig, TaxoTagger
from dnabarcoder_wrapper import DNABarcoderWrapper

from constants import LOGO_IMAGE, PAGE_TITLE
from utils import (
    validate_input, process_uploaded_files,
    create_header, create_settings_section, create_footer,
    process_fasta_and_run, process_results,
    display_results, create_export_section
)


# Configure page
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=LOGO_IMAGE,
    layout="centered",
)


# Initialize application resources
@st.cache_resource
def initialize_taxotagger():
    """Initialize the TaxoTagger object."""
    config = ProjectConfig()
    return TaxoTagger(config)


@st.cache_resource
def initialize_dnabarcoder():
    """Initialize the DNABarcoder wrapper."""
    return DNABarcoderWrapper()


def main():
    """Main application function."""
    tt = initialize_taxotagger()
    dnabarcoder = initialize_dnabarcoder()
    create_header()
    
    # Input section
    st.subheader("Enter DNA Sequence")
    input_method = st.radio(
        "Choose input method:",
        ["Upload FASTA file(s)", "Enter FASTA text"],
        horizontal=True,
        label_visibility="collapsed",
        on_change=st.session_state.clear,
    )

    if input_method == "Enter FASTA text":
        fasta_content = st.text_area(
            "Enter FASTA sequence(s):",
            height=200,
            placeholder=">seq1\nATGC...\n>seq2\nCGTA...",
        )
        if fasta_content:
            validate_input(fasta_content)
        else:
            st.session_state.clear()

    else:
        uploaded_files = st.file_uploader(
            "Upload FASTA files (max 100 sequences total)",
            type=["fasta", "fas", "fa"],
            accept_multiple_files=True,
        )
        if uploaded_files:
            fasta_content = process_uploaded_files(uploaded_files)
            validate_input(fasta_content)
        else:
            st.session_state.clear()
    
    # Settings section
    create_settings_section(dnabarcoder)
    
    # Run button
    if st.button("Run Analysis", type="primary", use_container_width=True):
        if "fasta_content" not in st.session_state:
            st.error("Please provide FASTA input before running the analysis.", icon="💡")
            st.stop()

        # Run the selected analysis method
        results = process_fasta_and_run(
            st.session_state["fasta_content"], 
            st.session_state["selected_method"],
            tt,
            dnabarcoder
        )
        
        # Process and store results
        process_results(results, st.session_state["selected_method"])
    
    display_results()
    create_export_section()
    create_footer()


if __name__ == "__main__":
    main()