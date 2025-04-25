import os
import tempfile
import subprocess
import shutil
import glob
from typing import Dict, List, Optional, Any, Tuple, Union
import pandas as pd
from constants import MIN_ALLOWED_CUTOFF, MAX_ALLOWED_CUTOFF

from .utils import (
    parse_fasta,
    create_temp_fasta_file,
    run_command,
    load_cutoffs_file,
    get_available_reference_datasets,
    parse_classification_result,
    get_cutoffs_file_path
)


class DNABarcoderWrapper:
    """Wrapper class for DNABarcoder functionality."""
    
    def __init__(self, 
                 dnabarcoder_path: Optional[str] = None,
                 data_dir: Optional[str] = None):
        """
        Initialize the DNABarcoder wrapper.
        
        Args:
            dnabarcoder_path: Path to dnabarcoder.py script. If None, will use environment.
            data_dir: Path to the data directory. If None, will use MYCOAI_HOME environment.
        """
        # Set the dnabarcoder path
        self.dnabarcoder_path = dnabarcoder_path
            
        # Set the data directory
        self.data_dir = data_dir if data_dir else os.environ.get('MYCOAI_HOME', 'data')
            
        # Check if the data directory exists
        if not os.path.exists(self.data_dir):
            raise ValueError(f"Data directory {self.data_dir} does not exist")
            
        # Create a temporary working directory
        self.temp_dir = tempfile.mkdtemp(prefix="dnabarcoder_")
        
        # Define path for the dnabarcoder data
        self.dnabarcoder_dir = os.path.join(self.data_dir, 'dnabarcoder')
        
        # Ensure directory exists
        os.makedirs(self.dnabarcoder_dir, exist_ok=True)
        
    def __del__(self):
        """Clean up temporary directory when the object is deleted."""
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
      
    def _get_script_path(self) -> str:
        """
        Get the path to the dnabarcoder.py script.
        
        Returns:
            The path to use in commands for the dnabarcoder.py script
        """
        if self.dnabarcoder_path:
            return self.dnabarcoder_path
        return "dnabarcoder/dnabarcoder.py"
    
    def _build_command_base(self, command: str) -> List[str]:
        """
        Build the base command for dnabarcoder operations.
        
        Args:
            command: The dnabarcoder subcommand (search, classify, etc.)
            
        Returns:
            List with the base command elements
        """
        return [
            "python",
            self._get_script_path(),
            command
        ]
    
    def _find_dataset_file(self, dataset_name: str, extension: str, exclude_pattern: Optional[str] = None) -> str:
        """
        Find a specific file type in the dataset directory.
        
        Args:
            dataset_name: Name of the dataset
            extension: File extension to search for (e.g., '.fasta', '.classification')
            exclude_pattern: Optional pattern to exclude from results
            
        Returns:
            Path to the first matching file
            
        Raises:
            ValueError: If no matching file is found
        """
        dataset_dir = os.path.join(self.dnabarcoder_dir, dataset_name)
        if not os.path.exists(dataset_dir):
            raise ValueError(f"Dataset directory {dataset_name} not found at {dataset_dir}")
            
        # Find files with the specified extension
        files = glob.glob(os.path.join(dataset_dir, f"*{extension}"))
        if not files:
            raise ValueError(f"No {extension} file found in {dataset_dir}")
            
        # If we need to exclude files with a specific pattern
        if exclude_pattern:
            filtered_files = [f for f in files if exclude_pattern not in os.path.basename(f)]
            if filtered_files:
                return filtered_files[0]
                
        # Return the first file found
        return files[0]
    
    def get_available_datasets(self) -> List[Tuple[str, str]]:
        """
        Get a list of available reference datasets.
        
        Returns:
            List of tuples (dataset_id, display_name)
        """
        return get_available_reference_datasets(self.data_dir)
    
    def search(self, 
               fasta_content: str, 
               reference_dataset: str, 
               min_alignment_length: int = 400) -> str:
        """
        Search for best matches in the reference dataset.
        
        Args:
            fasta_content: FASTA content to search
            reference_dataset: Name of the reference dataset (without extension)
            min_alignment_length: Minimum alignment length for BLAST
            
        Returns:
            Path to the bestmatch result file
        """
        input_file = None
        try:
            # Create temporary input file
            input_file = create_temp_fasta_file(fasta_content)
            
            # Find reference file in the dataset directory
            reference_file = self._find_dataset_file(
                reference_dataset, 
                '.fasta', 
                exclude_pattern="_classification"
            )
                
            # Build the command
            cmd = self._build_command_base("search")
            cmd.extend([
                "-i", input_file,
                "-r", reference_file,
                "-ml", str(min_alignment_length),
                "-o", self.temp_dir
            ])
                
            # Run the command
            stdout, stderr, returncode = run_command(cmd)
            
            if returncode != 0:
                raise RuntimeError(f"DNABarcoder search failed: {stderr}")
                
            # Get the output file name
            input_basename = os.path.basename(input_file)
            reference_basename = os.path.basename(reference_file)
            expected_output = os.path.join(
                self.temp_dir, 
                f"{input_basename}.{reference_basename.replace('.fasta', '')}_BLAST.bestmatch"
            )
            
            # Check if the result file exists
            if os.path.exists(expected_output):
                return expected_output
            
            # If the expected file doesn't exist, look for any bestmatch file
            bestmatch_files = [f for f in os.listdir(self.temp_dir) if f.endswith('.bestmatch')]
            if bestmatch_files:
                return os.path.join(self.temp_dir, bestmatch_files[0])
            
            raise FileNotFoundError(f"Search result file not found in {self.temp_dir}")
            
        except Exception as e:
            raise RuntimeError(f"Error during DNABarcoder search: {str(e)}") from e
            
        finally:
            # Clean up the temporary input file if it exists
            if input_file and os.path.exists(input_file):
                try:
                    os.unlink(input_file)
                except:
                    pass
        
    def _find_krona_html_file(self) -> Optional[str]:
        """
        Find the auto-generated Krona HTML file in the temp directory.
        
        Returns:
            Path to the Krona HTML file, or None if not found
        """
        # Look for any .krona.html files in the temp directory
        krona_files = [f for f in os.listdir(self.temp_dir) if f.endswith('.krona.html')]
        
        if krona_files:
            return os.path.join(self.temp_dir, krona_files[0])
            
        return None

    def classify(self, 
                bestmatch_file: str, 
                reference_dataset: str, 
                method: str = "local",
                cutoff: Optional[float] = None,
                rank: str = "species",
                confidence: Optional[float] = None) -> Tuple[str, pd.DataFrame, Optional[str]]:
        """
        Classify sequences using the best matches and cutoffs.
        
        Args:
            bestmatch_file: Path to the bestmatch file from search
            reference_dataset: Name of the reference dataset (without extension)
            method: Classification method ("local" or "single")
            cutoff: Similarity cutoff value (for single method)
            rank: Taxonomic rank for classification (species, genus, etc.)
            confidence: Confidence threshold
            
        Returns:
            Tuple of (result_file_path, results_dataframe, krona_html_path)
        """
        try:
            # Find classification file in the dataset directory
            classification_file = self._find_dataset_file(reference_dataset, '.classification')
            
            # Build command base
            cmd = self._build_command_base("classify")
            cmd.extend([
                "-i", bestmatch_file,
                "-c", classification_file,
                "-o", self.temp_dir
            ])
            
            # Add method-specific parameters
            if method.lower() == "single" and cutoff is not None:
                # For single method, use a single cutoff value for all taxa
                cmd.extend(["-cutoff", str(cutoff)])
            else:
                # For local method, use the cutoffs file
                cutoffs_file = get_cutoffs_file_path(self.data_dir, reference_dataset)
                cmd.extend(["-cutoffs", cutoffs_file])
            
            # Add rank if specified
            if rank:
                cmd.extend(["-rank", rank])
                
            # Add confidence if specified
            if confidence is not None:
                cmd.extend(["-confidence", str(confidence)])
            
            # Run the command
            stdout, stderr, returncode = run_command(cmd)
            
            if returncode != 0:
                raise RuntimeError(f"DNABarcoder classify failed: {stderr}")
            
            # Look for the .classified file
            classified_files = [f for f in os.listdir(self.temp_dir) if f.endswith('.classified')]
            if not classified_files:
                raise FileNotFoundError(f"No .classified result files found in {self.temp_dir}")
                
            classified_file = os.path.join(self.temp_dir, classified_files[0])
            results_df = parse_classification_result(classified_file)
    
            # Look for Krona HTML file
            krona_html_path = self._find_krona_html_file()
            
            # Store the classified file path in DataFrame metadata
            results_df.attrs['classified_file_path'] = classified_file
            
            return classified_file, results_df, krona_html_path
            
        except Exception as e:
            raise RuntimeError(f"Error during DNABarcoder classification: {str(e)}") from e

    def run_classification(self, 
                          fasta_content: str, 
                          reference_dataset: str, 
                          method: str = "local",
                          cutoff: Optional[float] = None,
                          min_alignment_length: int = 400,
                          rank: str = "species",
                          confidence: Optional[float] = None) -> pd.DataFrame:
        """
        Run the full classification pipeline: search and classify.
        
        Args:
            fasta_content: FASTA content to classify
            reference_dataset: Name of the reference dataset (without extension)
            method: Classification method ("local" or "single")
            cutoff: Similarity cutoff value (for single method)
            min_alignment_length: Minimum alignment length for BLAST
            rank: Taxonomic rank for classification (species, genus, etc.)
            confidence: Confidence threshold
            
        Returns:
            DataFrame with classification results and result file paths in metadata
        """
        try:
            # Validate cutoff if method is single
            if method.lower() == "single" and cutoff is not None:
                if not (MIN_ALLOWED_CUTOFF <= cutoff <= MAX_ALLOWED_CUTOFF):
                    error_msg = f"Invalid cutoff value: {cutoff}. Must be between {MIN_ALLOWED_CUTOFF} and {MAX_ALLOWED_CUTOFF}."
                    return pd.DataFrame({"Error": [error_msg]})
            
            # First, search for best matches
            bestmatch_file = self.search(
                fasta_content=fasta_content,
                reference_dataset=reference_dataset,
                min_alignment_length=min_alignment_length
            )
            
            # Then classify the sequences
            classified_file, results_df, krona_html_path = self.classify(
                bestmatch_file=bestmatch_file,
                reference_dataset=reference_dataset,
                method=method,
                cutoff=cutoff,
                rank=rank,
                confidence=confidence
            )
            
            # Store file paths and parameters in DataFrame metadata
            results_df.attrs['classified_file_path'] = classified_file
            
            if krona_html_path:
                results_df.attrs['krona_html_path'] = krona_html_path
                
            # Add classification method and parameters to DataFrame metadata
            results_df.attrs['classification_method'] = method
            if cutoff is not None:
                results_df.attrs['cutoff'] = cutoff
            if confidence is not None:
                results_df.attrs['confidence'] = confidence
            
            return results_df
            
        except Exception as e:
            # Handle errors gracefully
            error_msg = f"Error during classification: {str(e)}"
            print(error_msg)
            
            # Return an empty DataFrame with an error message
            return pd.DataFrame({"Error": [error_msg]})
            
    def get_rank_from_reference_dataset(self, reference_dataset: str) -> List[str]:
        """
        Get available taxonomic ranks from a reference dataset.
        
        Args:
            reference_dataset: Name of the reference dataset
            
        Returns:
            List of available taxonomic ranks
        """
        try:
            # Find classification file in the dataset directory
            classification_file = self._find_dataset_file(reference_dataset, '.classification')
            
            # Read the first line to get the header
            with open(classification_file, 'r') as f:
                header = f.readline().strip().split('\t')
            
            # Extract the taxonomic ranks
            ranks = []
            for rank in header[1:]:  # Skip ID column
                if rank.lower() not in ['strain number', 'id', 'strain', 'notes']:
                    ranks.append(rank.lower())
            
            return ranks
        except Exception:
            # Return default ranks if unable to extract from file
            return ["species", "genus", "family", "order", "class", "phylum"]
        
    def get_dataset_info(self, reference_dataset: str) -> Dict[str, Any]:
        """
        Get detailed information about a reference dataset.
        
        Args:
            reference_dataset: Name of the reference dataset
            
        Returns:
            Dictionary with dataset information
        """
        dataset_info = {
            "name": reference_dataset,
            "sequence_count": 0,
            "taxonomic_ranks": [],
            "cutoffs": {},
            "files": {
                "reference": "",
                "classification": "",
                "cutoffs": ""
            }
        }
        
        try:
            # Get dataset directory and check if it exists
            dataset_dir = os.path.join(self.dnabarcoder_dir, reference_dataset)
            if not os.path.exists(dataset_dir):
                raise ValueError(f"Dataset directory {reference_dataset} not found")
                
            # Find reference file
            try:
                reference_file = self._find_dataset_file(reference_dataset, '.fasta', "_classification")
                dataset_info["files"]["reference"] = reference_file
                
                # Count sequences in the reference file
                with open(reference_file, 'r') as f:
                    dataset_info["sequence_count"] = sum(1 for line in f if line.startswith('>'))
            except ValueError:
                pass
            
            # Find classification file
            try:
                classification_file = self._find_dataset_file(reference_dataset, '.classification')
                dataset_info["files"]["classification"] = classification_file
                dataset_info["taxonomic_ranks"] = self.get_rank_from_reference_dataset(reference_dataset)
            except ValueError:
                pass
            
            # Find cutoffs file
            try:
                cutoff_file = get_cutoffs_file_path(self.data_dir, reference_dataset)
                dataset_info["files"]["cutoffs"] = cutoff_file
                
                # Load cutoffs data if available
                try:
                    cutoffs_data = load_cutoffs_file(cutoff_file)
                    dataset_info["cutoffs"] = cutoffs_data.get("cut-off", {})
                except:
                    pass
            except ValueError:
                pass
            
            return dataset_info
            
        except Exception as e:
            dataset_info["error"] = str(e)
            return dataset_info