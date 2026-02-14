# Audio Dataset Creation Pipeline

> A production-level pipeline for creating high-quality audio datasets from audio files and SRT transcriptions.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 📋 Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Development](#development)
- [Testing](#testing)
- [License](#license)

## ✨ Features

1. **Audio Chunking**: Split audio files based on SRT timestamps with validation
2. **Audio Merging** (optional): Merge audio segments in pairs for longer samples
3. **Dual-Model Validation**: Validate transcriptions using two Whisper models via vllm
4. **Production-Ready**: Modular architecture, comprehensive logging, error handling
5. **Configurable**: YAML-based configuration with environment variable support
6. **Batch Processing**: Automatically processes all audio files in a directory
7. **CLI Interface**: User-friendly command-line interface with multiple options

## 🏗 Architecture

The pipeline is designed with a modular architecture:

```
┌─────────────────┐
│   Audio + SRT   │
│      Files      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Step 1: Chunk  │  Split by SRT timestamps
│   AudioChunker  │  Filter by duration
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Step 2: Merge  │  Merge pairs (optional)
│   AudioMerger   │  Combine audio + text
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Step 3: Validate│  Dual Whisper models
│   Validator     │  Boundary checking
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Validated Data  │
│  + Flagged      │
└─────────────────┘
```

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- FFmpeg installed on your system
- (Optional) vllm servers for validation

### Install from source

```bash
# Clone or navigate to the project
cd "STT project"

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Using Make (recommended)

```bash
# Install production dependencies
make install

# Install development dependencies
make install-dev
```

## 🎯 Quick Start

### 1. Setup Configuration

```bash
# Copy example config
cp config/config.example.yaml config/config.yaml

# Edit config.yaml with your settings
# Set input_dir, output_dir, and other parameters
```

### 2. Prepare Your Data

Place your audio files (`.wav`) and corresponding SRT files in the input directory:

```
data/input/
├── audio1.wav
├── audio1.srt (or audio1.fa.srt)
├── audio2.wav
└── audio2.srt
```

### 3. Start vllm Servers (for validation)

```bash
# Terminal 1: Primary model
vllm serve openai/whisper-large-v3 --port 8000

# Terminal 2: Secondary model
vllm serve openai/whisper-large-v3-turbo --port 8001

# Or use the setup script
bash scripts/setup_vllm.sh
```

### 4. Run the Pipeline

```bash
# Using the run script
python run_pipeline.py

# Or using the installed CLI
dataset-pipeline

# Or using make
make run
```

## ⚙ Configuration

Configuration is managed through YAML files in the `config/` directory.

### Main Configuration File

[config/config.yaml](config/config.yaml) (create from [config.example.yaml](config/config.example.yaml)):

```yaml
# Input/Output
input_dir: "data/input"
output_dir: "data/output"

# Enable/disable steps
steps:
  chunking: true
  merging: false    # Optional
  validation: true

# Validation settings
validation:
  max_workers: 8    # Concurrent workers
  primary_port: 8000
  secondary_port: 8001
```

### Environment Variables

You can override config values with environment variables:

```bash
export DATASET_INPUT_DIR="path/to/audio"
export DATASET_OUTPUT_DIR="path/to/output"
export DATASET_MAX_WORKERS=16
export WHISPER_PRIMARY_PORT=8000
export WHISPER_SECONDARY_PORT=8001
```

Or create a `.env` file (copy from [.env.example](.env.example)).

## 📖 Usage

### Command-Line Interface

```bash
# Basic usage with default config
dataset-pipeline

# Custom config file
dataset-pipeline --config my_config.yaml

# Override input/output directories
dataset-pipeline --input data/my_audio --output data/my_output

# Skip optional steps
dataset-pipeline --skip-merging
dataset-pipeline --skip-validation

# Adjust logging
dataset-pipeline --log-level DEBUG

# Show help
dataset-pipeline --help
```

### Python API

```python
from dataset_pipeline import DatasetPipeline
from dataset_pipeline.config import Config

# Load configuration
config = Config.from_yaml("config/config.yaml")

# Create and run pipeline
pipeline = DatasetPipeline(config)
results = pipeline.run()

print(f"Steps completed: {results['steps_completed']}")
```

## 📁 Project Structure

```
STT project/
├── src/
│   └── dataset_pipeline/         # Main package
│       ├── __init__.py
│       ├── cli.py               # Command-line interface
│       ├── config.py            # Configuration management
│       ├── pipeline.py          # Main orchestrator
│       ├── chunker.py           # Audio chunking
│       ├── merger.py            # Audio merging
│       ├── validator.py         # Transcription validation
│       └── utils.py             # Utility functions
│
├── tests/                       # Test suite
│   ├── test_config.py
│   ├── test_utils.py
│   └── test_chunker.py
│
├── config/                      # Configuration files
│   ├── config.yaml             # Main config (create from example)
│   └── config.example.yaml     # Example configuration
│
├── data/                        # Data directory
│   ├── input/                  # Input audio + SRT files
│   └── output/                 # Pipeline outputs
│       ├── chunked/            # Step 1 output
│       ├── merged/             # Step 2 output (if enabled)
│       ├── metadata_validated.csv
│       └── flagged_files.csv
│
├── logs/                        # Log files
│   └── pipeline.log
│
├── scripts/                     # Helper scripts
│   └── setup_vllm.sh           # Start vllm servers
│
├── pyproject.toml              # Project metadata & dependencies
├── requirements.txt            # Production dependencies
├── requirements-dev.txt        # Development dependencies
├── run_pipeline.py             # Convenience runner script
├── Makefile                    # Development commands
├── .env.example                # Example environment variables
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

## 🛠 Development

### Setup Development Environment

```bash
# Install with development dependencies
make install-dev

# Or manually
pip install -e ".[dev]"
pip install -r requirements-dev.txt
```

### Code Quality

```bash
# Format code
make format

# Run linters
make lint

# Run tests
make test

# Run tests with coverage
make test-cov
```

### Pre-commit Hooks (recommended)

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/dataset_pipeline --cov-report=html

# Run specific test file
pytest tests/test_config.py -v

# Using make
make test
make test-cov
```

## 📊 Pipeline Steps Explained

### Step 1: Chunking

Splits audio files based on SRT timestamps:
- Validates minimum duration (default: 500ms)
- Truncates overlapping segments
- Filters empty text segments
- Creates: `chunked/` directory + `metadata_chunked.csv`

### Step 2: Merging (Optional)

Merges audio segments in pairs:
- Optionally keeps/discards first segment
- Combines audio and text
- Creates: `merged/` directory + `metadata_merged.csv`

### Step 3: Validation

Validates transcriptions using dual Whisper models:
- **Primary Model** (Large V3): High accuracy transcription
- **Secondary Model** (Turbo): Judge/validator for disagreements
- Checks first/last N words (configurable boundary window)
- Flags files with model disagreements for manual review
- Creates: `metadata_validated.csv` + `flagged_files.csv`

### Validation Logic

```
┌─────────────────┐
│   SRT Text      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Primary Model   │  Transcribe & check boundaries
│  (Large V3)     │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Match?  │
    └────┬────┘
         │
    Yes  │  No
    ▼    │    ▼
┌────┐   │   ┌────────────┐
│Keep│   │   │ Secondary  │  Ask Turbo model
│SRT │   │   │   Model    │
└────┘   │   └──────┬─────┘
         │          │
         │     ┌────┴────┐
         │     │Consensus?│
         │     └────┬────┘
         │          │
         │     Yes  │  No
         │     ▼    │   ▼
         │   ┌────┐ │ ┌────┐
         │   │Use │ │ │Flag│
         └───│ V3 │ │ │for │
             └────┘ │ │Rev.│
                    │ └────┘
                    └──────┘
```

## 📝 Output Files

All metadata files use pipe-delimited CSV format:

**Validated files** (`metadata_validated.csv`):
```
file_name|text
segment_0001.wav|متن فارسی
```

**Flagged files** (`flagged_files.csv`):
```
file_name|srt|primary_v3|secondary_turbo|reason
segment_0042.wav|original|model1 text|model2 text|Model Disagreement
```

## 🔧 Troubleshooting

### Missing SRT Files

The pipeline will log and skip audio files without corresponding SRT files:
```
WARNING: No SRT found for: audio.wav
```

### vllm Connection Errors

Ensure vllm servers are running:
```bash
# Check if servers are responding
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### Memory Issues

Reduce `max_workers` in config if you encounter memory errors:
```yaml
validation:
  max_workers: 4  # Reduce from 8
```

## 📄 License

Generated for STT Project

## 🙏 Acknowledgments

- Uses [Whisper](https://github.com/openai/whisper) models for transcription
- [vllm](https://github.com/vllm-project/vllm) for efficient model serving
- [hazm](https://github.com/roshan-research/hazm) for Persian text normalization

---

For questions or issues, please check the documentation or create an issue.
