# Installation Guide

Complete installation guide for the Dataset Pipeline project.

## Prerequisites

### Required Software

1. **Python 3.8 or higher**
   ```bash
   python --version  # Should be >= 3.8
   ```

2. **FFmpeg** (for audio processing)

   - **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt-get install ffmpeg`

3. **vllm** (for validation step)
   ```bash
   pip install "vllm[audio]"
   ```

### Optional Software

- **Make** (for convenience commands)
  - macOS/Linux: Usually pre-installed
  - Windows: Install via [Chocolatey](https://chocolatey.org/) or use WSL

## Installation Steps

### 1. Clone or Download the Project

```bash
cd "C:\Users\arash\OneDrive\Desktop\STT project"
```

### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

#### Option A: Using pip (Simple)

```bash
# Install package in editable mode
pip install -e .

# Or with development tools
pip install -e ".[dev]"
```

#### Option B: Using Make (Recommended)

```bash
# Production installation
make install

# Development installation (includes testing tools)
make install-dev
```

#### Option C: Manual Installation

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

## Post-Installation Setup

### 1. Configure the Pipeline

```bash
# Copy example configuration
cp config/config.example.yaml config/config.yaml

# Edit the configuration
# Update input_dir, output_dir, and other settings
nano config/config.yaml  # or use your preferred editor
```

### 2. Set up Environment Variables (Optional)

```bash
# Copy example .env file
cp .env.example .env

# Edit .env file with your settings
nano .env
```

### 3. Prepare Data Directories

```bash
# Input directory structure
mkdir -p data/input
mkdir -p data/output

# Place your WAV and SRT files in data/input/
```

### 4. Start vllm Servers (for validation)

```bash
# Terminal 1: Primary Whisper model
vllm serve openai/whisper-large-v3 --gpu-memory-utilization 0.4 --port 8000

# Terminal 2: Secondary Whisper model
vllm serve openai/whisper-large-v3-turbo --gpu-memory-utilization 0.4 --port 8001
```

Or use the provided script:

```bash
bash scripts/setup_vllm.sh
```

## Verify Installation

### Check Package Installation

```bash
# Check if package is installed
pip show dataset-pipeline

# Try importing
python -c "from dataset_pipeline import DatasetPipeline; print('Success!')"
```

### Run Tests

```bash
# Run test suite
pytest tests/

# Or using make
make test
```

### Test the CLI

```bash
# Show help
dataset-pipeline --help

# Check version
dataset-pipeline --version
```

## Troubleshooting

### Issue: Module not found

**Problem**: `ModuleNotFoundError: No module named 'dataset_pipeline'`

**Solution**:
```bash
# Make sure you installed in editable mode
pip install -e .

# Or check your PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Issue: FFmpeg not found

**Problem**: `RuntimeWarning: Couldn't find ffmpeg or avconv`

**Solution**:
```bash
# Install FFmpeg
# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg

# Windows: Download from ffmpeg.org and add to PATH
```

### Issue: vllm connection error

**Problem**: `Connection refused to localhost:8000`

**Solution**:
- Make sure vllm servers are running
- Check if ports 8000 and 8001 are available
- Try: `curl http://localhost:8000/health`

### Issue: Import errors for pysrt or hazm

**Problem**: `ModuleNotFoundError: No module named 'pysrt'`

**Solution**:
```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or install specific package
pip install pysrt hazm
```

## Docker Installation (Alternative)

If you prefer using Docker:

```dockerfile
# Create a Dockerfile (not included in base project)
FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copy project
WORKDIR /app
COPY . /app

# Install dependencies
RUN pip install -e .

# Run
CMD ["dataset-pipeline"]
```

Build and run:
```bash
docker build -t dataset-pipeline .
docker run -v $(pwd)/data:/app/data dataset-pipeline
```

## Next Steps

After installation:

1. ✅ Configure your pipeline in `config/config.yaml`
2. ✅ Prepare your audio and SRT files in `data/input/`
3. ✅ Start vllm servers
4. ✅ Run the pipeline: `dataset-pipeline`

For detailed usage instructions, see [README.md](README.md).
