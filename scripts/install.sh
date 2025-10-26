#!/bin/bash
# PodKnow Installation Script
# Supports both pip and uv package managers with Apple Silicon optimization

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_VERSION="3.13"
VENV_NAME="podknow-env"
PROJECT_NAME="podknow"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to detect platform
detect_platform() {
    local machine=$(uname -m)
    local os=$(uname -s)
    
    if [[ "$os" == "Darwin" && "$machine" == "arm64" ]]; then
        echo "apple-silicon"
    elif [[ "$os" == "Darwin" ]]; then
        echo "macos-intel"
    elif [[ "$os" == "Linux" ]]; then
        echo "linux"
    else
        echo "unknown"
    fi
}

# Function to check Python version
check_python_version() {
    if command_exists python3.13; then
        PYTHON_CMD="python3.13"
    elif command_exists python3; then
        local version=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [[ "$version" == "3.13" ]]; then
            PYTHON_CMD="python3"
        else
            print_error "Python 3.13 is required, but found Python $version"
            print_status "Please install Python 3.13 from https://www.python.org/downloads/"
            exit 1
        fi
    else
        print_error "Python 3.13 not found"
        print_status "Please install Python 3.13 from https://www.python.org/downloads/"
        exit 1
    fi
    
    print_success "Found Python 3.13: $PYTHON_CMD"
}

# Function to check Apple Silicon optimizations
check_apple_silicon() {
    local platform=$(detect_platform)
    
    if [[ "$platform" == "apple-silicon" ]]; then
        print_status "Detected Apple Silicon Mac - enabling MLX optimizations"
        
        # Check if Xcode Command Line Tools are installed
        if ! xcode-select -p &> /dev/null; then
            print_warning "Xcode Command Line Tools not found"
            print_status "Installing Xcode Command Line Tools..."
            xcode-select --install
            print_status "Please run this script again after Xcode Command Line Tools installation completes"
            exit 0
        fi
        
        return 0
    else
        print_status "Non-Apple Silicon platform detected - using standard dependencies"
        return 1
    fi
}

# Function to install with uv
install_with_uv() {
    print_status "Installing PodKnow with uv package manager..."
    
    # Check if uv is installed
    if ! command_exists uv; then
        print_status "Installing uv package manager..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        source $HOME/.cargo/env
    fi
    
    # Create virtual environment with uv
    print_status "Creating virtual environment with uv..."
    uv venv "$VENV_NAME" --python "$PYTHON_CMD"
    
    # Activate virtual environment
    source "$VENV_NAME/bin/activate"
    
    # Install package with uv
    print_status "Installing PodKnow and dependencies..."
    if check_apple_silicon; then
        uv pip install -e ".[apple-silicon,dev]"
    else
        uv pip install -e ".[standard,dev]"
    fi
    
    print_success "Installation completed with uv!"
}

# Function to install with pip
install_with_pip() {
    print_status "Installing PodKnow with pip package manager..."
    
    # Create virtual environment
    print_status "Creating virtual environment..."
    "$PYTHON_CMD" -m venv "$VENV_NAME"
    
    # Activate virtual environment
    source "$VENV_NAME/bin/activate"
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip setuptools wheel
    
    # Install package
    print_status "Installing PodKnow and dependencies..."
    if check_apple_silicon; then
        pip install -e ".[apple-silicon,dev]"
    else
        pip install -e ".[standard,dev]"
    fi
    
    print_success "Installation completed with pip!"
}

# Function to verify installation
verify_installation() {
    print_status "Verifying installation..."
    
    # Check if podknow command is available
    if command_exists podknow; then
        print_success "PodKnow CLI is available"
        podknow --version
    else
        print_error "PodKnow CLI not found in PATH"
        return 1
    fi
    
    # Test basic functionality
    print_status "Testing basic functionality..."
    if podknow --help > /dev/null 2>&1; then
        print_success "PodKnow CLI is working correctly"
    else
        print_error "PodKnow CLI test failed"
        return 1
    fi
    
    # Check platform-specific dependencies
    local platform=$(detect_platform)
    if [[ "$platform" == "apple-silicon" ]]; then
        print_status "Verifying MLX-Whisper installation..."
        python -c "import mlx_whisper; print('MLX-Whisper:', mlx_whisper.__version__)" 2>/dev/null || {
            print_warning "MLX-Whisper verification failed"
            return 1
        }
        print_success "MLX-Whisper is properly installed"
    fi
    
    return 0
}

# Main installation function
main() {
    print_status "Starting PodKnow installation..."
    print_status "Platform: $(detect_platform)"
    
    # Check prerequisites
    check_python_version
    
    # Choose installation method
    if [[ "$1" == "--uv" ]] || command_exists uv; then
        install_with_uv
    else
        install_with_pip
    fi
    
    # Verify installation
    if verify_installation; then
        print_success "PodKnow installation completed successfully!"
        echo
        print_status "To activate the environment, run:"
        echo "  source $VENV_NAME/bin/activate"
        echo
        print_status "To get started, run:"
        echo "  podknow --help"
    else
        print_error "Installation verification failed"
        exit 1
    fi
}

# Show usage if help requested
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    echo "PodKnow Installation Script"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --uv      Use uv package manager (faster)"
    echo "  --help    Show this help message"
    echo
    echo "This script will:"
    echo "  1. Check for Python 3.13"
    echo "  2. Create a virtual environment"
    echo "  3. Install PodKnow with platform-optimized dependencies"
    echo "  4. Verify the installation"
    echo
    exit 0
fi

# Run main installation
main "$@"