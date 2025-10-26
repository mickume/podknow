#!/usr/bin/env python3
"""
Setup script for PodKnow - Podcast Transcription and Analysis Tool

This setup.py provides backward compatibility for pip installations
that don't fully support pyproject.toml. The primary configuration
is in pyproject.toml.
"""

import platform
from setuptools import setup, find_packages

# Determine platform-specific dependencies
def get_platform_dependencies():
    """Get dependencies based on the current platform."""
    base_deps = [
        "click>=8.0.0",
        "requests>=2.28.0", 
        "feedparser>=6.0.0",
        "pydantic>=2.0.0",
        "librosa>=0.10.0",
        "soundfile>=0.12.0",
        "anthropic>=0.8.0",
        "python-dateutil>=2.8.0",
        "pyyaml>=6.0.0",
        "rich>=13.0.0",
        "tqdm>=4.64.0",
    ]
    
    # Add platform-specific audio processing dependencies
    if platform.machine() == 'arm64' and platform.system() == 'Darwin':
        # Apple Silicon Mac
        base_deps.extend([
            "mlx>=0.0.6",
            "mlx-whisper>=0.1.0",
        ])
    else:
        # Other platforms
        base_deps.extend([
            "openai-whisper>=20231117",
            "torch>=2.0.0",
        ])
    
    return base_deps

if __name__ == "__main__":
    setup(
        name="podknow",
        version="0.1.0",
        description="Command-line podcast transcription and analysis tool",
        long_description=open("README.md").read(),
        long_description_content_type="text/markdown",
        author="PodKnow Team",
        author_email="team@podknow.dev",
        url="https://github.com/podknow/podknow",
        packages=find_packages(),
        install_requires=get_platform_dependencies(),
        extras_require={
            "dev": [
                "pytest>=7.0.0",
                "pytest-mock>=3.10.0",
                "pytest-cov>=4.0.0",
                "black>=23.0.0",
                "mypy>=1.0.0",
                "ruff>=0.1.0",
                "pre-commit>=3.0.0",
            ],
            "test": [
                "pytest>=7.0.0",
                "pytest-mock>=3.10.0", 
                "pytest-cov>=4.0.0",
            ],
        },
        entry_points={
            "console_scripts": [
                "podknow=podknow.cli.main:cli",
            ],
        },
        python_requires=">=3.13",
        classifiers=[
            "Development Status :: 3 - Alpha",
            "Intended Audience :: Developers",
            "Intended Audience :: End Users/Desktop",
            "License :: OSI Approved :: MIT License",
            "Operating System :: MacOS",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.13",
            "Topic :: Multimedia :: Sound/Audio :: Speech",
            "Topic :: Text Processing :: Linguistic",
        ],
        keywords=["podcast", "transcription", "ai", "analysis", "mlx", "whisper", "claude"],
        license="MIT",
        include_package_data=True,
        zip_safe=False,
    )