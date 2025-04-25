"""
Reusable UI components for the MycoAI application.
"""
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import streamlit as st

from constants import (
    TAXOTAGGER_DISPLAY_COLUMNS, METHOD_OPTIONS, 
    DEFAULT_CUTOFF, MIN_ALLOWED_CUTOFF, MAX_ALLOWED_CUTOFF
)
from taxotagger.defaults import PRETRAINED_MODELS, TAXONOMY_LEVELS


def create_header() -> None:
    """Create the application header with logo and title."""
    from constants import LOGO_IMAGE
    
    col1, col2 = st.columns([1, 6], vertical_alignment="bottom")
    with col1:
        st.image(LOGO_IMAGE, width=90)
    with col2:
        st.title("MycoAI")
        st.markdown("*Taxonomy identification for fungi, powered by AI, Semantic Search, and DNABarcoder*")


def create_labeled_widget(label: str, widget_func: Callable, *args, **kwargs) -> Any:
    """
    Create a two-column layout with a label and a widget.
    
    Args:
        label: The label to display
        widget_func: The Streamlit widget function to call
        *args, **kwargs: Arguments to pass to the widget function
        
    Returns:
        The return value of the widget function
    """
    col1, col2 = st.columns([2, 1])
    with col1:
        st.write(label)
    with col2:
        # Set label_visibility to collapsed by default if not specified
        if "label_visibility" not in kwargs:
            kwargs["label_visibility"] = "collapsed"
        return widget_func(*args, **kwargs)


def create_method_selector() -> str:
    """
    Create the method selection widget.
    
    Returns:
        The selected method
    """
    return create_labeled_widget(
        "Method:", 
        st.selectbox,
        "Select method", 
        METHOD_OPTIONS, 
        index=0
    )


def create_taxotagger_settings() -> None:
    """Create settings UI specific to TaxoTagger method."""
    # Embedding model selection
    model_options = PRETRAINED_MODELS.keys()
    st.session_state["selected_model"] = create_labeled_widget(
        "Select embedding model:",
        st.selectbox,
        "Select embedding model", 
        model_options
    )
    
    # Number of top matches
    st.session_state["top_n"] = create_labeled_widget(
        "Number of top matched results to display:",
        st.number_input,
        "Top results",  # Adding a label for the number_input widget
        min_value=1,
        max_value=5,
        value=2,
        step=1,
        format="%d"
    )


def create_dataset_info_expander(dnabarcoder, selected_dataset: str, dataset_dict: Dict[str, str]) -> None:
    """
    Create an expander with dataset information.
    
    Args:
        dnabarcoder: DNABarcoder wrapper instance
        selected_dataset: ID of the selected dataset
        dataset_dict: Dictionary mapping dataset IDs to display names
    """
    with st.expander("Dataset Information", expanded=False):
        try:
            dataset_info = dnabarcoder.get_dataset_info(selected_dataset)
            
            # Display dataset information
            st.markdown(f"**{dataset_dict.get(selected_dataset, selected_dataset)}**")
            st.markdown(f"* Reference sequences: {dataset_info['sequence_count']}")
            st.markdown(f"* Taxonomic ranks: {', '.join(dataset_info['taxonomic_ranks']) if dataset_info['taxonomic_ranks'] else 'Not specified'}")
            
            # Display available cutoffs if any
            if dataset_info.get('cutoffs'):
                cutoffs_html = "<div style='font-size: 0.9em;'><strong>Taxonomic Cutoffs:</strong><br/>"
                cutoffs_html += "<table style='width: 100%; max-width: 400px;'>"
                for rank, cutoff in dataset_info['cutoffs'].items():
                    cutoffs_html += f"<tr><td>{rank}</td><td>{cutoff}</td></tr>"
                cutoffs_html += "</table></div>"
                st.markdown(cutoffs_html, unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"Unable to load dataset information: {str(e)}")


def create_dnabarcoder_settings(dnabarcoder) -> None:
    """
    Create settings UI specific to DNABarcoder method.
    
    Args:
        dnabarcoder: DNABarcoder wrapper instance
    """
    from constants import DEFAULT_DATASETS
    
    # Try to get available datasets
    try:
        DNABARCODER_DATASETS = dnabarcoder.get_available_datasets()
        if not DNABARCODER_DATASETS:
            DNABARCODER_DATASETS = DEFAULT_DATASETS
    except Exception as e:
        st.warning(f"Error loading DNABarcoder datasets: {str(e)}. Using default datasets.")
        DNABARCODER_DATASETS = DEFAULT_DATASETS
    
    # Reference dataset selection
    if DNABARCODER_DATASETS:
        # Create a dictionary for displaying nice names in the UI
        dataset_dict = {dataset_id: display_name for dataset_id, display_name in DNABARCODER_DATASETS}
        
        st.session_state["reference_dataset"] = create_labeled_widget(
            "Reference dataset:",
            st.selectbox,
            "Select reference dataset", 
            [dataset_id for dataset_id, _ in DNABARCODER_DATASETS],
            format_func=lambda x: dataset_dict.get(x, x)
        )
        
        # Display dataset information in an expander
        create_dataset_info_expander(dnabarcoder, st.session_state["reference_dataset"], dataset_dict)
    else:
        st.error("No DNABarcoder reference datasets found. Please run the setup_datasets.py script.")
        st.session_state["reference_dataset"] = "unite2024ITS"
    
    # Similarity cutoff selection
    st.session_state["classification_method"] = create_labeled_widget(
        "Similarity cutoff:",
        st.radio,
        "Similarity cutoff",
        ["Local", "Single"],
        horizontal=True,
        index=0,
        help="Local: Uses reference-specific cutoffs. Single: Uses a single cutoff value for all taxa."
    )
    
    # Show text input only for single similarity cutoff method
    if st.session_state["classification_method"] == "Single":
        cutoff_input = create_labeled_widget(
            "Value:",
            st.text_input,
            "Similarity cutoff",
            value=str(DEFAULT_CUTOFF),
            help=f"Similarity threshold for classifying sequences. Enter a value between {MIN_ALLOWED_CUTOFF} and {MAX_ALLOWED_CUTOFF}. Higher values are more conservative."
        )
        
        # Validate the input as a float between MIN_ALLOWED_CUTOFF and MAX_ALLOWED_CUTOFF
        try:
            cutoff_value = float(cutoff_input)
            if MIN_ALLOWED_CUTOFF <= cutoff_value <= MAX_ALLOWED_CUTOFF:
                st.session_state["custom_cutoff"] = cutoff_value
            else:
                st.error(f"Similarity cutoff must be between {MIN_ALLOWED_CUTOFF} and {MAX_ALLOWED_CUTOFF}")
                st.session_state["custom_cutoff"] = None
                st.stop()
        except ValueError:
            st.error("Please enter a valid number for similarity cutoff")
            st.session_state["custom_cutoff"] = None
            st.stop()
    else:
        # For local method, use the predefined cutoffs from the dataset files
        st.session_state["custom_cutoff"] = None
    
    # Set default taxonomic rank to "species" - no UI option for changing it
    st.session_state["taxonomic_rank"] = "species"


def create_settings_section(dnabarcoder) -> None:
    """
    Create the settings section with method-specific options.
    
    Args:
        dnabarcoder: DNABarcoder wrapper instance
    """
    st.subheader("Settings")
    
    # Method selection
    st.session_state["selected_method"] = create_method_selector()
    
    # Method-specific settings
    if st.session_state["selected_method"] == "taxotagger":
        create_taxotagger_settings()
    elif st.session_state["selected_method"] == "dnabarcoder":
        create_dnabarcoder_settings(dnabarcoder)
    else:
        # No additional settings for other methods yet
        pass


def create_taxotagger_results_display(results_by_seq: Dict[str, List[Dict[str, Any]]]) -> None:
    """
    Display TaxoTagger results.
    
    Args:
        results_by_seq: Dictionary of results organized by sequence ID
    """
    import pandas as pd

    selected_seq_id = st.selectbox(
        "For input sequence:",
        results_by_seq.keys(),
    )

    df = pd.DataFrame(results_by_seq[selected_seq_id])
    
    # Create a display table for results
    if not df.empty:
        # Format the data for display
        for level in TAXONOMY_LEVELS:
            level_cap = level.capitalize()
            if level_cap in df.columns:
                df[level_cap] = df.apply(
                    lambda row: f"{row[level_cap]} ({row[level_cap+'_Hit']};{row[level_cap+'_Similarity']:.4f})"
                    if row[level_cap] and row[level_cap] != "No match found"
                    else row[level_cap],
                    axis=1,
                )
        
        st.dataframe(
            df[TAXOTAGGER_DISPLAY_COLUMNS],
            use_container_width=True,
            hide_index=True,
        )


def create_classification_tab(filtered_df, available_columns) -> None:
    """
    Create the classification results tab for DNABarcoder results.
    
    Args:
        filtered_df: DataFrame containing classification results
        available_columns: List of columns to display
    """
    st.dataframe(
        filtered_df[available_columns],
        use_container_width=True,
        hide_index=True,
    )


def create_visualization_tab(df) -> None:
    """
    Create the taxonomic visualization tab for DNABarcoder results.
    
    Args:
        df: DataFrame containing classification results with visualization data
    """
    import os
    import webbrowser
    
    # Check if Krona HTML visualization is available
    if hasattr(df, 'attrs') and 'krona_html_path' in df.attrs:
        krona_file = df.attrs['krona_html_path']
        
        if os.path.exists(krona_file):
            # Display information about the visualization
            st.info("The taxonomic visualization shows hierarchical relationships of classified organisms.")
            
            # Create a function to open the file in a new browser tab
            def open_krona_file():
                webbrowser.open_new_tab(f"file://{krona_file}")
            
            # Display the button
            st.button(
                "View Krona Visualization", 
                on_click=open_krona_file,
                use_container_width=True,
                type="primary"
            )
            
            # Add helpful information about the visualization
            st.caption("Opens in a new browser tab for full interactive visualization experience.")
        else:
            st.warning("The Krona visualization file could not be found at the expected location.")
            st.info("Try running the classification again or check if the DNABarcoder is properly configured.")
    else:
        st.info("Krona visualization is not available for this classification result.")


def create_sequence_selector(sequence_ids, display_ids) -> str:
    """
    Create a dropdown to select a sequence to display.
    
    Args:
        sequence_ids: List of sequence IDs
        display_ids: Dictionary mapping sequence IDs to display names
        
    Returns:
        The selected sequence ID
    """
    st.markdown("### Sequence Selection")
    return st.selectbox(
        "Choose sequence to display:",
        options=list(display_ids.keys()),
        format_func=lambda x: display_ids[x],
        key="sequence_selector_top"
    )


def create_footer() -> None:
    """Create the application footer."""
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center;">
            <p style="font-size: smaller; color: gray;">
                © 2023 MycoAI. All rights reserved.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )