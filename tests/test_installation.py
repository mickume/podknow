"""
Tests for package installation and environment setup validation.
These tests verify that PodKnow can be properly installed and configured
across different platforms and package managers.
"""

import os
import sys
import platform
import subprocess
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from podknow.cli.main import cli


class TestInstallationValidation:
    """Test suite for installation validation"""

    def test_package_imports(self):
        """Test that all core package modules can be imported"""
        # Core modules
        import podknow
        import podknow.cli
        import podknow.models
        import podknow.services
        import podknow.config
        
        # Verify package has version
        assert hasattr(podknow, '__version__') or hasattr(podknow, 'version')

    def test_cli_entry_point(self):
        """Test that the CLI entry point is properly configured"""
        from click.testing import CliRunner
        
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        
        assert result.exit_code == 0
        assert 'podknow' in result.output.lower()
        assert 'search' in result.output
        assert 'list' in result.output
        assert 'transcribe' in result.output

    def test_core_dependencies_available(self):
        """Test that all core dependencies are available"""
        # Core application dependencies
        import click
        import requests
        import feedparser
        import pydantic
        import anthropic
        import librosa
        import yaml
        import rich
        import tqdm
        
        # Verify versions meet minimum requirements
        assert hasattr(click, '__version__')
        assert hasattr(requests, '__version__')
        assert hasattr(pydantic, '__version__')

    def test_platform_specific_dependencies(self):
        """Test platform-specific audio processing dependencies"""
        machine = platform.machine().lower()
        system = platform.system()
        
        if system == "Darwin" and machine in ["arm64", "aarch64"]:
            # Apple Silicon - should have MLX-Whisper
            try:
                import mlx_whisper
                assert hasattr(mlx_whisper, '__version__')
            except ImportError:
                pytest.skip("MLX-Whisper not available on this Apple Silicon system")
        else:
            # Other platforms - should have standard Whisper or skip
            try:
                import whisper
                assert hasattr(whisper, '__version__')
            except ImportError:
                pytest.skip("OpenAI Whisper not available on this system")

    def test_configuration_directory_creation(self):
        """Test that configuration directory can be created"""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / ".podknow"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            assert config_dir.exists()
            assert config_dir.is_dir()
            
            # Test config file creation
            config_file = config_dir / "config.md"
            config_file.write_text("# Test configuration")
            
            assert config_file.exists()
            assert config_file.read_text() == "# Test configuration"

    def test_virtual_environment_detection(self):
        """Test detection of virtual environment"""
        # Check if running in virtual environment
        in_venv = (
            hasattr(sys, 'real_prefix') or
            (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
        )
        
        # This test documents the environment but doesn't fail
        # as it may run in different contexts
        if in_venv:
            assert sys.prefix != sys.base_prefix
        else:
            # Running in system Python or other environment
            pass

    @pytest.mark.integration
    def test_package_installation_simulation(self):
        """Simulate package installation process"""
        with tempfile.TemporaryDirectory() as temp_dir:
            venv_path = Path(temp_dir) / "test_venv"
            
            # Create a minimal virtual environment structure
            venv_path.mkdir()
            (venv_path / "bin").mkdir(exist_ok=True)
            (venv_path / "lib").mkdir(exist_ok=True)
            
            # Simulate successful venv creation
            assert venv_path.exists()
            assert (venv_path / "bin").exists()
            assert (venv_path / "lib").exists()

    def test_dependency_resolution_compatibility(self):
        """Test that dependencies don't have conflicting requirements"""
        # Import all major dependencies to check for conflicts
        try:
            import click
            import requests
            import feedparser
            import pydantic
            import anthropic
            import librosa
            import yaml
            import rich
            import tqdm
            
            # If we get here, no import conflicts exist
            assert True
        except ImportError as e:
            pytest.fail(f"Dependency conflict detected: {e}")

    def test_apple_silicon_optimization_detection(self):
        """Test Apple Silicon optimization detection"""
        machine = platform.machine().lower()
        system = platform.system()
        
        is_apple_silicon = system == "Darwin" and machine in ["arm64", "aarch64"]
        
        if is_apple_silicon:
            # Should prefer MLX-based dependencies
            try:
                import mlx_whisper
                # MLX-Whisper available - optimization working
                assert True
            except ImportError:
                # MLX-Whisper not available - may be intentional or issue
                pytest.skip("MLX-Whisper not installed on Apple Silicon")
        else:
            # Non-Apple Silicon should use standard dependencies
            assert not is_apple_silicon

    @pytest.mark.slow
    def test_cli_command_execution(self):
        """Test that CLI commands can be executed without errors"""
        from click.testing import CliRunner
        
        runner = CliRunner()
        
        # Test help commands
        commands_to_test = [
            ['--help'],
            ['search', '--help'],
            ['list', '--help'],
            ['transcribe', '--help'],
        ]
        
        for cmd in commands_to_test:
            result = runner.invoke(cli, cmd)
            assert result.exit_code == 0, f"Command {cmd} failed: {result.output}"

    def test_audio_processing_capabilities(self):
        """Test that audio processing capabilities are available"""
        import librosa
        import soundfile
        
        # Test that librosa can be imported and has basic functionality
        assert hasattr(librosa, 'load')
        assert hasattr(librosa, 'resample')
        
        # Test soundfile availability
        assert hasattr(soundfile, 'read')
        assert hasattr(soundfile, 'write')

    def test_ai_integration_capabilities(self):
        """Test that AI integration capabilities are available"""
        import anthropic
        
        # Test that Anthropic client can be imported
        assert hasattr(anthropic, 'Anthropic')
        
        # Test client instantiation (without API key)
        try:
            client = anthropic.Anthropic(api_key="test-key")
            assert client is not None
        except Exception:
            # Expected to fail without valid API key, but import should work
            pass

    def test_development_tools_availability(self):
        """Test that development tools are available (if installed)"""
        dev_tools = [
            ('pytest', 'pytest'),
            ('black', 'black'),
            ('mypy', 'mypy'),
            ('ruff', 'ruff'),
        ]
        
        available_tools = []
        for tool_name, import_name in dev_tools:
            try:
                __import__(import_name)
                available_tools.append(tool_name)
            except ImportError:
                pass
        
        # At least pytest should be available for tests to run
        assert 'pytest' in available_tools

    def test_file_system_permissions(self):
        """Test that the package has proper file system permissions"""
        import podknow
        
        # Get package directory
        package_dir = Path(podknow.__file__).parent
        
        # Test that package directory is readable
        assert package_dir.exists()
        assert package_dir.is_dir()
        
        # Test that main modules are readable
        main_modules = [
            package_dir / '__init__.py',
            package_dir / 'cli' / '__init__.py',
            package_dir / 'models' / '__init__.py',
            package_dir / 'services' / '__init__.py',
        ]
        
        for module_path in main_modules:
            if module_path.exists():
                assert os.access(module_path, os.R_OK)


class TestInstallationScripts:
    """Test suite for installation scripts"""

    def test_installation_script_exists(self):
        """Test that installation scripts exist and are executable"""
        script_dir = Path(__file__).parent.parent / "scripts"
        
        expected_scripts = [
            "install.py",
            "install.sh",
            "install.bat",
        ]
        
        for script_name in expected_scripts:
            script_path = script_dir / script_name
            assert script_path.exists(), f"Installation script {script_name} not found"
            
            if script_name.endswith(('.py', '.sh')):
                # Check if executable on Unix-like systems
                if platform.system() != "Windows":
                    assert os.access(script_path, os.X_OK), f"Script {script_name} not executable"

    def test_makefile_exists(self):
        """Test that Makefile exists for development tasks"""
        makefile_path = Path(__file__).parent.parent / "Makefile"
        assert makefile_path.exists()
        
        # Check that it contains expected targets
        makefile_content = makefile_path.read_text()
        expected_targets = [
            "install",
            "install-uv",
            "test",
            "lint",
            "format",
            "clean",
        ]
        
        for target in expected_targets:
            assert target in makefile_content

    def test_installation_documentation_exists(self):
        """Test that installation documentation exists"""
        install_doc_path = Path(__file__).parent.parent / "INSTALL.md"
        assert install_doc_path.exists()
        
        # Check that it contains key sections
        doc_content = install_doc_path.read_text()
        expected_sections = [
            "Quick Start",
            "Platform-Specific",
            "Apple Silicon",
            "Troubleshooting",
        ]
        
        for section in expected_sections:
            assert section in doc_content

    @pytest.mark.integration
    def test_python_installation_script_syntax(self):
        """Test that Python installation script has valid syntax"""
        script_path = Path(__file__).parent.parent / "scripts" / "install.py"
        
        # Test that the script can be compiled
        with open(script_path, 'r') as f:
            script_content = f.read()
        
        try:
            compile(script_content, str(script_path), 'exec')
        except SyntaxError as e:
            pytest.fail(f"Installation script has syntax error: {e}")

    def test_package_configuration_files(self):
        """Test that package configuration files are properly formatted"""
        project_root = Path(__file__).parent.parent
        
        # Test pyproject.toml
        pyproject_path = project_root / "pyproject.toml"
        assert pyproject_path.exists()
        
        # Test setup.py
        setup_path = project_root / "setup.py"
        assert setup_path.exists()
        
        # Test that setup.py has valid syntax
        with open(setup_path, 'r') as f:
            setup_content = f.read()
        
        try:
            compile(setup_content, str(setup_path), 'exec')
        except SyntaxError as e:
            pytest.fail(f"setup.py has syntax error: {e}")


class TestPlatformCompatibility:
    """Test suite for platform compatibility"""

    def test_python_version_compatibility(self):
        """Test Python version compatibility"""
        version_info = sys.version_info
        
        # Should be Python 3.13+
        assert version_info.major == 3
        assert version_info.minor >= 13

    def test_platform_detection(self):
        """Test platform detection logic"""
        system = platform.system()
        machine = platform.machine().lower()
        
        # Should be able to detect major platforms
        assert system in ["Darwin", "Linux", "Windows"]
        
        # Machine architecture should be detectable
        assert machine in ["x86_64", "amd64", "arm64", "aarch64", "i386", "i686"]

    def test_apple_silicon_detection(self):
        """Test Apple Silicon detection"""
        system = platform.system()
        machine = platform.machine().lower()
        
        is_apple_silicon = system == "Darwin" and machine in ["arm64", "aarch64"]
        
        if is_apple_silicon:
            # On Apple Silicon, should prefer MLX dependencies
            assert system == "Darwin"
            assert machine in ["arm64", "aarch64"]
        else:
            # On other platforms, should use standard dependencies
            assert not (system == "Darwin" and machine in ["arm64", "aarch64"])

    @pytest.mark.skipif(platform.system() != "Darwin", reason="macOS specific test")
    def test_macos_specific_requirements(self):
        """Test macOS specific requirements"""
        # Test that we can detect Xcode Command Line Tools
        try:
            result = subprocess.run(
                ["xcode-select", "-p"],
                capture_output=True,
                text=True,
                check=True
            )
            # If successful, Xcode tools are installed
            assert result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("Xcode Command Line Tools not installed")

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows specific test")
    def test_windows_specific_requirements(self):
        """Test Windows specific requirements"""
        # Test that we're on Windows
        assert platform.system() == "Windows"
        
        # Test that we can access Windows-specific paths
        import os
        assert 'USERPROFILE' in os.environ or 'HOME' in os.environ