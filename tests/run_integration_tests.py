#!/usr/bin/env python3
"""
Integration test runner for PodKnow.

This script runs comprehensive integration tests including:
- Workflow orchestration tests
- CLI integration tests  
- End-to-end functionality tests
- Error recovery and graceful degradation tests

Usage:
    python tests/run_integration_tests.py [options]

Options:
    --fast          Skip slow tests
    --real-apis     Include tests with real API calls (requires API keys)
    --verbose       Verbose test output
    --coverage      Generate coverage report
    --parallel      Run tests in parallel
"""

import os
import sys
import argparse
import subprocess
import tempfile
from pathlib import Path


def setup_test_environment():
    """Set up test environment variables and configuration."""
    # Set test mode
    os.environ['PODKNOW_TEST_MODE'] = '1'
    
    # Create temporary test directories
    test_temp_dir = tempfile.mkdtemp(prefix='podknow_test_')
    os.environ['PODKNOW_TEST_TEMP_DIR'] = test_temp_dir
    
    # Set test configuration directory
    test_config_dir = os.path.join(test_temp_dir, '.podknow')
    os.makedirs(test_config_dir, exist_ok=True)
    os.environ['PODKNOW_CONFIG_DIR'] = test_config_dir
    
    # Set test output directory
    test_output_dir = os.path.join(test_temp_dir, 'output')
    os.makedirs(test_output_dir, exist_ok=True)
    os.environ['PODKNOW_OUTPUT_DIR'] = test_output_dir
    
    return test_temp_dir


def cleanup_test_environment(test_temp_dir):
    """Clean up test environment."""
    import shutil
    
    # Remove temporary directories
    if os.path.exists(test_temp_dir):
        shutil.rmtree(test_temp_dir, ignore_errors=True)
    
    # Clean up environment variables
    test_env_vars = [
        'PODKNOW_TEST_MODE',
        'PODKNOW_TEST_TEMP_DIR', 
        'PODKNOW_CONFIG_DIR',
        'PODKNOW_OUTPUT_DIR'
    ]
    
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]


def check_dependencies():
    """Check if required test dependencies are available."""
    required_packages = [
        'pytest',
        'pytest-mock',
        'pytest-cov',
        'pytest-xdist'  # For parallel testing
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"Missing required test packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    
    return True


def check_optional_dependencies():
    """Check optional dependencies and warn if missing."""
    optional_packages = {
        'mlx_whisper': 'MLX-Whisper (Apple Silicon transcription)',
        'anthropic': 'Anthropic Claude API client',
        'requests': 'HTTP requests library',
        'feedparser': 'RSS feed parsing'
    }
    
    available = {}
    
    for package, description in optional_packages.items():
        try:
            __import__(package)
            available[package] = True
        except ImportError:
            available[package] = False
            print(f"Warning: {description} not available - some tests may be skipped")
    
    return available


def run_pytest(test_files, args):
    """Run pytest with specified test files and arguments."""
    pytest_args = ['python', '-m', 'pytest']
    
    # Add test files
    pytest_args.extend(test_files)
    
    # Add common pytest arguments
    pytest_args.extend([
        '-v',  # Verbose output
        '--tb=short',  # Short traceback format
        '--strict-markers',  # Strict marker checking
    ])
    
    # Add conditional arguments
    if args.fast:
        pytest_args.extend(['-m', 'not slow'])
    
    if args.real_apis:
        os.environ['PODKNOW_INTEGRATION_TESTS'] = '1'
        pytest_args.extend(['-m', 'integration'])
    else:
        pytest_args.extend(['-m', 'integration and not slow'])
    
    if args.verbose:
        pytest_args.append('-s')  # Don't capture output
    
    if args.coverage:
        pytest_args.extend([
            '--cov=podknow',
            '--cov-report=html',
            '--cov-report=term-missing',
            '--cov-fail-under=80'
        ])
    
    if args.parallel:
        pytest_args.extend(['-n', 'auto'])  # Auto-detect number of CPUs
    
    # Add custom markers
    pytest_args.extend([
        '--strict-config',
        '-p', 'no:warnings'  # Suppress warnings for cleaner output
    ])
    
    print(f"Running: {' '.join(pytest_args)}")
    return subprocess.run(pytest_args)


def create_test_report(result, args):
    """Create test execution report."""
    report_lines = [
        "=" * 60,
        "PodKnow Integration Test Report",
        "=" * 60,
        f"Exit Code: {result.returncode}",
        f"Test Mode: {'Fast' if args.fast else 'Full'}",
        f"Real APIs: {'Enabled' if args.real_apis else 'Disabled'}",
        f"Coverage: {'Enabled' if args.coverage else 'Disabled'}",
        f"Parallel: {'Enabled' if args.parallel else 'Disabled'}",
        ""
    ]
    
    if result.returncode == 0:
        report_lines.append("✅ All tests passed!")
    else:
        report_lines.append("❌ Some tests failed!")
        report_lines.append("")
        report_lines.append("Troubleshooting:")
        report_lines.append("- Check test output above for specific failures")
        report_lines.append("- Ensure all dependencies are installed")
        report_lines.append("- Verify API keys are set if using --real-apis")
        report_lines.append("- Try running with --verbose for more details")
    
    report_lines.extend([
        "",
        "Test Files Executed:",
        "- test_workflow_integration.py",
        "- test_cli_integration.py",
        "",
        "For more details, check the test output above."
    ])
    
    print("\n".join(report_lines))


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Run PodKnow integration tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python tests/run_integration_tests.py
    python tests/run_integration_tests.py --fast --verbose
    python tests/run_integration_tests.py --real-apis --coverage
    python tests/run_integration_tests.py --parallel --fast
        """
    )
    
    parser.add_argument(
        '--fast',
        action='store_true',
        help='Skip slow tests for faster execution'
    )
    
    parser.add_argument(
        '--real-apis',
        action='store_true',
        help='Include tests with real API calls (requires API keys)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose test output'
    )
    
    parser.add_argument(
        '--coverage',
        action='store_true',
        help='Generate coverage report'
    )
    
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Run tests in parallel'
    )
    
    parser.add_argument(
        '--test-file',
        action='append',
        help='Specific test file to run (can be used multiple times)'
    )
    
    args = parser.parse_args()
    
    # Check dependencies
    print("Checking test dependencies...")
    if not check_dependencies():
        sys.exit(1)
    
    print("Checking optional dependencies...")
    available_deps = check_optional_dependencies()
    
    # Set up test environment
    print("Setting up test environment...")
    test_temp_dir = setup_test_environment()
    
    try:
        # Determine test files to run
        if args.test_file:
            test_files = args.test_file
        else:
            # Default integration test files
            test_files = [
                'tests/test_workflow_integration.py',
                'tests/test_cli_integration.py'
            ]
        
        # Verify test files exist
        project_root = Path(__file__).parent.parent
        for test_file in test_files:
            test_path = project_root / test_file
            if not test_path.exists():
                print(f"Error: Test file not found: {test_file}")
                sys.exit(1)
        
        # Show test configuration
        print("\nTest Configuration:")
        print(f"  Fast mode: {args.fast}")
        print(f"  Real APIs: {args.real_apis}")
        print(f"  Verbose: {args.verbose}")
        print(f"  Coverage: {args.coverage}")
        print(f"  Parallel: {args.parallel}")
        print(f"  Test files: {len(test_files)}")
        
        if args.real_apis:
            print("\nReal API Testing Enabled:")
            print("  Ensure the following environment variables are set:")
            print("  - CLAUDE_API_KEY (required)")
            print("  - SPOTIFY_CLIENT_ID (optional)")
            print("  - SPOTIFY_CLIENT_SECRET (optional)")
            
            # Check for API keys
            if not os.getenv('CLAUDE_API_KEY'):
                print("  Warning: CLAUDE_API_KEY not set - some tests may fail")
        
        print("\nStarting integration tests...")
        print("=" * 60)
        
        # Run tests
        result = run_pytest(test_files, args)
        
        # Create report
        create_test_report(result, args)
        
        # Exit with pytest's exit code
        sys.exit(result.returncode)
        
    finally:
        # Clean up test environment
        print("\nCleaning up test environment...")
        cleanup_test_environment(test_temp_dir)


if __name__ == "__main__":
    main()