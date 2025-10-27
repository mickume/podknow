#!/usr/bin/env python3
"""
Script to create GitHub issues from WORK_BREAKDOWN.md

Usage:
    python scripts/create_github_issues.py [--dry-run] [--priority PRIORITY]

Options:
    --dry-run       Show what would be created without actually creating issues
    --priority      Only create issues with specific priority (critical, high, medium, low)
    --skip-existing Check if issue exists before creating (by title)

Requirements:
    - GitHub CLI (gh) must be installed and authenticated
    - Run from repository root directory
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional
import argparse


class IssueParser:
    """Parse WORK_BREAKDOWN.md and extract issue information."""

    PRIORITY_ICONS = {
        '🔴': 'critical',
        '🟡': 'high',
        '🟠': 'medium',
        '🔵': 'low',
        '📊': 'enhancement'
    }

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.content = file_path.read_text(encoding='utf-8')

    def parse_issues(self) -> List[Dict]:
        """Parse all issues from the markdown file."""
        issues = []

        # Find all ISSUE-XXX sections
        issue_pattern = r'### (ISSUE-\d+): (.+?)\n\n\*\*Severity:\*\* (.+?)\n\*\*Type:\*\* (.+?)\n\*\*Labels:\*\* (.+?)\n\n\*\*Description:\*\*\n(.+?)(?=\n### |$)'

        matches = re.finditer(issue_pattern, self.content, re.DOTALL)

        for match in matches:
            issue_id = match.group(1)
            title = match.group(2).strip()
            severity_icon = match.group(3).strip().split()[0]
            issue_type = match.group(4).strip()
            labels = match.group(5).strip()

            # Extract full content for this issue
            full_content = self._extract_full_issue(issue_id)

            # Parse priority from icon
            priority = self.PRIORITY_ICONS.get(severity_icon, 'medium')

            # Parse labels
            label_list = [l.strip().strip('`') for l in labels.split(',')]

            issue = {
                'id': issue_id,
                'title': title,
                'priority': priority,
                'type': issue_type,
                'labels': label_list,
                'body': full_content
            }

            issues.append(issue)

        return issues

    def _extract_full_issue(self, issue_id: str) -> str:
        """Extract full content for a specific issue."""
        # Find start of issue
        start_pattern = f'### {issue_id}:'
        start_idx = self.content.find(start_pattern)

        if start_idx == -1:
            return ""

        # Find end of issue (next ### or end of section)
        next_issue_pattern = r'\n### ISSUE-\d+:'
        next_issue = re.search(next_issue_pattern, self.content[start_idx + len(start_pattern):])

        if next_issue:
            end_idx = start_idx + len(start_pattern) + next_issue.start()
        else:
            # Check for section break
            section_break = self.content.find('\n## ', start_idx + len(start_pattern))
            if section_break != -1:
                end_idx = section_break
            else:
                end_idx = len(self.content)

        full_content = self.content[start_idx:end_idx].strip()

        # Remove the title line (already in title)
        lines = full_content.split('\n')
        body_lines = []
        skip_until_description = True

        for line in lines[1:]:  # Skip title line
            if '**Description:**' in line:
                skip_until_description = False
                continue
            if skip_until_description and line.startswith('**'):
                continue
            body_lines.append(line)

        return '\n'.join(body_lines).strip()


class GitHubIssueCreator:
    """Create GitHub issues using gh CLI."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self._check_gh_cli()

    def _check_gh_cli(self):
        """Check if gh CLI is installed and authenticated."""
        try:
            result = subprocess.run(
                ['gh', 'auth', 'status'],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print("❌ GitHub CLI not authenticated. Run: gh auth login")
                sys.exit(1)
        except FileNotFoundError:
            print("❌ GitHub CLI (gh) not found. Install from: https://cli.github.com/")
            sys.exit(1)

    def create_issue(self, issue: Dict) -> bool:
        """Create a single GitHub issue."""
        title = f"{issue['id']}: {issue['title']}"
        body = issue['body']
        labels = ','.join(issue['labels'])

        if self.dry_run:
            print(f"\n{'='*60}")
            print(f"Would create issue: {title}")
            print(f"Labels: {labels}")
            print(f"Priority: {issue['priority']}")
            print(f"Body length: {len(body)} chars")
            print(f"{'='*60}")
            return True

        try:
            # Create issue using gh CLI
            result = subprocess.run(
                [
                    'gh', 'issue', 'create',
                    '--title', title,
                    '--body', body,
                    '--label', labels
                ],
                capture_output=True,
                text=True,
                check=True
            )

            issue_url = result.stdout.strip()
            print(f"✅ Created: {issue_url}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to create issue {issue['id']}: {e.stderr}")
            return False

    def issue_exists(self, title: str) -> bool:
        """Check if an issue with similar title already exists."""
        try:
            result = subprocess.run(
                ['gh', 'issue', 'list', '--search', title, '--json', 'title'],
                capture_output=True,
                text=True,
                check=True
            )

            # If result is not empty JSON array, issue exists
            return result.stdout.strip() != '[]'

        except subprocess.CalledProcessError:
            return False


def main():
    parser = argparse.ArgumentParser(
        description='Create GitHub issues from WORK_BREAKDOWN.md'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be created without creating issues'
    )
    parser.add_argument(
        '--priority',
        choices=['critical', 'high', 'medium', 'low', 'enhancement'],
        help='Only create issues with specific priority'
    )
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip issues that already exist'
    )
    parser.add_argument(
        '--file',
        type=Path,
        default=Path('WORK_BREAKDOWN.md'),
        help='Path to work breakdown file (default: WORK_BREAKDOWN.md)'
    )

    args = parser.parse_args()

    # Check if file exists
    if not args.file.exists():
        print(f"❌ File not found: {args.file}")
        print("Run this script from the repository root directory.")
        sys.exit(1)

    # Parse issues
    print(f"📖 Parsing issues from {args.file}...")
    issue_parser = IssueParser(args.file)
    issues = issue_parser.parse_issues()

    print(f"📊 Found {len(issues)} issues")

    # Filter by priority if specified
    if args.priority:
        issues = [i for i in issues if i['priority'] == args.priority]
        print(f"🔍 Filtered to {len(issues)} issues with priority: {args.priority}")

    if not issues:
        print("No issues to create.")
        return

    # Create issues
    creator = GitHubIssueCreator(dry_run=args.dry_run)

    created = 0
    skipped = 0
    failed = 0

    print(f"\n{'🔍 DRY RUN MODE' if args.dry_run else '🚀 CREATING ISSUES'}...")
    print(f"{'='*60}\n")

    for issue in issues:
        title = f"{issue['id']}: {issue['title']}"

        # Check if issue exists
        if args.skip_existing and not args.dry_run:
            if creator.issue_exists(issue['title']):
                print(f"⏭️  Skipped (exists): {title}")
                skipped += 1
                continue

        # Create issue
        if creator.create_issue(issue):
            created += 1
        else:
            failed += 1

    # Print summary
    print(f"\n{'='*60}")
    print("📊 Summary:")
    print(f"  ✅ Created: {created}")
    if skipped > 0:
        print(f"  ⏭️  Skipped: {skipped}")
    if failed > 0:
        print(f"  ❌ Failed: {failed}")
    print(f"{'='*60}")

    if args.dry_run:
        print("\n💡 Remove --dry-run to actually create issues")


if __name__ == '__main__':
    main()
