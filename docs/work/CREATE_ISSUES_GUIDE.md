# Quick Guide: Creating GitHub Issues

**All issues are now in WORK_BREAKDOWN.md and ready to be created!**

---

## 🚀 Automated Method (Recommended)

### Prerequisites:
```bash
# 1. Install GitHub CLI (if not already installed)
brew install gh

# 2. Authenticate
gh auth login

# 3. Navigate to project directory
cd /path/to/podknow
```

### Create All Issues:
```bash
# Preview what will be created
python scripts/create_github_issues.py --dry-run

# Create all 32 issues
python scripts/create_github_issues.py
```

### Create by Priority:
```bash
# Create only critical issues (001-003)
python scripts/create_github_issues.py --priority critical

# Create only high priority (004-007, 025)
python scripts/create_github_issues.py --priority high

# Create only medium priority (008-013, 026-029)
python scripts/create_github_issues.py --priority medium

# Create only low priority (014-019, 030-032)
python scripts/create_github_issues.py --priority low

# Create only enhancements (020-024)
python scripts/create_github_issues.py --priority enhancement
```

### Advanced Options:
```bash
# Skip issues that already exist
python scripts/create_github_issues.py --skip-existing

# Combine options
python scripts/create_github_issues.py --priority critical --skip-existing --dry-run
```

---

## 📝 Manual Method

### Step-by-Step:

1. **Open WORK_BREAKDOWN.md**
2. **Find an issue** (e.g., ISSUE-001)
3. **Copy the entire section** from the heading to the "---"
4. **Go to GitHub:**
   - Click "Issues" tab
   - Click "New Issue"
5. **Fill in the form:**
   - **Title:** `ISSUE-XXX: Title from the heading`
   - **Description:** Paste the copied content
   - **Labels:** Add labels listed in the issue
   - **Assignee:** Assign if needed
   - **Milestone:** Add to sprint if needed
6. **Create issue**
7. **Repeat for remaining issues**

### Example:

For ISSUE-001:
```
Title: ISSUE-001: Duplicate setup Command Definition

Labels: bug, critical, cli, technical-debt

Description:
[Paste the entire ISSUE-001 section from WORK_BREAKDOWN.md]
```

---

## 📊 Recommended Creation Order

### Phase 1: Critical + High (Do First)
```bash
# Create critical issues (should take <1 min to create, <1 hour to fix)
python scripts/create_github_issues.py --priority critical

# Create high priority issues
python scripts/create_github_issues.py --priority high
```

**Result:** 8 issues created
**Fix time:** ~11.5 hours

### Phase 2: Medium Priority (Do Next)
```bash
# Create medium priority issues
python scripts/create_github_issues.py --priority medium
```

**Result:** 10 issues created
**Fix time:** ~15 hours

### Phase 3: Low Priority (Do Later)
```bash
# Create low priority issues
python scripts/create_github_issues.py --priority low
```

**Result:** 9 issues created
**Fix time:** ~10.5 hours

### Phase 4: Enhancements (Backlog)
```bash
# Create enhancement issues (can be done later)
python scripts/create_github_issues.py --priority enhancement
```

**Result:** 5 issues created
**Fix time:** ~46 hours

---

## 🎯 Quick Start (Most Common)

### Create Critical and High Priority Only:
```bash
# Day 1: Create urgent issues
python scripts/create_github_issues.py --priority critical
python scripts/create_github_issues.py --priority high

# Fix them (11.5 hours work)

# Day 2-3: Create and fix medium priority
python scripts/create_github_issues.py --priority medium

# Fix them (15 hours work)
```

---

## ✅ Verification

After creating issues, verify:

```bash
# List all issues
gh issue list

# Count issues by label
gh issue list --label "bug"
gh issue list --label "critical"
gh issue list --label "high-priority"

# View specific issue
gh issue view 1
```

---

## 🔍 What Each Issue Contains

Every issue in WORK_BREAKDOWN.md includes:

- ✅ **Title** - Clear, descriptive issue name
- ✅ **Severity** - Priority level (Critical/High/Medium/Low)
- ✅ **Type** - Bug/Code Quality/Documentation/Enhancement
- ✅ **Labels** - GitHub labels for organization
- ✅ **Description** - What the problem is
- ✅ **Test Evidence** - Proof from tests (for issues 025-032)
- ✅ **Files Affected** - Which files need changes
- ✅ **Proposed Solution** - How to fix it
- ✅ **Code Examples** - Specific code changes
- ✅ **Acceptance Criteria** - Definition of done
- ✅ **Estimated Effort** - Time to fix

---

## 🎨 Labels to Use

When creating issues manually, use these labels:

### By Severity:
- `critical` - ISSUE-001, 002, 003
- `high-priority` - ISSUE-004, 005, 006, 007, 025
- `medium-priority` - ISSUE-008 through 013, 026-029
- `low-priority` - ISSUE-014 through 019, 030-032

### By Type:
- `bug` - Most issues
- `enhancement` - ISSUE-020 through 024
- `documentation` - ISSUE-012, 018, 019
- `testing` - ISSUE-030, 031, 032
- `technical-debt` - ISSUE-001, 030

### By Component:
- `cli` - Command-line interface issues
- `analysis` - Analysis service issues
- `configuration` - Config-related issues
- `workflow` - Workflow orchestration issues
- `audio-processing` - Audio/transcription issues

---

## 💡 Pro Tips

### Tip 1: Create Issues in Batches
```bash
# Create and work on critical first
python scripts/create_github_issues.py --priority critical
# Fix them
# Then create high priority
python scripts/create_github_issues.py --priority high
```

### Tip 2: Use GitHub Projects
After creating issues:
1. Go to "Projects" tab
2. Create "PodKnow Improvements" project
3. Add all issues to project
4. Organize by sprint/priority

### Tip 3: Link Issues to PRs
When fixing issues:
```bash
# In commit messages
git commit -m "Fix: Remove duplicate setup function

Closes #1"

# In PR descriptions
gh pr create --title "Fix critical issues" \
  --body "Closes #1, Closes #2, Closes #3"
```

### Tip 4: Use Milestones
```bash
# Create milestones
gh api repos/:owner/:repo/milestones -f title="Sprint 1" -f due_on="2025-11-03T00:00:00Z"

# Add issues to milestone
gh issue edit 1 --milestone "Sprint 1"
```

---

## 🆘 Troubleshooting

### Error: "GitHub CLI not found"
```bash
# Install GitHub CLI
brew install gh  # macOS
# or visit https://cli.github.com/
```

### Error: "Not authenticated"
```bash
# Login to GitHub
gh auth login
# Follow the prompts
```

### Error: "Permission denied"
```bash
# Make sure you have write access to the repository
# Check repository settings
```

### Error: "Issue already exists"
```bash
# Use --skip-existing flag
python scripts/create_github_issues.py --skip-existing

# Or delete duplicate and try again
gh issue delete 123
```

---

## 📊 Expected Results

After running all commands, you should have:

- ✅ **32 GitHub issues created**
- ✅ **All properly labeled and organized**
- ✅ **Ready to assign and work on**
- ✅ **Linked to WORK_BREAKDOWN.md for details**

---

## 🎉 You're Done!

**Next steps:**
1. ✅ Issues are created in GitHub
2. ⏭️ Assign issues to team members
3. ⏭️ Start fixing critical issues
4. ⏭️ Track progress in ISSUES_CHECKLIST.md
5. ⏭️ Close issues as PRs are merged

---

*Guide created: 2025-10-27*
*All 32 issues ready to create*
*Estimated creation time: 5-10 minutes (automated) or 30-60 minutes (manual)*
