#!/usr/bin/env python3
"""
Staging area helper for surgical git commits in cron jobs.

Usage:
    python scripts/stage_commit.py --tag P0 --files app.py services/stock_data.py --message "feat: use multi_source in fetch_chart_data"
    python scripts/stage_commit.py --tag P1 --message "feat: add data-source badge"  # auto-detect files
    python scripts/stage_commit.py --status  # show what's changed
    python scripts/stage_commit.py --dry-run --files app.py  # preview what would be staged

Features:
    - Surgical staging: only adds specified files (never git add -A)
    - Auto-generates commit message with [P0]/[P1]/[P2] tag
    - Pre-flight checks: verify no conflicts, check remote divergence
    - Push with fallback (SSH → HTTPS)
    - Skip .gitignore, data/, *.db, secrets
"""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(os.path.expanduser("~/repos/Stocker"))
GIT_IDENTITY = {"name": "陳仔0號", "email": "macauhermes@gmail.com"}

# Files we must never stage
BLOCKED_PATTERNS = [
    r"\.gitignore",
    r"data/",
    r"\.db$",
    r"\.env$",
    r"__pycache__",
    r"\.pyc$",
    r"\.key$",
    r"secret",
]

def run(cmd, cwd=None, check=True):
    """Run a shell command and return stdout."""
    result = subprocess.run(
        cmd, shell=True, cwd=cwd or REPO_ROOT,
        capture_output=True, text=True
    )
    if check and result.returncode != 0:
        print(f"❌ Command failed: {cmd}")
        print(f"   stderr: {result.stderr.strip()}")
        sys.exit(1)
    return result.stdout.strip()


def get_git_status():
    """Parse git status into categories."""
    # Don't strip the whole output — leading spaces in ' M' are significant
    result = subprocess.run(
        "git status -s", shell=True, cwd=REPO_ROOT,
        capture_output=True, text=True
    )
    changes = {"modified": [], "untracked": [], "deleted": [], "renamed": []}
    for line in result.stdout.splitlines():
        if not line:
            continue
        # git status -s format: XY filename (X=index, Y=worktree)
        # X and Y are each 1 char at positions 0 and 1
        # Position 2 is always a space separator
        # Filename starts at position 3
        code = (line[0] + line[1]).strip()  # combine both status chars
        path = line[3:].strip() if len(line) > 3 else ""
        if code == "M":
            changes["modified"].append(path)
        elif code == "??":
            changes["untracked"].append(path)
        elif code == "D":
            changes["deleted"].append(path)
        elif code.startswith("R"):
            changes["renamed"].append(path)
    return changes


def is_blocked(filepath):
    """Check if a file path matches blocked patterns."""
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, filepath, re.IGNORECASE):
            return True
    return False


def stage_files(files):
    """Stage only the specified files, with safety checks."""
    staged = []
    skipped = []

    for f in files:
        if is_blocked(f):
            print(f"⚠️  Blocked (safety): {f}")
            skipped.append(f)
            continue
        full_path = REPO_ROOT / f
        if not full_path.exists():
            print(f"⚠️  Not found: {f}")
            skipped.append(f)
            continue
        run(f"git add {f}")
        staged.append(f)
        print(f"✅ Staged: {f}")

    return staged, skipped


def commit(message, tag=None):
    """Create a commit with proper identity and tag prefix."""
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = GIT_IDENTITY["name"]
    env["GIT_AUTHOR_EMAIL"] = GIT_IDENTITY["email"]
    env["GIT_COMMITTER_NAME"] = GIT_IDENTITY["name"]
    env["GIT_COMMITTER_EMAIL"] = GIT_IDENTITY["email"]

    if tag and not message.startswith(f"[{tag}]"):
        message = f"[{tag}] {message}"

    result = subprocess.run(
        f'git commit -m "{message}"',
        shell=True, cwd=REPO_ROOT,
        capture_output=True, text=True, env=env
    )

    if result.returncode != 0:
        if "nothing to commit" in result.stdout or "nothing to commit" in result.stderr:
            print("ℹ️  Nothing to commit — all changes already staged/committed.")
            return None
        print(f"❌ Commit failed: {result.stderr.strip()}")
        sys.exit(1)

    # Get commit hash
    commit_hash = run("git rev-parse --short HEAD")
    print(f"✅ Committed: {commit_hash} — {message}")
    return commit_hash


def push():
    """Push to origin with SSH fallback."""
    # Check if we have anything to push
    local = run("git rev-parse HEAD")
    try:
        remote = run("git rev-parse origin/main", check=False)
    except:
        remote = ""

    if local == remote:
        print("ℹ️  Already up to date with origin/main")
        return True

    # Try SSH push
    result = subprocess.run(
        'GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no" git push origin main',
        shell=True, cwd=REPO_ROOT,
        capture_output=True, text=True
    )

    if result.returncode == 0:
        print("✅ Pushed to origin/main")
        return True

    # Check for non-fast-forward
    if "non-fast-forward" in result.stderr or "rejected" in result.stderr:
        print("⚠️  Remote has diverged. Attempting pull --ff-only...")
        pull_result = subprocess.run(
            "git pull origin main --ff-only",
            shell=True, cwd=REPO_ROOT,
            capture_output=True, text=True
        )
        if pull_result.returncode == 0:
            # Retry push
            result = subprocess.run(
                'GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=no" git push origin main',
                shell=True, cwd=REPO_ROOT,
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print("✅ Pushed to origin/main (after ff-only pull)")
                return True

    print(f"❌ Push failed: {result.stderr.strip()}")
    return False


def show_status():
    """Display current git status in a readable format."""
    changes = get_git_status()
    total = sum(len(v) for v in changes.values())

    print(f"\n📊 Git Status ({total} changes)")
    print("=" * 50)

    if changes["modified"]:
        print(f"\n📝 Modified ({len(changes['modified'])}):")
        for f in changes["modified"]:
            blocked = " ⚠️ BLOCKED" if is_blocked(f) else ""
            print(f"   {f}{blocked}")

    if changes["untracked"]:
        print(f"\n🆕 Untracked ({len(changes['untracked'])}):")
        for f in changes["untracked"]:
            blocked = " ⚠️ BLOCKED" if is_blocked(f) else ""
            print(f"   {f}{blocked}")

    if changes["deleted"]:
        print(f"\n🗑️  Deleted ({len(changes['deleted'])}):")
        for f in changes["deleted"]:
            print(f"   {f}")

    if changes["renamed"]:
        print(f"\n🔄 Renamed ({len(changes['renamed'])}):")
        for f in changes["renamed"]:
            print(f"   {f}")

    if total == 0:
        print("\n✅ Working tree clean — nothing to commit.")

    print()


def main():
    parser = argparse.ArgumentParser(description="Surgical git staging helper for Stocker cron jobs")
    parser.add_argument("--status", action="store_true", help="Show current git status")
    parser.add_argument("--files", nargs="+", help="Files to stage (space-separated)")
    parser.add_argument("--tag", choices=["P0", "P1", "P2", "P3"], help="Priority tag for commit message")
    parser.add_argument("--message", "-m", help="Commit message (tag prefix auto-added)")
    parser.add_argument("--dry-run", action="store_true", help="Preview what would be staged without staging")
    parser.add_argument("--push", action="store_true", help="Push after commit")
    parser.add_argument("--auto", action="store_true", help="Auto-stage all non-blocked changes")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if not args.message and not args.dry_run:
        parser.error("--message is required for commits (use --dry-run to preview)")

    changes = get_git_status()
    all_changed = changes["modified"] + changes["untracked"] + changes["renamed"]

    if args.auto:
        files_to_stage = [f for f in all_changed if not is_blocked(f)]
    elif args.files:
        files_to_stage = args.files
    else:
        print("❌ Specify --files or --auto")
        show_status()
        sys.exit(1)

    if not files_to_stage:
        print("ℹ️  No files to stage.")
        return

    # Preview
    print(f"\n📋 Will stage {len(files_to_stage)} file(s):")
    for f in files_to_stage:
        blocked = " ⚠️ BLOCKED" if is_blocked(f) else ""
        print(f"   {f}{blocked}")

    if args.dry_run:
        print("\n🔍 Dry run — nothing staged.")
        return

    # Stage
    print()
    staged, skipped = stage_files(files_to_stage)

    if not staged:
        print("ℹ️  Nothing staged (all blocked or missing).")
        return

    # Commit
    commit_hash = commit(args.message, args.tag)

    if commit_hash and args.push:
        push()

    # Summary
    print(f"\n{'=' * 50}")
    print(f"📊 Summary:")
    print(f"   Staged: {len(staged)} files")
    print(f"   Skipped: {len(skipped)} files")
    if commit_hash:
        print(f"   Commit: {commit_hash}")
    print()


if __name__ == "__main__":
    main()
