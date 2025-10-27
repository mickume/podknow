# Scripts Directory

Utility scripts for PodKnow development and maintenance.

## 📋 Available Scripts

### `create_github_issues.py`

Automatically creates GitHub issues from the `WORK_BREAKDOWN.md` file.

#### Prerequisites

1. **Install GitHub CLI:**
   ```bash
   # macOS
   brew install gh

   # Linux
   sudo apt install gh  # Debian/Ubuntu
   sudo dnf install gh  # Fedora

   # Windows
   winget install GitHub.cli
   ```

2. **Authenticate with GitHub:**
   ```bash
   gh auth login
   ```

3. **Navigate to repository root:**
   ```bash
   cd /path/to/podknow
   ```

#### Usage

**Dry run (preview what would be created):**
```bash
python scripts/create_github_issues.py --dry-run
```

**Create all issues:**
```bash
python scripts/create_github_issues.py
```

**Create only critical priority issues:**
```bash
python scripts/create_github_issues.py --priority critical
```

**Create only high priority issues:**
```bash
python scripts/create_github_issues.py --priority high
```

**Skip issues that already exist:**
```bash
python scripts/create_github_issues.py --skip-existing
```

**Combine options:**
```bash
# Dry run for critical issues only
python scripts/create_github_issues.py --dry-run --priority critical

# Create high priority issues, skip existing
python scripts/create_github_issues.py --priority high --skip-existing
```

#### Examples

**Scenario 1: Initial Setup**
Create all critical and high priority issues:
```bash
# Preview critical issues
python scripts/create_github_issues.py --dry-run --priority critical

# Create them
python scripts/create_github_issues.py --priority critical

# Preview high priority
python scripts/create_github_issues.py --dry-run --priority high

# Create them
python scripts/create_github_issues.py --priority high
```

**Scenario 2: Batch Creation**
Create all issues at once:
```bash
# Preview first
python scripts/create_github_issues.py --dry-run

# Create all
python scripts/create_github_issues.py
```

**Scenario 3: Incremental Creation**
Add medium priority issues later:
```bash
python scripts/create_github_issues.py --priority medium --skip-existing
```

#### Output Example

```
📖 Parsing issues from WORK_BREAKDOWN.md...
📊 Found 24 issues
🔍 Filtered to 3 issues with priority: critical

🚀 CREATING ISSUES...
============================================================

✅ Created: https://github.com/user/podknow/issues/1
✅ Created: https://github.com/user/podknow/issues/2
✅ Created: https://github.com/user/podknow/issues/3

============================================================
📊 Summary:
  ✅ Created: 3
  ⏭️  Skipped: 0
  ❌ Failed: 0
============================================================
```

#### Troubleshooting

**Error: "GitHub CLI not authenticated"**
```bash
gh auth login
# Follow the prompts to authenticate
```

**Error: "File not found: WORK_BREAKDOWN.md"**
```bash
# Make sure you're in the repository root
cd /path/to/podknow
pwd  # Should show the podknow directory
```

**Error: "Failed to create issue"**
- Check you have write permissions to the repository
- Verify the repository is connected to GitHub
- Check your internet connection

---

### `install.py`

Installation script for PodKnow (see main README for details).

---

## 🔧 Adding New Scripts

When adding new scripts to this directory:

1. **Make them executable:**
   ```bash
   chmod +x scripts/your_script.py
   ```

2. **Add shebang line:**
   ```python
   #!/usr/bin/env python3
   ```

3. **Add docstring:**
   ```python
   """
   Brief description of what the script does.

   Usage:
       python scripts/your_script.py [options]
   """
   ```

4. **Update this README:**
   - Add script name to "Available Scripts"
   - Document usage and examples
   - Add troubleshooting section if needed

5. **Add to .gitignore if needed:**
   ```bash
   # Add to .gitignore if script generates temp files
   scripts/your_script_output/
   ```

---

## 📝 Script Development Guidelines

### Code Style
- Follow PEP 8
- Use type hints
- Add docstrings
- Handle errors gracefully

### Error Handling
```python
try:
    # Script logic
except FileNotFoundError as e:
    print(f"❌ File not found: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)
```

### User Feedback
- Use emojis for visual feedback: ✅ ❌ ⚠️ 📊 🔍
- Show progress for long operations
- Provide clear error messages
- Add `--verbose` flag for debugging

### Command Line Arguments
```python
import argparse

parser = argparse.ArgumentParser(description='Script description')
parser.add_argument('--dry-run', action='store_true', help='Preview only')
parser.add_argument('--verbose', action='store_true', help='Verbose output')
args = parser.parse_args()
```

---

## 🧪 Testing Scripts

Before committing a new script:

1. **Test with dry-run:**
   ```bash
   python scripts/your_script.py --dry-run
   ```

2. **Test error cases:**
   ```bash
   # Test with missing files
   python scripts/your_script.py --file nonexistent.txt

   # Test with invalid arguments
   python scripts/your_script.py --invalid-flag
   ```

3. **Test in clean environment:**
   ```bash
   # Create new venv and test
   python -m venv test_env
   source test_env/bin/activate
   python scripts/your_script.py
   ```

4. **Add to CI/CD if applicable:**
   ```yaml
   # .github/workflows/scripts.yml
   - name: Test scripts
     run: |
       python scripts/your_script.py --dry-run
   ```

---

## 📚 Related Documentation

- [Work Breakdown](../WORK_BREAKDOWN.md) - Detailed issue descriptions
- [Issues Checklist](../ISSUES_CHECKLIST.md) - Quick reference checklist
- [Contributing Guide](../CONTRIBUTING.md) - Development workflow
- [Main README](../README.md) - Project overview

---

## 🆘 Getting Help

If you encounter issues with scripts:

1. Check this README for troubleshooting
2. Check script's `--help` output
3. Run with `--verbose` flag for detailed logging
4. Create an issue on GitHub with:
   - Script name and version
   - Command you ran
   - Error message
   - Your environment (OS, Python version)

---

*Last Updated: 2025-10-27*
