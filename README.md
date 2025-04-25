# MycoAI Webapp

A webapp for fungal DNA taxonomy identification, integrating multiple classification methods:

- TaxoTagger - Taxonomy identification powered by AI and Semantic Search
- DNABarcoder - Classification using similarity cutoffs
- MycoAI-CNN and MycoAI-BERT (coming soon)

## Installation

1. Clone this repository

```bash
git clone https://github.com/MycoAI/mycoai-webapp-demo.git
```

2. Install the required packages

```bash
# Go to the mycoai-webapp-demo directory
cd mycoai-webapp-demo

# Create a new conda environment `mycoai-webapp`
conda create -n mycoai-webapp python=3.10

# Activate the conda environment
conda activate mycoai-webapp

# Install the required packages
pip install -r requirements.txt

# Install BLAST (required for DNABarcoder)
# For MacOS
brew install blast
# For Ubuntu/Debian
apt-get install ncbi-blast+
```

3. Copy DNABarcoder Reference Datasets

To copy DNABarcoder reference datasets from a dnabarcoder repository to your webapp, use the provided script:

```bash
# First, clone the dnabarcoder repository if you don't have it already
git clone https://github.com/vuthuyduong/dnabarcoder.git

# Then run the setup script
python setup_datasets.py --dnabarcoder_path /path/to/dnabarcoder
```

This script will organize the datasets as follows:

- `data/dnabarcoder/UNITE2024ITS/` - Contains all UNITE ITS full region files
- `data/dnabarcoder/UNITE2024ITS1/` - Contains all UNITE ITS1 region files
- `data/dnabarcoder/UNITE2024ITS2/` - Contains all UNITE ITS2 region files
- `data/dnabarcoder/CBSITS/` - Contains all CBS ITS dataset files

Each dataset directory contains the necessary reference FASTA, classification, and cutoff files for that dataset.

## Running the webapp

1. Set the environment variables `MYCOAI_HOME`

Set the environment variable `MYCOAI_HOME` to the path of the `data` directory in this repository. This directory contains the example vector databases and reference datasets.

```bash
# On Linux or MacOS
export MYCOAI_HOME=/path/to/mycoai-webapp-demo/data

# Or on Windows
set MYCOAI_HOME=C:\path\to\mycoai-webapp-demo\data
```

2. Start the webapp

```bash
# Make sure you are in the mycoai-webapp-demo directory and the conda environment is activated
cd mycoai-webapp-demo
conda activate mycoai-webapp

# Run the webapp
streamlit run app.py --server.fileWatcherType none
```

Then you can open the webapp in your browser by visiting the URL http://localhost:8501.

> [!NOTE]
> For the first time running, the webapp will download the embedding model files for TaxoTagger. This may take a few minutes depending on the internet connection speed.

## Using the MycoAI Webapp

The MycoAI webapp offers different methods for DNA taxonomy identification:

### TaxoTagger Method

- Upload your FASTA sequence(s) or enter them directly
- Select "taxotagger" from the Method dropdown
- Choose an embedding model
- Set the number of top results to display
- Click "Run Analysis"

### DNABarcoder Method

- Upload your FASTA sequence(s) or enter them directly
- Select "dnabarcoder" from the Method dropdown
- Choose a reference dataset (UNITE 2024 ITS, ITS1, ITS2, or CBS ITS)
- Click "Run Analysis"

Results will use optimized similarity cutoffs determined for each dataset and provide species-level identification.

### MycoAI-CNN and MycoAI-BERT (Coming Soon)

These methods will be implemented in future updates.

## For production deployment

The reference datasets provided in the `data` directory are for demo purposes only. To use the webapp in production, you should prepare the complete reference datasets:

1. For TaxoTagger, build the vector database by following the instructions in the [TaxoTagger Doc](https://mycoai.github.io/taxotagger/latest/quickstart/#build-a-vector-database).