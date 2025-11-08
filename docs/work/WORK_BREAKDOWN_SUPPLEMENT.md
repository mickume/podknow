# Work Breakdown Supplement - Test-Discovered Issues

**Date:** 2025-10-27
**Source:** pytest test failures analysis
**New Issues:** 8
**Test Results:** 227 passed, 35 failed, 3 skipped

This document supplements the main `WORK_BREAKDOWN.md` with issues discovered through running the test suite.

---

## 🟡 HIGH PRIORITY (Add to Sprint 1)

### ISSUE-025: Analysis Service Topic Validation Too Strict

**Severity:** 🟡 High
**Type:** Bug
**Labels:** `bug`, `high-priority`, `analysis`, `validation`

**Description:**
The `AnalysisResult` model requires at least one topic, but Claude API might return empty topic lists for very short transcriptions or when topic extraction fails. This causes the entire analysis to fail even when other components (summary, keywords) succeeded.

**Test Evidence:**
```
FAILED tests/test_analysis_service.py::TestAnalysisService::test_generate_markdown_output_with_sponsors
Error: Failed to analyze transcription: At least one topic is required
```

**Files Affected:**
- `podknow/models/analysis.py` (AnalysisResult dataclass)
- `podknow/services/analysis.py` (topic extraction logic)

**Current Behavior:**
```python
@dataclass
class AnalysisResult:
    summary: str
    topics: List[str]  # Requires at least one topic
    keywords: List[str]
    sponsor_segments: List[SponsorSegment]
```

**Proposed Solution:**
```python
@dataclass
class AnalysisResult:
    summary: str
    topics: List[str] = field(default_factory=list)  # Allow empty list
    keywords: List[str] = field(default_factory=list)
    sponsor_segments: List[SponsorSegment] = field(default_factory=list)

    def __post_init__(self):
        """Validate that at least summary exists."""
        if not self.summary or not self.summary.strip():
            raise ValueError("Summary is required")
```

**Acceptance Criteria:**
- [ ] Empty topic lists are accepted
- [ ] Analysis doesn't fail when no topics extracted
- [ ] Summary is still required (meaningful validation)
- [ ] Test passes: `test_generate_markdown_output_with_sponsors`
- [ ] Warning logged when topic list is empty

**Estimated Effort:** 30 minutes

---

## 🟠 MEDIUM PRIORITY

### ISSUE-026: CLI Integration Test Failures

**Severity:** 🟠 Medium
**Type:** Investigation + Bug
**Labels:** `bug`, `medium-priority`, `cli`, `integration`, `testing`

**Description:**
Multiple CLI integration tests fail due to incorrect mock setup or actual integration problems between CLI commands and WorkflowOrchestrator.

**Test Evidence:**
```
FAILED tests/test_cli_integration.py::TestCLISearchCommand::test_search_command_success
FAILED tests/test_cli_integration.py::TestCLISearchCommand::test_search_command_with_options
FAILED tests/test_cli_integration.py::TestCLISearchCommand::test_search_command_network_error
FAILED tests/test_cli_integration.py::TestCLISearchCommand::test_search_command_no_results
FAILED tests/test_cli_integration.py::TestCLIListCommand::test_list_command_success
```

**Files Affected:**
- `tests/test_cli_integration.py` (test mocks)
- `podknow/cli/main.py` (CLI commands)
- `podknow/services/workflow.py` (workflow integration)

**Investigation Tasks:**
- [ ] Review how integration tests mock WorkflowOrchestrator
- [ ] Verify CLI commands properly instantiate workflow
- [ ] Check error propagation from services to CLI
- [ ] Ensure mock return values match expected types
- [ ] Test actual CLI commands manually

**Root Causes to Investigate:**
1. WorkflowOrchestrator not being called as expected
2. Error handling not matching test expectations
3. Mock objects not configured correctly
4. CLI context not set up properly in tests

**Proposed Solution:**
After investigation, likely need to:
1. Fix mock setup in tests OR
2. Fix CLI command workflow integration OR
3. Both

**Acceptance Criteria:**
- [ ] All CLI integration tests pass
- [ ] Real CLI commands work as expected
- [ ] Mock setup matches production code behavior
- [ ] Error handling tested properly

**Estimated Effort:** 3 hours (1 hour investigation + 2 hours fixes)

---

### ISSUE-027: Setup Command Test Isolation Problem

**Severity:** 🟠 Medium
**Type:** Bug
**Labels:** `bug`, `medium-priority`, `testing`, `cli`

**Description:**
The `setup` command test fails because it finds an existing config file from previous runs or actual usage. Tests aren't properly isolated and use the real user's home directory.

**Test Evidence:**
```
FAILED tests/test_cli_integration.py::TestCLISetupCommands::test_setup_command_success
AssertionError: assert 'Configuration file created successfully' in
  'Configuration file already exists at: /Users/candlekeep/.podknow/config.md'
```

**Files Affected:**
- `tests/test_cli_integration.py` (test fixtures)
- `tests/conftest.py` (shared test fixtures)
- `podknow/config/manager.py` (config path handling)

**Current Problem:**
Tests use real `~/.podknow/config.md` instead of temporary test directory.

**Proposed Solution - Option A (Recommended):**
Use temporary directory for tests:
```python
# tests/conftest.py
@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Provide temporary home directory for tests."""
    temp_home_dir = tmp_path / "home"
    temp_home_dir.mkdir()
    monkeypatch.setenv("HOME", str(temp_home_dir))
    return temp_home_dir

@pytest.fixture
def clean_config(temp_home):
    """Ensure clean config state for tests."""
    config_dir = temp_home / ".podknow"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir
```

**Proposed Solution - Option B:**
Make ConfigManager accept path override:
```python
class ConfigManager:
    def __init__(self, config_path: Optional[Path] = None, home_dir: Optional[Path] = None):
        if config_path:
            self.config_path = config_path
        elif home_dir:
            self.config_path = home_dir / ".podknow" / "config.md"
        else:
            self.config_path = Path.home() / ".podknow" / "config.md"
```

**Acceptance Criteria:**
- [ ] Tests don't modify real user config
- [ ] Tests use isolated temporary directories
- [ ] Setup command tests pass consistently
- [ ] No cleanup required after test runs
- [ ] Tests can run in parallel without conflicts

**Estimated Effort:** 1 hour

---

### ISSUE-028: Keyboard Interrupt Exit Code Incorrect

**Severity:** 🟠 Medium
**Type:** Bug
**Labels:** `bug`, `medium-priority`, `cli`, `error-handling`

**Description:**
When a KeyboardInterrupt occurs (Ctrl+C), the CLI should exit with code 130 (Unix convention for SIGINT), but it returns 0 (success).

**Test Evidence:**
```
FAILED tests/test_cli_integration.py::TestCLIErrorHandling::test_cli_keyboard_interrupt
assert 0 == 130
```

**Files Affected:**
- `podknow/cli/main.py` (exception handler setup)

**Current Code:**
```python
def handle_exception(exc_type, exc_value, exc_traceback):
    # ...
    elif isinstance(exc_value, KeyboardInterrupt):
        click.echo("\nOperation cancelled by user.", err=True)
        sys.exit(130)  # Code is correct but not reached
```

**Problem:**
The exception handler exists but KeyboardInterrupt might be:
1. Caught by Click framework before reaching handler
2. Not properly propagated in test environment
3. Overridden by another exception handler

**Proposed Solution:**
Add explicit signal handling in addition to exception hook:
```python
import signal

@click.group()
@click.pass_context
def cli(ctx: click.Context, ...):
    # Existing exception handler
    sys.excepthook = handle_exception

    # Add signal handler for SIGINT
    def sigint_handler(signum, frame):
        click.echo("\nOperation cancelled by user.", err=True)
        sys.exit(130)

    signal.signal(signal.SIGINT, sigint_handler)

    # Rest of CLI initialization
```

**Acceptance Criteria:**
- [ ] Ctrl+C exits with code 130
- [ ] Test `test_cli_keyboard_interrupt` passes
- [ ] Works in both test and production environments
- [ ] User sees cancellation message
- [ ] No cleanup issues

**Estimated Effort:** 1 hour

---

### ISSUE-029: Error Exit Codes Not Set Properly

**Severity:** 🟠 Medium
**Type:** Bug
**Labels:** `bug`, `medium-priority`, `cli`, `error-handling`

**Description:**
When errors occur, the CLI exits with code 0 (success) instead of 1 (error). This breaks shell scripting, automation, and CI/CD pipelines.

**Test Evidence:**
```
FAILED tests/test_cli_integration.py::TestCLIErrorHandling::test_cli_unexpected_error_verbose
assert 0 == 1

FAILED tests/test_cli_integration.py::TestCLIErrorHandling::test_cli_unexpected_error_normal
assert 0 == 1
```

**Files Affected:**
- `podknow/cli/main.py` (error handling in all commands)

**Impact:**
- Shell scripts can't detect PodKnow failures
- CI/CD pipelines don't fail when they should
- Automation tools can't react to errors
- Poor developer experience

**Current Problem:**
Exceptions are caught but exit code not explicitly set:
```python
except Exception as e:
    verbose_echo(ctx, f"Unexpected error: {e}")
    error_echo("An unexpected error occurred")
    # Missing: sys.exit(1) or raise SystemExit(1)
```

**Proposed Solution:**
Ensure all error paths set exit code:
```python
except PodKnowError as e:
    error_echo(f"Error: {e}")
    raise SystemExit(1)

except NetworkError as e:
    error_echo(f"Network error: {e}")
    raise SystemExit(1)

except Exception as e:
    error_echo(f"Unexpected error: {e}")
    if ctx.obj.get('verbose'):
        raise  # Let Click handle with traceback
    raise SystemExit(1)
```

**Acceptance Criteria:**
- [ ] All errors exit with code 1
- [ ] Success exits with code 0
- [ ] Tests pass: `test_cli_unexpected_error_*`
- [ ] Shell scripts can detect failures
- [ ] CI/CD integration works correctly

**Estimated Effort:** 1 hour

---

## 🔵 LOW PRIORITY (Test Infrastructure)

### ISSUE-030: Mock Setup Issues in Tests

**Severity:** 🔵 Low
**Type:** Testing
**Labels:** `testing`, `low-priority`, `technical-debt`

**Description:**
Some unit tests have incorrect mock configurations, causing failures even though the production code works correctly.

**Test Evidence:**
```
FAILED tests/test_analysis_service.py::TestClaudeAPIClient::test_send_message_empty_response_raises_error
FAILED tests/test_analysis_service.py::TestClaudeAPIClient::test_send_message_rate_limit_retry
FAILED tests/test_analysis_service.py::TestAnalysisService::test_init_with_api_key
FAILED tests/test_analysis_service.py::TestAnalysisService::test_get_default_prompts
```

**Files Affected:**
- `tests/test_analysis_service.py` (mock setup)
- `tests/conftest.py` (shared fixtures)

**Issues:**
1. Claude API response mocks don't match actual API structure
2. ConfigManager mocks don't provide expected prompt structure
3. Rate limit retry test doesn't properly simulate retries
4. Mock return values have wrong types

**Proposed Solution:**
1. **Fix Claude API mocks:**
```python
@pytest.fixture
def mock_claude_response():
    """Provide properly structured Claude API response."""
    response = Mock()
    response.content = [Mock(text="Test response")]
    return response
```

2. **Fix ConfigManager mocks:**
```python
@pytest.fixture
def mock_config_with_prompts():
    """Provide config with all required prompts."""
    config = Mock()
    config.prompts = {
        'summary': 'Test summary prompt',
        'topics': 'Test topics prompt',
        'keywords': 'Test keywords prompt',
        'sponsor_detection': 'Test sponsor prompt'
    }
    return config
```

**Acceptance Criteria:**
- [ ] All analysis service tests pass
- [ ] Mocks match production API structure
- [ ] Tests properly verify behavior
- [ ] Easy to maintain test mocks

**Estimated Effort:** 2 hours

---

### ISSUE-031: Audio Processing Tests Need Mocking

**Severity:** 🔵 Low
**Type:** Testing
**Labels:** `testing`, `low-priority`, `audio-processing`

**Description:**
Language detection tests fail because they try to create real audio samples, which requires librosa/soundfile and test audio files.

**Test Evidence:**
```
FAILED tests/test_transcription_service.py::TestLanguageDetection::test_english_language_detection
FAILED tests/test_transcription_service.py::TestLanguageDetection::test_non_english_language_rejection
FAILED tests/test_transcription_service.py::TestLanguageDetection::test_language_detection_mlx_error
Error: AudioProcessingError: Failed to create audio sample
```

**Files Affected:**
- `tests/test_transcription_service.py` (language detection tests)

**Problem:**
Tests call real audio processing functions instead of mocking:
```python
def test_language_detection():
    # This tries to actually load audio
    result = service.detect_language(audio_path)
```

**Proposed Solution:**
Mock audio loading functions:
```python
@pytest.fixture
def mock_audio_data():
    """Provide mock audio data for testing."""
    import numpy as np
    sample_rate = 16000
    audio = np.random.randn(sample_rate)
    return audio, sample_rate

@patch('librosa.load')
@patch('soundfile.write')
def test_language_detection(mock_write, mock_load, mock_audio_data):
    mock_load.return_value = mock_audio_data
    # Test continues with mocked audio
```

**Acceptance Criteria:**
- [ ] Language detection tests pass
- [ ] Tests don't require real audio files
- [ ] Tests don't require librosa/soundfile installed
- [ ] Tests run quickly (no audio processing)

**Estimated Effort:** 2 hours

---

### ISSUE-032: Workflow Integration Tests Need Better Mocks

**Severity:** 🔵 Low
**Type:** Testing
**Labels:** `testing`, `low-priority`, `workflow`

**Description:**
Workflow orchestrator integration tests fail due to incomplete mock setup.

**Test Evidence:**
```
FAILED tests/test_workflow_integration.py::TestWorkflowOrchestrator::test_transcription_workflow_success
Error: TranscriptionError: Processing failed: object of type 'Mock' has no len()

FAILED tests/test_workflow_integration.py::TestWorkflowOrchestrator::test_transcription_workflow_language_error
AssertionError: Expected 'cleanup_audio_file' to have been called once. Called 0 times.
```

**Files Affected:**
- `tests/test_workflow_integration.py` (workflow tests)

**Issues:**
1. Mock objects don't have `__len__` method when needed
2. Cleanup not called in expected scenarios
3. Mock services don't properly simulate workflow steps

**Proposed Solution:**
Create comprehensive workflow test fixtures:
```python
@pytest.fixture
def mock_workflow_services():
    """Provide fully mocked services for workflow testing."""
    mock_transcription = Mock()
    mock_transcription.transcribe_audio.return_value = Mock(
        text="Test transcription",
        segments=[],
        language="en",
        confidence=0.95
    )
    mock_transcription.download_audio.return_value = "/tmp/audio.mp3"

    # Add __len__ for objects that need it
    mock_result = Mock()
    mock_result.__len__ = Mock(return_value=100)

    return {
        'transcription': mock_transcription,
        'analysis': Mock(),
        'episode': Mock()
    }
```

**Acceptance Criteria:**
- [ ] All workflow integration tests pass
- [ ] Mocks properly simulate service behavior
- [ ] Cleanup verification works correctly
- [ ] Tests verify workflow orchestration logic

**Estimated Effort:** 2 hours

---

## 📊 Updated Issue Summary

### Total Issues (Original + New):
- **Original:** 24 issues
- **New from Testing:** 8 issues
- **Total:** 32 issues

### Updated Priority Distribution:
```
🔴 Critical:    3 (Original)
🟡 High:        5 (Original: 4 + New: 1)
🟠 Medium:      10 (Original: 6 + New: 4)
🔵 Low:         9 (Original: 6 + New: 3)
📊 Enhancement: 5 (Original)
```

### Updated Effort Estimates:
```
Critical:     1 hour
High:        10.5 hours  (Original 10h + New 0.5h)
Medium:      15 hours    (Original 9h + New 6h)
Low:         10.5 hours  (Original 4.5h + New 6h)
Enhancement: 46 hours
Buffer:      17 hours
TOTAL:      ~100 hours
```

---

## 🎯 Updated Sprint Plan

### Sprint 1 - Critical + High (11.5 hours)
**Original:**
- ISSUE-001, 002, 003 (Critical)
- ISSUE-004, 005, 006, 007 (High)

**Add from Testing:**
- ISSUE-025 (High - Topic validation)

**Total Effort:** 11.5 hours

### Sprint 2 - Medium Priority (15 hours)
**Original:**
- ISSUE-008, 009, 010, 011, 012, 013

**Add from Testing:**
- ISSUE-026 (CLI integration)
- ISSUE-027 (Test isolation)
- ISSUE-028 (Keyboard interrupt)
- ISSUE-029 (Exit codes)

**Total Effort:** 15 hours

### Sprint 3 - Low Priority + Test Infrastructure (10.5 hours)
**Original:**
- ISSUE-014, 015, 016, 017, 018, 019

**Add from Testing:**
- ISSUE-030 (Mock setup)
- ISSUE-031 (Audio test mocking)
- ISSUE-032 (Workflow test mocking)

**Total Effort:** 10.5 hours

---

## 🚀 Quick Wins (Do These First!)

### 1. Fix Missing Import (5 minutes) - CONFIRMED BUG
```bash
# Add to podknow/cli/main.py imports
from ..exceptions import PodKnowError, NetworkError, AnalysisError
```
**Expected:** 6 test failures → 0 failures ✅

### 2. Make Topics Optional (10 minutes)
```bash
# Update podknow/models/analysis.py
topics: List[str] = field(default_factory=list)
```
**Expected:** 1 test failure → 0 failures ✅

### 3. Fix Exit Codes (15 minutes)
```bash
# Add to all error handlers in podknow/cli/main.py
raise SystemExit(1)
```
**Expected:** 3 test failures → 0 failures ✅

**Total Time:** 30 minutes
**Total Fixes:** 10 test failures eliminated
**Test Success Rate:** 85.7% → 89.4% ✅

---

## 📝 How to Use This Supplement

1. **Read TEST_FAILURE_ANALYSIS.md first** for detailed failure analysis
2. **Use this document** for GitHub issue creation
3. **Add these issues** to main WORK_BREAKDOWN.md
4. **Update ISSUES_CHECKLIST.md** with new issues
5. **Re-run tests** after each fix to verify

---

*Supplement created: 2025-10-27*
*Based on: pytest test run with 35 failures*
*New issues: 8 (1 high, 4 medium, 3 low priority)*
*Total estimated effort added: ~15 hours*
