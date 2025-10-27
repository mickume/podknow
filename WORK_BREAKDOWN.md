# PodKnow - Work Breakdown & Issue Tracker

> Generated: 2025-10-27
> Based on: Comprehensive codebase analysis
> Total Issues: 24

---

## 🔴 CRITICAL PRIORITY (Fix Immediately)

### ISSUE-001: Duplicate `setup` Command Definition

**Severity:** 🔴 Critical
**Type:** Bug
**Labels:** `bug`, `critical`, `cli`, `technical-debt`

**Description:**
The `setup` command is defined twice in `podknow/cli/main.py`, causing the first definition to be completely unreachable. This is a critical code smell indicating incomplete refactoring.

**Files Affected:**
- `podknow/cli/main.py` (lines 535-601, 718-763)

**Steps to Reproduce:**
1. Search for `def setup` in `cli/main.py`
2. Observe two complete function definitions with `@cli.command()` decorator

**Root Cause:**
Copy-paste error or incomplete refactoring during development.

**Proposed Solution:**
1. Compare both implementations to determine which is more complete
2. Delete the less complete or outdated implementation
3. Ensure all functionality from both versions is preserved in the remaining one
4. Add unit test to verify `setup` command works correctly

**Acceptance Criteria:**
- [ ] Only one `setup` command definition exists
- [ ] `podknow setup` command executes without errors
- [ ] `podknow setup --force` overwrites existing config correctly
- [ ] Unit test added for setup command

**Estimated Effort:** 30 minutes

---

### ISSUE-002: Missing `AnalysisError` Import in CLI

**Severity:** 🔴 Critical
**Type:** Bug
**Labels:** `bug`, `critical`, `cli`, `import-error`

**Description:**
`AnalysisError` exception is used in the `analyze` command (line 520) but never imported, causing a `NameError` at runtime when the exception is caught.

**Files Affected:**
- `podknow/cli/main.py` (line 520)

**Steps to Reproduce:**
1. Run `podknow analyze <file>` with invalid Claude API key or network error
2. Observe `NameError: name 'AnalysisError' is not defined`

**Current Code:**
```python
except AnalysisError as e:  # Line 520 - AnalysisError not imported!
    error_echo(f"Analysis failed: {e}")
```

**Proposed Solution:**
Add import at the top of the file:
```python
from ..exceptions import PodKnowError, NetworkError, AnalysisError
```

**Acceptance Criteria:**
- [ ] `AnalysisError` imported in `cli/main.py`
- [ ] Code runs without `NameError`
- [ ] Error handling works correctly for analysis failures
- [ ] Add integration test that triggers this exception path

**Estimated Effort:** 10 minutes

---

### ISSUE-003: Inconsistent Prompt Naming Convention

**Severity:** 🔴 Critical
**Type:** Bug
**Labels:** `bug`, `critical`, `configuration`, `analysis`

**Description:**
Inconsistent naming of the sponsor detection prompt across multiple files causes configuration mapping to fail. The workflow orchestrator uses `'sponsors'` while config files and analysis service use `'sponsor_detection'`.

**Files Affected:**
- `podknow/services/workflow.py` (line 220)
- `podknow/services/analysis.py` (line 228)
- `podknow/config/manager.py` (line 92)
- `podknow/config/models.py` (line 123)

**Current Code (workflow.py:220):**
```python
prompts = {
    'summary': config.prompts.get('summary'),
    'topics': config.prompts.get('topics'),
    'keywords': config.prompts.get('keywords'),
    'sponsors': config.prompts.get('sponsor_detection')  # WRONG KEY
}
```

**Impact:**
User-configured sponsor detection prompts are not loaded, causing the service to fall back to defaults or skip sponsor detection entirely.

**Proposed Solution:**
Standardize on `'sponsor_detection'` everywhere:
```python
prompts = {
    'summary': config.prompts.get('summary'),
    'topics': config.prompts.get('topics'),
    'keywords': config.prompts.get('keywords'),
    'sponsor_detection': config.prompts.get('sponsor_detection')
}
```

**Acceptance Criteria:**
- [ ] All files use consistent key name `'sponsor_detection'`
- [ ] Custom sponsor prompts load correctly from config
- [ ] Sponsor detection works with user-defined prompts
- [ ] Add integration test for custom prompt loading

**Estimated Effort:** 20 minutes

---

## 🟡 HIGH PRIORITY (Fix Soon)

### ISSUE-004: Configuration Regex Patterns Too Rigid ✅ FIXED

**Severity:** 🟡 High
**Type:** Bug
**Labels:** `bug`, `high-priority`, `configuration`, `parsing`
**Status:** ✅ **RESOLVED** (2025-10-27)

**Description:**
Regular expressions in `ConfigManager._parse_markdown_config()` don't correctly match the actual config file format due to whitespace differences.

**Files Affected:**
- `podknow/config/manager.py` (lines 88-93)

**Original Code:**
```python
prompt_sections = {
    'summary': r'### Summary Prompt\n```\n(.*?)\n```',
    # Doesn't match actual format with blank lines
}
```

**Actual Config Format:**
```markdown
### Summary Prompt

```
Analyze this podcast...
```
```

**Applied Solution:**
Updated regex to handle optional whitespace:
```python
prompt_sections = {
    'summary': r'### Summary Prompt\s*\n```\n(.*?)\n```',
    'topics': r'### Topic Extraction Prompt\s*\n```\n(.*?)\n```',
    'keywords': r'### Keyword Identification Prompt\s*\n```\n(.*?)\n```',
    'sponsor_detection': r'### Sponsor Detection Prompt\s*\n```\n(.*?)\n```'
}
```

**Acceptance Criteria:**
- [x] Regex patterns match actual config file format
- [x] All prompts load correctly from default config
- [x] Prompts with extra whitespace are handled gracefully
- [x] Config manager tests pass (27/27 passing)
- [x] Test with various whitespace configurations

**Actual Effort:** 1 hour

---

### ISSUE-005: Verify Episode Service Implementation Completeness

**Severity:** 🟡 High
**Type:** Investigation
**Labels:** `investigation`, `high-priority`, `services`

**Description:**
The workflow orchestrator references several methods from `EpisodeListingService` that need verification for completeness and correctness.

**Files Affected:**
- `podknow/services/episode.py` (needs review)
- `podknow/services/workflow.py` (lines 312-319, 364-366)

**Methods Referenced:**
- `get_podcast_info(rss_url)`
- `list_episodes(rss_url, count)`
- `find_episode_by_id(rss_url, episode_id)`

**Investigation Tasks:**
- [ ] Verify all three methods exist and are implemented
- [ ] Check method signatures match workflow expectations
- [ ] Ensure proper error handling
- [ ] Verify return types match model definitions
- [ ] Check for edge cases (empty feed, invalid ID, etc.)

**Proposed Solution:**
1. Review `services/episode.py` implementation
2. Add missing methods if any
3. Ensure consistent error handling
4. Add comprehensive unit tests
5. Document method contracts

**Acceptance Criteria:**
- [ ] All referenced methods exist and work correctly
- [ ] Methods handle edge cases properly
- [ ] Unit tests achieve >90% coverage
- [ ] Integration tests verify workflow integration

**Estimated Effort:** 2 hours

---

### ISSUE-006: Progress Bar Display Complexity and Duplication

**Severity:** 🟡 High
**Type:** Code Quality
**Labels:** `enhancement`, `high-priority`, `ux`, `refactoring`

**Description:**
Multiple layers of progress bars (service-level and workflow-level) create complexity and potential UI confusion. The current solution uses `suppress_progress` flags, which is fragile.

**Files Affected:**
- `podknow/services/transcription.py` (lines 169-215, 368-435)
- `podknow/services/analysis.py` (lines 278-348)
- `podknow/services/workflow.py` (lines 584-621)

**Current Issues:**
- Progress bars can nest if flags are set incorrectly
- Difficult to maintain consistency
- `suppress_progress` parameter spreads throughout codebase
- No centralized progress management

**Proposed Solution:**
Create a centralized progress manager:
```python
class ProgressManager:
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.current_context = None

    @contextmanager
    def task(self, description: str, total: int = None):
        # Centralized progress handling
        pass
```

**Acceptance Criteria:**
- [ ] Single source of truth for progress display
- [ ] No nested progress bars
- [ ] Consistent UX across all commands
- [ ] Easy to enable/disable progress globally
- [ ] Backward compatible with existing code

**Estimated Effort:** 4 hours

---

### ISSUE-007: Inconsistent Error Handling Across CLI Commands

**Severity:** 🟡 High
**Type:** Code Quality
**Labels:** `enhancement`, `high-priority`, `cli`, `error-handling`

**Description:**
CLI commands handle exceptions inconsistently, with some catching specific exceptions and others using broad `except Exception` clauses. Error messages are also inconsistent.

**Files Affected:**
- `podknow/cli/main.py` (multiple command functions)

**Examples of Inconsistency:**
```python
# search command - catches NetworkError specifically
except NetworkError as e:
    error_echo(f"Search failed: {e}")

# list command - catches generic Exception
except Exception as e:
    error_echo("An unexpected error occurred")
```

**Proposed Solution:**
1. Create standardized error handling decorator:
```python
def handle_podknow_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except LanguageDetectionError as e:
            # Specific handling
        except NetworkError as e:
            # Specific handling
        except PodKnowError as e:
            # Generic PodKnow error
        except Exception as e:
            # Unexpected error
    return wrapper
```

2. Apply decorator to all CLI commands
3. Standardize error message format

**Acceptance Criteria:**
- [ ] All CLI commands use consistent error handling
- [ ] Error messages follow standard format
- [ ] Specific exceptions are caught and handled appropriately
- [ ] Generic exceptions provide helpful troubleshooting info
- [ ] Verbose mode shows full stack traces

**Estimated Effort:** 3 hours

---

### ISSUE-025: Analysis Service Topic Validation Too Strict

**Severity:** 🟡 High
**Type:** Bug
**Labels:** `bug`, `high-priority`, `analysis`, `validation`
**Source:** pytest test failures

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

## 🟠 MEDIUM PRIORITY (Address in Next Sprint)

### ISSUE-008: Replace Print Statements with Proper Logging

**Severity:** 🟠 Medium
**Type:** Code Quality
**Labels:** `enhancement`, `medium-priority`, `logging`, `refactoring`

**Description:**
Multiple service files use `print()` statements instead of proper logging, making it difficult to control output levels and debug production issues.

**Files Affected:**
- `podknow/services/discovery.py` (lines 278, 288)
- `podknow/services/analysis.py` (lines 245, 492, 511, 534, 543)
- `podknow/services/rss.py` (line 200)
- `podknow/services/transcription.py` (multiple locations)

**Current Pattern:**
```python
print(f"iTunes search failed: {e}")  # Should use logger
```

**Proposed Solution:**
1. Add module-level logger to each service:
```python
import logging
logger = logging.getLogger(__name__)
```

2. Replace print statements:
```python
logger.warning(f"iTunes search failed: {e}")
```

3. Configure logging levels appropriately:
   - DEBUG: Detailed diagnostic information
   - INFO: General informational messages
   - WARNING: Warning messages (like search failures)
   - ERROR: Error messages

**Acceptance Criteria:**
- [ ] All `print()` statements replaced with logger calls
- [ ] Appropriate log levels used for each message
- [ ] Logging respects `--verbose` flag
- [ ] Log output can be redirected to file
- [ ] No breaking changes to CLI output

**Estimated Effort:** 2 hours

**Files to Update:**
```
podknow/services/discovery.py
podknow/services/analysis.py
podknow/services/rss.py
podknow/services/transcription.py
```

---

### ISSUE-009: Extract Magic Numbers to Named Constants

**Severity:** 🟠 Medium
**Type:** Code Quality
**Labels:** `enhancement`, `medium-priority`, `maintainability`, `refactoring`

**Description:**
Hard-coded numeric values scattered throughout the codebase reduce maintainability and make it difficult to tune parameters.

**Files Affected:**
- `podknow/services/transcription.py` (lines 234, 260, 538)
- `podknow/services/rss.py` (line 327)
- `podknow/config/manager.py` (line 327)

**Current Examples:**
```python
# transcription.py:538
if time_gap > 2.0:  # Magic number - paragraph threshold

# transcription.py:234
skip_minutes: float = 2.0  # Magic number - language detection skip

# rss.py:327
return hash_object.hexdigest()[:12]  # Magic number - ID length
```

**Proposed Solution:**
Add to `podknow/constants.py`:
```python
# Transcription Settings
PARAGRAPH_TIME_GAP_THRESHOLD = 2.0  # seconds
DEFAULT_LANGUAGE_DETECTION_SKIP_MINUTES = 2.0
LANGUAGE_DETECTION_SAMPLE_DURATION = 30.0  # seconds

# ID Generation
EPISODE_ID_HASH_LENGTH = 12
```

Then update all usage sites to reference constants.

**Acceptance Criteria:**
- [ ] All magic numbers identified and documented
- [ ] Constants added to `constants.py` with clear names
- [ ] All usage sites updated to reference constants
- [ ] Constants have docstring comments explaining usage
- [ ] No regression in functionality

**Estimated Effort:** 1.5 hours

**Magic Numbers Inventory:**
| File | Line | Value | Proposed Constant |
|------|------|-------|------------------|
| transcription.py | 538 | 2.0 | PARAGRAPH_TIME_GAP_THRESHOLD |
| transcription.py | 234 | 2.0 | DEFAULT_LANGUAGE_DETECTION_SKIP_MINUTES |
| transcription.py | 260 | 30.0 | LANGUAGE_DETECTION_SAMPLE_DURATION |
| rss.py | 327 | 12 | EPISODE_ID_HASH_LENGTH |
| discovery.py | 42 | 200 | ITUNES_API_MAX_LIMIT |
| discovery.py | 192 | 50 | SPOTIFY_API_MAX_LIMIT |

---

### ISSUE-010: Reduce Coupling Between Workflow and Service Internals

**Severity:** 🟠 Medium
**Type:** Architecture
**Labels:** `enhancement`, `medium-priority`, `architecture`, `refactoring`

**Description:**
`WorkflowOrchestrator` directly accesses private methods of service classes (methods prefixed with `_`), breaking encapsulation and making refactoring difficult.

**Files Affected:**
- `podknow/services/workflow.py` (line 460)
- `podknow/services/transcription.py` (method `_generate_filename`)

**Current Code:**
```python
# workflow.py:460
filename = self.transcription_service._generate_filename(episode_metadata)
```

**Problem:**
Private methods should not be called from outside the class. This creates tight coupling and makes it hard to change internal implementation.

**Proposed Solution:**
1. Make `_generate_filename` public by removing `_` prefix:
```python
# transcription.py
def generate_filename(self, episode_metadata: EpisodeMetadata) -> str:
    """Generate filename based on episode metadata."""
    # Implementation
```

2. Update workflow to call public method:
```python
# workflow.py
filename = self.transcription_service.generate_filename(episode_metadata)
```

3. Audit codebase for other private method calls across class boundaries

**Acceptance Criteria:**
- [ ] No private methods called from outside their class
- [ ] Public API clearly defined for each service
- [ ] Service methods are properly encapsulated
- [ ] No regression in functionality
- [ ] Update documentation to reflect public API

**Estimated Effort:** 1 hour

---

### ISSUE-011: Weak Audio File Format Validation

**Severity:** 🟠 Medium
**Type:** Enhancement
**Labels:** `enhancement`, `medium-priority`, `validation`, `audio-processing`

**Description:**
Current validation only checks MIME types and file extensions, not actual audio content. This can lead to processing failures on corrupted or misidentified files.

**Files Affected:**
- `podknow/services/transcription.py` (lines 110-135)

**Current Validation:**
```python
def _is_audio_content(self, content_type: str, filename: str) -> bool:
    # Only checks MIME type and extension
    if content_type and content_type.startswith('audio/'):
        return True
    # No actual content validation
```

**Limitations:**
- Doesn't detect corrupted audio files
- Doesn't verify audio can be decoded
- No duration or sample rate checks
- Could waste time downloading invalid files

**Proposed Solution:**
Add lightweight audio validation:
```python
def _validate_audio_file(self, file_path: str) -> bool:
    """Validate audio file can be decoded."""
    try:
        import librosa
        # Try to load just the first second
        y, sr = librosa.load(file_path, duration=1.0, sr=None)

        # Basic sanity checks
        if len(y) == 0 or sr == 0:
            return False

        return True
    except Exception as e:
        logger.warning(f"Audio validation failed: {e}")
        return False
```

**Acceptance Criteria:**
- [ ] Audio files validated before processing
- [ ] Corrupted files detected early
- [ ] Clear error messages for invalid files
- [ ] Minimal performance impact
- [ ] Graceful fallback if validation library unavailable

**Estimated Effort:** 2 hours

---

### ISSUE-012: Language Detection Requirement Not Enforced Per PRD

**Severity:** 🟠 Medium
**Type:** Documentation/Feature Mismatch
**Labels:** `documentation`, `medium-priority`, `feature-mismatch`

**Description:**
PRD states tool should only process English content, but CLI allows skipping language detection entirely with `--skip-language-detection` flag.

**Files Affected:**
- `prd.md` (line 16)
- `podknow/cli/main.py` (lines 342-344)
- `podknow/services/workflow.py` (lines 336, 598-605)

**PRD Statement:**
> "With a dedicated command, download the media file and transcribe the content, if the language is "english" only."

**Current Implementation:**
```python
@click.option(
    "--skip-language-detection",
    is_flag=True,
    help="Skip language detection and assume English content"
)
```

**Inconsistency:**
User can bypass English-only requirement, which contradicts PRD.

**Proposed Solution:**
Two options:

**Option A: Enforce PRD (Stricter)**
- Remove `--skip-language-detection` flag
- Always perform language detection
- Reject non-English content

**Option B: Update PRD (More Flexible)**
- Update PRD to allow optional language detection
- Keep current implementation
- Document the flag clearly

**Recommendation:** Option B (more flexible, better UX)

**Acceptance Criteria:**
- [ ] Decision made on which option to implement
- [ ] PRD updated to match implementation OR flag removed
- [ ] Documentation consistent across all files
- [ ] User guide explains language handling clearly

**Estimated Effort:** 30 minutes (decision) + 1 hour (implementation)

---

### ISSUE-013: String Formatting Inconsistency

**Severity:** 🟠 Medium
**Type:** Code Quality
**Labels:** `enhancement`, `medium-priority`, `code-style`, `refactoring`

**Description:**
Mix of f-strings, `.format()`, and concatenation throughout the codebase reduces readability and maintainability.

**Files Affected:**
- Multiple files across the project

**Current State:**
```python
# Modern (preferred)
f"Search failed: {error}"

# Older style
"Search failed: {}".format(error)

# Concatenation
"Search failed: " + str(error)
```

**Proposed Solution:**
1. Standardize on f-strings (PEP 498) for all Python 3.6+:
```python
f"Search failed: {error}"
```

2. Use format() only for templates that need to be stored:
```python
template = "Error {error_type}: {message}"
result = template.format(error_type="Network", message="Timeout")
```

3. Create linting rule to enforce f-strings

**Acceptance Criteria:**
- [ ] All string formatting uses f-strings (except templates)
- [ ] Ruff or flake8 rule added to enforce f-strings
- [ ] Pre-commit hook validates formatting
- [ ] No functional changes

**Estimated Effort:** 1 hour

---

### ISSUE-026: CLI Integration Test Failures

**Severity:** 🟠 Medium
**Type:** Investigation + Bug
**Labels:** `bug`, `medium-priority`, `cli`, `integration`, `testing`
**Source:** pytest test failures

**Description:**
Multiple CLI integration tests fail due to incorrect mock setup or actual integration problems between CLI commands and WorkflowOrchestrator.

**Test Evidence:**
```
FAILED tests/test_cli_integration.py::TestCLISearchCommand::test_search_command_success
FAILED tests/test_cli_integration.py::TestCLISearchCommand::test_search_command_with_options
FAILED tests/test_cli_integration.py::TestCLISearchCommand::test_search_command_network_error
FAILED tests/test_cli_integration.py::TestCLISearchCommand::test_search_command_no_results
FAILED tests/test_cli_integration.py::TestCLIListCommand::test_list_command_success
(15 total failures)
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
**Source:** pytest test failures

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

**Proposed Solution:**
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
**Source:** pytest test failures

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
**Source:** pytest test failures

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

## 🔵 LOW PRIORITY (Nice to Have)

### ISSUE-014: Missing Type Hints in Helper Methods

**Severity:** 🔵 Low
**Type:** Code Quality
**Labels:** `enhancement`, `low-priority`, `type-hints`, `documentation`

**Description:**
Some internal helper methods lack complete type hints, reducing IDE support and static type checking effectiveness.

**Files Affected:**
- `podknow/config/manager.py` (line 119)
- Various `_helper_method` functions

**Current Example:**
```python
def _extract_metadata_from_feed(self, feed, rss_url: str):  # Missing return type
    """Helper method to extract metadata from parsed feed."""
    # Implementation
```

**Proposed Solution:**
```python
def _extract_metadata_from_feed(self, feed, rss_url: str) -> PodcastMetadata:
    """Helper method to extract metadata from parsed feed."""
    # Implementation
```

**Acceptance Criteria:**
- [ ] All public methods have complete type hints
- [ ] All helper methods have return type hints
- [ ] mypy passes with no errors (or documented exceptions)
- [ ] Type hints match actual return values

**Estimated Effort:** 2 hours

---

### ISSUE-015: Improve Code Comments and TODO Tracking

**Severity:** 🔵 Low
**Type:** Code Quality
**Labels:** `enhancement`, `low-priority`, `documentation`, `technical-debt`

**Description:**
Some comments describe error handling or future work but don't use standard TODO/FIXME markers, making them hard to track.

**Files Affected:**
- `podknow/services/rss.py` (line 200)
- Multiple files with informal comments

**Current Example:**
```python
# Log the error but continue processing other episodes
```

**Should Be:**
```python
# TODO: Consider collecting all errors and reporting at the end
# Log the error but continue processing other episodes
```

**Proposed Solution:**
1. Standardize on comment markers:
   - `# TODO:` - Future work, nice to have
   - `# FIXME:` - Known issue that needs fixing
   - `# HACK:` - Temporary workaround
   - `# NOTE:` - Important information

2. Add tool to extract and track TODOs:
```bash
# Create script to generate TODO report
scripts/list_todos.py
```

**Acceptance Criteria:**
- [ ] All informal comments reviewed
- [ ] Appropriate markers added
- [ ] TODO extraction script created
- [ ] Documentation explains comment conventions

**Estimated Effort:** 1 hour

---

### ISSUE-016: Unused Exception Import in Workflow

**Severity:** 🔵 Low
**Type:** Code Quality
**Labels:** `enhancement`, `low-priority`, `cleanup`

**Description:**
`EpisodeManagementError` is imported but never used in workflow orchestrator.

**Files Affected:**
- `podknow/services/workflow.py` (line 27)

**Current Code:**
```python
from ..exceptions import (
    PodKnowError,
    NetworkError,
    TranscriptionError,
    AnalysisError,
    ConfigurationError,
    AudioProcessingError,
    LanguageDetectionError,
    FileOperationError,
    EpisodeManagementError  # Never used
)
```

**Proposed Solution:**
Either:
1. Remove unused import if not needed
2. Add proper error handling if it should be used

**Acceptance Criteria:**
- [ ] Verify exception is truly unused
- [ ] Remove import or add proper usage
- [ ] No linting warnings

**Estimated Effort:** 10 minutes

---

### ISSUE-017: Verify Claude Model Version IDs

**Severity:** 🔵 Low
**Type:** Investigation
**Labels:** `investigation`, `low-priority`, `api`, `configuration`

**Description:**
Model version strings in constants.py have future dates that seem suspicious and should be verified against Anthropic's actual API.

**Files Affected:**
- `podknow/constants.py` (lines 9-12)

**Current Values:**
```python
CLAUDE_MODELS = {
    "sonnet": "claude-sonnet-4-20250514",   # Date: May 2025
    "haiku": "claude-haiku-4-5-20251001",   # Date: Oct 2025
    "opus": "claude-opus-4-1-20250805",     # Date: Aug 2025
}
```

**Investigation Tasks:**
- [ ] Check Anthropic API documentation for correct model IDs
- [ ] Verify model versions are publicly available
- [ ] Test each model ID with actual API
- [ ] Update to correct/latest model IDs if needed
- [ ] Add comments explaining version scheme

**Acceptance Criteria:**
- [ ] Model IDs verified as correct
- [ ] Documentation added explaining version format
- [ ] Test suite validates models work

**Estimated Effort:** 30 minutes

---

### ISSUE-018: Fix Documentation Typo

**Severity:** 🔵 Low
**Type:** Documentation
**Labels:** `documentation`, `low-priority`, `typo`

**Description:**
Typo in PRD title: "Product requiremnet" should be "Product requirement"

**Files Affected:**
- `prd.md` (line 1)

**Current:**
```markdown
## Product requiremnet
```

**Fix:**
```markdown
## Product Requirement
```

**Acceptance Criteria:**
- [ ] Typo corrected
- [ ] Document spell-checked

**Estimated Effort:** 5 minutes

---

### ISSUE-019: Update README with Correct CLI Examples

**Severity:** 🔵 Low
**Type:** Documentation
**Labels:** `documentation`, `low-priority`, `cli`

**Description:**
README shows incomplete command examples that won't work without required parameters.

**Files Affected:**
- `README.md` (line 53)

**Current Example:**
```bash
# Transcribe an episode
podknow transcribe episode_123
```

**Problem:**
Missing required `--rss-url` parameter, command will fail.

**Correct Example:**
```bash
# Transcribe an episode
podknow transcribe episode_123 --rss-url "https://example.com/podcast.rss"
```

**Proposed Solution:**
1. Review all CLI examples in README
2. Add all required parameters
3. Show common optional parameters
4. Add troubleshooting section

**Acceptance Criteria:**
- [ ] All examples include required parameters
- [ ] Examples actually work when copy-pasted
- [ ] Common flags and options shown
- [ ] Link to full CLI documentation

**Estimated Effort:** 30 minutes

---

### ISSUE-030: Mock Setup Issues in Tests

**Severity:** 🔵 Low
**Type:** Testing
**Labels:** `testing`, `low-priority`, `technical-debt`
**Source:** pytest test failures

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
Fix Claude API mocks:
```python
@pytest.fixture
def mock_claude_response():
    """Provide properly structured Claude API response."""
    response = Mock()
    response.content = [Mock(text="Test response")]
    return response
```

Fix ConfigManager mocks:
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
**Source:** pytest test failures

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
**Source:** pytest test failures

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

## 📊 IMPROVEMENT OPPORTUNITIES (Future Enhancements)

### ISSUE-020: Add Comprehensive Unit Tests

**Severity:** 📊 Enhancement
**Type:** Testing
**Labels:** `testing`, `enhancement`, `quality`

**Description:**
While test files exist, comprehensive coverage is needed for all services and edge cases.

**Proposed Coverage:**
- [ ] Unit tests for discovery service
  - iTunes API success/failure
  - Spotify API success/failure
  - Combined results deduplication
  - Network error handling
- [ ] Unit tests for RSS parsing
  - Valid feeds
  - Malformed feeds
  - Empty feeds
  - Missing required fields
- [ ] Unit tests for transcription service
  - Audio download
  - Language detection
  - Transcription with various audio formats
  - Error conditions
- [ ] Unit tests for analysis service
  - Claude API interaction
  - Prompt customization
  - Error handling
  - Response parsing
- [ ] Unit tests for CLI
  - Each command
  - Flag combinations
  - Error scenarios
- [ ] Integration tests for workflows
  - Full transcription workflow
  - Error recovery
  - File generation

**Coverage Goal:** >90% line coverage

**Acceptance Criteria:**
- [ ] pytest coverage report shows >90%
- [ ] All services have dedicated test files
- [ ] Edge cases documented and tested
- [ ] Mock external APIs appropriately
- [ ] Tests run in CI/CD pipeline

**Estimated Effort:** 20 hours

---

### ISSUE-021: Create Centralized Progress Management System

**Severity:** 📊 Enhancement
**Type:** Enhancement
**Labels:** `enhancement`, `ux`, `architecture`

**Description:**
Implement a proper progress management system to replace ad-hoc progress bars throughout the codebase.

**Proposed Design:**
```python
class ProgressManager:
    """Centralized progress tracking and display."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.stack = []  # Stack of active progress contexts

    @contextmanager
    def task(self, description: str, total: Optional[int] = None):
        """Create a progress context."""
        pass

    def update(self, advance: float = 1):
        """Update current task progress."""
        pass

    def set_description(self, description: str):
        """Update current task description."""
        pass
```

**Benefits:**
- Single source of truth for progress
- No nested progress bars
- Easy to disable globally
- Consistent UX across all commands
- Better testability

**Acceptance Criteria:**
- [ ] ProgressManager class implemented
- [ ] All services use ProgressManager
- [ ] No more `suppress_progress` flags
- [ ] Progress can be disabled globally
- [ ] Tests verify progress tracking

**Estimated Effort:** 6 hours

---

### ISSUE-022: Implement Analysis Result Caching

**Severity:** 📊 Enhancement
**Type:** Enhancement
**Labels:** `enhancement`, `performance`, `caching`

**Description:**
Cache Claude API analysis results to avoid redundant API calls and costs when re-analyzing the same content.

**Proposed Design:**
```python
class AnalysisCache:
    """Cache for analysis results."""

    def __init__(self, cache_dir: Path):
        self.cache_dir = cache_dir

    def get(self, content_hash: str) -> Optional[AnalysisResult]:
        """Get cached analysis result."""
        pass

    def set(self, content_hash: str, result: AnalysisResult):
        """Cache analysis result."""
        pass

    def invalidate(self, content_hash: str):
        """Invalidate cached result."""
        pass
```

**Use Cases:**
- Re-analyze with different output formats
- Recover from failures without re-calling API
- Testing and development
- Batch processing of similar content

**Acceptance Criteria:**
- [ ] Cache implemented with configurable location
- [ ] Cache hit/miss logged appropriately
- [ ] Cache expiration policy (time-based)
- [ ] Cache can be disabled via config
- [ ] CLI command to clear cache

**Estimated Effort:** 4 hours

---

### ISSUE-023: Add Batch Processing Support

**Severity:** 📊 Enhancement
**Type:** Feature
**Labels:** `enhancement`, `feature`, `cli`

**Description:**
Add ability to process multiple episodes in batch mode for efficiency.

**Proposed CLI:**
```bash
# Process last 10 episodes
podknow batch transcribe https://example.com/feed.rss --last 10

# Process specific episodes
podknow batch transcribe https://example.com/feed.rss --episodes ep1,ep2,ep3

# Process date range
podknow batch transcribe https://example.com/feed.rss --after 2024-01-01
```

**Features:**
- Parallel processing with configurable workers
- Progress tracking for batch
- Resume on failure
- Summary report at end
- Skip already processed episodes

**Acceptance Criteria:**
- [ ] Batch command implemented
- [ ] Configurable parallelism
- [ ] Resume capability
- [ ] Error handling and reporting
- [ ] Documentation and examples

**Estimated Effort:** 12 hours

---

### ISSUE-024: Create Development Container Configuration

**Severity:** 📊 Enhancement
**Type:** DevOps
**Labels:** `enhancement`, `devops`, `developer-experience`

**Description:**
Add Docker/devcontainer configuration for consistent development environment.

**Proposed Files:**
```
.devcontainer/
├── devcontainer.json
├── Dockerfile
└── docker-compose.yml
```

**Features:**
- Python 3.13 environment
- All dependencies pre-installed
- MLX-Whisper support for Apple Silicon
- VS Code integration
- Pre-configured linting and formatting
- Test database/services if needed

**Acceptance Criteria:**
- [ ] devcontainer.json configured
- [ ] Dockerfile builds successfully
- [ ] All dependencies work in container
- [ ] Documentation for container usage
- [ ] Works on Mac, Linux, Windows

**Estimated Effort:** 4 hours

---

## 📋 SUMMARY STATISTICS

**Total Issues:** 32 (24 original + 8 from pytest)
**Resolved:** 1 ✅
**Remaining:** 31

**By Severity (Remaining):**
- 🔴 Critical: 3 (Issues 001, 002, 003)
- 🟡 High: 4 (Issues 005, 006, 007, 025) - ~~004~~ resolved ✅
- 🟠 Medium: 10 (Issues 008-013, 026-029)
- 🔵 Low: 9 (Issues 014-019, 030-032)
- 📊 Enhancement: 5 (Issues 020-024)

**By Type:**
- Bug: 14 (8 original + 6 from tests) - 1 resolved = 13 remaining
- Code Quality: 9
- Documentation: 3
- Enhancement: 5
- Testing: 3 (new category from test failures)

**Total Estimated Effort:** ~100 hours
**Completed:** ~1 hour
**Remaining:** ~99 hours

**Recently Resolved:**
- ✅ ISSUE-004: Configuration Regex Patterns Too Rigid (2025-10-27)

**Recommended Sprint Allocation:**
- Sprint 1 (Week 1): Critical + High Priority = ~10.5 hours (was 11.5 hours)
- Sprint 2 (Week 2): Medium Priority = ~15 hours
- Sprint 3 (Week 3): Low Priority = ~10.5 hours
- Future Backlog: Enhancements (~46 hours)

**Test-Discovered Issues:**
Issues 025-032 were discovered through pytest test failures and confirm/extend the static analysis findings.

---

## 🚀 QUICK START GUIDE

### For GitHub Issue Creation:

1. **Use GitHub CLI:**
```bash
# Create issue from markdown section
gh issue create --title "Duplicate setup command definition" \
  --body-file - < issue_001.md \
  --label "bug,critical,cli"
```

2. **Bulk Import:**
```bash
# Script to create all issues
python scripts/create_github_issues.py WORK_BREAKDOWN.md
```

3. **Manual Creation:**
   - Copy each ISSUE section
   - Create new GitHub issue
   - Use title, labels, and description from markdown

### For Development Workflow:

1. **Pick an issue by priority**
2. **Create feature branch:**
```bash
git checkout -b fix/issue-001-duplicate-setup
```

3. **Check acceptance criteria in issue**
4. **Implement fix**
5. **Run tests:**
```bash
pytest tests/ -v
```

6. **Create PR referencing issue:**
```bash
gh pr create --title "Fix: Remove duplicate setup command" \
  --body "Closes #1"
```

---

## 📝 NOTES

- Issues are numbered sequentially for easy reference
- Each issue has all information needed for implementation
- Acceptance criteria provide clear definition of done
- Estimated efforts are rough guides, adjust as needed
- Labels follow GitHub standard conventions
- Priority based on impact and effort required

---

*Generated by PodKnow Codebase Analysis Tool*
*Last Updated: 2025-10-27*
