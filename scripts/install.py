#!/usr/bin/env python3
"""
Cross-platform PodKnow installation script
Supports both pip and uv package managers with platform detection
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path
from typing import Optional, Tuple

# Configuration
PYTHON_VERSION = "3.13"
VENV_NAME = "podknow-env"
PROJECT_NAME = "podknow"

class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color
    
    @classmethod
    def disable_on_windows(cls):
        """Disable colors on Windows if not supported"""
        if platform.system() == "Windows":
            cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = cls.NC = ""

def print_status(message: str):
    """Print info message"""
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {message}")

def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {message}")

def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")

def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

def command_exists(command: str) -> bool:
    """Check if a command exists in PATH"""
    return shutil.which(command) is not None

def detect_platform() -> str:
    """Detect the current platform"""
    machine = platform.machine().lower()
    system = platform.system()
    
    if system == "Darwin" and machine in ["arm64", "aarch64"]:
        return "apple-silicon"
    elif system == "Darwin":
        return "macos-intel"
    elif system == "Linux":
        return "linux"
    elif system == "Windows":
        return "windows"
    else:
        return "unknown"

def check_python_version() -> str:
    """Check if Python 3.13 is available and return the command"""
    # Try different Python commands
    python_commands = ["python3.13", "python3", "python"]
    
    for cmd in python_commands:
        if command_exists(cmd):
            try:
                result = subprocess.run(
                    [cmd, "--version"], 
                    capture_output=True, 
                    text=True, 
                    check=True
                )
                version = result.stdout.strip().split()[1]
                major, minor = version.split('.')[:2]
                
                if f"{major}.{minor}" == "3.13":
                    print_success(f"Found Python 3.13: {cmd}")
                    return cmd
            except (subprocess.CalledProcessError, IndexError, ValueError):
                continue
    
    print_error("Python 3.13 not found")
    print_status("Please install Python 3.13 from https://www.python.org/downloads/")
    sys.exit(1)

def check_apple_silicon() -> bool:
    """Check if running on Apple Silicon and verify prerequisites"""
    platform_type = detect_platform()
    
    if platform_type == "apple-silicon":
        print_status("Detected Apple Silicon Mac - enabling MLX optimizations")
        
        # Check if Xcode Command Line Tools are installed (macOS only)
        try:
            subprocess.run(
                ["xcode-select", "-p"], 
                capture_output=True, 
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            print_warning("Xcode Command Line Tools not found")
            print_status("Please install with: xcode-select --install")
            return False
        
        return True
    else:
        print_status(f"Platform detected: {platform_type} - using standard dependencies")
        return False

def run_command(command: list, description: str) -> bool:
    """Run a command and handle errors"""
    print_status(f"{description}...")
    try:
        subprocess.run(command, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"{description} failed with exit code {e.returncode}")
        return False

def install_with_uv(python_cmd: str, is_apple_silicon: bool) -> bool:
    """Install PodKnow using uv package manager"""
    print_status("Installing PodKnow with uv package manager...")
    
    # Install uv if not available
    if not command_exists("uv"):
        print_status("Installing uv package manager...")
        try:
            if platform.system() == "Windows":
                subprocess.run(
                    ["powershell", "-c", "irm https://astral.sh/uv/install.ps1 | iex"],
                    check=True
                )
            else:
                subprocess.run(
                    ["curl", "-LsSf", "https://astral.sh/uv/install.sh"],
                    stdout=subprocess.PIPE,
                    check=True
                )
        except subprocess.CalledProcessError:
            print_error("Failed to install uv")
            return False
    
    # Create virtual environment
    if not run_command(
        ["uv", "venv", VENV_NAME, "--python", python_cmd],
        "Creating virtual environment with uv"
    ):
        return False
    
    # Determine activation script
    if platform.system() == "Windows":
        activate_script = Path(VENV_NAME) / "Scripts" / "activate.bat"
        pip_cmd = ["uv", "pip", "install"]
    else:
        activate_script = Path(VENV_NAME) / "bin" / "activate"
        pip_cmd = ["uv", "pip", "install"]
    
    # Install package
    extras = "apple-silicon,dev" if is_apple_silicon else "standard,dev"
    if not run_command(
        pip_cmd + ["-e", f".[{extras}]"],
        "Installing PodKnow and dependencies"
    ):
        return False
    
    print_success("Installation completed with uv!")
    return True

def install_with_pip(python_cmd: str, is_apple_silicon: bool) -> bool:
    """Install PodKnow using pip package manager"""
    print_status("Installing PodKnow with pip package manager...")
    
    # Create virtual environment
    if not run_command(
        [python_cmd, "-m", "venv", VENV_NAME],
        "Creating virtual environment"
    ):
        return False
    
    # Determine pip command based on platform
    if platform.system() == "Windows":
        pip_cmd = [str(Path(VENV_NAME) / "Scripts" / "python.exe"), "-m", "pip"]
    else:
        pip_cmd = [str(Path(VENV_NAME) / "bin" / "python"), "-m", "pip"]
    
    # Upgrade pip
    if not run_command(
        pip_cmd + ["install", "--upgrade", "pip", "setuptools", "wheel"],
        "Upgrading pip"
    ):
        return False
    
    # Install package
    extras = "apple-silicon,dev" if is_apple_silicon else "standard,dev"
    if not run_command(
        pip_cmd + ["install", "-e", f".[{extras}]"],
        "Installing PodKnow and dependencies"
    ):
        return False
    
    print_success("Installation completed with pip!")
    return True

def verify_installation() -> bool:
    """Verify that PodKnow was installed correctly"""
    print_status("Verifying installation...")
    
    # Determine python command in venv
    if platform.system() == "Windows":
        python_venv = str(Path(VENV_NAME) / "Scripts" / "python.exe")
        podknow_cmd = str(Path(VENV_NAME) / "Scripts" / "podknow.exe")
    else:
        python_venv = str(Path(VENV_NAME) / "bin" / "python")
        podknow_cmd = str(Path(VENV_NAME) / "bin" / "podknow")
    
    # Check if podknow command exists
    if not Path(podknow_cmd).exists():
        print_error("PodKnow CLI not found")
        return False
    
    # Test basic functionality
    try:
        result = subprocess.run(
            [python_venv, "-c", "import podknow; print('PodKnow imported successfully')"],
            capture_output=True,
            text=True,
            check=True
        )
        print_success("PodKnow module imports correctly")
    except subprocess.CalledProcessError:
        print_error("PodKnow module import failed")
        return False
    
    # Test CLI
    try:
        subprocess.run([podknow_cmd, "--help"], capture_output=True, check=True)
        print_success("PodKnow CLI is working correctly")
    except subprocess.CalledProcessError:
        print_error("PodKnow CLI test failed")
        return False
    
    # Check platform-specific dependencies
    platform_type = detect_platform()
    if platform_type == "apple-silicon":
        try:
            subprocess.run(
                [python_venv, "-c", "import mlx_whisper; print('MLX-Whisper available')"],
                capture_output=True,
                check=True
            )
            print_success("MLX-Whisper is properly installed")
        except subprocess.CalledProcessError:
            print_warning("MLX-Whisper verification failed")
            return False
    
    return True

def main():
    """Main installation function"""
    # Disable colors on Windows if needed
    if platform.system() == "Windows":
        Colors.disable_on_windows()
    
    print_status("Starting PodKnow installation...")
    print_status(f"Platform: {detect_platform()}")
    
    # Check prerequisites
    python_cmd = check_python_version()
    is_apple_silicon = check_apple_silicon()
    
    # Choose installation method
    use_uv = "--uv" in sys.argv or command_exists("uv")
    
    # Perform installation
    if use_uv:
        success = install_with_uv(python_cmd, is_apple_silicon)
    else:
        success = install_with_pip(python_cmd, is_apple_silicon)
    
    if not success:
        print_error("Installation failed")
        sys.exit(1)
    
    # Verify installation
    if verify_installation():
        print_success("PodKnow installation completed successfully!")
        print()
        print_status("To activate the environment, run:")
        if platform.system() == "Windows":
            print(f"  {VENV_NAME}\\Scripts\\activate.bat")
        else:
            print(f"  source {VENV_NAME}/bin/activate")
        print()
        print_status("To get started, run:")
        print("  podknow --help")
    else:
        print_error("Installation verification failed")
        sys.exit(1)

if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print("PodKnow Installation Script")
        print()
        print(f"Usage: {sys.argv[0]} [OPTIONS]")
        print()
        print("Options:")
        print("  --uv      Use uv package manager (faster)")
        print("  --help    Show this help message")
        print()
        print("This script will:")
        print("  1. Check for Python 3.13")
        print("  2. Create a virtual environment")
        print("  3. Install PodKnow with platform-optimized dependencies")
        print("  4. Verify the installation")
        print()
        sys.exit(0)
    
    main()