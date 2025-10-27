# PodKnow Issues Checklist

Quick reference checklist for tracking issue resolution.

## 🔴 CRITICAL PRIORITY

- [ ] **ISSUE-001**: Duplicate `setup` Command Definition
  - Files: `podknow/cli/main.py`
  - Effort: 30 min

- [x] **ISSUE-002**: Missing `AnalysisError` Import in CLI ✅ **FIXED (2025-10-27)**
  - Files: `podknow/cli/main.py`
  - Effort: 10 min

- [ ] **ISSUE-003**: Inconsistent Prompt Naming Convention
  - Files: `workflow.py`, `analysis.py`, `manager.py`, `models.py`
  - Effort: 20 min

**Critical Total: 3 issues, ~60 minutes**

---

## 🟡 HIGH PRIORITY

- [x] **ISSUE-004**: Configuration Regex Patterns Too Rigid ✅ **FIXED (2025-10-27)**
  - Files: `podknow/config/manager.py`
  - Effort: 1 hour

- [ ] **ISSUE-005**: Verify Episode Service Implementation Completeness
  - Files: `podknow/services/episode.py`, `workflow.py`
  - Effort: 2 hours

- [ ] **ISSUE-006**: Progress Bar Display Complexity and Duplication
  - Files: `transcription.py`, `analysis.py`, `workflow.py`
  - Effort: 4 hours

- [ ] **ISSUE-007**: Inconsistent Error Handling Across CLI Commands
  - Files: `podknow/cli/main.py`
  - Effort: 3 hours

- [x] **ISSUE-025**: Analysis Service Topic Validation Too Strict ⚡ ✅ **FIXED (2025-10-27)**
  - Files: `podknow/models/analysis.py`, `services/analysis.py`
  - Effort: 30 min

**High Priority Total: 5 issues, ~10.5 hours**

---

## 🟠 MEDIUM PRIORITY

- [ ] **ISSUE-008**: Replace Print Statements with Proper Logging
  - Files: `discovery.py`, `analysis.py`, `rss.py`, `transcription.py`
  - Effort: 2 hours

- [ ] **ISSUE-009**: Extract Magic Numbers to Named Constants
  - Files: `transcription.py`, `rss.py`, `manager.py`
  - Effort: 1.5 hours

- [ ] **ISSUE-010**: Reduce Coupling Between Workflow and Service Internals
  - Files: `workflow.py`, `transcription.py`
  - Effort: 1 hour

- [ ] **ISSUE-011**: Weak Audio File Format Validation
  - Files: `transcription.py`
  - Effort: 2 hours

- [ ] **ISSUE-012**: Language Detection Requirement Not Enforced Per PRD
  - Files: `prd.md`, `main.py`, `workflow.py`
  - Effort: 1.5 hours

- [ ] **ISSUE-013**: String Formatting Inconsistency
  - Files: Multiple
  - Effort: 1 hour

- [ ] **ISSUE-026**: CLI Integration Test Failures ⚡ **(From Tests)**
  - Files: `tests/test_cli_integration.py`, `cli/main.py`, `workflow.py`
  - Effort: 3 hours

- [x] **ISSUE-027**: Setup Command Test Isolation Problem ⚡ ✅ **FIXED (2025-10-27)**
  - Files: `tests/test_cli_integration.py`, `conftest.py`, `config/manager.py`
  - Effort: 1 hour

- [x] **ISSUE-028**: Keyboard Interrupt Exit Code Incorrect ⚡ ✅ **FIXED (2025-10-27)**
  - Files: `podknow/cli/main.py`
  - Effort: 1 hour

- [x] **ISSUE-029**: Error Exit Codes Not Set Properly ⚡ ✅ **FIXED (2025-10-27)**
  - Files: `podknow/cli/main.py`
  - Effort: 1 hour

**Medium Priority Total: 10 issues, ~15 hours**

---

## 🔵 LOW PRIORITY

- [ ] **ISSUE-014**: Missing Type Hints in Helper Methods
  - Files: `manager.py`, various
  - Effort: 2 hours

- [ ] **ISSUE-015**: Improve Code Comments and TODO Tracking
  - Files: Multiple
  - Effort: 1 hour

- [ ] **ISSUE-016**: Unused Exception Import in Workflow
  - Files: `workflow.py`
  - Effort: 10 min

- [ ] **ISSUE-017**: Verify Claude Model Version IDs
  - Files: `constants.py`
  - Effort: 30 min

- [ ] **ISSUE-018**: Fix Documentation Typo
  - Files: `prd.md`
  - Effort: 5 min

- [ ] **ISSUE-019**: Update README with Correct CLI Examples
  - Files: `README.md`
  - Effort: 30 min

- [x] **ISSUE-030**: Mock Setup Issues in Tests ⚡ ✅ **FIXED (2025-10-27)**
  - Files: `tests/test_analysis_service.py`, `conftest.py`
  - Effort: 2 hours

- [x] **ISSUE-031**: Audio Processing Tests Need Mocking ⚡ ✅ **FIXED (2025-10-27)**
  - Files: `tests/test_transcription_service.py`
  - Effort: 2 hours

- [x] **ISSUE-032**: Workflow Integration Tests Need Better Mocks ⚡ ✅ **FIXED (2025-10-27)**
  - Files: `tests/test_workflow_integration.py`
  - Effort: 2 hours

**Low Priority Total: 9 issues, ~10.5 hours**

---

## 📊 ENHANCEMENTS (BACKLOG)

- [ ] **ISSUE-020**: Add Comprehensive Unit Tests (20h)
- [ ] **ISSUE-021**: Create Centralized Progress Management System (6h)
- [ ] **ISSUE-022**: Implement Analysis Result Caching (4h)
- [ ] **ISSUE-023**: Add Batch Processing Support (12h)
- [ ] **ISSUE-024**: Create Development Container Configuration (4h)

**Enhancements Total: 5 issues, ~46 hours**

---

## 📈 PROGRESS TRACKING

**Sprint 1 - Critical & High Priority**
- Start: ____/____/____
- Target: 3 days
- Completed: ___/8 issues

**Sprint 2 - Medium Priority**
- Start: ____/____/____
- Target: 4 days
- Completed: ___/10 issues

**Sprint 3 - Low Priority**
- Start: ____/____/____
- Target: 3 days
- Completed: ___/9 issues

**Note:** ⚡ indicates issues discovered through pytest test failures

---

## 🎯 COMPLETION METRICS

| Priority | Total | Done | Percentage |
|----------|-------|------|------------|
| Critical | 3     | 1    | 33%        |
| High     | 5     | 2    | 40%        |
| Medium   | 10    | 3    | 30%        |
| Low      | 9     | 3    | 33%        |
| **Total**| **27**| **9**| **33%**    |

**Note:** Total excludes 5 enhancement issues in backlog (ISSUE-020 through ISSUE-024)

**Recently Fixed (2025-10-27):**
- ✅ ISSUE-002: Missing AnalysisError Import in CLI
- ✅ ISSUE-004: Configuration Regex Patterns Too Rigid
- ✅ ISSUE-025: Analysis Service Topic Validation Too Strict
- ✅ ISSUE-027: Setup Command Test Isolation Problem
- ✅ ISSUE-028: Keyboard Interrupt Exit Code Incorrect
- ✅ ISSUE-029: Error Exit Codes Not Set Properly
- ✅ ISSUE-030: Mock Setup Issues in Tests
- ✅ ISSUE-031: Audio Processing Tests Need Mocking
- ✅ ISSUE-032: Workflow Integration Tests Need Better Mocks

---

## 📋 QUICK COMMANDS

### Start working on an issue:
```bash
git checkout -b fix/issue-XXX-short-description
```

### Run tests after fix:
```bash
pytest tests/ -v --cov=podknow
```

### Create PR:
```bash
gh pr create --title "Fix: Issue XXX description" --body "Closes #XXX"
```

### Update this checklist:
```bash
# Mark issue as done by changing [ ] to [x]
# Update completion percentage
```

---

*Last Updated: 2025-10-27*
*Next Review: TBD*
