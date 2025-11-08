# PodKnow Installation Guide

This guide provides detailed instructions for installing PodKnow on different platforms with optimal configurations.

## Quick Start

### Automated Installation (Recommended)

The easiest way to install PodKnow is using our automated installation script:

```bash
# Download and run the installation script
curl -sSL https://raw.githubusercontent.com/podknow/podknow/main/scripts/install.py | python3
```

Or clone the repository and run locally:

```bash
git clone https://github.com/podknow/podknow.git
cd podknow
python scripts/install.py
```

### Using uv (Faster)

For faster installation, use the uv package manager:

```bash
python scripts/install.py --uv
```

## Platform-Specific Instructions

### macOS (Apple Silicon)

PodKnow is optimized for Apple Silicon Macs using MLX-Whisper for superior performance.

#### Prerequisites

1. **Python 3.13**: Install from [python.org](https://www.python.org/downloads/) or using Homebrew:
   ```bash
   brew install python@3.13
   ```

2. **Xcode Command Line Tools**: Required for MLX compilation:
   ```bash
   xcode-select --install
   ```

#### Installation

```bash
# Automated installation (detects Apple Silicon automatically)
python scripts/install.py

# Or using uv for faster installation
python scripts/install.py --uv

# Manual installation with Apple Silicon optimizations
pip install -e ".[apple-silicon,dev]"
```

#### Verification

```bash
# Verify MLX-Whisper is working
python -c "import mlx_whisper; print('MLX-Whisper version:', mlx_whisper.__version__)"

# Test PodKnow CLI
podknow --version
```

### macOS (Intel)

For Intel-based Macs, PodKnow uses the standard OpenAI Whisper implementation.

#### Installation

```bash
# Automated installation
python scripts/install.py

# Manual installation
pip install -e ".[standard,dev]"
```

### Linux

#### Prerequisites

1. **Python 3.13**: Install using your distribution's package manager or from source.

2. **Audio libraries**: Install system audio libraries:
   ```bash
   # Ubuntu/Debian
   sudo apt-get install libsndfile1 ffmpeg

   # CentOS/RHEL/Fedora
   sudo yum install libsndfile ffmpeg
   # or
   sudo dnf install libsndfile ffmpeg
   ```

#### Installation

```bash
# Automated installation
python scripts/install.py

# Manual installation
pip install -e ".[standard,dev]"
```

### Windows

#### Prerequisites

1. **Python 3.13**: Download from [python.org](https://www.python.org/downloads/windows/)
   - Make sure to check "Add Python to PATH" during installation

2. **Visual Studio Build Tools**: Required for some audio processing dependencies
   - Download from [Microsoft Visual Studio](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

#### Installation

Using PowerShell or Command Prompt:

```cmd
# Run the Windows installation script
scripts\install.bat

# Or use the Python script
python scripts\install.py
```

## Manual Installation

If you prefer to install manually or need custom configuration:

### 1. Create Virtual Environment

```bash
# Create virtual environment
python3.13 -m venv podknow-env

# Activate virtual environment
# On macOS/Linux:
source podknow-env/bin/activate
# On Windows:
podknow-env\Scripts\activate.bat
```

### 2. Install Dependencies

Choose the appropriate dependency set for your platform:

```bash
# Apple Silicon Mac
pip install -e ".[apple-silicon,dev]"

# Other platforms
pip install -e ".[standard,dev]"

# Minimal installation (no development tools)
pip install -e .
```

### 3. Verify Installation

```bash
# Check PodKnow installation
podknow --version
podknow --help

# Run tests
pytest tests/
```

## Package Managers

### Using pip

Standard Python package manager, works on all platforms:

```bash
pip install -e ".[dev]"
```

### Using uv (Recommended)

Faster alternative to pip with better dependency resolution:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install PodKnow
uv pip install -e ".[dev]"
```

### Using Poetry

If you prefer Poetry for dependency management:

```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install
```

## Development Installation

For development work on PodKnow:

```bash
# Clone repository
git clone https://github.com/podknow/podknow.git
cd podknow

# Install in development mode with all tools
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
make test
```

## Troubleshooting

### Common Issues

#### Python Version Issues

```bash
# Check Python version
python --version

# If wrong version, try:
python3.13 --version
```

#### MLX-Whisper Installation Fails (Apple Silicon)

```bash
# Ensure Xcode Command Line Tools are installed
xcode-select --install

# Update pip and try again
pip install --upgrade pip setuptools wheel
pip install mlx-whisper
```

#### Audio Processing Issues

```bash
# Install system audio libraries
# macOS:
brew install ffmpeg libsndfile

# Ubuntu/Debian:
sudo apt-get install libsndfile1-dev ffmpeg

# Windows: Install Visual Studio Build Tools
```

#### Permission Errors

```bash
# Use virtual environment (recommended)
python -m venv podknow-env
source podknow-env/bin/activate

# Or install with --user flag
pip install --user -e .
```

### Dependency Verification

Use the provided Makefile to check your installation:

```bash
# Check platform and dependencies
make check-platform
make verify-deps

# Run full test suite
make test
```

### Getting Help

If you encounter issues:

1. Check the [GitHub Issues](https://github.com/podknow/podknow/issues)
2. Run the verification commands above
3. Create a new issue with your system information and error messages

## Configuration

After installation, you may want to set up configuration:

```bash
# Create default configuration
mkdir -p ~/.podknow
cp config/default_config.md ~/.podknow/config.md

# Edit configuration
nano ~/.podknow/config.md
```

See the [Configuration Guide](CONFIG.md) for detailed configuration options.

## Uninstallation

To remove PodKnow:

```bash
# If installed in virtual environment
rm -rf podknow-env

# If installed globally
pip uninstall podknow

# Remove configuration (optional)
rm -rf ~/.podknow
```